import tempfile
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field
from ytsum.storage.common import BlobStorage
from ytsum.video import VideoImageExtractor


class VideoFrameExtractorResult(BaseModel):
    video_id: str
    error_message: Optional[str] = Field(default=None)
    saved_file_paths: List[str] = Field(default_factory=list)

    @property
    def failed(self) -> bool:
        return self.error_message is not None

    @property
    def succeeded(self) -> bool:
        return self.error_message is None


class VideoFrameExtractor:
    def __init__(
        self,
        video_id: str,
        video_file_path: str,
        input_storage: BlobStorage,
        output_storage: BlobStorage,
    ) -> None:
        self._video_id = video_id
        self._video_file_path = video_file_path
        self._input_storage = input_storage
        self._output_storage = output_storage

    async def run(self) -> VideoFrameExtractorResult:
        await self._output_storage.start()

        result = VideoFrameExtractorResult(video_id=self._video_id)

        # Check if we already have extracted frames
        async for fp in self._output_storage.list_files(path_prefix=self._video_id):
            result.saved_file_paths.append(fp)

        if len(result.saved_file_paths) > 0:
            print(
                (
                    f"{len(result.saved_file_paths)} files already exist for video: "
                    f"{self._video_id}. Skipping extraction."
                )
            )
            return result

        # In case we don't have extracted frames.
        # First, check if the video file exists
        await self._input_storage.start()
        if not await self._input_storage.exists(self._video_file_path):
            result.error_message = f"Video file not found: {self._video_file_path}"
            return result

        # Here, we know that the video file exists,
        # so we can start the frame extraction process
        await self._begin_processing(result=result)

        return result

    async def _begin_processing(self, result: VideoFrameExtractorResult) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            local_video_file_path = Path(temp_dir) / "input" / "video-file.mp4"
            await self._input_storage.download_file(
                src_file_path=self._video_file_path,
                destination_path=local_video_file_path,
            )

            output_dir = Path(temp_dir) / "output"

            extractor = VideoImageExtractor(
                video_path=local_video_file_path,
                output_dir=output_dir,
                threshold=0.95,
                sample_interval_secs=1.0,
            )
            extractor.run()

            result.saved_file_paths = await self._upload_files(directory=output_dir)

    async def _upload_files(self, directory: Path) -> List[str]:
        uploaded_file_paths = []
        for file_path in directory.iterdir():
            if file_path.is_file():
                dst_file_path = f"{self._video_id}/{file_path.name}"
                await self._output_storage.save_file(
                    src_file_path=file_path,
                    destination_path=dst_file_path,
                )
                uploaded_file_paths.append(dst_file_path)
        return uploaded_file_paths
