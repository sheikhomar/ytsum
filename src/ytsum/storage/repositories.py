from typing import List, Set

from pydantic import BaseModel, Field
from ytsum.storage.common import BlobStorage


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
