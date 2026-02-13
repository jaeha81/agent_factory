"""
command_engine.py
춘식이 채팅 응답에서 명령을 감지하고 실행하는 엔진

지원 명령:
  [COMMAND:CREATE_AGENT] name=이름, role=역할
  [COMMAND:DELETE_AGENT] agent_id=A0002
  [COMMAND:EQUIP_SKILL] agent_id=A0002, skill_id=echo
  [COMMAND:UNEQUIP_SKILL] agent_id=A0002, skill_id=echo
  [COMMAND:LEVELUP] agent_id=A0002, force=true
  [COMMAND:SET_STATUS] agent_id=A0002, status=dormant
  [COMMAND:LIST_AGENTS]
  [COMMAND:AGENT_INFO] agent_id=A0002
"""

import re
import json
from pathlib import Path
from typing import Optional

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent
AGENTS_DIR = PROJECT_ROOT / "agents"


def parse_commands(ai_response: str) -> list[dict]:
    """
    AI 응답 텍스트에서 [COMMAND:XXX] 패턴을 모두 추출한다.

    Returns: [{"command": "CREATE_AGENT", "params": {"name": "...", "role": "..."}}, ...]
    """
    pattern = r'\[COMMAND:(\w+)\]\s*([^\n\[]*)'
    matches = re.findall(pattern, ai_response)

    commands = []
    for cmd_name, param_str in matches:
        params = _parse_params(param_str.strip())
        commands.append({"command": cmd_name, "params": params})

    return commands


