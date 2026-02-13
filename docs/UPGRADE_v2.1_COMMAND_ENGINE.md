# Agent Factory v2.1 — 춘식이 커맨드 엔진
# Claude Code 전용 지침서

---

## 🚨 절대 규칙 (이전과 동일)
- 기존 파일 삭제 금지
- agents/A0001/ (춘식이) 데이터 보존
- core/registry.json 구조 보존

---

## 개요

춘식이가 채팅을 통해 직접 에이전트를 생성/삭제/스킬부여/레벨업/상태변경할 수 있게 한다.
사용자가 "에이전트 하나 만들어줘"라고 채팅하면, AI가 의도를 파악하고 실제 API를 호출하는 구조.

### 동작 흐름:
```
사용자 채팅 입력
  → ai_router로 AI 응답 생성
  → 응답에서 [COMMAND] 태그 감지
  → 명령 파싱 → 해당 API 함수 실행
  → 실행 결과를 채팅 메시지에 추가
```

---

## 1. [신규] core/command_engine.py

춘식이 응답에서 명령을 감지하고 실행하는 엔진.

### 핵심 구조:

```python
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
    pattern = r'\[COMMAND:(\w+)\]\s*(.*?)(?=\[COMMAND:|\Z)'
    matches = re.findall(pattern, ai_response, re.DOTALL)
    
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
    agent_id = params.get("agent_id", "")
    skill_id = params.get("skill_id", "")
    if not agent_id or not skill_id:
        return {"success": False, "message": "agent_id와 skill_id가 필요합니다", "data": None}
    
    profile_path = AGENTS_DIR / agent_id / "profile.json"
    if not profile_path.exists():
        return {"success": False, "message": f"에이전트 없음: {agent_id}", "data": None}
    
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    equipped = profile.get("equipped_skills", [])
    
    if skill_id in equipped:
        return {"success": False, "message": f"이미 장착됨: {skill_id}", "data": None}
    if len(equipped) >= 10:
        return {"success": False, "message": "스킬 최대 10개까지 장착 가능", "data": None}
    
    equipped.append(skill_id)
    profile["equipped_skills"] = equipped
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    
    return {"success": True, "message": f"{agent_id}에 스킬 {skill_id} 장착 완료", "data": {"agent_id": agent_id, "skill_id": skill_id}}


def _exec_unequip_skill(params: dict) -> dict:
    agent_id = params.get("agent_id", "")
    skill_id = params.get("skill_id", "")
    if not agent_id or not skill_id:
        return {"success": False, "message": "agent_id와 skill_id가 필요합니다", "data": None}
    
    profile_path = AGENTS_DIR / agent_id / "profile.json"
    if not profile_path.exists():
        return {"success": False, "message": f"에이전트 없음: {agent_id}", "data": None}
    
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    equipped = profile.get("equipped_skills", [])
    
    if skill_id not in equipped:
        return {"success": False, "message": f"장착되지 않음: {skill_id}", "data": None}
    
    equipped.remove(skill_id)
    profile["equipped_skills"] = equipped
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    
    return {"success": True, "message": f"{agent_id}에서 스킬 {skill_id} 해제 완료", "data": {"agent_id": agent_id, "skill_id": skill_id}}


def _exec_levelup(params: dict) -> dict:
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
    return {
        "success": True,
        "message": (
            f"[{profile['agent_id']}] {profile['name']}\n"
            f"역할: {profile['role']} | Lv.{profile.get('level', 1)} | 상태: {profile.get('status', 'unknown')}\n"
            f"스킬: {', '.join(profile.get('equipped_skills', [])) or '없음'}\n"
            f"능력치: {json.dumps(profile.get('stats', {}))}"
        ),
        "data": profile
    }


def strip_commands(text: str) -> str:
    """AI 응답에서 [COMMAND:...] 태그를 제거하고 사용자에게 보여줄 텍스트만 반환"""
    return re.sub(r'\[COMMAND:\w+\][^\[]*', '', text).strip()


def process_ai_response(ai_response: str) -> dict:
    """
    AI 응답을 처리한다:
    1. 명령 감지 & 실행
    2. 실행 결과 + 깨끗한 텍스트 반환
    
    Returns: {
        "display_text": str,  # 사용자에게 보여줄 텍스트
        "commands_executed": list,  # 실행된 명령 목록
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
```

---

## 2. [병합] agents/A0001/system_prompt.md

춘식이의 시스템 프롬프트에 명령 태그 사용법을 추가한다.
기존 내용 보존하고 맨 아래에 이 블록을 추가:

