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
