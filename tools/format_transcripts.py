import os
from typing import Optional

import anyio
import click
from ytsum.config import Settings, init_settings
from ytsum.llms.openai import OpenAILLM
from ytsum.repositories.video import VideoMetadata, VideoRepository
from ytsum.storage.azure import AzureBlobStorage
from ytsum.transcription.formatter_v2 import TranscriptFormatter
from ytsum.transcription.parsers import parse_vtt_from_string
from ytsum.transcription.topics import TopicCreator


def find_transcript_file_path(video_info: VideoMetadata) -> Optional[str]:
    for path in video_info.artifact_paths:
        if path.endswith(".en.vtt"):
            return path
    return None


async def run() -> None:
    settings: Settings = init_settings()
    strong_llm = OpenAILLM(
        settings.OPEN_AI_API_KEY,
        model_name=settings.OPEN_AI_STRONG_MODEL_NAME,
    )

    azure_storage_conn_str = os.environ.get("AzureWebJobsStorage")
    storage = AzureBlobStorage(
        connection_string=azure_storage_conn_str,
        container_name="youtube-videos",
    )

    topic_creator = TopicCreator(strong_llm=strong_llm)

    repo = VideoRepository(storage=storage)

    videos = await repo.find_all()

    print(f"Found {len(videos)} videos")

    for video_info in videos:
        print(f"Processing video {video_info.id}")

        video_has_formatted_transcript = await repo.has_formatted_transcript(video_id=video_info.id)

        if video_has_formatted_transcript:
            formatted_transcript = await repo.read_formatted_transcript(video_id=video_info.id)
            if len(formatted_transcript) > 10:
                print(f"Video {video_info.id} already has a formatted transcript, skipping...")
                continue

        transcript_path = find_transcript_file_path(video_info=video_info)
        if transcript_path is None:
            print(f"Could not find transcript for video {video_info.video_id}")
            continue

        print(f"Processing transcript at {transcript_path}...")

        raw_transcript_text = await storage.read_text(path=transcript_path)

        transcript = parse_vtt_from_string(vtt_string=raw_transcript_text)

        formatter = TranscriptFormatter(
            strong_llm=strong_llm,
            batch_size=1000,
        )

        formatted_transcript = await formatter.run(transcript=transcript)

        await repo.save_formatted_transcript(video_id=video_info.id, transcript=formatted_transcript)


@click.command()
def main() -> None:
    anyio.run(run)


if __name__ == "__main__":
    main()
