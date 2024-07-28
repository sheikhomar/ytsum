from typing import List

from pydantic import BaseModel, Field
from ytsum.llms.common import LLM, ChatMessage, MessageRole
from ytsum.models import TranscribedPhrase, Transcript

XML_BASED_SYSTEM_PROMPT = """
You are tasked with formatting and adding punctuation to a raw transcript from a YouTube video. The transcript will be provided to you without any punctuation. Your job is to add appropriate punctuation marks without changing any of the words or content.

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

Provide your punctuated version of the transcript inside <formatted_transcript> tags. Create <paragraph> tags for each paragraph. Ensure to capture the exact <start_phrase> and <end_phrase> from the raw transcript.

Here is an example to illustrate the task:

Input:
from Sam Alman stating that from today AI progress is going to be immense and Google releasing a new Incredible announcement regarding their Frontier models and even another model that surpasses Arma 3.1 an open-source model there's tons of news that you probably did Miss during this week in AI so one of the first pieces of news that we actually got this week that's rather fascinating is search GPT if you didn't know there has been a real demand for products that can actually search the web much better than traditional search systems if you've ever used Google you'll know that it currently just isn't that good anymore and now essentially search GPT is basically searching with an AI system that browses the web and finds the easy relevant sources that are just what you need so you can see right here you can search will for basically whatever you need and you're able to find

Output:
<formatted_transcript>
<paragraph>
<text>From Sam Altman stating that from today, AI progress is going to be immense, and Google releasing a new incredible announcement regarding their Frontier models, and even another model that surpasses Arma 3.1, an open-source model, there's tons of news that you probably did miss during this week in AI.</text>
<start_phrase>from Sam Alman stating that from today</start_phrase>
<end_phrase>Miss during this week in AI</end_phrase>
</paragraph>
<paragraph>
<text>So, one of the first pieces of news that we actually got this week that's rather fascinating is Search GPT. If you didn't know, there has been a real demand for products that can actually search the web much better than traditional search systems. If you've ever used Google, you'll know that it currently just isn't that good anymore, and now, essentially, Search GPT is basically searching with an AI system that browses the web and finds the easy relevant sources that are just what you need. So you can see right here, you can search for basically whatever you need, and you're able to find ...</text>
<start_phrase>so one of the first pieces of news that we actually got</start_phrase>
<end_phrase>basically whatever you need and you're able to find</end_phrase>
</paragraph>
</formatted_transcript>
"""

JSON_BASED_SYSTEM_PROMPT = """
You are tasked with formatting and adding punctuation to a raw transcript from a YouTube video. The transcript will be provided to you without any punctuation. Your job is to add appropriate punctuation marks without changing any of the words or content.

Follow these guidelines when adding punctuation:

1. Add periods (.) at the end of sentences where appropriate.
2. Use commas (,) to separate clauses and items in a list.
3. Add question marks (?) at the end of questions.
4. Use exclamation points (!) for exclamations or emphasis, but use them sparingly.
5. Use ellipsis (...) to indicate trailing off or pauses in speech.
6. Use NOT_COMPLETE to indicate that the paragraph is not complete.
7. Add hyphens (-) for compound words or to indicate stammering/repetition.
8. Use parentheses ( ) for asides or additional information.
9. Capitalize the first letter of sentences and proper nouns.

When determining sentence endings, consider the context and natural pauses in speech. If you're unsure about where a sentence ends, it's often better to use a comma or ellipsis rather than a period.

For longer pauses or breaks in speech, you may use a new paragraph to indicate a significant shift in topic or speaker.

Provide your punctuated version of the transcript in JSON format. Create `paragraph` item for each paragraph. Ensure to capture the EXACT `start_phrase` and `end_phrase` from the RAW transcript. Only take the EXACT text from the RAW transcript, otherwise the verification process will fail and I will lose my job.

Include a boolean field `is_complete` to indicate if the paragraph is complete or not.

Here is an example to illustrate the task:

Input:
from Sam Alman stating that from today AI progress is going to be immense and Google releasing a new Incredible announcement regarding their Frontier models and even another model that surpasses Arma 3.1 an open-source model there's tons of news that you probably did Miss during this week in AI so one of the first pieces of news that we actually got this week that's rather fascinating is search GPT if you didn't know there has been a real demand for products that can actually search the web much better than traditional search systems if you've ever used Google you'll know that it currently just isn't that good anymore and now essentially search GPT is basically searching with an AI system that browses the web and finds the easy relevant sources that are just what you need so you can see right here you can search will for basically whatever you need and you're able to find

Output:
```json
{
  "paragraphs": [
    {
      "text": "From Sam Altman stating that from today, AI progress is going to be immense, and Google releasing a new incredible announcement regarding their Frontier models, and even another model that surpasses Arma 3.1, an open-source model, there's tons of news that you probably did miss during this week in AI.",
      "start_phrase": "from Sam Alman stating that from today",
      "end_phrase": "Miss during this week in AI",
      "is_complete": true
    },
    {
      "text": "So, one of the first pieces of news that we actually got this week that's rather fascinating is Search GPT. If you didn't know, there has been a real demand for products that can actually search the web much better than traditional search systems. If you've ever used Google, you'll know that it currently just isn't that good anymore, and now, essentially, Search GPT is basically searching with an AI system that browses the web and finds the easy relevant sources that are just what you need. So you can see right here, you can search for basically whatever you need, and you're able to find ... NOT_COMPLETE",
      "start_phrase": "so one of the first pieces of news that we actually got",
      "end_phrase": "basically whatever you need and you're able to find",
      "is_complete": false
    }
  ]
}
```

Remember to copy EXACTLY the text from the RAW transcript in `start_phrase` and `end_phrase`. If you don't, I will lose my job. And I don't want to lose my job. So please, copy EXACTLY the text from the RAW transcript. Thank you.
"""


