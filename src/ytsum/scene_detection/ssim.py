from pathlib import Path
from time import time
from typing import List, Optional

import cv2
from numpy.typing import NDArray
from skimage.metrics import structural_similarity
from tqdm import tqdm
from ytsum.scene_detection.common import SceneDetectionResult, SceneDetector, SceneInfo
from ytsum.utils import format_elapsed_time


class StructuralSimilaritySceneDetector(SceneDetector):
    def __init__(
        self,
        threshold: float,
        min_scene_length_secs: int,
        sample_interval_secs: float,
        show_progress: bool = True,
    ) -> None:
        self._threshold: float = threshold
        self._min_scene_length_secs: int = min_scene_length_secs
        self._sample_interval_secs: float = sample_interval_secs
        self._show_progress: bool = show_progress

    def run(self, video_file_path: Path) -> SceneDetectionResult:
        start_time = time()

        video: cv2.VideoCapture = cv2.VideoCapture(str(video_file_path))

        if not video.isOpened():
            raise ValueError("Error opening video file")

        scenes: List[SceneInfo] = self._detect_scenes_using_ssim(video=video)

        end_time = time()
        elapsed_time_str = format_elapsed_time(start_time=start_time, end_time=end_time)

        return SceneDetectionResult(
            video_file_path=str(video_file_path),
            scene_count=len(scenes),
            scenes=scenes,
            frame_rate_secs=video.get(cv2.CAP_PROP_FPS),
            min_scene_length_secs=self._min_scene_length_secs,
            min_scene_length_frames=0,
            adaptive_threshold=self._threshold,
            min_content_val=0,
            detector_name="ssim",
            processing_time_human=elapsed_time_str,
            processing_time_ms=(end_time - start_time) * 1000,
        )

    def _detect_scenes_using_ssim(self, video: cv2.VideoCapture) -> List[SceneInfo]:
        scenes: List[SceneInfo] = []
        prev_frame: Optional[NDArray] = None
        frame_count: int = 0
        scene_start_frame: int = 0
        scene_start_time: float = 0.0

        fps: float = video.get(cv2.CAP_PROP_FPS)
        frame_interval: int = int(fps * self._sample_interval_secs)
        min_scene_length_frames: int = int(fps * self._min_scene_length_secs)
        total_frames: int = int(video.get(cv2.CAP_PROP_FRAME_COUNT))

        pbar = (
            tqdm(total=total_frames, desc="Detecting Scenes", unit="frame")
            if self._show_progress
            else None
        )

        while True:
            ret, frame = video.read()
            if not ret:
                break

            frame_count += 1
            frame_time_ms = video.get(cv2.CAP_PROP_POS_MSEC)

            if frame_count % frame_interval == 0:
                if prev_frame is None or self._images_differ(
                    img1=prev_frame, img2=frame
                ):
                    if frame_count - scene_start_frame >= min_scene_length_frames:
                        scenes.append(
                            SceneInfo(
                                index=len(scenes),
                                start_time=self._format_time(scene_start_time),
                                end_time=self._format_time(frame_time_ms),
                                start_frame=scene_start_frame,
                                end_frame=frame_count,
                            )
                        )
                        scene_start_frame = frame_count
                        scene_start_time = frame_time_ms

                prev_frame = frame

            if pbar:
                pbar.update(1)
            # End of while loop

        if pbar:
            pbar.close()
        video.release()

        return scenes

    def _images_differ(self, img1: NDArray, img2: NDArray) -> bool:
        """
        Determine if two images differ significantly using SSIM.

        This method calculates the Structural Similarity Index (SSIM) between two images
        and compares it to the threshold to determine if they are significantly different.

        Args:
            img1 (numpy.typing.NDArray): First image for comparison.
            img2 (numpy.typing.NDArray): Second image for comparison.

        Returns:
            bool: True if the images differ significantly, False otherwise.
        """
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        similarity_index = structural_similarity(im1=gray1, im2=gray2)

        return similarity_index < self._threshold

    def _format_time(self, time_ms: float) -> str:
        total_seconds = int(time_ms / 1000)
        milliseconds = int(time_ms % 1000)
        hours, rem = divmod(total_seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
