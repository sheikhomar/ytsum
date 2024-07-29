from abc import ABC, abstractmethod
from typing import List

from ytsum.models import Transcript, TranscriptSegment


class TranscriptSegmenter(ABC):
    @abstractmethod
    def run(self, transcript: Transcript) -> List[TranscriptSegment]:
        raise NotImplementedError


class NoOpSegmenter(TranscriptSegmenter):
    def run(self, transcript: Transcript) -> List[TranscriptSegment]:
        return [
            TranscriptSegment(
                start_time_ms=0,
                end_time_ms=transcript.get_end_time_in_ms(),
                phrases=transcript.phrases,
            )
        ]
