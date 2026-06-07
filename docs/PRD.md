# 🏠 Home Security Dashboard MCP - Product Requirements Document (PRD)

## 📋 **PRODUCT OVERVIEW** (Updated October 2025)

### **Product Name**
Home Security Dashboard MCP - Dual Architecture Platform

### **Product Vision**
A production-ready security monitoring platform with dual MCP architecture: serving as both individual camera/sensor MCP servers AND a unified security dashboard that orchestrates multiple MCP servers for comprehensive home security monitoring.

### **Target Users**
- **🏠 Home Security Professionals**: Users with comprehensive security ecosystems (cameras + sensors)
- **🤖 AI Integration Developers**: Developers building MCP-based security systems
- **🏢 System Administrators**: IT professionals managing multi-vendor security networks
- **🔧 Home Automation Enthusiasts**: Users integrating multiple smart home systems
- **📱 Remote Monitoring Users**: Users needing mobile access via VPN (Tailscale)

### **🎯 DUAL ARCHITECTURE EXPLANATION**

**This platform serves two complementary roles:**

#### **🎥 Role 1: Individual MCP Servers**
- **Devices MCP**: Standalone TP-Link camera control
- **USB Webcam MCP**: Direct webcam management
- **Ring MCP**: Doorbell/camera security integration
- **Nest Protect MCP**: Smoke/CO detector monitoring
- **Each MCP server**: Can run independently for specific device control

#### **🏠 Role 2: Unified Security Dashboard**
- **Multi-MCP Orchestrator**: Coordinates multiple MCP servers
- **Unified Interface**: Single dashboard for all security devices
- **Cross-System Correlation**: Intelligent alert analysis across systems
- **Real-time Monitoring**: Live status from cameras + sensors + alarms

### **🏆 MAJOR ACHIEVEMENT - PRODUCTION READY!**
- **✅ Robotics Integration**: Dreame D20 Pro (Cloud) and Yahboom ROS 2 (Mock) (WORKING)
- **✅ Fleet Expansion**: Multi-camera Tapo support (Kitchen + Living Room) (WORKING)
- **✅ Windows USB Camera Server**: Integrated local USB camera server on port 10715 (WORKING)
- **✅ Live Web Dashboard**: Working at `localhost:7777`
- **✅ USB Webcam Support**: Auto-detection and monitoring (WORKING)
- **✅ Claude Desktop Integration**: MCP server loads successfully (WORKING)
- **✅ Repository Cleanup**: Massive 270+ linting cleanup across 160+ files (WORKING)
- **✅ Hardware Research**: Added BETAFPV Pavo35 and Insta360 X5 documentation (WORKING)

## 🎯 **CORE REQUIREMENTS - CURRENT STATUS**

### **1. Camera Support**
- **✅ Tapo Cameras**: Multi-camera support with ONVIF bypass (WORKING)
- **✅ USB Webcams**: Auto-detected and monitored (WORKING)
- **✅ Robotics**: Dreame D20 Pro and Yahboom ROS 2 (WORKING)
- **📋 Furbo Cameras**: Pet camera support (planned)

### **2. MCP Integration**
- **✅ FastMCP 3.1 Compliance**: Full protocol compatibility, sampling, skills, prompts (WORKING)
- **✅ Tool Discovery**: 52+ tools registered and working (WORKING)
- **✅ Skills provider**: Cursor/Codex skills directories exposed as MCP resources (WORKING)
- **✅ Prompts**: device_status, list_cameras registered for LLM use (WORKING)
- **✅ Claude Desktop Integration**: Server loads successfully (WORKING)
- **✅ Real-time Communication**: Live camera data through MCP (WORKING)

### **3. Web Dashboard**
- **🔄 Real-time Video Streaming**: Live MJPEG streams (next phase)
- **🔄 RTSP Integration**: Direct streaming from Tapo cameras (pending auth)
- **✅ Dynamic Camera Management**: Auto-add USB cameras (WORKING)
- **✅ Responsive Design**: Professional UI at localhost:7777 (WORKING)
- **✅ Real-time Status**: Live camera monitoring (WORKING)

## 🚀 **GETTING STARTED GUIDE** (UPDATED October 2025)

### **✅ WHAT WORKS NOW**

```bash
# 1. Start the Live Dashboard (RECOMMENDED)
python start.py dashboard
# Result: Professional dashboard at http://localhost:7777 with USB webcam monitoring

# 2. Check Claude Desktop Integration
# MCP server loads automatically - look for Tapo Camera tools in Claude
```

