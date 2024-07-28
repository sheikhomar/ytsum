from pathlib import Path

import anyio
import click
from ytsum.config import Settings, init_settings
from ytsum.llms.openai import OpenAILLM
from ytsum.transcription.parsers import parse_vtt_file
from ytsum.transcription.segmentation.common import TranscriptSegmenter
from ytsum.transcription.segmentation.llm import NaiveLLMGuidedSegmenter


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

    segmenter: TranscriptSegmenter = NaiveLLMGuidedSegmenter(
        strong_llm=strong_llm,
        chunk_size=10000,
    )
    output = await segmenter.run(transcript=transcript)

    for i, segment in enumerate(output):
        print("-" * 80)
        print(f"Segment {i + 1}: {segment.title}")
        print(f" - Summary: {segment.summary}\n")


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
