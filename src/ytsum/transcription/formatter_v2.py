from typing import List

from ytsum.llms.common import LLM, ChatMessage, MessageRole
from ytsum.models import Transcript


class TranscriptFormatter:
    def __init__(self, strong_llm: LLM, batch_size: int) -> None:
        self._strong_llm = strong_llm
        self._batch_size = batch_size

    async def run(self, transcript: Transcript) -> str:
        results: List[str] = []

        batch_start_index = 0
        batch_end_index = batch_start_index + self._batch_size

        last_unfinished_sentence = ""

        while batch_start_index < len(transcript.phrases):
            current_batch = transcript.phrases[batch_start_index:batch_end_index]

            # Prepare the raw transcript text
            raw_transcript_text = " ".join(phrase.text for phrase in current_batch)
            if len(last_unfinished_sentence) > 0:
                raw_transcript_text = f"{last_unfinished_sentence} {raw_transcript_text}"
                last_unfinished_sentence = ""

            # Process the current batch
            fixed_text = await self._fix_punctuation(text=raw_transcript_text)

            # Keep track of the last unfinished sentence
            if fixed_text.endswith("..."):
                last_sentence_end = fixed_text.rfind(".", 0, -3)
                if last_sentence_end != -1:
                    # Extract the last unfinished sentence first
                    last_unfinished_sentence = fixed_text[last_sentence_end + 1 : -3]

                    # Remove the last unfinished sentence from the text
                    fixed_text = fixed_text[: last_sentence_end + 1]

            print("========================================")
            print(f"Original text:\n{raw_transcript_text}\n\n")
            print(f"Fixed text:\n{fixed_text}\n\n")

            results.append(fixed_text)

            # Update the batch end index
            batch_start_index = batch_end_index
            batch_end_index = min(batch_end_index + self._batch_size, len(transcript.phrases))

        return "\n\n".join(results)

    async def _fix_punctuation(self, text: str) -> str:
        """
        Fix punctuation in the given text using a language model.

        Args:
            text (str): Text to process.

        Returns:
            str: Text with corrected punctuation.
        """

        START_TAG = "<punctuated_transcript>"
        END_TAG = "</punctuated_transcript>"

        system_prompt = f"""
You are tasked with adding punctuation to a transcript from a YouTube video. The transcript will be provided to you without any punctuation. Your job is to add appropriate punctuation marks without changing any of the words or content.

Follow these guidelines when adding punctuation:

1. Add periods (.) at the end of sentences where appropriate.
2. Use commas (,) to separate clauses and items in a list.
3. Add question marks (?) at the end of questions.
4. Use exclamation points (!) for exclamations or emphasis, but use them sparingly.
5. Use ellipsis (...) to indicate trailing off or pauses in speech.
6. Add hyphens (-) for compound words or to indicate stammering/repetition.
7. Use parentheses ( ) for asides or additional information.
8. Capitalize the first letter of sentences and proper nouns.

When determining sentence endings, consider the context and natural pauses in speech. If you're unsure about where a sentence ends, it's often better to use a comma or ellipsis rather than a period.

For longer pauses or breaks in speech, you may use a new paragraph to indicate a significant shift in topic or speaker.

Provide your punctuated version of the transcript inside {START_TAG} tags. Maintain the original line breaks from the input transcript.

Here's a short example to illustrate the task:

Input:
hey guys welcome to my channel today were going to talk about the importance of punctuation in writing its often overlooked but it can really change the meaning of

Output:
{START_TAG}
Hey guys! Welcome to my channel. Today, we're going to talk about the importance of punctuation in writing. It's often overlooked, but it can really change the meaning of ...
{END_TAG}
"""

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
            ChatMessage(role=MessageRole.USER, content=text),
        ]

        success = False
        for i in range(5):
            response_text: str = await self._strong_llm.chat(messages=messages)
            if START_TAG in response_text and END_TAG in response_text:
                success = True
                break

        if not success:
            raise ValueError("Punctuated text not found in response.")

        start_index = response_text.find(f"{START_TAG}") + len(f"{START_TAG}")
        end_index = response_text.find("</punctuated_transcript>")
        punctuated_text = response_text[start_index:end_index].strip()

        if punctuated_text.startswith('"') or punctuated_text.startswith("'"):
            punctuated_text = punctuated_text[1:]
        if punctuated_text.endswith('"') or punctuated_text.endswith("'"):
            punctuated_text = punctuated_text[:-1]

        return punctuated_text
