from pathlib import Path
from typing import AsyncIterator, Type

import aiofiles
import aiofiles.os
from azure.storage.blob.aio import BlobClient, BlobServiceClient
from pydantic import BaseModel
from ytsum.storage.common import BlobStorage, ModelType


class AzureBlobStorage(BlobStorage):
    def __init__(self, connection_string: str, container_name: str) -> None:
        self._blob_service_client = BlobServiceClient.from_connection_string(
            conn_str=connection_string
        )
        self._container_client = self._blob_service_client.get_container_client(
            container=container_name
        )

    async def start(self) -> None:
        if not self._container_client.exists():
            await self._container_client.create_container()

    async def shutdown(self) -> None:
        await self._container_client.close()
        await self._blob_service_client.close()

    async def load_model(self, path: str, response_model: Type[ModelType]) -> ModelType:
        blob_client: BlobClient = self._container_client.get_blob_client(blob=path)

        exists = await blob_client.exists()
        if not exists:
            raise FileNotFoundError(f"File not found: {path}")

        data = await blob_client.download_blob()
        json_data = await data.readall()
        model = response_model.model_validate_json(json_data=json_data)
        return model

    async def save_model(self, path: str, model: BaseModel) -> None:
        blob_client: BlobClient = self._container_client.get_blob_client(blob=path)
        json_data = model.model_dump_json(indent=2)
        await blob_client.upload_blob(data=json_data, overwrite=True)

    async def exists(self, path: str) -> bool:
        blob_client: BlobClient = self._container_client.get_blob_client(blob=path)
        return await blob_client.exists()

    async def save_file(self, src_file_path: Path, destination_path: str) -> None:
        blob_client: BlobClient = self._container_client.get_blob_client(
            blob=destination_path
        )
        async with aiofiles.open(src_file_path, "rb") as fh:
            await blob_client.upload_blob(data=fh, overwrite=True)

    async def list_files(self, path_prefix: str) -> AsyncIterator[str]:
        async for blob in self._container_client.list_blobs(
            name_starts_with=path_prefix
        ):
            yield blob.name
