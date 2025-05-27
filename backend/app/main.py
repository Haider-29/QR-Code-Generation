from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os

from .api.endpoints import router as api_router

app = FastAPI(title="QR Code Generator", description="Dynamic QR Code Generator with Background Images")

# Mount static files - Fixed paths
static_path = "/app/frontend/static"
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Templates - Fixed paths
template_path = "/app/frontend/templates"
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
            <head><title>Fallback QR Generator</title></head>
            <body><h1>Template not found - using fallback</h1></body>
        </html>
        """)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "QR Code Generator API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)