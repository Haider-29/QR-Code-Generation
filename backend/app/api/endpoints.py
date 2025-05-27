from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
import os
import uuid
import shutil
from typing import List

from ..models.schemas import (
    QRGenerationRequest, 
    QRGenerationResponse, 
    ImageUploadResponse,
    ImageListResponse
)
from ..core.qr_generator import generate_qr_code_api

router = APIRouter()

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"

# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

@router.post("/upload", response_model=ImageUploadResponse)
async def upload_image(file: UploadFile = File(...)):
    """Upload a background image"""
    try:
        # Validate file type
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp', '.svg'}
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return ImageUploadResponse(
            success=True,
            filename=unique_filename,
            message="Image uploaded successfully"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/generate", response_model=QRGenerationResponse)
async def generate_qr_code(
    filename: str = Form(...),
    data: str = Form("https://www.example.com"),
    background_image_mode: str = Form("Stretched"),
    finder_shape: str = Form("rounded_square"),
    finder_color_mode: str = Form("dynamic"),
    finder_dynamic_submode: str = Form("single-color"),
    data_module_shape: str = Form("diamond"),
    data_module_color_mode: str = Form("adaptive"),
    box_size: int = Form(25),
    border: int = Form(4),
    padding: int = Form(4),
    diamond_border_width: int = Form(0),
    error_correction: str = Form("H"),
    background_alpha: int = Form(255),
    background_padding: int = Form(60),
    enable_finder_overlay: bool = Form(True),
    finder_overlay_padding: int = Form(15),
    reduce_innermost_brightness: bool = Form(True)
):
    """Generate QR code with specified parameters"""
    try:
        # Check if uploaded file exists
        input_path = os.path.join(UPLOAD_DIR, filename)
        if not os.path.exists(input_path):
            raise HTTPException(status_code=404, detail="Background image not found")
        
        # Generate output filename
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}_qr_{uuid.uuid4()}.png"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        # Prepare parameters - only include what the core function expects
        params = {
            'background_image_mode': background_image_mode,
            'finder_shape': finder_shape,
            'finder_color_mode': finder_color_mode,
            'finder_dynamic_submode': finder_dynamic_submode,
            'reduce_innermost_brightness': reduce_innermost_brightness,
            'data_module_shape': data_module_shape,
            'data_module_color_mode': data_module_color_mode,
            'box_size': box_size,
            'border': border,
            'padding': padding,
            'diamond_border_width': diamond_border_width,
            'error_correction': error_correction,
            'background_alpha': background_alpha,
            'background_padding': background_padding,
            'enable_finder_overlay': enable_finder_overlay,
            'finder_overlay_padding': finder_overlay_padding
        }
        
        # Generate QR code
        success = generate_qr_code_api(
            data=data,
            bg_image_path=input_path,
            output_path=output_path,
            **params
        )
        
        if success:
            return QRGenerationResponse(
                success=True,
                filename=output_filename,
                message="QR code generated successfully",
                output_path=output_filename
            )
        else:
            raise HTTPException(status_code=500, detail="QR code generation failed")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@router.get("/download/{filename}")
async def download_qr_code(filename: str):
    """Download generated QR code"""
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path,
        media_type="image/png",
        filename=filename
    )

@router.get("/images", response_model=ImageListResponse)
async def list_images():
    """List all uploaded images"""
    try:
        images = []
        if os.path.exists(UPLOAD_DIR):
            images = [f for f in os.listdir(UPLOAD_DIR) if os.path.isfile(os.path.join(UPLOAD_DIR, f))]
        return ImageListResponse(images=images)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list images: {str(e)}")

@router.get("/preview/{filename}")
async def preview_image(filename: str):
    """Preview uploaded image"""
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Determine media type based on extension
    extension = os.path.splitext(filename)[1].lower()
    media_type_map = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.bmp': 'image/bmp',
        '.gif': 'image/gif',
        '.tiff': 'image/tiff',
        '.webp': 'image/webp',
        '.svg': 'image/svg+xml'
    }
    
    media_type = media_type_map.get(extension, 'image/png')
    
    return FileResponse(file_path, media_type=media_type)