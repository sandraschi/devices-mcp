"""DINOv3 model integration for advanced image analysis."""

import logging
from typing import Dict, List, Union

import numpy as np
import torch
from PIL import Image

logger = logging.getLogger(__name__)


class DINOv3Processor:
    """Processor for DINOv3 model inference."""

    def __init__(self, model_name: str = "facebook/dinov2-base"):
        """Initialize DINOv3 model.

        Args:
            model_name: Name of the DINOv3 model variant to use.
                       Options: 'facebook/dinov2-small', 'facebook/dinov2-base', 'facebook/dinov2-large'
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_name = model_name
        self.model = None
        self.transform = None

        # Initialize model and transforms
        self._initialize_model()

    def _initialize_model(self):
        """Load the DINOv3 model and initialize transforms."""
        from transformers import AutoImageProcessor, AutoModel

        try:
            # Load model and processor
            self.processor = AutoImageProcessor.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name).to(self.device)
            self.model.eval()

            # Initialize transforms
            from torchvision import transforms

            self.transform = transforms.Compose(
                [
                    transforms.Resize(256, interpolation=transforms.InterpolationMode.BICUBIC),
                    transforms.CenterCrop(224),
                    transforms.ToTensor(),
                    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
                ]
            )

        except Exception as e:
            raise RuntimeError(f"Failed to initialize DINOv3 model: {e!s}") from e

    @torch.no_grad()
    def extract_features(self, image: Union[Image.Image, str, np.ndarray]) -> torch.Tensor:
        """Extract features from an image using DINOv3.

        Args:
            image: Input image (PIL Image, file path, or numpy array)

        Returns:
            torch.Tensor: Extracted features (1, feature_dim)
        """
        if self.model is None:
            raise RuntimeError("Model not initialized. Call _initialize_model() first.")

        # Convert input to PIL Image if needed
        if isinstance(image, str):
            image = Image.open(image).convert("RGB")
        elif isinstance(image, np.ndarray):
            image = Image.fromarray(image)

        # Apply transforms
        image_tensor = self.transform(image).unsqueeze(0).to(self.device)

        # Extract features
        with torch.no_grad():
            outputs = self.model(image_tensor)
            features = outputs.last_hidden_state.mean(dim=1)  # Global average pooling

        return features.cpu()

    def get_similarity(
        self,
        image1: Union[Image.Image, str, np.ndarray],
        image2: Union[Image.Image, str, np.ndarray],
    ) -> float:
        """Calculate cosine similarity between two images.

        Args:
            image1: First image
            image2: Second image

        Returns:
            float: Cosine similarity between the two images (0-1)
        """
        # Extract features
        feat1 = self.extract_features(image1)
        feat2 = self.extract_features(image2)

        # Calculate cosine similarity
        cos = torch.nn.CosineSimilarity(dim=1, eps=1e-6)
        similarity = cos(feat1, feat2).item()

        # Convert to 0-1 range
        return (similarity + 1) / 2

    def find_similar(
        self,
        query_image: Union[Image.Image, str, np.ndarray],
        image_paths: List[str],
        top_k: int = 5,
    ) -> List[Dict[str, float]]:
        """Find most similar images to the query image.

        Args:
            query_image: Query image
            image_paths: List of image paths to search through
            top_k: Number of similar images to return

        Returns:
            List of dictionaries with 'path' and 'similarity' for top_k matches
        """
        # Extract query features
        query_feat = self.extract_features(query_image)

        # Calculate similarities with all images
        similarities = []
        for img_path in image_paths:
            try:
                img_feat = self.extract_features(img_path)
                cos = torch.nn.CosineSimilarity(dim=1, eps=1e-6)
                sim = cos(query_feat, img_feat).item()
                similarities.append((img_path, (sim + 1) / 2))  # Convert to 0-1 range
            except Exception as exc:
                logger.debug("Failed to process image %s: %s", img_path, exc)

        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return [{"path": path, "similarity": float(sim)} for path, sim in similarities[:top_k]]


# Global instance for easy access
dinov3_processor = DINOv3Processor()
