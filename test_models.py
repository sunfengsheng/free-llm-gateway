"""
通过网关接口测试所有已注册模型是否真实可用
"""
import asyncio
import httpx
import json
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GATEWAY = "http://localhost:8000"
TEST_MSG = [{"role": "user", "content": "用一个词回答：天空是什么颜色？"}]
TIMEOUT = 40


async def test_model(client: httpx.AsyncClient, model_id: str, owned_by: str):
    start = time.time()
    try:
        r = await client.post(
            f"{GATEWAY}/v1/chat/completions",
            json={"model": model_id, "messages": TEST_MSG, "stream": False},
            timeout=TIMEOUT,
        )
        elapsed = time.time() - start

        if r.status_code != 200:
            return (model_id, owned_by, False, f"HTTP {r.status_code}", elapsed)

        data = r.json()

        # 检查是否有实际内容
        choices = data.get("choices", [])
        if not choices:
            return (model_id, owned_by, False, "no choices", elapsed)

        msg = choices[0].get("message", {})
        content = msg.get("content") or msg.get("reasoning_content") or ""
        if not content or not content.strip():
            return (model_id, owned_by, False, "empty content", elapsed)

        provider_used = data.get("_provider", "?")
        return (model_id, owned_by, True, f"via {provider_used} | {content.strip()[:40]}", elapsed)

    except Exception as e:
        elapsed = time.time() - start
        return (model_id, owned_by, False, repr(e)[:80], elapsed)


async def main():
    # 从网关拉取模型列表（同步避免事件循环问题）
    import urllib.request
    with urllib.request.urlopen(f"{GATEWAY}/v1/models", timeout=10) as resp:
        models = json.loads(resp.read())["data"]

    print(f"网关共注册 {len(models)} 个模型，开始测试...\n")

    # 按 provider 分组，每组并发3个，避免限速
    by_provider: dict[str, list] = {}
    for m in models:
        by_provider.setdefault(m["owned_by"], []).append(m["id"])

    all_results = []

    async with httpx.AsyncClient(trust_env=False) as client:
        for provider, model_ids in by_provider.items():
            print(f"--- {provider.upper()} ({len(model_ids)} 个) ---")
            sem = asyncio.Semaphore(3)

            async def bounded(mid=None, p=None):
                async with sem:
                    res = await test_model(client, mid, p)
                    status = "OK" if res[2] else "--"
                    print(f"  [{status}] {res[0][:55]:<55} {res[4]:.1f}s  {res[3]}")
                    return res

            tasks = [bounded(mid=m, p=provider) for m in model_ids]
            results = await asyncio.gather(*tasks)
            all_results.extend(results)
            await asyncio.sleep(1)  # provider 之间稍作间隔

    # 汇总
    ok   = [r for r in all_results if r[2]]
    fail = [r for r in all_results if not r[2]]

    print(f"\n{'='*65}")
    print(f"可用: {len(ok)}  不可用: {len(fail)}  共: {len(all_results)}")
    print(f"{'='*65}")

    if ok:
        print(f"\n✓ 可用模型 ({len(ok)} 个):")
        for r in ok:
            print(f"  [{r[1]}] {r[0]}")

    if fail:
        print(f"\n✗ 不可用 ({len(fail)} 个):")
        for r in fail:
            print(f"  [{r[1]}] {r[0]}  →  {r[3]}")

    # 保存结果
    out = {
        "tested_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ok": [{"model": r[0], "provider": r[1]} for r in ok],
        "fail": [{"model": r[0], "provider": r[1], "reason": r[3]} for r in fail],
    }
    with open("C:/Users/sun/AppData/Local/Temp/model_test_results.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("\n结果已保存到 model_test_results.json")


asyncio.run(main())
