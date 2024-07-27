from datetime import datetime
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field
from ytsum.scene_detection.common import SceneDetectionResult, SceneInfo


class AnnotatedSceneInfo(BaseModel):
    start_time: str
    end_time: str


class VideoSceneAnnotation(BaseModel):
    video_file_path: str = Field(description="The path to the video file.")
    frame_rate_secs: float = Field(
        description="The frame rate of the video in seconds."
    )
    scenes: List[AnnotatedSceneInfo] = Field(
        default_factory=list, description="The annotated scenes in the video."
    )


class SceneDetectorEvaluationResult(BaseModel):
    video_file_path: str
    min_scene_length_secs: int
    adaptive_threshold: float
    min_content_val: int
    accuracy: float
    precision: float
    recall: float
    f1_score: float


def parse_time(time_str: str) -> datetime:
    """
    Parse a time string in the format 'HH:MM:SS.mmm'.

    Args:
        time_str (str): The time string to parse.

    Returns:
        datetime.datetime: The parsed time as a datetime object.

    Raises:
        ValueError: If the time string is not in the correct format.
    """
    try:
        return datetime.strptime(time_str, "%H:%M:%S.%f")
    except ValueError:
        raise ValueError(
            f"Invalid time format: {time_str}. Expected format: HH:MM:SS.mmm"
        )


def time_difference_seconds(time1: str, time2: str) -> float:
    """
    Calculate the difference between two time strings in seconds.

    Args:
        time1 (str): The first time string.
        time2 (str): The second time string.

    Returns:
        float: The difference in seconds.
    """
    t1 = parse_time(time1)
    t2 = parse_time(time2)
    return abs((t2 - t1).total_seconds())


class SceneDetectionEvaluator:
    def __init__(self, tolerance_secs: float):
        self._tolerance_secs = tolerance_secs

    def run(
        self,
        annotation: VideoSceneAnnotation,
        result: SceneDetectionResult,
    ) -> SceneDetectorEvaluationResult:
        if Path(annotation.video_file_path) != Path(result.video_file_path):
            raise ValueError("Video file paths in annotation and result do not match.")

        correct_count = 0
        total_scenes = len(annotation.scenes)

        for annotated_scene in annotation.scenes:
            for detected_scene in result.scenes:
                if self._is_scene_match(annotated_scene, detected_scene):
                    correct_count += 1
                    break

        accuracy = correct_count / total_scenes * 100 if total_scenes > 0 else 0

        # Additional metrics
        precision = correct_count / len(result.scenes) if len(result.scenes) > 0 else 0
        recall = correct_count / total_scenes if total_scenes > 0 else 0
        f1_score = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0
        )

        return SceneDetectorEvaluationResult(
            video_file_path=annotation.video_file_path,
            min_scene_length_secs=result.min_scene_length_secs,
            adaptive_threshold=result.adaptive_threshold,
            min_content_val=result.min_content_val,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
        )

    def _is_scene_match(
        self,
        annotated_scene: AnnotatedSceneInfo,
        detected_scene: SceneInfo,
    ) -> bool:
        """
        Check if a detected scene matches an annotated scene within the given tolerance.

        Args:
            annotated_scene (AnnotatedSceneInfo): The ground truth annotated scene.
            detected_scene (SceneInfo): The detected scene from the algorithm.
            tolerance_secs (float): The tolerance in seconds for matching scenes.

        Returns:
            bool: True if the scenes match within the tolerance, False otherwise.
        """
        start_diff = time_difference_seconds(
            annotated_scene.start_time, detected_scene.start_time
        )
        end_diff = time_difference_seconds(
            annotated_scene.end_time, detected_scene.end_time
        )
        return start_diff <= self._tolerance_secs and end_diff <= self._tolerance_secs
