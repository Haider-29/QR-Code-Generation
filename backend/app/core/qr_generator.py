import qrcode
import qrcode.util
from PIL import Image, ImageDraw, UnidentifiedImageError
import os
import io
import math
import threading
import sys

# Configuration Constants
DEBUG_CONTAINED_MODE = False
DEFAULT_BACKGROUND_IMAGE_MODE = "Stretched"
DEFAULT_FINDER_PATTERN_SHAPE = "rounded_square"
DEFAULT_FINDER_COLOR_MODE = "dynamic"
DEFAULT_FINDER_DYNAMIC_SUBMODE = "single-color"
BACKGROUND_PADDING_PX = 60
REDUCE_INNERMOST_BRIGHTNESS = True
INNERMOST_BRIGHTNESS_REDUCTION = 0.25
ROUNDED_RADIUS_FACTOR = 1.2
ENABLE_FINDER_OVERLAY = True
FINDER_OVERLAY_PADDING_PX = 15
FINDER_OVERLAY_COLOR = (255, 255, 255, 128)
DATA_MODULE_SHAPE = "diamond"
DATA_MODULE_COLOR_MODE = "adaptive"
ADAPTIVE_COLOR_RADIUS = 10
ADAPTIVE_LUMINANCE_THRESHOLD = 130
ADAPTIVE_DARKEN_FACTOR = 0.5
ADAPTIVE_LIGHTEN_FACTOR = 0.5
ADAPTIVE_NEAR_WHITE_THRESHOLD = 240
ADAPTIVE_NEAR_BLACK_THRESHOLD = 15
DEFAULT_DATA = "https://www.example.com"
DEFAULT_BOX_SIZE = 25
DEFAULT_BORDER = 4
DEFAULT_PADDING = 4
DEFAULT_DIAMOND_BORDER_WIDTH = 0
DEFAULT_ERROR_CORRECTION = qrcode.constants.ERROR_CORRECT_H
DEFAULT_DARK_MODULE_COLOR = (0, 0, 0, 240)
DEFAULT_LIGHT_MODULE_COLOR = (255, 255, 255, 240)
DEFAULT_BACKGROUND_ALPHA = 255
LUMINOSITY_THRESHOLD = 70
BRIGHTNESS_FILTER = 225
SVG_SUPPORT = True

try:
    import cairosvg
except ImportError:
    SVG_SUPPORT = False

def calculate_hsl_from_rgb(r_in, g_in, b_in):
    if not all(isinstance(x, (int, float)) for x in [r_in, g_in, b_in]):
        return 0, 0, 0
    r, g, b = r_in / 255.0, g_in / 255.0, b_in / 255.0
    cmax, cmin = max(r, g, b), min(r, g, b)
    delta = cmax - cmin
    l = (cmax + cmin) / 2.0
    if delta == 0:
        h, s = 0.0, 0.0
    else:
        if l == 1 or l == 0:
            s = 0.0
        else:
            s = delta / (1 - abs(2 * l - 1))
        if cmax == r:
            h = ((g - b) / delta) % 6 if delta != 0 else 0
        elif cmax == g:
            h = ((b - r) / delta) + 2 if delta != 0 else 0
        else:
            h = ((r - g) / delta) + 4 if delta != 0 else 0
        h = h * 60.0
        h = h + 360.0 if h < 0 else h
    h_scaled = round(h * (240.0 / 360.0))
    s_scaled = round(s * 240.0)
    l_scaled = round(l * 240.0)
    h_scaled = max(0, min(240, h_scaled))
    s_scaled = max(0, min(240, s_scaled))
    l_scaled = max(0, min(240, l_scaled))
    if s_scaled == 0:
        h_scaled = 0
    return h_scaled, s_scaled, l_scaled

def reduce_rgb_brightness(rgb_tuple, factor):
    if not (0.0 <= factor <= 1.0):
        factor = max(0.0, min(1.0, factor))
    scale = 1.0 - factor
    if len(rgb_tuple) == 4:
        r, g, b, a = rgb_tuple
        return (max(0, int(r * scale)), max(0, int(g * scale)), max(0, int(b * scale)), a)
    elif len(rgb_tuple) == 3:
        r, g, b = rgb_tuple
        return (max(0, int(r * scale)), max(0, int(g * scale)), max(0, int(b * scale)))
    else:
        return rgb_tuple

def increase_rgb_brightness(rgb_tuple, factor):
    if not (0.0 <= factor <= 1.0):
        factor = max(0.0, min(1.0, factor))
    if len(rgb_tuple) == 4:
        r, g, b, a = rgb_tuple
        r_new = max(0, min(255, int(r + (255 - r) * factor)))
        g_new = max(0, min(255, int(g + (255 - g) * factor)))
        b_new = max(0, min(255, int(b + (255 - b) * factor)))
        return (r_new, g_new, b_new, a)
    elif len(rgb_tuple) == 3:
        r, g, b = rgb_tuple
        r_new = max(0, min(255, int(r + (255 - r) * factor)))
        g_new = max(0, min(255, int(g + (255 - g) * factor)))
        b_new = max(0, min(255, int(b + (255 - b) * factor)))
        return (r_new, g_new, b_new)
    else:
        return rgb_tuple

