
logger = logging.getLogger(__name__)

"""Test script for DINOv3 integration."""

import
import logging
 asyncio
import sys
from pathlib import Path

# Add the project root to the path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from devices_mcp.vision import DINOv3Processor


async def test_dinov3():
    """Test DINOv3 feature extraction and similarity."""
    logger.info("Initializing DINOv3 model...")
    processor = DINOv3Processor(model_name="facebook/dinov2-base")

    # Example images (replace with your own)
    image_path1 = "examples/images/cat.jpg"
    image_path2 = "examples/images/dog.jpg"

    # Check if images exist
    if not Path(image_path1).exists() or not Path(image_path2).exists():
        logger.info(f"Please add some test images to {Path('examples/images').absolute()}")
        return

    logger.info("Extracting features...")
    features1 = await processor.extract_features(image_path1)
    features2 = await processor.extract_features(image_path2)

    logger.info(f"Feature dimensions: {features1.shape}")

    # Calculate similarity
    cos = torch.nn.CosineSimilarity(dim=1, eps=1e-6)
    similarity = cos(features1, features2).item()
    similarity = (similarity + 1) / 2  # Convert to 0-1 range

    logger.info(f"Similarity between images: {similarity:.4f}")

    # Test finding similar images
    logger.info("\nTesting similar image search...")
    search_dir = "examples/images"
    if Path(search_dir).exists():
        similar = await processor.find_similar(
            query_image=image_path1,
            image_paths=list(Path(search_dir).glob("*.jpg")),
            top_k=3,
        )
        logger.info("\nMost similar images:")
        for i, item in enumerate(similar, 1):
            logger.info(f"{i}. {item['path']} (similarity: {item['similarity']:.4f})")


if __name__ == "__main__":
    import torch

    asyncio.run(test_dinov3())
