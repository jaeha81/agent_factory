"""
core/llm_router.py
JH Agent Factory — 지능형 LLM 라우터

기능:
  - task_class(light/general/coding/high_precision)별 프로바이더 우선순위 라우팅
  - 무료 → 저비용 → 프리미엄 자동 승격(failover + escalation)
  - config/llm_routing.yaml 기반 설정 (프로바이더 교체 용이)
  - 응답 정규화(response_normalizer) 연동
  - logs/llm_usage.jsonl에 모든 요청 기록
  - 예산 가드(일/월 한도 초과 시 유료 차단)

사용법:
  from core.llm_router import route, route_chat

  # 구조화 응답
  result = await route("general", prompt, agent_id="A0001")

  # 채팅 (기존 ai_router.chat 대체)
  result = await route_chat(session_id, user_message, system_prompt, task_class="general")
"""

import json
import os
import sys
import time
import logging
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Optional

# ── 경로 ──
_CORE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _CORE_DIR.parent
_CONFIG_PATH = _PROJECT_ROOT / "config" / "llm_routing.yaml"
_USAGE_LOG = _PROJECT_ROOT / "logs" / "llm_usage.jsonl"

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ── 기존 ai_router 재사용 ──
from core.ai_router import (
    _is_available as _legacy_is_available,
    _call_sync, _call_async, _mark_failed,
    _provider_failures, _HAS_HTTPX,
    get_session, add_message, get_chat_messages, clear_session,
    PROVIDERS as LEGACY_PROVIDERS,
)

try:
    import yaml
except ImportError:
    yaml = None

try:
    from core.response_normalizer import normalize, validate_schema
except ImportError:
    normalize = None
    validate_schema = None

logger = logging.getLogger("llm_router")

# ═══════════════════════════════════════════════════════
# 설정 로딩
# ═══════════════════════════════════════════════════════

def _load_config() -> dict:
    """config/llm_routing.yaml 로드. 없으면 기본값 반환."""
    if yaml and _CONFIG_PATH.is_file():
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    # yaml 미설치 시 최소 기본값
    return {
        "providers": {},
        "routing_chain": {
            "light": ["groq", "gemini_flash", "openrouter_free"],
            "general": ["groq", "gemini_flash", "together_free", "openrouter_free"],
            "coding": ["together_free", "gemini_flash", "groq"],
            "high_precision": ["groq", "gemini_flash", "together_free"],
        },
        "failover": {"cooldown_sec": 60, "max_retries_per_provider": 1},
        "escalation": {"schema_mismatch_threshold": 2, "consecutive_fail_threshold": 3,
                        "auto_escalate_to_tier": "low_cost"},
        "budget": {"daily_limit_usd": 1.0, "monthly_limit_usd": 20.0, "block_on_exceed": True},
    }


_config = _load_config()


def reload_config():
    """설정 핫 리로드."""
    global _config
    _config = _load_config()


# ═══════════════════════════════════════════════════════
# 프로바이더 레지스트리
# ═══════════════════════════════════════════════════════

def _build_provider_registry() -> dict:
    """
    YAML 설정의 providers + 기존 LEGACY_PROVIDERS를 통합하여
    name → provider dict 매핑을 구축.
    """
    registry = {}

    # 1) 기존 ai_router의 PROVIDERS를 기본으로 등록 (하위호환)
    legacy_name_map = {
        "groq": "groq", "gemini": "gemini_flash",
        "together": "together_free", "openrouter": "openrouter_free",
    }
    for lp in LEGACY_PROVIDERS:
        mapped_name = legacy_name_map.get(lp["name"], lp["name"])
        registry[mapped_name] = {**lp, "tier": "free", "mapped_legacy": lp["name"]}

    # 2) YAML 설정으로 오버라이드/추가
    for name, prov_cfg in _config.get("providers", {}).items():
        if name in registry:
            registry[name].update(prov_cfg)
        else:
            registry[name] = {**prov_cfg, "name": name}

    return registry


_providers = _build_provider_registry()


def _get_provider(name: str) -> Optional[dict]:
    """이름으로 프로바이더 조회."""
    return _providers.get(name)


def _is_provider_available(prov: dict) -> bool:
    """프로바이더 사용 가능 여부 (키 존재 + 쿨다운 미적용)."""
    key_env = prov.get("key_env", "")
    if not os.environ.get(key_env, ""):
        return False
    cooldown = _config.get("failover", {}).get("cooldown_sec", 60)
    prov_name = prov.get("mapped_legacy", prov.get("name", ""))
    fail_time = _provider_failures.get(prov_name)
    if fail_time and (time.time() - fail_time) < cooldown:
        return False
    return True


