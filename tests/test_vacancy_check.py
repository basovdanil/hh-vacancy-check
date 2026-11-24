"""Tests for vacancy_check: parsing, status decision and exit codes (no network)."""

from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import vacancy_check as vc  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
NOW = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)


def page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class ParsingTest(unittest.TestCase):
    def test_extracts_jobposting(self):
        posting = vc.parse_posting(page("open.html"))
        self.assertIsNotNone(posting)
        self.assertEqual(posting["@type"], "JobPosting")
        self.assertEqual(posting["title"], "Аналитик данных")

    def test_returns_none_without_jobposting(self):
        self.assertIsNone(vc.parse_posting(page("archived.html")))

    def test_ignores_broken_json_ld(self):
        self.assertIsNone(vc.parse_posting('<script type="application/ld+json">{oops</script>'))

    def test_ignores_other_ld_types(self):
        html = ('<script type="application/ld+json">'
                '{"@type": "BreadcrumbList", "itemListElement": []}</script>')
        self.assertIsNone(vc.parse_posting(html))


class IdTest(unittest.TestCase):
    def test_accepts_bare_id(self):
        self.assertEqual(vc.vacancy_id("139441388"), "139441388")

    def test_accepts_url(self):
        self.assertEqual(vc.vacancy_id("https://hh.ru/vacancy/139441388?query=1"), "139441388")

    def test_rejects_garbage(self):
        with self.assertRaises(ValueError):
            vc.vacancy_id("not-a-vacancy")


class StatusTest(unittest.TestCase):
    def test_future_deadline_is_open(self):
        row = vc.check("111111", page("open.html"), now=NOW)
        self.assertEqual(row["status"], "open")
        self.assertEqual(row["employer"], "ROSSKO")

    def test_past_deadline_is_closed(self):
        row = vc.check("222222", page("expired.html"), now=NOW)
        self.assertEqual(row["status"], "closed")
        self.assertIn("validThrough", row["note"])

    def test_missing_block_is_closed(self):
        row = vc.check("333333", page("archived.html"), now=NOW)
        self.assertEqual(row["status"], "closed")
        self.assertIn("no JobPosting block", row["note"])

    def test_missing_deadline_is_unknown(self):
        row = vc.check("444444", page("no-deadline.html"), now=NOW)
        self.assertEqual(row["status"], "unknown")


class ExitCodeTest(unittest.TestCase):
    def _run(self, pages: dict[str, str], ids: list[str]):
        original = vc.fetch

        def fake_fetch(url: str, timeout: int = 25) -> str:
            vid = url.rsplit("/", 1)[-1]
            return pages[vid]

        vc.fetch = fake_fetch  # type: ignore[assignment]
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                code = vc.main(ids)
        finally:
            vc.fetch = original  # type: ignore[assignment]
        return code, buf.getvalue()

    def test_all_open_returns_zero(self):
        code, out = self._run({"111111": page("open.html")}, ["111111"])
        self.assertEqual(code, 0)
        self.assertIn("OPEN", out)

    def test_one_closed_returns_four(self):
        code, _ = self._run({"111111": page("open.html"), "222222": page("expired.html")},
                            ["111111", "222222"])
        self.assertEqual(code, 4)

    def test_fetch_failure_returns_three(self):
        original = vc.fetch

        def boom(url: str, timeout: int = 25) -> str:
            raise OSError("boom")

        vc.fetch = boom  # type: ignore[assignment]
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                code = vc.main(["111111"])
        finally:
            vc.fetch = original  # type: ignore[assignment]
        self.assertEqual(code, 3)

    def test_bad_argument_returns_two(self):
        code, _ = self._run({}, ["no-id"])
        self.assertEqual(code, 2)

    def test_json_output_is_parseable(self):
        code, out = self._run({"111111": page("open.html")}, ["111111", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data[0]["id"], "111111")
        self.assertEqual(data[0]["status"], "open")


if __name__ == "__main__":
    unittest.main()
