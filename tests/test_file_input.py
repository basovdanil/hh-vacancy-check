"""Tests for the file input of vacancy_check: reading, dedup, comments, exit codes."""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import vacancy_check as vc  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def write_list(text: str) -> Path:
    handle = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    handle.write(text)
    handle.close()
    return Path(handle.name)


class ReadListTest(unittest.TestCase):
    def test_skips_blank_lines_and_comments(self):
        path = write_list(
            "# vacancies I applied to\n"
            "\n"
            "139441388\n"
            "  https://hh.ru/vacancy/139528682?query=x  \n"
            "   # trailing comment\n"
        )
        self.assertEqual(vc.read_list(path), ["139441388", "https://hh.ru/vacancy/139528682?query=x"])

    def test_empty_file_gives_empty_list(self):
        self.assertEqual(vc.read_list(write_list("\n\n# nothing\n")), [])

    def test_bom_is_tolerated(self):
        path = write_list("\ufeff139441388\n")
        self.assertEqual(vc.read_list(path), ["139441388"])


class CollectIdsTest(unittest.TestCase):
    def test_deduplicates_and_keeps_order(self):
        ids, rejected = vc.collect_ids(["139441388", "https://hh.ru/vacancy/139441388", "139528682"])
        self.assertEqual(ids, ["139441388", "139528682"])
        self.assertEqual(rejected, [])

    def test_rejects_garbage(self):
        ids, rejected = vc.collect_ids(["139441388", "not-a-vacancy"])
        self.assertEqual(ids, ["139441388"])
        self.assertEqual(rejected, ["not-a-vacancy"])


class MainWithFileTest(unittest.TestCase):
    def setUp(self):
        self.original = vc.fetch
        vc.fetch = lambda url, timeout=25: (FIXTURES / "open.html").read_text(encoding="utf-8")

    def tearDown(self):
        vc.fetch = self.original

    def _run(self, args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = vc.main(args)
        return code, buf.getvalue()

    def test_file_input_is_checked(self):
        path = write_list("139441388\n139528682\n")
        code, out = self._run(["--from-file", str(path)])
        self.assertEqual(code, 0)
        self.assertEqual(out.count("OPEN"), 2)

    def test_file_and_positional_are_merged(self):
        path = write_list("139441388\n")
        code, out = self._run(["--from-file", str(path), "139528682"])
        self.assertEqual(code, 0)
        self.assertEqual(out.count("OPEN"), 2)

    def test_missing_file_returns_three(self):
        code, _ = self._run(["--from-file", str(FIXTURES / "absent.txt")])
        self.assertEqual(code, 3)

    def test_empty_file_returns_two(self):
        code, _ = self._run(["--from-file", str(write_list("# only comments\n"))])
        self.assertEqual(code, 2)

    def test_no_arguments_returns_two(self):
        code, _ = self._run([])
        self.assertEqual(code, 2)

    def test_bad_line_returns_two(self):
        path = write_list("139441388\nhello\n")
        code, _ = self._run(["--from-file", str(path)])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
