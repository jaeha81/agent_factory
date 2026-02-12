# JH Agent Factory 체크포인트 (2026-02-13)

## 목표
- create_master.py 정상 실행 → agents/A0001 생성

## 최종 결과
- logs/*.log (activity/decision/error) 모두 "파일" 유지: OK
- agents/A0001 정상 생성: OK (profile.json, config.yaml, system_prompt.md)
- activity.log 기록: OK
- 워커 A0002 생성 E2E 검증: OK (PermissionError 없음)
- 재발 방지 가드: scripts/safe_e2e.bat 커밋 완료
- 릴리즈 태그: checkpoint-ok (4cb11c4)

## 핵심 이슈 & 원인
- PermissionError 원인: logs/activity.log (및 decision/error)가 "빈 디렉토리"로 존재 → open() 실패
- 해결: 해당 디렉토리 rmdir → 동일 경로에 파일로 재생성
- 코드 패치 불필요: _append_line은 이미 os.makedirs(exist_ok=True) + utf-8 append 구현이 올바름
  (문제는 "동명 디렉토리"가 파일 자리를 선점한 상태)

## 재현/검증 명령 (Windows)
- UTF-8 실행:
  chcp 65001 >nul && set PYTHONUTF8=1 && set PYTHONIOENCODING=utf-8 && py -X utf8 scripts\create_master.py

- 로그가 디렉토리로 잘못 생성됐을 때 복구:
  if exist logs\activity.log\NUL rmdir logs\activity.log
  if exist logs\decision.log\NUL rmdir logs\decision.log
  if exist logs\error.log\NUL rmdir logs\error.log
  if not exist logs mkdir logs
  if not exist logs\activity.log type nul > logs\activity.log
  if not exist logs\decision.log type nul > logs\decision.log
  if not exist logs\error.log type nul > logs\error.log

- 안전 실행(가드):
  scripts\safe_e2e.bat

## 산출물
- agents/A0001/ (생성물)
- scripts/safe_e2e.bat (가드)
- docs/NEXT.md (다음 작업)
- tag: checkpoint-ok

## Next (요약)
- create_master.py에서 ID 인자 지원(또는 create_worker.py 분리)
- (선택) preflight: logs/*.log가 dir이면 자동 정리
- CI smoke: clean env에서 생성/로그/registry 검증
