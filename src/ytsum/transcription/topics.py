from typing import List

from pydantic import BaseModel, Field
from ytsum.llms.common import LLM, ChatMessage, MessageRole


class TranscriptSection(BaseModel):
    title: str = Field(..., description="The title of the section")
    paragraphs: List[str] = Field(..., description="The paragraphs of the section")


class SectionedTranscript(BaseModel):
    sections: List[TranscriptSection] = Field(..., title="Sections")


class LLMOutputItem(BaseModel):
    topic_title: str = Field(..., title="Topic title")
    start_sentence: str = Field(..., title="Start sentence")


class LLMOutput(BaseModel):
    topics: List[LLMOutputItem] = Field(..., title="Topics")


class TopicCreator:
    def __init__(self, strong_llm: LLM) -> None:
        self._strong_llm = strong_llm

    async def run(self, transcript_text: str) -> List[TranscriptSection]:
        output = await self._generate_topics(transcript_text=transcript_text)

        start_index = -1

        sections = []
        for item in output.topics:
            print(f"========================================\nProcessing {item.topic_title}")
            if start_index == -1:
                print(" - Start index is 0, skipping...")
                start_index = 0
                continue

            start_sentence_index = transcript_text.find(item.start_sentence)
            if start_sentence_index == -1:
                raise ValueError("Start sentence not found in the transcript text.")

            section_text = transcript_text[start_index:start_sentence_index].strip()
            paragraphs = section_text.split("\n\n")
            print(f" - Found {len(paragraphs)} paragraphs")
            sections.append(TranscriptSection(title=item.topic_title, paragraphs=paragraphs))

            start_index = start_sentence_index

        return sections

    async def _generate_topics(self, transcript_text: str) -> LLMOutput:
        """
        Generate topics from the given transcript text.

        Args:
            transcript_text (str): Text to process.

        Returns:
            str: Text with corrected punctuation.
        """

        prompt = f"""Here is a formatted YouTube transcript:

```text
{transcript_text}
```

Your task is to divide the large block of text into smaller, topically coherent paragraph. 

Output format:

```json
{{

  "topics": [
    {{
      "topic_title": "Introduction",
      "start_sentence": "The possibility of re-using media products from different sources such as television, radio, etc. is very important for modern broadcasters."
    }},
    {{
      "topic_title": "Linear Text Segmentation",
      "start_sentence": "One of the earliest approaches for linear text segmentation, TextTiling, pioneered the idea of using two adjacent sliding windows over sentences"
    }},
  ]
}}
```
"""

        messages = [ChatMessage(role=MessageRole.USER, content=prompt)]

        START_TAG = "```json"
        END_TAG = "```"

        success = False
        for i in range(5):
            response_text: str = await self._strong_llm.chat(messages=messages)
            if START_TAG in response_text and END_TAG in response_text:
                success = True
                break

        if not success:
            raise ValueError("Start and end tags not found in response.")

        print(f"\n\n\nFrom LLM:\n{response_text} \n\n\n")

        start_index = response_text.rfind(f"{START_TAG}") + len(f"{START_TAG}")
        end_index = response_text.rfind(END_TAG)
        json_text = response_text[start_index:end_index].strip()

        print(f"\n\n\nFrom LLM JSON:\n{json_text} \n\n\n")

        return LLMOutput.model_validate_json(json_data=json_text)
