# Git 운영 정책 (Git Policy)

> JH Agent Factory의 Git 워크플로우, 브랜치 전략, 커밋 규칙, 민감정보 스캔 정책.

## 1. 브랜치 전략

| 브랜치 | 용도 | 보호 |
|--------|------|------|
| `main` / `master` | 안정 릴리스 | 직접 push 금지, PR 필수 |
| `claude/*` | Claude Code 작업 브랜치 | 자동 생성, 작업 후 PR |
| `feature/*` | 기능 개발 | 자유 push |
| `fix/*` | 버그 수정 | 자유 push |
| `experiment/*` | 실험적 변경 | 자유 push, merge 전 리뷰 |

### 규칙
- main/master에 직접 push하지 마라.
- 작업 브랜치는 `claude/`, `feature/`, `fix/` 접두사를 사용하라.
- 브랜치 이름에 한글, 공백, 특수문자를 넣지 마라.

## 2. 커밋 규칙

### 커밋 메시지 형식
```
<type>: <subject>

[optional body]
```

### 타입 (type)
| 타입 | 설명 |
|------|------|
| `feat` | 새 기능 |
| `fix` | 버그 수정 |
| `refactor` | 리팩토링 (기능 변경 없음) |
| `docs` | 문서 변경 |
| `test` | 테스트 추가/수정 |
| `chore` | 빌드, 설정, 스크립트 등 |

### 금지사항
- 빈 커밋 메시지 금지
- 커밋 메시지에 민감정보(API 키, 비밀번호) 포함 금지
- `WIP:` 메시지는 작업 중 임시 커밋에만 사용

## 3. 민감정보 스캔

### 커밋 전 자동 스캔 대상
아래 패턴이 staged 파일에 포함되면 **커밋을 차단**한다:

```
api_key=*, secret_key=*, password=*, token=*
aws_access_key_id=*, aws_secret_access_key=*
-----BEGIN (RSA )?PRIVATE KEY-----
ghp_* (GitHub Personal Access Token)
sk-* (OpenAI/Anthropic API Key)
```

### 스캔 실행
- `core/executor.py`의 `scan_secrets()` 함수가 자동 수행
- `git_ops("commit", ...)` 호출 시 staged diff를 자동 스캔
- 수동 스캔: `python -c "from core.executor import scan_secrets; ..."`

### 차단 시 대응
1. 민감정보가 감지되면 커밋이 차단됨
2. 해당 파일에서 민감정보를 제거하거나 환경변수로 교체
3. `.gitignore`에 해당 파일 추가 (필요 시)
4. 재시도

## 4. 금지 명령

아래 Git 명령은 **절대 사용 금지**:

| 명령 | 위험도 | 이유 |
|------|--------|------|
| `git push --force` | 치명적 | 원격 히스토리 파괴 |
| `git push -f` | 치명적 | 위와 동일 |
| `git reset --hard` | 높음 | 로컬 변경사항 영구 삭제 |
| `git clean -fd` | 높음 | 추적되지 않는 파일 영구 삭제 |
| `git branch -D main` | 치명적 | main 브랜치 삭제 |
| `git rebase -i` | 높음 | 히스토리 변조 (인터랙티브) |

## 5. Push 규칙

- push 전 `git status`로 상태 확인
- push 실패 시 최대 4회 재시도 (2s, 4s, 8s, 16s 지수 백오프)
- `-u origin <branch-name>` 형식 사용
- main/master에 직접 push 절대 금지

## 6. .gitignore 필수 항목

```
.env
.env.*
*.pem
*.key
*.secret
credentials.json
id_rsa*
__pycache__/
.venv/
node_modules/
*.pyc
```
