"""
test_llm_router.py
LLM 라우터 + Response Normalizer + 설정 통합 테스트.

실행:
  cd agent_factory
  python scripts/test_llm_router.py
"""

import json
import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _PROJECT_ROOT)

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    status = "PASS" if condition else "FAIL"
    if condition:
        PASS += 1
    else:
        FAIL += 1
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not condition else ""))


def test_config():
    """1. 설정 파일 로드 테스트"""
    print("\n=== 1. config/llm_routing.yaml 테스트 ===")

    config_path = os.path.join(_PROJECT_ROOT, "config", "llm_routing.yaml")
    check("config 파일 존재", os.path.isfile(config_path))

    try:
        import yaml
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)
        check("YAML 파싱 성공", cfg is not None)
        check("providers 섹션 존재", "providers" in cfg)
        check("routing_chain 섹션 존재", "routing_chain" in cfg)
        check("failover 섹션 존재", "failover" in cfg)
        check("escalation 섹션 존재", "escalation" in cfg)
        check("budget 섹션 존재", "budget" in cfg)

        # task_class 4종 확인
        chains = cfg.get("routing_chain", {})
        for tc in ["light", "general", "coding", "high_precision"]:
            check(f"routing_chain.{tc} 정의", tc in chains)

        # 프로바이더 티어 확인
        provs = cfg.get("providers", {})
        tiers = set(p.get("tier", "") for p in provs.values())
        check("free 티어 존재", "free" in tiers)
        check("low_cost 티어 존재", "low_cost" in tiers)
        check("premium 티어 존재", "premium" in tiers)

    except ImportError:
        check("PyYAML 설치 확인", False, "pip install pyyaml 필요")


def test_response_normalizer():
    """2. Response Normalizer 테스트"""
    print("\n=== 2. Response Normalizer 테스트 ===")

    from core.response_normalizer import normalize, validate_schema, get_schema_prompt_instruction

    # 2.1 정상 JSON 정규화
    valid_json = json.dumps({
        "title": "테스트",
        "summary": "테스트 요약",
        "steps": [{"step": 1, "action": "실행", "details": "상세"}],
        "artifacts": [],
        "risks": [],
        "next": ["다음 단계"]
    })
    result = normalize(valid_json)
    check("정상 JSON 정규화", result["_valid"] is True)
    check("title 추출", result["title"] == "테스트")

    # 2.2 코드 블록 안 JSON
    code_block = '```json\n{"title":"코드블록","summary":"테스트","steps":[],"artifacts":[],"risks":[],"next":[]}\n```'
    result = normalize(code_block)
    check("코드블록 JSON 추출", result["title"] == "코드블록")

    # 2.3 비JSON 텍스트 → summary 래핑
    plain_text = "이것은 그냥 텍스트입니다."
    result = normalize(plain_text)
    check("비JSON 텍스트 래핑", result["_valid"] is False)
    check("원문이 summary에 포함", plain_text in result["summary"])

    # 2.4 부분적 JSON (필드 누락)
    partial = json.dumps({"title": "부분", "summary": "없음"})
    result = normalize(partial)
    check("부분 JSON에 기본값 채움", isinstance(result["steps"], list))

    # 2.5 한국어 키 지원
    korean_json = json.dumps({"제목": "한글키", "요약": "테스트", "단계": [{"action": "실행"}]})
    result = normalize(korean_json)
    check("한국어 키 매핑(제목→title)", result["title"] == "한글키")

    # 2.6 스키마 검증
    valid_data = {
        "title": "t", "summary": "s", "steps": [{"step": 1, "action": "a", "details": "d"}],
        "artifacts": [], "risks": [], "next": []
    }
    violations = validate_schema(valid_data)
    check("유효 데이터 스키마 통과", len(violations) == 0)

    # 2.7 스키마 프롬프트 생성
    instruction = get_schema_prompt_instruction()
    check("스키마 지시문 생성", "title" in instruction and "steps" in instruction)


