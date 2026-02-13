"""
report_usage.py
LLM 사용량 집계 보고서 (logs/llm_usage.jsonl 기반)

실행:
  cd agent_factory
  python scripts/report_usage.py
  python scripts/report_usage.py --days 7
  python scripts/report_usage.py --today
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
_USAGE_LOG = Path(_PROJECT_ROOT) / "logs" / "llm_usage.jsonl"


def load_entries(log_path: Path, since: datetime = None) -> list:
    """JSONL 로그 파일에서 엔트리 로드."""
    if not log_path.is_file():
        return []
    entries = []
    for line in log_path.read_text(encoding="utf-8").strip().splitlines():
        try:
            entry = json.loads(line)
            if since:
                ts = entry.get("timestamp", "")
                if ts < since.strftime("%Y-%m-%dT%H:%M:%SZ"):
                    continue
            entries.append(entry)
        except json.JSONDecodeError:
            continue
    return entries


def aggregate(entries: list) -> dict:
    """집계 통계 생성."""
    if not entries:
        return {"total": 0, "message": "로그 데이터 없음"}

    total = len(entries)
    success = sum(1 for e in entries if e.get("success"))
    fail = total - success

    # 모델별 호출 수
    by_model = defaultdict(int)
    by_provider = defaultdict(int)
    by_tier = defaultdict(int)
    by_task = defaultdict(int)
    by_day = defaultdict(int)

    latencies = []
    failover_total = 0
    escalated_total = 0

    for e in entries:
        model = e.get("model", "unknown")
        provider = e.get("provider", "unknown")
        tier = e.get("tier", "unknown")
        task = e.get("task_class", "unknown")
        day = e.get("timestamp", "")[:10]

        by_model[model] += 1
        by_provider[provider] += 1
        by_tier[tier] += 1
        by_task[task] += 1
        by_day[day] += 1

        lat = e.get("latency_ms", 0)
        if lat > 0:
            latencies.append(lat)
        failover_total += e.get("failover_count", 0)
        if e.get("escalated"):
            escalated_total += 1

    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

    return {
        "total": total,
        "success": success,
        "fail": fail,
        "success_rate": f"{success / total * 100:.1f}%" if total else "N/A",
        "avg_latency_ms": round(avg_latency),
        "p95_latency_ms": p95_latency,
        "total_failovers": failover_total,
        "total_escalations": escalated_total,
        "by_provider": dict(sorted(by_provider.items(), key=lambda x: -x[1])),
        "by_model": dict(sorted(by_model.items(), key=lambda x: -x[1])),
        "by_tier": dict(sorted(by_tier.items(), key=lambda x: -x[1])),
        "by_task_class": dict(sorted(by_task.items(), key=lambda x: -x[1])),
        "by_day": dict(sorted(by_day.items())),
    }


def print_report(stats: dict):
    """보고서 출력."""
    print("=" * 60)
    print(" JH Agent Factory — LLM 사용량 보고서")
    print("=" * 60)

    if stats.get("message"):
        print(f"\n  {stats['message']}")
        return

    print(f"\n  총 호출: {stats['total']}회")
    print(f"  성공: {stats['success']}회  |  실패: {stats['fail']}회  |  성공률: {stats['success_rate']}")
    print(f"  평균 지연: {stats['avg_latency_ms']}ms  |  P95 지연: {stats['p95_latency_ms']}ms")
    print(f"  총 장애전환: {stats['total_failovers']}회  |  총 승격: {stats['total_escalations']}회")

    print("\n--- 프로바이더별 ---")
    for k, v in stats["by_provider"].items():
        pct = v / stats["total"] * 100
        bar = "#" * int(pct / 2)
        print(f"  {k:20s} {v:4d}회 ({pct:5.1f}%) {bar}")

    print("\n--- 티어별 ---")
    for k, v in stats["by_tier"].items():
        pct = v / stats["total"] * 100
        print(f"  {k:12s} {v:4d}회 ({pct:5.1f}%)")

    print("\n--- 작업분류별 ---")
    for k, v in stats["by_task_class"].items():
        print(f"  {k:16s} {v:4d}회")

    if stats["by_day"]:
        print("\n--- 일별 호출수 ---")
        for day, count in stats["by_day"].items():
            bar = "#" * min(count, 50)
            print(f"  {day} {count:4d}회 {bar}")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="LLM 사용량 집계 보고서")
    parser.add_argument("--days", type=int, default=0, help="최근 N일 데이터만 (0=전체)")
    parser.add_argument("--today", action="store_true", help="오늘 데이터만")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    since = None
    if args.today:
        since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    elif args.days > 0:
        since = datetime.now(timezone.utc) - timedelta(days=args.days)

    entries = load_entries(_USAGE_LOG, since)
    stats = aggregate(entries)

    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    else:
        print_report(stats)


if __name__ == "__main__":
    main()
