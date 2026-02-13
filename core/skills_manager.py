"""
=================================================================
  JH Agent Factory — Skills Manager
  스킬 장착/해제/생성/조회 시스템
  
  컨셉: 게임 아이템처럼 장착 가능한 플러그인 구조
=================================================================
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List


FACTORY_ROOT = Path(__file__).parent.parent
AGENTS_DIR = FACTORY_ROOT / "agents"
SKILLS_LIBRARY = FACTORY_ROOT / "skills_library"
SKILLS_JSON_DIR = SKILLS_LIBRARY / "skills"

_REQUIRED_SKILL_FIELDS = {"skill_id", "name", "description"}


# ─── 기본 스킬 템플릿 ────────────────────────────────
SKILL_TEMPLATES = {
    "log_analyzer": {
        "skill_id": "log_analyzer",
        "name": "로그 분석기",
        "description": "에이전트 로그를 분석하여 패턴과 이상을 감지",
        "category": "monitoring",
        "version": "1.0.0",
        "dependencies": ["pandas"],
        "cost": "free"
    },
    "api_reconnector": {
        "skill_id": "api_reconnector",
        "name": "API 재연결기",
        "description": "API 연결 실패 시 자동 재시도 및 복구",
        "category": "network",
        "version": "1.0.0",
        "dependencies": [],
        "cost": "free"
    },
    "agent_builder": {
        "skill_id": "agent_builder",
        "name": "에이전트 생성기",
        "description": "새로운 에이전트를 생성하는 핵심 스킬",
        "category": "factory",
        "version": "1.0.0",
        "dependencies": [],
        "cost": "free"
    },
    "resource_monitor": {
        "skill_id": "resource_monitor",
        "name": "리소스 모니터",
        "description": "CPU, 메모리, 스토리지 사용량 모니터링",
        "category": "monitoring",
        "version": "1.0.0",
        "dependencies": ["psutil"],
        "cost": "free"
    },
    "data_processor": {
        "skill_id": "data_processor",
        "name": "데이터 처리기",
        "description": "CSV, JSON, 텍스트 데이터 파싱 및 변환",
        "category": "data",
        "version": "1.0.0",
        "dependencies": ["pandas", "numpy"],
        "cost": "free"
    },
    "nlp_basic": {
        "skill_id": "nlp_basic",
        "name": "기본 자연어 처리",
        "description": "텍스트 분석, 키워드 추출, 감정 분석",
        "category": "ai",
        "version": "1.0.0",
        "dependencies": ["spacy"],
        "cost": "free"
    },
    "scheduler": {
        "skill_id": "scheduler",
        "name": "작업 스케줄러",
        "description": "주기적 작업 예약 및 실행",
        "category": "automation",
        "version": "1.0.0",
        "dependencies": [],
        "cost": "free"
    },
    "memory_compressor": {
        "skill_id": "memory_compressor",
        "name": "메모리 압축기",
        "description": "메모리 데이터를 요약·압축하여 효율적 저장",
        "category": "memory",
        "version": "1.0.0",
        "dependencies": [],
        "cost": "free"
    }
}


class SkillsManager:
    """에이전트 스킬 관리 시스템"""
    
    def __init__(self):
        self._ensure_library()
        self._json_skills = self._load_json_skills()

    def _ensure_library(self):
        """스킬 라이브러리 초기화"""
        SKILLS_LIBRARY.mkdir(parents=True, exist_ok=True)
        SKILLS_JSON_DIR.mkdir(parents=True, exist_ok=True)

        catalog_path = SKILLS_LIBRARY / "catalog.json"
        if not catalog_path.exists():
            catalog = {
                "name": "JH Skills Library",
                "version": "1.0.0",
                "skills": SKILL_TEMPLATES,
                "total_skills": len(SKILL_TEMPLATES),
                "last_updated": datetime.now().isoformat()
            }
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump(catalog, f, ensure_ascii=False, indent=2)

    def _load_json_skills(self) -> dict:
        """skills_library/skills/*.skill.json 파일에서 스킬 로드"""
        loaded = {}
        for fpath in sorted(SKILLS_JSON_DIR.glob("*.skill.json")):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                missing = _REQUIRED_SKILL_FIELDS - set(data.keys())
                if missing:
                    print(f"[WARN] Skipping {fpath.name}: missing fields {missing}")
                    continue
                loaded[data["skill_id"]] = data
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[WARN] Skipping {fpath.name}: {e}")
        return loaded

    def _resolve_skill(self, skill_id: str) -> Optional[dict]:
        """JSON 라이브러리 → 하드코딩 템플릿 순으로 스킬 조회"""
        if skill_id in self._json_skills:
            return self._json_skills[skill_id]
        if skill_id in SKILL_TEMPLATES:
            return SKILL_TEMPLATES[skill_id]
        return None

    def list_available_skills(self) -> List[dict]:
        """사용 가능한 스킬 전체 목록 (하드코딩 + JSON, JSON이 우선)"""
        merged = {**SKILL_TEMPLATES, **self._json_skills}
        return list(merged.values())
    
    def equip_skill(self, agent_id: str, skill_id: str) -> dict:
        """에이전트에 스킬 장착"""
        # 에이전트 존재 확인
        agent_path = AGENTS_DIR / agent_id
        profile_path = agent_path / "profile.json"
        
        if not profile_path.exists():
            return {"success": False, "message": f"에이전트 '{agent_id}'를 찾을 수 없습니다."}
        
        # 스킬 존재 확인
        resolved = self._resolve_skill(skill_id)
        if resolved is None:
            return {"success": False, "message": f"스킬 '{skill_id}'이(가) 라이브러리에 없습니다."}

        # 프로필 로드
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f)

        # 이미 장착 확인
        equipped_ids = [s["skill_id"] for s in profile.get("equipped_skills", [])]
        if skill_id in equipped_ids:
            return {"success": False, "message": f"스킬 '{skill_id}'은(는) 이미 장착되어 있습니다."}

        # 장착 가능 수 확인
        config_path = agent_path / "config.yaml"
        max_skills = 10
        if config_path.exists():
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            max_skills = config.get("skills", {}).get("max_equipped", 10)

        if len(equipped_ids) >= max_skills:
            return {"success": False, "message": f"최대 장착 가능 스킬 수({max_skills})에 도달했습니다."}

        # 유료 여부 확인
        skill_data = resolved.copy()
        if skill_data.get("cost") != "free":
            return {
                "success": False,
                "message": f"⚠️ 유료 스킬입니다. 비용: {skill_data['cost']}. 사용자 승인이 필요합니다.",
                "requires_approval": True
            }
        
        # 스킬 장착
        skill_data["equipped_at"] = datetime.now().isoformat()
        profile["equipped_skills"].append(skill_data)
        
        # 스킬 파일 복사
        skills_dir = agent_path / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skills_dir / f"{skill_id}.skill.json"
        with open(skill_file, "w", encoding="utf-8") as f:
            json.dump(skill_data, f, ensure_ascii=False, indent=2)
        
        # 프로필 저장
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
        
        # 로그 기록
        self._log_skill_event(agent_path, "SKILL_EQUIPPED", skill_id)
        
        return {
            "success": True,
            "message": f"✅ 스킬 '{skill_data['name']}' 장착 완료!",
            "skill": skill_data
        }
    
    def unequip_skill(self, agent_id: str, skill_id: str) -> dict:
        """에이전트에서 스킬 해제"""
        agent_path = AGENTS_DIR / agent_id
        profile_path = agent_path / "profile.json"
        
        if not profile_path.exists():
            return {"success": False, "message": f"에이전트 '{agent_id}'를 찾을 수 없습니다."}
        
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f)
        
        # 스킬 찾기
        skill_found = None
        for i, skill in enumerate(profile.get("equipped_skills", [])):
            if skill["skill_id"] == skill_id:
                skill_found = profile["equipped_skills"].pop(i)
                break
        
        if not skill_found:
            return {"success": False, "message": f"스킬 '{skill_id}'이(가) 장착되어 있지 않습니다."}
        
        # 프로필 저장
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
        
        # 스킬 파일 제거
        skill_file = agent_path / "skills" / f"{skill_id}.skill.json"
        if skill_file.exists():
            skill_file.unlink()
        
        self._log_skill_event(agent_path, "SKILL_UNEQUIPPED", skill_id)
        
        return {
            "success": True,
            "message": f"🔄 스킬 '{skill_found['name']}' 해제 완료."
        }
    
    def get_agent_skills(self, agent_id: str) -> List[dict]:
        """에이전트의 장착된 스킬 목록"""
        profile_path = AGENTS_DIR / agent_id / "profile.json"
        
        if not profile_path.exists():
            return []
        
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f)
        
        return profile.get("equipped_skills", [])
    
    def _log_skill_event(self, agent_path: Path, event: str, skill_id: str):
        """스킬 이벤트 로그"""
        log_path = agent_path / "logs" / "skills.log"
        
        logs = []
        if log_path.exists():
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except json.JSONDecodeError:
                logs = []
        
        logs.append({
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "skill_id": skill_id
        })
        
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)


# ─── 테스트 ──────────────────────────────────────────
if __name__ == "__main__":
    sm = SkillsManager()
    print("📦 사용 가능한 스킬 목록:")
    for skill in sm.list_available_skills():
        print(f"   [{skill['category']}] {skill['name']} — {skill['description']}")
