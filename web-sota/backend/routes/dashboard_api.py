"""Dashboard routes."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return HTMLResponse("""
    <html>
        <head><title>Devices MCP Dashboard</title></head>
        <body>
            <h1>Devices MCP Dashboard</h1>
            <p>Port 10716 - Following MCP Central Docs</p>
            <p>All functionality will be restored</p>
        </body>
    </html>
    """)
