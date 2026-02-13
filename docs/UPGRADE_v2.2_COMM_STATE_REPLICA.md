# Agent Factory v2.2 — 에이전트 통신/상태/복제 시스템
# Claude Code 전용 지침서

---

## 🚨 절대 규칙
- 기존 파일 삭제 금지
- agents/A0001/ (춘식이) 데이터 보존
- core/registry.json 구조 보존
- core/ai_router.py, core/agent_creator.py, core/prompt_injector.py 등 기존 모듈 건드리지 않기
- api_server.py는 기존 엔드포인트 유지하면서 새 엔드포인트만 추가

---

## 1. [신규] core/connection_manager.py

에이전트 간 메시지 전달/명령 체계. 춘식이 → 워커 명령, 워커 → 춘식이 보고.

### 핵심 설계:

```python
"""
connection_manager.py
에이전트 간 통신 시스템

구조:
  - 메시지 큐 기반 비동기 통신
  - 계층: master → worker (command), worker → master (report)
  - 메시지 타입: command, report, broadcast, peer
  - 메시지 저장: agents/{id}/connections/inbox.jsonl, outbox.jsonl

메시지 형식:
{
    "msg_id": "MSG-20260213-001",
    "from": "A0001",
    "to": "A0002",           # "ALL"이면 브로드캐스트
    "type": "command",        # command | report | broadcast | peer
    "priority": "normal",     # critical | high | normal | low
    "subject": "데이터 분석 실행",
    "body": "최근 7일 유튜브 채널 통계를 분석하고 보고해줘",
    "status": "pending",      # pending | delivered | read | completed | failed
    "created_at": "2026-02-13T12:00:00Z",
    "delivered_at": null,
    "completed_at": null
}
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
AGENTS_DIR = PROJECT_ROOT / "agents"
LOGS_DIR = PROJECT_ROOT / "logs"

# 메시지 카운터 (세션 내)
_msg_counter = 0


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gen_msg_id() -> str:
    global _msg_counter
    _msg_counter += 1
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"MSG-{date}-{_msg_counter:04d}"


def _get_inbox_path(agent_id: str) -> Path:
    p = AGENTS_DIR / agent_id / "connections" / "inbox.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _get_outbox_path(agent_id: str) -> Path:
    p = AGENTS_DIR / agent_id / "connections" / "outbox.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _append_jsonl(path: Path, data: dict):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    result = []
    for line in lines:
        line = line.strip()
        if line:
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return result


# ═══════════════════════════════════════════════════════
# 메시지 전송
# ═══════════════════════════════════════════════════════

def send_message(
    from_id: str,
    to_id: str,
    msg_type: str,  # command | report | broadcast | peer
    subject: str,
    body: str,
    priority: str = "normal",
) -> dict:
    """
    에이전트 간 메시지 전송

    Args:
        from_id: 발신 에이전트 ID
        to_id: 수신 에이전트 ID ("ALL"이면 브로드캐스트)
        msg_type: command | report | broadcast | peer
        subject: 제목
        body: 내용
        priority: critical | high | normal | low

    Returns:
        생성된 메시지 dict
    """
    msg = {
        "msg_id": _gen_msg_id(),
        "from": from_id,
        "to": to_id,
        "type": msg_type,
        "priority": priority,
        "subject": subject,
        "body": body,
        "status": "pending",
        "created_at": _now(),
        "delivered_at": None,
        "completed_at": None,
    }

    # 발신자 outbox에 기록
    _append_jsonl(_get_outbox_path(from_id), msg)

    if to_id == "ALL":
        # 브로드캐스트: 모든 에이전트 inbox에 전달
        _broadcast(from_id, msg)
    else:
        # 단일 수신
        target_dir = AGENTS_DIR / to_id
        if not target_dir.exists():
            msg["status"] = "failed"
            return msg
        msg["status"] = "delivered"
        msg["delivered_at"] = _now()
        _append_jsonl(_get_inbox_path(to_id), msg)

    # 통신 로그
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOGS_DIR / "communication.log", "a", encoding="utf-8") as f:
        f.write(f"[{_now()}] {from_id} → {to_id} [{msg_type}/{priority}] {subject}\n")

    return msg


def _broadcast(from_id: str, msg: dict):
    """모든 에이전트(발신자 제외)에게 메시지 전달"""
    from core.agent_creator import list_agents
    agents = list_agents()
    for a in agents:
        aid = a["agent_id"]
        if aid == from_id:
            continue
        broadcast_msg = msg.copy()
        broadcast_msg["to"] = aid
        broadcast_msg["status"] = "delivered"
        broadcast_msg["delivered_at"] = _now()
        _append_jsonl(_get_inbox_path(aid), broadcast_msg)


# ═══════════════════════════════════════════════════════
# 메시지 조회
# ═══════════════════════════════════════════════════════

def get_inbox(agent_id: str, unread_only: bool = False, limit: int = 50) -> list[dict]:
    """에이전트의 수신 메시지 목록"""
    messages = _read_jsonl(_get_inbox_path(agent_id))
    if unread_only:
        messages = [m for m in messages if m.get("status") == "delivered"]
    return messages[-limit:]


def get_outbox(agent_id: str, limit: int = 50) -> list[dict]:
    """에이전트의 발신 메시지 목록"""
    messages = _read_jsonl(_get_outbox_path(agent_id))
    return messages[-limit:]


def get_message(agent_id: str, msg_id: str) -> Optional[dict]:
    """특정 메시지 조회"""
    for m in _read_jsonl(_get_inbox_path(agent_id)):
        if m.get("msg_id") == msg_id:
            return m
    for m in _read_jsonl(_get_outbox_path(agent_id)):
        if m.get("msg_id") == msg_id:
            return m
    return None


# ═══════════════════════════════════════════════════════
# 메시지 상태 변경
# ═══════════════════════════════════════════════════════

def mark_read(agent_id: str, msg_id: str) -> bool:
    """메시지를 읽음 처리"""
    return _update_message_status(agent_id, msg_id, "read")


def mark_completed(agent_id: str, msg_id: str) -> bool:
    """메시지(명령)를 완료 처리"""
    return _update_message_status(agent_id, msg_id, "completed")


def mark_failed(agent_id: str, msg_id: str) -> bool:
    """메시지(명령)를 실패 처리"""
    return _update_message_status(agent_id, msg_id, "failed")


def _update_message_status(agent_id: str, msg_id: str, new_status: str) -> bool:
    """inbox에서 메시지 상태 업데이트"""
    inbox_path = _get_inbox_path(agent_id)
    messages = _read_jsonl(inbox_path)
    found = False
    for m in messages:
        if m.get("msg_id") == msg_id:
            m["status"] = new_status
            if new_status == "completed":
                m["completed_at"] = _now()
            found = True
            break
    if found:
        # 전체 다시 쓰기
        with open(inbox_path, "w", encoding="utf-8") as f:
            for m in messages:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")
    return found


# ═══════════════════════════════════════════════════════
# 춘식이 전용 헬퍼
# ═══════════════════════════════════════════════════════

def master_command(to_id: str, subject: str, body: str, priority: str = "normal") -> dict:
    """춘식이(마스터)가 워커에게 명령 전달하는 단축 함수"""
    from core.agent_creator import get_master_id
    master_id = get_master_id()
    if not master_id:
        return {"error": "마스터 에이전트가 없습니다"}
    return send_message(
        from_id=master_id,
        to_id=to_id,
        msg_type="command",
        subject=subject,
        body=body,
        priority=priority,
    )


def worker_report(from_id: str, subject: str, body: str) -> dict:
    """워커가 춘식이(마스터)에게 보고하는 단축 함수"""
    from core.agent_creator import get_master_id
    master_id = get_master_id()
    if not master_id:
        return {"error": "마스터 에이전트가 없습니다"}
    return send_message(
        from_id=from_id,
        to_id=master_id,
        msg_type="report",
        subject=subject,
        body=body,
    )


def master_broadcast(subject: str, body: str, priority: str = "normal") -> dict:
    """춘식이가 전체 에이전트에게 공지"""
    from core.agent_creator import get_master_id
    master_id = get_master_id()
    if not master_id:
        return {"error": "마스터 에이전트가 없습니다"}
    return send_message(
        from_id=master_id,
        to_id="ALL",
        msg_type="broadcast",
        subject=subject,
        body=body,
        priority=priority,
    )


# ═══════════════════════════════════════════════════════
# 통계
# ═══════════════════════════════════════════════════════

def get_comm_stats(agent_id: str) -> dict:
    """에이전트의 통신 통계"""
    inbox = _read_jsonl(_get_inbox_path(agent_id))
    outbox = _read_jsonl(_get_outbox_path(agent_id))
    pending = sum(1 for m in inbox if m.get("status") == "delivered")
    completed = sum(1 for m in inbox if m.get("status") == "completed")
    failed = sum(1 for m in inbox if m.get("status") == "failed")
    return {
        "total_received": len(inbox),
        "total_sent": len(outbox),
        "pending": pending,
        "completed": completed,
        "failed": failed,
    }
```

