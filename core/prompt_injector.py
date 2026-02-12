# core/prompt_injector.py
# JH Agent Factory - Prompt Injector (Phase 1-② MVP)
# 역할:
# - prompts/master_runtime.md 또는 prompts/worker_runtime.md 로드
# - agents/{ID}/profile.json + agents/{ID}/config.yaml 로드
# - 변수 치환 후 agents/{ID}/system_prompt.md 생성

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml  # PyYAML
except ImportError as e:
    raise SystemExit(
        "PyYAML이 필요합니다. 아래를 실행하세요:\n\n"
        "  pip install pyyaml\n"
    ) from e


@dataclass
class InjectResult:
    agent_id: str
    is_master: bool
    template_path: str
    output_path: str
    equipped_skills: List[str]
    active_frameworks: List[str]


def _read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"JSON 파일을 찾을 수 없습니다: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        # config.yaml은 나중에 생성될 수도 있으니, 없으면 빈 dict로 허용
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _normalize_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    # "a,b,c" 같은 문자열도 받아줌
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return [str(value)]


def _serialize_list_for_prompt(items: List[str]) -> str:
    # 프롬프트에 넣기 좋은 형태로 직렬화
    if not items:
        return "[]"
    return json.dumps(items, ensure_ascii=False)


def inject_runtime_prompt(
    project_root: str | Path,
    agent_id: str,
    is_master: bool,
    *,
    # 템플릿 파일명을 바꾸고 싶으면 여기서 오버라이드
    master_template_rel: str = "prompts/master_runtime.md",
    worker_template_rel: str = "prompts/worker_runtime.md",
) -> InjectResult:
    """
    project_root: agent_factory/ 폴더 경로
    agent_id: agents/{AGENT_ID}/ 대상
    is_master: 마스터 템플릿(master_runtime.md) 사용 여부
    """

    root = Path(project_root).resolve()

    # 1) 에이전트 경로
    agent_dir = root / "agents" / agent_id
    profile_path = agent_dir / "profile.json"
    config_path = agent_dir / "config.yaml"
    output_path = agent_dir / "system_prompt.md"

    # 2) 템플릿 선택
    template_path = root / (master_template_rel if is_master else worker_template_rel)

    # 3) 데이터 로드
    template = _read_text(template_path)
    profile = _read_json(profile_path)
    config = _read_yaml(config_path)

    # 4) 값 추출 (없으면 profile 우선, 부족하면 안전한 기본값)
    agent_name = str(profile.get("name") or profile.get("agent_name") or "UnnamedAgent")
    agent_role = str(profile.get("role") or profile.get("agent_role") or ("master_controller" if is_master else "worker"))
    agent_level = str(profile.get("level") or profile.get("agent_level") or (5 if is_master else 1))

    master_agent_id = str(profile.get("master_id") or profile.get("master_agent_id") or "MASTER_UNSET")

    equipped_skills = _normalize_list(profile.get("equipped_skills") or profile.get("skills"))
    # config.yaml 안에 frameworks: ["x","y"] 구조를 권장
    active_frameworks = _normalize_list(config.get("frameworks") or config.get("active_frameworks"))

    # 5) 치환 변수 준비
    replacements: Dict[str, str] = {
        "{AGENT_NAME}": agent_name,
        "{AGENT_ROLE}": agent_role,
        "{AGENT_ID}": agent_id,
        "{AGENT_LEVEL}": str(agent_level),
        "{MASTER_AGENT_ID}": master_agent_id,
        "{EQUIPPED_SKILLS}": _serialize_list_for_prompt(equipped_skills),
        "{ACTIVE_FRAMEWORKS}": _serialize_list_for_prompt(active_frameworks),
    }

    # 6) 템플릿 치환
    rendered = template
    for k, v in replacements.items():
        rendered = rendered.replace(k, v)

    # 7) 저장
    _write_text(output_path, rendered)

    return InjectResult(
        agent_id=agent_id,
        is_master=is_master,
        template_path=str(template_path),
        output_path=str(output_path),
        equipped_skills=equipped_skills,
        active_frameworks=active_frameworks,
    )


def inject_and_save(
    agent_id: str,
    agent_name: str,
    agent_role: str,
    agent_level: int,
    is_master: bool,
    master_agent_id: str = "",
) -> str:
    """agent_creator.py에서 호출하는 래퍼.
    profile.json·config.yaml이 이미 디스크에 존재하는 상태에서 호출됨.
    inject_runtime_prompt를 위임 호출하고 output_path(str)를 반환.
    """
    project_root = Path(__file__).resolve().parent.parent
    result = inject_runtime_prompt(
        project_root=project_root,
        agent_id=agent_id,
        is_master=is_master,
    )
    return result.output_path


# ---- (선택) 로컬 테스트용 실행 진입점 ----
if __name__ == "__main__":
    # 예:
    # python core/prompt_injector.py agent_factory CHUNSIK_0001 true
    import sys

    if len(sys.argv) < 4:
        print(
            "사용법:\n"
            "  python core/prompt_injector.py <project_root> <agent_id> <is_master>\n\n"
            "예:\n"
            "  python core/prompt_injector.py . CHUNSIK_0001 true\n"
        )
        raise SystemExit(1)

    project_root = sys.argv[1]
    agent_id = sys.argv[2]
    is_master = sys.argv[3].lower() in ("1", "true", "yes", "y")

    res = inject_runtime_prompt(project_root, agent_id, is_master)
    print("[OK] system_prompt 생성 완료")
    print(" - template:", res.template_path)
    print(" - output  :", res.output_path)
    print(" - skills  :", res.equipped_skills)
    print(" - frameworks:", res.active_frameworks)