### **📊 CURRENT CAPABILITIES**
- **✅ USB Webcam Detection**: Auto-discovered and displayed
- **✅ Real-time Status Monitoring**: Camera health and connections
- **✅ Professional Dashboard UI**: Clean, responsive interface
- **✅ Claude Desktop Tools**: 52 MCP tools available
- **🔄 Tapo Camera Integration**: Needs correct password authentication

### **Prerequisites**
```bash
# Required Software (Already Working)
✅ Python 3.8+ (installed)
✅ OpenCV (for webcam support) (working)
✅ FastMCP 3.1 (working)
✅ USB webcam (auto-detected)
🔄 Tapo cameras (pending auth resolution)
```

### **Installation** (Already Done)
git clone https://github.com/yourusername/devices-mcp.git
cd devices-mcp

# 2. Install dependencies
pip install -e .
pip install -r requirements.txt

# 3. Configure cameras
cp config.example.yaml config.yaml
# Edit config.yaml with your camera details
```

### **Starting the System**

#### **Option 1: MCP Server Only (for Claude Desktop)**
```bash
# Start MCP server
python -m devices_mcp.server_v2 --direct

# With debug logging
python -m devices_mcp.server_v2 --direct --debug
```

#### **Option 2: Web Dashboard Only**
```bash
# Start web dashboard
python -m devices_mcp.web.server

# Dashboard available at: http://localhost:7777
```

#### **Option 3: Both Services (Recommended)**
```bash
# Terminal 1: Start MCP server
python -m devices_mcp.server_v2 --direct

# Terminal 2: Start web dashboard
python -m devices_mcp.web.server
```

### **Quick Test with USB Webcam**
```bash
# Test webcam functionality
python test_webcam_streaming.py

