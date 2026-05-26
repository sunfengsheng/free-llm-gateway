import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    # Provider API keys — set via environment variables or .env file
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    openrouter_api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    cloudflare_account_id: str = field(default_factory=lambda: os.getenv("CF_ACCOUNT_ID", ""))
    cloudflare_api_token: str = field(default_factory=lambda: os.getenv("CF_API_TOKEN", ""))

    # Provider priority order (first = highest priority)
    # pollinations and g4f require no keys and are always available
    provider_order: list[str] = field(default_factory=lambda: [
        p.strip() for p in os.getenv(
            "PROVIDER_ORDER", "gemini,groq,openrouter,cloudflare,pollinations,g4f"
        ).split(",")
    ])

    # Gateway settings
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))


settings = Settings()
