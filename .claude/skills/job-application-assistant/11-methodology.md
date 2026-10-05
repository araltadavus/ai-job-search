---
framework_version: 1.0.0
---

# Methodology — corrections earned from real failures

**Every rule here traces to something that actually went wrong in a real job search run on this
framework.** They live in the skill rather than in a session handoff because a file rewritten every
session is the wrong home for rules that never change. **Items are numbered so other files can cite
them by number; keep the numbering stable and append new items at the end.**

---

## The grounding rules — read these before trusting any figure

In the search these rules come from, a cached or derived number silently rotted **six separate times**:
a central claim restated from memory, a stale git ref, a salary tier table written from memory, a count
that drifted by one between two files, an FX-stale currency conversion, and a "re-derivation" that
re-converted a mislabelled number.

- **Re-derive before you count.** Never copy a figure forward.
- **Never store a derived number without the numbers it was derived from.** A figure with no basis
  cannot be checked and will be wrong eventually.
- **Settle a disputed figure from the page's own text**, not from a summary of it.
- **Prefer a query to an answer.** Where a count can be produced by a command, store the command.

---

## 1–26 — the earlier corrections, in brief

1. Never filter by posting age.
2. Paginate.
3. A throttled fetch is indistinguishable from a dead posting.
4. Classify by the posting body, not the title.
5. Never judge an employer by its name.
6. Verify company claims against a fetched page.
7. Never trust a summary over the data.
8. Distrust an agent explaining why something is *fine*.
9. A `FLAG` costs one fetch — resolve it rather than guess.
10. Persist evidence at fetch time.
11. Ask about capability gaps before conceding them.
12. Never name a client beside a vulnerability you fixed for them.
13. A published band makes the salary step a conversion, not a discovery.
14. Fit and compensation can disagree, and the money is usually right.
15. A derived figure must carry its basis.
16. Offline triage orders the queue; it does not decide.
17. A `robots.txt` disallow binds.
18. Never weld two facts into one sentence.
19. Settle a disputed figure from the page's own text.
20. Grep every other draft when a review finds a grounding error.
21. Look for the same requisition in a pay-transparency geography.
22. A reviewer's layout advice has to survive the template.
23. The grounding controls only cover documents, and interviews are not documents.
24. Prep material has to be in the candidate's register.
25. Derive technical prep from the employer's own job description.
26. Ask the recruiter for their own prep material.

---

## 27 — A correction is not verification

**The most expensive lesson on this list.** A candidate corrected a spoken overstatement and supplied a
replacement. The replacement was recorded as **the accurate version**, tagged `[attested]`, and
propagated into the experience files and the prep material. **It was also false.**

**A self-correction arrives from the same source as the claim it replaces and inherits none of its
credibility.** Ask the same grounding question of the new version: what is the evidence, and does any
document, commit or third party corroborate it.

## 28 — Settle a disputed claim from the artifact, and the candidate may demand that

When a session's memory of a sent CV disagreed with the candidate's, the candidate supplied the actual
PDF, and one text extraction settled all three disputed phrasings. **When a session's memory and a file
disagree about what was sent, open what was sent.**

## 29 — A retired phrasing left alive in a summary file will be rewritten into the next draft

Phrasings retired in an `experience/` file's `Do NOT say` table stayed live in `CLAUDE.md` and
`01-candidate-profile.md` for a week and reached a draft from there. **When a phrasing is retired
anywhere, grep the summary files in the same turn.**

## 30 — A capability claim on a CV is a promise to be examined on it

A framework line was added to a CV to pass keyword filters, with no real experience behind it. What it
produced: two rejections where that framework was central, a recruiter question that forced an invented
figure, an interview question the candidate could not answer, and a final-round exam on it. **A gap
costs a filter. A fabricated capability costs the interview, and can cost the agency relationship
behind it.**

**The operational rule.** This framework grounds itself in the candidate's self-report, because for
most of a career no other source exists — and that method is fallible in one specific direction:
filling a gap the market keeps asking for. When a claim (a) covers a named requirement the candidate
otherwise lacks, (b) sits conveniently far in the past, and (c) has no document, commit or third party
behind it, **ask the grounding question explicitly rather than recording it as `[attested]`.** And a
"how fast I pick up frameworks" argument supports one sentence about learning speed beside a stated
gap; the moment it is used to imply experience in the missing framework, it becomes the fabrication it
was meant to replace.

## 31 — Verify a derived number with a script, not by re-reading your own arithmetic

Two figures were written into a study plan wrong and both survived being re-read. **Both died the
moment they were recomputed mechanically.** Re-reading a sum reproduces the reasoning that produced it.
**When a figure will be stored, compute it in code and print the components.**

## 32 — A recorded answer is a different risk class from a written one

A CV line can be retired and a document reissued. **A recording cannot be corrected, only
contradicted.** Anything that would need a grounding audit on paper (an async video interview, a
recorded screening question) needs rehearsal before the camera starts.

## 33 — Read the candidate portal, not only the invitation email

An employer's emails and its candidate portal disagreed on the number of questions, the length, the
deadline and whether two steps were linked — **and the portal did not carry a technical briefing the
emails did.** The email is marketing generated from a template; **the portal is the system of record.**

## 34 — A calendar invite's time lives in the `.ics`, not the email body

An invite rendered `11:30` under `TZID=SA Pacific Standard Time` (Bogotá, UTC−05:00) for an interview in
Mexico City (UTC−06:00). **Extract `DTSTART`/`DTEND` with their `TZID`, convert explicitly, then settle
it against the candidate's own calendar** — the calendar is the artifact; the arithmetic is a
hypothesis.

## 35 — Check the artifact before attributing a defect to the employer

A follow-up email was drafted pointing out a wrong label in a take-home exercise repo as a UX
observation. **The `git diff` showed the candidate had written that label.** One check before sending
prevented an own goal. **Before naming any flaw in someone else's codebase, confirm it is theirs.**

## 36 — A drill that assumes knowledge the candidate lacks is not a drill

Drills for a framework the candidate had never used required both its concepts and its profiling
tooling. Hours before an interview, that is a tutorial wearing a drill's clothes. **The learning
objective was always the observation and the sentence, never the authoring** — the means had been
confused with the end. **When preparation stalls, check whether it presumes a prerequisite the
candidate does not have.**

## 37 — Under time pressure, a preparation plan will be re-planned instead of executed

Five planning passes were made against one logged hour of actual practice. **Each re-plan moved
further from the keyboard and felt like progress.** The fix that worked was a **fixed-order queue**
with the re-planning decision removed: no budget to re-balance, no block to choose, only a next item.
**When a plan has been revised twice, the next revision is probably avoidance.**