---

## 2. [신규] core/state_machine.py

에이전트 상태 전이 + 자동 감시 엔진.

### 핵심 설계:

```python
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
```

---

## 3. [신규] core/agent_replicator.py

기존 에이전트를 복제(클론)하는 모듈.

### 핵심 설계:

```python
"""
agent_replicator.py
에이전트 복제(클론) 시스템

기능:
  - 기존 에이전트의 설정/스킬/프롬프트를 복제하여 새 에이전트 생성
  - 스킬 상속 (전체 또는 선택적)
  - 레벨은 1로 리셋 (경험은 직접 쌓아야 함)
  - 메모리는 복제하지 않음 (빈 상태에서 시작)
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
AGENTS_DIR = PROJECT_ROOT / "agents"


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def replicate(
    source_id: str,
    new_name: str,
    inherit_skills: bool = True,
    inherit_level: bool = False,
    new_role: Optional[str] = None,
) -> dict:
    """
    에이전트를 복제한다.

    Args:
        source_id: 원본 에이전트 ID
        new_name: 새 에이전트 이름
        inherit_skills: 스킬 상속 여부
        inherit_level: 레벨 상속 여부 (기본: False → Lv.1)
        new_role: 역할 변경 (None이면 원본과 동일)

    Returns:
        {"success": bool, "message": str, "source": str, "clone": dict|None}
    """
    source_dir = AGENTS_DIR / source_id
    source_profile_path = source_dir / "profile.json"

    if not source_profile_path.exists():
        return {"success": False, "message": f"원본 에이전트 없음: {source_id}", "source": source_id, "clone": None}

    source_profile = json.loads(source_profile_path.read_text(encoding="utf-8"))

    # 마스터는 복제 불가
    if source_profile.get("role") == "master_controller":
        return {"success": False, "message": "마스터 에이전트는 복제할 수 없습니다", "source": source_id, "clone": None}

    # 새 에이전트 생성 (agent_creator 사용)
    from core.agent_creator import create_agent
    role = new_role or source_profile.get("role", "general")
    new_profile = create_agent(name=new_name, role=role, is_master=False)
    new_id = new_profile["agent_id"]

    # 스킬 상속
    if inherit_skills:
        new_profile["equipped_skills"] = list(source_profile.get("equipped_skills", []))

    # 레벨 상속
    if inherit_level:
        new_profile["level"] = source_profile.get("level", 1)
    else:
        new_profile["level"] = 1

    # 능력치 복제 (레벨 미상속 시 기본값 유지)
    if inherit_level:
        new_profile["stats"] = dict(source_profile.get("stats", {}))

    # 클론 메타데이터
    new_profile["metadata"] = dict(source_profile.get("metadata", {}))
    new_profile["metadata"]["cloned_from"] = source_id
    new_profile["metadata"]["clone_date"] = _now()
    new_profile["metadata"]["tags"] = list(source_profile.get("metadata", {}).get("tags", []))
    if "clone" not in new_profile["metadata"]["tags"]:
        new_profile["metadata"]["tags"].append("clone")

    # learning은 리셋
    new_profile["learning"] = {
        "tasks_completed": 0,
        "error_rate": 0.0,
        "total_interactions": 0,
        "knowledge_files": 0,
        "last_trained": None,
    }

    # 저장
    new_profile_path = AGENTS_DIR / new_id / "profile.json"
    new_profile_path.write_text(
        json.dumps(new_profile, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # system_prompt.md 복제 (있으면)
    source_prompt = source_dir / "system_prompt.md"
    new_prompt = AGENTS_DIR / new_id / "system_prompt.md"
    if source_prompt.exists():
        prompt_text = source_prompt.read_text(encoding="utf-8")
        # 이름과 ID 치환
        prompt_text = prompt_text.replace(source_profile.get("name", ""), new_name)
        prompt_text = prompt_text.replace(source_id, new_id)
        new_prompt.write_text(prompt_text, encoding="utf-8")

    # 로그
    log_dir = AGENTS_DIR / new_id / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / "creation.log", "a", encoding="utf-8") as f:
        f.write(f"[{_now()}] CLONED from {source_id} ({source_profile.get('name', '')})\n")
        f.write(f"  skills_inherited: {inherit_skills}\n")
        f.write(f"  level_inherited: {inherit_level}\n")

    return {
        "success": True,
        "message": f"복제 완료: {source_id} → {new_id} ({new_name})",
        "source": source_id,
        "clone": new_profile,
    }


def bulk_replicate(
    source_id: str,
    count: int,
    name_prefix: str = "클론",
    inherit_skills: bool = True,
) -> list[dict]:
    """
    에이전트를 여러 개 대량 복제한다.

    Args:
        source_id: 원본 에이전트 ID
        count: 복제 수 (최대 10)
        name_prefix: 이름 접두사
        inherit_skills: 스킬 상속

    Returns:
        복제 결과 리스트
    """
    count = min(count, 10)  # 안전 제한
    results = []
    for i in range(1, count + 1):
        name = f"{name_prefix}_{i:02d}"
        result = replicate(source_id, name, inherit_skills=inherit_skills, inherit_level=False)
        results.append(result)
    return results
```

