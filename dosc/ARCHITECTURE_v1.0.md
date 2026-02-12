# ═══════════════════════════════════════════════════════════
# JH AGENT FACTORY — 3단계: 파일 구조 설계도
# 버전: v1.0
# 목적: 파일명·역할·연결 관계 정의 (구현 코드 없음)
# ═══════════════════════════════════════════════════════════


# ─────────────────────────────────────────────────────────
# 1. 전체 파일 트리
# ─────────────────────────────────────────────────────────

```
agent_factory/
│
├── core/                          # [핵심 엔진] 시스템의 두뇌
│   ├── __init__.py                # 코어 모듈 외부 노출 인터페이스
│   ├── agent_creator.py           # 에이전트 생산 라인
│   ├── agent_replicator.py        # 에이전트 복제 엔진
│   ├── skills_manager.py          # 스킬 장착/해제/카탈로그
│   ├── connection_manager.py      # 노드 연결 생성/해제/검증
│   ├── prompt_injector.py         # 런타임 프롬프트 변수 치환·주입
│   ├── state_machine.py           # 에이전트 상태 전환 엔진
│   ├── evolution_engine.py        # 레벨업 판정·Stats 갱신
│   ├── registry.json              # [자동생성] 전체 에이전트 중앙 등록부
│   └── factory_config.yaml        # 팩토리 전역 설정값
│
├── runtime/                       # [런타임] 에이전트 실행 환경
│   ├── agent_runner.py            # 에이전트 인스턴스 실행·관리
│   ├── message_bus.py             # 에이전트 간 메시지 라우팅
│   ├── task_queue.py              # 작업 큐 관리
│   └── resource_monitor.py        # 리소스 사용량 추적·경고
│
├── prompts/                       # [프롬프트] 시스템 프롬프트 원본
│   ├── master_runtime.md          # 마스터 에이전트 런타임 프롬프트
│   ├── worker_runtime.md          # 일반 에이전트 런타임 프롬프트
│   └── fragments/                 # 프롬프트 조립용 조각
│       ├── layer_0_immutable.md   # 불변 원칙 (공통)
│       ├── layer_2_decision.md    # 판단 프레임워크 (공통)
│       ├── layer_3_prohibitions.md # 금지 사항 (공통 8개)
│       ├── layer_3_worker_ban.md  # 워커 전용 BAN-09
│       ├── layer_4_comm.md        # 통신 프로토콜 (공통)
│       ├── layer_5_resources.md   # 자원 정책 (공통)
│       └── layer_6_evolution.md   # 진화 규칙 (공통)
│
├── skills_library/                # [스킬 저장소] 전체 스킬 카탈로그
│   ├── catalog.json               # 스킬 메타데이터 목록
│   └── definitions/               # 개별 스킬 정의 파일
│       ├── log_analyzer.skill.json
│       ├── api_reconnector.skill.json
│       ├── agent_builder.skill.json
│       ├── resource_monitor.skill.json
│       ├── data_processor.skill.json
│       ├── nlp_basic.skill.json
│       ├── scheduler.skill.json
│       └── memory_compressor.skill.json
│
├── agents/                        # [에이전트 홈] 각 에이전트의 독립 공간
│   └── {AGENT_ID}/               # 에이전트 1개 = 폴더 1개
│       ├── profile.json           # 탄생증명서 (ID, 이름, 역할, 레벨, 스탯)
│       ├── config.yaml            # 행동 설정 (메모리 정책, 학습 방식)
│       ├── system_prompt.md       # [자동생성] 주입 완료된 런타임 프롬프트
│       ├── memory/
│       │   ├── short_term/        # 단기 기억 (최근 대화/작업)
│       │   ├── long_term/         # 장기 기억 (검증된 지식)
│       │   └── compressed/        # 압축 아카이브
│       ├── skills/                # 장착된 스킬 복사본
│       ├── logs/                  # 행동 로그 (append-only)
│       │   ├── creation.log       # 생성 기록
│       │   ├── actions.log        # 행동 기록
│       │   ├── errors.log         # 오류 기록
│       │   └── skills.log         # 스킬 장착/해제 기록
│       ├── data/
│       │   ├── input/             # 작업 입력 데이터
│       │   └── output/            # 작업 출력 데이터
│       ├── training/              # 학습 관련 파일
│       └── connections/
│           └── manifest.json      # 연결된 에이전트 목록
│
├── dashboard/                     # [대시보드] 사용자 인터페이스
│   ├── app.jsx                    # 메인 React 앱
│   ├── api_client.js              # 코어 API 호출 레이어
│   └── index.html                 # 엔트리 포인트
│
├── api/                           # [API 서버] 대시보드 ↔ 코어 브릿지
│   ├── server.py                  # FastAPI 메인 서버
│   ├── routes/
│   │   ├── agents.py              # /api/agents 엔드포인트
│   │   ├── skills.py              # /api/skills 엔드포인트
│   │   ├── connections.py         # /api/connections 엔드포인트
│   │   ├── system.py              # /api/system 엔드포인트
│   │   └── messages.py            # /api/messages 엔드포인트
│   └── middleware/
│       ├── auth.py                # 소유자 인증
│       └── logger.py              # API 요청 로깅
│
├── docs/                          # [문서]
│   ├── CHUNSIK_PROTOCOL_v1.0.md   # 설계 원본 (헌법)
│   ├── ARCHITECTURE.md            # 이 파일 (구조 설계도)
│   └── CHANGELOG.md               # 변경 이력
│
└── tests/                         # [테스트]
    ├── test_agent_creator.py
    ├── test_replicator.py
    ├── test_prompt_injector.py
    ├── test_message_bus.py
    └── test_state_machine.py
```


