from pathlib import Path
from typing import Dict, Optional

import yt_dlp


class YouTubeVideoDownloader:
    """A class for downloading YouTube videos."""

    def __init__(self, url: str, output_dir: Path, ffmpeg_dir: Path = Path("tools")):
        """Initialize the YouTubeVideoDownloader.

        Args:
            url (str): The URL of the YouTube video to download.
            ffmpeg_dir (Path): The directory containing the ffmpeg and ffprobe binaries.
        """
        self._url = url
        self._output_dir = output_dir
        self._ffmpeg_dir = ffmpeg_dir

        self._ffmpeg_found = False

        if self._ffmpeg_dir.is_dir():
            binary_path = self._ffmpeg_dir / "ffmpeg"
            if binary_path.is_file():
                self._ffmpeg_found = True
        else:
            print(f"FFmpeg directory not found: {self._ffmpeg_dir}")

    def run(self) -> int:
        """Run the video download process."""

        # Options: https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/YoutubeDL.py#L148
        ydl_opts = {
            "format": "137+ba[ext=m4a]/137+ba/bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
            # This string describes a series of format preferences for yt-dlp, separated by forward slashes (/).
            # The program will try each option in order until it finds one that works:
            #
            # 1. "137+ba[ext=m4a]":
            #    - Try to get format ID 137 (typically a high-quality video stream)
            #    - Plus (+) the best available audio with m4a extension
            #
            # 2. "137+ba":
            #    - If the above fails, try format ID 137 plus the best available audio in any format
            #
            # 3. "bv*[ext=mp4]+ba[ext=m4a]":
            #    - If that fails, get the best video (bv*) with mp4 extension
            #    - Plus the best audio (ba) with m4a extension
            #
            # 4. "b[ext=mp4]":
            #    - If that fails, get the best available format (b) with mp4 extension
            #
            # 5. "bv*+ba":
            #    - If that fails, get the best video plus the best audio in any format
            #
            # 6. "b":
            #    - As a last resort, just get the best available format
            #
            # This format string is designed to give you the highest quality video and audio possible,
            # with preferences for certain formats (like mp4 for video and m4a for audio).
            # It provides several fallback options to ensure something will be downloaded
            # even if the preferred formats aren't available.
            "writedescription": True,  # Write the video description to a .description file
            "writeinfojson": True,  # Write the video metadata to a .info.json file
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en", "en-orig", "da", "-live_chat"],
            "paths": {"home": str(self._output_dir)},
            "ignoreerrors": True,
            "verbose": True,
            "ffmpeg_location": str(self._ffmpeg_dir),
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info: Optional[Dict[str, object]] = ydl.extract_info(
                self._url, download=False
            )
            if info is None:
                print("No video info found.")
                return -1

            video_title = info.get("title", "Unknown Title")
            file_size = info.get("filesize", 0)

            print(f"Downloaded video title: {video_title} ({file_size} bytes)")
            error_code = ydl.download([self._url])
            print(f"Error code: {error_code}")

        return error_code


# Usage example:
if __name__ == "__main__":
    video_url = "https://www.youtube.com/watch?v=Onf1UqKPMR4"
    output_dir = Path("data/downloads/Onf1UqKPMR4")

    downloader = YouTubeVideoDownloader(url=video_url, output_dir=output_dir)
    error_code = downloader.run()
    print(error_code)
