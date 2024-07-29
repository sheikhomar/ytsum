import os
from pathlib import Path

import anyio
import click
from ytsum.config import Settings, init_settings
from ytsum.llms.openai import OpenAILLM
from ytsum.repositories.video import VideoRepository
from ytsum.storage.azure import AzureBlobStorage
from ytsum.transcription.formatter_v2 import TranscriptFormatter
from ytsum.transcription.parsers import parse_vtt_file


async def run(video_id: str) -> None:
    downloads_dir = Path("data/downloads")
    video_dir = downloads_dir / video_id
    vtt_file_paths = list(video_dir.glob("*.en.vtt"))
    if len(vtt_file_paths) != 1:
        click.echo(f"Expected 1 VTT file, but found {len(vtt_file_paths)}")
        return

    vtt_file_path = vtt_file_paths[0]

    transcript = parse_vtt_file(file_path=vtt_file_path)

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

    repo = VideoRepository(storage=storage)

    formatter = TranscriptFormatter(
        strong_llm=strong_llm,
        batch_size=1000,
    )

    formatted_transcript = await formatter.run(transcript=transcript)

    await repo.save_formatted_transcript(video_id=video_id, transcript=formatted_transcript)


@click.command()
@click.option(
    "-i",
    "--video-id",
    required=True,
    help="The YouTube video ID to segment.",
)
def main(video_id: str) -> None:
    anyio.run(run, video_id)


if __name__ == "__main__":
    main()