def test_llm_router_module():
    """3. LLM 라우터 모듈 테스트 (네트워크 호출 없이)"""
    print("\n=== 3. LLM 라우터 모듈 테스트 ===")

    # import 테스트
    try:
        from core.llm_router import (
            get_router_status, get_budget_status,
            get_routing_chain, _check_budget,
            _build_provider_registry, reload_config,
        )
        check("llm_router import 성공", True)
    except ImportError as e:
        check("llm_router import 성공", False, str(e))
        return

    # 3.1 프로바이더 레지스트리
    registry = _build_provider_registry()
    check("프로바이더 레지스트리 구축", len(registry) > 0)
    check("groq 프로바이더 존재", "groq" in registry)

    # 3.2 라우팅 체인 조회
    chain = get_routing_chain("general")
    check("general 라우팅 체인 비어있지 않음", len(chain) > 0)
    chain_coding = get_routing_chain("coding")
    check("coding 라우팅 체인 비어있지 않음", len(chain_coding) > 0)

    # 3.3 예산 검사
    ok, reason = _check_budget("free")
    check("무료 티어 예산 항상 통과", ok is True)

    # 3.4 라우터 상태
    status = get_router_status()
    check("라우터 상태 조회", "providers" in status and "budget" in status)

    # 3.5 예산 상태
    budget = get_budget_status()
    check("예산 상태 조회", "daily_spent" in budget and "daily_limit" in budget)

    # 3.6 설정 리로드
    reload_config()
    check("설정 핫 리로드 성공", True)


def test_prompt_template():
    """4. LLM 시스템 프롬프트 테스트"""
    print("\n=== 4. prompts/llm_system.md 테스트 ===")

    prompt_path = os.path.join(_PROJECT_ROOT, "prompts", "llm_system.md")
    check("llm_system.md 존재", os.path.isfile(prompt_path))

    if os.path.isfile(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            content = f.read()
        check("JSON 스키마 포함", '"title"' in content and '"steps"' in content)
        check("task_class 설명 포함", "light" in content and "coding" in content)
        check("불변 규칙 포함", "순수 JSON" in content)


def test_report_usage():
    """5. 사용량 보고서 모듈 테스트"""
    print("\n=== 5. scripts/report_usage.py 테스트 ===")

    report_path = os.path.join(_PROJECT_ROOT, "scripts", "report_usage.py")
    check("report_usage.py 존재", os.path.isfile(report_path))

    # 모듈 함수 테스트
    sys.path.insert(0, os.path.join(_PROJECT_ROOT, "scripts"))
    from report_usage import aggregate

    # 빈 데이터 집계
    result = aggregate([])
    check("빈 데이터 집계", result["total"] == 0)

    # 샘플 데이터 집계
    sample_entries = [
        {"provider": "groq", "model": "llama-3.1-8b", "tier": "free",
         "task_class": "general", "success": True, "latency_ms": 500,
         "failover_count": 0, "escalated": False, "timestamp": "2026-02-13T10:00:00Z"},
        {"provider": "gemini_flash", "model": "gemini-2.0-flash", "tier": "free",
         "task_class": "coding", "success": True, "latency_ms": 800,
         "failover_count": 1, "escalated": False, "timestamp": "2026-02-13T11:00:00Z"},
        {"provider": "", "model": "", "tier": "",
         "task_class": "general", "success": False, "latency_ms": 3000,
         "failover_count": 4, "escalated": True, "timestamp": "2026-02-13T12:00:00Z"},
    ]
    result = aggregate(sample_entries)
    check("샘플 집계 총 호출수", result["total"] == 3)
    check("샘플 집계 성공수", result["success"] == 2)
    check("샘플 집계 실패수", result["fail"] == 1)
    check("샘플 집계 승격 횟수", result["total_escalations"] == 1)


def test_env_example():
    """6. .env.example 확인"""
    print("\n=== 6. .env.example 확인 ===")

    env_path = os.path.join(_PROJECT_ROOT, ".env.example")
    check(".env.example 존재", os.path.isfile(env_path))

    if os.path.isfile(env_path):
        with open(env_path, "r") as f:
            content = f.read()
        check("OPENAI_API_KEY 포함", "OPENAI_API_KEY" in content)
        check("ANTHROPIC_API_KEY 포함", "ANTHROPIC_API_KEY" in content)
        check("GROQ_API_KEY 포함", "GROQ_API_KEY" in content)


def main():
    print("=" * 60)
    print(" JH Agent Factory — LLM 라우터 통합 테스트")
    print("=" * 60)

    test_config()
    test_response_normalizer()
    test_llm_router_module()
    test_prompt_template()
    test_report_usage()
    test_env_example()

    print("\n" + "=" * 60)
    print(f" 결과: {PASS} passed, {FAIL} failed (total {PASS + FAIL})")
    print("=" * 60)

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
