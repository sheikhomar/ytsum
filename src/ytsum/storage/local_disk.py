from pathlib import Path
from typing import Type

import aiofiles
import aiofiles.os
import aioshutil
from pydantic import BaseModel
from ytsum.storage.common import BlobStorage, ModelType


class LocalDiskBlobStorage(BlobStorage):
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir

    async def start(self) -> None:
        print(f"Starting local disk storage at: {self._data_dir}")

    async def shutdown(self) -> None:
        print(f"Shutting down local disk storage at: {self._data_dir}")

    async def load_model(self, path: str, response_model: Type[ModelType]) -> ModelType:
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

    async def save_file(self, src_file_path: Path, destination_path: str) -> None:
        dst_file_path = self._data_dir / destination_path
        await aiofiles.os.makedirs(dst_file_path.parent, exist_ok=True)
        aioshutil.copyfile(src=src_file_path, dst=dst_file_path)