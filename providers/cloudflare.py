import httpx
from .base import BaseProvider


class CloudflareProvider(BaseProvider):
    name = "cloudflare"
    default_model = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"

    # Free tier: 10,000 neurons/day — requires Cloudflare account (free)
    # Get account_id + api_token: https://dash.cloudflare.com/ → AI → Workers AI
    # Free models: https://developers.cloudflare.com/workers-ai/models/

    def __init__(self, account_id: str, api_token: str):
        self.account_id = account_id
        self.api_token = api_token

    async def chat(self, messages: list, model: str | None = None, stream: bool = False, **kwargs) -> dict:
        model = model or self.default_model
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/{model}"
        headers = {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json={"messages": messages}, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        result = data["result"]

        # 新模型返回 OpenAI 兼容格式（choices），旧模型返回 result.response
        if "choices" in result:
            msg = result["choices"][0]["message"]
            content = msg.get("content") or msg.get("reasoning_content") or ""
            # 直接把整个 result 返回（已经是 OpenAI 格式）
            result["_provider"] = "cloudflare"
            return result
        else:
            content = result["response"]
            return self._openai_response(content, model)
