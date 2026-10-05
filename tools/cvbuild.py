#!/usr/bin/env python3
"""Compile a tailored CV or cover letter and report only what is wrong with it.

Why this exists
---------------
Drafting a real application burned roughly fifteen compile-inspect-trim
cycles across three documents, because nothing told the drafter how long a
document could be until after it had been written and compiled, and because
inspecting the result meant rendering whole PDF pages into the conversation.

This tool collapses that loop:

  * it warns about length BEFORE compiling, against a budget measured from
    documents in this repo that actually hit their page target;
  * it runs the two LaTeX passes that page numbers and cross-references need
    (a single pass silently reports stale page counts - that bit us);
  * on overflow it prints ONLY the spilled page, never the whole document;
  * it runs the ATS text-layer checks with an encoding that works on this
    machine, which took three tries to discover by hand.

Usage
-----
    python tools/cvbuild.py cv/main_acme_role.tex
    python tools/cvbuild.py cover_letters/cover_acme_role.tex
    python tools/cvbuild.py cv/main_acme_role.tex --keywords posting_terms.txt
    python tools/cvbuild.py cv/main_acme_role.tex --budget 9400

Engine and page target are inferred from the directory (cv/ -> lualatex, 2
pages; cover_letters/ -> xelatex, 1 page) and can be overridden.

Exit code is 0 only when every check passes, so this is usable as a gate.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

# --- Budgets -----------------------------------------------------------------
# Body characters, measured between \begin{document} and \end{document} with
# comment lines stripped. Calibrated on this repo (see --calibrate, which
# re-derives these from whatever is currently on disk and hitting its target).
#
# The budget is a WARNING, not a limit: it says "this will probably overflow",
# which is the thing that is expensive to discover after the fact. Spanish and
# other Romance-language drafts run roughly 15% longer than English for the same
# content, so a draft over budget is not automatically wrong - it just needs the
# trim planned rather than discovered.
# Measured 2026-09-01 with --calibrate:
#   cv, plain section flow ....... 8,074 / 8,528 / 8,603 / 8,816 chars -> 2 pages
#                                  9,393 chars (main_example) -> 3 pages
#   cv, with \newpage splitting ... 9,642 chars -> 2 pages
#   cover letters ................. 3,075 / 3,392 chars -> 1 page
#
# STRUCTURE MOVES THE CEILING, so these are set for the plain flow. Putting an
# explicit \newpage between the last page-1 section and Professional Experience
# buys roughly 800 more characters, because it stops LaTeX half-filling page 1
# and orphaning a section heading at its foot. If a draft is over budget, that
# is the first thing to try - it is free, and it is what got a real pair of CVs down to
# two pages. Only then start cutting content.
DEFAULT_BUDGETS = {"cv": 8800, "cover_letters": 3400}

DEFAULT_ENGINES = {"cv": "lualatex", "cover_letters": "xelatex"}
DEFAULT_PAGES = {"cv": 2, "cover_letters": 1}

# pdftotext encodings to try, in the order that worked here. Xpdf 4.00 on this
# machine emits cp1252 bytes when asked for Latin1 and mis-labels UTF-8 output,
# so we ask for one and try to decode as several.
PDFTOTEXT_ENCODINGS = [("Latin1", "cp1252"), ("UTF-8", "utf-8"), ("Latin1", "latin-1")]

OK, BAD, WARN = "ok", "FAIL", "warn"


def kind_of(path: Path) -> str:
    for part in path.parts:
        if part in DEFAULT_ENGINES:
            return part
    return "cv"


def body_chars(tex: Path) -> int:
    """Characters between \\begin{document} and \\end{document}, comments stripped."""
    src = tex.read_text(encoding="utf-8")
    start = src.find(r"\begin{document}")
    end = src.find(r"\end{document}")
    if start == -1 or end == -1:
        return len(src)
    body = src[start + len(r"\begin{document}"):end]
    body = "\n".join(l for l in body.splitlines() if not l.lstrip().startswith("%"))
    return len(body)


def compile_tex(tex: Path, engine: str, passes: int = 2) -> tuple[int | None, list[str]]:
    """Run the engine `passes` times. Returns (page_count, error_lines)."""
    pages, errors = None, []
    for _ in range(passes):
        proc = subprocess.run(
            [engine, "-interaction=nonstopmode", tex.name],
            cwd=tex.parent, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        out = proc.stdout or ""
        errors = [l for l in out.splitlines() if l.startswith("!")]
        # TeX hard-wraps terminal lines at 79 columns, so with a long filename this line
        # arrives as "...pdf (1 pag" + newline + "e)." -- join the lines before matching.
        m = re.search(r"Output written on .*?\((\d+) pages?", re.sub(r"[\r\n]", "", out))
        if m:
            pages = int(m.group(1))
    return pages, errors


def extract_text(pdf: Path) -> str | None:
    """pdftotext -layout with an encoding that actually decodes on this machine."""
    if not shutil.which("pdftotext"):
        return None
    out = pdf.with_suffix(".cvbuild.txt")
    for enc_flag, py_enc in PDFTOTEXT_ENCODINGS:
        subprocess.run(
            ["pdftotext", "-layout", "-enc", enc_flag, str(pdf), str(out)],
            capture_output=True,
        )
        if not out.exists():
            continue
        try:
            text = out.read_text(encoding=py_enc)
        except UnicodeDecodeError:
            continue
        finally:
            pass
        out.unlink(missing_ok=True)
        # Reject a decode that produced replacement characters where accents live.
        if "�" not in text:
            return text
    out.unlink(missing_ok=True)
    return None


def page_text(pdf: Path, page: int) -> str:
    if not shutil.which("pdftotext"):
        return ""
    out = pdf.with_suffix(".cvbuild.page.txt")
    for enc_flag, py_enc in PDFTOTEXT_ENCODINGS:
        subprocess.run(
            ["pdftotext", "-layout", "-f", str(page), "-l", str(page),
             "-enc", enc_flag, str(pdf), str(out)],
            capture_output=True,
        )
        if not out.exists():
            continue
        try:
            text = out.read_text(encoding=py_enc)
        except UnicodeDecodeError:
            continue
        out.unlink(missing_ok=True)
        if "�" not in text:
            return text
    out.unlink(missing_ok=True)
    return ""


def ats_checks(text: str) -> list[tuple[str, str, str]]:
    """Text-layer checks an ATS parser would effectively be doing."""
    results = []

    cids = text.count("(cid:")
    results.append(("no (cid:) markers", OK if not cids else BAD,
                    "" if not cids else f"{cids} found - font lacks a Unicode map"))

    repl = text.count("�")
    results.append(("no replacement chars", OK if not repl else BAD,
                    "" if not repl else f"{repl} found"))

    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    phone = re.search(r"\+\d[\d\s()-]{7,}", text)
    results.append(("email as literal text", OK if email else BAD,
                    email.group(0) if email else "not in the text layer"))
    results.append(("phone as literal text", OK if phone else BAD,
                    phone.group(0).strip() if phone else "not in the text layer"))

    ranges = sorted(set(f"{a}-{b}" for a, b in re.findall(r"\b(\d{4})-(\d{4})\b", text)))
    results.append(("ASCII date ranges", OK if ranges else WARN,
                    ", ".join(ranges) if ranges else "none found - en-dashes do not parse"))

    return results


def keyword_coverage(text: str, kw_file: Path) -> tuple[list[str], list[str]]:
    terms = [l.strip() for l in kw_file.read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.startswith("#")]
    low = text.lower()
    hit = [t for t in terms if t.lower() in low]
    miss = [t for t in terms if t.lower() not in low]
    return hit, miss


def calibrate(repo: Path) -> None:
    """Re-derive budgets from documents currently on disk that hit their target."""
    print("Calibrating budgets from documents that hit their page target\n")
    for kind, target in DEFAULT_PAGES.items():
        rows = []
        for tex in sorted((repo / kind).glob("*.tex")):
            pdf = tex.with_suffix(".pdf")
            if not pdf.exists():
                continue
            pages, _ = compile_tex(tex, DEFAULT_ENGINES[kind], passes=1)
            if pages is None:
                continue
            rows.append((body_chars(tex), pages, tex.name))
        good = [c for c, p, _ in rows if p == target]
        for chars, pages, name in sorted(rows):
            flag = "<- at target" if pages == target else ""
            print(f"  {kind:14} {chars:6,} chars  {pages} pages  {name} {flag}")
        if good:
            print(f"  => suggested {kind} budget: {max(good):,}\n")
        else:
            print(f"  => no {kind} document currently hits {target} pages\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tex", nargs="?", type=Path)
    ap.add_argument("--pages", type=int, help="expected page count")
    ap.add_argument("--engine", help="lualatex / xelatex / other")
    ap.add_argument("--budget", type=int, help="body character warning threshold")
    ap.add_argument("--keywords", type=Path, help="file with one posting term per line")
    ap.add_argument("--no-ats", action="store_true")
    ap.add_argument("--keep", action="store_true", help="keep .aux/.log/.out")
    ap.add_argument("--calibrate", action="store_true",
                    help="re-derive budgets from this repo and exit")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parent.parent
    if args.calibrate:
        calibrate(repo)
        return 0
    if not args.tex:
        ap.error("a .tex path is required (or use --calibrate)")

    tex = args.tex.resolve()
    if not tex.exists():
        print(f"FAIL  no such file: {tex}")
        return 2

    kind = kind_of(tex.relative_to(repo) if tex.is_relative_to(repo) else tex)
    engine = args.engine or DEFAULT_ENGINES[kind]
    want_pages = args.pages if args.pages else DEFAULT_PAGES[kind]
    budget = args.budget if args.budget else DEFAULT_BUDGETS[kind]

    failures = 0
    print(f"\n{tex.name}   [{kind}, {engine}, target {want_pages}p]\n")

    # --- length, before spending a compile on it
    chars = body_chars(tex)
    over = chars - budget
    status = OK if over <= 0 else WARN
    note = f"budget {budget:,}" if over <= 0 else f"{over:,} over budget {budget:,} - expect overflow"
    print(f"  body        {chars:6,} chars   {status:4}  {note}")

    # --- compile
    pages, errors = compile_tex(tex, engine)
    if errors:
        print(f"  compile     {engine} x2      {BAD}")
        for e in errors[:5]:
            print(f"                {e}")
        failures += 1
    else:
        print(f"  compile     {engine} x2      {OK}")

    pdf = tex.with_suffix(".pdf")
    if pages is None:
        print(f"  pages       ?              {BAD}  no page count in the log")
        failures += 1
    elif pages == want_pages:
        print(f"  pages       {pages} / {want_pages}          {OK}")
    else:
        print(f"  pages       {pages} / {want_pages}          {BAD}")
        failures += 1
        for p in range(want_pages + 1, pages + 1):
            spill = [l for l in page_text(pdf, p).splitlines() if l.strip()]
            print(f"\n              page {p} holds ({len(spill)} lines) - trim about this much:")
            for line in spill[:14]:
                safe = line.strip()[:88].encode("ascii", "replace").decode("ascii")
                print(f"                {safe}")
            if len(spill) > 14:
                print(f"                ... +{len(spill) - 14} more lines")
            print()

    # --- ATS text layer
    if not args.no_ats and pdf.exists():
        text = extract_text(pdf)
        if text is None:
            print(f"  ats         skipped        {WARN}  pdftotext missing or no encoding decoded")
        else:
            bits = []
            for name, status, detail in ats_checks(text):
                if status == BAD:
                    failures += 1
                    print(f"  ats         {name:20} {BAD}  {detail}")
                else:
                    bits.append(name)
            if bits:
                print(f"  ats         {OK}    " + " | ".join(bits))

            if args.keywords and args.keywords.exists():
                hit, miss = keyword_coverage(text, args.keywords)
                total = len(hit) + len(miss)
                st = OK if not miss else WARN
                print(f"  keywords    {len(hit)}/{total}          {st}")
                for m in miss:
                    print(f"                missing: {m}")

    if not args.keep:
        for ext in (".aux", ".log", ".out"):
            tex.with_suffix(ext).unlink(missing_ok=True)

    print()
    if failures:
        print(f"  {failures} check(s) failed\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
