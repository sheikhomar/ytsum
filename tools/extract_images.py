from pathlib import Path

from ytsum.video import VideoImageExtractor


def main() -> None:
    video_file_path = Path("data/raw/2023-11-25-gen-ai-720p-take-12.mp4")
    output_dir = Path("data/processed/2023-11-25-gen-ai-720p-take-12-images/")
    extractor = VideoImageExtractor(
        video_path=video_file_path,
        output_dir=output_dir,
        threshold=1000,
        sample_interval_secs=2.0,
    )
    extractor.run()


if __name__ == "__main__":
    main()