# ═══════════════════════════════════════════════════════
# 예산 가드
# ═══════════════════════════════════════════════════════

_daily_spend: dict = {}   # "YYYY-MM-DD" → float (USD)
_monthly_spend: dict = {}  # "YYYY-MM" → float (USD)


def _record_cost(cost_usd: float):
    """비용 기록."""
    today = date.today().isoformat()
    month = today[:7]
    _daily_spend[today] = _daily_spend.get(today, 0.0) + cost_usd
    _monthly_spend[month] = _monthly_spend.get(month, 0.0) + cost_usd


def _check_budget(tier: str) -> tuple:
    """예산 확인. (allowed: bool, reason: str)"""
    if tier == "free":
        return True, ""

    budget = _config.get("budget", {})
    if not budget.get("block_on_exceed", True):
        return True, ""

    today = date.today().isoformat()
    month = today[:7]
    daily = _daily_spend.get(today, 0.0)
    monthly = _monthly_spend.get(month, 0.0)
    daily_limit = budget.get("daily_limit_usd", 1.0)
    monthly_limit = budget.get("monthly_limit_usd", 20.0)

    if daily >= daily_limit:
        return False, f"일일 예산 초과 (${daily:.4f} / ${daily_limit})"
    if monthly >= monthly_limit:
        return False, f"월간 예산 초과 (${monthly:.4f} / ${monthly_limit})"
    return True, ""


def get_budget_status() -> dict:
    """현재 예산 상태."""
    budget = _config.get("budget", {})
    today = date.today().isoformat()
    month = today[:7]
    return {
        "daily_spent": round(_daily_spend.get(today, 0.0), 6),
        "daily_limit": budget.get("daily_limit_usd", 1.0),
        "monthly_spent": round(_monthly_spend.get(month, 0.0), 6),
        "monthly_limit": budget.get("monthly_limit_usd", 20.0),
    }


# ═══════════════════════════════════════════════════════
# 사용량 로그
# ═══════════════════════════════════════════════════════

