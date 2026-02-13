"""
core/ai_router.py
무료 AI API 4개를 순차 폴백으로 연결하는 라우터.
세션별 슬라이딩 윈도우 컨텍스트 관리 포함.

프로바이더 우선순위: Groq → Gemini → Together → OpenRouter
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path

# dotenv
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

# async http — httpx 우선, 없으면 urllib 동기 폴백
try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    import urllib.request
    import urllib.error
    _HAS_HTTPX = False

logger = logging.getLogger("ai_router")

# ─── 프로바이더 설정 ─────────────────────────────────
PROVIDERS = [
    {
        "name": "groq",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_env": "GROQ_API_KEY",
        "model": "llama-3.1-8b-instant",
        "max_tokens": 2048,
        "format": "openai",
    },
    {
        "name": "gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "key_env": "GEMINI_API_KEY",
        "model": "gemini-2.0-flash",
        "max_tokens": 2048,
        "format": "gemini",
    },
    {
        "name": "together",
        "url": "https://api.together.xyz/v1/chat/completions",
        "key_env": "TOGETHER_API_KEY",
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
        "max_tokens": 2048,
        "format": "openai",
    },
    {
        "name": "openrouter",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key_env": "OPENROUTER_API_KEY",
        "model": "meta-llama/llama-3.1-8b-instruct:free",
        "max_tokens": 2048,
        "format": "openai",
    },
]

COOLDOWN_SEC = 60
MAX_HISTORY = 20

# ─── 런타임 상태 ─────────────────────────────────────
_provider_failures: dict[str, float] = {}   # name → fail_timestamp
_sessions: dict[str, dict] = {}             # session_id → {messages, created}


# ═══════════════════════════════════════════════════════
# 세션 관리
# ═══════════════════════════════════════════════════════

def get_session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {
            "messages": [],
            "created": datetime.now(timezone.utc).isoformat(),
        }
    return _sessions[session_id]


def add_message(session_id: str, role: str, content: str):
    sess = get_session(session_id)
    sess["messages"].append({"role": role, "content": content})
    # 슬라이딩 윈도우: MAX_HISTORY 초과 시 앞부분 요약 압축
    if len(sess["messages"]) > MAX_HISTORY:
        _compress_history(sess)


def _compress_history(sess: dict):
    msgs = sess["messages"]
    # 앞 절반을 요약 텍스트로 압축
    half = len(msgs) // 2
    old_msgs = msgs[:half]
    summary_parts = []
    for m in old_msgs:
        tag = "사용자" if m["role"] == "user" else "AI"
        summary_parts.append(f"[{tag}] {m['content'][:80]}")
    summary = "[이전 대화 요약]\n" + "\n".join(summary_parts)
    sess["messages"] = [{"role": "system", "content": summary}] + msgs[half:]


def get_chat_messages(session_id: str, system_prompt: str) -> list[dict]:
    sess = get_session(session_id)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(sess["messages"])
    return messages


def clear_session(session_id: str):
    _sessions.pop(session_id, None)


# ═══════════════════════════════════════════════════════
# 프로바이더 호출
# ═══════════════════════════════════════════════════════

def _is_available(provider: dict) -> bool:
    name = provider["name"]
    key = os.environ.get(provider["key_env"], "")
    if not key:
        return False
    fail_time = _provider_failures.get(name)
    if fail_time and (time.time() - fail_time) < COOLDOWN_SEC:
        return False
    return True


def _mark_failed(name: str):
    _provider_failures[name] = time.time()


def _build_openai_payload(provider: dict, messages: list[dict]) -> dict:
    return {
        "model": provider["model"],
        "messages": messages,
        "max_tokens": provider["max_tokens"],
        "temperature": 0.7,
    }


def _build_gemini_payload(messages: list[dict]) -> tuple[dict, str]:
    """Gemini 형식 변환. (system → systemInstruction, user/assistant → contents)"""
    system_text = ""
    contents = []
    for m in messages:
        if m["role"] == "system":
            system_text += m["content"] + "\n"
        else:
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})

    payload = {"contents": contents}
    if system_text.strip():
        payload["systemInstruction"] = {"parts": [{"text": system_text.strip()}]}
    payload["generationConfig"] = {"maxOutputTokens": 2048, "temperature": 0.7}
    return payload


def _parse_openai_response(data: dict) -> str:
    return data["choices"][0]["message"]["content"]


def _parse_gemini_response(data: dict) -> str:
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _call_sync(provider: dict, messages: list[dict]) -> str:
    """urllib 동기 호출 (httpx 없을 때 폴백)."""
    key = os.environ.get(provider["key_env"], "")
    fmt = provider["format"]

    if fmt == "gemini":
        url = provider["url"].format(model=provider["model"]) + f"?key={key}"
        payload = _build_gemini_payload(messages)
        headers = {"Content-Type": "application/json"}
    else:
        url = provider["url"]
        payload = _build_openai_payload(provider, messages)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        }

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if fmt == "gemini":
        return _parse_gemini_response(data)
    return _parse_openai_response(data)


async def _call_async(provider: dict, messages: list[dict]) -> str:
    """httpx async 호출."""
    key = os.environ.get(provider["key_env"], "")
    fmt = provider["format"]

    if fmt == "gemini":
        url = provider["url"].format(model=provider["model"]) + f"?key={key}"
        payload = _build_gemini_payload(messages)
        headers = {"Content-Type": "application/json"}
    else:
        url = provider["url"]
        payload = _build_openai_payload(provider, messages)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    if fmt == "gemini":
        return _parse_gemini_response(data)
    return _parse_openai_response(data)


# ═══════════════════════════════════════════════════════
# 메인 chat 함수
# ═══════════════════════════════════════════════════════

async def chat(session_id: str, user_message: str, system_prompt: str) -> dict:
    """
    세션에 메시지를 추가하고 AI 응답을 받는다.
    4개 프로바이더를 순차 폴백으로 시도.

    Returns: {"reply": str, "provider": str, "model": str, "error": str|None}
    """
    add_message(session_id, "user", user_message)
    messages = get_chat_messages(session_id, system_prompt)

    last_error = None
    for prov in PROVIDERS:
        if not _is_available(prov):
            continue
        try:
            if _HAS_HTTPX:
                reply = await _call_async(prov, messages)
            else:
                reply = _call_sync(prov, messages)

            # 성공 — 쿨다운 해제
            _provider_failures.pop(prov["name"], None)
            add_message(session_id, "assistant", reply)
            return {
                "reply": reply,
                "provider": prov["name"],
                "model": prov["model"],
                "error": None,
            }
        except Exception as e:
            last_error = f"[{prov['name']}] {e}"
            logger.warning("Provider %s failed: %s", prov["name"], e)
            _mark_failed(prov["name"])
            continue

    # 모든 프로바이더 실패
    error_msg = last_error or "사용 가능한 AI 프로바이더가 없습니다. .env 파일에 API 키를 설정하세요."
    return {
        "reply": "",
        "provider": "",
        "model": "",
        "error": error_msg,
    }


# ═══════════════════════════════════════════════════════
# 상태 조회
# ═══════════════════════════════════════════════════════

def get_router_status() -> dict:
    status = []
    for prov in PROVIDERS:
        key_set = bool(os.environ.get(prov["key_env"], ""))
        fail_time = _provider_failures.get(prov["name"])
        cooldown_left = 0
        if fail_time:
            cooldown_left = max(0, COOLDOWN_SEC - (time.time() - fail_time))

        status.append({
            "name": prov["name"],
            "model": prov["model"],
            "key_set": key_set,
            "available": _is_available(prov),
            "cooldown_remaining": round(cooldown_left, 1),
        })
    return {
        "providers": status,
        "active_sessions": len(_sessions),
        "httpx_available": _HAS_HTTPX,
    }
