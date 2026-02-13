import argparse
import io
import os
import platform
import subprocess
import sys
import textwrap
import time
from pathlib import Path

# Windows cp949 인코딩 문제 방지
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"

def is_windows() -> bool:
    return platform.system().lower().startswith("win")

def venv_python() -> Path:
    if is_windows():
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"

def run(cmd, cwd=ROOT, env=None, check=True):
    print(f"\n$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(cwd), env=env, check=check)

def ensure_repo_root():
    api = ROOT / "api_server.py"
    if not api.exists():
        raise SystemExit("ERROR: api_server.py가 repo root에 없습니다. run.py는 repo root에서 실행해야 합니다.")

def ensure_venv():
    py = venv_python()
    if py.exists():
        return
    print("📦 .venv 생성 중...")
    run([sys.executable, "-m", "venv", str(VENV_DIR)])
    if not py.exists():
        raise SystemExit("ERROR: venv 생성 실패 (.venv/python 없음)")

def pip_install(no_install: bool):
    py = venv_python()
    if no_install:
        print("⏭️  --no-install 지정됨: 패키지 설치 생략")
        return
    req = ROOT / "requirements.txt"
    if not req.exists():
        raise SystemExit("ERROR: requirements.txt가 없습니다.")
    print("⬆️  pip 업그레이드...")
    run([str(py), "-m", "pip", "install", "-U", "pip"])
    print("📥 requirements 설치...")
    run([str(py), "-m", "pip", "install", "-r", str(req)])

def doctor_check():
    py = venv_python()
    print("🩺 환경 점검(import test)...")
    run([str(py), "-c", "import fastapi, uvicorn, yaml; print('OK: imports fine')"])

def serve(host: str, port: int, reload_: bool):
    py = venv_python()
    env = os.environ.copy()
    # repo root를 PYTHONPATH에 추가(어떤 실행환경에서도 core/ 등 import 안정화)
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    cmd = [str(py), "-m", "uvicorn", "api_server:app", "--host", host, "--port", str(port)]
    if reload_:
        cmd.append("--reload")

    banner = f"""
    ✅ 서버 실행 명령 준비 완료
    - Swagger:  http://{host}:{port}/docs
    - Agents:   http://{host}:{port}/api/agents
    - Status:   http://{host}:{port}/api/system/status
    종료: Ctrl+C
    """
    print(textwrap.dedent(banner).strip())
    run(cmd, env=env, check=True)

def main():
    ensure_repo_root()

    p = argparse.ArgumentParser(description="agent_factory one-command runner")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true", help="dev reload")
    p.add_argument("--doctor", action="store_true", help="setup + import test then exit")
    p.add_argument("--no-install", action="store_true", help="skip pip install")
    args = p.parse_args()

    ensure_venv()
    pip_install(no_install=args.no_install)

    if args.doctor:
        doctor_check()
        print("✅ DOCTOR OK. 이제 `python run.py`로 서버를 켜면 됩니다.")
        return

    serve(args.host, args.port, args.reload)

if __name__ == "__main__":
    main()
