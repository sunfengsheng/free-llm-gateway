import httpx
from .base import BaseProvider


class GroqProvider(BaseProvider):
    name = "groq"
    default_model = "llama-3.3-70b-versatile"

    # Free tier: 14,400 req/day, 30 req/min — no credit card needed
    # Get key: https://console.groq.com/keys
    # Free models: llama-3.3-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768, gemma2-9b-it

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1"

    async def chat(self, messages: list, model: str | None = None, stream: bool = False, **kwargs) -> dict:
        model = model or self.default_model

        payload = {"model": model, "messages": messages, "stream": False}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
