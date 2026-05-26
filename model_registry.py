# 经过实际测试验证的可用模型列表（2026-05-25）
# 网关的 /v1/models 端点从这里读取

VERIFIED_MODELS = {
    "gemini": [
        # 配额刷新后可用（1500次/天），当前 429 fallback 到 Groq
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
    ],
    "groq": [
        # 极速，14400次/天，已验证
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    ],
    "openrouter": [
        # 已验证直连，google/gemma-4-26b 实测 fallback 到 groq，移除
        "openai/gpt-oss-120b:free",
        "openai/gpt-oss-20b:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "liquid/lfm-2.5-1.2b-instruct:free",
    ],
    "cloudflare": [
        # 12 个全部直连验证通过
        "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        "@cf/meta/llama-4-scout-17b-16e-instruct",
        "@cf/meta/llama-3.2-3b-instruct",
        "@cf/meta/llama-3.1-8b-instruct-fp8",
        "@cf/mistralai/mistral-small-3.1-24b-instruct",
        "@cf/google/gemma-3-12b-it",
        "@cf/qwen/qwen2.5-coder-32b-instruct",
        "@cf/moonshotai/kimi-k2.5",
        "@cf/moonshotai/kimi-k2.6",
        "@cf/openai/gpt-oss-120b",
        "@cf/openai/gpt-oss-20b",
        "@cf/nvidia/nemotron-3-120b-a12b",
    ],
    "pollinations": [
        # 只保留 openai，其余实测 fallback 到 groq
        "pollinations/openai",
    ],
    # g4f 不暴露具名模型，仅作最后兜底 fallback
}
