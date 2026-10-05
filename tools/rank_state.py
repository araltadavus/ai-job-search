#!/usr/bin/env python3
"""State helper for /rank: select candidates and write results back.

/rank reads the whole of seen_jobs.json into the model's context to filter it
by eye (Step 1), then re-emits the whole file to record scores (Step 4). That
cost is paid on every run regardless of how many jobs are actually scored, and
it grows for the life of the workspace, since seen_jobs.json is append-only by
design and most stored entries are `skipped`.

This moves the state-file traffic into code. Three subcommands:

  candidates   select the eligible entries for this run and project only the
               fields a scoring agent needs
  sweep        rule 6's expiry pass over entries this run did not re-score -
               a stored-date comparison, no fetch, no agent
  apply        write scoring results back to seen_jobs.json and print the
               ranked/vetoed/expired rows Step 5's report is built from

Selection and projection follow Step 1's existing rules exactly (status
filter, tracker exclusion, focus filter, `--limit`/`--all`); the write-back
follows Step 4's existing rules exactly (the `location` -> `location_verdict`
legacy migration, the deadline null-is-not-a-correction rule, verbatim
strengths/gaps persistence, idempotent skip of already-ranked entries); the
sweep follows rule 6 exactly (defensive date parsing, an absent deadline left
alone, `--all` making a retired entry revivable).

Nothing here fetches a posting or judges a fit. Scoring stays with the model;
this only removes the state file from the conversation.

`apply` also enforces Step 4's guards, each of which exists because prose in
rank.md did not stop the failure it prevents:

  * an all-failed batch (5+ results, every one `expired`/`unknown`) is the
    signature of fetch throttling, not of that many dead postings - it is
    refused and nothing is written, unless `--force-expired` says a second
    spaced attempt confirmed it;
  * a failed retrieval (`unknown`) never destroys an existing ranking;
  * a score is never written without the rubric it was produced under
    (`--rubric`, the `framework_version` in 04-job-evaluation.md);
  * the store is copied to `seen_jobs.<date>.bak.json` before the first real
    write of the day.

Usage:
  python3 tools/rank_state.py candidates [--all] [--focus TEXT] [--limit N]
  python3 tools/rank_state.py sweep [--write] [--exclude KEY,KEY]
  python3 tools/rank_state.py apply --results results.json --rubric VERSION
                                    [--scope-note TEXT] [--force-expired] [--dry-run]

Every subcommand prints JSON on stdout. Exit 0 on success, 1 on a usage or
state error, or on `apply` when any result could not be written; 3 when
`apply` refuses an all-failed batch (nothing written).
"""

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import unicodedata
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "job_scraper" / "seen_jobs.json"
TRACKER = ROOT / "job_search_tracker.csv"

# 04-job-evaluation.md
WEIGHTS = {"technical": 0.30, "experience": 0.25, "behavioral": 0.15, "career": 0.30}
BANDS = ((75, "Strong Fit"), (60, "Good Fit"), (45, "Moderate Fit"), (30, "Weak Fit"), (0, "Poor Fit"))

DEFAULT_LIMIT = 10
URGENT_DAYS = 7
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Statuses a run selects by default. `unknown` is a fetch that failed, not a
# verdict - the question is still open, so the next run asks it again.
OPEN_STATUSES = ("new", "unknown")

# Result statuses Step 2's scoring agents may return. An absent status is
# read as "scored" for results written before the field existed.
RESULT_STATUSES = ("scored", "expired", "unknown")

# Step 2's decision fields, persisted verbatim when a result carries them.
# Never `location`: on an entry that key is the scraper's place field.
DECISION_FIELDS = ("visa", "visa_note", "portfolio_required", "still_open", "band", "language")

# Smallest batch the all-failed guard applies to. Measured 28 Aug 2026: 30
# rapid fetches failed 30/30 while a posting verified live minutes earlier
# was among them - a throttled client, not 30 dead postings.
ALL_FAILED_MIN_BATCH = 5
REFUSED_EXIT = 3


def load_state(path: Path) -> tuple[dict, dict]:
    """Return (document, seen-map). The map is mutated in place by callers."""
    if not path.is_file():
        sys.exit(f"{path} not found - run /scrape first")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"{path} is not valid JSON: {exc}")
    seen = doc.get("seen") if isinstance(doc, dict) and "seen" in doc else doc
    if not isinstance(seen, dict):
        sys.exit(f"{path}: expected an object of job entries")
    return doc, seen


