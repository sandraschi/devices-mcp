"""Audio streaming API for cameras."""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audio", tags=["audio"])


class AudioStreamRequest(BaseModel):
    """Request for audio stream."""

    camera_id: str


# Store active ffmpeg processes for cleanup
_active_streams: dict = {}


async def get_camera_rtsp_url(camera_id: str) -> str | None:
    """Get RTSP URL for a camera with authentication."""
    from devices_mcp.core.server import DevicesMCPServer

    server = await DevicesMCPServer.get_instance()
    camera = await server.camera_manager.get_camera(camera_id)

    if not camera:
        return None

    if not await camera.is_connected():
        await camera.connect()

    # Get base RTSP URL
    stream_url = await camera.get_stream_url()
    if not stream_url:
        return None

    # Add auth credentials
    from urllib.parse import urlparse

    parsed = urlparse(stream_url)
    username = camera.config.params.get("username", "")
    password = camera.config.params.get("password", "")

    if username and password:
        return f"rtsp://{username}:{password}@{parsed.hostname}:{parsed.port or 554}{parsed.path}"

    return stream_url


@router.get("/info/{camera_id}")
async def get_audio_info(camera_id: str):
    """Get audio stream information for a camera.

    Returns RTSP URL and audio capability info.
    Two-way audio is NOT supported via ONVIF - only listening is available.
    """
    rtsp_url = await get_camera_rtsp_url(camera_id)

    if not rtsp_url:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found or not connected")

    # Mask password in response
    from urllib.parse import urlparse

    parsed = urlparse(rtsp_url)
    safe_url = f"rtsp://{parsed.hostname}:{parsed.port or 554}{parsed.path}"

    return {
        "camera_id": camera_id,
        "rtsp_url": safe_url,
        "rtsp_url_full": rtsp_url,  # Full URL with auth for VLC
        "audio_capable": True,
        "two_way_audio": False,
        "two_way_audio_note": "Two-way audio is NOT supported via ONVIF. Use the Tapo app for two-way communication.",
        "playback_options": {
            "vlc": f"vlc {rtsp_url}",
            "ffplay": f"ffplay -i {rtsp_url}",
            "browser": f"/api/audio/hls/{camera_id}/stream.m3u8",
        },
    }