def _parse_params(param_str: str) -> dict:
    """'name=홍길동, role=data_analyst' → {"name": "홍길동", "role": "data_analyst"}"""
    params = {}
    if not param_str:
        return params
    # 쉼표 구분
    parts = [p.strip() for p in param_str.split(',')]
    for part in parts:
        if '=' in part:
            key, val = part.split('=', 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            # boolean 변환
            if val.lower() == 'true':
                val = True
            elif val.lower() == 'false':
                val = False
            params[key] = val
    return params


def execute_command(cmd: dict) -> dict:
    """
    파싱된 명령을 실행한다.

    Returns: {"success": bool, "message": str, "data": any}
    """
    command = cmd["command"]
    params = cmd["params"]

    try:
        if command == "CREATE_AGENT":
            return _exec_create_agent(params)
        elif command == "DELETE_AGENT":
            return _exec_delete_agent(params)
        elif command == "EQUIP_SKILL":
            return _exec_equip_skill(params)
        elif command == "UNEQUIP_SKILL":
            return _exec_unequip_skill(params)
        elif command == "LEVELUP":
            return _exec_levelup(params)
        elif command == "SET_STATUS":
            return _exec_set_status(params)
        elif command == "LIST_AGENTS":
            return _exec_list_agents()
        elif command == "AGENT_INFO":
            return _exec_agent_info(params)
        else:
            return {"success": False, "message": f"알 수 없는 명령: {command}", "data": None}
    except Exception as e:
        return {"success": False, "message": f"명령 실행 오류: {str(e)}", "data": None}


def _exec_create_agent(params: dict) -> dict:
    from core.agent_creator import create_agent
    name = params.get("name", "새 에이전트")
    role = params.get("role", "general")
    profile = create_agent(name=name, role=role, is_master=False)
    return {
        "success": True,
        "message": f"에이전트 생성 완료: {profile['agent_id']} ({name}, {role})",
        "data": {"agent_id": profile["agent_id"], "name": name, "role": role}
    }


def _exec_delete_agent(params: dict) -> dict:
    import shutil
    from core.agent_creator import _load_registry, _save_registry

    agent_id = params.get("agent_id", "")
    if not agent_id:
        return {"success": False, "message": "agent_id가 필요합니다", "data": None}

    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        return {"success": False, "message": f"에이전트 없음: {agent_id}", "data": None}

    # 프로필 확인
    profile_path = agent_dir / "profile.json"
    if profile_path.exists():
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        if profile.get("role") == "master_controller":
            return {"success": False, "message": "마스터 에이전트는 삭제할 수 없습니다", "data": None}

    shutil.rmtree(agent_dir)
    reg = _load_registry()
    reg["agents"] = [a for a in reg["agents"] if a["agent_id"] != agent_id]
    _save_registry(reg)

    return {"success": True, "message": f"에이전트 삭제 완료: {agent_id}", "data": {"agent_id": agent_id}}


def _exec_equip_skill(params: dict) -> dict:
    from core.skills_manager import SkillsManager
    agent_id = params.get("agent_id", "")
    skill_id = params.get("skill_id", "")
    if not agent_id or not skill_id:
        return {"success": False, "message": "agent_id와 skill_id가 필요합니다", "data": None}

    sm = SkillsManager()
    result = sm.equip_skill(agent_id, skill_id)
    return {
        "success": result.get("success", False),
        "message": result.get("message", f"{agent_id}에 스킬 {skill_id} 장착 완료"),
        "data": {"agent_id": agent_id, "skill_id": skill_id}
    }


def _exec_unequip_skill(params: dict) -> dict:
    from core.skills_manager import SkillsManager
    agent_id = params.get("agent_id", "")
    skill_id = params.get("skill_id", "")
    if not agent_id or not skill_id:
        return {"success": False, "message": "agent_id와 skill_id가 필요합니다", "data": None}

    sm = SkillsManager()
    result = sm.unequip_skill(agent_id, skill_id)
    return {
        "success": result.get("success", False),
        "message": result.get("message", f"{agent_id}에서 스킬 {skill_id} 해제 완료"),
        "data": {"agent_id": agent_id, "skill_id": skill_id}
    }


def _exec_levelup(params: dict) -> dict:
    from core.agent_creator import _load_registry, _save_registry
    agent_id = params.get("agent_id", "")
    force = params.get("force", False)
    if not agent_id:
        return {"success": False, "message": "agent_id가 필요합니다", "data": None}

    profile_path = AGENTS_DIR / agent_id / "profile.json"
    if not profile_path.exists():
        return {"success": False, "message": f"에이전트 없음: {agent_id}", "data": None}

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    old_level = profile.get("level", 1)

    if force:
        profile["level"] = old_level + 1
        profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
        # 레지스트리 동기화
        reg = _load_registry()
        for a in reg.get("agents", []):
            if a.get("agent_id") == agent_id:
                a["level"] = profile["level"]
                break
        _save_registry(reg)
        return {
            "success": True,
            "message": f"{agent_id} 레벨업: Lv.{old_level} → Lv.{old_level + 1} (강제)",
            "data": {"agent_id": agent_id, "new_level": old_level + 1}
        }

    return {"success": False, "message": "자동 레벨업 조건 판정은 API 서버를 통해 수행됩니다", "data": None}


def _exec_set_status(params: dict) -> dict:
    agent_id = params.get("agent_id", "")
    status = params.get("status", "")
    if not agent_id or not status:
        return {"success": False, "message": "agent_id와 status가 필요합니다", "data": None}

    valid_statuses = ["online", "dormant", "suspended", "training", "error"]
    if status not in valid_statuses:
        return {"success": False, "message": f"유효하지 않은 상태: {status} (허용: {valid_statuses})", "data": None}

    profile_path = AGENTS_DIR / agent_id / "profile.json"
    if not profile_path.exists():
        return {"success": False, "message": f"에이전트 없음: {agent_id}", "data": None}

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    old_status = profile.get("status", "unknown")
    profile["status"] = status
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

    # 레지스트리도 동기화
    from core.agent_creator import _load_registry, _save_registry
    reg = _load_registry()
    for a in reg["agents"]:
        if a["agent_id"] == agent_id:
            a["status"] = status
            break
    _save_registry(reg)

    return {
        "success": True,
        "message": f"{agent_id} 상태 변경: {old_status} → {status}",
        "data": {"agent_id": agent_id, "old_status": old_status, "new_status": status}
    }


def _exec_list_agents() -> dict:
    from core.agent_creator import list_agents
    agents = list_agents()
    summary = []
    for a in agents:
        summary.append(f"{a['agent_id']}: {a['name']} ({a['role']}, Lv.{a.get('level', 1)}, {a.get('status', 'unknown')})")
    return {
        "success": True,
        "message": f"등록된 에이전트 {len(agents)}개:\n" + "\n".join(summary) if summary else "등록된 에이전트 없음",
        "data": {"count": len(agents), "agents": agents}
    }


def _exec_agent_info(params: dict) -> dict:
    agent_id = params.get("agent_id", "")
    if not agent_id:
        return {"success": False, "message": "agent_id가 필요합니다", "data": None}

    profile_path = AGENTS_DIR / agent_id / "profile.json"
    if not profile_path.exists():
        return {"success": False, "message": f"에이전트 없음: {agent_id}", "data": None}

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    equipped_names = [s.get("name", s.get("skill_id", "?")) if isinstance(s, dict) else s for s in profile.get("equipped_skills", [])]
    return {
        "success": True,
        "message": (
            f"[{profile['agent_id']}] {profile['name']}\n"
            f"역할: {profile['role']} | Lv.{profile.get('level', 1)} | 상태: {profile.get('status', 'unknown')}\n"
            f"스킬: {', '.join(equipped_names) or '없음'}\n"
            f"능력치: {json.dumps(profile.get('stats', {}))}"
        ),
        "data": profile
    }


def strip_commands(text: str) -> str:
    """AI 응답에서 [COMMAND:...] 태그를 제거하고 사용자에게 보여줄 텍스트만 반환"""
    return re.sub(r'\[COMMAND:\w+\][^\n\[]*', '', text).strip()


def process_ai_response(ai_response: str) -> dict:
    """
    AI 응답을 처리한다:
    1. 명령 감지 & 실행
    2. 실행 결과 + 깨끗한 텍스트 반환

    Returns: {
        "display_text": str,
        "commands_executed": list,
        "had_commands": bool
    }
    """
    commands = parse_commands(ai_response)

    if not commands:
        return {
            "display_text": ai_response,
            "commands_executed": [],
            "had_commands": False
        }

    results = []
    for cmd in commands:
        result = execute_command(cmd)
        results.append({
            "command": cmd["command"],
            "params": cmd["params"],
            "result": result
        })

    # 명령 태그 제거한 텍스트
    clean_text = strip_commands(ai_response)

    # 실행 결과를 텍스트에 추가
    result_lines = []
    for r in results:
        icon = "✅" if r["result"]["success"] else "❌"
        result_lines.append(f"{icon} {r['result']['message']}")

    if result_lines:
        clean_text = clean_text + "\n\n" + "\n".join(result_lines) if clean_text else "\n".join(result_lines)

    return {
        "display_text": clean_text,
        "commands_executed": results,
        "had_commands": True
    }
