"""
问每个模型"你是什么模型？"，验证身份是否符合预期
"""
import asyncio
import httpx
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GATEWAY = "http://localhost:8000"
TIMEOUT = 40
TEST_MSG = [{"role": "user", "content": "你是什么模型？请直接说出你的模型名称，一句话回答。"}]


async def ask_identity(client: httpx.AsyncClient, model_id: str, owned_by: str):
    try:
        r = await client.post(
            f"{GATEWAY}/v1/chat/completions",
            json={"model": model_id, "messages": TEST_MSG, "stream": False},
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return (model_id, owned_by, False, f"HTTP {r.status_code}", "")

        data = r.json()
        choices = data.get("choices", [])
        if not choices:
            return (model_id, owned_by, False, "no choices", "")

        msg = choices[0].get("message", {})
        content = (msg.get("content") or msg.get("reasoning_content") or "").strip()
        provider_used = data.get("_provider", "?")
        actual_model = data.get("model", "?")

        return (model_id, owned_by, True, provider_used, actual_model, content[:120])

    except Exception as e:
        return (model_id, owned_by, False, repr(e)[:60], "", "")


async def main():
    with urllib.request.urlopen(f"{GATEWAY}/v1/models", timeout=10) as resp:
        models = json.loads(resp.read())["data"]

    print(f"共 {len(models)} 个模型，开始询问身份...\n")

    by_provider: dict[str, list] = {}
    for m in models:
        by_provider.setdefault(m["owned_by"], []).append(m["id"])

    all_results = []

    async with httpx.AsyncClient(trust_env=False) as client:
        for provider, model_ids in by_provider.items():
            print(f"{'='*70}")
            print(f"[{provider.upper()}]")
            sem = asyncio.Semaphore(2)

            async def ask(mid=None, p=None):
                async with sem:
                    res = await ask_identity(client, mid, p)
                    if res[2]:  # success
                        match = "OK" if res[1] == res[3] else "FALLBACK"
                        print(f"  [{match}] {mid}")
                        print(f"         注册provider: {res[1]}  实际provider: {res[3]}")
                        print(f"         实际模型名: {res[4]}")
                        print(f"         回答: {res[5]}")
                    else:
                        print(f"  [FAIL] {mid}  ->  {res[3]}")
                    print()
                    return res

            tasks = [ask(mid=m, p=provider) for m in model_ids]
            results = await asyncio.gather(*tasks)
            all_results.extend(results)
            await asyncio.sleep(1)

    ok       = [r for r in all_results if r[2]]
    fail     = [r for r in all_results if not r[2]]
    fallback = [r for r in ok if r[1] != r[3]]

    print(f"\n{'='*70}")
    print(f"成功: {len(ok)}  失败: {len(fail)}  fallback到其他provider: {len(fallback)}")

    if fallback:
        print(f"\n⚠ 以下模型实际由其他 provider 提供（原 provider 失败）:")
        for r in fallback:
            print(f"  [{r[1]}] {r[0]}")
            print(f"    → 实际走的: [{r[3]}] 模型: {r[4]}")


asyncio.run(main())
