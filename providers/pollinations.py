import httpx
from .base import BaseProvider


class PollinationsProvider(BaseProvider):
    name = "pollinations"
    default_model = "openai"

    # Pollinations.ai: 完全免费合法，无需注册、无需 Key
    # 官网: https://pollinations.ai
    # 可用模型: openai, mistral, llama, deepseek, qwen, gemini, ...

    MODELS = ["openai", "mistral", "llama", "deepseek", "qwen", "gemini"]

    async def chat(self, messages: list, model: str | None = None, stream: bool = False, **kwargs) -> dict:
        model = model or self.default_model

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://text.pollinations.ai/openai",
                json={"model": model, "messages": messages},
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()
