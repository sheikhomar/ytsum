from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Set, Type, TypeVar

import aiofiles
import aiofiles.os
import anyio
from pydantic import BaseModel, Field

from ytsum.config import Settings, init_settings
from ytsum.llms.common import LLM, ChatMessage, MessageRole
from ytsum.llms.openai import OpenAILLM
from ytsum.models import Frame, FrameOutput, TranscribedPhrase
from ytsum.utils import batched

T = TypeVar("T", bound=BaseModel)


class BlobStorage(ABC):
    @abstractmethod
    async def load_model(self, path: str, response_model: Type[T]) -> T:
        raise NotImplementedError

    @abstractmethod
    async def save_model(self, path: str, model: BaseModel) -> None:
        raise NotImplementedError

    @abstractmethod
    async def exists(self, path: str) -> bool:
        raise NotImplementedError


class LocalDiskBlobStorage(BlobStorage):
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir

    async def load_model(self, path: str, response_model: Type[T]) -> T:
        full_path = self._data_dir / path

        exists = await aiofiles.os.path.exists(full_path)
        if not exists:
            raise FileNotFoundError(f"File not found: {full_path}")

        async with aiofiles.open(full_path, mode="r") as f:
            json_data = await f.read()
            model = response_model.model_validate_json(json_data=json_data)
            return model

    async def save_model(self, path: str, model: BaseModel) -> None:
        full_path = self._data_dir / path

        await aiofiles.os.makedirs(full_path.parent, exist_ok=True)

        async with aiofiles.open(full_path, mode="w") as f:
            json_data = model.model_dump_json(indent=2)
            await f.write(json_data)

    async def exists(self, path: str) -> bool:
        full_path = self._data_dir / path
        return await aiofiles.os.path.exists(full_path)


class ProcessedText(BaseModel):
    index: int = Field(...)
    text: str = Field(..., description="The processed text.")
    original_text: str = Field(..., description="The original text.")


class ProcessedTextMetadata(BaseModel):
    count: int = Field(default=0, description="The number of processed texts.")
    indices: Set[int] = Field(default_factory=set)


class ProcessedTextRepository:
    def __init__(self, path_prefix: str, blob_storage: BlobStorage) -> None:
        self._path_prefix = path_prefix
        self._processed_texts: List[ProcessedText] = []
        self._metadata: ProcessedTextMetadata = ProcessedTextMetadata()
        self._blob_storage = blob_storage

    async def load(self) -> None:
        meta_data_path = f"{self._path_prefix}/meta-data.json"
        meta_data_exists = await self._blob_storage.exists(path=meta_data_path)

        # Create the metadata file if it doesn't exist
        if not meta_data_exists:
            await self._save_metadata()
            return

        # Otherwise, load the metadata and processed texts
        self._metadata = await self._blob_storage.load_model(
            path=f"{self._path_prefix}/meta-data.json",
            response_model=ProcessedTextMetadata,
        )

        for index in self._metadata.indices:
            processed_text = await self._blob_storage.load_model(
                path=f"{self._path_prefix}/data/{index}.json",
                response_model=ProcessedText,
            )
            self._processed_texts.append(processed_text)

    async def add(self, processed_text: ProcessedText) -> None:
        # Save the new ProcessedText object
        await self._blob_storage.save_model(
            path=f"{self._path_prefix}/data/{processed_text.index}.json",
            model=processed_text,
        )

        # Then finally do some bookkeeping
        self._metadata.count += 1
        self._metadata.indices.add(processed_text.index)
        await self._save_metadata()

        self._processed_texts.append(processed_text)

    async def get_last_index(self) -> int:
        return max(self._metadata.indices) if self._metadata.indices else 0

    async def _save_metadata(self) -> None:
        await self._blob_storage.save_model(
            path=f"{self._path_prefix}/meta-data.json",
            model=self._metadata,
        )


