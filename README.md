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
│   └── save_and_push.bat / .sh # 원클릭 저장+푸시
├── core/                      # 코어 모듈
│   ├── agent_creator.py       # 에이전트 생성
│   ├── skills_manager.py      # 스킬 관리
│   ├── prompt_injector.py     # 프롬프트 주입
│   └── factory_config.yaml
├── agents/                    # 생성된 에이전트 데이터
├── prompts/                   # 런타임 프롬프트 템플릿
└── docs/                      # 문서
```
