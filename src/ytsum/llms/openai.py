from typing import AsyncGenerator, Optional, Sequence, TypeVar

from openai import AsyncOpenAI
from ytsum.llms.common import LLM, ChatMessage

T = TypeVar("T")


class OpenAILLM(LLM):
    def __init__(self, api_key: str, model_name: str):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model_name = model_name

    async def chat_stream(
        self,
        messages: Sequence[ChatMessage],
        temperature: Optional[float] = None,
    ) -> AsyncGenerator[str, None]:
        response = await self._client.chat.completions.create(
            model=self._model_name,
            messages=[{"role": msg.role, "content": msg.content} for msg in messages],
            temperature=temperature,
            stream=True,
        )

        async for chunk in response:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

    async def chat(
        self,
        messages: Sequence[ChatMessage],
        temperature: Optional[float] = None,
    ) -> str:
        response = await self._client.chat.completions.create(
            model=self._model_name,
            messages=[{"role": msg.role, "content": msg.content} for msg in messages],
            temperature=temperature,
        )
        return response.choices[0].message.content

    async def close(self) -> None:
        await self._client.close()
