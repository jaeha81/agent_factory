"""
prompt_injector.py
런타임 프롬프트 템플릿을 로드하고, 플레이스홀더를 치환하여
agents/{AGENT_ID}/system_prompt.md 를 생성한다.

외부 라이브러리 의존: 없음 (표준 라이브러리만 사용)
Windows/Linux 호환
"""

import os

# 이 파일(core/) 기준 → 프로젝트 루트
_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_CORE_DIR)
_PROMPTS_DIR = os.path.join(_PROJECT_ROOT, "prompts")
_AGENTS_DIR = os.path.join(_PROJECT_ROOT, "agents")


def inject_and_save(
    agent_id: str,
    agent_name: str,
    agent_role: str,
    agent_level: int,
    is_master: bool,
    master_agent_id: str = "",
) -> str:
    """
    프롬프트 템플릿을 로드 → 변수 치환 → agents/{id}/system_prompt.md 저장

    Args:
        agent_id:       에이전트 고유 ID
        agent_name:     에이전트 이름
        agent_role:     역할 문자열
        agent_level:    레벨 숫자
        is_master:      마스터 여부
        master_agent_id: 마스터 에이전트 ID (워커 전용)

    Returns:
        저장된 파일 절대경로
    """
    # 1) 템플릿 선택
    if is_master:
        template_path = os.path.join(_PROMPTS_DIR, "master_runtime.md")
    else:
        template_path = os.path.join(_PROMPTS_DIR, "worker_runtime.md")

    if not os.path.isfile(template_path):
        raise FileNotFoundError(f"프롬프트 템플릿 없음: {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 2) 플레이스홀더 치환
    replacements = {
        "{AGENT_NAME}":      agent_name,
        "{AGENT_ROLE}":      agent_role,
        "{AGENT_ID}":        agent_id,
        "{AGENT_LEVEL}":     str(agent_level),
        "{MASTER_AGENT_ID}": master_agent_id,
    }
    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)

    # 3) 저장
    agent_dir = os.path.join(_AGENTS_DIR, agent_id)
    os.makedirs(agent_dir, exist_ok=True)
    output_path = os.path.join(agent_dir, "system_prompt.md")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path
