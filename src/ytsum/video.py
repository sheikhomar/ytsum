from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from numpy.typing import NDArray


class VideoImageExtractor:
    """A class for extracting significant frames from a video file.

    This class processes a video file and saves frames that differ significantly
    from the previously saved frame, based on a given threshold. It can also
    sample frames at a specified time interval.
    """

    def __init__(
        self,
        video_path: Path,
        output_dir: Path,
        threshold: float = 1000,
        image_format: str = "jpg",
        sample_interval_secs: float = 2.0,
    ) -> None:
        """
        Initialize the VideoImageExtractor.

        Args:
            video_path (Path): Path to the input video file.
            output_dir (Path, optional): Directory to save extracted images.
            threshold (float, optional): Threshold for frame difference. Defaults to 1000.
            image_format (str, optional): Format for saved images. Defaults to 'jpg'.
            sample_interval_secs (float, optional): Time between frame samples in seconds. Defaults to 2.0.
        """

        self._video_path: Path = video_path
        self._output_dir: Path = output_dir
        self._threshold: float = threshold
        self._image_format: str = image_format
        self._sample_interval_secs: float = sample_interval_secs

        self._output_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        """Process the video and extract significant frames.

        This method reads the video file, samples frames at the specified interval,
        compares each sampled frame with the previously saved frame, and saves
        the frame if it differs significantly.

        Raises:
            ValueError: If there's an error opening or reading the video file.
        """

        print("Reading video file...")
        video: cv2.VideoCapture = cv2.VideoCapture(filename=str(self._video_path))

        if not video.isOpened():
            raise ValueError("Error opening video file")

        fps: float = video.get(cv2.CAP_PROP_FPS)
        frame_interval: int = int(fps * self._sample_interval_secs)

        ret: bool = False
        prev_frame: Optional[NDArray] = None
        frame_count: int = 0
        saved_count: int = 0

        while True:
            ret, frame = video.read()
            if not ret:
                break

            frame_count += 1

            if frame_count % frame_interval == 0:
                if prev_frame is None or self._images_differ(
                    img1=prev_frame, img2=frame
                ):
                    self._save_image(image=frame, count=saved_count)
                    prev_frame = frame
                    saved_count += 1

        video.release()
        print(f"Processed {frame_count} frames, saved {saved_count} images.")

    def _images_differ(self, img1: NDArray, img2: NDArray) -> bool:
        """Determine if two images differ significantly.

        This method calculates the Mean Squared Error (MSE) between two images
        and compares it to the threshold to determine if they are significantly different.

        Args:
            img1 (numpy.typing.NDArray): First image for comparison.
            img2 (numpy.typing.NDArray): Second image for comparison.

        Returns:
            bool: True if the images differ significantly, False otherwise.
        """

        err: float = np.sum(
            (img1.astype(dtype="float") - img2.astype(dtype="float")) ** 2
        )
        err /= float(img1.shape[0] * img1.shape[1])
        print(f"Error: {err}")
        return err > self._threshold

    def _save_image(self, image: NDArray, count: int) -> None:
        """Save an image to the output directory.

        Args:
            image (numpy.typing.NDArray): The image to be saved.
            count (int): A counter used in generating the filename.
        """
        filename: str = f"frame-{count:04d}.{self._image_format}"
        filepath: Path = self._output_dir / filename
        cv2.imwrite(filename=str(filepath), img=image)
