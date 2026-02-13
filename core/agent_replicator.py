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