def _log_usage(entry: dict):
    """logs/llm_usage.jsonl에 요청 기록."""
    _USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(_USAGE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ═══════════════════════════════════════════════════════
# 저수준 호출 (기존 ai_router 함수 래핑)
# ═══════════════════════════════════════════════════════

async def _call_provider(prov: dict, messages: list) -> str:
    """단일 프로바이더 호출. 기존 ai_router의 _call_async/_call_sync 재사용."""
    # 기존 레거시 프로바이더 형식으로 변환
    legacy_prov = {
        "name": prov.get("mapped_legacy", prov.get("name")),
        "url": prov["url"],
        "key_env": prov["key_env"],
        "model": prov["model"],
        "max_tokens": prov.get("max_tokens", 2048),
        "format": prov.get("format", "openai"),
    }

    if prov.get("format") == "anthropic":
        return await _call_anthropic(prov, messages)

    if _HAS_HTTPX:
        return await _call_async(legacy_prov, messages)
    else:
        return _call_sync(legacy_prov, messages)


async def _call_anthropic(prov: dict, messages: list) -> str:
    """Anthropic Messages API 호출."""
    import httpx

    key = os.environ.get(prov["key_env"], "")
    system_text = ""
    api_messages = []
    for m in messages:
        if m["role"] == "system":
            system_text += m["content"] + "\n"
        else:
            api_messages.append({"role": m["role"], "content": m["content"]})

    payload = {
        "model": prov["model"],
        "max_tokens": prov.get("max_tokens", 4096),
        "messages": api_messages,
    }
    if system_text.strip():
        payload["system"] = system_text.strip()

    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    async with httpx.AsyncClient(timeout=prov.get("timeout_sec", 120)) as client:
        resp = await client.post(prov["url"], json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    return data["content"][0]["text"]


# ═══════════════════════════════════════════════════════
# 핵심 라우팅 함수
# ═══════════════════════════════════════════════════════

async def route(
    task_class: str = "general",
    prompt: str = "",
    *,
    system_prompt: str = "",
    messages: Optional[list] = None,
    agent_id: str = "",
    priority: str = "normal",
    require_structured: bool = False,
) -> dict:
    """
    task_class에 따라 최적 프로바이더를 선택하여 LLM을 호출한다.

    Args:
        task_class: light | general | coding | high_precision
        prompt: 사용자 메시지 (messages가 없을 때 사용)
        system_prompt: 시스템 프롬프트
        messages: 전체 메시지 리스트 (있으면 prompt 무시)
        agent_id: 호출한 에이전트 ID (로깅용)
        priority: normal | high | critical (critical이면 premium 즉시 시도)
        require_structured: True면 응답 정규화 강제

    Returns:
        {"reply": str, "provider": str, "model": str, "tier": str,
         "task_class": str, "latency_ms": int, "retries": int,
         "failover_count": int, "escalated": bool, "error": str|None,
         "normalized": dict|None}
    """
    # 메시지 구성
    if messages is None:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

    # task_class 설정
    tc_config = _config.get("task_classes", {}).get(task_class, {})

    # 라우팅 체인 결정
    chain = list(_config.get("routing_chain", {}).get(task_class, ["groq", "gemini_flash"]))

    # critical 우선순위면 premium을 체인 앞에 추가
    if priority == "critical":
        premium_provs = [n for n, p in _providers.items() if p.get("tier") == "premium"]
        chain = premium_provs + [c for c in chain if c not in premium_provs]

    # 순회 변수
    retries = 0
    failover_count = 0
    escalated = False
    consecutive_schema_fails = 0
    last_error = None
    start_time = time.time()
    escalation_cfg = _config.get("escalation", {})

    # 승격 대상 체인 (필요시 추가)
    escalation_chain = []

    for prov_name in chain:
        prov = _get_provider(prov_name)
        if not prov:
            continue
        if not _is_provider_available(prov):
            continue

        tier = prov.get("tier", "free")

        # 예산 검사 (유료 프로바이더)
        budget_ok, budget_reason = _check_budget(tier)
        if not budget_ok:
            logger.info("예산 초과로 %s 건너뜀: %s", prov_name, budget_reason)
            continue

        try:
            call_start = time.time()
            reply = await _call_provider(prov, messages)
            latency_ms = int((time.time() - call_start) * 1000)

            # 쿨다운 해제
            legacy_name = prov.get("mapped_legacy", prov_name)
            _provider_failures.pop(legacy_name, None)

            # 비용 기록
            cost = prov.get("cost_per_1k_tokens", 0.0)
            if cost > 0:
                estimated_tokens = len(reply) / 4 + len(prompt or "") / 4
                _record_cost(cost * estimated_tokens / 1000)

            # 응답 정규화 (선택적)
            normalized = None
            if require_structured and normalize:
                normalized = normalize(reply)
                if normalized.get("_valid") is False:
                    consecutive_schema_fails += 1
                    threshold = escalation_cfg.get("schema_mismatch_threshold", 2)
                    if consecutive_schema_fails >= threshold:
                        # 승격 트리거
                        escalated = True
                        _append_escalation_chain(escalation_chain, tier, chain)
                        # 다음 후보로 넘어감
                        failover_count += 1
                        last_error = f"스키마 불일치 {consecutive_schema_fails}회 (승격 발동)"
                        continue
                else:
                    consecutive_schema_fails = 0

            # 성공 로깅
            _log_usage({
                "agent_id": agent_id,
                "provider": prov_name,
                "model": prov.get("model", ""),
                "tier": tier,
                "task_class": task_class,
                "success": True,
                "latency_ms": latency_ms,
                "retries": retries,
                "failover_count": failover_count,
                "escalated": escalated,
            })

            return {
                "reply": reply,
                "provider": prov_name,
                "model": prov.get("model", ""),
                "tier": tier,
                "task_class": task_class,
                "latency_ms": latency_ms,
                "retries": retries,
                "failover_count": failover_count,
                "escalated": escalated,
                "error": None,
                "normalized": normalized,
            }

        except Exception as e:
            retries += 1
            failover_count += 1
            last_error = f"[{prov_name}] {e}"
            logger.warning("Provider %s 실패: %s", prov_name, e)
            legacy_name = prov.get("mapped_legacy", prov_name)
            _mark_failed(legacy_name)

            # 연속 실패 승격 검사
            fail_threshold = escalation_cfg.get("consecutive_fail_threshold", 3)
            if failover_count >= fail_threshold and not escalated:
                escalated = True
                _append_escalation_chain(escalation_chain, "free", chain)

            continue

    # 승격 체인 시도
    if escalation_chain:
        for prov_name in escalation_chain:
            if prov_name in chain:
                continue  # 이미 시도한 것은 건너뜀
            prov = _get_provider(prov_name)
            if not prov or not _is_provider_available(prov):
                continue
            tier = prov.get("tier", "free")
            budget_ok, _ = _check_budget(tier)
            if not budget_ok:
                continue
            try:
                call_start = time.time()
                reply = await _call_provider(prov, messages)
                latency_ms = int((time.time() - call_start) * 1000)
                legacy_name = prov.get("mapped_legacy", prov_name)
                _provider_failures.pop(legacy_name, None)

                cost = prov.get("cost_per_1k_tokens", 0.0)
                if cost > 0:
                    estimated_tokens = len(reply) / 4 + len(prompt or "") / 4
                    _record_cost(cost * estimated_tokens / 1000)

                normalized = None
                if require_structured and normalize:
                    normalized = normalize(reply)

                _log_usage({
                    "agent_id": agent_id,
                    "provider": prov_name,
                    "model": prov.get("model", ""),
                    "tier": tier,
                    "task_class": task_class,
                    "success": True,
                    "latency_ms": latency_ms,
                    "retries": retries,
                    "failover_count": failover_count,
                    "escalated": True,
                })

                return {
                    "reply": reply, "provider": prov_name,
                    "model": prov.get("model", ""), "tier": tier,
                    "task_class": task_class, "latency_ms": latency_ms,
                    "retries": retries, "failover_count": failover_count,
                    "escalated": True, "error": None, "normalized": normalized,
                }
            except Exception as e:
                last_error = f"[escalation:{prov_name}] {e}"
                legacy_name = prov.get("mapped_legacy", prov_name)
                _mark_failed(legacy_name)
                continue

    # 모든 프로바이더 실패
    total_ms = int((time.time() - start_time) * 1000)
    error_msg = last_error or "사용 가능한 AI 프로바이더가 없습니다."

    _log_usage({
        "agent_id": agent_id,
        "provider": "",
        "model": "",
        "tier": "",
        "task_class": task_class,
        "success": False,
        "latency_ms": total_ms,
        "retries": retries,
        "failover_count": failover_count,
        "escalated": escalated,
        "error": error_msg[:200],
    })

    return {
        "reply": "", "provider": "", "model": "", "tier": "",
        "task_class": task_class, "latency_ms": total_ms,
        "retries": retries, "failover_count": failover_count,
        "escalated": escalated, "error": error_msg, "normalized": None,
    }


def _append_escalation_chain(esc_chain: list, current_tier: str, tried: list):
    """승격 대상 프로바이더를 체인에 추가."""
    esc_cfg = _config.get("escalation", {})
    target_tier = esc_cfg.get("auto_escalate_to_tier", "low_cost")

    tiers_order = ["free", "low_cost", "premium"]
    try:
        current_idx = tiers_order.index(current_tier)
    except ValueError:
        current_idx = 0

    target_idx = tiers_order.index(target_tier) if target_tier in tiers_order else 1

    # 현재 티어보다 높은 프로바이더 추가
    for name, prov in _providers.items():
        prov_tier = prov.get("tier", "free")
        if prov_tier in tiers_order[max(target_idx, current_idx + 1):]:
            continue
        if prov_tier in tiers_order[target_idx:] and name not in esc_chain and name not in tried:
            esc_chain.append(name)

    # premium까지 필요하면 추가
    premium_after = esc_cfg.get("premium_escalate_after", 2)
    if len(esc_chain) <= premium_after:
        for name, prov in _providers.items():
            if prov.get("tier") == "premium" and name not in esc_chain:
                esc_chain.append(name)


# ═══════════════════════════════════════════════════════
# 채팅 라우터 (기존 ai_router.chat 대체)
# ═══════════════════════════════════════════════════════

async def route_chat(
    session_id: str,
    user_message: str,
    system_prompt: str,
    task_class: str = "general",
    agent_id: str = "",
) -> dict:
    """
    기존 ai_router.chat()를 대체하는 지능형 채팅 라우터.
    세션 관리는 기존 ai_router의 세션 시스템 재사용.

    Returns: {"reply", "provider", "model", "tier", "error", ...}
    """
    add_message(session_id, "user", user_message)
    messages = get_chat_messages(session_id, system_prompt)

    result = await route(
        task_class=task_class,
        messages=messages,
        agent_id=agent_id,
    )

    if result.get("error") is None and result.get("reply"):
        add_message(session_id, "assistant", result["reply"])

    return result


# ═══════════════════════════════════════════════════════
# 상태 조회
# ═══════════════════════════════════════════════════════

def get_router_status() -> dict:
    """라우터 전체 상태."""
    providers_status = []
    for name, prov in _providers.items():
        key_set = bool(os.environ.get(prov.get("key_env", ""), ""))
        available = _is_provider_available(prov) if key_set else False
        providers_status.append({
            "name": name,
            "model": prov.get("model", ""),
            "tier": prov.get("tier", "free"),
            "key_set": key_set,
            "available": available,
        })

    return {
        "providers": providers_status,
        "budget": get_budget_status(),
        "config_loaded": _CONFIG_PATH.is_file(),
        "httpx_available": _HAS_HTTPX,
    }


def get_routing_chain(task_class: str = "general") -> list:
    """특정 task_class의 라우팅 체인 조회."""
    return list(_config.get("routing_chain", {}).get(task_class, []))
