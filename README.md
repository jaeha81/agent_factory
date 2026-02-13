# JH Agent Factory

멀티 에이전트 생성·관리 시스템 (FastAPI + React Dashboard)

## Quick Start

```bash
git clone https://github.com/jaeha81/agent_factory.git
cd agent_factory
python run.py --doctor   # 환경 점검 (venv 생성 + 의존성 설치 + import 테스트)
python run.py            # API 서버 실행
# http://127.0.0.1:8000/docs
```

### 원클릭 런처

```bash
# Windows CMD
run_api.bat

# Git Bash / macOS / Linux
./run_api.sh
```

### run.py 옵션

| 옵션 | 설명 |
|------|------|
| `--doctor` | venv + 설치 + import 테스트 후 종료 |
| `--host 0.0.0.0` | 바인딩 호스트 (기본 127.0.0.1) |
| `--port 9000` | 포트 변경 (기본 8000) |
| `--reload` | 코드 변경 시 자동 재시작 (개발용) |
| `--no-install` | pip install 생략 |

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
├── run.py                 # 원커맨드 부트스트랩 러너
├── run_api.bat / .sh      # OS별 런처
├── api_server.py          # FastAPI 서버 (port 8000)
├── requirements.txt       # Python 의존성
├── core/                  # 코어 모듈
│   ├── agent_creator.py   # 에이전트 생성
│   ├── skills_manager.py  # 스킬 관리
│   ├── prompt_injector.py # 프롬프트 주입
│   └── factory_config.yaml
├── agents/                # 생성된 에이전트 데이터
├── prompts/               # 런타임 프롬프트 템플릿
├── scripts/               # 유틸 스크립트
└── docs/                  # 문서
```
