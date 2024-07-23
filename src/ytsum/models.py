from typing import List

from pydantic import BaseModel

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
    text: str


class FrameOutput(BaseModel):
    frames: List[Frame]