# ─────────────────────────────────────────────────────────
# 2. 각 파일의 역할 정의
# ─────────────────────────────────────────────────────────

## core/ — 핵심 엔진

### agent_creator.py
  역할: 에이전트 생산의 진입점
  입력: 이름, 역할, 아이콘, 설명, is_master 플래그
  동작:
    1. 고유 ID 발급
    2. 폴더 구조 생성 (agents/{ID}/ 하위 전체)
    3. profile.json 작성
    4. config.yaml 작성
    5. prompt_injector 호출 → system_prompt.md 생성
    6. registry.json 등록
    7. 마스터인 경우 기본 스킬 4종 자동 장착
  출력: 생성 결과 객체
  호출: prompt_injector, skills_manager, registry.json

### agent_replicator.py
  역할: 검증 완료된 에이전트를 복제
  입력: 원본 agent_id
  동작:
    1. 원본 profile.json + config.yaml 복사
    2. 새 고유 ID 발급
    3. 새 폴더 구조 생성
    4. 스킬/설정 상속, 메모리/로그 초기화
    5. prompt_injector 호출 → 새 system_prompt.md
    6. registry.json 등록
  출력: 복제본 agent_id
  호출: agent_creator (폴더 생성 재사용), prompt_injector

### skills_manager.py
  역할: 스킬 장착/해제/조회/카탈로그 관리
  입력: agent_id, skill_id
  동작:
    - equip: 카탈로그에서 스킬 검증 → 에이전트 skills/ 복사 → profile.json 갱신
    - unequip: skills/ 제거 → profile.json 갱신
    - list: 카탈로그 전체 또는 에이전트별 조회
  출력: 작업 결과
  참조: skills_library/catalog.json, agents/{ID}/profile.json

### connection_manager.py
  역할: 에이전트 간 노드 연결 생성/해제/검증
  입력: from_agent_id, to_agent_id
  동작:
    - connect: 양쪽 manifest.json 갱신, 통신 권한 검증
    - disconnect: 양쪽 manifest.json 제거
    - validate: 연결 유효성 검사 (양쪽 에이전트 존재·활성 여부)
  출력: 연결 상태
  참조: agents/{ID}/connections/manifest.json

