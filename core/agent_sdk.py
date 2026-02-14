"""
core/agent_sdk.py
OpenAI Agents SDK 기반 전문화 에이전트 시스템

전문화 에이전트 5종:
  1. 코드 리뷰어 (code_reviewer)     — 코드 분석, 리뷰, 버그 탐지, 개선 제안
  2. 데이터 분석가 (data_analyst)     — 데이터 분석, 패턴 감지, 인사이트 도출
  3. 리서치 어시스턴트 (researcher)   — 조사, 요약, 정리, 비교 분석
  4. 콘텐츠 크리에이터 (content_creator) — 글쓰기, 콘텐츠 기획, 카피라이팅
  5. 시스템 관리자 (system_admin)     — 팩토리 모니터링, 트러블슈팅, 상태 점검

+ 트리아지 에이전트: 사용자 요청을 분석하여 적합한 전문 에이전트로 핸드오프

외부 의존: openai-agents>=0.8.0
"""

import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("agent_sdk")

# ─── 경로 상수 ────────────────────────────────────────
_CORE_DIR = Path(__file__).parent
_PROJECT_ROOT = _CORE_DIR.parent
_AGENTS_DIR = _PROJECT_ROOT / "agents"

# ─── dotenv ───────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(_PROJECT_ROOT / ".env")
except ImportError:
    pass

# ─── SDK imports ──────────────────────────────────────
try:
    from agents import Agent, Runner, function_tool, ModelSettings
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from openai import AsyncOpenAI
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    logger.warning("openai-agents SDK가 설치되지 않았습니다. pip install openai-agents")


# ═══════════════════════════════════════════════════════
# 모델 프로바이더
# ═══════════════════════════════════════════════════════

# 무료 프로바이더 (우선 사용)
FREE_PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
        "model": "llama-3.1-8b-instant",
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "key_env": "TOGETHER_API_KEY",
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
        "model": "meta-llama/llama-3.1-8b-instruct:free",
    },
}

# 유료 프로바이더 (무료 제한 시 폴백)
PAID_PROVIDERS = {
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "key_env": "GEMINI_API_KEY",
        "model": "gemini-2.5-pro",
    },
}

# 전체 프로바이더 (API에서 참조용)
PROVIDER_CONFIGS = {**FREE_PROVIDERS, **PAID_PROVIDERS}


def _create_model(provider: str = "groq") -> "OpenAIChatCompletionsModel":
    """프로바이더 이름으로 SDK 모델을 생성한다."""
    if not SDK_AVAILABLE:
        raise RuntimeError("openai-agents SDK가 필요합니다. pip install openai-agents")

    config = PROVIDER_CONFIGS.get(provider)
    if not config:
        raise ValueError(f"지원하지 않는 프로바이더: {provider}")

    api_key = os.environ.get(config["key_env"], "")
    if not api_key:
        raise RuntimeError(f"{config['key_env']} 환경변수가 설정되지 않았습니다.")

    client = AsyncOpenAI(
        base_url=config["base_url"],
        api_key=api_key,
    )

    return OpenAIChatCompletionsModel(
        model=config["model"],
        openai_client=client,
    )


def _get_available_model(include_paid: bool = False) -> "OpenAIChatCompletionsModel":
    """사용 가능한 모델을 생성한다. 무료 우선, include_paid=True면 유료도 포함."""
    # 1차: 무료 프로바이더 시도
    for name, config in FREE_PROVIDERS.items():
        if os.environ.get(config["key_env"]):
            try:
                return _create_model(name)
            except Exception as e:
                logger.warning("무료 프로바이더 %s 모델 생성 실패: %s", name, e)
                continue

    # 2차: 유료 프로바이더 폴백
    if include_paid:
        for name, config in PAID_PROVIDERS.items():
            if os.environ.get(config["key_env"]):
                try:
                    logger.info("유료 프로바이더 폴백: %s (%s)", name, config["model"])
                    return _create_model(name)
                except Exception as e:
                    logger.warning("유료 프로바이더 %s 모델 생성 실패: %s", name, e)
                    continue

    raise RuntimeError("사용 가능한 AI 프로바이더가 없습니다. .env에 API 키를 설정하세요.")


# ═══════════════════════════════════════════════════════
# 함수 도구 (Function Tools)
# ═══════════════════════════════════════════════════════

