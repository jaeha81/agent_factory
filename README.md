# JH Agent Factory

멀티 에이전트 생성·관리 시스템 (FastAPI + React Dashboard)

## Quick Start (새 PC 재현 3줄)

```bash
git clone https://github.com/jaeha81/agent_factory.git
cd agent_factory
./scripts/run_api.sh        # Git Bash / macOS / Linux
# 또는
scripts\run_api.bat          # Windows CMD
```

브라우저: **http://localhost:8000/docs**

## 수동 설치

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
python api_server.py
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
├── api_server.py          # FastAPI 서버 (port 8000)
├── requirements.txt       # Python 의존성
├── core/                  # 코어 모듈
│   ├── agent_creator.py   # 에이전트 생성
│   ├── skills_manager.py  # 스킬 관리
│   ├── prompt_injector.py # 프롬프트 주입
│   └── factory_config.yaml
├── agents/                # 생성된 에이전트 데이터
├── prompts/               # 런타임 프롬프트 템플릿
├── scripts/               # 실행·유틸 스크립트
└── docs/                  # 문서
```
