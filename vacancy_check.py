#!/usr/bin/env python3
"""Check whether hh.ru vacancies are still open, without logging in.

Why this exists: hh keeps an archived posting online, and its page always contains
the phrase "Вакансия в архиве" in the template, so a text search gives a false
answer. The reliable signal is the schema.org JobPosting block: `validThrough` is
the employer's deadline, and hh removes the block from postings it has closed.

Usage:
  python vacancy_check.py 139441388 139017091
  python vacancy_check.py https://hh.ru/vacancy/139441388 --json

Exit codes: 0 — every vacancy is open; 2 — bad arguments; 3 — the page could not
be fetched or parsed; 4 — at least one vacancy is closed or unknown.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
LD_JSON = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
ID_RE = re.compile(r"(\d{6,})")


def vacancy_id(value: str) -> str:
    match = ID_RE.search(value)
    if not match:
        raise ValueError(f"no vacancy id in {value!r}")
    return match.group(1)


def fetch(url: str, timeout: int = 25) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ru-RU,ru"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def parse_posting(page: str) -> dict | None:
    for raw in LD_JSON.findall(page):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == "JobPosting":
            return data
    return None


def to_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def check(vid: str, page: str | None = None, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    if page is None:
        page = fetch(f"https://hh.ru/vacancy/{vid}")
    posting = parse_posting(page)
    if posting is None:
        return {"id": vid, "status": "closed", "title": None, "valid_through": None,
                "date_posted": None, "note": "no JobPosting block: archived or removed"}
    deadline = to_datetime(posting.get("validThrough"))
    if deadline is None:
        status, note = "unknown", "no validThrough in the posting"
    elif deadline > now:
        status, note = "open", ""
    else:
        status, note = "closed", "validThrough has passed"
    employer = posting.get("hiringOrganization") or {}
    return {
        "id": vid,
        "status": status,
        "title": posting.get("title"),
        "employer": employer.get("name") if isinstance(employer, dict) else None,
        "valid_through": posting.get("validThrough"),
        "date_posted": posting.get("datePosted"),
        "note": note,
    }


def read_list(path: Path) -> list[str]:
    """Read ids or URLs from a text file: one per line, blank lines and # comments skipped."""
    entries = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        entries.append(stripped)
    return entries


def collect_ids(items: list[str]) -> tuple[list[str], list[str]]:
    """Turn raw input into unique vacancy ids, keeping the order. Returns (ids, rejected)."""
    ids: list[str] = []
    rejected: list[str] = []
    for item in items:
        try:
            vid = vacancy_id(item)
        except ValueError:
            rejected.append(item)
            continue
        if vid not in ids:
            ids.append(vid)
    return ids, rejected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check whether hh.ru vacancies are still open (validThrough from JSON-LD).")
    parser.add_argument("vacancies", nargs="*", help="vacancy ids or hh.ru URLs")
    parser.add_argument("--from-file", dest="from_file", metavar="PATH",
                        help="file with ids or URLs, one per line; blank lines and # comments ignored")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    items = list(args.vacancies)
    if args.from_file:
        path = Path(args.from_file)
        if not path.exists():
            print(f"error: no such file: {path}", file=sys.stderr)
            return 3
        try:
            items.extend(read_list(path))
        except (OSError, UnicodeDecodeError) as exc:
            print(f"error: cannot read {path}: {exc}", file=sys.stderr)
            return 3

    if not items:
        print("error: pass at least one vacancy id, or use --from-file", file=sys.stderr)
        return 2

    ids, rejected = collect_ids(items)
    if rejected:
        shown = ", ".join(repr(item) for item in rejected[:3])
        print(f"error: no vacancy id in {shown}", file=sys.stderr)
        return 2
    if not ids:
        print("error: the list is empty after removing comments", file=sys.stderr)
        return 2

    rows, failed = [], False
    for vid in ids:
        try:
            rows.append(check(vid))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            rows.append({"id": vid, "status": "unknown", "title": None,
                         "valid_through": None, "date_posted": None,
                         "note": f"fetch failed: {exc}"})
            failed = True

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
    else:
        for row in rows:
            deadline = (row["valid_through"] or "")[:10] or "—"
            title = (row["title"] or "")[:52]
            print(f"{row['status'].upper():8} {row['id']:>10}  {deadline:10}  {title}")
            if row["note"]:
                print(f"{'':8} {'':>10}  {row['note']}")

    if failed:
        return 3
    return 0 if all(row["status"] == "open" for row in rows) else 4


if __name__ == "__main__":
    raise SystemExit(main())