if SDK_AVAILABLE:

    @function_tool
    def list_factory_agents() -> str:
        """팩토리에 등록된 모든 에이전트 목록을 조회합니다."""
        from core.agent_creator import list_agents
        agents = list_agents()
        if not agents:
            return "등록된 에이전트가 없습니다."
        lines = []
        for a in agents:
            lines.append(
                f"- {a['agent_id']}: {a['name']} "
                f"(역할={a['role']}, Lv.{a['level']}, 상태={a['status']})"
            )
        return "\n".join(lines)

    @function_tool
    def get_agent_detail(agent_id: str) -> str:
        """특정 에이전트의 상세 프로필(스킬, 스탯, 학습 이력)을 조회합니다."""
        from core.agent_creator import get_agent
        agent = get_agent(agent_id)
        if not agent:
            return f"에이전트 '{agent_id}'를 찾을 수 없습니다."
        return json.dumps(agent, ensure_ascii=False, indent=2)

    @function_tool
    def list_skills_catalog() -> str:
        """팩토리 스킬 라이브러리에서 사용 가능한 모든 스킬을 조회합니다."""
        from core.skills_manager import SkillsManager
        sm = SkillsManager()
        skills = sm.list_available_skills()
        if not skills:
            return "사용 가능한 스킬이 없습니다."
        lines = []
        for s in skills:
            lines.append(
                f"- {s['skill_id']}: {s['name']} "
                f"[{s.get('category', 'etc')}] — {s['description']}"
            )
        return "\n".join(lines)

    @function_tool
    def read_agent_memory(agent_id: str, memory_type: str = "short_term") -> str:
        """에이전트의 메모리를 읽습니다. memory_type: short_term / long_term / compressed"""
        mem_dir = _AGENTS_DIR / agent_id / "memory" / memory_type
        if not mem_dir.exists():
            return f"메모리 디렉토리가 없습니다: {agent_id}/memory/{memory_type}"

        files = sorted(mem_dir.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True)
        if not files:
            return f"{memory_type} 메모리가 비어있습니다."

        result = []
        for f in files[:5]:
            try:
                content = f.read_text(encoding="utf-8")[:500]
                result.append(f"[{f.name}]\n{content}")
            except Exception:
                continue
        return "\n---\n".join(result) if result else "메모리 데이터를 읽을 수 없습니다."

    @function_tool
    def save_to_memory(agent_id: str, content: str, memory_type: str = "short_term") -> str:
        """에이전트의 메모리에 데이터를 저장합니다."""
        mem_dir = _AGENTS_DIR / agent_id / "memory" / memory_type
        mem_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filepath = mem_dir / f"{ts}.json"

        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "content": content,
            "source": "agent_sdk",
        }
        filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return f"메모리 저장 완료: {agent_id}/memory/{memory_type}/{filepath.name}"

    @function_tool
    def analyze_code(code: str, language: str = "python") -> str:
        """코드를 정적 분석하여 구조, 함수, 클래스, 임포트 정보를 반환합니다."""
        lines = code.strip().split("\n")
        analysis = {
            "language": language,
            "total_lines": len(lines),
            "blank_lines": sum(1 for ln in lines if not ln.strip()),
            "comment_lines": 0,
            "functions": [],
            "classes": [],
            "imports": [],
        }

        for i, line in enumerate(lines):
            s = line.strip()
            if language == "python":
                if s.startswith("#"):
                    analysis["comment_lines"] += 1
                if s.startswith("def "):
                    name = s.split("(")[0].replace("def ", "")
                    analysis["functions"].append({"line": i + 1, "name": name})
                elif s.startswith("class "):
                    name = s.split("(")[0].split(":")[0].replace("class ", "")
                    analysis["classes"].append({"line": i + 1, "name": name})
                elif s.startswith("import ") or s.startswith("from "):
                    analysis["imports"].append(s)
            elif language in ("javascript", "typescript"):
                if s.startswith("//"):
                    analysis["comment_lines"] += 1
                if "function " in s:
                    analysis["functions"].append({"line": i + 1, "snippet": s[:80]})
                elif s.startswith("class "):
                    analysis["classes"].append({"line": i + 1, "snippet": s[:80]})

        return json.dumps(analysis, ensure_ascii=False, indent=2)

    @function_tool
    def search_project_files(pattern: str, directory: str = ".") -> str:
        """프로젝트 내 파일을 glob 패턴으로 검색합니다."""
        search_dir = _PROJECT_ROOT / directory
        if not search_dir.exists():
            return f"디렉토리가 없습니다: {directory}"

        matches = []
        for f in search_dir.rglob(pattern):
            rel = str(f.relative_to(_PROJECT_ROOT))
            if ".git" in rel or "__pycache__" in rel or ".venv" in rel:
                continue
            matches.append(rel)

        if not matches:
            return f"패턴 '{pattern}'에 일치하는 파일이 없습니다."
        return "\n".join(sorted(matches)[:30])

    @function_tool
    def read_file_content(filepath: str, max_lines: int = 100) -> str:
        """프로젝트 내 파일의 내용을 읽습니다. (최대 max_lines줄)"""
        target = _PROJECT_ROOT / filepath
        if not target.exists():
            return f"파일이 없습니다: {filepath}"
        if not target.is_file():
            return f"파일이 아닙니다: {filepath}"

        try:
            lines = target.read_text(encoding="utf-8").split("\n")
            content = "\n".join(lines[:max_lines])
            if len(lines) > max_lines:
                content += f"\n... (이하 {len(lines) - max_lines}줄 생략)"
            return content
        except Exception as e:
            return f"파일 읽기 실패: {e}"

    @function_tool
    def get_factory_status() -> str:
        """팩토리 시스템의 전체 상태(에이전트 수, 라우터 상태 등)를 조회합니다."""
        from core.agent_creator import list_agents
        from core.ai_router import get_router_status

        agents = list_agents()
        router = get_router_status()

        status = {
            "factory": "JH Agent Factory",
            "total_agents": len(agents),
            "online": sum(1 for a in agents if a.get("status") == "online"),
            "agents": [
                {"id": a["agent_id"], "name": a["name"], "role": a["role"], "status": a["status"]}
                for a in agents
            ],
            "ai_router": {
                "active_sessions": router.get("active_sessions", 0),
                "providers": [
                    {"name": p["name"], "available": p["available"]}
                    for p in router.get("providers", [])
                ],
            },
        }
        return json.dumps(status, ensure_ascii=False, indent=2)

    # ─── 지식 베이스 도구 ─────────────────────────────

    @function_tool
    def query_knowledge_base(kb_id: str, question: str) -> str:
        """지식 베이스에 질문합니다. Gemini 2.5 Pro가 등록된 문서를 기반으로 답변합니다."""
        import asyncio
        from core.knowledge_base import get_knowledge_base

        kb = get_knowledge_base(kb_id)
        if not kb:
            return f"지식 베이스 '{kb_id}'를 찾을 수 없습니다."

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(
                        asyncio.run, kb.query(question)
                    ).result()
            else:
                result = asyncio.run(kb.query(question))
        except Exception as e:
            return f"질의 실패: {e}"

        if result.get("error"):
            return f"오류: {result['error']}"
        return result["answer"]

    @function_tool
    def list_knowledge() -> str:
        """사용 가능한 지식 베이스 목록을 조회합니다."""
        from core.knowledge_base import list_knowledge_bases

        kbs = list_knowledge_bases()
        if not kbs:
            return "등록된 지식 베이스가 없습니다."

        lines = []
        for kb in kbs:
            lines.append(
                f"- {kb['kb_id']}: {kb['name']} "
                f"(소스 {kb['sources_count']}개) — {kb.get('description', '')}"
            )
        return "\n".join(lines)

    @function_tool
    def get_knowledge_sources(kb_id: str) -> str:
        """특정 지식 베이스에 등록된 소스(문서) 목록을 조회합니다."""
        from core.knowledge_base import get_knowledge_base

        kb = get_knowledge_base(kb_id)
        if not kb:
            return f"지식 베이스 '{kb_id}'를 찾을 수 없습니다."

        sources = kb.list_sources()
        if not sources:
            return f"지식 베이스 '{kb_id}'에 등록된 소스가 없습니다."

        lines = []
        for s in sources:
            size_kb = s.get("size_bytes", 0) / 1024
            lines.append(
                f"- {s['source_id']}: {s['title']} "
                f"({s['type']}, {size_kb:.1f}KB, {s.get('added_at', '')[:10]})"
            )
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# 전문화 에이전트 정의
# ═══════════════════════════════════════════════════════

