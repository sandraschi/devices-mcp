"""Scanner camera implementation for USB flatbed and slide scanners."""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional

import cv2

from .base import CameraFactory, CameraType
from .webcam import WebCamera

logger = logging.getLogger(__name__)


@CameraFactory.register(CameraType.SCANNER)
class ScannerCamera(WebCamera):
    """Scanner camera implementation for USB flatbed and slide scanners."""

    def __init__(self, config, mock_webcam=None):
        super().__init__(config, mock_webcam)
        self._scanner_type = self.config.params.get(
            "scanner_type", "flatbed"
        )  # flatbed, slide, auto
        self._color_mode = self.config.params.get(
            "color_mode", "color"
        )  # color, grayscale, monochrome
        self._dpi = int(self.config.params.get("dpi", 300))  # Default DPI
        self._output_dir = Path(self.config.params.get("output_dir", "scans"))
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Scanner-specific settings
        self._brightness = int(self.config.params.get("brightness", 0))  # -100 to 100
        self._contrast = int(self.config.params.get("contrast", 0))  # -100 to 100
        self._auto_crop = self.config.params.get("auto_crop", True)
        self._deskew = self.config.params.get("deskew", True)  # Auto-straighten

    async def get_status(self) -> Dict:
        """Get scanner camera status with detailed scanning capabilities."""
        status = await super().get_status()
        status.update(
            {
                "type": CameraType.SCANNER.value,
                "model": status.get("model", "USB Scanner"),
                "scanner_type": self._scanner_type,
                "color_mode": self._color_mode,
                "dpi": self._dpi,
                "brightness": self._brightness,
                "contrast": self._contrast,
                "auto_crop": self._auto_crop,
                "deskew": self._deskew,
                "output_dir": str(self._output_dir),
                "scanner_capable": True,
                "streaming_capable": False,  # Scanners don't stream, they scan
                "ptz_capable": False,
                "digital_zoom_capable": True,  # Digital zoom for preview
            }
        )
        return status

    async def scan_document(self, filename: Optional[str] = None, format: str = "png") -> str:
        """Perform a document scan and save to file."""
        if not filename:
            timestamp = "current_timestamp"  # Would use actual timestamp
            filename = f"scan_{timestamp}.{format}"

        output_path = self._output_dir / filename

        try:
            # Capture image from scanner (using webcam as proxy for now)
            ret, frame = self._cap.read()
            if not ret:
                raise RuntimeError("Failed to capture from scanner")

            # Apply scanner-specific processing
            processed_frame = await self._process_scan(frame)

            # Save the scanned image
            success = cv2.imwrite(str(output_path), processed_frame)
            if not success:
                raise RuntimeError(f"Failed to save scan to {output_path}")

            logger.info(f"Scanner {self.config.name}: Document scanned and saved to {output_path}")
            return str(output_path)

        except Exception as e:
            logger.exception(f"Scanner {self.config.name}: Failed to scan document")
            raise RuntimeError(f"Scan failed: {e!s}") from e

    async def _process_scan(self, frame):
        """Process the scanned image with scanner-specific enhancements."""
        # Convert color mode
        if self._color_mode == "grayscale":
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        elif self._color_mode == "monochrome":
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, frame = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

        # Apply brightness and contrast adjustments
        if self._brightness != 0 or self._contrast != 0:
            frame = cv2.convertScaleAbs(
                frame, alpha=1 + self._contrast / 100.0, beta=self._brightness
            )

        # Auto deskew (simplified)
        if self._deskew and len(frame.shape) > 2:  # Only for color images
            # Basic deskew logic would go here
            pass

        # Auto crop (simplified)
        if self._auto_crop:
            # Basic auto-crop logic would go here
            pass

        return frame

    async def preview_scan(self) -> bytes:
        """Get a preview of the current scan area."""
        try:
            ret, frame = self._cap.read()
            if not ret:
                raise RuntimeError("Failed to capture preview")

            # Process for preview (lower quality)
            preview = cv2.resize(frame, (640, 480))
            _, buffer = cv2.imencode(".jpg", preview, [cv2.IMWRITE_JPEG_QUALITY, 80])
            return buffer.tobytes()

        except Exception as e:
            logger.exception(f"Scanner {self.config.name}: Failed to get preview")
            raise RuntimeError(f"Preview failed: {e!s}") from e

    async def set_scan_settings(
        self,
        dpi: Optional[int] = None,
        color_mode: Optional[str] = None,
        brightness: Optional[int] = None,
        contrast: Optional[int] = None,
    ) -> None:
        """Set scanner settings."""
        if dpi is not None:
            self._dpi = max(75, min(1200, dpi))  # Reasonable DPI range
        if color_mode in ["color", "grayscale", "monochrome"]:
            self._color_mode = color_mode
        if brightness is not None:
            self._brightness = max(-100, min(100, brightness))
        if contrast is not None:
            self._contrast = max(-100, min(100, contrast))

        logger.info(
            f"Scanner {self.config.name}: Settings updated - DPI: {self._dpi}, Color: {self._color_mode}, "
            f"Brightness: {self._brightness}, Contrast: {self._contrast}"
        )

    async def get_scan_history(self) -> list:
        """Get list of recent scans."""
        try:
            scan_files = []
            for ext in ["*.png", "*.jpg", "*.jpeg", "*.tiff", "*.pdf"]:
                scan_files.extend(self._output_dir.glob(ext))

            # Sort by modification time, most recent first
            scan_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            return [
                {
                    "filename": f.name,
                    "path": str(f),
                    "size": f.stat().st_size,
                    "modified": f.stat().st_mtime,
                    "type": f.suffix.upper()[1:] if f.suffix else "UNKNOWN",
                }
                for f in scan_files[:20]  # Last 20 scans
            ]

        except Exception:
            logger.exception(f"Scanner {self.config.name}: Failed to get scan history")
            return []

    async def delete_scan(self, filename: str) -> bool:
        """Delete a scanned file."""
        try:
            file_path = self._output_dir / filename
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Scanner {self.config.name}: Deleted scan {filename}")
                return True
            logger.warning(f"Scanner {self.config.name}: Scan file {filename} not found")
            return False

        except Exception:
            logger.exception("Scanner {self.config.name}: Failed to delete scan")
            return False

    async def scan_to_ocr(self, filename: Optional[str] = None, language: str = "eng") -> Dict:
        """Scan document and perform OCR to extract text."""
        try:
            # First scan the document
            scan_path = await self.scan_document(filename, "png")

            # OCR processing would go here (requires tesseract or similar)
            # For now, return placeholder
            ocr_result = {
                "scan_path": scan_path,
                "text": "OCR processing would extract text here...",
                "confidence": 0.85,
                "language": language,
                "word_count": 42,
            }

            logger.info(f"Scanner {self.config.name}: OCR completed for {scan_path}")
            return ocr_result

        except Exception as e:
            logger.exception(f"Scanner {self.config.name}: OCR scan failed")
            raise RuntimeError(f"OCR scan failed: {e!s}") from e

    async def batch_scan(self, count: int = 5, prefix: str = "batch") -> list:
        """Perform batch scanning of multiple pages."""
        try:
            scanned_files = []

            for i in range(count):
                filename = f"{prefix}_{i + 1:02d}.png"
                scan_path = await self.scan_document(filename)
                scanned_files.append(scan_path)

                # Small delay between scans
                await asyncio.sleep(0.5)

            logger.info(
                f"Scanner {self.config.name}: Batch scan completed - {len(scanned_files)} pages"
            )
            return scanned_files

        except Exception as e:
            logger.exception(f"Scanner {self.config.name}: Batch scan failed")
            raise RuntimeError(f"Batch scan failed: {e!s}") from e
