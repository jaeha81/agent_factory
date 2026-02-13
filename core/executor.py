"""
core/executor.py
JH Agent Factory — 로컬 실행기 (Executor)

기능:
  - safe_run(cmd): allowlist 기반 셸 명령 실행
  - read_file(path): 레포 내부 파일 읽기
  - write_file(path, content): 레포 내부 파일 쓰기
  - list_dir(path): 디렉토리 목록
  - grep(pattern, path): 파일 내용 검색
  - git_ops(action, **kwargs): 안전한 Git 작업
  - scan_secrets(text): 민감정보 패턴 스캔

보안:
  - allowlist 명령만 실행
  - 경로는 레포 내부(PROJECT_ROOT)만 허용
  - 비밀키 출력 마스킹
  - 위험 명령 차단 (rm -rf, format, reset --hard 등)
  - 모든 실행 결과를 JSONL 로그로 기록
"""

import json
import os
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── 경로 상수 ──────────────────────────────────────────
_CORE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _CORE_DIR.parent
_LOGS_DIR = PROJECT_ROOT / "logs"
_EXEC_LOG = _LOGS_DIR / "executor.jsonl"

# ── allowlist / blocklist ──────────────────────────────
ALLOWED_COMMANDS = {
    "python", "python3", "pip", "pip3",
    "git",
    "ls", "cat", "head", "tail", "grep", "find", "echo", "mkdir", "cp", "mv", "touch",
    "pytest", "unittest",
    "npm", "node", "npx",
    "wc", "sort", "uniq", "diff", "tree",
}

BLOCKED_PATTERNS = [
    re.compile(r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|--recursive\s+--force|-[a-zA-Z]*f[a-zA-Z]*r)\b"),
    re.compile(r"\brm\s+-rf\b"),
    re.compile(r"\bformat\b", re.IGNORECASE),
    re.compile(r"\bmkfs\b"),
    re.compile(r"\bdd\s+if="),
    re.compile(r"\bshutdown\b"),
    re.compile(r"\breboot\b"),
    re.compile(r"\bpowershell\s+-[eE]nc"),
    re.compile(r"\bcurl\b.*\|\s*(ba)?sh"),
    re.compile(r"\bwget\b.*\|\s*(ba)?sh"),
    re.compile(r"\beval\s*\("),
    re.compile(r"\bgit\s+push\s+--force\b"),
    re.compile(r"\bgit\s+push\s+-f\b"),
    re.compile(r"\bgit\s+reset\s+--hard\b"),
    re.compile(r"\bgit\s+clean\s+-fd\b"),
    re.compile(r"\bgit\s+branch\s+-D\s+(main|master)\b"),
]

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret[_-]?key|password|passwd|token|private[_-]?key)\s*[=:]\s*\S+"),
    re.compile(r"(?i)(aws_access_key_id|aws_secret_access_key)\s*[=:]\s*\S+"),
    re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"),
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
]

SENSITIVE_FILE_PATTERNS = [
    re.compile(r"\.env$"),
    re.compile(r"\.env\..+$"),
    re.compile(r"\.secret$"),
    re.compile(r"credentials", re.IGNORECASE),
    re.compile(r"\.pem$"),
    re.compile(r"\.key$"),
    re.compile(r"id_rsa"),
]