# 각 전문 에이전트의 지시문과 도구 매핑
SPECIALIST_DEFS = {
    "code_reviewer": {
        "name": "코드 리뷰어",
        "icon": "🔍",
        "role": "code_reviewer",
        "description": "코드 분석, 리뷰, 버그 탐지, 리팩토링 제안 전문 에이전트",
        "instructions": (
            "너는 JH Agent Factory의 코드 리뷰 전문 에이전트다.\n\n"
            "전문 분야:\n"
            "- 코드 구조 분석 및 아키텍처 리뷰\n"
            "- 버그 및 잠재적 이슈 탐지\n"
            "- 성능 개선 포인트 식별\n"
            "- 코딩 컨벤션 및 베스트 프랙티스 제안\n"
            "- 리팩토링 방향 제시\n\n"
            "원칙:\n"
            "- 구체적인 코드 라인을 언급하며 리뷰하라.\n"
            "- 문제점뿐 아니라 잘된 점도 언급하라.\n"
            "- 개선 제안은 코드 예시와 함께 제시하라.\n"
            "- 보안 취약점(SQL injection, XSS 등)을 주의 깊게 확인하라.\n"
            "- 한국어로 응답하라."
        ),
        "tools_keys": [
            "analyze_code", "search_project_files", "read_file_content",
            "read_agent_memory", "save_to_memory",
            "query_knowledge_base", "list_knowledge",
        ],
    },
    "data_analyst": {
        "name": "데이터 분석가",
        "icon": "📊",
        "role": "data_analyst",
        "description": "데이터 분석, 패턴 감지, 인사이트 도출, 시각화 제안 전문 에이전트",
        "instructions": (
            "너는 JH Agent Factory의 데이터 분석 전문 에이전트다.\n\n"
            "전문 분야:\n"
            "- 데이터 구조 분석 및 품질 평가\n"
            "- 통계적 패턴 및 이상치 탐지\n"
            "- 인사이트 도출 및 비즈니스 의미 해석\n"
            "- 데이터 시각화 방법 제안\n"
            "- 데이터 파이프라인 설계 조언\n\n"
            "원칙:\n"
            "- 데이터를 기반으로 근거 있는 분석을 제시하라.\n"
            "- 수치와 비율을 구체적으로 명시하라.\n"
            "- 시각화가 필요한 경우 적합한 차트 유형을 추천하라.\n"
            "- 분석 결과의 한계와 가정을 명확히 밝혀라.\n"
            "- 한국어로 응답하라."
        ),
        "tools_keys": [
            "analyze_code", "search_project_files", "read_file_content",
            "read_agent_memory", "save_to_memory", "get_agent_detail",
            "query_knowledge_base", "list_knowledge",
        ],
    },
    "researcher": {
        "name": "리서치 어시스턴트",
        "icon": "🔬",
        "role": "researcher",
        "description": "조사, 요약, 비교 분석, 보고서 작성 전문 에이전트",
        "instructions": (
            "너는 JH Agent Factory의 리서치 전문 에이전트다.\n\n"
            "전문 분야:\n"
            "- 기술 조사 및 비교 분석\n"
            "- 문서 요약 및 핵심 포인트 추출\n"
            "- 트렌드 분석 및 기술 동향 파악\n"
            "- 구조화된 보고서 작성\n"
            "- 장단점 비교표 작성\n\n"
            "원칙:\n"
            "- 출처와 근거를 명시하라.\n"
            "- 객관적 사실과 주관적 의견을 구분하라.\n"
            "- 요약은 핵심 3~5개 포인트로 구조화하라.\n"
            "- 비교 분석 시 동일한 기준으로 평가하라.\n"
            "- 한국어로 응답하라."
        ),
        "tools_keys": [
            "search_project_files", "read_file_content",
            "list_factory_agents", "list_skills_catalog",
            "read_agent_memory", "save_to_memory",
            "query_knowledge_base", "list_knowledge", "get_knowledge_sources",
        ],
    },
    "content_creator": {
        "name": "콘텐츠 크리에이터",
        "icon": "✍️",
        "role": "content_creator",
        "description": "글쓰기, 콘텐츠 기획, 카피라이팅, 문서 작성 전문 에이전트",
        "instructions": (
            "너는 JH Agent Factory의 콘텐츠 크리에이션 전문 에이전트다.\n\n"
            "전문 분야:\n"
            "- 기술 블로그 및 문서 작성\n"
            "- 카피라이팅 및 마케팅 문구 작성\n"
            "- README, 가이드, 튜토리얼 작성\n"
            "- 프레젠테이션 구조 기획\n"
            "- 소셜 미디어 콘텐츠 기획\n\n"
            "원칙:\n"
            "- 독자의 수준에 맞춰 난이도를 조절하라.\n"
            "- 명확하고 간결한 문장을 사용하라.\n"
            "- 구조화된 형식(헤딩, 목록, 코드블록)을 활용하라.\n"
            "- 톤앤매너를 요청에 맞게 조절하라.\n"
            "- 한국어로 응답하라."
        ),
        "tools_keys": [
            "search_project_files", "read_file_content",
            "read_agent_memory", "save_to_memory",
            "query_knowledge_base", "list_knowledge",
        ],
    },
    "system_admin": {
        "name": "시스템 관리자",
        "icon": "⚙️",
        "role": "system_admin",
        "description": "팩토리 모니터링, 에이전트 상태 점검, 트러블슈팅 전문 에이전트",
        "instructions": (
            "너는 JH Agent Factory의 시스템 관리 전문 에이전트다.\n\n"
            "전문 분야:\n"
            "- 팩토리 시스템 상태 모니터링\n"
            "- 에이전트 상태 점검 및 진단\n"
            "- 스킬 시스템 관리 및 권장\n"
            "- 오류 분석 및 트러블슈팅\n"
            "- 시스템 최적화 제안\n\n"
            "원칙:\n"
            "- 시스템 상태를 정확한 수치로 보고하라.\n"
            "- 이상 징후 발견 시 원인과 대응 방안을 함께 제시하라.\n"
            "- 에이전트 레벨업 조건 충족 여부를 점검하라.\n"
            "- 스킬 장착 추천은 에이전트의 역할에 맞게 하라.\n"
            "- 한국어로 응답하라."
        ),
        "tools_keys": [
            "get_factory_status", "list_factory_agents", "get_agent_detail",
            "list_skills_catalog", "read_agent_memory", "save_to_memory",
            "query_knowledge_base", "list_knowledge", "get_knowledge_sources",
        ],
    },
}

