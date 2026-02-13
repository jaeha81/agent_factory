# Agent Factory v2.0 업그레이드 지침서
# Claude Code 전용 — 기존 파일 절대 삭제 금지

---

## 🚨 절대 규칙
- agents/A0001/ (춘식이) 절대 건드리지 않기
- core/prompt_injector.py 건드리지 않기
- core/skills_manager.py 건드리지 않기
- core/factory_config.yaml 건드리지 않기
- prompts/ 폴더 건드리지 않기
- scripts/ 폴더 건드리지 않기
- docs/, dosc/ 폴더 건드리지 않기
- core/registry.json 데이터 보존 (구조 변경 금지)

---

## 1. [신규] core/ai_router.py

무료 AI API 4개를 순차 폴백으로 연결하는 라우터.
세션별 슬라이딩 윈도우 컨텍스트 관리 포함.

### 핵심 설계:
- 프로바이더 우선순위: Groq → Gemini → Together → OpenRouter
- 각 프로바이더 API 키는 .env에서 로드 (GROQ_API_KEY, GEMINI_API_KEY, TOGETHER_API_KEY, OPENROUTER_API_KEY)
- 프로바이더 장애 시 60초 쿨다운, 자동 다음 프로바이더 전환
- httpx 있으면 async 사용, 없으면 urllib.request 동기 폴백
- 세션 관리: MAX_HISTORY=20, 초과 시 앞부분 텍스트 요약으로 압축

### 주요 함수:
```python
async def chat(session_id: str, user_message: str, system_prompt: str) -> dict:
    # Returns: {"reply": str, "provider": str, "model": str, "error": str|None}

def get_session(session_id: str) -> dict
def add_message(session_id: str, role: str, content: str)
def get_chat_messages(session_id: str, system_prompt: str) -> list[dict]
def clear_session(session_id: str)
def get_router_status() -> dict
```

### 프로바이더 설정:
```python
PROVIDERS = [
    {
        "name": "groq",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_env": "GROQ_API_KEY",
        "model": "llama-3.1-8b-instant",
        "max_tokens": 2048,
        "format": "openai",
    },
    {
        "name": "gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "key_env": "GEMINI_API_KEY",
        "model": "gemini-2.0-flash",
        "max_tokens": 2048,
        "format": "gemini",
    },
    {
        "name": "together",
        "url": "https://api.together.xyz/v1/chat/completions",
        "key_env": "TOGETHER_API_KEY",
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
        "max_tokens": 2048,
        "format": "openai",
    },
    {
        "name": "openrouter",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key_env": "OPENROUTER_API_KEY",
        "model": "meta-llama/llama-3.1-8b-instruct:free",
        "max_tokens": 2048,
        "format": "openai",
    },
]
```

### Gemini 호출 형식 (openai와 다름):
- system 메시지 → systemInstruction.parts[0].text
- user → contents[].role="user"
- assistant → contents[].role="model"
- URL: {base_url}?key={api_key}

---

## 2. [병합] core/agent_creator.py

기존 코드 100% 보존. 아래 2개 함수가 없으면 추가:

```python
def _load_registry() -> dict:
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {"factory": "JH Agent Factory", "agents": [], "updated": _now()}

def _save_registry(reg: dict):
    reg["updated"] = _now()
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(
        json.dumps(reg, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
```

api_server.py에서 `from core.agent_creator import _load_registry, _save_registry` 하므로 반드시 필요.

---

## 3. [업그레이드] api_server.py

기존 엔드포인트 유지 + 아래 추가:

### 새 엔드포인트:
```
POST   /api/chat                 → 춘식이 채팅
GET    /api/chat/history/{sid}   → 채팅 히스토리  
DELETE /api/chat/{sid}           → 세션 초기화
POST   /api/agents/{id}/skills   → 스킬 장착 (body: {skill_id: str})
DELETE /api/agents/{id}/skills/{skill_id} → 스킬 해제
POST   /api/agents/{id}/levelup  → 레벨업 (body: {force: bool})
DELETE /api/agents/{id}          → 에이전트 삭제 (마스터는 삭제 불가)
GET    /api/skills/catalog       → skills_library/catalog.json 반환
GET    /api/router/status        → AI 라우터 상태
```

### 춘식이 채팅 로직:
1. agents/A0001/system_prompt.md 를 system prompt로 로드
2. ai_router.chat(session_id, user_message, system_prompt) 호출
3. 결과 반환: {reply, provider, model, error}

### 레벨업 조건:
```python
LEVEL_REQUIREMENTS = {
    1: {"skills": 1, "tasks": 1},
    2: {"skills": 3, "tasks": 10},
    3: {"skills": 3, "tasks": 50, "max_error_rate": 0.10},
    5: {"skills": 5, "tasks": 200},
    7: {"skills": 5, "tasks": 500, "max_error_rate": 0.05},
}
```
force=True면 조건 무시하고 +1 레벨업.

### 에이전트 삭제:
- role=="master_controller" 이면 400 에러 반환 (마스터 삭제 불가)
- 폴더 삭제 + registry.json에서 제거

---

## 4. [업그레이드] static/index.html

기존 디자인 톤 유지 (DM Mono, Syne, 다크 테마, 산업-미래주의):
- --bg-0: #0a0a0c, --accent: #ff6b2b

### 레이아웃:
```
[HEADER: 로고 + AI상태 + 에이전트수]
[SIDEBAR 280px] [MAIN: 채팅] [PANEL 320px: 상세]
```

### 사이드바:
- 에이전트 목록 (카드형, 마스터는 좌측 accent 보더)
- "+ 생산" 버튼 → 모달 (이름 input + 역할 select)

### 메인 (채팅):
- 춘식이 채팅 메시지 영역 (user=우측, assistant=좌측)
- 하단 입력창 + 전송 버튼
- Enter 전송, Shift+Enter 줄바꿈
- 로딩 시 "춘식이 생각 중..." 애니메이션
- 프로바이더 태그 표시 (via groq · llama-3.1-8b-instant)

### 우측 패널:
- 선택한 에이전트의 ID, 역할, 레벨
- 능력치 (INT/MEM/SPD/REL) 그리드
- 장착 스킬 목록 (태그형, X 클릭 해제)
- "+ 스킬 장착" → catalog.json에서 선택
- "레벨업 심사" 버튼 (자동 판정)
- "강제↑" 버튼 (소유자 권한)
- "에이전트 삭제" 버튼 (마스터 제외)

---

## 5. [신규] .env.example

```
GROQ_API_KEY=
GEMINI_API_KEY=
TOGETHER_API_KEY=
OPENROUTER_API_KEY=
```

---

## 6. requirements.txt 에 추가

```
httpx>=0.25.0
python-dotenv>=1.0.0
```

---

## 7. 작업 후 실행

```powershell
pip install httpx python-dotenv
python -m uvicorn api_server:app --reload --port 8000
```

브라우저: http://localhost:8000
