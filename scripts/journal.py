"""Append evidence to history; update the current session and navigation explicitly."""

import argparse
from datetime import date, datetime

from index_files import write_indexes
from layout import ROOT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("message", help="actual result, failure or rollback, with evidence")
    parser.add_argument("--handoff", action="store_true")
    parser.add_argument("--next", help="remaining work and decisions")
    args = parser.parse_args()
    if args.handoff and not args.next:
        parser.error("--handoff requires --next")
    directory = ROOT / "docs/04-progress"
    journal = directory / (date.today().isoformat() + "-complete-engineering.md")
    if not journal.exists():
        journal.write_text("# 工程进度记录\n", encoding="utf-8")
    with journal.open("a", encoding="utf-8") as stream:
        stream.write(f"\n- {datetime.now().isoformat(timespec='minutes')} {args.message}\n")
    if args.handoff:
        (directory / "SESSION.md").write_text(
            "# SESSION — 当前会话交接\n\n## 已完成\n\n"
            + args.message
            + "\n\n## 进行中\n\n以最新当日日志为准；没有证据不声明完成。\n\n## 下一步 + 待确认\n\n"
            + args.next
            + "\n",
            encoding="utf-8",
        )
        (ROOT / "MEMORY.md").write_text(
            "# System1 Ops 当前状态入口\n\n目标system1-ops；状态真源docs/04-progress/SESSION.md，过程/基线在该目录。\n\n"
            + args.next
            + "\n",
            encoding="utf-8",
        )
    write_indexes()
    print("Updated history/navigation" + (" and session/memory" if args.handoff else ""))


if __name__ == "__main__":
    main()
