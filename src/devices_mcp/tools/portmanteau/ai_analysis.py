"""
AI Analysis Portmanteau Tool
Consolidates all AI-powered analysis operations into a single tool with action-based interface.
Currently supports scene analysis, object detection, and activity recognition.
"""

import logging
from typing import Any, Literal

from fastmcp import FastMCP

_READ_ONLY: dict[str, bool] = {"readonly": True}
_MUTATING: dict[str, bool] = {}
_DESTRUCTIVE: dict[str, bool] = {"destructive": True}

logger = logging.getLogger(__name__)
AI_ANALYSIS_ACTIONS = {
    "analyze_scene": "Analyze camera scene for objects, activities, and context",
    "detect_objects": "Detect objects in camera scene",
    "analyze_activity": "Analyze activities in camera scene",
    "classify_scene": "Classify scene type (indoor/outdoor, day/night, etc.)",
}


def register_ai_analysis_tool(mcp: FastMCP) -> None:
    """Register the AI analysis portmanteau tool."""

    @mcp.tool(annotations=_READ_ONLY)
    async def ai_analysis(
        action: Literal[
            "analyze_scene",
            "detect_objects",
            "analyze_activity",
            "classify_scene",
        ],
        camera_id: str,
        confidence_threshold: float = 0.7,
        analysis_type: str = "comprehensive",
    ) -> dict[str, Any]:
        """
        Comprehensive AI analysis portmanteau tool for computer vision and scene understanding.
        PORTMANTEAU PATTERN RATIONALE:
        Consolidates AI analysis operations into a single interface to reduce tool explosion
        while maintaining full functionality. Supports scene analysis, object detection,
        activity recognition, and contextual insights.
        Args:
            action (Literal, required): The analysis operation to perform. Must be one of:
                - "analyze_scene": Comprehensive scene analysis (objects + activities + context)
                - "detect_objects": Object detection only
                - "analyze_activity": Activity analysis only
                - "classify_scene": Scene classification (indoor/outdoor, day/night, etc.)
            camera_id (str, required): ID of the camera to analyze
            confidence_threshold (float): Minimum confidence threshold (0.0-1.0, default: 0.7)
            include_details (bool): Include detailed analysis results (default: True)
            analysis_type (str): Type of analysis for analyze_scene action (default: "comprehensive")
                - "comprehensive": Full analysis with recommendations
                - "quick": Fast analysis without recommendations
                - "detailed": Detailed analysis with all metadata
        Returns:
            dict[str, Any]: Dictionary containing:
                - success (bool): Boolean indicating if analysis succeeded
                - action (str): The action that was performed
                - data (dict): Analysis results (scene_type, objects, activities, recommendations, etc.)
                - error (str | None): Error message if success is False
        Examples:
            # Comprehensive scene analysis
            result = await ai_analysis(action="analyze_scene", camera_id="living_room_cam")
            # Quick object detection
            result = await ai_analysis(action="detect_objects", camera_id="kitchen_cam", confidence_threshold=0.8)
            # Activity analysis only
            result = await ai_analysis(action="analyze_activity", camera_id="front_door_cam")
            # Scene classification
            result = await ai_analysis(action="classify_scene", camera_id="garden_cam")
        """
        try:
            if action not in AI_ANALYSIS_ACTIONS:
                return {
                    "success": False,
                    "message": f"Invalid action '{action}'. Available: {list(AI_ANALYSIS_ACTIONS.keys())}",
                }
            logger.info(f"Executing AI analysis action: {action} on camera {camera_id}")
            # Import the scene analyzer tool
            from ...tools.ai.scene_analyzer import SceneAnalyzerTool

            analyzer = SceneAnalyzerTool()
            # Map actions to scene analyzer parameters
            if action == "analyze_scene":
                include_objects = True
                include_activities = True
            elif action == "detect_objects":
                include_objects = True
                include_activities = False
            elif action == "analyze_activity":
                include_objects = False
                include_activities = True
            elif action == "classify_scene":
                include_objects = False
                include_activities = False
            # Execute analysis
            result = await analyzer.execute(
                camera_id=camera_id,
                analysis_type=analysis_type,
                include_objects=include_objects,
                include_activities=include_activities,
                confidence_threshold=confidence_threshold,
            )
            # Format result for portmanteau consistency
            return {
                "success": result.get("success", False),
                "action": action,
                "data": result.get("analysis", {}),
                "error": result.get("error"),
            }
        except Exception as e:
            logger.exception("Error in AI analysis action '{action}':")
            return {
                "success": False,
                "message": f"Failed to execute AI analysis '{action}': {e!s}",
                "error": f"Failed to execute AI analysis '{action}': {e!s}",
            }
