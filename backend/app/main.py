from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os

from .api.endpoints import router as api_router

app = FastAPI(title="QR Code Generator", description="Dynamic QR Code Generator with Background Images")

# Mount static files
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend", "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Templates
template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend", "templates")
templates = Jinja2Templates(directory=template_path) if os.path.exists(template_path) else None

# Include API routes
app.include_router(api_router, prefix="/api")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main application page"""
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    else:
        return HTMLResponse("""
        <html>
            <head>
                <title>QR Code Generator</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                    .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                    .upload-area { border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 20px 0; cursor: pointer; }
                    .form-group { margin: 15px 0; }
                    label { display: block; margin-bottom: 5px; font-weight: bold; }
                    input, select { width: 100%; padding: 8px; margin-top: 5px; border: 1px solid #ddd; border-radius: 4px; }
                    button { background: #007bff; color: white; padding: 12px 24px; border: none; cursor: pointer; border-radius: 4px; }
                    .preview { margin: 20px 0; text-align: center; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🎨 QR Code Generator</h1>
                    <div class="upload-area" onclick="document.getElementById('imageUpload').click()">
                        <input type="file" id="imageUpload" accept="image/*" style="display: none;">
                        <p>📷 Click to upload background image</p>
                    </div>
                    <div class="form-group">
                        <label>QR Code Data:</label>
                        <input type="text" id="qrData" value="https://www.example.com">
                    </div>
                    <button onclick="generateQR()">Generate QR Code</button>
                    <div class="preview" id="preview"></div>
                </div>
                <script>
                    let currentFilename = null;
                    document.getElementById('imageUpload').addEventListener('change', uploadImage);
                    
                    async function uploadImage(event) {
                        const file = event.target.files[0];
                        if (!file) return;
                        const formData = new FormData();
                        formData.append('file', file);
                        try {
                            const response = await fetch('/api/upload', { method: 'POST', body: formData });
                            const result = await response.json();
                            if (result.success) {
                                currentFilename = result.filename;
                                alert('Image uploaded successfully!');
                            } else {
                                alert('Upload failed: ' + result.message);
                            }
                        } catch (error) {
                            alert('Upload error: ' + error.message);
                        }
                    }
                    
                    async function generateQR() {
                        if (!currentFilename) {
                            alert('Please upload an image first!');
                            return;
                        }
                        const formData = new FormData();
                        formData.append('filename', currentFilename);
                        formData.append('data', document.getElementById('qrData').value);
                        try {
                            const response = await fetch('/api/generate', { method: 'POST', body: formData });
                            const result = await response.json();
                            if (result.success) {
                                document.getElementById('preview').innerHTML = 
                                    '<h3>Generated QR Code:</h3><img src="/api/download/' + result.filename + '" style="max-width: 400px;"><br><br><a href="/api/download/' + result.filename + '" download><button>Download QR Code</button></a>';
                            } else {
                                alert('Generation failed: ' + result.message);
                            }
                        } catch (error) {
                            alert('Generation error: ' + error.message);
                        }
                    }
                </script>
            </body>
        </html>
        """)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "QR Code Generator API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)