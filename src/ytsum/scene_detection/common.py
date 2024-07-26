from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field


class SceneInfo(BaseModel):
    index: int
    start_time: str
    end_time: str
    start_frame: int
    end_frame: int


class SceneDetectionResult(BaseModel):
    video_file_path: str
    scene_count: int
    frame_rate_secs: float

    min_scene_length_secs: int = Field(
        default=2, description="The minimum scene length in seconds."
    )

    min_scene_length_frames: int = Field(
        description="The minimum scene length in frames."
    )
    adaptive_threshold: float = Field(
        description="The adaptive threshold used for scene detection."
    )
    scenes: List[SceneInfo] = Field(default_factory=list)
    min_content_val: int = Field(
        description="The minimum content value used for scene detection."
    )
    processing_time_human: str = Field(
        description="The time taken to process the video in human-readable format."
    )
    processing_time_ms: float = Field(
        description="The time taken to process the video in milliseconds."
    )


class SceneDetector(ABC):
    @abstractmethod
    def run(self, video_file_path: Path) -> SceneDetectionResult:
        raise NotImplementedError
