from pathlib import Path
from time import time
from typing import List, Tuple

from scenedetect import AdaptiveDetector, FrameTimecode, VideoStream, detect, open_video
from ytsum.scene_detection.common import SceneDetectionResult, SceneDetector, SceneInfo


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


class AdaptiveSceneDetector(SceneDetector):
    def __init__(
        self,
        adaptive_threshold: float,
        min_scene_length_secs: int,
        min_content_value: float,
    ):
        self._adaptive_threshold = adaptive_threshold
        self._min_scene_length_secs = min_scene_length_secs
        self._min_content_value = min_content_value

    def run(self, video_file_path: Path) -> SceneDetectionResult:
        start_time = time()

        video_stream: VideoStream = open_video(str(video_file_path))

        min_scene_length_frames = self._min_scene_length_secs * video_stream.frame_rate

        detector = AdaptiveDetector(
            adaptive_threshold=self._adaptive_threshold,
            min_content_val=self._min_content_value,
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
            min_scene_length_secs=self._min_scene_length_secs,
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

        return result