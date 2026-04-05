# MCPB Quick Start Guide

**Devices MCP Server - MCPB Packaging**

---

## 📦 What is MCPB?

**MCPB (MCP Bundle)** is Anthropic's official packaging format for MCP servers. It provides:

- ✅ **One-click installation** - Drag & drop to Claude Desktop
- ✅ **User configuration** - Interactive setup prompts
- ✅ **Bundled dependencies** - Everything included
- ✅ **Automated builds** - GitHub Actions integration

---

## 🚀 Quick Installation (For Users)

### Install from MCPB Package

1. **Download** the latest `.mcpb` package from [GitHub Releases](https://github.com/sandraschi/devices-mcp/releases)
2. **Drag** the file to Claude Desktop
3. **Configure** when prompted:
   - Tapo Camera IP Address (optional)
   - Tapo Camera Username (optional)
   - Tapo Camera Password (optional)
   - Web Dashboard Port (default: 7777)
4. **Restart** Claude Desktop
5. **Done!** All 26+ tools are now available

### Quick Start Commands

```
"Connect to my USB webcam using add_camera tool"
"Add a Tapo camera at 192.168.1.100"
"Start the dashboard and show me the camera feed"
"Help me set up PTZ controls"
```

---

## 🛠 Building MCPB Package (For Developers)

### Prerequisites

```bash
# Install MCPB CLI
npm install -g @anthropic-ai/mcpb

# Verify installation
mcpb --version  # Should show 1.1.1 or higher
```

### Build Process

```powershell
# 1. Validate manifest
mcpb validate manifest.json

# 2. Build package (Windows PowerShell)
.\scripts\build-mcpb-package.ps1 -NoSign

# 3. Verify output
# Package created: dist/devices-mcp.mcpb (~280KB)
```

---

## 📄 Configuration Files

### mcpb.json (Build Configuration)

Located in project root. Defines build settings:

```json
{
  "name": "devices-mcp",
  "version": "1.0.0",
  "mcp": {
    "version": "3.1.0",
    "server": {
      "command": "python",
      "args": ["-m", "devices_mcp.server_v2", "--direct"]
    }
  }
}
```

### manifest.json (Runtime Configuration)

Located in project root. Defines runtime behavior:

```json
{
  "manifest_version": "0.2",
  "name": "devices-mcp",
  "version": "1.0.0",
  "server": {
    "type": "python",
    "entry_point": "src/devices_mcp/server_v2.py"
  },
  "user_config": {
    "tapo_camera_host": { ... },
    "tapo_camera_username": { ... },
    "tapo_camera_password": { ... },
    "dashboard_port": { ... }
  }
}
```

### .mcpbignore (Exclude Files)

Similar to `.gitignore`, excludes files from the package:

```
venv/
__pycache__/
*.pyc
.pytest_cache/
htmlcov/
docs/development/
*.dxt
```

---

## 🚀 Automated Builds (GitHub Actions)

### Trigger Build

```bash
# Create and push version tag
git tag v1.0.0
git push origin v1.0.0

# GitHub Actions will automatically:
# 1. Build MCPB package
# 2. Create GitHub Release
# 3. Upload .mcpb file
# 4. Publish to PyPI (if configured)
```

### Workflow File

Located at `.github/workflows/build-mcpb.yml`:

- **Validates** manifest.json
- **Builds** MCPB package
- **Uploads** artifacts
- **Creates** GitHub releases
- **Publishes** to PyPI

---

## 📊 Package Details

| Property | Value |
|----------|-------|
| **Name** | devices-mcp |
| **Version** | 1.0.0 |
| **Size** | ~280KB |
| **Files** | 134 source files |
| **Tools** | 26+ MCP tools |
| **Platforms** | Windows, macOS, Linux |

---

## 🔍 Troubleshooting

### MCPB CLI Not Found

```bash
# Install globally
npm install -g @anthropic-ai/mcpb

# Verify
mcpb --version
```

### Manifest Validation Fails

```bash
# Check manifest syntax
mcpb validate manifest.json

# Common issues:
# - Invalid JSON syntax
# - Unrecognized keys
# - Missing required fields
```

### Package Too Large

The `.mcpbignore` file excludes:
- Virtual environments (`venv/`)
- Test files and coverage reports
- Development documentation
- IDE configuration files
- Old DXT files

If package is still large, check:
```bash
# See what's being included
mcpb pack . dist/test.mcpb --verbose
```

### Server Won't Start in Claude Desktop

Check logs:
```
%APPDATA%\Claude\logs\mcp-server-devices-mcp.log
```

Common fixes:
1. Ensure Python 3.10+ is installed
2. Check PYTHONPATH in manifest.json
3. Verify FastMCP >= 3.1.0
4. Check camera configuration

---

## 📚 Documentation

### MCPB-Specific Docs

- [MCPB Building Guide](docs/mcpb-packaging/MCPB_BUILDING_GUIDE.md) - Comprehensive 1,900+ line guide
- [MCPB Implementation Summary](docs/mcpb-packaging/MCPB_IMPLEMENTATION_SUMMARY.md) - Our implementation
- [MCPB Packaging README](docs/mcpb-packaging/README.md) - Quick reference

### General Docs

- [README.md](README.md) - Main documentation
- [PRD.md](docs/PRD.md) - Product requirements
- [Assessment](docs/assessment.md) - Technical assessment
- [Dashboard Startup](docs/DASHBOARD_STARTUP.md) - Web dashboard guide
- [Camera Setup](docs/CAMERA_SETUP_GUIDE.md) - Camera configuration

---

## 🎯 Next Steps After Installation

1. **Add a camera:**
   ```
   "Add my USB webcam"
   "Connect to Tapo camera at 192.168.1.100"
   ```

2. **Start the dashboard:**
   ```
   "Start the web dashboard"
   # Opens at http://localhost:7777
   ```

3. **Explore tools:**
   ```
   "Show me available camera tools"
   "Help me with PTZ controls"
   ```

4. **View live feed:**
   - Open dashboard in browser
   - Click camera to see live stream
   - Use PTZ controls (if supported)

---

## 🏆 Success Metrics

Our MCPB implementation:
- ✅ Package builds successfully (280KB)
- ✅ Manifest validates without errors
- ✅ All 26+ tools registered
- ✅ User configuration working
- ✅ GitHub Actions automated
- ✅ Production-ready distribution

---

*For detailed MCPB documentation, see [docs/mcpb-packaging/](docs/mcpb-packaging/)*
