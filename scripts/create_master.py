"""
create_master.py
에이전트를 생성한다 (마스터 또는 워커).

실행:
  cd agent_factory
  python scripts/create_master.py                  # 마스터 생성 (기본)
  python scripts/create_master.py --id A0002       # 워커 생성
  python scripts/create_master.py --id A0002 --name 워커봇 --role data_analyst
"""

import argparse
import os
import sys

# 프로젝트 루트를 sys.path에 추가 (어디서 실행해도 import 가능하게)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _PROJECT_ROOT)

from core.agent_creator import create_agent


def main():
    parser = argparse.ArgumentParser(description="JH Agent Factory — 에이전트 생성")
    parser.add_argument("--id", default=None, help="A0001=마스터(기본), A0002+=워커")
    parser.add_argument("--name", default=None, help="에이전트 이름")
    parser.add_argument("--role", default=None, help="에이전트 역할")
    args = parser.parse_args()

    is_master = args.id is None or args.id == "A0001"
    name = args.name or ("춘식이" if is_master else "워커")
    role = args.role or ("master_controller" if is_master else "general")
    label = "마스터" if is_master else "워커"

    print("=" * 56)
    print(f"  JH AGENT FACTORY — {label} 에이전트 생성")
    print("=" * 56)
    print()

    try:
        profile = create_agent(
            name=name,
            role=role,
            is_master=is_master,
        )
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    agent_id = profile["agent_id"]
    agent_dir = os.path.join(_PROJECT_ROOT, "agents", agent_id)

    print(f"  [OK] {label} 에이전트 생성 완료")
    print(f"  ID     : {agent_id}")
    print(f"  이름   : {profile['name']}")
    print(f"  역할   : {profile['role']}")
    print(f"  레벨   : {profile['level']}")
    print(f"  상태   : {profile['status']}")
    print(f"  경로   : {agent_dir}")
    print()

    # 생성된 파일 확인
    print("  생성된 파일/폴더:")
    for root, dirs, files in os.walk(agent_dir):
        depth = root.replace(agent_dir, "").count(os.sep)
        indent = "    " + "  " * depth
        folder_name = os.path.basename(root)
        print(f"{indent}{folder_name}/")
        sub_indent = "    " + "  " * (depth + 1)
        for f in files:
            fpath = os.path.join(root, f)
            size = os.path.getsize(fpath)
            print(f"{sub_indent}{f}  ({size} bytes)")

    print()
    print("=" * 56)
    print(f"  {name} 탄생 완료!")
    print("=" * 56)


if __name__ == "__main__":
    main()
