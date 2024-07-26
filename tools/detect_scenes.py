from datetime import datetime
from pathlib import Path
from time import time
from typing import List, Tuple

from pydantic import BaseModel, Field
from scenedetect import AdaptiveDetector, FrameTimecode, VideoStream, detect, open_video


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


def format_elapsed_time(start_time: float, end_time: float) -> str:
    elapsed_seconds: float = end_time - start_time
    minutes_seconds: Tuple[int, float] = divmod(elapsed_seconds, 60)
    minutes: int = int(minutes_seconds[0])
    seconds: int = int(minutes_seconds[1])
    milliseconds: int = int((elapsed_seconds - int(elapsed_seconds)) * 1000)

    parts: List[str] = []
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    if milliseconds > 0:
        parts.append(f"{milliseconds} millisecond{'s' if milliseconds != 1 else ''}")

    if len(parts) > 1:
        return f"{', '.join(parts[:-1])} and {parts[-1]}"
    elif len(parts) == 1:
        return parts[0]
    else:
        return "0 milliseconds"


def _parse_time(time_str: str) -> datetime:
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


def _time_difference_seconds(time1: str, time2: str) -> float:
    """
    Calculate the difference between two time strings in seconds.

    Args:
        time1 (str): The first time string.
        time2 (str): The second time string.

    Returns:
        float: The difference in seconds.
    """
    t1 = _parse_time(time1)
    t2 = _parse_time(time2)
    return abs((t2 - t1).total_seconds())


def _is_scene_match(
    annotated_scene: AnnotatedSceneInfo,
    detected_scene: SceneInfo,
    tolerance_secs: float,
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
    start_diff = _time_difference_seconds(
        annotated_scene.start_time, detected_scene.start_time
    )
    end_diff = _time_difference_seconds(
        annotated_scene.end_time, detected_scene.end_time
    )
    return start_diff <= tolerance_secs and end_diff <= tolerance_secs


def run_eval(
    annotation: VideoSceneAnnotation,
    result: SceneDetectionResult,
    tolerance_secs: float,
) -> None:
    """
    Evaluate the accuracy of the scene detection algorithm.

    Args:
        annotation (VideoSceneAnnotation): The ground truth annotation.
        result (SceneDetectionResult): The result from the scene detection algorithm.
        tolerance_secs (float, optional): The tolerance in seconds for matching scenes.

    Raises:
        ValueError: If the video file paths in the annotation and result don't match.
    """
    if Path(annotation.video_file_path) != Path(result.video_file_path):
        raise ValueError("Video file paths in annotation and result do not match.")

    print(f"\n\nRunning evaluation for {annotation.video_file_path}")

    # Print algorithm parameters
    print("Algorithm Parameters:")
    print(f" - Adaptive Threshold: {result.adaptive_threshold}")
    print(f" - Minimum Content Value: {result.min_content_val}")
    print(f" - Minimum Scene Length: {result.min_scene_length_secs} seconds")

    correct_count = 0
    total_scenes = len(annotation.scenes)

    for annotated_scene in annotation.scenes:
        for detected_scene in result.scenes:
            if _is_scene_match(annotated_scene, detected_scene, tolerance_secs):
                correct_count += 1
                break

    accuracy = correct_count / total_scenes * 100 if total_scenes > 0 else 0
    print(
        f"Correctly detected {correct_count} out of {total_scenes} scenes: {accuracy:.2f}%"
    )

    # Additional metrics
    precision = correct_count / len(result.scenes) if len(result.scenes) > 0 else 0
    recall = correct_count / total_scenes if total_scenes > 0 else 0
    f1_score = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0
    )

    print(f"Precision: {precision:.2f}")
    print(f"Recall: {recall:.2f}")
    print(f"F1 Score: {f1_score:.2f}")


