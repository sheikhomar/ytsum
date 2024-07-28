import click
from ytsum.models import TranscribedPhrase, Transcript
from ytsum.transcription.segmentation.common import NoOpSegmenter, TranscriptSegmenter


@click.command()
@click.option(
    "-i",
    "--video-id",
    required=True,
    help="The YouTube video ID to segment.",
)
def main(video_id: str) -> None:
    transcript = Transcript(
        phrases=[
            TranscribedPhrase(text="Hello", starts_at="0:00:00.000"),
            TranscribedPhrase(text="world", starts_at="0:00:01.000"),
        ]
    )

    segmenter: TranscriptSegmenter = NoOpSegmenter()
    output = segmenter.run(transcript=transcript)

    for segment in output:
        click.echo(f"Segment: {segment.text}")


if __name__ == "__main__":
    main()
