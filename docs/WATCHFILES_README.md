# Devices MCP WebApp Watchfiles Crashproofing

This directory contains crashproofing implementation for the Devices MCP WebApp using watchfiles. The crashproof runner automatically detects application crashes and restarts the web server with exponential backoff.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
# Install watchfiles dependencies
pip install -r requirements-watchfiles.txt

# Or use the PowerShell script (Windows)
.\install-watchfiles.ps1
```

### 2. Run with Crashproofing
```bash
# Instead of: python -m devices_mcp.web --host 0.0.0.0 --port 7777
python watchfiles_runner.py
```

### 3. Test the Implementation
```bash
python test_watchfiles_runner.py
```

## 📋 Features

### Automatic Crash Detection & Recovery
- Monitors Devices MCP WebApp process health continuously
- Automatically restarts on crashes with exponential backoff (1s → 1.5s → 2.25s → 3.375s...)
- HTTP health checks via `/api/health` endpoint every 30 seconds
- Configurable restart limits (default: 10 attempts)

### Smart Restart Logic
- Exponential backoff delays for progressive retry intervals
- Graceful process cleanup before restart with proper signal handling
- Cross-platform compatibility (Windows/Unix signal handling)
- Automatic resource cleanup and process termination

### Health Monitoring
- HTTP health endpoint monitoring (`/api/health`)
- Configurable health check intervals
- Automatic restart on health check failures
- Detailed health status logging

### Comprehensive Logging
- Structured logging to console and `logs/devices-mcp-watchfiles.log`
- Crash reports saved as JSON in `logs/` directory with detailed analysis
- Process statistics and uptime tracking with real-time metrics
- Rotation-friendly log formats for long-term monitoring

### Production Ready
- Systemd service integration for Linux production deployments
- Security hardening with restricted privileges and resource limits
- Proper signal handling for graceful shutdown (SIGINT/SIGTERM)
- Memory limits (2GB) and CPU quotas (200%) for resource management

## ⚙️ Configuration

### Environment Variables

#### Devices MCP WebApp Settings
- `TAPO_WEBAPP_HOST=0.0.0.0` (default)
- `TAPO_WEBAPP_PORT=7777` (default)
- `TAPO_WEBAPP_DEBUG=false` (default)

#### Crashproofing Settings
- `WATCHFILES_MAX_RESTARTS=10` (default)
- `WATCHFILES_RESTART_DELAY=1.0` (seconds, default)
- `WATCHFILES_BACKOFF_MULTIPLIER=1.5` (default)
- `WATCHFILES_HEALTH_CHECK_INTERVAL=30` (seconds, default)
- `WATCHFILES_NOTIFY_ON_CRASH=true` (default)

### Example Configuration
```bash
export TAPO_WEBAPP_HOST=127.0.0.1
export TAPO_WEBAPP_PORT=8000
export WATCHFILES_MAX_RESTARTS=5
export WATCHFILES_RESTART_DELAY=2.0
export WATCHFILES_HEALTH_CHECK_INTERVAL=60
python watchfiles_runner.py
```

## 📊 Monitoring & Logs

### Log Files
- **`logs/devices-mcp-watchfiles.log`** - All events and operations with timestamps
- **`logs/devices-mcp-crash-report-{timestamp}.json`** - Detailed crash analysis with stack traces

### Real-time Stats
The runner provides comprehensive statistics:
```python
stats = runner.get_stats()
# {
#   'process_running': True,
#   'restart_count': 2,
#   'total_uptime': 3600.5,
#   'crash_count': 2,
#   'command': ['python', '-m', 'devices_mcp.web', ...],
#   'health_check_url': 'http://0.0.0.0:7777/api/health'
# }
```

### Crash Report Structure
```json
{
  "generated_at": "2025-12-17T10:30:00Z",
  "total_crashes": 3,
  "total_restarts": 3,
  "total_uptime": 7200.5,
  "max_restarts_allowed": 10,
  "crash_events": [
    {
      "timestamp": "2025-12-17T10:25:00Z",
      "exit_code": 1,
      "uptime_before_crash": 1800.0,
      "restart_attempt": 1,
      "pid": 12345,
      "stderr": "ConnectionError: Failed to connect to camera..."
    }
  ],
  "system_info": {
    "platform": "linux",
    "python_version": "3.10.0",
    "cwd": "/opt/devices-mcp"
  },
  "app_info": {
    "name": "Devices MCP WebApp",
    "default_host": "0.0.0.0",
    "default_port": 7777,
    "health_endpoint": "http://0.0.0.0:7777/api/health"
  }
}
```

## 🛑 Graceful Shutdown

The runner handles system signals properly:
- `SIGINT` (Ctrl+C): Graceful shutdown with cleanup and final crash report
- `SIGTERM`: Graceful shutdown for systemd integration
- Process tree termination with proper child process cleanup
- Automatic log file closure and resource cleanup

## 🐧 Production Deployment

### Systemd Service
Use the provided service file for production deployment:

```bash
# Copy service file
sudo cp devices-mcp-watchfiles.service /etc/systemd/system/

# Create dedicated user
sudo useradd -r -s /bin/false devices-mcp