---

## 4. [병합] api_server.py — 신규 엔드포인트 추가

기존 엔드포인트 전부 유지. 아래만 추가:

### 통신 엔드포인트:
```python
# ── 에이전트 통신 ──

class SendMessageReq(BaseModel):
    from_id: str
    to_id: str
    msg_type: str = "command"
    subject: str
    body: str
    priority: str = "normal"

class MasterCommandReq(BaseModel):
    to_id: str
    subject: str
    body: str
    priority: str = "normal"

@app.post("/api/messages/send")
def api_send_message(req: SendMessageReq):
    from core.connection_manager import send_message
    msg = send_message(req.from_id, req.to_id, req.msg_type, req.subject, req.body, req.priority)
    return msg

@app.post("/api/messages/master-command")
def api_master_command(req: MasterCommandReq):
    from core.connection_manager import master_command
    msg = master_command(req.to_id, req.subject, req.body, req.priority)
    return msg

@app.post("/api/messages/broadcast")
def api_broadcast(req: MasterCommandReq):
    from core.connection_manager import master_broadcast
    msg = master_broadcast(req.subject, req.body, req.priority)
    return msg

@app.get("/api/agents/{agent_id}/inbox")
def api_inbox(agent_id: str, unread: bool = False):
    from core.connection_manager import get_inbox
    return {"messages": get_inbox(agent_id, unread_only=unread)}

@app.get("/api/agents/{agent_id}/outbox")
def api_outbox(agent_id: str):
    from core.connection_manager import get_outbox
    return {"messages": get_outbox(agent_id)}

@app.get("/api/agents/{agent_id}/comm-stats")
def api_comm_stats(agent_id: str):
    from core.connection_manager import get_comm_stats
    return get_comm_stats(agent_id)

@app.post("/api/messages/{agent_id}/{msg_id}/read")
def api_mark_read(agent_id: str, msg_id: str):
    from core.connection_manager import mark_read
    return {"success": mark_read(agent_id, msg_id)}

@app.post("/api/messages/{agent_id}/{msg_id}/complete")
def api_mark_complete(agent_id: str, msg_id: str):
    from core.connection_manager import mark_completed
    return {"success": mark_completed(agent_id, msg_id)}
```

