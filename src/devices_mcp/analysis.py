"""Advanced image analysis tools using DINOv3."""

from pathlib import Path
from typing import Dict, List, Optional, Union

from .vision.dinov3 import DINOv3Processor


class ImageAnalyzer:
    """Advanced image analysis using DINOv3."""

    def __init__(self, model_name: str = "facebook/dinov2-base"):
        """Initialize the image analyzer.

        Args:
            model_name: Name of the DINOv3 model variant to use.
        """
        self.model_name = model_name
        self.processor = DINOv3Processor(model_name)

    async def analyze_image(
        self, image_path: Union[str, Path], features_only: bool = False
    ) -> Dict[str, any]:
        """Analyze an image using DINOv3.

        Args:
            image_path: Path to the image file or PIL Image
            features_only: If True, only return the feature vector

        Returns:
            Dictionary containing analysis results
        """
        try:
            # Extract features
            features = self.processor.extract_features(image_path)

            if features_only:
                return {
                    "status": "success",
                    "features": features.cpu().numpy().tolist(),
                    "feature_dim": features.shape[-1],
                }

            # For now, just return basic info with features
            # In a real implementation, you might want to add more analysis
            return {
                "status": "success",
                "analysis": {
                    "feature_dim": features.shape[-1],
                    "has_objects": True,  # Placeholder
                    "is_high_quality": True,  # Placeholder
                },
                "features": features.cpu().numpy().tolist(),
            }

        except Exception as e:
            return {"status": "error", "message": f"Image analysis failed: {e!s}"}

    async def find_similar_images(
        self,
        query_image: Union[str, Path],
        search_dir: Union[str, Path],
        extensions: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> Dict[str, any]:
        """Find similar images in a directory.

        Args:
            query_image: Path to the query image
            search_dir: Directory to search for similar images
            extensions: List of image extensions to consider (e.g., ['.jpg', '.png'])
            top_k: Number of similar images to return

        Returns:
            Dictionary containing similar images and their similarity scores
        """
        if extensions is None:
            extensions = [".jpg", ".jpeg", ".png", ".bmp"]

        # Get list of image files
        search_path = Path(search_dir)
        if not search_path.exists() or not search_path.is_dir():
            return {
                "status": "error",
                "message": f"Search directory not found: {search_dir}",
            }

        image_paths = []
        for ext in extensions:
            image_paths.extend(list(search_path.glob(f"*{ext}")))
            image_paths.extend(list(search_path.glob(f"*{ext.upper()}")))

        if not image_paths:
            return {
                "status": "error",
                "message": f"No images found in {search_dir} with extensions: {extensions}",
            }

        try:
            # Find similar images
            similar = self.processor.find_similar(
                query_image=query_image, image_paths=image_paths, top_k=top_k
            )

            return {
                "status": "success",
                "query_image": str(query_image),
                "search_dir": str(search_dir),
                "similar_images": similar,
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to find similar images: {e!s}",
            }


# Global instance for easy access
image_analyzer = ImageAnalyzer()