def save_state(path: Path, doc: dict) -> None:
    """Atomic replace: a half-written seen_jobs.json loses the scrape history."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".seen_jobs.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def parse_iso(value) -> date | None:
    """Rule 6's defensive-parse rule: anything that is not YYYY-MM-DD is treated
    exactly like an absent value - never compared, never guessed at."""
    if not isinstance(value, str) or not ISO.match(value.strip()):
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def norm(text) -> str:
    """Ignore case and separators without discarding non-Latin identity."""
    text = unicodedata.normalize("NFC", str(text or "").casefold())
    # Combining marks can distinguish names even after NFC (e.g. Indic vowels).
    return "".join(
        char for char in text
        if char.isalnum() or unicodedata.category(char).startswith("M")
    )


def tracker_pairs(path: Path) -> set[tuple[str, str]]:
    """company+role pairs already in the tracker - out of scope for ranking."""
    if not path.is_file():
        return set()
    import csv

    pairs = set()
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            company, role = norm(row.get("company")), norm(row.get("role"))
            if company:
                pairs.add((company, role))
    return pairs


def entry_location_verdict(entry: dict) -> str | None:
    """location_verdict, falling back to a legacy verdict stored under `location`
    (Step 4: "an entry ranked before this rename may carry a legacy PASS/FAIL/
    FLAG string in `location`")."""
    verdict = entry.get("location_verdict")
    if verdict:
        return verdict
    legacy = entry.get("location")
    return legacy if legacy in ("PASS", "FAIL", "FLAG") else None


def cmd_candidates(args) -> int:
    _, seen = load_state(args.state)
    excluded = tracker_pairs(args.tracker)

    selected, skipped_tracker = [], 0
    for key, entry in seen.items():
        status = entry.get("status")
        if args.all:
            if status == "skipped":
                continue
        elif status not in OPEN_STATUSES:
            continue
        if (norm(entry.get("company")), norm(entry.get("title"))) in excluded:
            skipped_tracker += 1
            continue
        if args.focus:
            haystack = " ".join(
                [str(entry.get("title") or ""), str(entry.get("company") or "")]
                + [str(b) for b in entry.get("strengths") or []]
                + [str(b) for b in entry.get("gaps") or []]
            ).lower()
            if args.focus.lower() not in haystack:
                continue
        selected.append(
            {
                "key": key,
                "title": entry.get("title"),
                "company": entry.get("company"),
                "url": entry.get("url"),
                "portal": entry.get("portal"),
                "deadline": entry.get("deadline"),
                "posted_date": entry.get("posted_date"),
            }
        )

    eligible = len(selected)
    if args.limit > 0:
        selected = selected[: args.limit]
    print(
        json.dumps(
            {
                "eligible": eligible,
                "selected": selected,
                "deferred": max(0, eligible - len(selected)),
                "excluded_by_tracker": skipped_tracker,
                "total_entries": len(seen),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def cmd_sweep(args) -> int:
    doc, seen = load_state(args.state)
    today = args.today
    exclude = {k for k in (args.exclude or "").split(",") if k}

    expired, closing, unparseable, checked = [], [], [], 0
    for key, entry in seen.items():
        if entry.get("status") != "ranked" or key in exclude:
            continue
        checked += 1
        raw = entry.get("deadline")
        if raw in (None, ""):
            continue
        parsed = parse_iso(raw)
        if parsed is None:
            unparseable.append({"key": key, "portal": entry.get("portal"), "deadline": raw})
            continue
        row = {
            "key": key,
            "title": entry.get("title"),
            "company": entry.get("company"),
            "url": entry.get("url"),
            "deadline": raw,
        }
        if parsed < today:
            expired.append(row)
        elif (parsed - today).days <= URGENT_DAYS:
            closing.append(row)

    if args.write and expired:
        for row in expired:
            seen[row["key"]]["status"] = "expired"
        save_state(args.state, doc)

    print(
        json.dumps(
            {
                "swept": checked,
                "newly_expired": expired,
                "closing_soon": sorted(closing, key=lambda r: r["deadline"]),
                "unparseable_deadlines": unparseable,
                "written": bool(args.write and expired),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def overall_score(scores: dict) -> int:
    total = 0.0
    for dim, weight in WEIGHTS.items():
        value = scores.get(dim)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"missing or non-numeric score '{dim}'")
        if not 0 <= value <= 100:
            raise ValueError(f"score '{dim}' must be finite and between 0 and 100")
        total += float(value) * weight
    return int(total + 0.5)


def band(score: int) -> str:
    for floor, name in BANDS:
        if score >= floor:
            return name
    return "Poor Fit"


def result_status(result: dict):
    """A result's status; absent (or null) reads as "scored" for compatibility."""
    status = result.get("status")
    return "scored" if status is None else status


def all_failed_refusal(results: list) -> dict | None:
    """Guard: an all-failed batch is a throttling signal, not a finding."""
    statuses = [result_status(r) if isinstance(r, dict) else None for r in results]
    expired, unknown = statuses.count("expired"), statuses.count("unknown")
    if len(results) < ALL_FAILED_MIN_BATCH or expired + unknown != len(results):
        return None
    return {
        "reason": "all_failed_batch",
        "batch": len(results),
        "expired": expired,
        "unknown": unknown,
        "message": (
            f"refused: every one of {len(results)} results is expired or unknown. That is the "
            f"signature of fetch throttling, not of {len(results)} dead postings - on 28 Aug 2026 "
            "30/30 rapid fetches failed while a posting verified live minutes earlier was among "
            "them. Writing this batch would mark live roles expired, permanently, and nothing "
            "re-checks an expired entry. Nothing was written. Back off, retry the slice spaced "
            "out, and re-run; pass --force-expired only after a second spaced attempt confirmed "
            "the postings really are gone."
        ),
    }


def cmd_apply(args) -> int:
    rubric = args.rubric.strip()
    if not rubric:
        sys.exit("--rubric must name the framework_version the scores were produced under")
    doc, seen = load_state(args.state)
    today = args.today
    try:
        results = json.loads(Path(args.results).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.exit(f"cannot read results file {args.results}: {exc}")
    if isinstance(results, dict):
        results = results.get("results", [])
    if not isinstance(results, list):
        sys.exit("results file must be a JSON array of scoring objects")

    refusal = None if args.force_expired else all_failed_refusal(results)
    if refusal:
        print(refusal["message"], file=sys.stderr)
        print(json.dumps({"refused": refusal, "written": False}, indent=2, ensure_ascii=False))
        return REFUSED_EXIT

    rows, expired, unknown, errors = [], [], [], []
    for result in results:
        if not isinstance(result, dict):
            errors.append({"key": None, "error": "result is not a JSON object"})
            continue
        key = result.get("key")
        entry = seen.get(key)
        if entry is None:
            errors.append({"key": key, "error": "no such key in seen_jobs.json"})
            continue

        status = result_status(result)
        if status not in RESULT_STATUSES:
            errors.append(
                {"key": key, "error": f"unusable status {status!r} - expected one of {', '.join(RESULT_STATUSES)}"}
            )
            continue

        if status == "unknown":
            # Never destroy a real score with a failed retrieval, and never
            # promote unknown to expired: the question is still open. The
            # reverse holds too - a failed fetch adds nothing to a confirmed
            # expiry, and reopening it would re-fetch a dead posting every run.
            prior = entry.get("status")
            kept = prior in ("ranked", "expired")
            if not kept:
                entry["status"] = "unknown"
                entry["last_fetch_failed"] = today.isoformat()
            unknown.append(
                {
                    "key": key,
                    "title": entry.get("title"),
                    "company": entry.get("company"),
                    "url": entry.get("url"),
                    "kept_status": prior if kept else None,
                    "kept_existing_score": prior == "ranked",
                    "rank_score": entry.get("rank_score") if prior == "ranked" else None,
                }
            )
            continue

        if status == "expired":
            entry["status"] = "expired"
            entry["expired_confirmed"] = today.isoformat()
            expired.append(
                {"key": key, "title": entry.get("title"), "company": entry.get("company"), "url": entry.get("url")}
            )
            continue

        try:
            score = overall_score(result.get("scores") or {})
        except ValueError as exc:
            errors.append({"key": key, "error": str(exc)})
            continue

        legacy = entry_location_verdict(entry)
        if entry.get("location") in ("PASS", "FAIL", "FLAG"):
            entry.pop("location", None)  # legacy verdict, never a place
        entry["status"] = "ranked"
        entry["rank_score"] = score
        entry["rank_verdict"] = band(score)
        entry["rank_date"] = today.isoformat()
        entry["rubric"] = rubric
        entry.pop("last_fetch_failed", None)  # this fetch succeeded
        entry.pop("rank_scope_note", None)  # it was looked at after all
        entry["location_verdict"] = result.get("location_verdict") or legacy or "PASS"
        entry["language_gate"] = result.get("language_gate") or "PASS"
        if entry["language_gate"] == "PASS":
            entry.pop("language_note", None)
        else:
            entry["language_note"] = result.get("language_note")
        # Absence is not a correction: a fetch that degraded to a listing page
        # returns no deadline, and blanking a stored one would erase a real
        # date and make the entry immortal to rule 6's sweep.
        if result.get("deadline"):
            entry["deadline"] = result["deadline"]
        for field in ("strengths", "gaps"):
            value = result.get(field)
            if isinstance(value, list):
                entry[field] = [str(b) for b in value][:3]
        for field in DECISION_FIELDS:
            if field in result:
                entry[field] = result[field]

        parsed = parse_iso(entry.get("deadline"))
        rows.append(
            {
                "key": key,
                "title": entry.get("title"),
                "company": entry.get("company"),
                "location": entry.get("location"),
                "url": entry.get("url"),
                "score": score,
                "verdict": entry["rank_verdict"],
                "location_verdict": entry["location_verdict"],
                "language_gate": entry["language_gate"],
                "language_note": entry.get("language_note"),
                "visa": entry.get("visa"),
                "band": entry.get("band"),
                "deadline": entry.get("deadline"),
                "posted_date": entry.get("posted_date"),
                "urgent": bool(parsed and today <= parsed <= today + timedelta(days=URGENT_DAYS)),
                "strengths": entry.get("strengths", []),
                "gaps": entry.get("gaps", []),
            }
        )

    # Record what this run deliberately did not rank, so "never looked at"
    # stays distinguishable from "scored low".
    if args.scope_note:
        note = f"{today.isoformat()}: {args.scope_note}"
        for entry in seen.values():
            if entry.get("status") == "new":
                entry["rank_scope_note"] = note

    stale_rubric = sum(
        1 for entry in seen.values() if entry.get("status") == "ranked" and entry.get("rubric") != rubric
    )

    backup = None
    if not args.dry_run:
        backup = args.state.with_name(f"{args.state.stem}.{today.isoformat()}.bak.json")
        if not backup.exists():
            shutil.copy2(args.state, backup)  # the store as it was before the day's first write
        save_state(args.state, doc)

    rows.sort(key=lambda r: (r["score"], r["urgent"]), reverse=True)
    veto = lambda r: r["location_verdict"] == "FAIL" or r["language_gate"] == "FAIL"
    vetoed = [r for r in rows if veto(r)]
    ranked = [r for r in rows if not veto(r)]
    print(
        json.dumps(
            {
                "ranked": ranked,
                "vetoed": vetoed,
                "expired": expired,
                "unknown": unknown,
                "errors": errors,
                "rubric": rubric,
                "stale_rubric": stale_rubric,
                "written": not args.dry_run,
                "backup": backup.name if backup else None,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 1 if errors else 0


def _force_utf8_output() -> None:
    """Write UTF-8 whatever the host's default encoding is.

    A piped stdout on Windows defaults to the ANSI code page (cp1252 on most
    Western installs), so printing a company, title or file name outside it
    raised UnicodeEncodeError before the workflow saw any output.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)  # absent on a StringIO under test
        if reconfigure:
            reconfigure(encoding="utf-8")


def main() -> int:
    _force_utf8_output()
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--state", type=Path, default=STATE)
    common.add_argument("--today", type=date.fromisoformat, default=date.today())

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)

    cand = sub.add_parser("candidates", parents=[common], help="select the entries to score")
    cand.add_argument("--tracker", type=Path, default=TRACKER)
    cand.add_argument("--all", action="store_true", help="include every non-skipped status")
    cand.add_argument("--focus", help="substring filter over title, company and stored fit notes")
    cand.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="0 for no cap")
    cand.set_defaults(func=cmd_candidates)

    sweep = sub.add_parser("sweep", parents=[common], help="rule 6's expiry pass, no fetch")
    sweep.add_argument("--write", action="store_true", help="persist the expiries")
    sweep.add_argument("--exclude", help="comma-separated keys re-scored this run")
    sweep.set_defaults(func=cmd_sweep)

    app = sub.add_parser("apply", parents=[common], help="write scoring results back and print the ranking")
    app.add_argument("--results", required=True, help="JSON array from the scoring agents")
    app.add_argument(
        "--rubric", required=True, help="framework_version from 04-job-evaluation.md; stamped on every ranked entry"
    )
    app.add_argument("--scope-note", help="what this run deliberately did not rank, and why")
    app.add_argument(
        "--force-expired",
        action="store_true",
        help="override the all-failed-batch guard - only after a second, spaced attempt confirmed the postings are gone",
    )
    app.add_argument("--dry-run", action="store_true")
    app.set_defaults(func=cmd_apply)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
