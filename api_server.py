"""
=================================================================
  JH Agent Factory — API Server  v2.0
  에이전트 팩토리 REST API (FastAPI)

  대시보드 UI와 코어 엔진을 연결하는 브릿지
=================================================================
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import json
import os
import shutil
import sys
from pathlib import Path

# 코어 모듈 임포트
sys.path.insert(0, str(Path(__file__).parent / "core"))
from agent_creator import (
    create_agent, create_master_agent,
    list_agents, get_agent, update_factory_registry,
    _load_registry, _save_registry,
)
from skills_manager import SkillsManager
from ai_router import chat as ai_chat, get_router_status, clear_session, get_session

# ─── 경로 상수 ──────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
AGENTS_DIR = PROJECT_ROOT / "agents"
CATALOG_PATH = PROJECT_ROOT / "skills_library" / "catalog.json"
STATIC_DIR = PROJECT_ROOT / "static"

app = FastAPI(
    title="JH Agent Factory",
    description="에이전트 공장형 시스템 API",
    version="2.2.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

skills_mgr = SkillsManager()


# ─── Request Models ──────────────────────────────────
class CreateAgentRequest(BaseModel):
    name: str
    role: str = "general"
    created_by: Optional[str] = None
    icon: str = "🤖"
    color: str = "#3B82F6"
    description: str = ""
    is_master: bool = False


class SkillActionRequest(BaseModel):
    agent_id: str
    skill_id: str


class SkillBody(BaseModel):
    skill_id: str


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class LevelUpRequest(BaseModel):
    force: bool = False


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


class TransitionReq(BaseModel):
    new_state: str
    reason: str = "manual"


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


# ─── 레벨업 조건 ─────────────────────────────────────
LEVEL_REQUIREMENTS = {
    1: {"skills": 1, "tasks": 1},
    2: {"skills": 3, "tasks": 10},
    3: {"skills": 3, "tasks": 50, "max_error_rate": 0.10},
    5: {"skills": 5, "tasks": 200},
    7: {"skills": 5, "tasks": 500, "max_error_rate": 0.05},
}


# ═══════════════════════════════════════════════════════
# 에이전트 API (기존 유지)
# ═══════════════════════════════════════════════════════

@app.get("/api/agents")
def api_list_agents():
    """전체 에이전트 목록"""
    agents = list_agents()
    return {"agents": agents, "total": len(agents)}


@app.get("/api/agents/{agent_id}")
def api_get_agent(agent_id: str):
    """에이전트 상세 정보"""
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="에이전트를 찾을 수 없습니다.")
    return agent


@app.post("/api/agents/create")
def api_create_agent(req: CreateAgentRequest):
    """새 에이전트 생성"""
    if req.is_master:
        result = create_master_agent(req.name)
    else:
        try:
            profile = create_agent(
                name=req.name,
                role=req.role,
                is_master=False
            )
            result = {"success": True, "agent_id": profile["agent_id"], "profile": profile}
        except Exception as e:
            result = {"success": False, "message": str(e)}

    return result


@app.delete("/api/agents/{agent_id}")
def api_delete_agent(agent_id: str):
    """에이전트 삭제 (마스터는 삭제 불가)"""
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="에이전트를 찾을 수 없습니다.")
    if agent.get("role") == "master_controller":
        raise HTTPException(status_code=400, detail="마스터 에이전트는 삭제할 수 없습니다.")

    # 폴더 삭제
    agent_path = AGENTS_DIR / agent_id
    if agent_path.exists():
        shutil.rmtree(agent_path)

    # 레지스트리에서 제거
    reg = _load_registry()
    reg["agents"] = [a for a in reg.get("agents", []) if a.get("agent_id") != agent_id]
    _save_registry(reg)

    return {"success": True, "message": f"에이전트 {agent_id} 삭제 완료"}


# ═══════════════════════════════════════════════════════
# 스킬 API (기존 유지 + 새 엔드포인트)
# ═══════════════════════════════════════════════════════

@app.get("/api/skills")
def api_list_skills():
    """사용 가능한 스킬 목록"""
    skills = skills_mgr.list_available_skills()
    return {"skills": skills, "total": len(skills)}


@app.get("/api/agents/{agent_id}/skills")
def api_agent_skills(agent_id: str):
    """에이전트 장착 스킬 목록"""
    skills = skills_mgr.get_agent_skills(agent_id)
    return {"skills": skills, "total": len(skills)}


@app.post("/api/skills/equip")
def api_equip_skill(req: SkillActionRequest):
    """스킬 장착 (레거시)"""
    return skills_mgr.equip_skill(req.agent_id, req.skill_id)


@app.post("/api/skills/unequip")
def api_unequip_skill(req: SkillActionRequest):
    """스킬 해제 (레거시)"""
    return skills_mgr.unequip_skill(req.agent_id, req.skill_id)


@app.post("/api/agents/{agent_id}/skills")
def api_equip_skill_v2(agent_id: str, body: SkillBody):
    """스킬 장착 v2"""
    return skills_mgr.equip_skill(agent_id, body.skill_id)


@app.delete("/api/agents/{agent_id}/skills/{skill_id}")
def api_unequip_skill_v2(agent_id: str, skill_id: str):
    """스킬 해제 v2"""
    return skills_mgr.unequip_skill(agent_id, skill_id)


@app.get("/api/skills/catalog")
def api_skills_catalog():
    """skills_library/catalog.json 반환"""
    if CATALOG_PATH.exists():
        data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        return data
    return {"skills": {}, "total_skills": 0}


# ═══════════════════════════════════════════════════════
# 레벨업 API
# ═══════════════════════════════════════════════════════

@app.post("/api/agents/{agent_id}/levelup")
def api_levelup(agent_id: str, body: LevelUpRequest):
    """에이전트 레벨업 심사"""
    profile_path = AGENTS_DIR / agent_id / "profile.json"
    if not profile_path.exists():
        raise HTTPException(status_code=404, detail="에이전트를 찾을 수 없습니다.")

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    current_level = profile.get("level", 1)
    equipped = profile.get("equipped_skills", [])
    learning = profile.get("learning", {})
    tasks_done = learning.get("tasks_completed", 0)
    error_rate = learning.get("error_rate", 0.0)

    if body.force:
        # 강제 레벨업
        profile["level"] = current_level + 1
        profile_path.write_text(
            json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # 레지스트리도 동기화
        reg = _load_registry()
        for a in reg.get("agents", []):
            if a.get("agent_id") == agent_id:
                a["level"] = profile["level"]
                break
        _save_registry(reg)
        return {"success": True, "new_level": profile["level"], "method": "force"}

    # 자동 판정
    req = LEVEL_REQUIREMENTS.get(current_level)
    if not req:
        return {"success": False, "message": f"레벨 {current_level}에서의 승급 조건이 정의되지 않았습니다."}

    reasons = []
    if len(equipped) < req.get("skills", 0):
        reasons.append(f"스킬 {len(equipped)}/{req['skills']}개")
    if tasks_done < req.get("tasks", 0):
        reasons.append(f"완료 작업 {tasks_done}/{req['tasks']}회")
    if "max_error_rate" in req and error_rate > req["max_error_rate"]:
        reasons.append(f"오류율 {error_rate:.1%} > {req['max_error_rate']:.0%}")

    if reasons:
        return {"success": False, "message": "레벨업 조건 미달: " + ", ".join(reasons)}

    profile["level"] = current_level + 1
    profile_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    reg = _load_registry()
    for a in reg.get("agents", []):
        if a.get("agent_id") == agent_id:
            a["level"] = profile["level"]
            break
    _save_registry(reg)
    return {"success": True, "new_level": profile["level"], "method": "auto"}


# ═══════════════════════════════════════════════════════
# 채팅 API (춘식이)
# ═══════════════════════════════════════════════════════

def _load_system_prompt() -> str:
    """agents/A0001/system_prompt.md 로드"""
    sp_path = AGENTS_DIR / "A0001" / "system_prompt.md"
    if sp_path.exists():
        return sp_path.read_text(encoding="utf-8")
    return "너는 JH Agent Factory의 마스터 에이전트 춘식이다."


@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    """춘식이 채팅"""
    system_prompt = _load_system_prompt()
    result = await ai_chat(req.session_id, req.message, system_prompt)

    # 명령 엔진 처리
    if result.get("error") is None and result.get("reply"):
        from core.command_engine import process_ai_response
        processed = process_ai_response(result["reply"])
        result["reply"] = processed["display_text"]
        result["commands_executed"] = processed["commands_executed"]
        result["had_commands"] = processed["had_commands"]

    return result


@app.get("/api/chat/history/{session_id}")
def api_chat_history(session_id: str):
    """채팅 히스토리"""
    sess = get_session(session_id)
    return {"session_id": session_id, "messages": sess["messages"]}


@app.delete("/api/chat/{session_id}")
def api_chat_clear(session_id: str):
    """세션 초기화"""
    clear_session(session_id)
    return {"success": True, "message": f"세션 {session_id} 초기화 완료"}


# ═══════════════════════════════════════════════════════
# 시스템 / 라우터 상태
# ═══════════════════════════════════════════════════════

@app.get("/api/system/status")
def api_system_status():
    """팩토리 시스템 상태"""
    agents = list_agents()
    master_count = sum(1 for a in agents if a.get("role") == "master_controller")

    return {
        "status": "operational",
        "factory_name": "JH Agent Factory",
        "version": "2.2.0",
        "total_agents": len(agents),
        "master_agents": master_count,
        "worker_agents": len(agents) - master_count,
        "skills_available": len(skills_mgr.list_available_skills())
    }


@app.get("/api/router/status")
def api_router_status():
    """AI 라우터 상태"""
    return get_router_status()


# ═══════════════════════════════════════════════════════
# 에이전트 통신 API (v2.2)
# ═══════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════
# 상태 머신 API (v2.2)
# ═══════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════
# 에이전트 복제 API (v2.2)
# ═══════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════
# 대시보드 UI
# ═══════════════════════════════════════════════════════

@app.get("/")
def dashboard():
    """대시보드 메인 페이지"""
    return FileResponse(STATIC_DIR / "index.html")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health")
def health_check():
    """Railway 헬스체크 엔드포인트"""
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
