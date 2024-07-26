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

    min_scene_length_secs = 2
    min_scene_length_frames = min_scene_length_secs * video_stream.frame_rate

    print(
        f"Minimum scene length: {min_scene_length_secs} seconds -> {min_scene_length_frames} frames (at {video_stream.frame_rate} FPS)"
    )

    detector = AdaptiveDetector(
        adaptive_threshold=0.8,
        min_content_val=10,
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
    annotation_file_path.write_text(annotation.model_dump_json(indent=2))


def main() -> None:
    video_dir = Path("data/downloads")

    run_algorithm(video_dir=video_dir / "Onf1UqKPMR4")
    run_algorithm(video_dir=video_dir / "MBdEWLqfdms")
    run_algorithm(video_dir=video_dir / "4gcGkFAG7OA")


if __name__ == "__main__":
    main()
