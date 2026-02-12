# JH Agent Factory 체크포인트 (2026-02-13) - next-id

## 목표
- create_master.py에 --next 자동 ID 발급 기능 추가

## 최종 결과
- CLI: --next 지원 (agents/ 스캔 → max+1 → A####)
- 충돌 검증: --next 와 --id 동시 사용 시 exit 2
- stdout: CREATED_ID=A0004 형식으로 출력
- 머지: feat/next-id → master fast-forward
- 태그: next-id-ok

## 사용 예시 (Windows)
- 자동 발급:
  chcp 65001 >nul && set PYTHONUTF8=1 && set PYTHONIOENCODING=utf-8 && py -X utf8 scripts\create_master.py --next --name "워커NEXT" --role data_analyst

- 충돌(의도된 에러):
  py -X utf8 scripts\create_master.py --next --id A9999

## 산출물
- scripts/create_master.py (--next / CREATED_ID 출력)
- tag: next-id-ok

## Next
- (선택) --next 사용 시 생성된 ID로 후속 명령(예: open folder) 자동 출력
- (선택) role validation / schema
- CI smoke에 --next 케이스 추가