# ── 로그 유틸 ──────────────────────────────────────────
def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log_execution(entry: dict):
    """실행 로그를 JSONL 파일에 추가."""
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    entry.setdefault("timestamp", _now_iso())
    entry.setdefault("task_id", str(uuid.uuid4())[:8])
    with open(_EXEC_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _mask_secrets(text: str) -> str:
    """출력 텍스트에서 민감정보를 마스킹."""
    masked = text
    for pat in SECRET_PATTERNS:
        masked = pat.sub("***REDACTED***", masked)
    return masked


# ── 경로 검증 ──────────────────────────────────────────
def _validate_path(path: str) -> Path:
    """경로가 레포 내부인지 검증. 외부이면 ValueError 발생."""
    resolved = (PROJECT_ROOT / path).resolve()
    if not str(resolved).startswith(str(PROJECT_ROOT)):
        raise ValueError(f"접근 금지: 레포 외부 경로입니다 — {path}")
    return resolved


def _is_sensitive_file(path: str) -> bool:
    """민감한 파일인지 확인."""
    for pat in SENSITIVE_FILE_PATTERNS:
        if pat.search(path):
            return True
    return False


# ── 명령 검증 ──────────────────────────────────────────
def _validate_command(cmd: str) -> tuple:
    """명령어 allowlist/blocklist 검증. (allowed: bool, reason: str)"""
    # blocklist 검사 (패턴 매칭)
    for pat in BLOCKED_PATTERNS:
        if pat.search(cmd):
            return False, f"차단된 명령 패턴: {pat.pattern}"

    # allowlist 검사 (첫 번째 명령어 기준)
    # 파이프 분리 후 각 명령의 첫 토큰 검사
    parts = cmd.split("|")
    for part in parts:
        tokens = part.strip().split()
        if not tokens:
            continue
        base_cmd = os.path.basename(tokens[0])
        if base_cmd not in ALLOWED_COMMANDS:
            return False, f"허용되지 않은 명령: {base_cmd}"

    return True, "OK"


# ═══════════════════════════════════════════════════════
# 공개 API
# ═══════════════════════════════════════════════════════

def safe_run(cmd: str, timeout: int = 30, cwd: Optional[str] = None) -> dict:
    """
    allowlist 기반 안전한 셸 명령 실행.

    Args:
        cmd: 실행할 명령어
        timeout: 타임아웃(초)
        cwd: 작업 디렉토리 (레포 내부만 허용)

    Returns:
        {"stdout", "stderr", "returncode", "success", "blocked", "reason"}
    """
    task_id = str(uuid.uuid4())[:8]
    log_entry = {"task_id": task_id, "action": "safe_run", "command": cmd}

    # 1) 명령 검증
    allowed, reason = _validate_command(cmd)
    if not allowed:
        log_entry.update({"result": "BLOCKED", "reason": reason, "error": None, "rollback": False})
        _log_execution(log_entry)
        return {"stdout": "", "stderr": f"BLOCKED: {reason}", "returncode": -1,
                "success": False, "blocked": True, "reason": reason}

    # 2) cwd 검증
    work_dir = str(PROJECT_ROOT)
    if cwd:
        resolved_cwd = _validate_path(cwd)
        if not resolved_cwd.is_dir():
            return {"stdout": "", "stderr": f"디렉토리 없음: {cwd}", "returncode": -1,
                    "success": False, "blocked": False, "reason": "invalid_cwd"}
        work_dir = str(resolved_cwd)

    # 3) 실행
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=work_dir,
        )
        stdout = _mask_secrets(result.stdout)
        stderr = _mask_secrets(result.stderr)

        log_entry.update({
            "result": "OK" if result.returncode == 0 else "FAIL",
            "returncode": result.returncode,
            "error": stderr[:500] if result.returncode != 0 else None,
            "rollback": False,
        })
        _log_execution(log_entry)

        return {"stdout": stdout, "stderr": stderr, "returncode": result.returncode,
                "success": result.returncode == 0, "blocked": False, "reason": ""}

    except subprocess.TimeoutExpired:
        log_entry.update({"result": "TIMEOUT", "error": f"타임아웃 {timeout}초 초과", "rollback": False})
        _log_execution(log_entry)
        return {"stdout": "", "stderr": f"타임아웃: {timeout}초 초과", "returncode": -1,
                "success": False, "blocked": False, "reason": "timeout"}

    except Exception as e:
        log_entry.update({"result": "ERROR", "error": str(e), "rollback": False})
        _log_execution(log_entry)
        return {"stdout": "", "stderr": str(e), "returncode": -1,
                "success": False, "blocked": False, "reason": str(e)}


def read_file(path: str) -> dict:
    """레포 내부 파일 읽기."""
    task_id = str(uuid.uuid4())[:8]
    log_entry = {"task_id": task_id, "action": "read_file", "path": path}

    try:
        resolved = _validate_path(path)
        if _is_sensitive_file(str(resolved)):
            log_entry.update({"result": "BLOCKED", "reason": "민감 파일"})
            _log_execution(log_entry)
            return {"result": "", "success": False, "error": "민감 파일 접근 차단"}

        if not resolved.is_file():
            return {"result": "", "success": False, "error": f"파일 없음: {path}"}

        content = resolved.read_text(encoding="utf-8")
        log_entry.update({"result": "OK", "bytes": len(content)})
        _log_execution(log_entry)
        return {"result": content, "success": True, "error": None}

    except ValueError as e:
        log_entry.update({"result": "BLOCKED", "reason": str(e)})
        _log_execution(log_entry)
        return {"result": "", "success": False, "error": str(e)}


