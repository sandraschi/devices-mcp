# Devices MCP - Multimodal Enhancement Implementation Plan

**Date:** 2025-08-19
**Status:** Ready for Implementation
**Target:** Add multimodal LLM integration to existing MCP server
**Windsurf Task:** Enhance existing server without breaking current functionality

---

## Executive Summary

The existing `devices-mcp` server is **well-implemented** with FastMCP 2.10+, real Tapo camera integration, and comprehensive control features. The enhancement adds **multimodal image analysis** capabilities to enable Claude Desktop to "see" camera feeds and provide intelligent analysis.

**Key Gap:** Missing multimodal LLM integration for image analysis (schnitzel quality, security threats, pet monitoring).

---

## Current Status Assessment

### ✅ EXISTING STRENGTHS (Preserve These!)
- **FastMCP 2.10+ Ready:** Using fastmcp>=2.10.0
- **Real Tapo Integration:** pytapo>=3.3.48 with working camera control
- **Comprehensive Tools:** 12 working MCP tools for camera operations
- **DXT Packaging:** Ready for distribution
- **Testing Framework:** pytest setup with coverage

### ❌ CRITICAL GAPS (Fix These!)
1. **No Multimodal Integration** - Cannot analyze camera images
2. **Incomplete Image Capture** - snapshot() returns empty placeholder
3. **No Security Scanning** - Missing multi-camera threat detection
4. **No Analysis Presets** - No predefined analysis scenarios

---

## Implementation Tasks for Windsurf

### PHASE 1: Fix Image Capture Foundation 🔧

#### Task 1.1: Fix Existing snapshot() Tool
**File:** `src/devices_mcp/server_v2.py`

**Current Code (Lines ~400+):**
```python
async def handle_snapshot(self, message: McpMessage) -> Dict[str, Any]:
    """Handle snapshot request."""
    try:
        # In a real implementation, this would capture a snapshot
        snapshot_data = b""  # Placeholder for actual image data

        return {
            "status": "success",
            "snapshot": f"data:image/jpeg;base64,{base64.b64encode(snapshot_data).decode()}",
            "timestamp": datetime.now().isoformat()
        }
```

**REPLACE WITH:**
```python
@self.mcp.tool()
async def capture_still(params: dict) -> Dict[str, Any]:
    """
    Capture still image from camera with optional analysis.

    Args:
        params: Dictionary containing:
            - save_to_temp: Save image to C:/temp/ (default: True)
            - analyze: Perform multimodal analysis (default: False)
            - prompt: Analysis prompt (default: "Describe what you see")
            - camera_name: Camera identifier (default: "main")

    Returns:
        dict: Capture results with optional analysis
    """
    if not self.camera:
        return {"status": "error", "message": "Not connected to camera"}

    try:
        # Capture image using pytapo
        image_data = await self.camera.getSnapshot()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        camera_name = params.get("camera_name", "main")

        result = {
            "status": "success",
            "camera": camera_name,
            "timestamp": datetime.now().isoformat(),
            "image_size": len(image_data) if image_data else 0
        }

        # Save to temp directory if requested
        if params.get("save_to_temp", True) and image_data:
            import os
            os.makedirs("C:/temp", exist_ok=True)
            temp_path = f"C:/temp/tapo_{camera_name}_{timestamp}.jpg"

            with open(temp_path, 'wb') as f:
                f.write(image_data)

            result["saved_path"] = temp_path

            # Perform analysis if requested
            if params.get("analyze", False):
                analysis = await self._analyze_image(
                    temp_path,
                    params.get("prompt", "Describe what you see in this image")
                )
                result["analysis"] = analysis

        return result

    except Exception as e:
        logger.error(f"Failed to capture image: {str(e)}")
        return {"status": "error", "message": str(e)}
```

#### Task 1.2: Add Image Processing Dependencies
**File:** `pyproject.toml`

**ADD to dependencies section:**
```toml
dependencies = [
    "fastmcp>=2.10.0",
    "pytapo>=3.3.48",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
    "aiohttp>=3.9.0",
    "pillow>=10.0.0",    # ADD: Image processing
]
```

### PHASE 2: Implement Multimodal Analysis 🧠

#### Task 2.1: Add Core Analysis Function
**File:** `src/devices_mcp/server_v2.py`

