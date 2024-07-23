import json
import re
from pathlib import Path
from typing import List

import webvtt
from pydantic import BaseModel

PHRASE_PATTERN = re.compile(r"<(\d{2}:\d{2}:\d{2}\.\d{3})>(?:<c>)?([^<]+)(?:</c>)?")


def convert_timestamp_to_ms(timestamp: str) -> int:
    """
    Convert a timestamp string to milliseconds.

    Args:
        timestamp (str): Timestamp in format "HH:MM:SS.mmm" or "HH:MM:SS:mmm" or "HH_MM_SS_mmm".

    Returns:
        int: Time in milliseconds.
    """
    parts = timestamp.replace(".", ":").replace("_", ":").split(":")
    h, m, s, ms = parts
    return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms)


class TranscribedPhrase(BaseModel):
    text: str
    starts_at: str

    @property
    def starts_at_ms(self) -> int:
        return convert_timestamp_to_ms(timestamp=self.starts_at)


class Transcription(BaseModel):
    phrases: List[TranscribedPhrase]

    def get_phrases_in_range(
        self, start_ms: int, end_ms: int
    ) -> List[TranscribedPhrase]:
        return [
            phrase
            for phrase in self.phrases
            if phrase.starts_at_ms >= start_ms and phrase.starts_at_ms < end_ms
        ]

    def get_end_time(self) -> int:
        return max(phrase.starts_at_ms for phrase in self.phrases) + 1000


class Frame(BaseModel):
    index: int
    starts_at_ms: int
    ends_at_ms: int
    text: str


class FrameOutput(BaseModel):
    frames: List[Frame]


def parse_subtitle_line(line: str) -> List[TranscribedPhrase]:
    matches = PHRASE_PATTERN.findall(line)
    return [
        TranscribedPhrase(text=text, starts_at=start_time)
        for start_time, text in matches
    ]


class SubtitleFrameAligner:
    """Aligns subtitle data from a WebVTT file with frame images."""

    def __init__(self, vtt_file: Path, frames_dir: Path, output_file: Path):
        """Initialize the SubtitleFrameAligner.

        Args:
            vtt_file (Path): Path to the WebVTT file.
            frames_dir (Path): Directory containing frame images.
            output_file (Path): Path for the output JSON file.

        Raises:
            FileNotFoundError: If the VTT file or frames directory doesn't exist.
        """
        self._vtt_file = vtt_file
        self._frames_dir = frames_dir
        self._output_file = output_file

        if not self._vtt_file.is_file():
            raise FileNotFoundError(f"VTT file not found: {self._vtt_file}")
        if not self._frames_dir.is_dir():
            raise FileNotFoundError(f"Frames directory not found: {self._frames_dir}")

    def run(self) -> None:
        """
        Process the VTT file and frame images, generate and save the JSON output.
        """
        transcription = self._get_transcription()

        frame_file_paths = sorted(self._frames_dir.glob("frame-*-*-*.jpg"))

        output = FrameOutput(frames=[])
        for frame_file_path in frame_file_paths:
            parts = frame_file_path.stem.split("-")
            frame_index = int(parts[1])
            frame_starts_at_ms = convert_timestamp_to_ms(timestamp=parts[2])
            frame_ends_at_ms = convert_timestamp_to_ms(timestamp=parts[3])

            phrases = transcription.get_phrases_in_range(
                start_ms=frame_starts_at_ms, end_ms=frame_ends_at_ms
            )

            frame_text = " ".join([phrase.text.strip() for phrase in phrases])
            output.frames.append(
                Frame(
                    index=frame_index,
                    starts_at_ms=frame_starts_at_ms,
                    ends_at_ms=frame_ends_at_ms,
                    text=frame_text,
                )
            )

        # Update the last frame with the remaining transcription text
        last_frame = output.frames[-1]
        last_frame.ends_at_ms = transcription.get_end_time()
        phrases = transcription.get_phrases_in_range(
            start_ms=last_frame.starts_at_ms,
            end_ms=last_frame.ends_at_ms,
        )
        last_frame.text = " ".join([phrase.text.strip() for phrase in phrases])

        with self._output_file.open("w") as f:
            json.dump(output.model_dump(), f, indent=2)

    def _get_transcription(self) -> Transcription:
        phrases: List[TranscribedPhrase] = []

        vtt = webvtt.read(str(self._vtt_file))

        for caption in vtt.captions:
            raw_text = caption.raw_text
            lines = raw_text.split("\n")
            for line in lines:
                has_cue_tags = webvtt.Caption.CUE_TEXT_TAGS.findall(line)
                if has_cue_tags:
                    modified_line = f"<{caption.start}>{line}"
                    phrases.extend(parse_subtitle_line(line=modified_line))
        return Transcription(phrases=phrases)


if __name__ == "__main__":
    vtt_file = Path(
        "data/downloads/Onf1UqKPMR4/Webinar： Fix Hallucinations in RAG Systems with Pinecone and Galileo [Onf1UqKPMR4].en-orig.vtt"
    )
    frames_dir = Path("data/processed/Onf1UqKPMR4-images")
    output_file = Path("data/processed/Onf1UqKPMR4-output.json")
    aligner = SubtitleFrameAligner(vtt_file, frames_dir, output_file)
    aligner.run()