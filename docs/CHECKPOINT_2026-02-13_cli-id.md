# JH Agent Factory 체크포인트 (2026-02-13) - CLI agent id

## 목표
- create_master.py에 CLI 인자 추가 → 워커 에이전트 생성 공식화

## 최종 결과
- 브랜치: feat/cli-agent-id → master fast-forward 머지 완료
- CLI: --id / --name / --role 지원
- 검증:
  - A0002 생성 OK (워커봇, data_analyst)
  - A0003 스모크 OK (워커3, data_analyst)
  - 생성물: agents/<ID>/{profile.json, config.yaml, system_prompt.md}
  - logs/activity.log append OK

## 사용 예시 (Windows)
- UTF-8 실행:
  chcp 65001 >nul && set PYTHONUTF8=1 && set PYTHONIOENCODING=utf-8 && py -X utf8 scripts\create_master.py --id A0002 --name "워커봇" --role data_analyst

## 태그
- cli-id-ok @ d40f3fd

## Next
- (선택) role validation(허용 role 목록/스키마)
- (선택) id auto-increment(최신 ID 스캔 후 next 생성)
- CI smoke에 --id 워커 생성 케이스 추가