# 도구 이름 → 함수 매핑 (SDK 사용 가능 시에만)
_TOOL_REGISTRY = {}
if SDK_AVAILABLE:
    _TOOL_REGISTRY = {
        "list_factory_agents": list_factory_agents,
        "get_agent_detail": get_agent_detail,
        "list_skills_catalog": list_skills_catalog,
        "read_agent_memory": read_agent_memory,
        "save_to_memory": save_to_memory,
        "analyze_code": analyze_code,
        "search_project_files": search_project_files,
        "read_file_content": read_file_content,
        "get_factory_status": get_factory_status,
        "query_knowledge_base": query_knowledge_base,
        "list_knowledge": list_knowledge,
        "get_knowledge_sources": get_knowledge_sources,
    }


def _build_tools(keys: list) -> list:
    """도구 키 목록으로 실제 function_tool 객체 리스트를 생성한다."""
    tools = []
    for k in keys:
        tool = _TOOL_REGISTRY.get(k)
        if tool:
            tools.append(tool)
    return tools


# ═══════════════════════════════════════════════════════
# 에이전트 팩토리 (SDK Agent 빌더)
# ═══════════════════════════════════════════════════════

_cached_agents: dict[str, "Agent"] = {}
_cached_triage: Optional["Agent"] = None


def _build_specialist(agent_type: str, model=None) -> "Agent":
    """전문화 에이전트를 생성한다."""
    if not SDK_AVAILABLE:
        raise RuntimeError("openai-agents SDK가 필요합니다.")

    defn = SPECIALIST_DEFS.get(agent_type)
    if not defn:
        raise ValueError(f"알 수 없는 에이전트 타입: {agent_type}")

    if model is None:
        model = _get_available_model()

    tools = _build_tools(defn["tools_keys"])

    return Agent(
        name=defn["name"],
        instructions=defn["instructions"],
        tools=tools,
        model=model,
    )


