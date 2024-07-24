import tempfile
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

from ytsum.storage.common import BlobStorage
from ytsum.youtube import YouTubeVideoDownloader


class YouTubeVideoDownloadProcessorResult(BaseModel):
    video_id: str
    download_result: int = Field(default=0)
    error_message: Optional[str] = Field(default=None)
    saved_file_paths: List[str] = Field(default_factory=list)

    @property
    def failed(self) -> bool:
        return self.error_message is not None

    @property
    def succeeded(self) -> bool:
        return self.error_message is None


class YouTubeVideoDownloadProcessor:
    def __init__(self, video_id: str, storage: BlobStorage):
        self._video_id = video_id

        self._storage = storage

    async def run(self) -> YouTubeVideoDownloadProcessorResult:
        await self._storage.start()

        output = YouTubeVideoDownloadProcessorResult(video_id=self._video_id)

        async for fp in self._storage.list_files(path_prefix=self._video_id):
            output.saved_file_paths.append(fp)

        if len(output.saved_file_paths) == 0:
            video_url = f"https://www.youtube.com/watch?v={self._video_id}"
            with tempfile.TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir)
                downloader = YouTubeVideoDownloader(
                    url=video_url, output_dir=output_dir
                )
                download_result = downloader.run()

                if download_result != 0:
                    output.download_result = download_result
                    output.error_message = (
                        f"Failed to download YouTube files from {video_url}."
                    )
                    return output

                files = list(output_dir.glob("*"))
                if not files:
                    output.error_message = "No files found after download."
                    return output

                uploaded_file_paths = await self._upload_files(files=files)
                output.saved_file_paths.extend(uploaded_file_paths)

        await self._storage.shutdown()

        return output

    async def _upload_files(self, files: list[Path]) -> List[str]:
        uploaded_file_paths: List[str] = []
        for file_path in files:
            destination_path = f"{self._video_id}/{file_path.name}"
            await self._storage.save_file(
                src_file_path=file_path,
                destination_path=destination_path,
            )
            uploaded_file_paths.append(destination_path)
        return uploaded_file_paths
