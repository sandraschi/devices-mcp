"""
Quality and performance related Pydantic models for PlexMCP.

This module contains models related to transcoding, bandwidth, and performance.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QualityProfile(BaseModel):
    """Media quality profile for transcoding optimization"""

    name: str = Field(description="Profile name (4K, 1080p, 720p, mobile, etc)")
    max_bitrate: int = Field(description="Maximum bitrate in kbps")
    resolution: str = Field(description="Target resolution (e.g., 1920x1080)")
    codec: str = Field(description="Video codec (h264, h265, etc)")
    container: str = Field(description="Container format (mp4, mkv, etc)")
    audio_codec: Optional[str] = Field(description="Audio codec preference")
    subtitle_format: Optional[str] = Field(description="Subtitle format")


class TranscodingStatus(BaseModel):
    """Current transcoding operation status"""

    active_sessions: int = Field(description="Number of active transcoding sessions")
    queue_length: int = Field(description="Transcoding queue length")
    cpu_usage: float = Field(description="CPU usage percentage for transcoding")
    memory_usage: float = Field(description="Memory usage for transcoding processes")
    disk_io: float = Field(description="Disk I/O usage for transcoding")
    estimated_completion: Optional[int] = Field(description="Estimated completion time in seconds")
    current_jobs: List[Dict[str, Any]] = Field(description="Details of current transcoding jobs")
    recommendations: List[str] = Field(description="Performance optimization recommendations")


class BandwidthAnalysis(BaseModel):
    """Network bandwidth usage analysis"""

    time_period: str = Field(description="Analysis time period")
    total_bandwidth_gb: float = Field(description="Total bandwidth used in GB")
    peak_usage_mbps: float = Field(description="Peak usage in Mbps")
    average_usage_mbps: float = Field(description="Average usage in Mbps")
    concurrent_streams: int = Field(description="Peak concurrent streams")
    transcoding_overhead: float = Field(description="Bandwidth overhead from transcoding")
    client_breakdown: List[Dict[str, Any]] = Field(description="Bandwidth usage by client")
    quality_distribution: Dict[str, int] = Field(description="Stream quality distribution")
    optimization_suggestions: List[str] = Field(
        description="Bandwidth optimization recommendations"
    )
    cost_estimate: Optional[float] = Field(description="Estimated cost if using metered connection")
