"""Tests for tools/rank_state.py - /rank's state helper (#395).

/rank used to pull the whole of seen_jobs.json through the model's context to
select candidates, then emit it back to record scores. That cost the whole
backlog per run no matter how few jobs were being scored, and it grew for the
life of the workspace. These pin the behaviour the three subcommands took
over: selection matches Step 1's existing rules, the sweep matches rule 6
exactly (including its two defensive-parse edge cases), and the write-back
matches Step 4's existing rules exactly - the location_verdict legacy
migration, the deadline null-is-not-a-correction rule, and verbatim
strengths/gaps persistence.
"""
import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "tools" / "rank_state.py"

TODAY = "2026-09-03"
RUBRIC = "1.2.7"
BACKUP_NAME = f"seen_jobs.{TODAY}.bak.json"
FIFTY = {"technical": 50, "experience": 50, "behavioral": 50, "career": 50}


def entry(**over):
    base = {
        "title": "SOC Analyst",
        "company": "Acme",
        "url": "https://example.com/job",
        "first_seen": "2026-08-30",
        "deadline": None,
        "status": "new",
        "portal": "linkedin-search",
    }
    base.update(over)
    return base


class RankStateCase(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.state = self.tmp / "seen_jobs.json"
        self.addCleanup(self._tmp.cleanup)

    def write_state(self, seen):
        self.state.write_text(json.dumps({"seen": seen}), encoding="utf-8")

    def run_raw(self, *args):
        return subprocess.run(
            [sys.executable, str(TOOL), *args, "--state", str(self.state), "--today", TODAY],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def run_tool(self, *args, expect=0):
        proc = self.run_raw(*args)
        self.assertEqual(proc.returncode, expect, proc.stderr)
        return json.loads(proc.stdout)

    def read_state(self):
        return json.loads(self.state.read_text(encoding="utf-8"))["seen"]


class Candidates(RankStateCase):
    def test_selects_only_new_entries_and_projects_a_compact_row(self):
        self.write_state(
            {
                "a": entry(),
                "b": entry(status="ranked", rank_score=70),
                "c": entry(status="skipped"),
                "d": entry(status="expired"),
            }
        )
        out = self.run_tool("candidates", "--tracker", str(self.tmp / "none.csv"))
        self.assertEqual([row["key"] for row in out["selected"]], ["a"])
        self.assertEqual(
            set(out["selected"][0]),
            {"key", "title", "company", "url", "portal", "deadline", "posted_date"},
            "the projection is the point: strengths/gaps and every other stored field "
            "stay on disk rather than entering the conversation",
        )

    def test_limit_defers_the_rest_and_reports_the_count(self):
        self.write_state({f"k{i}": entry(title=f"Role {i}") for i in range(25)})
        out = self.run_tool("candidates", "--limit", "10", "--tracker", str(self.tmp / "none.csv"))
        self.assertEqual(len(out["selected"]), 10)
        self.assertEqual(out["eligible"], 25)
        self.assertEqual(
            out["deferred"],
            15,
            "a backlog larger than the batch limit must be reported, not silently truncated - "
            "the user has to know a re-run continues it",
        )

    def test_limit_zero_means_no_cap(self):
        self.write_state({f"k{i}": entry(title=f"Role {i}") for i in range(15)})
        out = self.run_tool("candidates", "--limit", "0", "--tracker", str(self.tmp / "none.csv"))
        self.assertEqual(len(out["selected"]), 15)
        self.assertEqual(out["deferred"], 0)

    def test_tracker_pairs_are_excluded(self):
        self.write_state({"a": entry(company="Acme", title="SOC Analyst"), "b": entry(company="Other")})
        tracker = self.tmp / "tracker.csv"
        tracker.write_text("date,company,role\n2026-08-01,ACME,soc analyst\n", encoding="utf-8")
        out = self.run_tool("candidates", "--tracker", str(tracker))
        self.assertEqual([row["key"] for row in out["selected"]], ["b"])
        self.assertEqual(out["excluded_by_tracker"], 1)

    def test_tracker_exclusion_handles_utf8_bom_and_reordered_columns(self):
        self.write_state({"a": entry(company="Acme", title="SOC Analyst"), "b": entry(company="Other")})
        tracker = self.tmp / "tracker.csv"
        # A spreadsheet export can prepend a BOM to either matching column.
        for encoding in ("utf-8", "utf-8-sig"):
            for csv_text in (
                "date,company,role\r\n2026-08-01,ACME,soc analyst\r\n",
                "company,role,date\r\nACME,soc analyst,2026-08-01\r\n",
                "role,company,date\r\nsoc analyst,ACME,2026-08-01\r\n",
            ):
                with self.subTest(encoding=encoding, header=csv_text.splitlines()[0]):
                    tracker.write_bytes(csv_text.encode(encoding))
                    out = self.run_tool("candidates", "--tracker", str(tracker))
                    self.assertEqual([row["key"] for row in out["selected"]], ["b"])
                    self.assertEqual(out["excluded_by_tracker"], 1)

    def test_tracker_exclusion_preserves_unicode_identity(self):
        # Use the standard /outcome header and the real candidates CLI.
        header = (
            "date,company,sector,role,role_type,channel,status,contact_person,"
            "fit_rating,notes,cv_file,cover_letter_file,source,deadline"
        ).split(",")
        cases = (
            # Tracked company/role, candidate company/title, expected exclusion.
            ("Acme", "设计师", "Acme", "工程师", False),
            ("Acme", "工程师", "Acme", "工程师", True),
            ("腾讯", "Engineer", "腾讯", "Engineer", True),
            ("腾讯", "Engineer", "阿里巴巴", "Engineer", False),
            ("Компания", "Инженер", "КОМПАНИЯ", "ИНЖЕНЕР", True),
            ("Café", "Engineer", "Cafe\u0301", "Engineer", True),
            ("Straße", "Engineer", "STRASSE", "Engineer", True),
            ("कला Labs", "Engineer", "कल Labs", "Engineer", False),
            ("Acme, Inc.", "SOC Analyst", "ACME_INC", "soc-analyst", True),
        )
        tracker = self.tmp / "tracker.csv"
        for company, role, candidate_company, title, excluded in cases:
            with self.subTest(tracked=(company, role), candidate=(candidate_company, title)):
                self.write_state({
                    "candidate": entry(company=candidate_company, title=title),
                    "other": entry(company="Other", title="Untracked role"),
                })
                with tracker.open("w", encoding="utf-8", newline="") as fh:
                    writer = csv.DictWriter(fh, fieldnames=header)
                    writer.writeheader()
                    writer.writerow({"date": TODAY, "company": company, "role": role, "status": "applied"})
                out = self.run_tool("candidates", "--tracker", str(tracker))
                self.assertEqual(
                    [row["key"] for row in out["selected"]],
                    ["other"] if excluded else ["candidate", "other"],
                )
                self.assertEqual(out["excluded_by_tracker"], int(excluded))

    def test_focus_filters_on_title_company_and_stored_fit_notes(self):
        self.write_state(
            {
                "a": entry(title="Data Scientist"),
                "b": entry(title="SOC Analyst"),
                "c": entry(title="Engineer", strengths=["strong data science match"]),
            }
        )
        out = self.run_tool("candidates", "--focus", "data scien", "--tracker", str(self.tmp / "n.csv"))
        self.assertEqual(sorted(row["key"] for row in out["selected"]), ["a", "c"])

    def test_all_flag_includes_every_status_but_skipped(self):
        self.write_state(
            {
                "a": entry(status="ranked"),
                "b": entry(status="expired"),
                "c": entry(status="skipped"),
                "d": entry(status="new"),
            }
        )
        out = self.run_tool("candidates", "--all", "--tracker", str(self.tmp / "n.csv"))
        self.assertEqual(sorted(row["key"] for row in out["selected"]), ["a", "b", "d"])

    def test_unknown_entries_are_re_eligible_without_all(self):
        """A failed fetch is an open question, not a verdict: an `unknown` entry
        must come back on the next default run, or one throttled batch parks
        live postings where only `--all` would ever look at them again."""
        self.write_state(
            {
                "n": entry(),
                "u": entry(status="unknown", last_fetch_failed="2026-09-01"),
                "r": entry(status="ranked", rank_score=70),
                "x": entry(status="expired"),
            }
        )
        out = self.run_tool("candidates", "--tracker", str(self.tmp / "none.csv"))
        self.assertEqual(sorted(row["key"] for row in out["selected"]), ["n", "u"])

    def test_missing_state_file_exits_nonzero(self):
        proc = subprocess.run(
            [sys.executable, str(TOOL), "candidates", "--state", str(self.tmp / "nope.json"),
             "--tracker", str(self.tmp / "n.csv")],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("not found", proc.stderr + proc.stdout)


class Sweep(RankStateCase):
    def test_retires_past_deadlines_and_flags_the_closing_ones(self):
        self.write_state(
            {
                "past": entry(status="ranked", deadline="2026-09-01"),
                "soon": entry(status="ranked", deadline="2026-09-07"),
                "later": entry(status="ranked", deadline="2026-12-01"),
            }
        )
        out = self.run_tool("sweep", "--write")
        self.assertEqual([r["key"] for r in out["newly_expired"]], ["past"])
        self.assertEqual([r["key"] for r in out["closing_soon"]], ["soon"])
        self.assertEqual(self.read_state()["past"]["status"], "expired")
        self.assertEqual(self.read_state()["soon"]["status"], "ranked")

    def test_entries_without_a_deadline_are_left_alone(self):
        """The majority case. Inferring one from first_seen would retire jobs
        on a date nobody set."""
        self.write_state({"a": entry(status="ranked", deadline=None), "b": entry(status="ranked")})
        out = self.run_tool("sweep", "--write")
        self.assertEqual(out["newly_expired"], [])
        self.assertTrue(all(e["status"] == "ranked" for e in self.read_state().values()))

    def test_non_iso_deadlines_are_reported_not_compared(self):
        """Portals have shipped "ASAP", DD.MM.YYYY and free text into this field."""
        self.write_state(
            {
                "asap": entry(status="ranked", deadline="ASAP", portal="jobindex-search"),
                "euro": entry(status="ranked", deadline="31.08.2026", portal="jobbank-search"),
            }
        )
        out = self.run_tool("sweep", "--write")
        self.assertEqual(out["newly_expired"], [])
        self.assertEqual(
            sorted(r["portal"] for r in out["unparseable_deadlines"]),
            ["jobbank-search", "jobindex-search"],
            "a bad stored value is traced back to the portal that wrote it",
        )
        self.assertTrue(all(e["status"] == "ranked" for e in self.read_state().values()))

    def test_only_ranked_entries_are_swept_and_excluded_keys_are_skipped(self):
        self.write_state(
            {
                "new_past": entry(status="new", deadline="2026-09-01"),
                "rescored": entry(status="ranked", deadline="2026-09-01"),
                "other": entry(status="ranked", deadline="2026-09-01"),
            }
        )
        out = self.run_tool("sweep", "--write", "--exclude", "rescored")
        self.assertEqual([r["key"] for r in out["newly_expired"]], ["other"])
        self.assertEqual(out["swept"], 1)
        self.assertEqual(self.read_state()["new_past"]["status"], "new")

    def test_without_write_nothing_is_persisted(self):
        self.write_state({"past": entry(status="ranked", deadline="2026-09-01")})
        out = self.run_tool("sweep")
        self.assertEqual([r["key"] for r in out["newly_expired"]], ["past"])
        self.assertFalse(out["written"])
        self.assertEqual(self.read_state()["past"]["status"], "ranked")


class Apply(RankStateCase):
    def results(self, payload):
        path = self.tmp / "results.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return str(path)

    def test_weights_bands_and_persisted_fields(self):
        self.write_state({"a": entry()})
        out = self.run_tool(
            "apply",
            "--rubric",
            RUBRIC,
            "--results",
            self.results(
                [
                    {
                        "key": "a",
                        "status": "scored",
                        "scores": {"technical": 80, "experience": 60, "behavioral": 70, "career": 75},
                        "location_verdict": "PASS",
                        "language_gate": "PASS",
                        "deadline": "2026-09-05",
                        "strengths": ["s1", "s2"],
                        "gaps": ["g1"],
                    }
                ]
            ),
        )
        stored = self.read_state()["a"]
        # 80*.30 + 60*.25 + 70*.15 + 75*.30 = 72
        self.assertEqual(stored["rank_score"], 72)
        self.assertEqual(stored["rank_verdict"], "Good Fit")
        self.assertEqual(stored["status"], "ranked")
        self.assertEqual(stored["rank_date"], TODAY)
        self.assertEqual(stored["strengths"], ["s1", "s2"])
        self.assertEqual(stored["gaps"], ["g1"])
        self.assertEqual(stored["deadline"], "2026-09-05")
        self.assertTrue(out["ranked"][0]["urgent"], "a deadline inside 7 days carries the urgency marker")

    def test_expired_status_is_written_through(self):
        self.write_state({"a": entry()})
        out = self.run_tool("apply", "--rubric", RUBRIC, "--results", self.results([{"key": "a", "status": "expired"}]))
        self.assertEqual(self.read_state()["a"]["status"], "expired")
        self.assertEqual([r["key"] for r in out["expired"]], ["a"])

    def test_null_deadline_does_not_erase_a_stored_one(self):
        """Absence is not a correction: a fetch that degraded to a listing page
        returns no deadline, and blanking the stored date would also put the
        entry out of the sweep's reach forever."""
        self.write_state({"a": entry(deadline="2026-10-01")})
        self.run_tool(
            "apply",
            "--rubric",
            RUBRIC,
            "--results",
            self.results(
                [
                    {
                        "key": "a",
                        "status": "scored",
                        "scores": {"technical": 50, "experience": 50, "behavioral": 50, "career": 50},
                        "deadline": None,
                    }
                ]
            ),
        )
        self.assertEqual(self.read_state()["a"]["deadline"], "2026-10-01")

    def test_legacy_verdict_stored_under_location_is_migrated(self):
        self.write_state({"a": entry(location="FLAG")})
        self.run_tool(
            "apply",
            "--rubric",
            RUBRIC,
            "--results",
            self.results(
                [
                    {
                        "key": "a",
                        "status": "scored",
                        "scores": {"technical": 50, "experience": 50, "behavioral": 50, "career": 50},
                    }
                ]
            ),
        )
        stored = self.read_state()["a"]
        self.assertEqual(stored["location_verdict"], "FLAG")
        self.assertNotIn("location", stored, "a legacy verdict is moved, never left to read as a place")

    def test_a_real_place_in_location_survives(self):
        self.write_state({"a": entry(location="Athens, Greece")})
        self.run_tool(
            "apply",
            "--rubric",
            RUBRIC,
            "--results",
            self.results(
                [
                    {
                        "key": "a",
                        "status": "scored",
                        "scores": {"technical": 50, "experience": 50, "behavioral": 50, "career": 50},
                        "location_verdict": "PASS",
                    }
                ]
            ),
        )
        self.assertEqual(self.read_state()["a"]["location"], "Athens, Greece")

    def test_vetoed_rows_are_separated_from_the_ranking(self):
        self.write_state({"a": entry(), "b": entry(), "c": entry()})
        scores = {"technical": 90, "experience": 90, "behavioral": 90, "career": 90}
        out = self.run_tool(
            "apply",
            "--rubric",
            RUBRIC,
            "--results",
            self.results(
                [
                    {"key": "a", "status": "scored", "scores": scores, "location_verdict": "FAIL"},
                    {"key": "b", "status": "scored", "scores": scores, "language_gate": "FAIL",
                     "language_note": "requires fluent Polish"},
                    {"key": "c", "status": "scored", "scores": {"technical": 40, "experience": 40,
                                                                "behavioral": 40, "career": 40}},
                ]
            ),
        )
        self.assertEqual(sorted(r["key"] for r in out["vetoed"]), ["a", "b"])
        self.assertEqual([r["key"] for r in out["ranked"]], ["c"])
        self.assertEqual(self.read_state()["b"]["language_note"], "requires fluent Polish")

    def test_language_note_is_dropped_when_gate_passes(self):
        self.write_state({"a": entry(language_note="stale note from a prior run")})
        self.run_tool(
            "apply",
            "--rubric",
            RUBRIC,
            "--results",
            self.results(
                [
                    {
                        "key": "a",
                        "status": "scored",
                        "scores": {"technical": 50, "experience": 50, "behavioral": 50, "career": 50},
                        "language_gate": "PASS",
                    }
                ]
            ),
        )
        self.assertNotIn("language_note", self.read_state()["a"])

    def test_strengths_and_gaps_are_capped_and_stored_verbatim(self):
        self.write_state({"a": entry()})
        self.run_tool(
            "apply",
            "--rubric",
            RUBRIC,
            "--results",
            self.results(
                [
                    {
                        "key": "a",
                        "status": "scored",
                        "scores": {"technical": 50, "experience": 50, "behavioral": 50, "career": 50},
                        "strengths": ["one", "two", "three", "four"],
                        "gaps": ["<script>not sanitized on purpose, stored as plain data</script>"],
                    }
                ]
            ),
        )
        stored = self.read_state()["a"]
        self.assertEqual(len(stored["strengths"]), 3, "at most 3 bullets, matching the spec")
        self.assertEqual(
            stored["gaps"],
            ["<script>not sanitized on purpose, stored as plain data</script>"],
            "gaps are stored verbatim - untrusted data, never reformatted",
        )

    def test_all_replaces_rather_than_accumulates_arrays(self):
        self.write_state({"a": entry(status="ranked", strengths=["old strength"], gaps=["old gap"])})
        self.run_tool(
            "apply",
            "--rubric",
            RUBRIC,
            "--results",
            self.results(
                [
                    {
                        "key": "a",
                        "status": "scored",
                        "scores": {"technical": 50, "experience": 50, "behavioral": 50, "career": 50},
                        "strengths": ["new strength"],
                        "gaps": ["new gap"],
                    }
                ]
            ),
        )
        stored = self.read_state()["a"]
        self.assertEqual(stored["strengths"], ["new strength"])
        self.assertEqual(stored["gaps"], ["new gap"])

    def test_unknown_key_is_an_error_not_a_silent_drop(self):
        self.write_state({"a": entry()})
        out = self.run_tool(
            "apply", "--rubric", RUBRIC, "--results", self.results([{"key": "ghost", "status": "scored", "scores": {}}]), expect=1
        )
        self.assertEqual(out["errors"][0]["key"], "ghost")

    def test_missing_score_dimension_is_an_error(self):
        self.write_state({"a": entry()})
        out = self.run_tool(
            "apply",
            "--rubric",
            RUBRIC,
            "--results",
            self.results([{"key": "a", "status": "scored", "scores": {"technical": 80}}]),
            expect=1,
        )
        self.assertIn("experience", out["errors"][0]["error"])
        self.assertEqual(self.read_state()["a"]["status"], "new", "a rejected result never half-writes an entry")

    def test_dry_run_prints_but_never_writes(self):
        self.write_state({"a": entry()})
        self.run_tool(
            "apply",
            "--rubric",
            RUBRIC,
            "--results",
            self.results(
                [{"key": "a", "status": "scored",
                  "scores": {"technical": 50, "experience": 50, "behavioral": 50, "career": 50}}]
            ),
            "--dry-run",
        )
        self.assertEqual(self.read_state()["a"]["status"], "new")

    def test_invalid_scores_report_errors_without_changing_the_entry(self):
        dimensions = ("technical", "experience", "behavioral", "career")
        invalid = (-1, 101, True, False, float("nan"), float("inf"), -float("inf"), 10**400)
        for dimension in dimensions:
            for value in invalid:
                with self.subTest(dimension=dimension, value=value):
                    original = entry(status="ranked", rank_score=70, strengths=["keep"])
                    self.write_state({"a": original, "b": entry()})
                    scores = dict.fromkeys(dimensions, 50)
                    scores[dimension] = value
                    out = self.run_tool(
                        "apply", "--rubric", RUBRIC, "--results", self.results([
                            {"key": "a", "status": "scored", "scores": scores},
                            {"key": "b", "status": "scored", "scores": dict.fromkeys(dimensions, 80)},
                        ]), expect=1,
                    )
                    self.assertEqual(len(out["errors"]), 1)
                    self.assertEqual(out["errors"][0]["key"], "a")
                    self.assertIn(dimension, out["errors"][0]["error"])
                    self.assertEqual(self.read_state()["a"], original)
                    self.assertEqual([row["key"] for row in out["ranked"]], ["b"])
                    self.assertEqual(self.read_state()["b"]["rank_score"], 80)

    def test_score_boundaries_and_fractional_scores_remain_valid(self):
        for value, expected in ((0, 0), (100, 100), (72.5, 73)):
            with self.subTest(value=value):
                self.write_state({"a": entry()})
                out = self.run_tool("apply", "--rubric", RUBRIC, "--results", self.results([
                    {"key": "a", "status": "scored", "scores": dict.fromkeys(
                        ("technical", "experience", "behavioral", "career"), value)},
                ]))
                self.assertEqual(out["errors"], [])
                self.assertEqual(self.read_state()["a"]["rank_score"], expected)

    def test_re_scoring_an_already_ranked_job_is_idempotent(self):
        """Re-running /rank never re-scores an already-ranked job unless --all
        says so (Step 4), but if it does score one again, apply must produce
        the same result deterministically rather than accumulating state."""
        self.write_state({"a": entry(status="ranked", rank_score=40, strengths=["old"])})
        scores = {"technical": 90, "experience": 90, "behavioral": 90, "career": 90}
        self.run_tool(
            "apply", "--rubric", RUBRIC, "--results",
            self.results([{"key": "a", "status": "scored", "scores": scores, "strengths": ["new"]}]),
        )
        stored = self.read_state()["a"]
        self.assertEqual(stored["rank_score"], 90)
        self.assertEqual(stored["strengths"], ["new"])


class ApplyGuards(RankStateCase):
    """The write-back guards the fork's own merge tool carried, now in `apply`.

    Each one exists because prose in rank.md did not stop the failure it
    guards against: a throttled batch read as dead postings, a failed fetch
    erasing a real score, scores from two rubric generations interleaved with
    nothing on disk to tell them apart, and 285 postings skipped by judgement
    with no record that anyone chose to skip them.
    """

    def results(self, payload):
        path = self.tmp / "results.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return str(path)

    def apply(self, payload, *extra, expect=0):
        return self.run_tool("apply", "--rubric", RUBRIC, "--results", self.results(payload), *extra, expect=expect)

    def scored(self, key, **over):
        result = {"key": key, "status": "scored", "scores": dict(FIFTY)}
        result.update(over)
        return result

    # --- rubric -----------------------------------------------------------

    def test_rubric_is_required(self):
        self.write_state({"a": entry()})
        before = self.state.read_bytes()
        proc = self.run_raw("apply", "--results", self.results([self.scored("a")]))
        self.assertNotEqual(proc.returncode, 0, "a score without a rubric must be refused, not written")
        self.assertIn("--rubric", proc.stderr)
        self.assertEqual(self.state.read_bytes(), before)

    def test_blank_rubric_is_refused(self):
        self.write_state({"a": entry()})
        before = self.state.read_bytes()
        proc = self.run_raw("apply", "--rubric", "  ", "--results", self.results([self.scored("a")]))
        self.assertNotEqual(proc.returncode, 0, "a blank stamp is no stamp")
        self.assertEqual(self.state.read_bytes(), before)

    def test_rubric_is_stamped_on_every_entry_ranked_this_run(self):
        self.write_state({"a": entry(), "b": entry(status="ranked", rank_score=60, rubric="old"), "c": entry()})
        self.apply([self.scored("a"), self.scored("b"), {"key": "c", "status": "expired"}])
        stored = self.read_state()
        self.assertEqual(stored["a"]["rubric"], RUBRIC)
        self.assertEqual(stored["b"]["rubric"], RUBRIC, "a re-score replaces the old generation's stamp")
        self.assertNotIn("rubric", stored["c"], "only a score carries a rubric")

    def test_stale_rubric_counts_ranked_entries_on_another_or_no_rubric(self):
        self.write_state(
            {
                "old": entry(status="ranked", rank_score=70, rubric="1.0.0"),
                "none": entry(status="ranked", rank_score=70),
                "current": entry(status="ranked", rank_score=70, rubric=RUBRIC),
                "expired_old": entry(status="expired", rubric="1.0.0"),
                "fresh": entry(),
            }
        )
        out = self.apply([self.scored("fresh")])
        self.assertEqual(
            out["stale_rubric"],
            2,
            "both the other-generation entry and the unstamped one are not comparable to this run's scores; "
            "only ranked entries count",
        )

    # --- status vocabulary -------------------------------------------------

    def test_absent_status_is_treated_as_scored(self):
        self.write_state({"a": entry()})
        out = self.apply([{"key": "a", "scores": dict(FIFTY)}])
        self.assertEqual(self.read_state()["a"]["status"], "ranked")
        self.assertEqual([r["key"] for r in out["ranked"]], ["a"])

    def test_unrecognised_status_is_an_error_for_that_result_only(self):
        self.write_state({"a": entry(), "b": entry()})
        out = self.apply(
            [{"key": "a", "status": "pending", "scores": dict(FIFTY)}, self.scored("b")],
            expect=1,
        )
        self.assertEqual([e["key"] for e in out["errors"]], ["a"])
        self.assertIn("pending", out["errors"][0]["error"])
        self.assertEqual(self.read_state()["a"], entry(), "a malformed result never touches its entry")
        self.assertEqual(self.read_state()["b"]["status"], "ranked")

    # --- unknown / expired ----------------------------------------------------

    def test_unknown_on_an_unranked_entry_records_the_failed_fetch(self):
        self.write_state({"a": entry()})
        out = self.apply([{"key": "a", "status": "unknown"}])
        stored = self.read_state()["a"]
        self.assertEqual(stored["status"], "unknown")
        self.assertEqual(stored["last_fetch_failed"], TODAY)
        self.assertEqual(out["expired"], [], "unknown is never promoted to expired")
        self.assertEqual(len(out["unknown"]), 1)
        self.assertEqual(out["unknown"][0]["key"], "a")
        self.assertFalse(out["unknown"][0]["kept_existing_score"])
        self.assertEqual(out["unknown"][0]["url"], "https://example.com/job")

    def test_unknown_never_destroys_an_existing_ranking(self):
        ranked = entry(status="ranked", rank_score=81, rank_verdict="Strong Fit", rubric="1.0.0",
                       strengths=["keep me"], visa="OPEN")
        self.write_state({"a": ranked})
        out = self.apply([{"key": "a", "status": "unknown", "still_open": "unknown"}])
        self.assertEqual(self.read_state()["a"], ranked, "every field of a ranked entry survives a failed fetch")
        self.assertTrue(out["unknown"][0]["kept_existing_score"])
        self.assertEqual(out["unknown"][0]["rank_score"], 81)

    def test_unknown_never_reopens_a_confirmed_expiry(self):
        dead = entry(status="expired", expired_confirmed="2026-09-01")
        self.write_state({"a": dead})
        out = self.apply([{"key": "a", "status": "unknown"}])
        self.assertEqual(self.read_state()["a"], dead, "a failed fetch adds nothing to a confirmed expiry")
        self.assertEqual(out["unknown"][0]["kept_status"], "expired")
        self.assertFalse(out["unknown"][0]["kept_existing_score"])

    def test_a_later_successful_score_clears_the_failed_fetch_marker(self):
        self.write_state({"a": entry(status="unknown", last_fetch_failed="2026-09-01")})
        self.apply([self.scored("a")])
        stored = self.read_state()["a"]
        self.assertEqual(stored["status"], "ranked")
        self.assertNotIn("last_fetch_failed", stored, "the question the marker recorded is now answered")

    def test_expired_records_the_confirmation_date(self):
        self.write_state({"a": entry()})
        self.apply([{"key": "a", "status": "expired"}])
        stored = self.read_state()["a"]
        self.assertEqual(stored["status"], "expired")
        self.assertEqual(stored["expired_confirmed"], TODAY)

    # --- all-failed batch guard ---------------------------------------------

    def _all_failed_batch(self):
        keys = [f"k{i}" for i in range(5)]
        self.write_state({k: entry(title=f"Role {k}") for k in keys})
        return [{"key": k, "status": "expired" if i % 2 else "unknown"} for i, k in enumerate(keys)]

    def test_all_failed_batch_is_refused_and_nothing_is_written(self):
        """Measured 28 Aug 2026: 30/30 fetches failed, a posting verified live
        minutes earlier among them. Written, that batch marks live roles
        expired permanently."""
        payload = self._all_failed_batch()
        before = self.state.read_bytes()
        proc = self.run_raw("apply", "--rubric", RUBRIC, "--results", self.results(payload))
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotEqual(proc.returncode, 1, "a refusal is distinguishable from a per-result error")
        self.assertEqual(self.state.read_bytes(), before, "nothing may be written")
        self.assertFalse((self.tmp / BACKUP_NAME).exists(), "a refused run makes no backup either")
        out = json.loads(proc.stdout)
        self.assertFalse(out["written"])
        self.assertIn("throttl", out["refused"]["message"])
        self.assertIn("--force-expired", out["refused"]["message"])
        self.assertIn("throttl", proc.stderr)

    def test_all_failed_batch_is_refused_on_dry_run_too(self):
        payload = self._all_failed_batch()
        proc = self.run_raw("apply", "--rubric", RUBRIC, "--results", self.results(payload), "--dry-run")
        self.assertNotEqual(proc.returncode, 0, "the inspection pass must show the refusal the real run would hit")

    def test_force_expired_overrides_the_guard(self):
        payload = self._all_failed_batch()
        out = self.apply(payload, "--force-expired")
        self.assertTrue(out["written"])
        stored = self.read_state()
        self.assertEqual(stored["k1"]["status"], "expired")
        self.assertEqual(stored["k0"]["status"], "unknown")

    def test_guard_needs_a_batch_of_five(self):
        self.write_state({f"k{i}": entry() for i in range(4)})
        out = self.apply([{"key": f"k{i}", "status": "expired"} for i in range(4)])
        self.assertTrue(out["written"])
        self.assertEqual(len(out["expired"]), 4)

    def test_one_success_disarms_the_guard(self):
        self.write_state({f"k{i}": entry() for i in range(6)})
        payload = [{"key": f"k{i}", "status": "expired"} for i in range(5)] + [self.scored("k5")]
        out = self.apply(payload)
        self.assertTrue(out["written"])
        self.assertEqual(self.read_state()["k5"]["status"], "ranked")

    # --- backup ----------------------------------------------------------------

    def test_first_write_of_the_day_backs_up_the_store(self):
        self.write_state({"a": entry()})
        before = self.state.read_bytes()
        self.apply([self.scored("a")])
        backup = self.tmp / BACKUP_NAME
        self.assertTrue(backup.is_file())
        self.assertEqual(backup.read_bytes(), before, "the backup is the store as it was before this write")

    def test_an_existing_backup_is_never_overwritten(self):
        self.write_state({"a": entry(), "b": entry()})
        backup = self.tmp / BACKUP_NAME
        backup.write_text("earliest state of the day", encoding="utf-8")
        self.apply([self.scored("a")])
        self.apply([self.scored("b")])
        self.assertEqual(backup.read_text(encoding="utf-8"), "earliest state of the day")

    def test_dry_run_makes_no_backup(self):
        self.write_state({"a": entry()})
        self.apply([self.scored("a")], "--dry-run")
        self.assertFalse((self.tmp / BACKUP_NAME).exists())

    # --- scope note ---------------------------------------------------------------

    def test_scope_note_marks_what_was_left_unranked_and_clears_what_was_ranked(self):
        self.write_state(
            {
                "ranked_now": entry(rank_scope_note="2026-08-28: older note"),
                "left_new": entry(),
                "ranked_before": entry(status="ranked", rank_score=70),
                "skipped": entry(status="skipped"),
            }
        )
        self.apply([self.scored("ranked_now")], "--scope-note", "only remote roles; 3 international skipped")
        stored = self.read_state()
        self.assertNotIn("rank_scope_note", stored["ranked_now"])
        self.assertEqual(stored["left_new"]["rank_scope_note"], f"{TODAY}: only remote roles; 3 international skipped")
        self.assertNotIn("rank_scope_note", stored["ranked_before"])
        self.assertNotIn("rank_scope_note", stored["skipped"])

    def test_without_scope_note_nothing_is_marked(self):
        self.write_state({"a": entry(), "b": entry()})
        self.apply([self.scored("a")])
        self.assertNotIn("rank_scope_note", self.read_state()["b"])

    def test_ranking_clears_an_old_scope_note_even_without_a_new_one(self):
        """A note says "deliberately not ranked". Once the entry is ranked that
        is false, whether or not this run was itself scoped."""
        old_note = "2026-08-28: international skipped"
        self.write_state({"a": entry(rank_scope_note=old_note), "b": entry(rank_scope_note=old_note)})
        self.apply([self.scored("a")])
        stored = self.read_state()
        self.assertNotIn("rank_scope_note", stored["a"])
        self.assertEqual(stored["b"]["rank_scope_note"], old_note, "an unscoped run leaves the previous record alone")

    # --- decision fields --------------------------------------------------------

    def test_decision_fields_are_copied_verbatim_and_reported(self):
        self.write_state({"a": entry()})
        out = self.apply(
            [
                self.scored(
                    "a",
                    visa="CLOSED",
                    visa_note="\"We are unable to sponsor visas for this role.\"",
                    portfolio_required=False,
                    still_open=True,
                    band="MXN 50,000-65,000 / month",
                    language="es",
                )
            ]
        )
        stored = self.read_state()["a"]
        self.assertEqual(stored["visa"], "CLOSED")
        self.assertEqual(stored["visa_note"], "\"We are unable to sponsor visas for this role.\"")
        self.assertIs(stored["portfolio_required"], False)
        self.assertIs(stored["still_open"], True)
        self.assertEqual(stored["band"], "MXN 50,000-65,000 / month")
        self.assertEqual(stored["language"], "es")
        row = out["ranked"][0]
        self.assertEqual(row["visa"], "CLOSED", "Step 5's table has a Visa column")
        self.assertEqual(row["band"], "MXN 50,000-65,000 / month", "Step 5's table has a Band column")

    def test_absent_decision_fields_are_left_alone(self):
        self.write_state({"a": entry(visa="OPEN", band="EUR 70k")})
        self.apply([self.scored("a")])
        stored = self.read_state()["a"]
        self.assertEqual(stored["visa"], "OPEN")
        self.assertEqual(stored["band"], "EUR 70k")

    def test_a_results_location_never_overwrites_the_scrapers_place(self):
        self.write_state({"a": entry(location="Aarhus, Denmark")})
        self.apply([self.scored("a", location="PASS", location_verdict="PASS")])
        stored = self.read_state()["a"]
        self.assertEqual(stored["location"], "Aarhus, Denmark")
        self.assertEqual(stored["location_verdict"], "PASS")


if __name__ == "__main__":
    unittest.main()
