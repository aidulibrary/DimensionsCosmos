"""免费 AI 额度降级链：Groq → Gemini → OpenRouter 免费模型。
零固定成本：三个平台都有免费层。环境变量里配了哪个 key 就启用哪个；
任一渠道限流/故障自动降级到下一个。配钥匙方法见各平台官网，均免费。

用法：
    import os; os.environ["GROQ_API_KEY"] = "..."
    from ai_client import chat
    print(chat("用 200 字白话概述《论语》"))
"""
import os

import requests

TIMEOUT = 60


def _chat_completions(url, key, model, prompt, system, max_tokens):
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}
    ]
    resp = requests.post(
        url,
        json={"model": model, "messages": messages, "max_tokens": max_tokens},
        headers={"Authorization": f"Bearer {key}"},
        timeout=TIMEOUT,
    )
    if resp.status_code == 429:
        raise RuntimeError("rate limited")
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _groq(prompt, system, max_tokens):
    return _chat_completions(
        "https://api.groq.com/openai/v1/chat/completions",
        os.environ["GROQ_API_KEY"],
        os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        prompt, system, max_tokens,
    )


def _gemini(prompt, system, max_tokens):
    key = os.environ["GEMINI_API_KEY"]
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": key},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            **({"systemInstruction": {"parts": [{"text": system}]}} if system else {}),
            "generationConfig": {"maxOutputTokens": max_tokens},
        },
        timeout=TIMEOUT,
    )
    if resp.status_code == 429:
        raise RuntimeError("rate limited")
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _openrouter(prompt, system, max_tokens):
    return _chat_completions(
        "https://openrouter.ai/api/v1/chat/completions",
        os.environ["OPENROUTER_API_KEY"],
        os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"),
        prompt, system, max_tokens,
    )


_CHAIN = [
    ("groq", _groq, "GROQ_API_KEY"),
    ("gemini", _gemini, "GEMINI_API_KEY"),
    ("openrouter", _openrouter, "OPENROUTER_API_KEY"),
]


def chat(prompt, system=None, max_tokens=1024):
    """按优先级尝试所有已配置渠道，全部失败则报错并列出原因。"""
    errors = []
    for name, fn, env in _CHAIN:
        if not os.getenv(env):
            errors.append(f"{name}: 未配置 {env}")
            continue
        try:
            return fn(prompt, system, max_tokens)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: {exc}")
    raise RuntimeError("免费渠道全部不可用：\n" + "\n".join(errors))