**ADD after `__init__` method:**
```python
async def _analyze_image(self, image_path: str, prompt: str) -> Dict[str, Any]:
    """
    Prepare image for multimodal LLM analysis.

    Args:
        image_path: Path to image file
        prompt: Analysis prompt for LLM

    Returns:
        dict: Analysis preparation data for Claude Desktop
    """
    try:
        import base64
        from PIL import Image

        # Load and validate image
        with Image.open(image_path) as img:
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Resize if too large (max 2048x2048 for LLM efficiency)
            max_size = 2048
            if max(img.size) > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

                # Save resized image
                resized_path = image_path.replace(".jpg", "_resized.jpg")
                img.save(resized_path, "JPEG", quality=85)
                image_path = resized_path

        # Encode to base64 for multimodal LLM
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
            base64_data = base64.b64encode(image_data).decode('utf-8')

        return {
            "image_base64": base64_data,
            "image_path": image_path,
            "prompt": prompt,
            "media_type": "image/jpeg",
            "analysis_ready": True,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to prepare image for analysis: {str(e)}")
        return {
            "error": str(e),
            "analysis_ready": False,
            "timestamp": datetime.now().isoformat()
        }
```

#### Task 2.2: Add Standalone Analysis Tool
**ADD to `_register_tools()` method:**
```python
@self.mcp.tool()
async def analyze_image(params: dict) -> Dict[str, Any]:
    """
    Analyze existing image with multimodal LLM.

    Args:
        params: Dictionary containing:
            - image_path: Path to image file (required)
            - prompt: Analysis prompt (default: "Analyze this image")
            - preset: Use predefined prompt (security/food/pets/general)

    Returns:
        dict: Image analysis preparation data
    """
    image_path = params.get("image_path")
    if not image_path:
        return {"status": "error", "message": "image_path parameter required"}

    import os
    if not os.path.exists(image_path):
        return {"status": "error", "message": f"Image file not found: {image_path}"}

    # Handle preset prompts
    preset = params.get("preset")
    prompt = params.get("prompt")

    if preset and not prompt:
        presets = {
            "security": "Analyze this security camera image for potential threats: unknown people, suspicious activity, unusual objects, or security concerns. Provide threat level (none/low/medium/high) and recommended actions.",
            "food": "Analyze this food image for quality, presentation, and cooking status. Rate the appearance and suggest any improvements. Perfect for monitoring schnitzel perfection!",
            "pets": "Analyze this image for pet activity and behavior. Identify animals present and describe their actions, mood, and any notable behaviors.",
            "delivery": "Check this image for packages, delivery personnel, items left at door, or delivery vehicles. Note any delivery-related activity.",
            "general": "Describe what you see in this image, noting any significant activities, objects, or points of interest."
        }
        prompt = presets.get(preset, presets["general"])
    elif not prompt:
        prompt = "Analyze this image and describe what you see"

    analysis = await self._analyze_image(image_path, prompt)

    return {
        "status": "success" if analysis.get("analysis_ready") else "error",
        **analysis
    }
```

### PHASE 3: Advanced Security Scanning 🛡️

#### Task 3.1: Multi-Camera Security Scan Tool
**ADD to `_register_tools()` method:**
```python
@self.mcp.tool()
async def security_scan(params: dict) -> Dict[str, Any]:
    """
    Perform security scan across multiple cameras.

    Args:
        params: Dictionary containing:
            - cameras: List of camera configs (default: current camera)
            - threat_types: Types to detect (default: ["person", "unknown_person", "package"])
            - save_images: Save captured images (default: True)

    Returns:
        dict: Security scan results from all cameras
    """
    import uuid
    import asyncio

    # For now, use current camera (future: multi-camera support)
    if not self.camera:
        return {"status": "error", "message": "No camera connected"}

    threat_types = params.get("threat_types", ["person", "unknown_person", "package"])
    save_images = params.get("save_images", True)

    scan_id = str(uuid.uuid4())[:8]

    try:
        # Capture image for analysis
        capture_result = await self.capture_still({
            "save_to_temp": save_images,
            "analyze": True,
            "prompt": f'''Security analysis for: {", ".join(threat_types)}

CRITICAL ASSESSMENT NEEDED:
- Unknown people (not family members)
- Suspicious or unusual activity
- Packages or deliveries
- Unusual objects or vehicles
- Animals (pets vs wildlife)

Respond with:
- Threat level: none/low/medium/high
- Description of what you see
- Specific concerns identified
- Recommended action if any''',
            "camera_name": f"security_scan_{scan_id}"
        })

        # Format security scan result
        return {
            "status": "success",
            "scan_id": scan_id,
            "scan_type": "security",
            "cameras_scanned": 1,
            "timestamp": datetime.now().isoformat(),
            "threat_types_monitored": threat_types,
            "results": [capture_result]
        }

    except Exception as e:
        logger.error(f"Security scan failed: {str(e)}")
        return {
            "status": "error",
            "scan_id": scan_id,
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
```

