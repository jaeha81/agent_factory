"""
create_master.py
춘식이 마스터 에이전트 1호를 생성한다.

실행:
  cd agent_factory
  python scripts/create_master.py
"""

import os
import sys

# 프로젝트 루트를 sys.path에 추가 (어디서 실행해도 import 가능하게)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _PROJECT_ROOT)

from core.agent_creator import create_agent


def main():
    print("=" * 56)
    print("  JH AGENT FACTORY — 마스터 에이전트 생성")
    print("=" * 56)
    print()

    try:
        profile = create_agent(
            name="춘식이",
            role="master_controller",
            is_master=True,
        )
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    agent_id = profile["agent_id"]
    agent_dir = os.path.join(_PROJECT_ROOT, "agents", agent_id)

    print(f"  [OK] 마스터 에이전트 생성 완료")
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
    print("  춘식이 1호 탄생 완료!")
    print("=" * 56)


if __name__ == "__main__":
    main()