class FrameContentEnhancer:
    """
    Enhances and structures transcribed content within Frame objects.
    """

    def __init__(
        self,
        strong_llm: LLM,
        processed_text_repo: ProcessedTextRepository,
        batch_size: int,
    ):
        """
        Initialize the FrameContentEnhancer.

        Args:
            batch_size (int): Maximum number of phrases to process in a single batch.
        """
        self._strong_llm = strong_llm
        self._batch_size = batch_size
        self._processed_text_repo = processed_text_repo

    async def run(self, frames: List[Frame]) -> None:
        """
        Process a list of Frame objects to enhance and structure their content.

        Args:
            frames (List[Frame]): List of Frame objects to process.

        Raises:
            ValueError: If the input frames list is empty.
        """
        if not frames:
            raise ValueError("Input frames list is empty.")

        all_phrases: List[TranscribedPhrase] = [
            phrase for frame in frames for phrase in frame.phrases
        ]

        batched_phrases = batched(iterable=all_phrases, n=self._batch_size)

        last_unfinished_sentence = ""
        last_processed_index = await self._processed_text_repo.get_last_index()

        for index, current_batch in enumerate(batched_phrases):
            # Skip already processed batches
            if index < last_processed_index:
                print(f"Skipping already processed batch {index}.")
                continue

            print(f"Processing batch {index}/{len(batched_phrases)}.")

            # Prepare the original text
            original_text = " ".join([phrase.text for phrase in current_batch])
            if len(last_unfinished_sentence) > 0:
                original_text = f"{last_unfinished_sentence} {original_text}"
                last_unfinished_sentence = ""

            # Process the current batch
            fixed_text = await self._fix_punctuation(text=original_text)

            # Keep track of the last unfinished sentence
            if fixed_text.endswith("..."):
                last_sentence_end = fixed_text.rfind(".", 0, -3)
                if last_sentence_end != -1:
                    # Extract the last unfinished sentence first
                    last_unfinished_sentence = fixed_text[last_sentence_end + 1 : -3]

                    # Remove the last unfinished sentence from the text
                    fixed_text = fixed_text[: last_sentence_end + 1]

            processed_text = ProcessedText(
                index=index,
                text=fixed_text,
                original_text=original_text,
            )

            await self._processed_text_repo.add(processed_text=processed_text)

    async def _fix_punctuation(self, text: str) -> str:
        """
        Fix punctuation in the given text using a language model.

        Args:
            text (str): Text to process.

        Returns:
            str: Text with corrected punctuation.
        """

        START_TAG = "{START_TAG}"
        END_TAG = "</punctuated_transcript>"

        system_prompt = f"""
You are tasked with adding punctuation to a transcript from a YouTube video. The transcript will be provided to you without any punctuation. Your job is to add appropriate punctuation marks without changing any of the words or content.

Follow these guidelines when adding punctuation:

1. Add periods (.) at the end of sentences where appropriate.
2. Use commas (,) to separate clauses and items in a list.
3. Add question marks (?) at the end of questions.
4. Use exclamation points (!) for exclamations or emphasis, but use them sparingly.
5. Add quotation marks (" ") around direct speech or quotes.
6. Use ellipsis (...) to indicate trailing off or pauses in speech.
7. Add hyphens (-) for compound words or to indicate stammering/repetition.
8. Use parentheses ( ) for asides or additional information.
9. Capitalize the first letter of sentences and proper nouns.

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

        print(f"Sending {len(messages)} messages to the language model.")
        response_text: str = await self._strong_llm.chat(messages=messages)

        # Extract the punctuated text within the {START_TAG} tags
        if START_TAG not in response_text and END_TAG not in response_text:
            raise ValueError("Punctuated text not found in response.")
        start_index = response_text.find(f"{START_TAG}") + len(f"{START_TAG}")
        end_index = response_text.find("</punctuated_transcript>")
        punctuated_text = response_text[start_index:end_index].strip()

        return punctuated_text


async def main() -> None:
    blob_storage = LocalDiskBlobStorage(
        data_dir=Path("data/repositories/processed-text")
    )
    repo = ProcessedTextRepository(
        path_prefix="Onf1UqKPMR4",
        blob_storage=blob_storage,
    )

    await repo.load()

    frame_file_path = Path("data/processed/Onf1UqKPMR4-output.json.gz")
    frame_output = FrameOutput.load(input_file=frame_file_path)

    settings: Settings = init_settings()
    strong_llm = OpenAILLM(
        settings.OPEN_AI_API_KEY,
        model_name=settings.OPEN_AI_STRONG_MODEL_NAME,
    )

    enhancer = FrameContentEnhancer(
        strong_llm=strong_llm,
        processed_text_repo=repo,
        batch_size=256,
    )

    await enhancer.run(frames=frame_output.frames)


# Usage example:
if __name__ == "__main__":
    anyio.run(main)
