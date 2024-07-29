from typing import Optional

from pydantic import BaseModel

from ytsum.llms.common import LLM
from ytsum.repositories.video import VideoMetadata, VideoRepository
from ytsum.storage.common import BlobStorage
from ytsum.transcription.formatter_v2 import TranscriptFormatter
from ytsum.transcription.parsers import parse_vtt_from_string


class YouTubeTranscriptFormatterResult(BaseModel):
    video_id: str
    error_message: Optional[str] = None


class YouTubeTranscriptFormatter:
    def __init__(
        self,
        video_id: str,
        strong_llm: LLM,
        storage: BlobStorage,
    ) -> None:
        self._video_id = video_id
        self._storage = storage
        self._repo = VideoRepository(storage=storage)
        self._formatter = TranscriptFormatter(strong_llm=strong_llm, batch_size=1000)

    async def run(self) -> YouTubeTranscriptFormatterResult:
        video_info = await self._repo.find_by_id(video_id=self._video_id)
        if not video_info:
            return YouTubeTranscriptFormatterResult(
                video_id=self._video_id, error_message=f"Video with ID {self._video_id} not found"
            )

        video_has_formatted_transcript = await self._repo.has_formatted_transcript(video_id=video_info.id)
        if video_has_formatted_transcript:
            transcript_text = await self._repo.read_formatted_transcript(video_id=video_info.id)
            print(f"Transcript text length {len(transcript_text)}")
            return YouTubeTranscriptFormatterResult(video_id=self._video_id)

        transcript_path = self._find_transcript_file_path(video_info=video_info)
        if transcript_path is None:
            print(f"Could not find transcript for video {video_info.video_id}")
            return YouTubeTranscriptFormatterResult(
                video_id=self._video_id, error_message=f"Could not find transcript for video {video_info.video_id}"
            )

        print(f"Processing transcript at {transcript_path}...")
        raw_transcript_text = await self._storage.read_text(path=transcript_path)

        print(f"Raw transcript size: {len(raw_transcript_text)}\n{raw_transcript_text[:100]}")

        transcript = parse_vtt_from_string(vtt_string=raw_transcript_text)

        print(f"Transcript parsed with {len(transcript.phrases)} phrases")

        formatted_transcript = await self._formatter.run(transcript=transcript)

        print(f"Formatted transcript size: {len(formatted_transcript)}")

        await self._repo.save_formatted_transcript(video_id=video_info.id, transcript=formatted_transcript)

        return YouTubeTranscriptFormatterResult(video_id=self._video_id)

    def _find_transcript_file_path(self, video_info: VideoMetadata) -> Optional[str]:
        for path in video_info.artifact_paths:
            if path.endswith(".en-orig.vtt"):
                return path
        return None
