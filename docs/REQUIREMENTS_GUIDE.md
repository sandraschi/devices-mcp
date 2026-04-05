# 📦 **REQUIREMENTS GUIDE - ALL DEPENDENCIES**

## 🚀 **Quick Installation**

### **Complete Installation (Recommended)**
```bash
# Install all dependencies including AI/vision features
pip install -r requirements.txt
```

### **Minimal Installation**
```bash
# Install only core camera functionality
pip install -r requirements-minimal.txt
```

### **Camera-Specific Installation**
```bash
# Core dependencies
pip install -r requirements-core.txt

# Web dashboard
pip install -r requirements-web.txt

# Vision/AI features (optional)
pip install -r requirements-vision.txt
```

## 📋 **Dependency Categories**

### **Core MCP Dependencies** (`requirements-core.txt`)
- **`fastmcp`**: MCP protocol implementation
- **`pytapo`**: Tapo camera control
- **`pydantic`**: Data validation
- **`python-dotenv`**: Environment variables
- **`aiohttp`**: Async HTTP client/server
- **`Pillow`**: Image processing
- **`numpy`**: Numerical operations

### **Camera-Specific Dependencies**
- **`opencv-python`**: USB webcam support
- **`ring-doorbell`**: Ring doorbell integration
- **`oauthlib`**: OAuth authentication
- **`requests-oauthlib`**: OAuth requests

### **Web Dashboard Dependencies** (`requirements-web.txt`)
- **`fastapi`**: Modern web framework
- **`uvicorn`**: ASGI server
- **`jinja2`**: Template engine
- **`python-multipart`**: File uploads
- **`aiofiles`**: Async file operations
- **`python-jose`**: JWT tokens
- **`passlib`**: Password hashing
- **`httpx`**: HTTP client
- **`starlette`**: Web framework components

### **Vision/AI Dependencies** (`requirements-vision.txt`)
- **`torch`**: PyTorch deep learning
- **`torchvision`**: Computer vision
- **`timm`**: Image models
- **`huggingface-hub`**: Model downloads
- **`matplotlib`**: Plotting
- **`scikit-learn`**: Machine learning
- **`transformers`**: NLP models

### **Development Dependencies**
- **`pytest`**: Testing framework
- **`pytest-asyncio`**: Async testing
- **`pytest-mock`**: Mocking
- **`black`**: Code formatting
- **`isort`**: Import sorting
- **`mypy`**: Type checking
- **`pylint`**: Code linting
- **`pytest-cov`**: Coverage
- **`codecov`**: Coverage reporting

## 🎯 **Installation by Camera Type**

### **USB Webcam Only**
```bash
pip install opencv-python fastapi uvicorn
```

### **Tapo Cameras Only**
```bash
pip install pytapo fastmcp pydantic
```

### **Ring Doorbell Only**
```bash
pip install ring-doorbell oauthlib requests-oauthlib
```

### **Furbo Pet Camera Only**
```bash
# Uses built-in API client, no additional dependencies
pip install aiohttp
```

### **All Camera Types**
```bash
pip install -r requirements.txt
```

## 🔧 **Version Compatibility**

### **Python Version**
- **Minimum**: Python 3.8
- **Recommended**: Python 3.11+
- **Tested**: Python 3.8, 3.9, 3.10, 3.11, 3.12

### **Operating Systems**
- **Windows**: ✅ Fully supported
- **macOS**: ✅ Fully supported
- **Linux**: ✅ Fully supported

### **Dependency Versions**
- **FastMCP**: 2.12.0+ (required for tool registration)
- **PyTapo**: 3.3.48+ (latest Tapo API support)
- **OpenCV**: 4.8.0+ (webcam support)
- **FastAPI**: 0.100.0+ (modern web features)

## 🚨 **Troubleshooting**

### **Common Installation Issues**

#### **OpenCV Installation Failed**
```bash
# Try alternative installation
pip install opencv-python-headless
# OR
conda install opencv
```

#### **PyTorch Installation Failed**
```bash
# Install CPU-only version
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

#### **Ring Doorbell Installation Failed**
```bash
# Install from source if needed
pip install git+https://github.com/tchellomello/python-ring-doorbell.git
```

#### **Permission Errors**
```bash
# Use user installation
pip install --user -r requirements.txt
```

### **Platform-Specific Issues**

#### **Windows**
- Install Visual C++ Build Tools
- Use conda instead of pip for problematic packages

#### **macOS**
- Install Xcode command line tools
- Use Homebrew for system dependencies

#### **Linux**
- Install system packages: `sudo apt-get install python3-dev libffi-dev`
- Use virtual environment: `python -m venv venv && source venv/bin/activate`

## ✅ **Verification**

### **Check Installation**
```bash
# Test core dependencies
python -c "import fastmcp, pytapo, cv2, fastapi; print('✅ All core dependencies installed')"

# Test camera dependencies
python -c "import ring_doorbell, oauthlib; print('✅ Camera dependencies installed')"

# Test web dependencies
python -c "import uvicorn, jinja2; print('✅ Web dependencies installed')"
```

### **Test Camera Support**
```bash
# Test webcam
python -c "import cv2; cap = cv2.VideoCapture(0); print('✅ Webcam support working')"

# Test Tapo
python -c "import pytapo; print('✅ Tapo support working')"

# Test Ring
python -c "import ring_doorbell; print('✅ Ring support working')"
```

## 🎉 **Success!**

Once installed, you'll have:
- ✅ **All camera types** supported
- ✅ **Web dashboard** with video streaming
- ✅ **MCP integration** for Claude Desktop
- ✅ **Real-time video** from USB webcams
- ✅ **Complete camera management** system

**Ready to start**: `python start.py dashboard` 🎥✨
