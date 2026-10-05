"""Tests for tools/cvbuild.py's page-count read from the TeX log.

TeX hard-wraps its terminal output at 79 columns. With a long document
filename, the "Output written on <file>.pdf (N pages, ...)" line arrives
split mid-word ("(1 pag" + newline + "e)."), the page regex never matched,
and a correctly compiled one-page letter was reported as "no page count in
the log" - a FAIL on a document that was fine. compile_tex now joins the
log's lines before matching; these pin that.
"""
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import cvbuild  # noqa: E402


def fake_run(stdout):
    return mock.patch.object(
        subprocess, "run", return_value=SimpleNamespace(stdout=stdout, returncode=0)
    )


class CompileTexPageCount(unittest.TestCase):
    def test_reads_an_unwrapped_line(self):
        log = "This is XeTeX\nOutput written on cover_acme.pdf (1 page, 23456 bytes).\n"
        with fake_run(log):
            pages, errors = cvbuild.compile_tex(Path("cover_acme.tex"), "xelatex", passes=1)
        self.assertEqual(pages, 1)
        self.assertEqual(errors, [])

    def test_reads_a_line_wrapped_mid_word(self):
        long_name = "cover_some_company_senior_frontend_engineer_tech_lead"
        log = (
            "This is XeTeX\n"
            f"Output written on {long_name}.pdf (1 pag\n"
            "e).\n"
        )
        with fake_run(log):
            pages, _ = cvbuild.compile_tex(Path(f"{long_name}.tex"), "xelatex", passes=1)
        self.assertEqual(pages, 1)

    def test_reads_a_line_wrapped_with_crlf(self):
        log = "Output written on main_some_company_staff_engineer_role.pdf (2 pa\r\nges, 98765 bytes).\r\n"
        with fake_run(log):
            pages, _ = cvbuild.compile_tex(Path("main_x.tex"), "lualatex", passes=1)
        self.assertEqual(pages, 2)

    def test_error_lines_are_still_read_per_line(self):
        log = "! Paragraph ended before \\cventry was complete.\nOutput written on main_x.pdf (2 pages).\n"
        with fake_run(log):
            pages, errors = cvbuild.compile_tex(Path("main_x.tex"), "lualatex", passes=1)
        self.assertEqual(pages, 2)
        self.assertEqual(errors, ["! Paragraph ended before \\cventry was complete."])

    def test_no_output_line_means_no_page_count(self):
        with fake_run("! Emergency stop.\n"):
            pages, errors = cvbuild.compile_tex(Path("main_x.tex"), "lualatex", passes=1)
        self.assertIsNone(pages)
        self.assertEqual(errors, ["! Emergency stop."])


if __name__ == "__main__":
    unittest.main()