# Then start dashboard
python -m devices_mcp.web.server
```

## 📺 **VIDEO STREAMING FEATURES**

### **USB Webcam Streaming**
- **Format**: MJPEG (Motion JPEG)
- **Frame Rate**: 30 FPS
- **Quality**: Adjustable JPEG quality (80% default)
- **Latency**: ~100ms end-to-end
- **Browser Support**: All modern browsers

### **Tapo Camera Streaming**
- **Format**: RTSP streams
- **Integration**: Direct camera stream URLs
- **Multiple Formats**: HLS, RTSP, RTMP support
- **Authentication**: Secure credential handling

### **Dashboard Features**
- **Live View**: Real-time video display
- **Stream Controls**: Start/stop per camera
- **Camera Grid**: Multi-camera layout
- **Status Monitoring**: Online/offline indicators
- **Snapshot Capture**: Still image capture

## 🔧 **TECHNICAL SPECIFICATIONS**

### **Backend Architecture**
- **Framework**: FastAPI for web server
- **Async Processing**: asyncio for concurrent operations
- **Camera Abstraction**: Unified interface across camera types
- **Tool System**: Modular MCP tool architecture

### **Frontend Architecture**
- **Target stack (web-sota standard):** React + Vite + Tailwind CSS + shadcn/ui. See [Web SOTA Frontend Standards](standards/WEB_SOTA_FRONTEND_STANDARDS.md).
- **Current/legacy:** Jinja2 SSR + vanilla JS + custom CSS (to be migrated to the target stack).
- **Real-time updates:** Prefer React state + fetch/SSE/WebSocket; AJAX acceptable in legacy pages.

### **API Endpoints**
```
GET  /                           # Dashboard homepage
GET  /api/cameras               # List all cameras
GET  /api/cameras/{id}/stream   # Video stream
GET  /api/cameras/{id}/snapshot # Camera snapshot
GET  /api/status                # Server status
```

### **MCP Tools Available**
- **Camera Management**: 6 tools (list, add, connect, disconnect, info, status)
- **PTZ Controls**: 7 tools (move, position, presets, home, stop)
- **Media Operations**: 4 tools (capture, recording, status)
- **System Management**: 8 tools (info, reboot, logs, settings)

## 🔄 **STABILITY & RELIABILITY STANDARDS (v1.18.1)**

### **Zero Stdout Pollution**
- **CRITICAL**: No plain-text `print()` or `sys.stdout.write()` allowed in production code.
- **Protocol Integrity**: All JSON-RPC communication MUST be the only data on `stdout`.
- **Diagnostic Redirection**: All startup banners, progress bars, and debug logs MUST go to `stderr`.

### **Asyncio Context Safety**
- **Loop Management**: Use `@mcp.run()` or similar context managers that handle loop creation safely.
- **Thread Safety**: Ensure no conflicting event loops are started in the same thread.
- **Graceful Shutdown**: All async resources must be closed properly on exit.

## 📊 **PERFORMANCE REQUIREMENTS**

### **Video Streaming**
- **Frame Rate**: 30 FPS minimum
- **Latency**: <200ms end-to-end
- **Bandwidth**: 1-2 Mbps per stream
- **Concurrent Streams**: Up to 10 simultaneous

### **System Performance**
- **CPU Usage**: <20% per active stream
- **Memory**: <100MB base + 50MB per camera
- **Startup Time**: <5 seconds
- **Response Time**: <100ms for API calls

## 🔒 **SECURITY REQUIREMENTS**

### **Authentication**
- **Camera Credentials**: Secure storage and transmission
- **API Security**: Optional OAuth2 integration
- **Network Security**: HTTPS support for production

### **Privacy**
- **Local Processing**: No cloud data transmission
- **Data Retention**: Configurable storage policies
- **Access Control**: User-based permissions

## 🚀 **DEPLOYMENT OPTIONS**

### **Development Mode**
```bash
# Local development with hot reload
python -m devices_mcp.web.server --reload
```

### **Production Mode**
```bash
# Production deployment with uvicorn
uvicorn devices_mcp.web.server:app --host 0.0.0.0 --port 7777
```

### **Docker Deployment**
```dockerfile
# Dockerfile for containerized deployment
FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install -e .
EXPOSE 7777
CMD ["python", "-m", "devices_mcp.web.server"]
```

## 📱 **BROWSER COMPATIBILITY**

### **Supported Browsers**
- ✅ **Chrome/Chromium**: Full support
- ✅ **Firefox**: Full support
- ✅ **Safari**: Full support
- ✅ **Edge**: Full support
- ✅ **Mobile Browsers**: Responsive design

### **Required Features**
- **HTML5 Video**: For video streaming
- **WebSocket**: For real-time updates
- **Fetch API**: For AJAX requests
- **CSS Grid**: For responsive layout

## 🎯 **SUCCESS METRICS**

### **Technical Metrics**
- **Uptime**: 99.9% availability
- **Stream Quality**: <1% dropped frames
- **Response Time**: <100ms API response
- **Error Rate**: <0.1% failed requests

### **User Experience Metrics**
- **Setup Time**: <5 minutes from install to streaming
- **Ease of Use**: Intuitive dashboard interface
- **Camera Discovery**: Automatic detection where possible
- **Documentation**: Comprehensive guides and examples

## 🔮 **FUTURE ROADMAP**

### **Phase 1 (Current)**
- ✅ Windows USB camera server integration (Port 10715)
- ✅ Massive repository linting cleanup (270+ lints, 160+ files)
- ✅ Drone Research: BETAFPV Pavo35 documented
- ✅ Camera Research: Insta360 X5 connectivity guide added
- ✅ Real video streaming implementation
- ✅ USB webcam support
- ✅ Tapo camera integration
- ✅ MCP tool registration

### **Phase 2 (Next)**
- 🔄 Advanced PTZ controls
- 🔄 Motion detection alerts
- 🔄 Recording management
- 🔄 Mobile app integration

### **Phase 3 (Future)**
- 📋 AI-powered analytics
- 📋 Cloud storage integration
- 📋 Multi-tenant support
- 📋 Enterprise features

## 📞 **SUPPORT & DOCUMENTATION**

### **Getting Help**
- **GitHub Issues**: Bug reports and feature requests
- **Documentation**: Comprehensive guides in `/docs`
- **Examples**: Sample configurations and use cases
- **Community**: Developer forums and discussions

### **Documentation Structure**
```
docs/
├── assessment.md                    # Current system assessment
├── video_streaming_implementation.md # Streaming implementation details
├── mock_removal_progress.md         # Mock removal progress
├── USER_GUIDE.md                    # User documentation
├── GRAFANA_INTEGRATION_*.md         # Grafana integration guides
└── standards/                       # Development standards
```

---

## Fleet integration (2026-06)

**Requirement:** Expose aggregated home-safety priority incidents for Fritz urgent dispatch without pushing webhooks.

| Item | Status |
|------|--------|
| `GET /api/fleet/priority` on backend `:10717` | Implemented |
| Shelly kitchen/temp thresholds | Implemented |
| Nest CO/smoke via Home Assistant | Implemented |
| Ring intrusion window (configurable minutes) | Implemented |
| Consumer: Fritz `coworker_devices_watch` (5m poll) | Implemented |

See [FLEET_INTEGRATION.md](FLEET_INTEGRATION.md).

---

**Last Updated**: June 2026
**Version**: 1.21.5+
**Status**: Beta
