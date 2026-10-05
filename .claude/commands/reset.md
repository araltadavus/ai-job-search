# /reset - Reset Candidate Profile Data

You are resetting parts of the job search framework back to a blank state so the user can start fresh with `/setup`.

**This command is destructive.** Nothing is deleted until the user explicitly confirms. Follow these steps exactly in order.

---

## Step 0: Parse Scope from Arguments

Check `$ARGUMENTS` for a scope keyword:

- `profile` — clears candidate profile data from skill files only
- `documents` — deletes user-provided files from the `documents/` folder only
- `experience` — deletes user-added role files from the `experience/` folder and restores its router
- `all` — all three of the above

If `$ARGUMENTS` is empty or does not contain a recognized scope keyword, ask:

> **What would you like to reset?**
>
> - **`profile`** — Clears candidate data from the skill files (profile, behavioral, STAR examples, profile statements, personalized evaluation criteria, search queries). The framework structure, scoring framework, and writing rules are preserved. Use this to re-run `/setup` from scratch.
>
> - **`documents`** — Deletes all files you've placed in the `documents/` folder (CV PDFs, LinkedIn export, diplomas, references, project summaries, pasted job postings, past applications). The folder structure and `README.md` are preserved.
>
> - **`experience`** — Deletes any role files you've added to `experience/` and restores `INDEX.md`'s router to its placeholder rows. `README.md` and `00-example-role.md` (the layer's own documentation and worked example) are preserved — they never hold personal data. This is a separate scope from `profile` because `/setup` does not generate these files and cannot regenerate them either: unlike the skill files, clearing this scope is not something you'd casually re-run before `/setup`.
>
> - **`all`** — All three of the above.
>
> Reply with `profile`, `documents`, `experience`, or `all`.

Wait for the user's response before continuing.

---

## Step 1: Show Exactly What Will Be Cleared

Before doing anything, show the user precisely what will be wiped.

### If scope includes `profile`:

Read the current state of these files and report whether each has content or is already empty:

- `.claude/skills/job-application-assistant/01-candidate-profile.md`
- `.claude/skills/job-application-assistant/02-behavioral-profile.md`
- `.claude/skills/job-application-assistant/04-job-evaluation.md` *(personalized match areas, career goals, and life-situation constraints only — the scoring framework is preserved)*
- `.claude/skills/job-application-assistant/05-cv-templates.md` *(profile statements section and the contact block inside the LaTeX template only — framework structure is preserved)*
- `.claude/skills/job-application-assistant/06-cover-letter-templates.md` *(contact line and signature inside the LaTeX template only — framework structure is preserved)*
- `.claude/skills/job-application-assistant/07-interview-prep.md` *(STAR examples and STAR candidates sections only — framework structure is preserved)*
- `.claude/skills/job-scraper/search-queries.md` *(role titles, domain keywords, and location terms only — query structure is preserved)*

This list must stay in step with what `/setup` Step 3 populates: every skill file it writes candidate data into is cleared here.

Present as:

```
## Profile reset will clear:

- 01-candidate-profile.md — [has content / already empty]
  Full file will be replaced with a blank template.

- 02-behavioral-profile.md — [has content / already empty]
  Full file will be replaced with a blank template.

- 04-job-evaluation.md — [has personalized criteria / already blank]
  Your match areas, career goals, energizing/draining tasks, and life-situation
  constraints will be restored to placeholders. The scoring framework (dimensions,
  score bands, weights, Language Gate, Company Research Checklist) is preserved.

- 05-cv-templates.md — [has profile statements or contact details / already blank]
  Profile statement templates will be cleared and the contact block in the LaTeX template restored to placeholders. LaTeX structure and tailoring guidelines are preserved.

- 06-cover-letter-templates.md — [has contact details / already blank]
  The contact line and signature in the LaTeX template will be restored to placeholders. Letter structure, opening patterns, and closing formulations are preserved.

- 07-interview-prep.md — [has STAR examples / already blank]
  STAR examples and any STAR candidate stubs will be cleared. Framework, tough questions, and roleplay guidelines are preserved.

- job-scraper/search-queries.md — [has personalized queries / already blank]
  Your job boards, role titles, domain keywords, city, and commute tiers will be
  restored to placeholders. The query structure and filter sections are preserved.

The following files are NOT touched (they contain framework rules, not candidate data):
  - 03-writing-style.md

Outside the profile scope, still holding your personal data: CLAUDE.md, cv/main_example.tex, and
experience/ (if you have populated it). experience/ is the most sensitive of the three - it holds
the unsummarised, unpolished account of your work history (see experience/README.md), not the
curated, CV-ready text the other files hold. Clear CLAUDE.md and cv/main_example.tex by hand;
clear experience/ with `/reset experience`. This scope covers skill files only.
```

### If scope includes `documents`:

Use Glob to list all files present in `documents/cv/`, `documents/linkedin/`, `documents/diplomas/`, `documents/references/`, `documents/projects/`, `documents/postings/`, and `documents/applications/`. Present as:

```
## Documents reset will delete:

documents/cv/
  - [filename] or "(empty)"

documents/linkedin/
  - [filename] or "(empty)"

documents/diplomas/
  - [filename] or "(empty)"

documents/references/
  - [filename] or "(empty)"

documents/projects/
  - [filename] or "(empty)"

documents/postings/
  - [filename] or "(empty)"

documents/applications/
  - [subfolder/filename] or "(empty)"

documents/README.md — NOT deleted (instructions file)
```

If all document subfolders are already empty, state "All document subfolders are already empty — nothing to delete." and skip the confirmation step for this scope.

### If scope includes `experience`:

Use Glob to list all `experience/*.md` files, then exclude `README.md` and `00-example-role.md` from
the list — those two never hold personal data and are never touched by this scope. Check whether the
remaining `INDEX.md` still matches the placeholder shipped with the template (the file starts
`# Experience index — router` and its `## The files` table rows are still `[BRACKETED]`) or has been
edited with real routing content. Present as:

```
## Experience reset will clear:

- INDEX.md — [placeholder, nothing to clear / has real routing content]
  Router rows will be restored to the shipped placeholder.

- [any other experience/*.md file found, e.g. 01-<employer>-<role>.md] — will be deleted

experience/README.md and experience/00-example-role.md — NOT touched (the layer's own
documentation and worked example; they never hold personal data).
```

If the only files present are `README.md`, `INDEX.md` (still the placeholder), and
`00-example-role.md`, state "experience/ has no role files and INDEX.md is still the shipped
placeholder — nothing to clear." and skip the confirmation step for this scope.

---

## Step 2: Require Explicit Confirmation

Present the confirmation prompt:

> **This cannot be undone.**
>
> Type **`RESET`** (all caps) to confirm, or anything else to cancel.

Wait for the user's response.

- If the user types exactly `RESET`: proceed to Step 3.
- If the user types anything else: abort and tell them "Reset cancelled. Nothing was changed."

---

## Step 3: Execute the Reset

### Profile reset

**For `01-candidate-profile.md`**, replace the file content with:

```markdown
# Candidate Profile

<!-- Run /setup to populate this file -->

## Identity

## Education

## Professional Experience

## Independent Projects

## Technical Skills

## Publications

## Awards

## References
```

**For `02-behavioral-profile.md`**, replace the file content with:

```markdown
# Behavioral Profile

<!-- Run /setup to populate this file -->

## Overview

## Strongest Behavioral Traits

## How I Work Best

## Growth Areas

## Mapping to Job Posting Language

## Management Style Preferences

## Using This in Applications
```

**For `04-job-evaluation.md`**, restore the values `/setup` Step 3.4 personalized back to their placeholder tokens, leaving every surrounding line untouched:

| Line to restore | Token |
|---|---|
| `**Strong match areas:**` | `[YOUR_PRIMARY_SKILLS]` |
| `**Moderate match areas:**` | `[YOUR_SECONDARY_SKILLS]` |
| `**Weak match areas:**` | `[SKILLS_YOU_LACK]` |
| `**Strong:**` (Experience Match) | `[YOUR_DIRECT_EXPERIENCE_DOMAINS]` |
| `**Moderate:**` (Experience Match) | `[YOUR_ADJACENT_EXPERIENCE]` |
| `**Entry-level:**` (Experience Match) | `[ROLES_WITH_LIMITED_EXPERIENCE]` |
| the three `**Career goals:**` bullets | `[YOUR_CAREER_GOAL_1]`, `[YOUR_CAREER_GOAL_2]`, `[YOUR_CAREER_GOAL_3]` |
| `- Tasks that energize:` | `[YOUR_ENERGIZING_TASKS]` |
| `- Tasks that drain:` | `[YOUR_DRAINING_TASKS]` |
| `- **Security**:` | `[YOUR_FINANCIAL_SITUATION_CONTEXT]` |
| `- **Screening floor**:` | `[YOUR_SALARY_FLOOR_NET_MONTHLY]` |
| `- **Target**:` | `[YOUR_SALARY_TARGET_NET_MONTHLY]` |
| `- **Flexibility**:` | `[YOUR_SCHEDULE_CONSTRAINTS]` |
| `- **Professional development**:` | `[YOUR_GROWTH_PRIORITIES]` |

Also remove any `## Calibration from Past Applications` section, which `/setup` Path A writes from the user's own application outcomes.

Leave the rest of `04-job-evaluation.md` intact: the five scoring dimensions and their score bands, the weighting, the Language Gate, the red-flag guidance, the Company Research Checklist and cache schema, and the salary benchmark section. If `/setup` Step 3.4 ever personalizes a value not in the table above, add it here too.

**For `05-cv-templates.md`**, locate the section that begins with `**Profile statement templates` and extends through the role-specific template blocks. Replace only that section with:

```markdown
**Profile statement templates:**

<!-- Run /setup to populate role-specific profile statements -->
```

Then restore the contact block inside the file's LaTeX template to its placeholder tokens: `\name{[FIRST_NAME]}{[LAST_NAME]}`, `\address{[YOUR_ADDRESS]}{}{}`, `\phone[mobile]{[YOUR_PHONE]}`, `\email{[YOUR_EMAIL]}`, the `\extrainfo{...}` line's `[YOUR_LINKEDIN_URL]` and `[YOUR_GITHUB_URL]`, and `[YOUR_NAME]` in the `pdftitle`. Leave all other content in `05-cv-templates.md` intact.

**For `06-cover-letter-templates.md`**, restore the contact line and the signature inside the file's LaTeX template to their placeholder tokens: the `\namesection{}` line becomes `\namesection{}{\Huge{[YOUR_NAME]}}{  \href{mailto:[YOUR_EMAIL]}{[YOUR_EMAIL]} | [YOUR_PHONE] |  \urlstyle{same}\href{[YOUR_LINKEDIN_URL]}{LinkedIn}` and `\signature{...}` becomes `\signature{[YOUR_NAME]}`. Leave all other content in `06-cover-letter-templates.md` intact - the letter structure, opening patterns, and closing formulations are framework, not candidate data. If `/setup` Step 3.6 ever personalizes anything beyond these two lines, add it here too.

**For `07-interview-prep.md`**, locate and remove:
- The entire `## Ready-Made STAR Examples` section and all numbered STAR examples under it
- Any `## STAR Candidates (Complete Manually)` section added by `/setup` Path A

Replace with:

```markdown
## Ready-Made STAR Examples

<!-- Run /setup to populate STAR examples from your actual experience -->
```

Leave all other content in `07-interview-prep.md` intact (STAR format explanation, tough questions, questions to ask interviewers, phone/video tips, follow-up etiquette, roleplay guidelines).

**For `.claude/skills/job-scraper/search-queries.md`**, restore the values `/setup` Step 3.9 personalized back to their placeholder tokens:

- **Search Sites**: the board names back to `[YOUR_JOB_BOARD]`, `[YOUR_INDUSTRY_JOB_BOARD]`, `[YOUR_ADDITIONAL_JOB_BOARD]`, and the LinkedIn filter back to `[YOUR_COUNTRY]` / `[YOUR_CITY]`.
- **Query Categories**: the four priority headings back to `[YOUR_PRIMARY_ROLE_TYPE]`, `[YOUR_DOMAIN_EXPERTISE]`, `[YOUR_ADJACENT_ROLE_TYPE]`, and `Broader Technical / Consulting`; inside the query blocks, the titles, skills, and domain terms back to `[YOUR_PRIMARY_JOB_TITLE_1]`, `[YOUR_PRIMARY_JOB_TITLE_2]`, `[YOUR_ADJACENT_TITLE_1]`, `[YOUR_ADJACENT_TITLE_2]`, `[YOUR_KEY_SKILL]`, `[YOUR_DOMAIN_KEYWORD_1]`, `[YOUR_DOMAIN_KEYWORD_2]`, `[YOUR_DOMAIN]`, and the location terms back to `[YOUR_CITY]`, `[YOUR_COUNTRY]`, `[YOUR_REGION]`.
- **Location Filter**: the commute tiers back to `[YOUR_CITY]`, `[ACCEPTABLE_AREA_1]`, `[ACCEPTABLE_AREA_2]`, `[BORDERLINE_AREA]`, `[TOO_FAR_AREA]`.
- Remove any extra priority categories or translated query duplicates `/setup` added beyond the four shipped tiers.

Leave the rest of the file intact: the portal-CLI and WebSearch-fallback explanation, the Language scope note, the "organize by function, not job title" guidance, and the Language, Date, and Adapting Queries sections.

### Documents reset

For each non-empty document subfolder, delete all files within it using Bash `rm`. Do not delete the folder itself, and do not delete `documents/README.md`.

```bash
rm -f documents/cv/*
rm -f documents/linkedin/*
rm -f documents/diplomas/*
rm -f documents/references/*
rm -f documents/projects/*
rm -f documents/postings/*
rm -rf documents/applications/*/
```

### Experience reset

Delete every file Step 1 found in `experience/` other than `README.md`, `INDEX.md`, and
`00-example-role.md` — these are real role files, so delete each one with Bash `rm`
(`rm -f experience/<filename>` per file, or one `rm -f` call listing all of them).

If Step 1 found `INDEX.md` no longer matching the shipped placeholder, replace its **entire content**
with:

```markdown
# Experience index — router

`/apply` Step 2 reads this file, matches the posting's requirement list against the table below, and
then reads **only the one or two experience files that match**. Reading the whole folder defeats the
purpose: these files are deliberately unsummarised, and a model given all of them writes vaguer
bullets than one given the right subset.

> **This file ships as a placeholder.** It has no real role files behind it yet, and `/setup` does
> not generate them. Write `experience/NN-<employer>-<role>.md` files by hand using the skeleton in
> `experience/README.md`, then replace every `[BRACKETED]` row below with your own. `/recall`
> (`.claude/commands/recall.md`) keeps the *files themselves* in sync as facts come in, but it does
> not update this router — add or adjust a row here yourself whenever a new file appears or a file's
> scope changes, or a posting will fail to find it.

## The files

| File | Role | Period | Weight |
|---|---|---|---|
| `01-[employer]-[role-slug].md` | [JOB_TITLE_1] | [YEAR_START] – [YEAR_END] | [Why a drafter should default here — e.g. largest role by scope or duration] |
| `02-[employer]-[role-slug].md` | [JOB_TITLE_2] | [YEAR_START] – [YEAR_END] | [What this file is the best or only source for] |
| `03-[employer]-[role-slug].md` | [JOB_TITLE_3] | [YEAR_START] – [YEAR_END] | [What this file is the best or only source for] |

---

## Keyword router

Match on the posting's own terms. Where two files are listed, the first leads and the second
supports.

| If the posting asks for… | Read | Go straight to |
|---|---|---|
| [PRIMARY_SKILL_OR_STACK] | `01` | §[N] |
| [SECONDARY_SKILL] | `02`, `01` | `02` §[N] ([what it is evidence of]), `01` §[N] ([supporting detail]) |
| **[A CAPABILITY YOU LACK DIRECT EXPERIENCE IN]** | `0N` | **Start at `01-candidate-profile.md` → "[the section documenting how you acquire unfamiliar tools/frameworks]"**, then the file and section with the nearest genuine adjacency. Demonstrate the sequence honestly, never assert "fast learner", and never phrase it as "whatever the job required" |
| [DOMAIN_OR_INDUSTRY] | `0N`, `0M` | Both — name what each file uniquely supports |
| **[A THEME WORTH CALLING OUT EXPLICITLY]** | `0N` | §[N]. [One line on why this is a standout theme in the profile] |
| **[SOMETHING YOU DID ADJACENT TO BUT DID NOT OWN]** | `0N` | §[N]. **Always include the honest boundary:** [what you did not do, stated plainly] |

Add a row per capability, tool, or theme a posting is likely to ask about — one row is cheap; a
missing one means `/apply` reads the wrong file or skips the folder's best evidence entirely.

---

## Rules that apply to every read

1. **Provenance tags bind.** `[evidence]` and `[attested]` may be used. **`[to-confirm]` may not
   reach a CV or cover letter** — surface it to the user instead.
2. **`Do NOT say` sections bind.** Every file opens with one. Those are retired exaggerations still
   present in LinkedIn and older CVs; reintroducing one is a grounding failure.
3. **Depth ratings bind.** DEEP / WORKING / EXPOSURE. An EXPOSURE technology is never presented as
   owned.
4. **Honest boundaries are assets, not liabilities.** A file that states plainly what you did *not*
   do — the layer you didn't own, the system you extended rather than built — makes everything
   adjacent to that boundary more credible. Say those boundaries out loud where a posting touches
   them, rather than treating them as things to omit.
```

`README.md` and `00-example-role.md` are never modified by this scope.

---

## Step 4: Confirm What Was Done and Next Steps

After the reset is complete, report:

```
## Reset complete

### Cleared
[List each file/folder that was actually modified or cleared]

### Unchanged
[List anything that was already empty or was intentionally preserved]
```

Then tell the user what to do next based on what was reset:

**If profile was reset:**
> The skill files are now blank. Run `/setup` to repopulate them. The command auto-detects any files in your `documents/` folder and offers to read from there; otherwise it walks you through a CV import or interactive interview.
>
> Note that `CLAUDE.md`, `cv/main_example.tex`, and `experience/` are outside the `profile` scope and still hold your personal data. `experience/` is the most sensitive of the three - it holds the unsummarised, unpolished account of your work history, not curated CV-ready text. `/setup` does not regenerate any of these, so if you are handing this fork over or making it public: clear `CLAUDE.md` and `cv/main_example.tex` by hand, and run `/reset experience` for the rest.

**If documents were reset:**
> The `documents/` folder is now empty. Add your career documents and run `/setup` to populate your profile. See `documents/README.md` for instructions on what to put where.

**If experience was reset:**
> Any role files you had added are gone and `INDEX.md` is back to its shipped placeholder. `/setup` cannot regenerate these - write new role files by hand from the skeleton in `experience/README.md`, or add facts to them over time with `/recall` as they come up.

**If more than one scope was reset (including `all`):**
> Everything above applies to the scopes you reset. Run `/setup` next for `profile` or `documents`; for `experience`, write role files by hand (or via `/recall`) whenever you are ready - there is no command that generates them.