@router.get("/vlc-link/{camera_id}")
async def get_vlc_link(camera_id: str):
    """Get a VLC-compatible link for the camera stream with audio.

    Open this URL in VLC Media Player for full video + audio playback.
    """
    rtsp_url = await get_camera_rtsp_url(camera_id)

    if not rtsp_url:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")

    # Return HTML page that attempts to open VLC
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Open in VLC - {camera_id}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                text-align: center;
            }}
            .url-box {{
                background: #f5f5f5;
                padding: 15px;
                border-radius: 8px;
                word-break: break-all;
                font-family: monospace;
                margin: 20px 0;
            }}
            .btn {{
                display: inline-block;
                padding: 12px 24px;
                background: #ff6600;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                margin: 10px;
                font-weight: bold;
            }}
            .btn:hover {{
                background: #e55c00;
            }}
            .info {{
                color: #666;
                font-size: 0.9rem;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <h1>🎥 {camera_id}</h1>
        <h2>Camera Stream with Audio</h2>

        <div class="url-box">
            <strong>RTSP URL:</strong><br>
            {rtsp_url}
        </div>

        <p>Copy the URL above and paste in VLC Media Player:</p>
        <p><strong>Media → Open Network Stream → Paste URL</strong></p>

        <a href="vlc://{rtsp_url}" class="btn">🎬 Open in VLC</a>

        <div class="info">
            <p>WARNING <strong>Two-Way Audio Limitation:</strong></p>
            <p>ONVIF protocol only supports <em>listening</em> to camera audio.</p>
            <p>For two-way communication, use the <strong>Tapo app</strong>.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/player/{camera_id}")
async def audio_player_page(camera_id: str):
    """Embedded audio player page with stream controls."""
    rtsp_url = await get_camera_rtsp_url(camera_id)

    if not rtsp_url:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")

    # HLS stream URL (if ffmpeg transcoding is available)
    hls_url = f"/api/audio/hls/{camera_id}/stream.m3u8"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Audio Player - {camera_id}</title>
        <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
        <style>
            * {{ box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                color: white;
                min-height: 100vh;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
            }}
            h1 {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .player-card {{
                background: rgba(255,255,255,0.1);
                border-radius: 16px;
                padding: 24px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.1);
            }}
            .video-container {{
                position: relative;
                width: 100%;
                padding-top: 56.25%;
                background: #000;
                border-radius: 8px;
                overflow: hidden;
                margin-bottom: 20px;
            }}
            video {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
            }}
            .controls {{
                display: flex;
                gap: 12px;
                flex-wrap: wrap;
                justify-content: center;
            }}
            .btn {{
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .btn-primary {{
                background: #3b82f6;
                color: white;
            }}
            .btn-primary:hover {{
                background: #2563eb;
            }}
            .btn-secondary {{
                background: rgba(255,255,255,0.2);
                color: white;
            }}
            .btn-secondary:hover {{
                background: rgba(255,255,255,0.3);
            }}
            .btn-vlc {{
                background: #ff6600;
                color: white;
            }}
            .btn-vlc:hover {{
                background: #e55c00;
            }}
            .status {{
                text-align: center;
                padding: 10px;
                margin-top: 20px;
                border-radius: 8px;
                font-size: 0.9rem;
            }}
            .status-connecting {{
                background: rgba(59, 130, 246, 0.2);
                border: 1px solid #3b82f6;
            }}
            .status-playing {{
                background: rgba(34, 197, 94, 0.2);
                border: 1px solid #22c55e;
            }}
            .status-error {{
                background: rgba(239, 68, 68, 0.2);
                border: 1px solid #ef4444;
            }}
            .warning-box {{
                background: rgba(251, 191, 36, 0.2);
                border: 1px solid #fbbf24;
                border-radius: 8px;
                padding: 16px;
                margin-top: 20px;
            }}
            .warning-box h3 {{
                margin: 0 0 8px 0;
                color: #fbbf24;
            }}
            .warning-box p {{
                margin: 0;
                opacity: 0.9;
            }}
            .volume-control {{
                display: flex;
                align-items: center;
                gap: 10px;
                justify-content: center;
                margin-top: 15px;
            }}
            .volume-control input {{
                width: 150px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔊 {camera_id} - Audio Stream</h1>

            <div class="player-card">
                <div class="video-container">
                    <video id="video" controls autoplay muted></video>
                </div>

                <div class="controls">
                    <button class="btn btn-primary" onclick="startStream()">
                        ▶️ Start Stream
                    </button>
                    <button class="btn btn-secondary" onclick="stopStream()">
                        ⏹️ Stop
                    </button>
                    <button class="btn btn-secondary" onclick="toggleMute()">
                        🔊 Unmute
                    </button>
                    <a href="vlc://{rtsp_url}" class="btn btn-vlc">
                        🎬 Open in VLC
                    </a>
                </div>

                <div class="volume-control">
                    <span>🔈</span>
                    <input type="range" id="volume" min="0" max="1" step="0.1" value="0.5" onchange="setVolume(this.value)">
                    <span>🔊</span>
                </div>

                <div id="status" class="status status-connecting">
                    Ready to connect...
                </div>

                <div class="warning-box">
                    <h3>WARNING Two-Way Audio Limitation</h3>
                    <p>ONVIF protocol only supports <strong>listening</strong> to camera audio.</p>
                    <p>For two-way communication (talking to camera), use the <strong>Tapo app</strong>.</p>
                </div>
            </div>
        </div>

        <script>
            const video = document.getElementById('video');
            const statusEl = document.getElementById('status');
            let hls = null;
            const hlsUrl = '{hls_url}';
            const rtspUrl = '{rtsp_url}';

            function setStatus(message, type) {{
                statusEl.textContent = message;
                statusEl.className = 'status status-' + type;
            }}

            function startStream() {{
                setStatus('Connecting to stream...', 'connecting');

                // Try HLS first (works in browser)
                if (Hls.isSupported()) {{
                    if (hls) {{
                        hls.destroy();
                    }}
                    hls = new Hls({{
                        enableWorker: true,
                        lowLatencyMode: true
                    }});
                    hls.loadSource(hlsUrl);
                    hls.attachMedia(video);
                    hls.on(Hls.Events.MANIFEST_PARSED, function() {{
                        video.play();
                        setStatus('🎬 Stream playing (HLS)', 'playing');
                    }});
                    hls.on(Hls.Events.ERROR, function(event, data) {{
                        if (data.fatal) {{
                            setStatus('ERROR HLS not available. Use VLC for full audio.', 'error');
                        }}
                    }});
                }} else if (video.canPlayType('application/vnd.apple.mpegurl')) {{
                    // Native HLS support (Safari)
                    video.src = hlsUrl;
                    video.addEventListener('loadedmetadata', function() {{
                        video.play();
                        setStatus('🎬 Stream playing (Native HLS)', 'playing');
                    }});
                }} else {{
                    setStatus('ERROR HLS not supported. Use VLC button for audio stream.', 'error');
                }}
            }}

            function stopStream() {{
                if (hls) {{
                    hls.destroy();
                    hls = null;
                }}
                video.pause();
                video.src = '';
                setStatus('Stream stopped', 'connecting');
            }}

            function toggleMute() {{
                video.muted = !video.muted;
                const btn = event.target;
                btn.textContent = video.muted ? '🔇 Muted' : '🔊 Unmute';
            }}

            function setVolume(val) {{
                video.volume = parseFloat(val);
            }}

            // Auto-start on load
            // startStream();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


# HLS transcoding endpoint (requires ffmpeg)
@router.get("/hls/{camera_id}/stream.m3u8")
async def hls_stream_manifest(camera_id: str):
    """Get HLS manifest for browser-compatible streaming.

    Requires ffmpeg to be running for transcoding.
    This is a placeholder - full implementation needs ffmpeg subprocess management.
    """
    # For now, return a message about using VLC
    raise HTTPException(
        status_code=501,
        detail=f"HLS transcoding not implemented for {camera_id}. "
        "Use VLC or ffplay for audio streaming. "
        "RTSP streams can be opened directly in VLC Media Player.",
    )


@router.get("/capabilities")
async def get_audio_capabilities():
    """Get audio capabilities overview for all camera types."""
    return {
        "onvif_cameras": {
            "listen_audio": True,
            "two_way_audio": False,
            "note": "ONVIF Profile S does not support audio backchannel (two-way audio)",
        },
        "ring_doorbell": {
            "listen_audio": True,
            "two_way_audio": True,
            "note": "Ring supports two-way audio via WebRTC",
        },
        "tapo_app": {
            "listen_audio": True,
            "two_way_audio": True,
            "note": "Full two-way audio available in official Tapo app",
        },
        "recommendation": "For two-way audio with Universal IoT Devices, use the Tapo app. "
        "For listening only, use VLC with the RTSP URL.",
    }
