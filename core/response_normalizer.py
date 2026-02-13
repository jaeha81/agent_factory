"""
core/response_normalizer.py
JH Agent Factory — 응답 정규화기 (Response Normalizer)

모든 LLM 응답을 공통 JSON 스키마로 변환/검증한다.
모델이 바뀌어도 출력 포맷이 흔들리지 않도록 강제한다.

표준 스키마:
{
  "title": str,
  "summary": str,
  "steps": [{"step": int, "action": str, "details": str}],
  "artifacts": [{"type": str, "path": str}],
  "risks": [{"risk": str, "mitigation": str}],
  "next": [str]
}
"""

import json
import re
import logging
from typing import Optional

logger = logging.getLogger("response_normalizer")

# ── 표준 응답 스키마 ──────────────────────────────────
RESPONSE_SCHEMA = {
    "title": str,
    "summary": str,
    "steps": list,      # [{"step": int, "action": str, "details": str}]
    "artifacts": list,   # [{"type": str, "path": str}]
    "risks": list,       # [{"risk": str, "mitigation": str}]
    "next": list,        # [str]
}

EMPTY_RESPONSE = {
    "title": "",
    "summary": "",
    "steps": [],
    "artifacts": [],
    "risks": [],
    "next": [],
}


def _extract_json(text: str) -> Optional[dict]:
    """
    텍스트에서 JSON 블록을 추출 시도.
    1) 전체 텍스트가 JSON인 경우
    2) ```json ... ``` 코드 블록 안의 JSON
    3) { ... } 패턴 추출
    """
    # 1) 전체 텍스트가 JSON
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass

    # 2) ```json 코드 블록
    match = re.search(r'```(?:json)?\s*\n?(\{.*?\})\s*\n?```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 3) 첫 번째 { ... } 패턴
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def _coerce_to_schema(data: dict) -> dict:
    """
    추출된 JSON을 표준 스키마에 맞게 강제 변환.
    누락된 필드는 기본값으로 채움.
    """
    result = dict(EMPTY_RESPONSE)

    # title
    result["title"] = str(data.get("title", data.get("제목", "")))

    # summary
    result["summary"] = str(data.get("summary", data.get("요약",
                          data.get("description", data.get("설명", "")))))

    # steps
    raw_steps = data.get("steps", data.get("단계", []))
    if isinstance(raw_steps, list):
        steps = []
        for i, s in enumerate(raw_steps):
            if isinstance(s, dict):
                steps.append({
                    "step": s.get("step", i + 1),
                    "action": str(s.get("action", s.get("name", ""))),
                    "details": str(s.get("details", s.get("description", s.get("detail", "")))),
                })
            elif isinstance(s, str):
                steps.append({"step": i + 1, "action": s, "details": ""})
        result["steps"] = steps

    # artifacts
    raw_arts = data.get("artifacts", data.get("산출물", []))
    if isinstance(raw_arts, list):
        arts = []
        for a in raw_arts:
            if isinstance(a, dict):
                arts.append({
                    "type": str(a.get("type", a.get("유형", "file"))),
                    "path": str(a.get("path", a.get("경로", ""))),
                })
            elif isinstance(a, str):
                arts.append({"type": "file", "path": a})
        result["artifacts"] = arts

    # risks
    raw_risks = data.get("risks", data.get("위험", []))
    if isinstance(raw_risks, list):
        risks = []
        for r in raw_risks:
            if isinstance(r, dict):
                risks.append({
                    "risk": str(r.get("risk", r.get("위험", ""))),
                    "mitigation": str(r.get("mitigation", r.get("대응", r.get("완화", "")))),
                })
            elif isinstance(r, str):
                risks.append({"risk": r, "mitigation": ""})
        result["risks"] = risks

    # next
    raw_next = data.get("next", data.get("다음", []))
    if isinstance(raw_next, list):
        result["next"] = [str(n) for n in raw_next]
    elif isinstance(raw_next, str):
        result["next"] = [raw_next]

    return result


def validate_schema(data: dict) -> list:
    """
    데이터가 표준 스키마를 준수하는지 검증.
    Returns: 위반 사항 리스트. 빈 리스트 = 유효.
    """
    violations = []

    for field, expected_type in RESPONSE_SCHEMA.items():
        if field not in data:
            violations.append(f"필드 누락: {field}")
        elif not isinstance(data[field], expected_type):
            violations.append(f"타입 불일치: {field} (기대: {expected_type.__name__}, 실제: {type(data[field]).__name__})")

    # steps 내부 구조 검증
    if isinstance(data.get("steps"), list):
        for i, s in enumerate(data["steps"]):
            if not isinstance(s, dict):
                violations.append(f"steps[{i}]: dict가 아님")
            elif "action" not in s:
                violations.append(f"steps[{i}]: action 필드 누락")

    return violations


def normalize(raw_text: str) -> dict:
    """
    LLM 응답 텍스트를 표준 JSON 스키마로 정규화.

    1) JSON 추출 시도
    2) 스키마에 맞게 강제 변환
    3) 실패 시 원문을 summary에 넣고 기본 스키마 반환

    Returns:
        표준 스키마 dict + {"_raw": str, "_valid": bool, "_violations": list}
    """
    # JSON 추출 시도
    extracted = _extract_json(raw_text)

    if extracted:
        # 스키마로 강제 변환
        normalized = _coerce_to_schema(extracted)
        violations = validate_schema(normalized)
        normalized["_raw"] = raw_text
        normalized["_valid"] = len(violations) == 0
        normalized["_violations"] = violations
        return normalized

    # JSON 추출 실패 — 원문을 summary로 래핑
    logger.info("JSON 추출 실패, 원문을 summary로 래핑")
    result = dict(EMPTY_RESPONSE)
    result["summary"] = raw_text.strip()
    result["title"] = raw_text.strip()[:80]
    result["_raw"] = raw_text
    result["_valid"] = False
    result["_violations"] = ["JSON 추출 실패: 원문이 JSON 형식이 아님"]
    return result


def get_schema_prompt_instruction() -> str:
    """LLM에게 주입할 JSON 스키마 강제 지시문."""
    return """반드시 아래 JSON 형식으로만 답하라. 다른 형식은 허용하지 않는다.

```json
{
  "title": "응답 제목",
  "summary": "핵심 요약 (1-3문장)",
  "steps": [
    {"step": 1, "action": "수행할 동작", "details": "상세 설명"}
  ],
  "artifacts": [
    {"type": "file|code|data", "path": "생성/수정 경로"}
  ],
  "risks": [
    {"risk": "위험 요소", "mitigation": "완화 방안"}
  ],
  "next": ["다음 추천 행동 1", "다음 추천 행동 2"]
}
```

규칙:
- 순수 JSON만 출력하라. JSON 앞뒤에 설명 텍스트를 넣지 마라.
- 빈 필드도 빈 배열([]) 또는 빈 문자열("")로 반드시 포함하라.
- 한국어 응답을 기본으로 하되, 코드/경로는 영문 그대로."""
