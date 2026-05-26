import httpx
from .base import BaseProvider


class GeminiProvider(BaseProvider):
    name = "gemini"
    default_model = "gemini-2.0-flash-lite"

    # Free tier: 1500 req/day, 15 req/min — no credit card needed
    # Get key: https://aistudio.google.com/apikey

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def chat(self, messages: list, model: str | None = None, stream: bool = False, **kwargs) -> dict:
        model = model or self.default_model
        # Strip "gemini/" prefix if passed through OpenAI-style model name
        if model.startswith("gemini/"):
            model = model[7:]

        # Convert OpenAI messages to Gemini format
        contents = []
        system_prompt = None
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                system_prompt = content
            elif role == "user":
                contents.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})

        payload: dict = {"contents": contents}
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return self._openai_response(text, model)