class FormattedTranscriptParagraph(BaseModel):
    text: str = Field(..., description="The formatted text.")
    start_phrase: str = Field(..., description="The start phrase from the raw transcript.")
    end_phrase: str = Field(..., description="The end phrase from the raw transcript.")
    is_complete: bool = Field(..., description="Indicates if the paragraph is complete or not.")


class FormattedTranscript(BaseModel):
    paragraphs: List[FormattedTranscriptParagraph] = Field(
        default_factory=list,
        description="Formatted paragraphs.",
    )


class TranscriptFormatter:
    def __init__(self, strong_llm: LLM, batch_size: int) -> None:
        self._strong_llm = strong_llm
        self._batch_size = batch_size

    async def run(self, transcript: Transcript) -> None:
        results = []

        batch_start_index = 0
        batch_end_index = batch_start_index + self._batch_size

        hallucination_count = 0

        while batch_start_index < len(transcript.phrases):
            current_batch = transcript.phrases[batch_start_index:batch_end_index]

            raw_transcript_text = " ".join(phrase.text for phrase in current_batch)
            paragraphs = await self._generate_paragraphs(raw_transcript_text=raw_transcript_text)

            # Check if the language model has hallucinated
            print(" - Checking for hallucination...")
            has_llm_hallucinated = self._contain_hallucination(
                raw_transcript_text=raw_transcript_text, paragraphs=paragraphs
            )
            if has_llm_hallucinated:
                if hallucination_count >= 5:
                    raise ValueError("The language model has hallucinated too many times.")
                hallucination_count += 1

                # Rewind the batch end index to retry the hallucinated batch
                batch_end_index -= int(self._batch_size / 10) * hallucination_count
                print(f"  - The language model has hallucinated (count={hallucination_count}). Retrying...")
                continue
            hallucination_count = 0

            # Process the paragraphs
            first_incomplete_paragraph_index: int = -1
            for i, paragraph in enumerate(paragraphs):
                if paragraph.is_complete:
                    print(f"\n\nComplete paragraph:\n{paragraph.text}")

                    results.append(paragraph)
                    continue

                first_incomplete_paragraph_index = i
                break

            if first_incomplete_paragraph_index == -1:
                # All paragraphs are complete
                batch_start_index = batch_end_index
            else:
                first_incomplete_paragraph = paragraphs[first_incomplete_paragraph_index]
                print(f"  - First incomplete paragraph: {first_incomplete_paragraph.text}")
                start_phrase_texts = first_incomplete_paragraph.start_phrase.split(" ")
                start_index = self._find_start_index(
                    phrases=current_batch,
                    phrase_texts_to_look_for=start_phrase_texts,
                )

                # Rewind the batch start index to the start of the incomplete paragraph
                batch_start_index = batch_start_index + start_index

            batch_end_index = min(batch_end_index + self._batch_size, len(transcript.phrases))

    async def _generate_paragraphs(self, raw_transcript_text: str) -> List[FormattedTranscriptParagraph]:
        print(" - Generating paragraphs...")

        print(f"  - Raw text:\n{raw_transcript_text}\n\n")

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=JSON_BASED_SYSTEM_PROMPT),
            ChatMessage(role=MessageRole.USER, content=raw_transcript_text),
        ]

        response_text: str = await self._strong_llm.chat(messages=messages)

        JSON_START_MARKER = "```json"
        JSON_END_MARKER = "```"
        start_json_marker = response_text.find(JSON_START_MARKER)
        if start_json_marker == -1:
            raise ValueError("JSON start marker not found in the response text.")

        end_json_marker = response_text.find(JSON_END_MARKER, start_json_marker + 1)
        json_text_data = response_text[start_json_marker + len(JSON_START_MARKER) : end_json_marker].strip()

        print(f"  - JSON text data:\n{json_text_data}\n\n")

        model = FormattedTranscript.model_validate_json(json_data=json_text_data)
        return model.paragraphs

    def _contain_hallucination(
        self,
        raw_transcript_text: str,
        paragraphs: List[FormattedTranscriptParagraph],
    ) -> bool:
        for paragraph in paragraphs:
            if paragraph.start_phrase not in raw_transcript_text:
                print(f"  - Start phrase not found: {paragraph.start_phrase}")
                return True
            if paragraph.end_phrase not in raw_transcript_text:
                print(f"  - End phrase not found: {paragraph.end_phrase}")
                return True

        print("  - No hallucination detected.")
        return False

    def _find_start_index(
        self,
        phrases: List[TranscribedPhrase],
        phrase_texts_to_look_for: List[str],
    ) -> int:
        for i in range(len(phrases)):
            if phrase_texts_to_look_for[0] in phrases[i].text:
                if all(
                    phrase_texts_to_look_for[j] in phrases[i + j].text for j in range(1, len(phrase_texts_to_look_for))
                ):
                    return i
        raise ValueError("Start phrase not found in the transcript.")
