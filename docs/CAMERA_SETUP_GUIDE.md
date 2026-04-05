# 🎥 **CAMERA SETUP GUIDE - ALL CAMERA TYPES**

## 🚀 **Quick Setup**

### **1. Install Dependencies**
```bash
# Core dependencies
pip install -r requirements.txt

# For Ring cameras (optional)
pip install ring-doorbell

# For USB webcams (already included)
pip install opencv-python
```

### **2. Configure Cameras**
```bash
# Copy example config
cp config.example.yaml config.yaml

# Edit with your camera details
# Windows: notepad config.yaml
# Linux/Mac: nano config.yaml
```

### **3. Start Dashboard & Servers**
```bash
# Start everything (Dashboard, USB Camera Server, MCP)
./start.ps1  # Windows
./start.sh   # Linux/Mac

# Access Dashboard at: http://localhost:7777
# USB Camera Server at: http://localhost:10705
```

## 📷 **Camera Configuration Examples**

### **USB Webcam (Easiest to Test)**
```yaml
cameras:
  webcam:
    type: webcam
    device_id: 0  # Usually 0 for first webcam
    resolution: "1920x1080"
    fps: 30
```

### **Tapo Camera**
```yaml
cameras:
  living_room:
    type: tapo
    host: 192.168.1.100
    username: "your_tapo_username"
    password: "your_tapo_password"
    port: 443
    verify_ssl: true
```

### **Ring Doorbell Camera**
```yaml
cameras:
  front_door:
    type: ring
    params:
      username: "your_ring_email@example.com"
      password: "your_ring_password"
      # Alternative: use token
      # token: "your_ring_token"
      device_id: "optional_device_id"
```

### **Furbo Pet Camera**
```yaml
cameras:
  pet_cam:
    type: furbo
    params:
      email: "your_furbo_email@example.com"
      password: "your_furbo_password"
      device_id: "optional_device_id"
      # For RTSP streaming:
      host: "192.168.1.xxx"
      username: "furbo_username"
      password: "furbo_password"
```

## 🔧 **Camera-Specific Setup**

### **USB Webcam Setup**
1. **Connect webcam** to your computer
2. **Test webcam**: `python start.py test`
3. **Check device ID**: Usually 0, try 1, 2, etc. if needed
4. **Start dashboard**: `python start.py dashboard`

### **Tapo Camera Setup**
1. **Find camera IP**: Check your router or use Tapo app
2. **Get credentials**: Username/password from Tapo app
3. **Test connection**: Use Tapo app to verify camera works
4. **Add to config**: Update config.yaml with your details

### **Ring Doorbell Setup**
1. **Install Ring app**: Set up your Ring doorbell
2. **Get credentials**: Email/password from Ring account
3. **Install dependency**: `pip install ring-doorbell`
4. **Add to config**: Update config.yaml with Ring details

### **Furbo Pet Camera Setup**
1. **Set up Furbo**: Use Furbo app to configure camera
2. **Get credentials**: Email/password from Furbo account
3. **Find IP address**: Check router or Furbo app
4. **Add to config**: Update config.yaml with Furbo details

## 🎯 **Testing Your Setup**

### **Test Individual Cameras**
```bash
# Test webcam
python start.py test

# Test all cameras
python -c "
import asyncio
from devices_mcp.core.server import TapoCameraServer
async def test():
    server = await TapoCameraServer.get_instance()
    cameras = await server.list_cameras()
    print(f'Found {cameras[\"total\"]} cameras')
asyncio.run(test())
"
```

### **Start Dashboard**
```bash
# Start web dashboard
python start.py dashboard

# Check dashboard
# Open browser to: http://localhost:7777
```

## 🎥 **What You'll See**

### **Servers**
- ✅ **Web Dashboard**: `localhost:7777`
- ✅ **USB Camera Server**: `localhost:10705` (Auto-started by `start.ps1`)

### **Dashboard Features**
- ✅ **Real-time video streams** from USB webcams
- ✅ **Live camera status** with actual health data
- ✅ **Stream controls** to start/stop video
- ✅ **Camera management** with add/remove functionality
- ✅ **Responsive design** for mobile and desktop

### **Camera Types Supported**
- ✅ **USB Webcams**: MJPEG streaming at 30 FPS
- ✅ **Tapo Cameras**: RTSP stream integration
- ✅ **Ring Doorbells**: Real snapshot and stream URLs
- ✅ **Furbo Pet Cameras**: API integration + RTSP

## 🚨 **Troubleshooting**

### **Common Issues**

#### **Webcam Not Working**
- Check if webcam is connected
- Try different device_id (0, 1, 2, etc.)
- Install opencv-python: `pip install opencv-python`

#### **Tapo Camera Connection Failed**
- Verify IP address and credentials
- Check if camera is online
- Try disabling SSL verification: `verify_ssl: false`

#### **Ring Camera Authentication Failed**
- Install ring-doorbell: `pip install ring-doorbell`
- Verify email/password in Ring app
- Check if 2FA is enabled (may need token)

#### **Furbo Camera Not Found**
- Verify email/password in Furbo app
- Check if camera is online
- Try without device_id (uses first device)

### **Debug Mode**
```bash
# Start with debug logging
python start.py dashboard --debug

# Check logs
tail -f tapo_mcp.log
```

## 🎉 **Success!**

Once configured, you'll have:
- **Real-time video streaming** from all camera types
- **Unified camera management** through web dashboard
- **Live status monitoring** with actual camera data
- **No more mocks** - everything is real!

**Dashboard URL**: `http://localhost:7777` 🎥✨
