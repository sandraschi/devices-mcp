@echo off
cd /d "%~dp0web-sota"
set PYTHONPATH=D:\Dev\repos\devices-mcp\src;D:\Dev\repos\devices-mcp\web-sota
C:\Users\sandr\.local\bin\uv.exe run python -m backend.server --host 127.0.0.1 --port 10717