```markdown

## 명령 실행 기능

너는 대화 중에 시스템 명령을 실행할 수 있다. 사용자가 에이전트 생성, 삭제, 스킬 관리 등을 요청하면 응답 텍스트 안에 [COMMAND] 태그를 포함해라.

### 사용 가능한 명령:

- 에이전트 생성: [COMMAND:CREATE_AGENT] name=이름, role=역할
  - 역할: general, data_analyst, content_creator, monitor, trader, researcher, automation, security
- 에이전트 삭제: [COMMAND:DELETE_AGENT] agent_id=A0002
- 스킬 장착: [COMMAND:EQUIP_SKILL] agent_id=A0002, skill_id=스킬명
- 스킬 해제: [COMMAND:UNEQUIP_SKILL] agent_id=A0002, skill_id=스킬명
- 레벨업: [COMMAND:LEVELUP] agent_id=A0002, force=true
- 상태 변경: [COMMAND:SET_STATUS] agent_id=A0002, status=online|dormant|suspended|training|error
- 에이전트 목록: [COMMAND:LIST_AGENTS]
- 에이전트 정보: [COMMAND:AGENT_INFO] agent_id=A0002

### 규칙:
1. 사용자가 명확하게 요청했을 때만 명령을 실행해라
2. 명령 실행 전에 사용자에게 무엇을 할 건지 설명해라
3. 마스터 에이전트(너 자신)는 삭제할 수 없다
4. 역할이 불분명하면 사용자에게 물어봐라
5. 여러 명령을 한 번에 실행할 수 있다

### 예시 응답:
"데이터 분석 에이전트를 생성하겠습니다.
[COMMAND:CREATE_AGENT] name=분석봇, role=data_analyst
생성이 완료되면 기본 스킬을 장착해드릴까요?"
```

---

## 3. [병합] api_server.py의 POST /api/chat 엔드포인트 수정

기존 chat 엔드포인트에서 ai_router 응답을 받은 후, command_engine.process_ai_response()를 통과시킨다.

### 변경 전:
```python
@app.post("/api/chat")
async def api_chat(req: ChatReq):
    system_prompt = _get_chunsik_prompt()
    result = await ai_router.chat(
        session_id=req.session_id,
        user_message=req.message,
        system_prompt=system_prompt,
    )
    return result
```

### 변경 후:
```python
@app.post("/api/chat")
async def api_chat(req: ChatReq):
    system_prompt = _get_chunsik_prompt()
    result = await ai_router.chat(
        session_id=req.session_id,
        user_message=req.message,
        system_prompt=system_prompt,
    )
    
    # 명령 엔진 처리
    if result.get("error") is None:
        from core.command_engine import process_ai_response
        processed = process_ai_response(result["reply"])
        result["reply"] = processed["display_text"]
        result["commands_executed"] = processed["commands_executed"]
        result["had_commands"] = processed["had_commands"]
    
    return result
```

---

## 4. [병합] static/index.html 채팅 메시지 표시

명령 실행 결과가 있을 때 시각적으로 구분해서 보여준다.
기존 채팅 전송 함수(sendChat)에서 응답 처리 부분을 수정:

### 변경 포인트:
응답에 had_commands가 true이면 메시지 하단에 실행 결과 배지를 표시.

CSS 추가:
```css
.cmd-badge {
  display: inline-block;
  background: var(--green-dim);
  border: 1px solid var(--green);
  color: var(--green);
  padding: 2px 6px;
  font-size: 10px;
  margin-top: 6px;
  margin-right: 4px;
}
.cmd-badge.fail {
  background: var(--red-dim);
  border-color: var(--red);
  color: var(--red);
}
```

---

## 실행 순서

1. core/command_engine.py 생성
2. agents/A0001/system_prompt.md 하단에 명령 가이드 추가
3. api_server.py의 /api/chat 엔드포인트에 command_engine 연동
4. static/index.html에 명령 실행 결과 표시 CSS/JS 추가
5. pip install 필요 없음 (표준 라이브러리만 사용)
6. 테스트: 채팅에서 "에이전트 하나 만들어줘" 입력 → 실제 생성 확인

---

## 테스트 시나리오

1. "현재 에이전트 목록 보여줘" → [COMMAND:LIST_AGENTS] 실행
2. "데이터 분석 에이전트 하나 만들어줘" → [COMMAND:CREATE_AGENT] name=분석봇, role=data_analyst
3. "A0002에 echo 스킬 장착해줘" → [COMMAND:EQUIP_SKILL] agent_id=A0002, skill_id=echo
4. "A0002 레벨업 시켜줘" → [COMMAND:LEVELUP] agent_id=A0002, force=true
5. "A0002 삭제해" → [COMMAND:DELETE_AGENT] agent_id=A0002
