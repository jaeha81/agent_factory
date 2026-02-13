"""
=================================================================
  JH Agent Factory — API Server
  에이전트 팩토리 REST API (FastAPI)
  
  대시보드 UI와 코어 엔진을 연결하는 브릿지
=================================================================
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import sys
from pathlib import Path

# 코어 모듈 임포트
sys.path.insert(0, str(Path(__file__).parent / "core"))
from agent_creator import (
    create_agent, create_master_agent,
    list_agents, get_agent, update_factory_registry
)
from skills_manager import SkillsManager

app = FastAPI(
    title="JH Agent Factory",
    description="에이전트 공장형 시스템 API",
    version="1.0.0"
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


# ─── 에이전트 API ────────────────────────────────────
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


# ─── 스킬 API ────────────────────────────────────────
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
    """스킬 장착"""
    return skills_mgr.equip_skill(req.agent_id, req.skill_id)


@app.post("/api/skills/unequip")
def api_unequip_skill(req: SkillActionRequest):
    """스킬 해제"""
    return skills_mgr.unequip_skill(req.agent_id, req.skill_id)


# ─── 시스템 상태 ─────────────────────────────────────
@app.get("/api/system/status")
def api_system_status():
    """팩토리 시스템 상태"""
    agents = list_agents()
    master_count = sum(1 for a in agents if a.get("role") == "master_controller")
    
    return {
        "status": "operational",
        "factory_name": "JH Agent Factory",
        "total_agents": len(agents),
        "master_agents": master_count,
        "worker_agents": len(agents) - master_count,
        "skills_available": len(skills_mgr.list_available_skills())
    }


# ─── 대시보드 UI ─────────────────────────────────────
STATIC_DIR = Path(__file__).parent / "static"

@app.get("/")
def dashboard():
    """대시보드 메인 페이지"""
    return FileResponse(STATIC_DIR / "index.html")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
