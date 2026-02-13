# JH Agent Factory

멀티 에이전트 생성·관리 시스템 (FastAPI + React Dashboard)

## Quick Start (새 PC, 1회 실행)

```bash
git clone https://github.com/jaeha81/agent_factory.git
cd agent_factory
```

### Windows (CMD)
```
scripts\run_api.bat
```

### macOS / Linux / Git Bash
```bash
chmod +x scripts/run_api.sh   # 최초 1회
./scripts/run_api.sh
```

스크립트가 자동으로 `.venv` 생성 → 의존성 설치 → 서버 실행까지 처리합니다.

서버가 뜨면:
- Swagger UI: http://localhost:8000/docs
- 에이전트 목록: http://localhost:8000/api/agents
- 시스템 상태: http://localhost:8000/api/system/status

## Stop

터미널에서 `Ctrl+C`

## Save & Push (원클릭 저장)

작업 내용을 커밋하고 원격에 푸시합니다.

### Windows (CMD)
```
scripts\save_and_push.bat "커밋 메시지"
scripts\save_and_push.bat                  :: 메시지 생략 시 WIP: <timestamp>
```

### macOS / Linux / Git Bash
```bash
./scripts/save_and_push.sh "커밋 메시지"
./scripts/save_and_push.sh                 # 메시지 생략 시 WIP: <timestamp>
```

## 수동 실행

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
python api_server.py
```

## 유용한 Git 명령

```bash
git status -sb           # 현재 브랜치/원격 상태
git tag --list           # 태그(체크포인트) 목록
git log --oneline -5     # 최근 커밋 5개
```

## API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/agents` | 에이전트 목록 |
| GET | `/api/agents/{id}` | 에이전트 상세 |
| POST | `/api/agents/create` | 에이전트 생성 |
| GET | `/api/skills` | 스킬 목록 |
| POST | `/api/skills/equip` | 스킬 장착 |
| POST | `/api/skills/unequip` | 스킬 해제 |
| GET | `/api/system/status` | 시스템 상태 |

## 프로젝트 구조

```
agent_factory/
├── api_server.py              # FastAPI 서버 (port 8000)
├── run.py                     # 부트스트랩 러너
├── requirements.txt           # Python 의존성
├── scripts/
│   ├── run_api.bat / .sh      # 원클릭 서버 실행
│   ├── save_and_push.bat / .sh # 원클릭 저장+푸시
│   └── test_executor.py       # Executor 테스트 시나리오
├── core/                      # 코어 모듈
│   ├── agent_creator.py       # 에이전트 생성 (기본 스킬 자동 주입)
│   ├── skills_manager.py      # 스킬 관리
│   ├── prompt_injector.py     # 프롬프트 주입
│   ├── executor.py            # 로컬 실행기 (safe_run, file I/O, git_ops)
│   └── logger.py              # 통합 JSONL 로거
├── agents/                    # 생성된 에이전트 데이터
│   └── _base/                 # 기본 에이전트 템플릿 (자동 주입)
│       ├── base_instructions.md   # 보안/정직/실행가능성/Git 규칙
│       ├── base_skills.json       # 기본 스킬팩 (filesystem, terminal, git, coding)
│       └── memory_policy.md       # 요약 메모리 규칙
├── skills_library/            # 스킬 저장소
│   ├── schema.skill.json      # 스킬 JSON 표준 스키마
│   ├── core/                  # 기본 스킬팩 (모든 에이전트에 자동 장착)
│   │   ├── filesystem.skill.json  # 파일 읽기/쓰기/검색
│   │   ├── terminal.skill.json    # 안전한 명령 실행 (allowlist)
│   │   ├── git.skill.json         # Git 작업 + 민감정보 스캔
│   │   └── coding.skill.json      # 코드 작성/리팩토링/디버깅
│   └── skills/                # 커스텀 추가 스킬
├── prompts/                   # 런타임 프롬프트 템플릿
├── logs/                      # 팩토리 실행 로그 (JSONL 형식)
└── docs/                      # 문서 (git_policy.md 포함)
```

## 핵심 아키텍처

| 컴포넌트 | 위치 | 역할 |
|----------|------|------|
| **스킬 저장소** | `skills_library/` | 표준 스키마 기반 스킬 JSON 보관. `core/`에 기본 4종, `skills/`에 커스텀 |
| **기본 템플릿** | `agents/_base/` | 모든 에이전트 생성 시 자동 주입되는 지침·스킬·메모리 정책 |
| **실행기** | `core/executor.py` | allowlist 기반 명령 실행, 파일 I/O, Git 작업, 민감정보 스캔 |
| **JSONL 로거** | `core/logger.py` | 모든 실행 이벤트를 `logs/*.jsonl`에 구조화 기록 |
| **스킬 매니저** | `core/skills_manager.py` | 에이전트별 스킬 장착/해제/조회 |
| **프롬프트 주입** | `core/prompt_injector.py` | 템플릿 변수 치환 → system_prompt.md 생성 |
| **에이전트 생성** | `core/agent_creator.py` | ID 발급 → 폴더 생성 → 기본 스킬 주입 → 프롬프트 생성 → 등록 |
| **Git 정책** | `docs/git_policy.md` | 브랜치 전략, 커밋 규칙, 민감정보 스캔, 금지 명령 목록 |

---

## 원클릭 실행 (Windows)

### 기본 실행
```
scripts\run_api.bat
```

### 추천: 종료 시 자동 저장+푸시
```
scripts\run_api_auto_save.bat
```
서버 실행 → `Ctrl+C`로 종료 → 커밋 메시지 입력(Enter=자동) → `git add/commit/push` 자동 수행

## 바탕화면 바로가기 설치 (Windows)

아래 명령 1회 실행하면 바탕화면에 아이콘 2개가 생성됩니다:
```
scripts\install_shortcuts_windows.bat
```

| 바로가기 | 동작 |
|----------|------|
| **AgentFactory - Run(API+AutoSave)** | 서버 실행 + 종료 시 자동 저장 |
| **AgentFactory - Save+Push** | 즉시 저장+푸시 |

## 종료

- 서버 종료: 터미널에서 `Ctrl+C`
- 자동 저장: `run_api_auto_save.bat` 사용 시에만 종료 후 자동 커밋+푸시
- 수동 저장: `scripts\save_and_push.bat "메시지"` (메시지 생략 시 자동 타임스탬프)

## 커스텀 스킬 추가

`skills_library/skills/` 디렉토리에 JSON 파일을 추가하면 API 서버 시작 시 자동으로 로드됩니다.

```
skills_library/skills/<skill_id>.skill.json
```

필수 필드: `skill_id`, `name`, `description`, `prompt`

```json
{
  "skill_id": "my_skill",
  "name": "My Skill",
  "description": "What this skill does",
  "prompt": "System prompt for the skill"
}
```

GitHub에 커밋하면 다른 PC에서 clone/pull만으로 동일한 스킬을 사용할 수 있습니다.
자세한 스키마는 `skills_library/README.md` 참고.