def write_file(path: str, content: str) -> dict:
    """레포 내부 파일 쓰기."""
    task_id = str(uuid.uuid4())[:8]
    log_entry = {"task_id": task_id, "action": "write_file", "path": path}

    try:
        resolved = _validate_path(path)
        if _is_sensitive_file(str(resolved)):
            log_entry.update({"result": "BLOCKED", "reason": "민감 파일"})
            _log_execution(log_entry)
            return {"success": False, "error": "민감 파일 쓰기 차단"}

        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")

        log_entry.update({"result": "OK", "bytes": len(content)})
        _log_execution(log_entry)
        return {"success": True, "error": None}

    except ValueError as e:
        log_entry.update({"result": "BLOCKED", "reason": str(e)})
        _log_execution(log_entry)
        return {"success": False, "error": str(e)}


def list_dir(path: str = ".") -> dict:
    """디렉토리 목록 조회."""
    try:
        resolved = _validate_path(path)
        if not resolved.is_dir():
            return {"result": [], "success": False, "error": f"디렉토리 없음: {path}"}

        entries = sorted(
            [{"name": e.name, "type": "dir" if e.is_dir() else "file"}
             for e in resolved.iterdir() if not e.name.startswith(".")],
            key=lambda x: (x["type"] == "file", x["name"]),
        )
        return {"result": entries, "success": True, "error": None}

    except ValueError as e:
        return {"result": [], "success": False, "error": str(e)}


def grep(pattern: str, path: str = ".", max_results: int = 50) -> dict:
    """파일 내용 검색 (레포 내부만)."""
    try:
        resolved = _validate_path(path)
        regex = re.compile(pattern)
        matches = []

        if resolved.is_file():
            targets = [resolved]
        else:
            targets = [f for f in resolved.rglob("*") if f.is_file() and f.suffix in
                        (".py", ".json", ".md", ".yaml", ".yml", ".js", ".jsx", ".ts", ".tsx", ".txt", ".cfg")]

        for fpath in targets:
            if len(matches) >= max_results:
                break
            try:
                lines = fpath.read_text(encoding="utf-8").splitlines()
                for i, line in enumerate(lines, 1):
                    if regex.search(line):
                        matches.append({
                            "file": str(fpath.relative_to(PROJECT_ROOT)),
                            "line": i,
                            "content": line.strip()[:200],
                        })
                        if len(matches) >= max_results:
                            break
            except (UnicodeDecodeError, PermissionError):
                continue

        return {"result": matches, "success": True, "count": len(matches), "error": None}

    except (ValueError, re.error) as e:
        return {"result": [], "success": False, "count": 0, "error": str(e)}


def scan_secrets(text: str) -> list:
    """
    텍스트에서 민감정보 패턴을 스캔.
    Returns: [{"line": int, "pattern": str, "snippet": str}, ...]
    """
    warnings = []
    for i, line in enumerate(text.splitlines(), 1):
        for pat in SECRET_PATTERNS:
            if pat.search(line):
                warnings.append({
                    "line": i,
                    "pattern": pat.pattern[:60],
                    "snippet": line.strip()[:100],
                })
    return warnings


