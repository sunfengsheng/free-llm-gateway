import json
import logging
import os
import signal
import subprocess
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv, set_key
load_dotenv()

import httpx
import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from config import Settings, settings
from model_registry import VERIFIED_MODELS
from providers import GeminiProvider, GroqProvider, OpenRouterProvider, CloudflareProvider, G4FProvider, PollinationsProvider

# PyInstaller bundles files under sys._MEIPASS; fall back to script dir in dev
BASE_PATH = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).parent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / response models (OpenAI-compatible subset)
# ---------------------------------------------------------------------------

class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "auto"
    messages: list[Message]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None


# ---------------------------------------------------------------------------
# Build active providers from config
# ---------------------------------------------------------------------------

def build_providers() -> dict:
    available = {}
    if settings.gemini_api_key:
        available["gemini"] = GeminiProvider(settings.gemini_api_key)
        log.info("✓ Gemini provider loaded")
    if settings.groq_api_key:
        available["groq"] = GroqProvider(settings.groq_api_key)
        log.info("✓ Groq provider loaded")
    if settings.openrouter_api_key:
        available["openrouter"] = OpenRouterProvider(settings.openrouter_api_key)
        log.info("✓ OpenRouter provider loaded")
    if settings.cloudflare_account_id and settings.cloudflare_api_token:
        available["cloudflare"] = CloudflareProvider(
            settings.cloudflare_account_id, settings.cloudflare_api_token
        )
        log.info("✓ Cloudflare provider loaded")
    # No-key providers — always available
    available["pollinations"] = PollinationsProvider()
    log.info("✓ Pollinations provider loaded (no key required)")
    available["g4f"] = G4FProvider()
    log.info("✓ g4f provider loaded (no key required)")
    return available


providers: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global providers
    providers = build_providers()
    if not providers:
        log.warning("⚠  No providers configured")
    else:
        order = [p for p in settings.provider_order if p in providers]
        log.info(f"Provider order: {' → '.join(order) or 'none'}")
        log.info("💡 Tip: pollinations & g4f work without any API keys")
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Free LLM Gateway", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    html_path = BASE_PATH / "static" / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/api/status")
async def api_status():
    active = [n for n in settings.provider_order if n in providers]
    return {
        "service": "Free LLM Gateway",
        "active_providers": active,
        "total_providers": len(providers),
        "port": settings.port,
        "keys": {
            "gemini": bool(settings.gemini_api_key),
            "groq": bool(settings.groq_api_key),
            "openrouter": bool(settings.openrouter_api_key),
            "cloudflare": bool(settings.cloudflare_account_id and settings.cloudflare_api_token),
        },
    }


class ConfigUpdate(BaseModel):
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    CF_ACCOUNT_ID: str = ""
    CF_API_TOKEN: str = ""
    PORT: str = ""


@app.post("/api/config")
async def save_config(body: ConfigUpdate, background_tasks: BackgroundTasks):
    global providers
    env_path = Path(".env")
    if not env_path.exists():
        env_path.write_text("")
    new_port = int(body.PORT) if body.PORT else None
    port_changed = bool(new_port and new_port != settings.port)
    for key, val in body.model_dump().items():
        if val:
            set_key(str(env_path), key, val)
            os.environ[key] = val
    new_settings = Settings()
    for attr in ("gemini_api_key", "groq_api_key", "openrouter_api_key",
                 "cloudflare_account_id", "cloudflare_api_token"):
        setattr(settings, attr, getattr(new_settings, attr))
    providers = build_providers()
    if port_changed:
        background_tasks.add_task(_restart_on_port, new_port)
    return {"ok": True, "active_providers": list(providers.keys()),
            "restart_required": port_changed, "new_port": new_port if port_changed else None}


async def _restart_on_port(port: int):
    import asyncio
    await asyncio.sleep(1.5)
    # 打包成 exe 时直接运行自身；开发模式用 uvicorn
    if getattr(sys, "frozen", False):
        subprocess.Popen([sys.executable, f"--port={port}"])
    else:
        subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app",
                          "--host", settings.host, "--port", str(port)])
    await asyncio.sleep(0.8)
    os.kill(os.getpid(), signal.SIGTERM)