def _build_triage(model=None) -> "Agent":
    """트리아지 에이전트를 생성한다. 요청을 분석하여 적절한 전문가에게 핸드오프한다."""
    if not SDK_AVAILABLE:
        raise RuntimeError("openai-agents SDK가 필요합니다.")

    if model is None:
        model = _get_available_model()

    # 전문가 에이전트들 생성
    specialists = []
    for agent_type in SPECIALIST_DEFS:
        agent = _build_specialist(agent_type, model)
        specialists.append(agent)

    # 전문가 목록을 지시문에 포함
    specialist_desc = []
    for defn in SPECIALIST_DEFS.values():
        specialist_desc.append(f"- {defn['name']}: {defn['description']}")
    specialist_list = "\n".join(specialist_desc)

    triage_instructions = (
        "너는 JH Agent Factory의 트리아지(분류) 에이전트다.\n"
        "사용자의 요청을 분석하여 가장 적합한 전문 에이전트에게 핸드오프하라.\n\n"
        f"사용 가능한 전문 에이전트:\n{specialist_list}\n\n"
        "라우팅 규칙:\n"
        "- 코드 관련 질문 → 코드 리뷰어\n"
        "- 데이터/분석/통계 관련 → 데이터 분석가\n"
        "- 조사/비교/요약 관련 → 리서치 어시스턴트\n"
        "- 글쓰기/문서/콘텐츠 → 콘텐츠 크리에이터\n"
        "- 시스템/에이전트 관리/상태 → 시스템 관리자\n\n"
        "판단이 어려우면 사용자에게 명확히 질문하라.\n"
        "한국어로 응답하라."
    )

    return Agent(
        name="트리아지",
        instructions=triage_instructions,
        handoffs=specialists,
        model=model,
    )


