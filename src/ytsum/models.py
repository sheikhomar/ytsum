import gzip
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class TranscribedPhrase(BaseModel):
    text: str = Field(..., description="The transcribed text.")
    start_time_ms: Optional[int] = Field(
        default=None,
        description="Start time of the phrase in milliseconds.",
    )


class Transcript(BaseModel):
    phrases: List[TranscribedPhrase]

    def get_phrases_in_range(self, start_ms: int, end_ms: int) -> List[TranscribedPhrase]:
        return [phrase for phrase in self.phrases if phrase.start_time_ms >= start_ms and phrase.start_time_ms < end_ms]

    def get_end_time_in_ms(self) -> int:
        """
        Get the end time of the transcript in milliseconds.

        Returns:
            int: The end time of the transcript in milliseconds.
        """
        return max(phrase.start_time_ms for phrase in self.phrases)


class TranscriptSegment(BaseModel):
    start_time_ms: int = Field(..., description="Start time of the segment in milliseconds.")
    end_time_ms: int = Field(..., description="End time of the segment in milliseconds.")
    phrases: List[TranscribedPhrase] = Field(
        default_factory=list,
        description="Transcribed phrases in the segment.",
    )
    title: Optional[str] = Field(default=None, description="Title of the segment.")
    summary: Optional[str] = Field(default=None, description="A brief summary of the segment.")

    @property
    def text(self) -> str:
        return " ".join(phrase.text for phrase in self.phrases)


class Frame(BaseModel):
    index: int
    starts_at_ms: int
    ends_at_ms: int
    phrases: List[TranscribedPhrase] = Field(
        default_factory=list,
        description="Transcribed phrases in the frame.",
    )

    def get_text(self) -> str:
        return " ".join(phrase.text for phrase in self.phrases)


class FrameOutput(BaseModel):
    frames: List[Frame]

    def save(self, output_file: Path) -> None:
        with gzip.open(output_file, "wt") as fh:
            fh.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, input_file: Path) -> "FrameOutput":
        with gzip.open(input_file, "rt") as fh:
            json_data = fh.read()
            return cls.model_validate_json(json_data=json_data)
