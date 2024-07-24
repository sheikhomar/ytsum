from abc import ABC, abstractmethod
from typing import Type, TypeVar

from pydantic import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BlobStorage(ABC):
    @abstractmethod
    async def load_model(self, path: str, response_model: Type[ModelType]) -> ModelType:
        raise NotImplementedError

    @abstractmethod
    async def save_model(self, path: str, model: BaseModel) -> None:
        raise NotImplementedError

    @abstractmethod
    async def exists(self, path: str) -> bool:
        raise NotImplementedError
