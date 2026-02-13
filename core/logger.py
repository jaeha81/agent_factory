"""
core/logger.py
JH Agent Factory — 통합 JSONL 로거

모든 팩토리 이벤트를 logs/ 폴더에 JSONL 형식으로 기록한다.
기존 plain-text 로그(activity.log 등)와 병행하여
구조화된 로그를 executor.jsonl, factory.jsonl에 추가한다.

JSONL 형식:
{"timestamp": "ISO8601", "task_id": "...", "event": "...", "action": "...", "details": {...}}
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LOGS_DIR = _PROJECT_ROOT / "logs"

# 로그 파일 경로
FACTORY_LOG = _LOGS_DIR / "factory.jsonl"
EXECUTOR_LOG = _LOGS_DIR / "executor.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gen_task_id() -> str:
    return str(uuid.uuid4())[:8]


def log_event(
    event: str,
    action: str,
    details: dict = None,
    log_file: Path = None,
    task_id: str = None,
) -> dict:
    """
    JSONL 로그 엔트리를 기록.

    Args:
        event: 이벤트 유형 (AGENT_CREATED, SKILL_EQUIPPED, COMMAND_EXECUTED 등)
        action: 수행된 동작 요약
        details: 추가 상세 정보 dict
        log_file: 로그 파일 경로 (기본: logs/factory.jsonl)
        task_id: 작업 ID (없으면 자동 생성)

    Returns:
        기록된 로그 엔트리 dict
    """
    log_file = log_file or FACTORY_LOG
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": _now_iso(),
        "task_id": task_id or _gen_task_id(),
        "event": event,
        "action": action,
        "details": details or {},
    }

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


def read_log(log_file: Path = None, limit: int = 50, event_filter: str = None) -> list:
    """
    JSONL 로그 읽기.

    Args:
        log_file: 로그 파일 경로 (기본: logs/factory.jsonl)
        limit: 최대 반환 개수
        event_filter: 특정 이벤트만 필터링

    Returns:
        로그 엔트리 리스트 (최신순)
    """
    log_file = log_file or FACTORY_LOG
    if not log_file.is_file():
        return []

    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    entries = []

    for line in reversed(lines):
        try:
            entry = json.loads(line)
            if event_filter and entry.get("event") != event_filter:
                continue
            entries.append(entry)
            if len(entries) >= limit:
                break
        except json.JSONDecodeError:
            continue

    return entries


def log_agent_event(agent_id: str, event: str, details: dict = None):
    """에이전트별 로그 기록 (agents/{id}/logs/events.jsonl)."""
    agent_log = _PROJECT_ROOT / "agents" / agent_id / "logs" / "events.jsonl"
    return log_event(event, f"agent:{agent_id}", details, log_file=agent_log)
