from pathlib import Path

import click
from ytsum.transcription.parsers import parse_vtt_file
from ytsum.transcription.segmentation.common import NoOpSegmenter, TranscriptSegmenter


@click.command()
@click.option(
    "-i",
    "--video-id",
    required=True,
    help="The YouTube video ID to segment.",
)
def main(video_id: str) -> None:
    downloads_dir = Path("data/downloads")
    video_dir = downloads_dir / video_id
    vtt_file_paths = list(video_dir.glob("*.en.vtt"))
    if len(vtt_file_paths) != 1:
        click.echo(f"Expected 1 VTT file, but found {len(vtt_file_paths)}")
        return

    vtt_file_path = vtt_file_paths[0]

    transcript = parse_vtt_file(file_path=vtt_file_path)

    segmenter: TranscriptSegmenter = NoOpSegmenter()
    output = segmenter.run(transcript=transcript)

    for segment in output:
        click.echo(f"Segment: {segment.text}")


if __name__ == "__main__":
    main()
