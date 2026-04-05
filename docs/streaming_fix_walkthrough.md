# Devices MCP - Streaming Fix Walkthrough

## 1. Overview
We have transitioned to a **Split-Server Architecture** to resolve USB camera conflicts on Windows. This setup prevents the "Device in use" error by isolating USB hardware access to a dedicated process.

### Architecture
- **Server A (Port 7778)**: `windows_camera_server.py`
  - **Role**: Exclusive hardware access to USB webcams.
  - **Tech**: OpenCV direct capture.
  - **Endpoints**: `http://localhost:7778/mjpeg?device=0`

- **Server B (Port 7777)**: `devices_mcp.web` (Main App)
  - **Role**: Main UI, Tapo/ONVIF streaming, and Proxy for Server A.
  - **Tech**: FastAPI + HTTPX Proxy.
  - **Endpoints**: `/api/cameras`, `/api/cameras/<id>/mjpeg`

## 2. Startup Procedure
You must start the servers in this specific order.

### Step 1: Start the USB Hardware Server (Port 7778)
Open a new terminal (PowerShell) and run:
```powershell
$env:PYTHONPATH="D:\Dev\repos\devices-mcp\src"
python D:\Dev\repos\devices-mcp\src\devices_mcp\camera\windows_camera_server.py --port 7778
```
*Wait until you see "Starting Windows USB Camera Server".*

### Step 2: Start the Main Web App (Port 7777)
Open a second terminal and run:
```powershell
$env:PYTHONPATH="D:\Dev\repos\devices-mcp\src"
python -m devices_mcp.web --port 7777
```

## 3. Verification

### Test USB Proxy
Go to: `http://localhost:7777/api/cameras/usb_camera_1/mjpeg`
- You should see the live feed.
- Internally, this request routes: Browser -> Port 7777 -> Port 7778 -> Webcam -> Return

### Test Tapo/ONVIF
Go to: `http://localhost:7777/api/cameras/tapo_kitchen/mjpeg`
- This uses the new hardened FFMPEG transcoding path (`rtsp_transport=tcp`).

## 4. Troubleshooting

**"Connection Refused" on USB Camera:**
- Check if Server A (Port 7778) is running.
- Verify `windows_camera_server.py` didn't crash.

**"Request Timed Out" on Camera List:**
- We increased the discovery timeout to 8 seconds.
- Check if your Tapo camera IP (e.g., `192.168.0.174`) is reachable via `ping`.

**"Device In Use" Error:**
- Ensure NO other app (Zoom, Teams, Camera App) is using the webcam.
- Ensure only **one** instance of `windows_camera_server.py` is running.
