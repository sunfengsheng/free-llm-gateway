import httpx
from .base import BaseProvider


class OpenRouterProvider(BaseProvider):
    name = "openrouter"
    default_model = "meta-llama/llama-3.3-70b-instruct:free"

    # Free tier: models with ":free" suffix — no credit card needed for free models
    # Get key: https://openrouter.ai/keys
    # Free models list: https://openrouter.ai/models?order=top-weekly&supported_parameters=free

    FREE_MODELS = [
        "meta-llama/llama-3.3-70b-instruct:free",
        "deepseek/deepseek-r1:free",
        "google/gemma-3-27b-it:free",
        "mistralai/mistral-7b-instruct:free",
        "qwen/qwen3-235b-a22b:free",
    ]

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"

    async def chat(self, messages: list, model: str | None = None, stream: bool = False, **kwargs) -> dict:
        model = model or self.default_model
        # Ensure free model suffix
        if not model.endswith(":free") and "/" not in model:
            model = f"meta-llama/llama-3.3-70b-instruct:free"

        payload = {"model": model, "messages": messages}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/free-llm-gateway",
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
