"""
agent_creator.py
에이전트를 생성하는 최소 동작(MVP).

기능:
  create_agent(name, role, is_master) → profile dict
    1) A0001 형식 ID 발급
    2) agents/{id}/ 하위 폴더 생성
    3) profile.json 생성
    4) config.yaml 생성
    5) prompt_injector → system_prompt.md
    6) agents/{id}/logs/creation.log 기록
    7) core/registry.json 등록
    8) logs/activity.log 기록

외부 라이브러리 의존: 없음 (표준 라이브러리만 사용)
Windows/Linux 호환
"""

import os
import sys
import json
from datetime import datetime, timezone

# ── import prompt_injector ────────────────────────────
# 같은 core/ 패키지 안이므로 상대경로로 import 시도,
# 안 되면 sys.path 보정 후 절대경로 import
_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_CORE_DIR)

if _CORE_DIR not in sys.path:
    sys.path.insert(0, _CORE_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from core.prompt_injector import inject_and_save

# ── 경로 상수 ────────────────────────────────────────
_AGENTS_DIR = os.path.join(_PROJECT_ROOT, "agents")
_REGISTRY_PATH = os.path.join(_PROJECT_ROOT, "core", "registry.json")
_FACTORY_LOG = os.path.join(_PROJECT_ROOT, "logs", "activity.log")
_BASE_DIR = os.path.join(_AGENTS_DIR, "_base")
_BASE_SKILLS_PATH = os.path.join(_BASE_DIR, "base_skills.json")
_BASE_INSTRUCTIONS_PATH = os.path.join(_BASE_DIR, "base_instructions.md")
_SKILLS_LIBRARY_CORE = os.path.join(_PROJECT_ROOT, "skills_library", "core")


# ═══════════════════════════════════════════════════════
# 내부 유틸리티
# ═══════════════════════════════════════════════════════

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_registry() -> dict:
    """registry.json 로드. 없으면 빈 구조 반환."""
    if os.path.isfile(_REGISTRY_PATH):
        with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"factory": "JH Agent Factory", "agents": [], "updated": ""}


def _save_registry(reg: dict):
    """registry.json 저장."""
    reg["updated"] = _now_iso()
    os.makedirs(os.path.dirname(_REGISTRY_PATH), exist_ok=True)
    with open(_REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)


def _next_agent_id(registry: dict) -> str:
    """
    A0001, A0002, ... 형식으로 다음 ID를 반환.
    registry에 등록된 에이전트 수 기반.
    """
    existing = registry.get("agents", [])
    # 기존 ID 중 가장 큰 번호 찾기
    max_num = 0
    for a in existing:
        aid = a.get("agent_id", "")
        if aid.startswith("A") and aid[1:].isdigit():
            max_num = max(max_num, int(aid[1:]))
    return f"A{max_num + 1:04d}"