def run_algorithm(video_dir: Path) -> None:
    video_file_paths = list(video_dir.glob("*.mp4"))
    if len(video_file_paths) != 1:
        print(
            f"Expected 1 video file in {video_dir}. But found {len(video_file_paths)} files."
        )
        return

    video_file_path = video_file_paths[0]

    print(f"Detecting scenes in video file: {video_file_path}")

    start_time = time()

    video_stream: VideoStream = open_video(str(video_file_path))

    min_scene_length_secs = 1
    min_scene_length_frames = min_scene_length_secs * video_stream.frame_rate

    print(
        f"Minimum scene length: {min_scene_length_secs} seconds -> {min_scene_length_frames} frames (at {video_stream.frame_rate} FPS)"
    )

    detector = AdaptiveDetector(
        adaptive_threshold=1.5,
        min_content_val=5,
        min_scene_len=min_scene_length_frames,
    )

    scene_list = detect(
        video_path=str(video_file_path),
        detector=detector,
        show_progress=True,
    )

    end_time = time()

    elapsed_time_str = format_elapsed_time(start_time=start_time, end_time=end_time)

    print(f"Found {len(scene_list)} scenes in {elapsed_time_str}.")

    result = SceneDetectionResult(
        video_file_path=str(video_file_path),
        scene_count=len(scene_list),
        frame_rate_secs=video_stream.frame_rate,
        min_scene_length_secs=min_scene_length_secs,
        min_scene_length_frames=min_scene_length_frames,
        adaptive_threshold=detector.adaptive_threshold,
        min_content_val=detector.min_content_val,
        processing_time_human=elapsed_time_str,
        processing_time_ms=(end_time - start_time) * 1000,
    )

    for i, scene in enumerate(scene_list):
        start_frame: FrameTimecode = scene[0]
        end_frame: FrameTimecode = scene[1]

        result.scenes.append(
            SceneInfo(
                index=i,
                start_time=start_frame.get_timecode(),
                end_time=end_frame.get_timecode(),
                start_frame=start_frame.get_frames(),
                end_frame=end_frame.get_frames(),
            )
        )

        scene_starts_at = start_frame.get_timecode()
        scene_ends_at = end_frame.get_timecode()

        print(f"Scene {i + 1}: {scene_starts_at} to {scene_ends_at}")

    result_file_path = video_dir / "scene-detection-result.json"
    result_file_path.write_text(result.model_dump_json(indent=2))

    annotation = VideoSceneAnnotation(
        video_file_path=str(video_file_path),
        frame_rate_secs=video_stream.frame_rate,
        scenes=[
            AnnotatedSceneInfo(start_time=scene.start_time, end_time=scene.end_time)
            for scene in result.scenes
        ],
    )

    annotation_file_path = video_dir / "scene-annotation.json"

    if annotation_file_path.exists():
        annotation = VideoSceneAnnotation.model_validate_json(
            json_data=annotation_file_path.read_text()
        )

        run_eval(annotation=annotation, result=result, tolerance_secs=1.5)


def run_evaluation(video_dir: Path) -> None:
    result_file_path = video_dir / "scene-detection-result.json"
    annotation_file_path = video_dir / "scene-annotation.json"

    if not result_file_path.exists():
        print(f"Scene detection result file not found: {result_file_path}")
        return

    if not annotation_file_path.exists():
        print(f"Scene annotation file not found: {annotation_file_path}")
        return

    result = SceneDetectionResult.model_validate_json(
        json_data=result_file_path.read_text()
    )
    annotation = VideoSceneAnnotation.model_validate_json(
        json_data=annotation_file_path.read_text()
    )

    run_eval(annotation=annotation, result=result, tolerance_secs=1.5)


def main() -> None:
    video_dir = Path("data/downloads")

    # run_algorithm(video_dir=video_dir / "Onf1UqKPMR4")
    # run_algorithm(video_dir=video_dir / "MBdEWLqfdms")
    run_algorithm(video_dir=video_dir / "4gcGkFAG7OA")
    # run_evaluation(video_dir=video_dir / "4gcGkFAG7OA")


if __name__ == "__main__":
    main()
