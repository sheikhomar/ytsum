from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncIterator, Type, TypeVar

from pydantic import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BlobStorage(ABC):
    @abstractmethod
    async def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def shutdown(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def load_model(self, path: str, response_model: Type[ModelType]) -> ModelType:
        raise NotImplementedError

    @abstractmethod
    async def save_model(self, path: str, model: BaseModel) -> None:
        raise NotImplementedError

    @abstractmethod
    async def exists(self, path: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def save_file(self, src_file_path: Path, destination_path: str) -> None:
        """
        Save a local file to the storage system.
        """
        raise NotImplementedError

    @abstractmethod
    async def list_files(self, path_prefix: str) -> AsyncIterator[str]:
        """
        Fetch a list of files in the storage system with the given path prefix.
        """
        raise NotImplementedError