### 상태 머신 엔드포인트:
```python
# ── 상태 머신 ──

class TransitionReq(BaseModel):
    new_state: str
    reason: str = "manual"

@app.post("/api/agents/{agent_id}/state")
def api_transition(agent_id: str, req: TransitionReq):
    from core.state_machine import transition
    return transition(agent_id, req.new_state, req.reason)

@app.get("/api/agents/{agent_id}/state")
def api_get_state(agent_id: str):
    from core.state_machine import get_state, get_state_history
    return {"state": get_state(agent_id), "history": get_state_history(agent_id, 10)}

@app.get("/api/states")
def api_all_states():
    from core.state_machine import get_all_states
    return {"agents": get_all_states()}

@app.post("/api/watchdog")
def api_run_watchdog():
    from core.state_machine import run_watchdog
    changes = run_watchdog()
    return {"changes": changes, "count": len(changes)}
```

### 복제 엔드포인트:
```python
# ── 에이전트 복제 ──

class ReplicateReq(BaseModel):
    source_id: str
    new_name: str
    inherit_skills: bool = True
    inherit_level: bool = False
    new_role: Optional[str] = None

class BulkReplicateReq(BaseModel):
    source_id: str
    count: int = 3
    name_prefix: str = "클론"
    inherit_skills: bool = True

@app.post("/api/agents/replicate")
def api_replicate(req: ReplicateReq):
    from core.agent_replicator import replicate
    return replicate(req.source_id, req.new_name, req.inherit_skills, req.inherit_level, req.new_role)

@app.post("/api/agents/bulk-replicate")
def api_bulk_replicate(req: BulkReplicateReq):
    from core.agent_replicator import bulk_replicate
    results = bulk_replicate(req.source_id, req.count, req.name_prefix, req.inherit_skills)
    success_count = sum(1 for r in results if r["success"])
    return {"results": results, "total": len(results), "success": success_count}
```

