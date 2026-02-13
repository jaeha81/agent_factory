"""
test_executor.py
Executor + 기본 에이전트 템플릿 통합 테스트 시나리오.

실행:
  cd agent_factory
  python scripts/test_executor.py
"""

import json
import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _PROJECT_ROOT)

from core.executor import (
    safe_run, read_file, write_file, list_dir, grep,
    scan_secrets, git_ops, _validate_command, PROJECT_ROOT,
)

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    status = "PASS" if condition else "FAIL"
    if condition:
        PASS += 1
    else:
        FAIL += 1
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not condition else ""))


def test_safe_run():
    print("\n=== 1. safe_run 테스트 ===")

    # 1.1 허용 명령 실행
    r = safe_run("echo hello")
    check("허용 명령(echo)", r["success"] and "hello" in r["stdout"])

    # 1.2 차단 명령
    r = safe_run("rm -rf /")
    check("차단 명령(rm -rf)", r["blocked"] is True)

    # 1.3 allowlist 외 명령
    r = safe_run("curl http://example.com")
    check("allowlist 외 명령(curl)", r["success"] is False)

    # 1.4 타임아웃
    r = safe_run("python -c \"import time; time.sleep(5)\"", timeout=1)
    check("타임아웃(1초)", r["success"] is False and "타임아웃" in r["stderr"])

    # 1.5 git push --force 차단
    r = safe_run("git push --force origin main")
    check("git push --force 차단", r["blocked"] is True)

    # 1.6 git reset --hard 차단
    r = safe_run("git reset --hard HEAD")
    check("git reset --hard 차단", r["blocked"] is True)


def test_file_ops():
    print("\n=== 2. 파일 I/O 테스트 ===")

    # 2.1 파일 읽기
    r = read_file("README.md")
    check("파일 읽기(README.md)", r["success"] and len(r["result"]) > 0)

    # 2.2 민감 파일 차단
    r = read_file(".env")
    check("민감 파일 차단(.env)", r["success"] is False)

    # 2.3 레포 외부 차단
    r = read_file("../../etc/passwd")
    check("레포 외부 차단(../../etc/passwd)", r["success"] is False)

    # 2.4 파일 쓰기 + 읽기 확인
    test_path = "logs/_test_write_temp.txt"
    w = write_file(test_path, "test_content_12345")
    r = read_file(test_path)
    check("파일 쓰기+읽기", w["success"] and r["success"] and "test_content_12345" in r["result"])

    # 정리
    full_path = PROJECT_ROOT / test_path
    if full_path.exists():
        full_path.unlink()


def test_list_dir():
    print("\n=== 3. list_dir 테스트 ===")

    r = list_dir("core")
    check("디렉토리 목록(core/)",
          r["success"] and any(e["name"] == "executor.py" for e in r["result"]))


def test_grep():
    print("\n=== 4. grep 테스트 ===")

    r = grep("def safe_run", "core/executor.py")
    check("grep(def safe_run)", r["success"] and r["count"] > 0)

    r = grep("NONEXISTENT_PATTERN_XYZ", "core/")
    check("grep(존재하지 않는 패턴)", r["success"] and r["count"] == 0)


def test_scan_secrets():
    print("\n=== 5. 민감정보 스캔 테스트 ===")

    # 5.1 민감정보 감지
    text1 = "config.api_key = sk-1234567890abcdef\nother_line = safe"
    warnings = scan_secrets(text1)
    check("민감정보 감지(api_key)", len(warnings) > 0)

    # 5.2 안전한 텍스트
    text2 = "def hello():\n    return 'world'\n"
    warnings = scan_secrets(text2)
    check("안전 텍스트 통과", len(warnings) == 0)

    # 5.3 GitHub PAT 감지
    text3 = "token = ghp_ABCDEFghijklmnop1234567890abcdef01"
    warnings = scan_secrets(text3)
    check("GitHub PAT 감지", len(warnings) > 0)


def test_git_ops():
    print("\n=== 6. git_ops 테스트 ===")

    # 6.1 git status
    r = git_ops("status")
    check("git status", r["success"])

    # 6.2 금지된 작업
    r = git_ops("push", args=["--force", "origin", "main"])
    check("git push --force 차단", r["success"] is False)

    # 6.3 빈 커밋 메시지 차단
    r = git_ops("commit", message="")
    check("빈 커밋 메시지 차단", r["success"] is False)

    # 6.4 허용되지 않은 action
    r = git_ops("rebase", args=["-i"])
    check("허용되지 않은 action(rebase)", r["success"] is False)


def test_base_template():
    print("\n=== 7. 기본 에이전트 템플릿 확인 ===")

    base_dir = os.path.join(_PROJECT_ROOT, "agents", "_base")

    check("agents/_base/ 존재",
          os.path.isdir(base_dir))

    check("base_instructions.md 존재",
          os.path.isfile(os.path.join(base_dir, "base_instructions.md")))

    check("base_skills.json 존재",
          os.path.isfile(os.path.join(base_dir, "base_skills.json")))

    check("memory_policy.md 존재",
          os.path.isfile(os.path.join(base_dir, "memory_policy.md")))

    # base_skills.json에 4개 기본 스킬이 정의되어 있는지
    with open(os.path.join(base_dir, "base_skills.json"), "r") as f:
        base_skills = json.load(f)
    skill_ids = [s["skill_id"] for s in base_skills.get("skills", [])]
    check("기본 스킬 4종 정의(filesystem, terminal, git, coding)",
          all(s in skill_ids for s in ["filesystem", "terminal", "git", "coding"]))


def test_skill_library():
    print("\n=== 8. 스킬 라이브러리 확인 ===")

    lib_core = os.path.join(_PROJECT_ROOT, "skills_library", "core")
    check("skills_library/core/ 존재", os.path.isdir(lib_core))

    for name in ["filesystem", "terminal", "git", "coding"]:
        path = os.path.join(lib_core, f"{name}.skill.json")
        exists = os.path.isfile(path)
        if exists:
            with open(path, "r") as f:
                data = json.load(f)
            has_fields = all(k in data for k in ["skill_id", "name", "version", "safety_rules", "inputs", "outputs"])
        else:
            has_fields = False
        check(f"{name}.skill.json 표준 스키마 준수", exists and has_fields)

    schema_path = os.path.join(_PROJECT_ROOT, "skills_library", "schema.skill.json")
    check("schema.skill.json 존재", os.path.isfile(schema_path))


def main():
    print("=" * 60)
    print(" JH Agent Factory — Executor & Template 통합 테스트")
    print("=" * 60)

    test_safe_run()
    test_file_ops()
    test_list_dir()
    test_grep()
    test_scan_secrets()
    test_git_ops()
    test_base_template()
    test_skill_library()

    print("\n" + "=" * 60)
    print(f" 결과: {PASS} passed, {FAIL} failed (total {PASS + FAIL})")
    print("=" * 60)

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
