from pathlib import Path

import click
from ytsum.video import VideoImageExtractor


@click.command()
@click.option(
    "-i",
    "--video-file-path",
    type=click.Path(
        exists=True, file_okay=True, dir_okay=False, readable=True, path_type=Path
    ),
    required=True,
    help="Location of the video file from which to extract images.",
)
@click.option("-t", "--threshold", type=float, default=0.98)
@click.option("-s", "--sample-interval-secs", type=float, default=1.0)
@click.option(
    "-o",
    "--output-dir",
    required=True,
    type=click.Path(
        exists=False, file_okay=False, dir_okay=True, writable=True, path_type=Path
    ),
    help="The directory where the output files will be saved.",
)
def main(
    video_file_path: Path,
    threshold: float,
    sample_interval_secs: float,
    output_dir: Path,
) -> None:
    extractor = VideoImageExtractor(
        video_path=video_file_path,
        output_dir=output_dir,
        threshold=threshold,
        sample_interval_secs=sample_interval_secs,
    )
    extractor.run()


if __name__ == "__main__":
    main()
