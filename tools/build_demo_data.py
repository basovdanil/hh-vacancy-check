#!/usr/bin/env python3
"""Build docs/data.json for the demo page from live hh.ru pages.

Usage: python tools/build_demo_data.py [--ids 1 2 3] [--out docs/data.json]

The demo page is static, so it shows a snapshot generated here rather than
calling hh.ru from the browser (cross-origin requests to hh.ru are blocked).
The scheduled workflow reruns this weekly, so the snapshot does not go stale.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import vacancy_check as vc  # noqa: E402

DEFAULT_IDS = [
    "139441388",  # open at the time of writing
    "139528682",  # closed, deadline passed
    "139386982",
    "139578310",
    "137593872",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh the demo snapshot.")
    parser.add_argument("--ids", nargs="*", default=DEFAULT_IDS)
    parser.add_argument("--out", default="docs/data.json")
    args = parser.parse_args()

    items, failed = [], 0
    for vid in args.ids:
        try:
            row = vc.check(vid)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            row = {"id": vid, "status": "unknown", "title": None, "valid_through": None,
                   "date_posted": None, "note": f"fetch failed: {exc}"}
        row["url"] = f"https://hh.ru/vacancy/{vid}"
        items.append(row)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "hh.ru public vacancy page, schema.org JobPosting",
        "items": items,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{out}: {len(items)} vacancies, {failed} fetch errors")
    for row in items:
        print(f"  {row['status']:8} {row['id']} {(row['valid_through'] or '')[:10]:10} {row['title'] or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
