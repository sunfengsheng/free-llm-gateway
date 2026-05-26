from g4f.client import AsyncClient
from .base import BaseProvider


class G4FProvider(BaseProvider):
    name = "g4f"
    default_model = "gpt-4o-mini"

    # gpt4free: 逆向工程多个 AI 服务，无需任何 API Key
    # 支持的模型/provider 见: https://github.com/xtekky/gpt4free
    # 注意: 属于逆向工程，稳定性不如官方接口，仅供学习研究

    PROVIDER_MAP = {
        "gpt-4o": "Blackbox",
        "gpt-4o-mini": "Blackbox",
        "claude-3-haiku": "Liaobots",
        "gemini-pro": "GeminiPro",
        "deepseek-r1": "DeepSeekAPI",
        "llama-3-70b": "Blackbox",
    }

    def __init__(self):
        self.client = AsyncClient()

    async def chat(self, messages: list, model: str | None = None, stream: bool = False, **kwargs) -> dict:
        model = model or self.default_model
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
        )
        # g4f already returns OpenAI-compatible objects; convert to dict
        choice = response.choices[0]
        return self._openai_response(choice.message.content, model)