### PHASE 4: Enhanced Configuration 📋

#### Task 4.1: Update imports at top of server_v2.py
**ADD these imports:**
```python
import base64
import uuid
from datetime import datetime
from PIL import Image
import os
```

#### Task 4.2: Create Analysis Presets Configuration
**CREATE NEW FILE:** `src/devices_mcp/presets.py`
```python
"""Analysis presets for different scenarios."""

ANALYSIS_PRESETS = {
    "security": {
        "prompt": """Security analysis - Look for potential threats:

ASSESS FOR:
- Unknown people (not family members)
- Suspicious or unusual activity
- Packages or deliveries
- Unusual objects or vehicles
- Animals (pets vs wildlife)
- Entry/exit activity

RESPOND WITH:
- Threat level: none/low/medium/high
- Description of what you see
- Specific security concerns
- Recommended action""",
        "description": "Security threat detection and assessment"
    },

    "food": {
        "prompt": """Food quality analysis:

ANALYZE:
- Food presentation and appearance
- Cooking status and doneness
- Color, texture, and quality indicators
- Plating and presentation
- Any quality concerns

PERFECT FOR:
- Monitoring schnitzel perfection!
- Cooking progress assessment
- Food safety evaluation""",
        "description": "Food quality and cooking analysis"
    },

    "pets": {
        "prompt": """Pet activity monitoring:

OBSERVE:
- Animals present and their species
- Pet behavior and activity
- Mood and demeanor indicators
- Interactions with environment
- Any concerning behaviors
- Play, rest, or feeding activities

GREAT FOR:
- Benny monitoring and activity tracking
- Pet behavior assessment""",
        "description": "Pet behavior and activity analysis"
    },

    "delivery": {
        "prompt": """Delivery detection:

CHECK FOR:
- Packages at door or entrance
- Delivery personnel present
- Delivery vehicles (trucks, vans, cars)
- Items left at entrance
- Delivery notifications needed

USEFUL FOR:
- Package delivery monitoring
- Entrance activity tracking""",
        "description": "Package and delivery monitoring"
    },

    "general": {
        "prompt": """General image analysis:

DESCRIBE:
- Main subjects and objects
- Activities taking place
- Notable features or changes
- Overall scene assessment
- Any interesting observations""",
        "description": "General purpose image description"
    }
}

def get_preset_prompt(preset_name: str) -> str:
    """Get prompt for a specific preset."""
    return ANALYSIS_PRESETS.get(preset_name, ANALYSIS_PRESETS["general"])["prompt"]

def list_presets() -> dict:
    """List all available presets with descriptions."""
    return {name: preset["description"] for name, preset in ANALYSIS_PRESETS.items()}
```

### PHASE 5: Testing and Validation ✅

#### Task 5.1: Update Test Files
**FILE:** `tests/test_server_v2.py`

**ADD test for new functionality:**
```python
import pytest
from unittest.mock import AsyncMock, patch
import tempfile
import os

@pytest.mark.asyncio
async def test_capture_still_with_analysis():
    """Test image capture with analysis functionality."""
    from devices_mcp.server_v2 import TapoCameraServer

    server = TapoCameraServer()
    server.camera = AsyncMock()

    # Mock image data
    fake_image_data = b"fake_jpeg_data"
    server.camera.getSnapshot.return_value = fake_image_data

    # Test capture with analysis
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch('os.makedirs'), \
             patch('builtins.open', mock_open()) as mock_file:

            result = await server.capture_still({
                "save_to_temp": True,
                "analyze": True,
                "prompt": "Test analysis"
            })

            assert result["status"] == "success"
            assert "saved_path" in result
            assert "analysis" in result

@pytest.mark.asyncio
async def test_security_scan():
    """Test security scanning functionality."""
    from devices_mcp.server_v2 import TapoCameraServer

    server = TapoCameraServer()
    server.camera = AsyncMock()
    server.camera.getSnapshot.return_value = b"fake_image"

    with patch.object(server, 'capture_still') as mock_capture:
        mock_capture.return_value = {
            "status": "success",
            "analysis": {"threat_level": "none"}
        }

        result = await server.security_scan({})

        assert result["status"] == "success"
        assert "scan_id" in result
        assert result["cameras_scanned"] == 1
```

