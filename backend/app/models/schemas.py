from pydantic import BaseModel
from typing import Optional, List

class QRGenerationRequest(BaseModel):
    filename: str
    data: str = "https://www.example.com"
    background_image_mode: str = "Stretched"
    finder_shape: str = "rounded_square"
    finder_color_mode: str = "dynamic"
    finder_dynamic_submode: str = "single-color"
    data_module_shape: str = "diamond"
    data_module_color_mode: str = "adaptive"
    box_size: int = 25
    border: int = 4
    padding: int = 4
    diamond_border_width: int = 0
    error_correction: str = "H"
    background_alpha: int = 255
    background_padding: int = 60
    enable_finder_overlay: bool = True
    finder_overlay_padding: int = 15
    reduce_innermost_brightness: bool = True
    innermost_brightness_reduction: float = 0.25

class QRGenerationResponse(BaseModel):
    success: bool
    filename: str
    message: str
    output_path: Optional[str] = None

class ImageUploadResponse(BaseModel):
    success: bool
    filename: str
    message: str

class ImageListResponse(BaseModel):
    images: List[str]