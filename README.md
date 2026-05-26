# Free LLM Gateway

OpenAI 兼容的统一 API 网关，聚合多个免费大模型提供商，自动 fallback。

## 支持的免费 Provider

| Provider | 免费额度 | 申请地址 |
|----------|---------|---------|
| **Google Gemini** | 1500 次/天，15 次/分 | https://aistudio.google.com/apikey |
| **Groq** | 14400 次/天，30 次/分 | https://console.groq.com/keys |
| **OpenRouter** | 20 次/分（免费模型） | https://openrouter.ai/keys |
| **Cloudflare Workers AI** | 10000 neurons/天 | https://dash.cloudflare.com → Workers AI |
| **Pollinations** | 无限制，无需注册 | 开箱即用 |
| **g4f** | 无需 Key，兜底用 | 开箱即用 |

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env，填入你有的 Key（pollinations/g4f 无需 Key，开箱即用）

# 3. 启动网关
python main.py
# 服务运行在 http://localhost:8000
```

## 使用方式

网关完全兼容 OpenAI API 格式：

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed",
)

response = client.chat.completions.create(
    model="auto",  # 自动选择可用 provider
    messages=[{"role": "user", "content": "你好"}]
)
print(response.choices[0].message.content)
```

```bash
# 或直接 curl
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"auto","messages":[{"role":"user","content":"你好"}]}'
```

## 已验证可用模型（2026-05-26）

通过 `/v1/models` 接口获取完整列表。以下为实测验证过的模型：

| Provider | 模型 |
|----------|------|
| Groq | `llama-3.3-70b-versatile` · `llama-3.1-8b-instant` |
| OpenRouter | `openai/gpt-oss-120b:free` · `openai/gpt-oss-20b:free` · `nvidia/nemotron-3-super-120b-a12b:free` · `liquid/lfm-2.5-1.2b-instruct:free` |
| Cloudflare | `@cf/meta/llama-3.3-70b-instruct-fp8-fast` · `@cf/meta/llama-4-scout-17b-16e-instruct` · `@cf/meta/llama-3.2-3b-instruct` · `@cf/meta/llama-3.1-8b-instruct-fp8` · `@cf/mistralai/mistral-small-3.1-24b-instruct` · `@cf/google/gemma-3-12b-it` · `@cf/qwen/qwen2.5-coder-32b-instruct` · `@cf/moonshotai/kimi-k2.5` · `@cf/moonshotai/kimi-k2.6` · `@cf/openai/gpt-oss-120b` · `@cf/openai/gpt-oss-20b` · `@cf/nvidia/nemotron-3-120b-a12b` |
| Pollinations | `pollinations/openai` |
| Gemini | `gemini-2.0-flash` · `gemini-2.0-flash-lite` · `gemini-1.5-flash`（每天配额耗尽后返回 503） |

## Fallback 逻辑

- **指定具名模型**（如 `@cf/openai/gpt-oss-120b`）：只走对应 provider，失败直接报错，不会静默换成其他模型
- **`auto` 或未知模型名**：按 `PROVIDER_ORDER` 顺序依次尝试，任意 provider 成功即返回

```
auto 请求 → Gemini → Groq → OpenRouter → Cloudflare → Pollinations → g4f → 503
```

响应中带 `_provider` 字段，说明实际使用了哪个 provider。

## 接口

| 接口 | 说明 |
|------|------|
| `GET /` | 查看活跃 providers |
| `GET /v1/models` | 列出所有可用模型 |
| `POST /v1/chat/completions` | 发送聊天请求（OpenAI 格式） |

## 在 Cherry Studio 中使用

1. 设置 → 模型服务 → 添加 → OpenAI 兼容
2. API 地址填 `http://localhost:8000/v1`
3. API Key 随便填（不校验）
4. 点击"获取模型列表"

## 许可证

MIT
