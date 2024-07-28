from typing import List, Optional

from ytsum.llms.common import LLM, ChatMessage, MessageRole
from ytsum.models import Transcript, TranscriptSegment
from ytsum.transcription.segmentation.common import TranscriptSegmenter


class NaiveLLMGuidedSegmenter(TranscriptSegmenter):
    def __init__(self, strong_llm: LLM, chunk_size: int) -> None:
        self._strong_llm = strong_llm
        self._chunk_size = chunk_size

    async def run(self, transcript: Transcript) -> List[TranscriptSegment]:
        result: List[TranscriptSegment] = []

        system_prompt = (
            "You are an AI assistant tasked with segmenting a video transcript into logical chapters or sections. "
            "Analyze the content and identify natural breakpoints where the topic or focus changes significantly. "
            "For each segment, provide a title and a brief summary."
        )

        chunks = self._split_transcript_into_chunks(transcript=transcript, chunk_size=self._chunk_size)

        current_segment: Optional[TranscriptSegment] = None
        for chunk in chunks:
            prompt = self._generate_chunk_prompt(chunk=chunk, current_segment=current_segment)
            response = await self._get_llm_response(system_prompt=system_prompt, user_prompt=prompt)
            new_segments = self._parse_llm_response(response=response, chunk=chunk)

            if new_segments:
                if current_segment:
                    current_segment.end_time_ms = new_segments[0].start_time_ms - 1
                    result.append(current_segment)
                result.extend(new_segments[:-1])
                current_segment = new_segments[-1]
            elif current_segment:
                current_segment.phrases.extend(chunk.phrases)
                current_segment.end_time_ms = chunk.phrases[-1].start_time_ms

        if current_segment:
            result.append(current_segment)

        return result

    def _split_transcript_into_chunks(self, transcript: Transcript, chunk_size: int) -> List[Transcript]:
        chunks = []
        current_chunk = []
        word_count = 0

        for phrase in transcript.phrases:
            current_chunk.append(phrase)
            word_count += len(phrase.text.split())

            if word_count >= chunk_size:
                chunks.append(Transcript(phrases=current_chunk))
                current_chunk = []
                word_count = 0

        if current_chunk:
            chunks.append(Transcript(phrases=current_chunk))

        return chunks

    def _generate_chunk_prompt(self, chunk: Transcript, current_segment: Optional[TranscriptSegment]) -> str:
        prompt = "Analyze the following transcript chunk and identify any logical breakpoints for new segments:\n\n"
        prompt += " ".join(phrase.text for phrase in chunk.phrases)
        prompt += "\n\nIf this chunk continues the previous segment, respond with 'CONTINUE'. "
        prompt += "Otherwise, provide the breakpoints in the following format:\n"
        prompt += "BREAKPOINT: \nTITLE: [segment title]\nSUMMARY: [brief summary]\n\n"

        if current_segment:
            prompt += f"Note: The current segment started at {current_segment.start_time_ms}ms with the title '{current_segment.title}'."

        return prompt

    async def _get_llm_response(self, system_prompt: str, user_prompt: str) -> str:
        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
            ChatMessage(role=MessageRole.USER, content=user_prompt),
        ]
        return await self._strong_llm.chat(messages=messages)

    def _parse_llm_response(self, response: str, chunk: Transcript) -> List[TranscriptSegment]:
        segments: List[TranscriptSegment] = []

        if response.strip().upper() == "CONTINUE":
            return segments

        lines = response.strip().split("\n")
        current_segment: Optional[TranscriptSegment] = None

        for line in lines:
            if line.startswith("BREAKPOINT:"):
                if current_segment:
                    segments.append(current_segment)
                start_time_ms = 0
                try:
                    start_time_ms = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
                current_segment = TranscriptSegment(
                    start_time_ms=start_time_ms,
                    end_time_ms=chunk.phrases[-1].start_time_ms,
                    phrases=[phrase for phrase in chunk.phrases if phrase.start_time_ms >= start_time_ms],
                    title=None,
                    summary=None,
                )
            elif line.startswith("TITLE:") and current_segment:
                current_segment.title = line.split(":", 1)[1].strip()
            elif line.startswith("SUMMARY:") and current_segment:
                current_segment.summary = line.split(":", 1)[1].strip()

        if current_segment:
            segments.append(current_segment)

        return segments

    async def close(self) -> None:
        await self._strong_llm.close()
