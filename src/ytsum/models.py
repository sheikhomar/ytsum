import gzip
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

from ytsum.utils import convert_timestamp_to_ms


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
    phrases: List[TranscribedPhrase] = Field(
        default_factory=list,
        description="Transcribed phrases in the frame.",
    )


class FrameOutput(BaseModel):
    frames: List[Frame]

    def save(self, output_file: Path) -> None:
        with gzip.open(output_file, "wt") as fh:
            fh.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, input_file: Path) -> None:
        with gzip.open(input_file, "rt") as fh:
            json_data = fh.read()
            cls.model_validate_json(json_data=json_data)