@app.get("/v1/models")
async def list_models():
    model_list = []
    for provider_name, models in VERIFIED_MODELS.items():
        if provider_name not in providers:
            continue
        for model_id in models:
            model_list.append({
                "id": model_id,
                "object": "model",
                "owned_by": provider_name,
            })
    return {"object": "list", "data": model_list}


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    messages = [m.model_dump() for m in req.messages]
    kwargs = {}
    if req.temperature is not None:
        kwargs["temperature"] = req.temperature
    if req.max_tokens is not None:
        kwargs["max_tokens"] = req.max_tokens

    # 如果指定了具体模型，优先找对应 provider
    model_to_provider = {
        m: p for p, ms in VERIFIED_MODELS.items() for m in ms
    }
    for m in VERIFIED_MODELS.get("pollinations", []):
        model_to_provider[m.replace("pollinations/", "")] = "pollinations"

    # 指定了具名模型：只用对应 provider，失败直接报错，不乱 fallback 到其他模型
    # auto / 未知模型名：走完整 fallback 链
    if req.model != "auto" and req.model in model_to_provider:
        target = model_to_provider[req.model]
        order = [target]
    else:
        order = [p for p in settings.provider_order if p in providers]

    if not order:
        raise HTTPException(503, "No providers configured. Add API keys to .env")

    errors = {}
    result = None
    for name in order:
        provider = providers[name]

        # 模型名选择：
        # 1. "auto" → 用 provider 默认模型
        # 2. 模型在 registry 里且属于本 provider → 用请求的模型名
        # 3. 模型不在 registry → 用 provider 默认模型（避免 404）
        if req.model == "auto":
            model = None
        elif req.model in model_to_provider and model_to_provider[req.model] == name:
            model = req.model
        else:
            model = None  # 不认识这个模型名，用默认

        if name == "pollinations" and model and model.startswith("pollinations/"):
            model = model.replace("pollinations/", "")
        try:
            log.info(f"Trying {name} (model={model or 'default'}) ...")
            result = await provider.chat(messages, model=model, stream=False, **kwargs)
            log.info(f"✓ {name} succeeded")
            if isinstance(result, dict):
                result.setdefault("_provider", name)
            break
        except httpx.HTTPStatusError as e:
            msg = f"HTTP {e.response.status_code}"
            log.warning(f"✗ {name} failed: {msg}")
            errors[name] = msg
        except Exception as e:
            log.warning(f"✗ {name} failed: {e}")
            errors[name] = str(e)

    if result is None:
        raise HTTPException(503, detail={"message": "All providers failed", "errors": errors})

    # 非流式请求直接返回
    if not req.stream:
        return result

    # 流式请求：把完整响应包装成 SSE 事件流返回给 Cherry Studio 等客户端
    async def sse_stream():
        choices = result.get("choices", [])
        content = ""
        if choices:
            msg = choices[0].get("message", {})
            content = msg.get("content") or msg.get("reasoning_content") or ""

        chunk_id = result.get("id") or f"chatcmpl-{uuid.uuid4().hex}"
        model_name = result.get("model", req.model)
        created = result.get("created", int(time.time()))

        # 第一个 chunk：role
        first = {
            "id": chunk_id, "object": "chat.completion.chunk",
            "created": created, "model": model_name,
            "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}]
        }
        yield f"data: {json.dumps(first)}\n\n"

        # 把内容切成小块逐字发送，模拟流式效果
        chunk_size = 4
        for i in range(0, len(content), chunk_size):
            piece = content[i:i + chunk_size]
            chunk = {
                "id": chunk_id, "object": "chat.completion.chunk",
                "created": created, "model": model_name,
                "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}]
            }
            yield f"data: {json.dumps(chunk)}\n\n"

        # 结束 chunk
        end = {
            "id": chunk_id, "object": "chat.completion.chunk",
            "created": created, "model": model_name,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
        }
        yield f"data: {json.dumps(end)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=settings.port)
    parser.add_argument("--host", default=settings.host)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
