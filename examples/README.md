# DINOv3 Integration Examples

This directory contains examples for using the DINOv3 integration with the Devices MCP server.

## Prerequisites

1. Install the required dependencies:
   ```bash
   pip install -r ../requirements-vision.txt
   ```

2. Add some test images to the `examples/images` directory.

## Examples

### 1. Basic Feature Extraction

```python
from devices_mcp.vision import DINOv3Processor
import asyncio

async def main():
    # Initialize the processor
    processor = DINOv3Processor()

    # Extract features from an image
    features = await processor.extract_features("path/to/your/image.jpg")
    print(f"Feature vector shape: {features.shape}")

asyncio.run(main())
```

### 2. Find Similar Images

```python
from devices_mcp.vision import DINOv3Processor
import asyncio
from pathlib import Path

async def main():
    # Initialize the processor
    processor = DINOv3Processor()

    # Find similar images
    similar = await processor.find_similar(
        query_image="path/to/query.jpg",
        image_paths=list(Path("path/to/search/dir").glob("*.jpg")),
        top_k=5
    )

    # Print results
    for i, item in enumerate(similar, 1):
        print(f"{i}. {item['path']} (similarity: {item['similarity']:.4f})")

asyncio.run(main())
```

### 3. Using with TapoCameraServer

```python
from devices_mcp import TapoCameraServer
import asyncio

async def main():
    # Initialize the server
    server = TapoCameraServer({
        "host": "your_camera_ip",
        "username": "your_username",
        "password": "your_password"
    })

    # Capture and analyze an image with DINOv3
    result = await server.capture_still({
        "analyze": True,
        "advanced_analysis": True  # Enable DINOv3 analysis
    })

    print("Analysis results:", result)

asyncio.run(main())
```

## Available Models

The following DINOv3 model variants are available:

- `facebook/dinov2-small` (21M parameters)
- `facebook/dinov2-base` (86M parameters) - Default
- `facebook/dinov2-large` (300M parameters)

## Performance Notes

- The first run will download the model weights (300MB-1.2GB depending on the model)
- Processing time depends on your hardware (faster with CUDA)
- For production use, consider using a dedicated GPU for better performance

## Troubleshooting

1. **Out of Memory Errors**: Try using a smaller model variant
2. **Download Errors**: Check your internet connection and proxy settings
3. **CUDA Errors**: Make sure you have compatible CUDA drivers installed if using GPU
