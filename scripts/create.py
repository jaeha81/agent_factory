"""
create.py
단일 명령 E2E: 에이전트 생성 + registry 등록 + 검증 + 로그.

실행:
  cd agent_factory
  py -X utf8 scripts/create.py create --next --name "워커X" --role data_analyst
  py -X utf8 scripts/create.py create --id A0005 --name "워커5" --role general
  py -X utf8 scripts/create.py create --next --name "워커X" --role data_analyst --pack basic
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _PROJECT_ROOT)

from core.agent_creator import create_agent


def _find_next_agent_id(agents_dir: Path) -> str:
    agents_dir.mkdir(parents=True, exist_ok=True)
    max_n = 0
    for p in agents_dir.iterdir():
        if p.is_dir():
            m = re.match(r"^A(\d{4})$", p.name)
            if m:
                max_n = max(max_n, int(m.group(1)))
    return f"A{max_n + 1:04d}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append_registry(agents_dir: Path, record: dict) -> None:
    registry_path = agents_dir / "registry.jsonl"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with open(registry_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _validate_agent(agent_dir: Path) -> list[str]:
    missing = []
    for name in ("profile.json", "config.yaml", "system_prompt.md"):
        if not (agent_dir / name).is_file():
            missing.append(name)
    return missing


def cmd_create(args) -> None:
    project_root = Path(_PROJECT_ROOT)
    agents_dir = project_root / "agents"
    agent_id = "N/A"

    try:
        # 1) ID 결정
        if args.next and args.id:
            print(f"CREATED_ID=N/A STATUS=FAIL REASON=--next cannot be used with --id")
            raise SystemExit(2)

        if args.next:
            resolved_id = _find_next_agent_id(agents_dir)
        elif args.id:
            resolved_id = args.id
        else:
            resolved_id = None  # master mode

        is_master = resolved_id is None or resolved_id == "A0001"
        name = args.name
        role = args.role

        # 2) 에이전트 생성 (core.agent_creator 재사용)
        profile = create_agent(
            name=name,
            role=role,
            is_master=is_master,
        )
        agent_id = profile["agent_id"]

        # 3) registry.jsonl append
        record = {
            "id": agent_id,
            "name": name,
            "role": role,
            "pack": args.pack,
            "created_at": _now_iso(),
            "status": "ok",
        }
        _append_registry(agents_dir, record)

        # 4) validate
        agent_dir = agents_dir / agent_id
        missing = _validate_agent(agent_dir)
        if missing:
            print(f"CREATED_ID={agent_id} STATUS=FAIL REASON=missing files: {', '.join(missing)}")
            raise SystemExit(1)

        # 5) log — already handled by create_agent internally

        # 6) stdout
        print(f"CREATED_ID={agent_id} STATUS=OK")

    except (ValueError, FileNotFoundError) as e:
        print(f"CREATED_ID={agent_id} STATUS=FAIL REASON={e}")
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description="JH Agent Factory — E2E CLI")
    sub = parser.add_subparsers(dest="command")

    p_create = sub.add_parser("create", help="에이전트 생성 + 등록 + 검증")
    p_create.add_argument("--id", default=None, help="에이전트 ID (A0001=마스터)")
    p_create.add_argument("--next", action="store_true", help="다음 ID 자동 발급")
    p_create.add_argument("--name", required=True, help="에이전트 이름")
    p_create.add_argument("--role", required=True, help="에이전트 역할")
    p_create.add_argument("--pack", default=None, help="스킬 팩 (optional)")

    args = parser.parse_args()

    if args.command == "create":
        cmd_create(args)
    else:
        parser.print_help()
        raise SystemExit(1)


if __name__ == "__main__":
    main()