def get_dominant_colors(img, resize_thumbnail=(150, 150), num_colors_to_quantize=16):
    try:
        img_rgb = img.convert("RGB")
    except Exception:
        return [(0, 0, 0)] * 3
    img_thumb = img_rgb.copy()
    img_thumb.thumbnail(resize_thumbnail, Image.Resampling.LANCZOS)
    quantized_img, colors_with_counts = None, None
    try:
        quantized_img = img_thumb.quantize(
            colors=num_colors_to_quantize, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
        )
        colors_with_counts = quantized_img.getcolors(maxcolors=img_thumb.size[0] * img_thumb.size[1])
    except Exception:
        pass
    
    dom_cols = []
    if colors_with_counts and quantized_img:
        colors_with_counts.sort(key=lambda item: item[0], reverse=True)
        palette = quantized_img.getpalette()
        if palette:
            indices_seen = set()
            palette_list = list(palette) if isinstance(palette, (bytes, list)) else []
            for count, index in colors_with_counts:
                if index in indices_seen or not palette_list:
                    continue
                start_idx, end_idx = index * 3, index * 3 + 3
                if end_idx <= len(palette_list):
                    dominant_color_rgb = tuple(palette_list[start_idx:end_idx])
                    if len(dominant_color_rgb) == 3 and all(isinstance(c, int) for c in dominant_color_rgb):
                        dom_cols.append(dominant_color_rgb)
                        indices_seen.add(index)
                if len(dom_cols) >= num_colors_to_quantize:
                    break
    
    if not dom_cols:
        try:
            pixel_val = img_rgb.getpixel((0, 0))
            if isinstance(pixel_val, tuple) and len(pixel_val) >= 3 and all(isinstance(c, int) for c in pixel_val[:3]):
                dom_cols = [pixel_val[:3]]
            elif isinstance(pixel_val, int):
                dom_cols = [(pixel_val, pixel_val, pixel_val)]
            else:
                dom_cols = [(0, 0, 0)]
        except Exception:
            dom_cols = [(0, 0, 0)]
    
    if not dom_cols:
        dom_cols.append((0, 0, 0))
    while len(dom_cols) < 3:
        dom_cols.append(dom_cols[-1])
    return dom_cols[:num_colors_to_quantize]

