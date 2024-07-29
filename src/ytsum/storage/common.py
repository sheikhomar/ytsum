from abc import ABC, abstractmethod
from pathlib import Path
from typing import IO, AnyStr, AsyncIterable, AsyncIterator, Iterable, Type, TypeVar, Union

from pydantic import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)
Blob = Union[bytes, str, Iterable[AnyStr], AsyncIterable[AnyStr], IO[AnyStr]]


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

    @abstractmethod
    def download_file(self, src_file_path: str, destination_path: Path) -> None:
        """
        Download a file from the storage system to the local file system.

        Args:
            src_file_path: The path to the file in the storage system.
            destination_path: The path to save the file to on the local file
        """
        raise NotImplementedError

    @abstractmethod
    async def upload_blob(self, data: Blob, destination_path: str) -> None:
        """
        Upload a blob to the storage system.

        Args:
            data: The blob to upload.
            destination_path: The path to save the blob to in the storage system.
        """
        raise NotImplementedError

    @abstractmethod
    async def read_text(self, path: str) -> str:
        raise NotImplementedError