---

## 5. [병합] static/index.html — 우측 패널에 통신/상태 탭 추가

우측 패널(에이전트 상세)에 3개 탭을 추가:

### 탭 구성:
1. **정보** (기존) — 프로필, 능력치, 스킬, 레벨업
2. **통신** (신규) — inbox/outbox 메시지 목록, 명령 전송 폼
3. **상태** (신규) — 상태 전이 버튼(online/dormant/suspended), 히스토리

### 명령 전송 UI:
- 제목 input
- 내용 textarea
- 우선순위 select (critical/high/normal/low)
- "명령 전송" 버튼 → POST /api/messages/master-command

### 상태 전이 UI:
- 현재 상태 표시 (색상 구분)
- 전이 가능한 상태만 버튼 활성화
- 전이 로그 리스트

### 복제 UI:
- 에이전트 상세 패널 하단에 "복제" 버튼 추가
- 클릭 시 모달: 새 이름 input, 스킬 상속 체크박스
- "복제 실행" → POST /api/agents/replicate

---

## 실행 순서

1. core/connection_manager.py 생성
2. core/state_machine.py 생성
3. core/agent_replicator.py 생성
4. api_server.py에 신규 엔드포인트 추가 (기존 유지)
5. static/index.html 우측 패널에 탭 추가
6. pip install 필요 없음 (표준 라이브러리만 사용)
7. 서버 재시작 후 테스트

---

## 테스트 시나리오

### 통신 테스트:
1. POST /api/messages/master-command → 춘식이가 워커에게 명령
2. GET /api/agents/A0002/inbox → 메시지 수신 확인
3. POST /api/messages/broadcast → 전체 공지 테스트

### 상태 머신 테스트:
1. POST /api/agents/A0002/state {new_state: "dormant"} → 휴면 전환
2. POST /api/agents/A0002/state {new_state: "online"} → 재활성
3. POST /api/watchdog → 자동 감시 실행

### 복제 테스트:
1. POST /api/agents/replicate {source_id: "A0002", new_name: "분석봇v2"} → 단일 복제
2. POST /api/agents/bulk-replicate {source_id: "A0002", count: 3} → 대량 복제
