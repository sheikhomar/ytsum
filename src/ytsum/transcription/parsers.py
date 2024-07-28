import re
from pathlib import Path
from typing import List

import webvtt
from ytsum.models import (
    TranscribedPhrase,
    Transcript,
)
from ytsum.utils import convert_timestamp_to_ms

PHRASE_PATTERN = re.compile(r"<(\d{2}:\d{2}:\d{2}\.\d{3})>(?:<c>)?([^<]+)(?:</c>)?")


def parse_vtt_file(file_path: Path) -> Transcript:
    """Parse a WebVTT file and extract transcribed phrases.

    Args:
        file_path (Path): Path to the WebVTT file.

    Returns:
        Transcript: The parsed transcript.

    Raises:
        FileNotFoundError: If the input file is not a file or does not exist.
    """

    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"Input file {file_path} is not a file or does not exist.")

    vtt = webvtt.read(str(file_path))

    phrases: List[TranscribedPhrase] = []
    for caption in vtt.captions:
        raw_text = caption.raw_text
        lines = raw_text.split("\n")
        for line in lines:
            has_cue_tags = webvtt.Caption.CUE_TEXT_TAGS.findall(line)
            if not has_cue_tags:
                continue

            # Only process lines with cue tags
            modified_line = f"<{caption.start}>{line}"
            matches = PHRASE_PATTERN.findall(modified_line)
            for start_time_str, text in matches:
                phrases.append(
                    TranscribedPhrase(
                        text=text.strip(),
                        start_time_ms=convert_timestamp_to_ms(start_time_str),
                    )
                )
    return Transcript(phrases=phrases)
