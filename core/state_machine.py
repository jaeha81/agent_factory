"""
state_machine.py
에이전트 상태 머신 + 자동 감시

상태 전이 다이어그램:
  created → online → dormant → online (재활성)
                   → suspended → online (소유자 승인)
                   → training → online (훈련 완료)
  online → error → online (복구)

  * = 어떤 상태에서든 → terminated (삭제)

상태 설명:
  online     — 활성, 작업 수행 가능
  dormant    — 휴면, 일정 시간 미사용 시 자동 전환
  suspended  — 정지, 소유자/마스터 명령으로만 해제
  training   — 훈련 중, 새 스킬/지식 학습
  error      — 오류, 자동 복구 시도 후 실패 시 suspended로
  terminated — 종료, 삭제 예정

자동 감시 규칙:
  - 30분 이상 미사용 → dormant
  - 오류율 20% 초과 → error
  - error 상태 3회 연속 → suspended
  - training 완료 조건 충족 → online
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
AGENTS_DIR = PROJECT_ROOT / "agents"
LOGS_DIR = PROJECT_ROOT / "logs"

# 유효한 상태
VALID_STATES = {"online", "dormant", "suspended", "training", "error", "terminated"}

# 허용된 상태 전이 (from → [to, ...])
TRANSITIONS = {
    "online":     ["dormant", "suspended", "training", "error", "terminated"],
    "dormant":    ["online", "suspended", "terminated"],
    "suspended":  ["online", "terminated"],
    "training":   ["online", "error", "terminated"],
    "error":      ["online", "suspended", "terminated"],
    "terminated": [],  # 종료 상태에서는 전이 불가
}

# 자동 전이 규칙
AUTO_RULES = {
    "idle_timeout_minutes": 30,     # 미사용 → dormant
    "error_rate_threshold": 0.20,   # 오류율 → error
    "consecutive_errors_max": 3,    # 연속 오류 → suspended
}


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_profile(agent_id: str) -> Optional[dict]:
    p = AGENTS_DIR / agent_id / "profile.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def _save_profile(agent_id: str, profile: dict):
    p = AGENTS_DIR / agent_id / "profile.json"
    p.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")


def _log_transition(agent_id: str, old_state: str, new_state: str, reason: str):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    line = f"[{_now()}] {agent_id}: {old_state} → {new_state} ({reason})\n"
    with open(LOGS_DIR / "state_transitions.log", "a", encoding="utf-8") as f:
        f.write(line)
    # 에이전트 개별 로그
    agent_log = AGENTS_DIR / agent_id / "logs" / "state.log"
    agent_log.parent.mkdir(parents=True, exist_ok=True)
    with open(agent_log, "a", encoding="utf-8") as f:
        f.write(line)


# ═══════════════════════════════════════════════════════
# 상태 전이
# ═══════════════════════════════════════════════════════

def transition(agent_id: str, new_state: str, reason: str = "manual") -> dict:
    """
    에이전트 상태를 전이한다.

    Args:
        agent_id: 에이전트 ID
        new_state: 목표 상태
        reason: 전이 사유

    Returns:
        {"success": bool, "old_state": str, "new_state": str, "message": str}
    """
    if new_state not in VALID_STATES:
        return {"success": False, "message": f"유효하지 않은 상태: {new_state}"}

    profile = _load_profile(agent_id)
    if not profile:
        return {"success": False, "message": f"에이전트 없음: {agent_id}"}

    old_state = profile.get("status", "online")

    # 같은 상태면 스킵
    if old_state == new_state:
        return {"success": True, "old_state": old_state, "new_state": new_state, "message": "이미 해당 상태"}

    # 전이 가능 여부 확인
    allowed = TRANSITIONS.get(old_state, [])
    if new_state not in allowed:
        return {
            "success": False,
            "message": f"전이 불가: {old_state} → {new_state} (허용: {allowed})"
        }

    # 마스터는 suspended/terminated 불가
    if profile.get("role") == "master_controller" and new_state in ("suspended", "terminated"):
        return {"success": False, "message": "마스터 에이전트는 정지/종료할 수 없습니다"}

    # 상태 변경
    profile["status"] = new_state
    profile["last_state_change"] = _now()

    # 상태별 추가 처리
    if new_state == "dormant":
        profile["dormant_since"] = _now()
    elif new_state == "online" and old_state == "dormant":
        profile.pop("dormant_since", None)
    elif new_state == "error":
        error_count = profile.get("consecutive_errors", 0) + 1
        profile["consecutive_errors"] = error_count
        # 연속 오류 3회 → suspended
        if error_count >= AUTO_RULES["consecutive_errors_max"]:
            profile["status"] = "suspended"
            new_state = "suspended"
            reason = f"연속 오류 {error_count}회 → 자동 정지"
            profile["consecutive_errors"] = 0
    elif new_state == "online":
        profile["consecutive_errors"] = 0

    _save_profile(agent_id, profile)

    # 레지스트리 동기화
    _sync_registry_status(agent_id, new_state)

    # 로그
    _log_transition(agent_id, old_state, new_state, reason)

    return {
        "success": True,
        "old_state": old_state,
        "new_state": new_state,
        "message": f"{agent_id}: {old_state} → {new_state} ({reason})"
    }


def _sync_registry_status(agent_id: str, status: str):
    """레지스트리의 에이전트 상태도 동기화"""
    from core.agent_creator import _load_registry, _save_registry
    reg = _load_registry()
    for a in reg["agents"]:
        if a["agent_id"] == agent_id:
            a["status"] = status
            break
    _save_registry(reg)


# ═══════════════════════════════════════════════════════
# 상태 조회
# ═══════════════════════════════════════════════════════

def get_state(agent_id: str) -> Optional[str]:
    """현재 상태 반환"""
    profile = _load_profile(agent_id)
    if profile:
        return profile.get("status", "online")
    return None


def get_all_states() -> list[dict]:
    """모든 에이전트의 상태 요약"""
    from core.agent_creator import list_agents
    agents = list_agents()
    result = []
    for a in agents:
        aid = a["agent_id"]
        profile = _load_profile(aid)
        result.append({
            "agent_id": aid,
            "name": a.get("name", ""),
            "role": a.get("role", ""),
            "status": profile.get("status", "unknown") if profile else "unknown",
            "level": profile.get("level", 1) if profile else 1,
            "last_state_change": profile.get("last_state_change") if profile else None,
        })
    return result


def get_state_history(agent_id: str, limit: int = 20) -> list[str]:
    """상태 전이 히스토리 반환"""
    log_path = AGENTS_DIR / agent_id / "logs" / "state.log"
    if not log_path.exists():
        return []
    lines = log_path.read_text(encoding="utf-8").strip().split("\n")
    return lines[-limit:]


# ═══════════════════════════════════════════════════════
# 자동 감시 (수동 호출 또는 스케줄러에서 주기적 실행)
# ═══════════════════════════════════════════════════════

def run_watchdog() -> list[dict]:
    """
    전체 에이전트를 스캔하여 자동 상태 전이를 수행한다.
    서버 시작 시 또는 주기적으로 호출.

    Returns:
        상태 변경된 에이전트 목록
    """
    from core.agent_creator import list_agents
    agents = list_agents()
    changes = []

    for a in agents:
        aid = a["agent_id"]
        profile = _load_profile(aid)
        if not profile:
            continue

        current = profile.get("status", "online")

        # 마스터는 자동 전이 대상 아님
        if profile.get("role") == "master_controller":
            continue

        # 규칙 1: 오류율 초과 → error
        learning = profile.get("learning", {})
        error_rate = learning.get("error_rate", 0.0)
        if current == "online" and error_rate > AUTO_RULES["error_rate_threshold"]:
            result = transition(aid, "error", f"오류율 {error_rate:.1%} 초과")
            if result["success"]:
                changes.append(result)
            continue

        # 규칙 2: (향후) 미사용 시간 체크 → dormant
        # last_activity를 tracking하면 여기서 체크 가능
        # 현재는 수동 전이로 처리

    return changes
