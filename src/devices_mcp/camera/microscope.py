"""USB Microscope camera implementation."""

import asyncio
import logging

from .base import CameraFactory, CameraType
from .webcam import WebCamera

logger = logging.getLogger(__name__)


@CameraFactory.register(CameraType.MICROSCOPE)
class MicroscopeCamera(WebCamera):
    """USB Microscope camera implementation.

    Extends WebCamera with microscope-specific features:
    - Enhanced focus and zoom controls
    - LED lighting control (if supported)
    - Magnification indicators
    - Microscope-specific resolutions
    """

    def __init__(self, config, mock_webcam=None):
        super().__init__(config, mock_webcam)
        # Microscope-specific settings
        self._magnification = float(self.config.params.get("magnification", 1.0))
        self._focus_mode = self.config.params.get("focus_mode", "auto")  # auto, manual, fixed
        self._led_brightness = int(self.config.params.get("led_brightness", 50))  # 0-100
        self._calibration_factor = float(self.config.params.get("calibration_factor", 1.0))
        # Track active background tasks
        self._active_tasks: set[asyncio.Task] = set()

    async def get_status(self) -> dict:
        """Get microscope camera status with enhanced microscope info."""
        status = await super().get_status()

        # Add microscope-specific status
        status.update(
            {
                "magnification": self._magnification,
                "focus_mode": self._focus_mode,
                "led_brightness": self._led_brightness,
                "calibration_factor": self._calibration_factor,
                "microscope_features": {
                    "focus_control": True,
                    "led_lighting": True,
                    "calibration": True,
                    "measurement": True,
                },
            }
        )

        return status

    async def set_magnification(self, magnification: float) -> bool:
        """Set magnification level (typically 1x to 200x+ for microscopes)."""
        try:
            self._magnification = max(1.0, min(1000.0, magnification))
            logger.info(f"Set microscope magnification to {self._magnification}x")
            return True
        except Exception:
            logger.exception("Failed to set magnification")
            return False

    async def set_led_brightness(self, brightness: int) -> bool:
        """Set LED lighting brightness (0-100)."""
        try:
            self._led_brightness = max(0, min(100, brightness))
            logger.info(f"Set microscope LED brightness to {self._led_brightness}%")
            # TODO: Implement actual LED control if microscope supports it
            return True
        except Exception:
            logger.exception("Failed to set LED brightness")
            return False

    async def calibrate(self, known_distance_pixels: int, actual_distance_mm: float) -> bool:
        """Calibrate microscope for accurate measurements."""
        try:
            self._calibration_factor = actual_distance_mm / known_distance_pixels
            logger.info(f"Calibrated microscope: {self._calibration_factor} mm/pixel")
            return True
        except Exception:
            logger.exception("Failed to calibrate microscope")
            return False

    async def measure_distance(self, pixel_distance: int) -> float | None:
        """Convert pixel distance to actual distance using calibration."""
        try:
            if self._calibration_factor > 0:
                return pixel_distance * self._calibration_factor
            return None
        except Exception:
            logger.exception("Failed to measure distance")
            return None

    async def auto_focus(self) -> bool:
        """Perform auto-focus if supported."""
        try:
            # TODO: Implement auto-focus logic
            # This would typically involve capturing frames at different focus positions
            # and analyzing sharpness/contrast to find optimal focus
            logger.info("Performing auto-focus (not yet implemented)")
            return False
        except Exception:
            logger.exception("Auto-focus failed")
            return False

    def get_microscope_info(self) -> dict:
        """Get detailed microscope information."""
        return {
            "type": "usb_microscope",
            "magnification_range": "1x - 1000x (typical)",
            "focus_modes": ["auto", "manual", "fixed"],
            "lighting": "LED (programmable brightness)",
            "calibration": "pixel-to-mm conversion",
            "measurement_tools": ["distance", "area", "scale"],
            "timelapse_capable": True,
            "plant_monitoring": True,
            "current_magnification": self._magnification,
            "current_led_brightness": self._led_brightness,
            "calibration_factor": self._calibration_factor,
        }

    async def start_timelapse(
        self, interval_minutes: int, duration_hours: int, session_name: str, auto_focus: bool = True
    ) -> dict:
        """Start a time-lapse photography session for plant growth monitoring."""
        import os
        from datetime import datetime, timedelta

        # Calculate session parameters
        interval_seconds = interval_minutes * 60
        total_duration_seconds = duration_hours * 3600
        total_shots = int(total_duration_seconds / interval_seconds)

        session_info = {
            "session_name": session_name,
            "interval_minutes": interval_minutes,
            "duration_hours": duration_hours,
            "total_shots": total_shots,
            "start_time": datetime.now(),
            "end_time": datetime.now() + timedelta(hours=duration_hours),
            "auto_focus": auto_focus,
            "status": "starting",
        }

        # Create session directory
        session_dir = f"data/timelapse/{session_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(session_dir, exist_ok=True)
        session_info["session_dir"] = session_dir

        # Ensure microscope light is on for consistent illumination
        await self.set_led_brightness(80)  # Good brightness for plant photography
        await self.set_focus_mode("auto" if auto_focus else "manual")

        logger.info(
            f"Microscope {self.config.name}: Starting timelapse session '{session_name}' - "
            f"{total_shots} shots over {duration_hours} hours (every {interval_minutes} min)"
        )

        # Start background task
        task = asyncio.create_task(self._run_timelapse(session_info))
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)

        return session_info

    async def _run_timelapse(self, session_info: dict) -> None:
        """Run the timelapse capture loop in background."""
        import time
        from datetime import datetime

        session_name = session_info["session_name"]
        interval_seconds = session_info["interval_minutes"] * 60
        total_shots = session_info["total_shots"]
        session_dir = session_info["session_dir"]
        auto_focus = session_info["auto_focus"]

        session_info["status"] = "running"
        shots_taken = 0

        try:
            while shots_taken < total_shots:
                start_time = time.time()

                # Auto-focus if enabled
                if auto_focus and shots_taken % 10 == 0:  # Re-focus every 10 shots
                    await self.set_focus_mode("auto")
                    await asyncio.sleep(1)  # Allow focus to settle

                # Capture image
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{session_name}_{timestamp}_{shots_taken:04d}.jpg"
                image_path = await self.capture_image(filename, save_path=session_dir)

                logger.info(f"Timelapse {session_name}: Captured shot {shots_taken + 1}/{total_shots} - {image_path}")

                shots_taken += 1
                session_info["shots_taken"] = shots_taken

                # Wait for next interval, accounting for capture time
                elapsed = time.time() - start_time
                wait_time = max(0, interval_seconds - elapsed)
                await asyncio.sleep(wait_time)

            session_info["status"] = "completed"
            logger.info(f"Timelapse {session_name}: Session completed - {shots_taken} shots taken")

        except Exception as e:
            session_info["status"] = "error"
            session_info["error"] = str(e)
            logger.exception(f"Timelapse {session_name}: Session failed")

    async def stop_timelapse(self, session_name: str) -> dict:
        """Stop a running timelapse session."""
        # In a real implementation, we'd need to track running tasks
        # For now, we'll just log and return status
        logger.info(f"Microscope {self.config.name}: Stopping timelapse session '{session_name}'")
        return {
            "session_name": session_name,
            "action": "stopped",
            "message": "Timelapse session stop requested",
        }

    async def get_timelapse_status(self) -> dict:
        """Get status of any running timelapse sessions."""
        # In a real implementation, we'd track active sessions
        return {
            "active_sessions": [],  # Would contain running session info
            "recent_sessions": [],  # Would contain completed session info
            "message": "No timelapse sessions currently tracked",
        }

    async def create_growth_video(
        self,
        session_dir: str,
        output_path: str | None = None,
        fps: int = 30,
        add_timestamp: bool = True,
    ) -> str:
        """Create a time-lapse video from captured images."""
        import glob
        from pathlib import Path

        import cv2

        if not output_path:
            session_name = Path(session_dir).name
            output_path = f"data/timelapse/{session_name}_growth.mp4"

        # Find all images in session directory
        image_pattern = f"{session_dir}/*.jpg"
        image_files = sorted(glob.glob(image_pattern))

        if not image_files:
            raise ValueError(f"No images found in {session_dir}")

        logger.info(f"Creating timelapse video from {len(image_files)} images: {output_path}")

        # Read first image to get dimensions
        first_image = cv2.imread(image_files[0])
        height, width = first_image.shape[:2]

        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        try:
            for image_file in image_files:
                frame = cv2.imread(image_file)

                if add_timestamp:
                    # Add timestamp overlay
                    timestamp = Path(image_file).stem.split("_")[-2]  # Extract timestamp from filename
                    readable_time = f"{timestamp[:8]} {timestamp[8:10]}:{timestamp[10:12]}:{timestamp[12:14]}"
                    cv2.putText(
                        frame,
                        readable_time,
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (255, 255, 255),
                        2,
                    )

                video_writer.write(frame)

            logger.info(f"Timelapse video created: {output_path}")
            return output_path

        finally:
            video_writer.release()

    async def analyze_growth(self, session_dir: str) -> dict:
        """Analyze plant growth patterns from timelapse images."""
        import glob
        from pathlib import Path

        image_files = sorted(glob.glob(f"{session_dir}/*.jpg"))
        analysis = {
            "total_images": len(image_files),
            "session_name": Path(session_dir).name,
            "analysis": {
                "growth_rate": "Not implemented - would analyze pixel changes over time",
                "color_changes": "Not implemented - would track green color development",
                "movement_detection": "Not implemented - would detect subtle movements",
                "health_indicators": "Not implemented - would analyze leaf color/health",
            },
            "recommendations": [
                "Implement computer vision analysis for growth tracking",
                "Add color analysis for plant health monitoring",
                "Include size measurement capabilities",
                "Add automated alerts for growth milestones",
            ],
        }

        logger.info(f"Microscope {self.config.name}: Analyzed growth session {session_dir}")
        return analysis
