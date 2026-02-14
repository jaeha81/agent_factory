# CLAUDE.md — JH Agent Factory v2.2

## 프로젝트 개요

다중 에이전트 공장형 시스템. 에이전트를 "생산"하고, 스킬을 장착하며, LLM 라우팅으로 자동 운영한다.

- **언어:** Python 3.11 + FastAPI
- **프론트엔드:** React 18 (CDN + Babel in-browser, Node.js 빌드 없음)
- **아키텍처:** 파일 기반 (SQLite 없음), JSONL 로그, YAML 설정

## 빠른 시작

```bash
# 자동 설정 + 실행
python run.py

# 수동 실행
pip install -r requirements.txt
python api_server.py
# → http://localhost:8000 (대시보드)
# → http://localhost:8000/docs (Swagger)
# → http://localhost:8000/mobile (모바일 QR)
```

## 테스트

```bash
python scripts/test_executor.py      # Executor 31개 테스트
python scripts/test_llm_router.py    # LLM 라우터 테스트
```

정식 pytest 프레임워크 없음. 스크립트 기반 통합 테스트.

## 핵심 디렉토리 구조

```
core/               # 엔진 모듈
  agent_creator.py   - 에이전트 생성 (ID 발급, 폴더 생성, 레지스트리 등록)
  llm_router.py      - LLM 라우팅 (free→low_cost→premium 자동 에스컬레이션)
  executor.py        - 안전 실행 (allowlist 기반 명령어, 시크릿 스캐닝)
  skills_manager.py  - 스킬 장착/해제
  ai_router.py       - 레거시 LLM 라우터 (llm_router가 래핑)
  response_normalizer.py - LLM 응답 JSON 정규화
  prompt_injector.py - 런타임 프롬프트 변수 치환
  connection_manager.py - 에이전트 간 통신
  state_machine.py   - 상태 전이 (online/dormant/suspended/training/error)
  command_engine.py  - 명령 파싱/실행
  agent_replicator.py - 에이전트 복제
  logger.py          - JSONL 이벤트 로깅

agents/              # 에이전트 홈 디렉토리
  _base/             - 모든 에이전트에 자동 주입되는 기본 템플릿
  A0001/             - 개별 에이전트 (profile.json, system_prompt.md, skills/, logs/)

skills_library/      # 스킬 저장소
  core/              - 필수 4개: filesystem, terminal, git, coding
  skills/            - 커스텀 스킬
  schema.skill.json  - 스킬 JSON 스키마

config/              # 설정
  llm_routing.yaml   - 프로바이더, 라우팅 체인, 페일오버, 예산

prompts/             # 프롬프트 템플릿
  master_runtime.md  - 마스터 에이전트 시스템 프롬프트
  worker_runtime.md  - 워커 에이전트 시스템 프롬프트

static/index.html    # 대시보드 (React SPA, 모바일 반응형)
api_server.py        # FastAPI 서버 진입점 (port 8000)
```

## 코딩 컨벤션

- 주석과 문서는 한국어
- 린터/포매터 설정 없음 (자유 스타일)
- 기존 패턴 유지: 인라인 스타일 React, 함수형 컴포넌트
- 프론트엔드 수정 시 `static/index.html` 단일 파일 내 JSX 편집
- 새 파일 생성보다 기존 파일 편집 우선

## Git 규칙

```
커밋 형식: <type>: <subject>
타입: feat, fix, refactor, docs, test, chore
```

- `main`/`master` 직접 푸시 금지 → PR 필수
- `claude/*` 브랜치에서 작업 후 PR
- 시크릿 스캐닝: api_key=, sk-*, ghp_*, -----BEGIN PRIVATE KEY 포함 커밋 차단
- 금지 명령: `git push --force`, `git reset --hard`, `git clean -fd`, `git branch -D main`

## 주요 아키텍처 패턴

### 에이전트 생명주기
1. `POST /api/agents/create` → agent_creator가 ID 발급, 폴더 생성
2. `_base/` 템플릿 자동 주입 (base_instructions.md, 코어 스킬 4개)
3. 스킬 장착/해제, 레벨업 심사, 상태 전이
4. 마스터(Lv.5) → 워커 관리, 명령 전파

### LLM 라우팅
- **config/llm_routing.yaml** 기반 프로바이더 관리
- 무료(Groq, Gemini Flash, Together, OpenRouter) → 저가(Gemini Pro) → 프리미엄(GPT-4o, Claude)
- task_class별 라우팅 체인: light, general, coding, high_precision
- 실패 시 자동 페일오버, 스키마 불일치 2회 시 에스컬레이션
- 예산 가드: 일 $1 / 월 $20

### 안전 실행 (executor.py)
- ALLOWED_COMMANDS 화이트리스트 기반
- BLOCKED_PATTERNS로 위험 명령 차단 (rm -rf, format 등)
- 파일 I/O는 PROJECT_ROOT 내부만 허용
- git commit 전 시크릿 자동 스캐닝

## 환경 변수 (.env)

```bash
GROQ_API_KEY=        # 무료 티어
GEMINI_API_KEY=      # 무료/저가 티어
TOGETHER_API_KEY=    # 무료 티어
OPENROUTER_API_KEY=  # 무료 티어
OPENAI_API_KEY=      # 프리미엄 (선택)
ANTHROPIC_API_KEY=   # 프리미엄 (선택)
```

## 의존성

```
fastapi, uvicorn[standard], pyyaml, httpx>=0.25.0, python-dotenv>=1.0.0
```

## 주의사항

- 프론트엔드에 빌드 스텝 없음. `static/index.html` 하나에 모든 React 코드 존재
- DB 없음. `agents/` 폴더 구조 + `core/registry.json`이 상태 저장소
- 로그는 `logs/` 디렉토리에 JSONL 형식으로 append-only
- CHUNSIK Protocol v1.0-runtime이 시스템 조율 규약
