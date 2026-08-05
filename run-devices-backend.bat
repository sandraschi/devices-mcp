@echo off
cd /d "%~dp0web-sota"
set PYTHONPATH=D:\Dev\repos\devices-mcp\src;D:\Dev\repos\devices-mcp\web-sota
"%~dp0.venv\Scripts\python.exe" -m backend.server --host 127.0.0.1 --port 10717