# ═══════════════════════════════════════════════════════
# 공개 API
# ═══════════════════════════════════════════════════════

def list_specialists() -> list[dict]:
    """사용 가능한 전문 에이전트 목록을 반환한다."""
    result = []
    for agent_type, defn in SPECIALIST_DEFS.items():
        result.append({
            "type": agent_type,
            "name": defn["name"],
            "icon": defn["icon"],
            "role": defn["role"],
            "description": defn["description"],
            "tools": defn["tools_keys"],
        })
    return result


async def run_specialist(agent_type: str, task: str, provider: str = None) -> dict:
    """
    특정 전문 에이전트를 직접 실행한다.
    무료 프로바이더 실패 시 Gemini 2.5 Pro로 자동 폴백.

    Args:
        agent_type: 전문 에이전트 타입 (code_reviewer, data_analyst, ...)
        task: 사용자 요청 텍스트
        provider: LLM 프로바이더 (groq, together, openrouter, gemini). None이면 자동 선택.

    Returns:
        {"output": str, "agent": str, "agent_type": str, "provider": str, "error": str|None}
    """
    if not SDK_AVAILABLE:
        return {"output": "", "agent": "", "agent_type": agent_type,
                "provider": "", "error": "openai-agents SDK가 설치되지 않았습니다."}

    # 명시적 프로바이더 지정 시 해당 프로바이더만 사용
    if provider:
        return await _run_specialist_with_model(agent_type, task, provider)

    # 자동 선택: 무료 → 유료 폴백
    # 1차: 무료 프로바이더로 시도
    free_error = None
    for name, config in FREE_PROVIDERS.items():
        if not os.environ.get(config["key_env"]):
            continue
        result = await _run_specialist_with_model(agent_type, task, name)
        if result["error"] is None:
            return result
        free_error = result["error"]
        logger.warning("무료 프로바이더 %s 실행 실패, 다음 시도: %s", name, free_error)

    # 2차: Gemini 2.5 Pro 폴백
    for name, config in PAID_PROVIDERS.items():
        if not os.environ.get(config["key_env"]):
            continue
        logger.info("유료 폴백 → %s (%s)", name, config["model"])
        result = await _run_specialist_with_model(agent_type, task, name)
        if result["error"] is None:
            result["fallback"] = True
            result["fallback_reason"] = f"무료 프로바이더 실패: {free_error}"
            return result

    return {
        "output": "", "agent": SPECIALIST_DEFS.get(agent_type, {}).get("name", agent_type),
        "agent_type": agent_type, "provider": "",
        "error": free_error or "사용 가능한 프로바이더가 없습니다.",
    }