### prompt_injector.py
  역할: 런타임 프롬프트 템플릿에 변수를 치환하여 최종 프롬프트 생성
  입력: agent profile, is_master 플래그
  동작:
    1. is_master → prompts/master_runtime.md 로드
       else → prompts/worker_runtime.md 로드
    2. {AGENT_NAME}, {AGENT_ID}, {AGENT_ROLE} 등 변수 치환
    3. {EQUIPPED_SKILLS} → 현재 장착 스킬 목록 직렬화
    4. {ACTIVE_FRAMEWORKS} → config.yaml에서 추출
    5. agents/{ID}/system_prompt.md로 저장
  출력: 주입 완료된 프롬프트 파일 경로
  참조: prompts/*.md, agents/{ID}/profile.json, agents/{ID}/config.yaml

### state_machine.py
  역할: 에이전트 상태 전환 관리
  상태 목록: initialized → online → dormant / unstable / suspended
  입력: agent_id, 전환 트리거
  동작:
    - 전환 조건 검증 (layer_6 규칙 기반)
    - profile.json의 status 필드 갱신
    - 전환 이력 로그 기록
  출력: 전환 성공 여부
  참조: agents/{ID}/profile.json, agents/{ID}/logs/actions.log

### evolution_engine.py
  역할: 레벨업 판정, Stats 갱신
  입력: agent_id
  동작:
    - 레벨업 조건 충족 여부 판정 (layer_6 기준)
    - Stats(INT/MEM/SPD/REL) 계산·갱신
    - 결과를 profile.json에 반영
    - 레벨업 시 로그 기록
  출력: 레벨업 결과
  참조: agents/{ID}/profile.json, agents/{ID}/logs/actions.log

### factory_config.yaml
  역할: 팩토리 전역 설정
  내용:
    - 에이전트당 기본 스토리지 한도 (100MB)
    - 기본 컨텍스트 토큰 한도 (4000)
    - 로그 보관 기간 (30일)
    - 메시지 재전송 횟수 (3회)
    - 레벨업 조건표
    - 상태 전환 임계값


## runtime/ — 실행 환경

### agent_runner.py
  역할: 에이전트 인스턴스의 생명주기 관리
  동작:
    - 에이전트 로드 (profile + config + system_prompt)
    - 작업 수신 → 실행 → 결과 반환
    - 상태 변경 감지 → state_machine 호출
  연결: core/state_machine, core/prompt_injector, runtime/task_queue

### message_bus.py
  역할: LAYER 4 통신 프로토콜의 실제 구현
  동작:
    - 메시지 발송 (from → to 라우팅)
    - 통신 권한 매트릭스 검증
    - requires_ack 처리 (30초 타임아웃, 3회 재전송)
    - 메시지 로그 기록
  연결: agents/{ID}/connections/manifest.json

### task_queue.py
  역할: 에이전트 작업 큐 관리
  동작:
    - 작업 등록 (우선순위 기반)
    - 에이전트에 작업 배분
    - 작업 완료/실패 상태 추적
  연결: runtime/agent_runner

### resource_monitor.py
  역할: LAYER 5 자원 정책의 실제 구현
  동작:
    - 에이전트별 스토리지 사용량 추적
    - 80%/95%/100% 임계값 알림
    - 컨텍스트 토큰 카운팅
  연결: core/factory_config.yaml, runtime/message_bus (경고 전달)


## prompts/ — 프롬프트 관리

### master_runtime.md
  내용: CHUNSIK_PROTOCOL_v1.0-runtime.md 원본 그대로
  용도: prompt_injector가 마스터 에이전트 생성 시 로드

### worker_runtime.md
  내용: WORKER_AGENT_PROMPT_v1.0-runtime.md 원본 그대로
  용도: prompt_injector가 일반 에이전트 생성 시 로드

### fragments/
  역할: 프롬프트 유지보수를 위한 레이어별 분리 보관
  용도: layer_0 수정 시 → fragments/layer_0_immutable.md 하나만 수정
        → master_runtime.md와 worker_runtime.md 양쪽에 자동 반영
  주의: fragments는 직접 주입되지 않음. runtime.md를 빌드할 때만 사용.


## api/ — REST API

### server.py
  역할: FastAPI 앱 초기화, 라우터 등록, 미들웨어 적용
  연결: routes/*.py, middleware/*.py

### routes/agents.py
  엔드포인트:
    GET    /api/agents          → 전체 목록
    GET    /api/agents/{id}     → 상세 정보
    POST   /api/agents          → 생성 (→ core/agent_creator)
    POST   /api/agents/{id}/replicate → 복제 (→ core/agent_replicator)
    PATCH  /api/agents/{id}/status    → 상태 변경 (→ core/state_machine)

### routes/skills.py
  엔드포인트:
    GET    /api/skills           → 카탈로그 조회
    GET    /api/agents/{id}/skills → 에이전트 스킬 조회
    POST   /api/agents/{id}/skills/{skill_id}/equip   → 장착
    POST   /api/agents/{id}/skills/{skill_id}/unequip  → 해제

### routes/connections.py
  엔드포인트:
    GET    /api/connections       → 전체 연결 맵
    POST   /api/connections       → 연결 생성
    DELETE /api/connections       → 연결 해제

### routes/system.py
  엔드포인트:
    GET    /api/system/status     → 팩토리 상태
    GET    /api/system/logs       → 시스템 로그
    GET    /api/system/resources  → 리소스 현황

### routes/messages.py
  엔드포인트:
    POST   /api/messages          → 에이전트에게 메시지 전송
    GET    /api/messages/{id}     → 메시지 이력 조회


# ─────────────────────────────────────────────────────────
# 3. 파일 간 연결 관계 (의존성 맵)
# ─────────────────────────────────────────────────────────

```
[dashboard/app.jsx]
    │
    ▼ HTTP
[api/server.py]
    │
    ├── routes/agents.py ──────┬──▶ core/agent_creator.py
    │                          ├──▶ core/agent_replicator.py
    │                          └──▶ core/state_machine.py
    │
    ├── routes/skills.py ─────────▶ core/skills_manager.py
    │
    ├── routes/connections.py ────▶ core/connection_manager.py
    │
    ├── routes/system.py ─────────▶ core/factory_config.yaml
    │                              runtime/resource_monitor.py
    │
    └── routes/messages.py ───────▶ runtime/message_bus.py
```

```
[core/agent_creator.py]
    │
    ├──▶ core/prompt_injector.py ──▶ prompts/master_runtime.md
    │                              prompts/worker_runtime.md
    │
    ├──▶ core/skills_manager.py ──▶ skills_library/catalog.json
    │
    └──▶ core/registry.json
         agents/{ID}/  (폴더 생성)
```

```
[core/agent_replicator.py]
    │
    ├──▶ core/agent_creator.py (폴더 생성 함수 재사용)
    ├──▶ core/prompt_injector.py
    └──▶ core/registry.json
```

```
[core/prompt_injector.py]
    │
    ├── 읽기: prompts/master_runtime.md 또는 worker_runtime.md
    ├── 읽기: agents/{ID}/profile.json
    ├── 읽기: agents/{ID}/config.yaml
    └── 쓰기: agents/{ID}/system_prompt.md
```

```
[runtime/agent_runner.py]
    │
    ├──▶ agents/{ID}/system_prompt.md (로드)
    ├──▶ agents/{ID}/profile.json (상태 읽기)
    ├──▶ runtime/task_queue.py (작업 수신)
    ├──▶ runtime/message_bus.py (통신)
    └──▶ core/state_machine.py (상태 전환)
```

```
[runtime/message_bus.py]
    │
    ├── 읽기: agents/{ID}/connections/manifest.json (권한 검증)
    ├── 쓰기: agents/{ID}/logs/actions.log (메시지 기록)
    └── 참조: core/factory_config.yaml (재전송 횟수 등)
```

```
[core/evolution_engine.py]
    │
    ├── 읽기: agents/{ID}/profile.json (현재 레벨/스탯)
    ├── 읽기: agents/{ID}/logs/actions.log (작업 횟수/오류율)
    ├── 쓰기: agents/{ID}/profile.json (레벨/스탯 갱신)
    └── 참조: core/factory_config.yaml (레벨업 조건표)
```


# ─────────────────────────────────────────────────────────
# 4. 데이터 흐름 요약
# ─────────────────────────────────────────────────────────

## A. 에이전트 생성 흐름
사용자(대시보드)
  → api/routes/agents.py [POST /api/agents]
    → core/agent_creator.py
      → 폴더 생성 (agents/{ID}/)
      → profile.json 작성
      → config.yaml 작성
      → core/prompt_injector.py
        → prompts/{master|worker}_runtime.md 로드
        → 변수 치환
        → agents/{ID}/system_prompt.md 저장
      → core/skills_manager.py (마스터 시 기본 스킬 장착)
      → core/registry.json 등록
    → 대시보드에 결과 반환

## B. 스킬 장착 흐름
사용자(대시보드)
  → api/routes/skills.py [POST /api/agents/{id}/skills/{skill_id}/equip]
    → core/skills_manager.py
      → skills_library/catalog.json에서 스킬 검증
      → agents/{ID}/skills/에 스킬 파일 복사
      → agents/{ID}/profile.json 갱신
      → core/prompt_injector.py (system_prompt.md 재생성)
    → 대시보드에 결과 반환

## C. 에이전트 간 메시지 흐름
에이전트 A (발신)
  → runtime/message_bus.py
    → connections/manifest.json으로 연결 권한 검증
    → LAYER 4 메시지 형식 검증
    → 수신 에이전트 B의 task_queue에 등록
  → runtime/agent_runner.py (B)
    → 작업 처리
    → 결과를 message_bus 통해 A에게 응답

## D. 에이전트 복제 흐름
소유자/마스터
  → api/routes/agents.py [POST /api/agents/{id}/replicate]
    → core/agent_replicator.py
      → 원본 profile.json + config.yaml 복사
      → 새 ID 발급 + 새 폴더 생성
      → 스킬 상속 / 메모리·로그 초기화
      → core/prompt_injector.py (새 system_prompt.md)
      → core/registry.json 등록
    → 결과 반환

## E. 레벨업 흐름
마스터(춘식이) 또는 자동 트리거
  → core/evolution_engine.py
    → agents/{ID}/logs/actions.log 분석 (작업 횟수, 오류율)
    → factory_config.yaml 조건표 대조
    → 조건 충족 시 profile.json 갱신 (level, stats)
    → 변경 로그 기록
    → message_bus로 해당 에이전트에 레벨업 통보


# ─────────────────────────────────────────────────────────
# 5. 구현 순서 (권장)
# ─────────────────────────────────────────────────────────

Phase 1: 기반 (즉시 구현 가능)
  ① core/factory_config.yaml
  ② core/prompt_injector.py
  ③ core/agent_creator.py (기존 코드 리팩토링)
  ④ prompts/ 폴더 세팅

Phase 2: 관리 (Phase 1 완료 후)
  ⑤ core/skills_manager.py (기존 코드 리팩토링)
  ⑥ core/connection_manager.py
  ⑦ core/state_machine.py
  ⑧ core/evolution_engine.py

Phase 3: 실행 환경 (Phase 2 완료 후)
  ⑨ runtime/message_bus.py
  ⑩ runtime/task_queue.py
  ⑪ runtime/agent_runner.py
  ⑫ runtime/resource_monitor.py

Phase 4: API + 대시보드 (Phase 3 완료 후)
  ⑬ api/server.py + routes/
  ⑭ dashboard/app.jsx (기존 코드 연결)

Phase 5: 복제 + 테스트 (Phase 4 완료 후)
  ⑮ core/agent_replicator.py
  ⑯ tests/


# ═══════════════════════════════════════════════════════════
# 문서 끝
# 이 설계도가 확정되면 Phase 1부터 순차 구현을 시작한다.
# ═══════════════════════════════════════════════════════════
