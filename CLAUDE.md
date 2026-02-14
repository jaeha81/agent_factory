# Agent Factory - Claude Code 작업 메모

## 현재 상태 (2026-02-14)

### 완료된 작업
1. GitHub 원격 동기화 완료 (9커밋 pull)
2. 대시보드 로컬 실행 확인 (http://127.0.0.1:8000)
3. Render 클라우드 배포 설정 완료
   - `api_server.py`: PORT 환경변수 동적 할당, `/health` 헬스체크 엔드포인트 추가
   - `Procfile`: Render 서버 시작 명령
   - `render.yaml`: Render 빌드/배포/환경변수 설정
   - railway.json은 삭제 (Railway → Render로 전환, 무료 티어 사용 가능)
4. 커밋 `a9be5ba` push 완료

### 다음 작업 (모바일에서 진행)
Render 배포 실행:
1. https://render.com 접속 → GitHub 로그인
2. New → Web Service → `jaeha81/agent_factory` 선택
3. 환경변수 설정:
   - GROQ_API_KEY
   - GEMINI_API_KEY
   - TOGETHER_API_KEY
   - OPENROUTER_API_KEY
4. Create Web Service → 자동 배포
5. 생성된 `https://agent-factory-xxxx.onrender.com` URL로 외부 접속 확인

### 참고사항
- Render 무료 티어: 15분 미사용 시 슬립모드 (재접속 시 ~30초 대기)
- 휘발성 파일시스템: 재배포 시 agents/, logs/ 데이터 초기화됨
- 영구 데이터 보존 필요 시 PostgreSQL 추가 검토
- 로컬 서버 실행: `python run.py` (http://127.0.0.1:8000)
