from abc import ABC, abstractmethod
from typing import AsyncGenerator
import httpx


class BaseProvider(ABC):
    name: str = ""
    default_model: str = ""

    @abstractmethod
    async def chat(self, messages: list, model: str | None, stream: bool, **kwargs) -> dict | AsyncGenerator:
        pass

    def _openai_response(self, content: str, model: str) -> dict:
        return {
            "id": f"chatcmpl-{self.name}",
            "object": "chat.completion",
            "model": model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }
