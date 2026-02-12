# Release Notes (Checkpoint series)

## checkpoint-ok
- A0001 생성 흐름 정상화

## cli-id-ok
- create_master.py: --id/--name/--role 지원

## next-id-ok
- create_master.py: --next 자동 ID 발급 + CREATED_ID 출력
- --next + --id 충돌 exit 2

## e2e-create-ok
- scripts/create.py: 단일 명령 create → registry append(JSONL) → validate → log
- stdout: CREATED_ID=AXXXX STATUS=OK/FAIL

## safety
- scripts/safe_e2e.bat: logs/*.log dir-collision 가드