async def _run_specialist_with_model(agent_type: str, task: str, provider: str) -> dict:
    """단일 프로바이더로 전문 에이전트를 실행한다."""
    try:
        model = _create_model(provider)
        agent = _build_specialist(agent_type, model)
        result = await Runner.run(agent, task)

        return {
            "output": result.final_output,
            "agent": SPECIALIST_DEFS[agent_type]["name"],
            "agent_type": agent_type,
            "provider": provider,
            "error": None,
        }
    except Exception as e:
        logger.error("에이전트 실행 실패 [%s/%s]: %s", agent_type, provider, e)
        return {
            "output": "",
            "agent": SPECIALIST_DEFS.get(agent_type, {}).get("name", agent_type),
            "agent_type": agent_type,
            "provider": provider,
            "error": str(e),
        }


async def run_triage(task: str, provider: str = None) -> dict:
    """
    트리아지 에이전트를 통해 자동으로 적합한 전문가를 선택하여 실행한다.
    무료 프로바이더 실패 시 Gemini 2.5 Pro로 자동 폴백.

    Args:
        task: 사용자 요청 텍스트
        provider: LLM 프로바이더. None이면 자동 선택.

    Returns:
        {"output": str, "agent": str, "agent_type": str, "provider": str, "error": str|None}
    """
    if not SDK_AVAILABLE:
        return {"output": "", "agent": "", "agent_type": "triage",
                "provider": "", "error": "openai-agents SDK가 설치되지 않았습니다."}

    # 명시적 프로바이더 지정 시
    if provider:
        return await _run_triage_with_model(task, provider)

    # 자동 선택: 무료 → 유료 폴백
    free_error = None
    for name, config in FREE_PROVIDERS.items():
        if not os.environ.get(config["key_env"]):
            continue
        result = await _run_triage_with_model(task, name)
        if result["error"] is None:
            return result
        free_error = result["error"]
        logger.warning("트리아지 무료 프로바이더 %s 실패: %s", name, free_error)

    # Gemini 2.5 Pro 폴백
    for name, config in PAID_PROVIDERS.items():
        if not os.environ.get(config["key_env"]):
            continue
        logger.info("트리아지 유료 폴백 → %s (%s)", name, config["model"])
        result = await _run_triage_with_model(task, name)
        if result["error"] is None:
            result["fallback"] = True
            result["fallback_reason"] = f"무료 프로바이더 실패: {free_error}"
            return result

    return {
        "output": "", "agent": "트리아지", "agent_type": "triage",
        "provider": "", "error": free_error or "사용 가능한 프로바이더가 없습니다.",
    }


async def _run_triage_with_model(task: str, provider: str) -> dict:
    """단일 프로바이더로 트리아지 에이전트를 실행한다."""
    try:
        model = _create_model(provider)
        triage = _build_triage(model)
        result = await Runner.run(triage, task)

        final_agent_name = result.last_agent.name if result.last_agent else "트리아지"
        agent_type = "triage"
        for at, defn in SPECIALIST_DEFS.items():
            if defn["name"] == final_agent_name:
                agent_type = at
                break

        return {
            "output": result.final_output,
            "agent": final_agent_name,
            "agent_type": agent_type,
            "provider": provider,
            "error": None,
        }
    except Exception as e:
        logger.error("트리아지 실행 실패 [%s]: %s", provider, e)
        return {
            "output": "", "agent": "트리아지", "agent_type": "triage",
            "provider": provider, "error": str(e),
        }


# ═══════════════════════════════════════════════════════
# CLI 테스트
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio

    print("=" * 50)
    print("  JH Agent Factory — SDK 전문 에이전트 시스템")
    print("=" * 50)

    print("\n📋 전문 에이전트 목록:")
    for spec in list_specialists():
        print(f"  {spec['icon']} {spec['name']} ({spec['type']})")
        print(f"     {spec['description']}")
        print(f"     도구: {', '.join(spec['tools'])}")
        print()

    if SDK_AVAILABLE:
        print("✅ OpenAI Agents SDK 로드 완료")
    else:
        print("❌ OpenAI Agents SDK가 설치되지 않았습니다.")
        print("   설치: pip install openai-agents")
