import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from ytsum.repositories.video import VideoMetadata, VideoRepository, YoutubeDLVideoInfo
from ytsum.storage.common import BlobStorage
from ytsum.youtube import YouTubeVideoDownloader


class YouTubeVideoDownloadProcessorResult(BaseModel):
    video_id: str
    download_result: int = Field(default=0)
    error_message: Optional[str] = Field(default=None)
    video_info: Optional[VideoMetadata] = Field(default=None)

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
        self._repo = VideoRepository(storage=storage)

    async def run(self) -> YouTubeVideoDownloadProcessorResult:
        await self._repo.start()

        video_metadata = await self._find_or_create_video_metadata()
        output = YouTubeVideoDownloadProcessorResult(video_id=self._video_id, video_info=video_metadata)

        is_download_needed = await self._download_video_is_needed(video_metadata=video_metadata)

        if is_download_needed:
            video_url = f"https://www.youtube.com/watch?v={self._video_id}"
            video_metadata.url = video_url
            with tempfile.TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir)
                downloader = YouTubeVideoDownloader(url=video_url, output_dir=output_dir)
                download_result = downloader.run()

                if download_result != 0:
                    output.download_result = download_result
                    output.error_message = f"Failed to download YouTube files from {video_url}."
                    return output

                file_paths = list(output_dir.glob("*"))
                if not file_paths:
                    output.error_message = "No files found after download."
                    return output

                await self._process_downloaded_files(local_file_paths=file_paths, video_info=video_metadata)

        await self._repo.shutdown()

        return output

    async def _find_or_create_video_metadata(self) -> VideoMetadata:
        video_metadata = await self._repo.find_by_id(video_id=self._video_id)
        if video_metadata is None:
            video_metadata = VideoMetadata(id=self._video_id)
            await self._repo.upsert(video=video_metadata)
        return video_metadata

    async def _download_video_is_needed(self, video_metadata: VideoMetadata) -> bool:
        if video_metadata.video_file_path is None:
            return True

        if not await self._storage.exists(path=video_metadata.video_file_path):
            return True

        return False

    async def _process_downloaded_files(self, local_file_paths: List[Path], video_info: VideoMetadata) -> None:
        # Upload the files to the storage
        uploaded_paths: Dict[Path, str] = await self._repo.upload_artifacts(
            video_id=self._video_id, local_file_paths=local_file_paths
        )

        # Artifact paths should have all the uploaded paths
        video_info.artifact_paths.extend(uploaded_paths.values())

        # Update the specific file paths
        video_info.video_file_path = self._find_single_file_path(uploaded_paths=uploaded_paths, extension=".mp4")
        video_info.audio_file_path = self._find_single_file_path(uploaded_paths=uploaded_paths, extension=".m4a")
        video_info.subtitle_file_paths = self._find_all_file_paths(uploaded_paths=uploaded_paths, extension=".vtt")
        video_info.info_file_path = self._find_single_file_path(uploaded_paths=uploaded_paths, extension=".info.json")

        ytdl_info = await self._load_ytdl_info(path=video_info.info_file_path)
        if ytdl_info is not None:
            video_info.title = ytdl_info.title
            video_info.description = ytdl_info.description

        # Finally, persist the changes to the storage
        await self._repo.upsert(video=video_info)

    def _find_all_file_paths(self, uploaded_paths: Dict[Path, str], extension: str) -> List[str]:
        return [path for path in uploaded_paths.values() if path.lower().endswith(extension.lower())]

    def _find_single_file_path(self, uploaded_paths: Dict[Path, str], extension: str) -> Optional[str]:
        file_paths = self._find_all_file_paths(uploaded_paths=uploaded_paths, extension=extension)
        if len(file_paths) == 1:
            return file_paths[0]
        return None

    async def _load_ytdl_info(self, path: Optional[str]) -> Optional[YoutubeDLVideoInfo]:
        if path is None:
            return None

        exists = await self._storage.exists(path=path)
        if not exists:
            return None

        return await self._storage.load_model(path=path, response_model=YoutubeDLVideoInfo)