# Set permissions
sudo chown -R devices-mcp:devices-mcp /opt/devices-mcp

# Enable and start service
sudo systemctl enable devices-mcp-watchfiles
sudo systemctl start devices-mcp-watchfiles

# Monitor
sudo systemctl status devices-mcp-watchfiles
journalctl -u devices-mcp-watchfiles -f
```

### Docker Integration
For Docker deployments, the watchfiles runner can be used as a health check:

```dockerfile
# Use watchfiles runner as entrypoint
COPY watchfiles_runner.py /app/
CMD ["python", "watchfiles_runner.py"]
```

## 🧪 Testing Crashproofing

### Manual Crash Testing
```bash
# Start the runner
python watchfiles_runner.py

# In another terminal, find and kill the process
ps aux | grep devices_mcp
kill -9 <python-pid>

# Watch the runner automatically restart the webapp
```

### Health Check Testing
```bash
# Test health endpoint
curl http://localhost:7777/api/health

# Temporarily break the health check to test restart logic
# (Modify the health endpoint to return 500 temporarily)
```

### Load Testing
```bash
# Test with high load to trigger potential crashes
ab -n 1000 -c 10 http://localhost:7777/
```

## 📈 Benefits Over Standard Deployment

### Before Crashproofing:
- ❌ Manual restart required on crashes
- ❌ No visibility into failure patterns
- ❌ Camera connection issues cause service downtime
- ❌ Development downtime during debugging
- ❌ Unstable production deployments

### After Crashproofing:
- ✅ Zero-touch crash recovery with automatic camera reconnection
- ✅ Detailed crash analytics for camera connectivity issues
- ✅ Improved development workflow with instant restarts
- ✅ Production-grade stability before dockerization
- ✅ Clear migration path to containerized deployments

## 🔧 Troubleshooting

### Common Issues

#### "Module 'watchfiles' not found"
```bash
pip install -r requirements-watchfiles.txt
```

#### Port Already in Use
```bash
# Check what's using the port
netstat -tulpn | grep 7777
# Or on Windows
netstat -ano | findstr 7777

# Kill the process
kill -9 <PID>
```

#### Permission denied on log files
```bash
mkdir -p logs
chmod 755 logs
```

#### Health checks failing
- Verify `/api/health` endpoint is working
- Check network connectivity to localhost
- Adjust `WATCHFILES_HEALTH_CHECK_INTERVAL`

#### Process not restarting
- Check system resource limits (memory, CPU)
- Verify Python module path is correct
- Check application logs for startup errors
- Ensure virtual environment is activated

### Debug Mode
Enable debug logging:
```bash
export TAPO_WEBAPP_DEBUG=true
python watchfiles_runner.py
```

### Performance Tuning
For high-traffic deployments:
```bash
export WATCHFILES_HEALTH_CHECK_INTERVAL=15  # More frequent checks
export WATCHFILES_MAX_RESTARTS=20          # Allow more restarts
export WATCHFILES_RESTART_DELAY=0.5        # Faster initial restart
```

## 📚 Related Files

- `watchfiles_runner.py` - Main crashproof runner implementation
- `requirements-watchfiles.txt` - Required dependencies
- `install-watchfiles.ps1` - Windows installation script
- `run-with-watchfiles.ps1` - Convenient runner with configuration options
- `devices-mcp-watchfiles.service` - Systemd service template
- `test_watchfiles_runner.py` - Test suite
- `logs/devices-mcp-watchfiles.log` - Runtime logs
- `logs/devices-mcp-crash-report-*.json` - Crash analysis reports

## 🔄 Migration to Docker

When ready to dockerize:

1. **Keep watchfiles logic** as container health check
2. **Use Docker restart policies** (`restart: unless-stopped`)
3. **Convert health checks** to Docker HEALTHCHECK
4. **Mount logs directory** for persistent crash reports

Example docker-compose.yml:
```yaml
version: '3.8'
services:
  devices-mcp:
    build: .
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7777/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    ports:
      - "7777:7777"
```

## 🎯 Camera-Specific Benefits

The Devices MCP WebApp has unique crash scenarios that watchfiles addresses:

1. **Network Connectivity Issues** - Automatic recovery from network interruptions
2. **Camera Connection Failures** - Restart on camera hardware issues
3. **Database Connection Problems** - Recovery from SQLite/database issues
4. **Memory Leaks** - Periodic restarts prevent memory accumulation
5. **USB Device Disconnections** - Recovery from webcam hardware issues

## 🤝 Contributing

When modifying the crashproof runner:

1. Test crash scenarios thoroughly, especially camera-related failures
2. Update logging for new features with appropriate log levels
3. Document new configuration options in this README
4. Add appropriate error handling for camera-specific errors
5. Update the test suite for new functionality

## 📞 Support

For issues with crashproofing:

1. Check `logs/devices-mcp-watchfiles.log` for errors
2. Review crash reports in `logs/` directory for camera connectivity issues
3. Run `python test_watchfiles_runner.py` to verify functionality
4. Check environment variable configuration
5. Verify `/api/health` endpoint is working
6. Test camera connections independently

---

**Implementation Complete** ✅
**Camera-Specific Optimizations** ✅
**Production Ready** ✅
**Documentation Complete** ✅