def get_prominent_color_in_region(image, center_x, center_y, radius):
    try:
        x0, y0 = max(0, int(center_x - radius)), max(0, int(center_y - radius))
        x1, y1 = min(image.width, int(center_x + radius)), min(image.height, int(center_y + radius))
        if x1 <= x0 or y1 <= y0:
            try:
                px, py = max(0, min(image.width - 1, int(center_x))), max(0, min(image.height - 1, int(center_y)))
                pixel_val = image.getpixel((px, py))
                if isinstance(pixel_val, tuple) and len(pixel_val) >= 3:
                    return tuple(max(0, min(255, int(c))) for c in pixel_val[:3])
                elif isinstance(pixel_val, int):
                    return (pixel_val, pixel_val, pixel_val)
                else:
                    return (128, 128, 128)
            except Exception:
                return (128, 128, 128)
        
        cropped_img = image.crop((x0, y0, x1, y1))
        if cropped_img.width <= 0 or cropped_img.height <= 0:
            return (128, 128, 128)

        quantized_img, colors_with_counts = None, None
        try:
            cropped_rgb = cropped_img.convert("RGB")
            quantized_img = cropped_rgb.quantize(colors=4, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
            colors_with_counts = quantized_img.getcolors(maxcolors=cropped_rgb.width * cropped_rgb.height)
        except Exception:
            pass

        if colors_with_counts and quantized_img:
            colors_with_counts.sort(key=lambda item: item[0], reverse=True)
            palette = quantized_img.getpalette()
            if palette:
                palette_list = list(palette) if isinstance(palette, (bytes, list)) else []
                if palette_list:
                    most_frequent_index = colors_with_counts[0][1]
                    start_idx, end_idx = most_frequent_index * 3, most_frequent_index * 3 + 3
                    if end_idx <= len(palette_list):
                        dominant_rgb = tuple(palette_list[start_idx:end_idx])
                        if len(dominant_rgb) == 3 and all(isinstance(c, int) for c in dominant_rgb):
                            return dominant_rgb

        try:
            px, py = max(0, min(image.width - 1, int(center_x))), max(0, min(image.height - 1, int(center_y)))
            pixel_val = image.getpixel((px, py))
            if isinstance(pixel_val, tuple) and len(pixel_val) >= 3:
                return tuple(max(0, min(255, int(c))) for c in pixel_val[:3])
            elif isinstance(pixel_val, int):
                return (pixel_val, pixel_val, pixel_val)
            else:
                return (128, 128, 128)
        except Exception:
            return (128, 128, 128)
    except Exception:
        return (128, 128, 128)

def get_contrasting_color(dominant_colors_list, type, luminance_threshold, default_dark_rgba, default_light_rgba):
    suitable_color = None
    default_dark_rgb = default_dark_rgba[:3] if len(default_dark_rgba) >= 3 else (0, 0, 0)
    default_light_rgb = default_light_rgba[:3] if len(default_light_rgba) >= 3 else (255, 255, 255)
    
    if type == "dark":
        for color_tuple in dominant_colors_list:
            if isinstance(color_tuple, tuple) and len(color_tuple) == 3:
                r, g, b = color_tuple
                try:
                    h, s, l = calculate_hsl_from_rgb(r, g, b)
                    if l < luminance_threshold and color_tuple != (0, 0, 0):
                        suitable_color = color_tuple
                        break
                except Exception:
                    continue
        return suitable_color if suitable_color else default_dark_rgb
    elif type == "light":
        for color_tuple in dominant_colors_list:
            if isinstance(color_tuple, tuple) and len(color_tuple) == 3:
                r, g, b = color_tuple
                try:
                    h, s, l = calculate_hsl_from_rgb(r, g, b)
                    if l > luminance_threshold and color_tuple != (255, 255, 255):
                        suitable_color = color_tuple
                        break
                except Exception:
                    continue
        return suitable_color if suitable_color else default_light_rgb
    return default_dark_rgb

def is_finder_pattern_module(r, c, matrix_size):
    if 0 <= r < 7 and 0 <= c < 7:
        return True
    if 0 <= r < 7 and matrix_size - 7 <= c < matrix_size:
        return True
    if matrix_size - 7 <= r < matrix_size and 0 <= c < 7:
        return True
    return False

def get_alignment_pattern_centers(version):
    if version < 2:
        return []
    try:
        positions = qrcode.util.pattern_position(version)
        if not positions:
            return []
        last_pos = positions[-1]
        all_coords = set((r, c) for r in positions for c in positions)
        finder_centers = {(6, 6), (6, last_pos), (last_pos, 6)}
        centers = all_coords - finder_centers
        return list(centers)
    except Exception:
        return []

def is_alignment_pattern_module(r, c, alignment_centers):
    if not isinstance(alignment_centers, list):
        return False
    for item in alignment_centers:
        if (
            isinstance(item, (list, tuple))
            and len(item) == 2
            and all(isinstance(coord, (int, float)) for coord in item)
        ):
            center_r, center_c = item
            if (center_r - 2 <= r <= center_r + 2) and (center_c - 2 <= c <= center_c + 2):
                return True
    return False

def determine_finder_colors(dominant_colors, finder_color_mode, finder_dynamic_submode, reduce_innermost_brightness):
    outer_color = (0, 0, 0, 225)
    black_color_rgba = (0, 0, 0, 225)
    white_color_rgba = (255, 255, 255, 225)
    
    if not isinstance(dominant_colors, list):
        dominant_colors = [(0, 0, 0)] * 3
    while len(dominant_colors) < 3:
        dominant_colors.append(dominant_colors[-1] if dominant_colors else (0, 0, 0))

    if finder_color_mode == "static":
        inner_color_list = [white_color_rgba] * 3
        innermost_color_list = [black_color_rgba] * 3
    elif finder_color_mode == "dynamic":
        if finder_dynamic_submode == "single-color":
            bright_suitable_colors = []
            for color_tuple in dominant_colors:
                if not (isinstance(color_tuple, tuple) and len(color_tuple) == 3):
                    continue
                r, g, b = color_tuple
                if r >= BRIGHTNESS_FILTER and g >= BRIGHTNESS_FILTER and b >= BRIGHTNESS_FILTER:
                    continue
                try:
                    h, s, l = calculate_hsl_from_rgb(r, g, b)
                except Exception:
                    continue
                if l > LUMINOSITY_THRESHOLD and (s > 20 or l > 150):
                    bright_suitable_colors.append(((r, g, b), l))
            bright_suitable_colors.sort(key=lambda item: item[1], reverse=True)
            inner_color_rgb = (255, 255, 255)
            if (
                bright_suitable_colors
                and isinstance(bright_suitable_colors[0][0], tuple)
                and len(bright_suitable_colors[0][0]) == 3
            ):
                inner_color_rgb = bright_suitable_colors[0][0]
            inner_color_list = [tuple(list(inner_color_rgb) + [225])] * 3
            innermost_color_list = [black_color_rgba] * 3
        elif finder_dynamic_submode == "multi-color":
            base_dominant_colors_rgb = []
            for color_tuple in dominant_colors:
                if not (isinstance(color_tuple, tuple) and len(color_tuple) == 3):
                    continue
                r, g, b = color_tuple
                if r >= BRIGHTNESS_FILTER and g >= BRIGHTNESS_FILTER and b >= BRIGHTNESS_FILTER:
                    continue
                base_dominant_colors_rgb.append((r, g, b))
            original_valid_dominants = [c for c in dominant_colors[:3] if isinstance(c, tuple) and len(c) == 3]
            if not base_dominant_colors_rgb:
                base_dominant_colors_rgb = original_valid_dominants if original_valid_dominants else [(0, 0, 0)]
            chosen_innermost_rgb = (
                base_dominant_colors_rgb[:3]
                if len(base_dominant_colors_rgb) >= 3
                else ([base_dominant_colors_rgb[0]] * 3 if base_dominant_colors_rgb else [(0, 0, 0)] * 3)
            )
            processed_innermost_rgb = []
            if reduce_innermost_brightness:
                for rgb in chosen_innermost_rgb:
                    processed_innermost_rgb.append(
                        reduce_rgb_brightness(rgb, INNERMOST_BRIGHTNESS_REDUCTION)
                        if isinstance(rgb, tuple) and len(rgb) == 3
                        else (0, 0, 0)
                    )
            else:
                processed_innermost_rgb = [
                    rgb if isinstance(rgb, tuple) and len(rgb) == 3 else (0, 0, 0) for rgb in chosen_innermost_rgb
                ]
            inner_color_list = [white_color_rgba] * 3
            innermost_color_list = [
                tuple(list(c) + [225]) if isinstance(c, tuple) and len(c) == 3 else black_color_rgba
                for c in processed_innermost_rgb
            ]
        else:
            inner_color_list = [white_color_rgba] * 3
            innermost_color_list = [black_color_rgba] * 3
    else:
        inner_color_list = [white_color_rgba] * 3
        innermost_color_list = [black_color_rgba] * 3

    while len(inner_color_list) < 3:
        inner_color_list.append(white_color_rgba)
    while len(innermost_color_list) < 3:
        innermost_color_list.append(black_color_rgba)
    return outer_color, inner_color_list[:3], innermost_color_list[:3]

def _draw_single_shape_circle(draw, center_x, center_y, radius_px, fill_color):
    if radius_px <= 0:
        return
    x0, y0 = center_x - radius_px, center_y - radius_px
    x1, y1 = center_x + radius_px, center_y + radius_px
    if x1 > x0 and y1 > y0:
        try:
            draw.ellipse([(x0, y0), (x1, y1)], fill=fill_color)
        except Exception:
            pass

def _draw_single_shape_square(draw, center_x, center_y, size_px, fill_color):
    if size_px <= 0:
        return
    half_size_px = size_px / 2.0
    x0, y0 = center_x - half_size_px, center_y - half_size_px
    x1, y1 = center_x + half_size_px, center_y + half_size_px
    if x0 < x1 and y0 < y1:
        try:
            draw.rectangle([(x0, y0), (x1, y1)], fill=fill_color)
        except Exception:
            pass

def _draw_single_shape_rounded_square(draw, center_x, center_y, size_px, corner_radius_px, fill_color):
    if size_px <= 0:
        return
    half_size_px = size_px / 2.0
    x0, y0 = center_x - half_size_px, center_y - half_size_px
    x1, y1 = center_x + half_size_px, center_y + half_size_px
    if x0 < x1 and y0 < y1:
        actual_radius = min(corner_radius_px, (x1 - x0) / 2, (y1 - y0) / 2)
        actual_radius = max(0, actual_radius)
        try:
            if actual_radius >= 0.5:
                draw.rounded_rectangle([(x0, y0), (x1, y1)], fill=fill_color, radius=actual_radius)
            else:
                draw.rectangle([(x0, y0), (x1, y1)], fill=fill_color)
        except Exception:
            pass

def draw_finder_patterns(final_image, matrix_size, module_size, border_modules, finder_shape, outer_color, inner_color_list, innermost_color_list, enable_overlay, overlay_padding_px, overlay_color):
    finder_base_size_modules = 7
    center_offset_modules = 3.5
    centers_px = []
    tl_cx = (center_offset_modules + border_modules) * module_size
    tl_cy = tl_cx
    tr_cx = ((matrix_size - finder_base_size_modules) + center_offset_modules + border_modules) * module_size
    bl_cy = ((matrix_size - finder_base_size_modules) + center_offset_modules + border_modules) * module_size
    centers_px.extend([(tl_cx, tl_cy), (tr_cx, tl_cy), (tl_cx, bl_cy)])

    if enable_overlay and overlay_padding_px >= 0:
        overlay_layer = Image.new("RGBA", final_image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay_layer)
        base_size_px = finder_base_size_modules * module_size
        shape_to_draw_overlay = finder_shape if finder_shape in ["circle", "square", "rounded_square"] else "square"
        overlay_radius_px, overlay_size_px, overlay_corner_radius_px = 0, 0, 0
        if shape_to_draw_overlay == "circle":
            overlay_radius_px = (base_size_px / 2.0) + overlay_padding_px
        elif shape_to_draw_overlay in ["square", "rounded_square"]:
            overlay_size_px = base_size_px + (2 * overlay_padding_px)
            if shape_to_draw_overlay == "rounded_square":
                base_corner_radius = module_size * ROUNDED_RADIUS_FACTOR
                overlay_corner_radius_px = max(0, min(base_corner_radius, overlay_size_px / 2.0))
        for center_x_px, center_y_px in centers_px:
            try:
                if shape_to_draw_overlay == "circle":
                    _draw_single_shape_circle(overlay_draw, center_x_px, center_y_px, overlay_radius_px, overlay_color)
                elif shape_to_draw_overlay == "square":
                    _draw_single_shape_square(overlay_draw, center_x_px, center_y_px, overlay_size_px, overlay_color)
                elif shape_to_draw_overlay == "rounded_square":
                    _draw_single_shape_rounded_square(overlay_draw, center_x_px, center_y_px, overlay_size_px, overlay_corner_radius_px, overlay_color)
            except Exception:
                pass
        if final_image.mode != "RGBA":
            final_image = final_image.convert("RGBA")
        final_image.alpha_composite(overlay_layer)
        del overlay_draw, overlay_layer

    pattern_layer = Image.new("RGBA", final_image.size, (0, 0, 0, 0))
    pattern_draw = ImageDraw.Draw(pattern_layer)
    finder_sizes_sq = [7.0 * module_size, 5.0 * module_size, 3.0 * module_size]
    finder_radii_circ = [3.5 * module_size, 2.5 * module_size, 1.5 * module_size]
    pattern_corner_radius_px = module_size * ROUNDED_RADIUS_FACTOR
    shape_to_draw = finder_shape if finder_shape in ["circle", "square", "rounded_square"] else "square"

    for i, (center_x_px, center_y_px) in enumerate(centers_px):
        pattern_colors = [outer_color, inner_color_list[i], innermost_color_list[i]]
        if shape_to_draw == "circle":
            for layer_idx, radius_px in enumerate(finder_radii_circ):
                _draw_single_shape_circle(pattern_draw, center_x_px, center_y_px, radius_px, pattern_colors[layer_idx])
        elif shape_to_draw == "square":
            for layer_idx, size_px in enumerate(finder_sizes_sq):
                _draw_single_shape_square(pattern_draw, center_x_px, center_y_px, size_px, pattern_colors[layer_idx])
        elif shape_to_draw == "rounded_square":
            for layer_idx, size_px in enumerate(finder_sizes_sq):
                _draw_single_shape_rounded_square(pattern_draw, center_x_px, center_y_px, size_px, pattern_corner_radius_px, pattern_colors[layer_idx])

    if final_image.mode != "RGBA":
        final_image = final_image.convert("RGBA")
    final_image.alpha_composite(pattern_layer)
    del pattern_draw, pattern_layer

def draw_alignment_patterns(final_image, alignment_centers, module_size, border_modules, pattern_shape, outer_color, inner_color, innermost_color):
    if not alignment_centers:
        return
    align_pattern_layer = Image.new("RGBA", final_image.size, (0, 0, 0, 0))
    align_pattern_draw = ImageDraw.Draw(align_pattern_layer)
    align_sizes_sq = [5.0 * module_size, 3.0 * module_size, 1.0 * module_size]
    align_radii_circ = [2.5 * module_size, 1.5 * module_size, 0.5 * module_size]
    pattern_colors = [outer_color, inner_color, innermost_color]
    pattern_corner_radius_px = module_size * ROUNDED_RADIUS_FACTOR
    shape_to_draw = pattern_shape if pattern_shape in ["circle", "square", "rounded_square"] else "square"

    for center_r, center_c in alignment_centers:
        center_x_px = (center_c + border_modules + 0.5) * module_size
        center_y_px = (center_r + border_modules + 0.5) * module_size
        if shape_to_draw == "circle":
            for layer_idx, radius_px in enumerate(align_radii_circ):
                _draw_single_shape_circle(align_pattern_draw, center_x_px, center_y_px, radius_px, pattern_colors[layer_idx])
        elif shape_to_draw == "square":
            for layer_idx, size_px in enumerate(align_sizes_sq):
                _draw_single_shape_square(align_pattern_draw, center_x_px, center_y_px, size_px, pattern_colors[layer_idx])
        elif shape_to_draw == "rounded_square":
            for layer_idx, size_px in enumerate(align_sizes_sq):
                _draw_single_shape_rounded_square(align_pattern_draw, center_x_px, center_y_px, size_px, pattern_corner_radius_px, pattern_colors[layer_idx])

    if final_image.mode != "RGBA":
        final_image = final_image.convert("RGBA")
    final_image.alpha_composite(align_pattern_layer)
    del align_pattern_draw, align_pattern_layer

def create_qr_code(
    data,
    bg_image_path,
    output_path,
    background_image_mode=DEFAULT_BACKGROUND_IMAGE_MODE,
    finder_shape=DEFAULT_FINDER_PATTERN_SHAPE,
    finder_color_mode=DEFAULT_FINDER_COLOR_MODE,
    finder_dynamic_submode=DEFAULT_FINDER_DYNAMIC_SUBMODE,
    reduce_innermost_brightness=REDUCE_INNERMOST_BRIGHTNESS,
    print_lock=None,
    data_module_shape=DATA_MODULE_SHAPE,
    data_module_color_mode=DATA_MODULE_COLOR_MODE,
    box_size=DEFAULT_BOX_SIZE,
    border=DEFAULT_BORDER,
    padding=DEFAULT_PADDING,
    diamond_border_width=DEFAULT_DIAMOND_BORDER_WIDTH,
    error_correction=DEFAULT_ERROR_CORRECTION,
    dark_module_color=DEFAULT_DARK_MODULE_COLOR,
    light_module_color=DEFAULT_LIGHT_MODULE_COLOR,
    background_alpha=DEFAULT_BACKGROUND_ALPHA,
    background_padding=BACKGROUND_PADDING_PX,
    enable_finder_overlay=ENABLE_FINDER_OVERLAY,
    finder_overlay_padding=FINDER_OVERLAY_PADDING_PX,
    finder_overlay_color=FINDER_OVERLAY_COLOR,
):
    if padding < 0:
        raise ValueError("Padding cannot be negative.")
    if data_module_shape == "diamond":
        if diamond_border_width < 0:
            raise ValueError("Diamond border width cannot be negative.")
        if (padding + diamond_border_width) * 2 > box_size:
            raise ValueError(f"Padding+Border too large for box_size.")
    elif (padding * 2) > box_size:
        raise ValueError(f"Padding too large for box_size.")
    if not (0 <= background_alpha <= 255):
        raise ValueError("background_alpha must be 0-255.")

    qr = qrcode.QRCode(version=None, error_correction=error_correction, box_size=box_size, border=border)
    qr.add_data(data)
    qr.make(fit=True)
    qr_matrix = qr.modules
    matrix_size = qr.modules_count
    final_border_size_modules = qr.border
    qr_version = qr.version
    alignment_centers = get_alignment_pattern_centers(qr_version)
    main_size_px = (matrix_size + 2 * final_border_size_modules) * box_size

    bg_img = None
    bg_img_orig = None
    try:
        is_svg = bg_image_path.lower().endswith(".svg")
        if is_svg and SVG_SUPPORT:
            png_data = cairosvg.svg2png(url=bg_image_path)
            bg_img_orig = Image.open(io.BytesIO(png_data))
        elif is_svg and not SVG_SUPPORT:
            raise ValueError("SVG file provided but SVG support disabled.")
        else:
            bg_img_orig = Image.open(bg_image_path)
        bg_img = bg_img_orig.convert("RGBA")
    except (FileNotFoundError, UnidentifiedImageError, ValueError) as e:
        raise e
    except Exception as e:
        raise IOError(f"Unexpected error loading background image '{os.path.basename(bg_image_path)}': {e}")
    finally:
        if bg_img_orig:
            try:
                bg_img_orig.close()
            except Exception:
                pass
    if bg_img is None:
        raise ValueError("Background image could not be loaded or converted.")

    dominant_colors = get_dominant_colors(bg_img.copy(), num_colors_to_quantize=10)
    background_canvas = Image.new("RGBA", (main_size_px, main_size_px), (255, 255, 255, 255))
    padded_width = max(0, main_size_px - 2 * background_padding)
    padded_height = max(0, main_size_px - 2 * background_padding)
    pad_offset_x, pad_offset_y = background_padding, background_padding

    if padded_width > 0 and padded_height > 0 and bg_img:
        try:
            if background_image_mode == "Stretched":
                bg_layer_resized = bg_img.resize((padded_width, padded_height), Image.Resampling.LANCZOS)
                background_canvas.paste(bg_layer_resized, (pad_offset_x, pad_offset_y), bg_layer_resized)
                del bg_layer_resized
            elif background_image_mode == "Contained":
                target_contained_box_width = padded_width * math.sqrt(0.40)
                target_contained_box_height = padded_height * math.sqrt(0.40)
                bg_img_thumb = bg_img.copy()
                img_ratio = bg_img_thumb.width / bg_img_thumb.height
                if target_contained_box_width <= 0 or target_contained_box_height <= 0:
                    resize_width, resize_height = 1, 1
                else:
                    target_box_ratio = target_contained_box_width / target_contained_box_height
                    if img_ratio > target_box_ratio:
                        resize_width = target_contained_box_width
                        resize_height = round(resize_width / img_ratio) if img_ratio != 0 else target_contained_box_height
                    else:
                        resize_height = target_contained_box_height
                        resize_width = round(resize_height * img_ratio)
                resize_width = max(1, int(resize_width))
                resize_height = max(1, int(resize_height))
                bg_img_thumb = bg_img_thumb.resize((resize_width, resize_height), Image.Resampling.LANCZOS)
                if bg_img_thumb.mode != "RGBA":
                    bg_img_thumb = bg_img_thumb.convert("RGBA")
                paste_x = pad_offset_x + (padded_width - resize_width) // 2
                paste_y = pad_offset_y + (padded_height - resize_height) // 2
                background_canvas.paste(bg_img_thumb, (paste_x, paste_y), bg_img_thumb)
                del bg_img_thumb
        except Exception as bg_err:
            raise ValueError(f"Error applying background image ({background_image_mode}): {bg_err}")

    if background_alpha < 255:
        try:
            alpha_layer = Image.new("RGBA", background_canvas.size, (255, 255, 255, background_alpha))
            temp_canvas = Image.alpha_composite(Image.new("RGBA", background_canvas.size, (255, 255, 255, 255)), background_canvas)
            background_canvas = Image.alpha_composite(temp_canvas, alpha_layer)
            del alpha_layer, temp_canvas
        except Exception as alpha_err:
            raise ValueError(f"Error applying global background alpha: {alpha_err}")

    final_image = Image.new("RGBA", (main_size_px, main_size_px), (0, 0, 0, 0))
    final_image.alpha_composite(background_canvas)
    del background_canvas

    data_module_layer = Image.new("RGBA", final_image.size, (0, 0, 0, 0))
    draw_data = ImageDraw.Draw(data_module_layer)

    for r in range(matrix_size):
        for c in range(matrix_size):
            if is_finder_pattern_module(r, c, matrix_size):
                continue
            if is_alignment_pattern_module(r, c, alignment_centers):
                continue
            is_dark = qr_matrix[r][c]
            fill_color, border_color = None, None

            if data_module_color_mode == "adaptive":
                center_x = (c + final_border_size_modules + 0.5) * box_size
                center_y = (r + final_border_size_modules + 0.5) * box_size
                local_prominent_rgb = get_prominent_color_in_region(final_image, center_x, center_y, ADAPTIVE_COLOR_RADIUS)
                if not (isinstance(local_prominent_rgb, tuple) and len(local_prominent_rgb) == 3):
                    local_prominent_rgb = (128, 128, 128)
                try:
                    h, s, l = calculate_hsl_from_rgb(*local_prominent_rgb)
                except Exception:
                    l = 120
                r_loc, g_loc, b_loc = local_prominent_rgb
                final_module_rgb = None
                if is_dark:
                    if (r_loc >= ADAPTIVE_NEAR_WHITE_THRESHOLD and g_loc >= ADAPTIVE_NEAR_WHITE_THRESHOLD and b_loc >= ADAPTIVE_NEAR_WHITE_THRESHOLD):
                        final_module_rgb = get_contrasting_color(dominant_colors, "dark", ADAPTIVE_LUMINANCE_THRESHOLD, dark_module_color, light_module_color)
                    elif l >= ADAPTIVE_LUMINANCE_THRESHOLD:
                        final_module_rgb = reduce_rgb_brightness(local_prominent_rgb, ADAPTIVE_DARKEN_FACTOR)
                    else:
                        final_module_rgb = local_prominent_rgb
                else:
                    if (r_loc <= ADAPTIVE_NEAR_BLACK_THRESHOLD and g_loc <= ADAPTIVE_NEAR_BLACK_THRESHOLD and b_loc <= ADAPTIVE_NEAR_BLACK_THRESHOLD):
                        final_module_rgb = get_contrasting_color(dominant_colors, "light", ADAPTIVE_LUMINANCE_THRESHOLD, dark_module_color, light_module_color)
                    elif l < ADAPTIVE_LUMINANCE_THRESHOLD:
                        final_module_rgb = increase_rgb_brightness(local_prominent_rgb, ADAPTIVE_LIGHTEN_FACTOR)
                    else:
                        final_module_rgb = local_prominent_rgb
                if not (isinstance(final_module_rgb, tuple) and len(final_module_rgb) == 3):
                    final_module_rgb = dark_module_color[:3] if is_dark else light_module_color[:3]
                alpha_comp = dark_module_color[3] if is_dark else light_module_color[3]
                fill_color = final_module_rgb + (alpha_comp,)
                border_color = light_module_color if is_dark else dark_module_color
            else:
                fill_color = dark_module_color if is_dark else light_module_color
                border_color = light_module_color if is_dark else dark_module_color

            x_box_start = (c + final_border_size_modules) * box_size
            y_box_start = (r + final_border_size_modules) * box_size
            x_box_end = x_box_start + box_size
            y_box_end = y_box_start + box_size
            center_x_draw = x_box_start + box_size / 2.0
            center_y_draw = y_box_start + box_size / 2.0
            inner_padding = padding

            try:
                if data_module_shape == "diamond":
                    half_outer_edge = (box_size / 2.0) - padding
                    half_inner_edge = half_outer_edge - diamond_border_width
                    if half_outer_edge < 0:
                        continue
                    if diamond_border_width > 0 and border_color is not None:
                        vertices_border = [
                            (center_x_draw, y_box_start + padding),
                            (x_box_end - padding, center_y_draw),
                            (center_x_draw, y_box_end - padding),
                            (x_box_start + padding, center_y_draw),
                        ]
                        if all(coord >= 0 for v in vertices_border for coord in v) and (x_box_end - padding > x_box_start + padding):
                            draw_data.polygon(vertices_border, fill=border_color)
                    if half_inner_edge >= 0:
                        inner_pad_diamond = padding + diamond_border_width
                        vertices_fill = [
                            (center_x_draw, y_box_start + inner_pad_diamond),
                            (x_box_end - inner_pad_diamond, center_y_draw),
                            (center_x_draw, y_box_end - inner_pad_diamond),
                            (x_box_start + inner_pad_diamond, center_y_draw),
                        ]
                        if all(coord >= 0 for v in vertices_fill for coord in v) and (x_box_end - inner_pad_diamond > x_box_start + inner_pad_diamond):
                            draw_data.polygon(vertices_fill, fill=fill_color)
                elif data_module_shape == "square":
                    sq_x0, sq_y0 = x_box_start + inner_padding, y_box_start + inner_padding
                    sq_x1, sq_y1 = x_box_end - inner_padding, y_box_end - inner_padding
                    if sq_x1 > sq_x0 and sq_y1 > sq_y0:
                        draw_data.rectangle([(sq_x0, sq_y0), (sq_x1, sq_y1)], fill=fill_color)
                elif data_module_shape == "circle":
                    circ_x0, circ_y0 = x_box_start + inner_padding, y_box_start + inner_padding
                    circ_x1, circ_y1 = x_box_end - inner_padding, y_box_end - inner_padding
                    if circ_x1 > circ_x0 and circ_y1 > circ_y0:
                        draw_data.ellipse([(circ_x0, circ_y0), (circ_x1, circ_y1)], fill=fill_color)
            except Exception as draw_err:
                if print_lock:
                    with print_lock:
                        print(f"Warning: Error drawing data module at ({r},{c}) for {os.path.basename(output_path)}: {draw_err}", file=sys.stderr)

    final_image.alpha_composite(data_module_layer)
    del draw_data, data_module_layer

    outer_pcolor, inner_pcolor_list, innermost_pcolor_list = determine_finder_colors(dominant_colors, finder_color_mode, finder_dynamic_submode, reduce_innermost_brightness)

    draw_finder_patterns(final_image, matrix_size, box_size, final_border_size_modules, finder_shape, outer_pcolor, inner_pcolor_list, innermost_pcolor_list, enable_finder_overlay, finder_overlay_padding, finder_overlay_color)

    inner_align_color = inner_pcolor_list[0] if inner_pcolor_list else (255, 255, 255, 225)
    innermost_align_color = innermost_pcolor_list[0] if innermost_pcolor_list else (0, 0, 0, 225)
    draw_alignment_patterns(final_image, alignment_centers, box_size, final_border_size_modules, finder_shape, outer_pcolor, inner_align_color, innermost_align_color)

    try:
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        if final_image.mode != "RGBA":
            final_image = final_image.convert("RGBA")
        final_image.save(output_path, "PNG")
    except Exception as e:
        raise IOError(f"Error saving final image '{os.path.basename(output_path)}': {e}")
    finally:
        if final_image:
            try:
                final_image.close()
            except Exception:
                pass
        if bg_img:
            try:
                bg_img.close()
            except Exception:
                pass

# Error correction mapping for the API
ERROR_CORRECTION_MAP = {
    "L": qrcode.constants.ERROR_CORRECT_L,
    "M": qrcode.constants.ERROR_CORRECT_M,
    "Q": qrcode.constants.ERROR_CORRECT_Q,
    "H": qrcode.constants.ERROR_CORRECT_H,
}

def generate_qr_code_api(data: str, bg_image_path: str, output_path: str, **kwargs) -> bool:
    """API wrapper for the create_qr_code function"""
    try:
        # Convert error correction string to constant
        error_correction = kwargs.get('error_correction', 'H')
        if isinstance(error_correction, str):
            kwargs['error_correction'] = ERROR_CORRECTION_MAP.get(error_correction, qrcode.constants.ERROR_CORRECT_H)
        
        # Remove parameters that are not part of create_qr_code function
        # These are handled internally or not needed
        kwargs.pop('innermost_brightness_reduction', None)
        
        # Create a dummy print lock for single threaded operation
        print_lock = threading.Lock()
        
        # Call the create_qr_code function
        create_qr_code(
            data=data,
            bg_image_path=bg_image_path,
            output_path=output_path,
            print_lock=print_lock,
            **kwargs
        )
        
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return False