def _append_line(filepath: str, line: str):
    """파일에 한 줄 append. 없으면 생성."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _write_json(filepath: str, data):
    """JSON 저장."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _write_text(filepath: str, text: str):
    """텍스트 저장."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)


# ═══════════════════════════════════════════════════════
# 기본 스킬/지침 주입
# ═══════════════════════════════════════════════════════

def _inject_base_skills(agent_dir: str, profile: dict) -> list:
    """
    agents/_base/base_skills.json에 정의된 기본 스킬을
    에이전트의 skills/ 폴더에 복사하고 profile에 추가.
    """
    if not os.path.isfile(_BASE_SKILLS_PATH):
        return []

    with open(_BASE_SKILLS_PATH, "r", encoding="utf-8") as f:
        base_config = json.load(f)

    if not base_config.get("auto_equip"):
        return []

    injected = []
    skills_dir = os.path.join(agent_dir, "skills")
    os.makedirs(skills_dir, exist_ok=True)

    for entry in base_config.get("skills", []):
        skill_id = entry["skill_id"]
        source_path = os.path.join(_PROJECT_ROOT, entry["source"])

        if not os.path.isfile(source_path):
            continue

        # 스킬 JSON 로드
        with open(source_path, "r", encoding="utf-8") as f:
            skill_data = json.load(f)

        # 에이전트 skills/ 폴더에 복사
        dest_path = os.path.join(skills_dir, f"{skill_id}.skill.json")
        skill_data["equipped_at"] = _now_iso()
        with open(dest_path, "w", encoding="utf-8") as f:
            json.dump(skill_data, f, ensure_ascii=False, indent=2)

        # profile에 스킬 정보 추가 (간략 버전)
        profile["equipped_skills"].append({
            "skill_id": skill_data["skill_id"],
            "name": skill_data["name"],
            "description": skill_data.get("description", ""),
            "category": skill_data.get("category", ""),
            "version": skill_data.get("version", "1.0.0"),
            "cost": skill_data.get("cost", "free"),
            "equipped_at": skill_data["equipped_at"],
        })
        injected.append(skill_id)

    return injected


def _inject_base_instructions(agent_dir: str):
    """
    agents/_base/base_instructions.md 내용을
    에이전트의 system_prompt.md 끝에 추가 주입.
    """
    if not os.path.isfile(_BASE_INSTRUCTIONS_PATH):
        return

    prompt_path = os.path.join(agent_dir, "system_prompt.md")
    if not os.path.isfile(prompt_path):
        return

    with open(_BASE_INSTRUCTIONS_PATH, "r", encoding="utf-8") as f:
        base_text = f.read()

    with open(prompt_path, "a", encoding="utf-8") as f:
        f.write("\n\n<!-- ═══ BASE INSTRUCTIONS (auto-injected) ═══ -->\n")
        f.write(base_text)


# ═══════════════════════════════════════════════════════
# 메인 함수
# ═══════════════════════════════════════════════════════

def create_agent(name: str, role: str = "general", is_master: bool = False) -> dict:
    """
    에이전트를 생성한다.

    Args:
        name:      에이전트 이름 (예: "춘식이")
        role:      역할 (예: "master_controller", "data_analyst")
        is_master: True면 마스터, False면 워커

    Returns:
        생성된 에이전트의 profile dict
    """
    now = _now_iso()

    # ── 0. 마스터 중복 체크 ──
    registry = _load_registry()
    if is_master:
        for a in registry.get("agents", []):
            if a.get("role") == "master_controller":
                raise ValueError(
                    f"마스터 에이전트가 이미 존재합니다: {a['agent_id']} ({a['name']})"
                )

    # ── 1. ID 발급 ──
    agent_id = _next_agent_id(registry)
    if is_master:
        role = "master_controller"
    level = 5 if is_master else 1
    agent_dir = os.path.join(_AGENTS_DIR, agent_id)

    # ── 2. 폴더 구조 생성 ──
    subdirs = [
        os.path.join("memory", "short_term"),
        os.path.join("memory", "long_term"),
        os.path.join("memory", "compressed"),
        "logs",
        os.path.join("data", "input"),
        os.path.join("data", "output"),
        "connections",
        "skills",
        "training",
    ]
    for sub in subdirs:
        os.makedirs(os.path.join(agent_dir, sub), exist_ok=True)

    # ── 3. profile.json ──
    profile = {
        "agent_id": agent_id,
        "name": name,
        "role": role,
        "level": level,
        "status": "online",
        "equipped_skills": [],
        "stats": {
            "INT": 5 if is_master else 1,
            "MEM": 5 if is_master else 1,
            "SPD": 3 if is_master else 1,
            "REL": 5 if is_master else 1,
        },
        "connections": [],
        "learning": {
            "total_tasks": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "error_rate": 0.0,
        },
        "metadata": {
            "description": "시스템 총괄 관리 에이전트" if is_master else "",
            "tags": [],
            "icon": "★" if is_master else "◇",
        },
        "created_at": now,
        "protocol": "CHUNSIK_PROTOCOL_v1.0",
    }
    _write_json(os.path.join(agent_dir, "profile.json"), profile)

    # ── 4. config.yaml ──
    config_text = (
        f"# Agent Config — {agent_id}\n"
        f"active_frameworks: []\n"
        f"memory_policy:\n"
        f"  max_tokens: 4000\n"
        f"  storage_mb: 100\n"
    )
    _write_text(os.path.join(agent_dir, "config.yaml"), config_text)

    # ── 5. 기본 스킬 자동 주입 (base_skills.json → skills/) ──
    injected_skills = _inject_base_skills(agent_dir, profile)
    if injected_skills:
        _write_json(os.path.join(agent_dir, "profile.json"), profile)

    # ── 6. system_prompt.md (prompt_injector 호출) ──
    master_id = ""
    if not is_master:
        # 레지스트리에서 마스터 ID 조회
        for a in registry.get("agents", []):
            if a.get("role") == "master_controller":
                master_id = a["agent_id"]
                break

    prompt_path = inject_and_save(
        agent_id=agent_id,
        agent_name=name,
        agent_role=role,
        agent_level=level,
        is_master=is_master,
        master_agent_id=master_id,
    )

    # ── 6.1. base_instructions.md를 system_prompt.md에 추가 주입 ──
    _inject_base_instructions(agent_dir)

    # ── 8. agents/{id}/logs/creation.log ──
    creation_log = os.path.join(agent_dir, "logs", "creation.log")
    skills_str = ",".join(s["skill_id"] for s in profile.get("equipped_skills", []))
    _append_line(creation_log, f"[{now}] AGENT_CREATED id={agent_id} name={name} role={role} level={level} base_skills=[{skills_str}]")

    # ── 9. core/registry.json 등록 ──
    registry["agents"].append({
        "agent_id": agent_id,
        "name": name,
        "role": role,
        "level": level,
        "status": "online",
        "created_at": now,
    })
    _save_registry(registry)

    # ── 10. logs/activity.log 기록 ──
    _append_line(_FACTORY_LOG, f"[{now}] AGENT_CREATED id={agent_id} name={name} role={role} base_skills=[{skills_str}]")

    return profile


# ═══════════════════════════════════════════════════════
# 편의 함수
# ═══════════════════════════════════════════════════════

def create_master_agent(name: str) -> dict:
    """마스터 에이전트 생성 (API용 래퍼)."""
    try:
        profile = create_agent(name, role="master_controller", is_master=True)
        return {"success": True, "agent_id": profile["agent_id"], "profile": profile}
    except ValueError as e:
        return {"success": False, "message": str(e)}


def list_agents() -> list:
    """등록된 전체 에이전트 목록."""
    return _load_registry().get("agents", [])


def get_agent(agent_id: str):
    """에이전트 프로필 반환."""
    profile_path = os.path.join(_AGENTS_DIR, agent_id, "profile.json")
    if os.path.isfile(profile_path):
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def update_factory_registry(agent_id: str, name: str, role: str):
    """외부 호출용 레지스트리 업데이트 (create_agent 내부에서 이미 처리됨)."""
    pass


def get_master_id() -> str:
    """마스터 에이전트 ID. 없으면 빈 문자열."""
    for a in list_agents():
        if a.get("role") == "master_controller":
            return a["agent_id"]
    return ""
