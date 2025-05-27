# 🎨 Dynamic QR Code Generator

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://hub.docker.com/r/salman2002ahmad/qr-generator)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A professional, full-stack web application for creating beautiful, customizable QR codes with background images and real-time parameter tuning. Built with FastAPI backend and modern frontend technologies.

## 🚀 Quick Start

### Using Docker (Recommended)
```bash
docker pull salman2002ahmad/qr-generator:latest
docker run -d -p 8000:8000 salman2002ahmad/qr-generator:latest
Then open http://localhost:8000 in your browser.
```

## Recommended (With Persistent Storage)
```bash
mkdir -p qr-uploads qr-outputs

docker run -d \
  --name qr-generator \
  -p 8000:8000 \
  -v $(pwd)/qr-uploads:/app/uploads \
  -v $(pwd)/qr-outputs:/app/outputs \
  --restart unless-stopped \
  salman2002ahmad/qr-generator:latest

Access at: http://localhost:8000
```

## Using Docker Compose
```bash
version: '3.8'
services:
  qr-generator:
    image: salman2002ahmad/qr-generator:latest
    container_name: qr-generator
    ports:
      - "8000:8000"
    volumes:
      - ./uploads:/app/uploads
      - ./outputs:/app/outputs
    restart: unless-stopped
```

Then Run :
```bash
docker-compose up -d
```



### Local Development
```bash
git clone https://github.com/Haider-29/QR-Code-Generation
cd qr-generator-app
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
```


## ✨ Features

- 🖼️ **Background Image Integration**: Upload PNG, JPG, SVG, and more
- ⚡ **Real-time Generation**: See instant QR previews as you change parameters
- 📱 **Responsive Design**: Works flawlessly across desktop, tablet, and mobile
- 🎨 **Advanced Customization**: Modify QR styling, colors, and layout
- 📥 **High-Quality Downloads**: Export as high-res PNGs
- 🔄 **Drag & Drop Interface**: Effortless image uploads

---
