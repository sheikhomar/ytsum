from abc import ABC, abstractmethod
from enum import StrEnum
from typing import AsyncGenerator, Optional, Sequence

from pydantic import BaseModel, Field


class MessageRole(StrEnum):
    """Message role."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """A message in a chat conversation."""

    role: MessageRole = Field(
        default=MessageRole.USER,
        description="The role of this message.",
    )

    content: str = Field(
        description="The content of this message.",
    )


class LLM(ABC):
    """Represents an interface to a Large Language Model (LLM)."""

    @abstractmethod
    async def chat_stream(
        self,
        messages: Sequence[ChatMessage],
        temperature: Optional[float] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Sends a sequences of messages to the LLM and yields text fragment generator.

        Args:
            messages: A sequence of chat messages.
            temperature: The temperature to use when generating the response. Defaults to None.

        Yields:
            A generator of text fragments returned by the LLM.
        """
        raise NotImplementedError

    @abstractmethod
    async def chat(
        self,
        messages: Sequence[ChatMessage],
        temperature: Optional[float] = None,
    ) -> str:
        """
        Sends a sequences of messages to the LLM and returns the response.

        Args:
            messages: A sequence of chat messages.
            temperature: The temperature to use when generating the response. Defaults to None.

        Returns:
            The response text returned by the LLM.
        """

        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """
        Releases any resources associated with the LLM client.

        This method should be called when the LLM client is no longer needed.
        """
        raise NotImplementedError
