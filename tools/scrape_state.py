#!/usr/bin/env python3
"""Keep /scrape's growing history out of the agent context.

Pass a JSON array of search hits to `candidates` before fetching details, then
pass the enriched entries to `store`. Both commands deduplicate against the
current history and tracker; `store` writes the history atomically.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

from job_key import make_key
from rank_state import STATE, TRACKER, _force_utf8_output, load_state, norm, save_state, tracker_pairs


def read_jobs(path: Path) -> list:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    if isinstance(data, dict):
        data = data.get("results")
    if not isinstance(data, list):
        raise ValueError("results must be a JSON array of jobs")
    return data


def identity(job: dict) -> tuple[str, tuple[str, str]]:
    for field in ("title", "company", "url"):
        if not isinstance(job.get(field), str) or not job[field].strip():
            raise ValueError(f"job needs a non-empty {field}")
    url = job["url"].strip()
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"job has an invalid posting URL: {url}")
    return url.rstrip("/"), (norm(job["company"]), norm(job["title"]))


def select(jobs: list, seen: dict, tracker: set, *, strict: bool = False) -> tuple[list[dict], dict]:
    # History and in-batch repeats match on URL only, never on company+title:
    # one employer posting the same title in two cities is sometimes one
    # requisition and sometimes two live roles, and only the description hash
    # tells them apart (job-scraper SKILL.md, "Collapsing genuine duplicates").
    # The tracker still matches on company+role - that is what it records.
    urls = set()
    for entry in seen.values():
        if not isinstance(entry, dict):
            raise ValueError("job_scraper/seen_jobs.json contains a non-object entry")
        if isinstance(entry.get("url"), str):
            urls.add(entry["url"].rstrip("/"))

    selected = []
    counts = {"already_seen": 0, "already_applied": 0, "repeated_in_batch": 0, "invalid": []}
    batch_urls = set()
    for index, job in enumerate(jobs):
        try:
            if not isinstance(job, dict):
                raise ValueError("job is not an object")
            url, pair = identity(job)
        except ValueError as exc:
            if strict:
                raise ValueError(f"job {index + 1}: {exc}") from exc
            counts["invalid"].append({"index": index, "error": str(exc)})
            continue
        if url in urls:
            counts["already_seen"] += 1
        elif pair in tracker:
            counts["already_applied"] += 1
        elif url in batch_urls:
            counts["repeated_in_batch"] += 1
        else:
            selected.append(job)
            batch_urls.add(url)
    return selected, counts


def storage_key(job: dict, seen: dict) -> str:
    """The canonical key, kept apart from a different posting that shares it.

    select() has already removed every same-URL hit, so a taken key here means
    a distinct posting with the same company and title. Keep both, keyed by a
    short hash of the URL - still a pure function of the posting.
    """
    key = make_key(job["company"], job["title"], job["url"])
    if key not in seen:
        return key
    suffixed = f"{key}-{hashlib.sha1(job['url'].rstrip('/').encode('utf-8')).hexdigest()[:8]}"
    if suffixed in seen:
        raise ValueError(f"canonical key already exists for another posting: {suffixed}")
    return suffixed


def run(args) -> int:
    if args.state.exists():
        doc, seen = load_state(args.state)
    else:
        doc = {"seen": {}}
        seen = doc["seen"]
    if args.command == "history":
        domain = (args.domain or "").lower().strip(".")
        if not args.portal or not domain:
            raise ValueError("history needs --portal and --domain")
        count = 0
        for entry in seen.values():
            if not isinstance(entry, dict):
                continue
            if entry.get("portal") == args.portal:
                count += 1
            elif not entry.get("portal"):
                url = entry.get("url")
                try:
                    host = (urlsplit(url if isinstance(url, str) else "").hostname or "").lower()
                except ValueError:
                    continue
                if host == domain or host.endswith("." + domain):
                    count += 1
        print(json.dumps({"portal": args.portal, "prior_entries": count}))
        return 0

    jobs = read_jobs(args.results)
    selected, counts = select(jobs, seen, tracker_pairs(args.tracker), strict=args.command == "store")
    if args.command == "candidates":
        print(json.dumps({"selected": selected, **counts}, ensure_ascii=False))
        return 0

    added = []
    for job in selected:
        for field in ("first_seen", "posted_date", "deadline", "fit", "status", "portal", "source"):
            if field not in job:
                raise ValueError(f"job needs {field} before storage")
        if job["fit"] not in ("high", "medium", "low") or job["status"] not in ("new", "skipped", "expired"):
            raise ValueError("job has an invalid fit or status")
        if job["source"] not in ("cli", "websearch") or not isinstance(job["portal"], str):
            raise ValueError("job has an invalid portal or source")
        key = storage_key(job, seen)
        seen[key] = job
        added.append(key)
    if selected:
        args.state.parent.mkdir(parents=True, exist_ok=True)
        save_state(args.state, doc)
    print(json.dumps({"added": added, **counts}, ensure_ascii=False))
    return 0


def main() -> int:
    _force_utf8_output()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("candidates", "store", "history"))
    parser.add_argument("--results", type=Path)
    parser.add_argument("--portal")
    parser.add_argument("--domain")
    args = parser.parse_args()
    args.state, args.tracker = STATE, TRACKER
    try:
        if args.command != "history" and args.results is None:
            parser.error("candidates and store need --results")
        return run(args)
    except ValueError as exc:
        print(f"scrape_state: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