def git_ops(action: str, args: Optional[list] = None, message: Optional[str] = None) -> dict:
    """
    안전한 Git 작업 수행.

    Args:
        action: status, diff, log, branch, add, commit, checkout, fetch, pull, push
        args: 추가 인자
        message: 커밋 메시지 (commit 시)

    Returns:
        {"result", "success", "scan_warnings"}
    """
    ALLOWED_GIT_ACTIONS = {"status", "diff", "log", "branch", "add", "commit",
                           "checkout", "fetch", "pull", "push", "stash", "tag"}

    if action not in ALLOWED_GIT_ACTIONS:
        return {"result": "", "success": False, "scan_warnings": [],
                "error": f"허용되지 않은 Git 작업: {action}"}

    args = args or []

    # 위험 인자 필터링
    dangerous_args = {"--force", "-f", "--hard", "-D"}
    if action == "push" and any(a in dangerous_args for a in args):
        return {"result": "", "success": False, "scan_warnings": [],
                "error": "금지: force push / hard reset"}

    if action == "reset" and "--hard" in args:
        return {"result": "", "success": False, "scan_warnings": [],
                "error": "금지: git reset --hard"}

    # 커밋 전 민감정보 스캔
    scan_warnings = []
    if action == "commit":
        if not message:
            return {"result": "", "success": False, "scan_warnings": [],
                    "error": "커밋 메시지가 비어있습니다"}

        # staged 파일 내용 스캔
        diff_result = safe_run("git diff --cached", timeout=10)
        if diff_result["success"]:
            scan_warnings = scan_secrets(diff_result["stdout"])
            if scan_warnings:
                _log_execution({"action": "git_commit_blocked", "reason": "민감정보 감지",
                                "warnings": scan_warnings})
                return {"result": "", "success": False, "scan_warnings": scan_warnings,
                        "error": "커밋 차단: 민감정보가 감지되었습니다"}

    # 명령 조립
    cmd_parts = ["git", action]
    if action == "commit" and message:
        cmd_parts.extend(["-m", message])
    cmd_parts.extend(args)

    # 안전한 인자 조합을 위해 shell=False로 실행
    task_id = str(uuid.uuid4())[:8]
    log_entry = {"task_id": task_id, "action": f"git_{action}", "args": args}

    try:
        result = subprocess.run(
            cmd_parts, capture_output=True, text=True, timeout=60,
            cwd=str(PROJECT_ROOT),
        )
        stdout = _mask_secrets(result.stdout)
        stderr = _mask_secrets(result.stderr)

        log_entry.update({"result": "OK" if result.returncode == 0 else "FAIL",
                          "returncode": result.returncode})
        _log_execution(log_entry)

        return {"result": stdout + stderr, "success": result.returncode == 0,
                "scan_warnings": scan_warnings, "error": None}

    except subprocess.TimeoutExpired:
        log_entry.update({"result": "TIMEOUT"})
        _log_execution(log_entry)
        return {"result": "", "success": False, "scan_warnings": [],
                "error": "Git 작업 타임아웃"}

    except Exception as e:
        log_entry.update({"result": "ERROR", "error": str(e)})
        _log_execution(log_entry)
        return {"result": "", "success": False, "scan_warnings": [],
                "error": str(e)}


# ── 편의 함수 ──────────────────────────────────────────
def get_execution_log(limit: int = 50) -> list:
    """최근 실행 로그 조회."""
    if not _EXEC_LOG.is_file():
        return []
    lines = _EXEC_LOG.read_text(encoding="utf-8").strip().splitlines()
    entries = []
    for line in lines[-limit:]:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


# ── CLI 테스트 ─────────────────────────────────────────
if __name__ == "__main__":
    print("=== Executor Self-Test ===\n")

    # 1) safe_run 테스트
    print("[1] safe_run('ls core/')")
    r = safe_run("ls core/")
    print(f"    success={r['success']}, stdout={r['stdout'][:100]}\n")

    # 2) 차단 테스트
    print("[2] safe_run('rm -rf /')")
    r = safe_run("rm -rf /")
    print(f"    blocked={r['blocked']}, reason={r['reason']}\n")

    # 3) read_file
    print("[3] read_file('README.md')")
    r = read_file("README.md")
    print(f"    success={r['success']}, length={len(r['result'])}\n")

    # 4) 민감파일 차단
    print("[4] read_file('.env')")
    r = read_file(".env")
    print(f"    success={r['success']}, error={r['error']}\n")

    # 5) grep
    print("[5] grep('def create_agent', 'core/')")
    r = grep("def create_agent", "core/")
    print(f"    count={r['count']}, matches={r['result'][:2]}\n")

    # 6) git status
    print("[6] git_ops('status')")
    r = git_ops("status")
    print(f"    success={r['success']}, result={r['result'][:100]}\n")

    print("=== Self-Test Complete ===")