### PHASE 6: Documentation Updates 📚

#### Task 6.1: Update README.md
**ADD to features section:**
```markdown
### New Multimodal Features
- **Image Analysis**: Capture and analyze camera feeds with multimodal LLMs
- **Security Scanning**: Multi-camera threat detection and assessment
- **Analysis Presets**: Pre-configured prompts for security, food, pets, delivery
- **Base64 Integration**: Direct integration with Claude Desktop for image analysis
- **Temp File Management**: Automatic image storage in C:/temp/ for analysis
```

#### Task 6.2: Create Usage Examples
**ADD to README.md:**
```markdown
### Multimodal Analysis Examples

```python
# Capture and analyze image
result = await camera.capture_still({
    "analyze": True,
    "prompt": "How does my schnitzel look?"
})

# Security scan
scan_result = await camera.security_scan({
    "threat_types": ["person", "package", "unusual_activity"]
})

# Analyze existing image
analysis = await camera.analyze_image({
    "image_path": "C:/temp/camera_image.jpg",
    "preset": "security"
})
```

---

## Testing Strategy

### Local Testing (No Real Camera)
1. **Mock Tests**: Verify tool registration and basic functionality
2. **Image Processing Tests**: Test base64 encoding and file operations
3. **Error Handling Tests**: Validate error scenarios

### Real Camera Testing (Sandra's Setup)
1. **Connection Test**: Verify existing camera tools still work
2. **Image Capture Test**: Test real snapshot capture and save
3. **Analysis Preparation Test**: Verify base64 encoding for Claude Desktop
4. **Security Scan Test**: Full workflow with real camera

### Integration Testing (Claude Desktop)
1. **Multimodal Flow Test**: Image → base64 → Claude Desktop analysis
2. **Preset Testing**: Verify different analysis scenarios
3. **Performance Testing**: Multi-camera scanning efficiency

---

## Success Criteria

### ✅ Phase 1 Complete When:
- Real image capture works with existing pytapo integration
- Images save to C:/temp/ with proper naming
- No existing functionality broken

### ✅ Phase 2 Complete When:
- Base64 encoding works for multimodal LLMs
- Claude Desktop can receive and analyze images
- Analysis presets system functional

### ✅ Phase 3 Complete When:
- Security scanning detects threats effectively
- Multi-camera support framework ready
- Performance acceptable for real-time use

### ✅ Project Complete When:
- Sandra can analyze her schnitzel quality! 🍖
- Benny monitoring works reliably 🐕
- Security scanning provides useful threat detection 🛡️
- DXT packaging still works correctly 📦

---

## Risk Mitigation

### Preserve Existing Functionality
- **DO NOT** modify existing working tools
- **ADD** new tools alongside existing ones
- **TEST** existing functionality after each phase

### Handle Edge Cases
- **Camera disconnection** during image capture
- **Large image files** that exceed memory limits
- **Network timeouts** during real-time analysis
- **File system permissions** for C:/temp/ access

### Performance Considerations
- **Image compression** before base64 encoding
- **Async processing** for multi-camera scenarios
- **Memory management** for large image batches
- **Error recovery** for failed captures

---

## Implementation Notes for Windsurf

### Starting Point
The codebase is **production-ready** with good architecture. Focus on **adding features** rather than rewriting.

### Key Files to Modify
1. `src/devices_mcp/server_v2.py` - Main enhancement target
2. `pyproject.toml` - Add dependencies
3. `tests/test_server_v2.py` - Add test coverage
4. `README.md` - Update documentation

### Key Files to CREATE
1. `src/devices_mcp/presets.py` - Analysis presets
2. `docs/MULTIMODAL_USAGE.md` - Usage examples

### Testing Approach
1. **Start with mocked tests** - Verify structure
2. **Progress to real camera tests** - Validate integration
3. **Final Claude Desktop integration** - Complete workflow

---

**Ready for Implementation! This plan preserves all existing functionality while adding the multimodal capabilities from the artifact specification.** 🎯
