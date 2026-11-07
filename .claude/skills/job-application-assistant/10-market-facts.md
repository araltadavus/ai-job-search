---
framework_version: 1.1.0
---

# Market facts — compensation in your market, with sources and dates

<!-- SETUP: This file ships as an empty template. Fill it as you gather evidence during your own
search; nothing here is pre-populated, because market data from someone else's discipline, city and
year would mislead the salary analyst more than an empty table does. -->

Reference data for the `salary-analyst` agent and for `04-job-evaluation.md` → Compensation Framework.
**Every figure here carries its basis and the date it was read.** Where a figure is specific to one
discipline (frontend, data, design...), say so in the row. Add data under the same rule throughout:
no figure without its source, its basis and its read date.

> **⚠ These rot.** FX moves, bands are re-published, the corpus ages. **Re-derive before quoting any
> conversion.** A figure without its basis is not usable — see `11-methodology.md`.

---

## Employer compensation tiers — gross [CURRENCY] per month

**The employer tier sets the ceiling, not the national market.** In markets with a large foreign-employer
presence, the same title can span several times over across tiers, so classify the employer before
reading any figure. **Read the `n` and `Confidence` columns before using any row** — a tier resting on one
data point is a lead, not a band.

| Tier | Who | Gross [CURRENCY]/month | n | Confidence | Evidence |
|---|---|---|---|---|---|
| 1 | **Locally-owned employers** | [RANGE] | [N] | [LOW/MEDIUM/HIGH] | [Source, role, band as published, read date] |
| 2 | **Foreign employers on local payroll, median** | [FIGURE] — see the benchmark below | [N] | [LOW/MEDIUM/HIGH] | [Survey or postings, read date] |
| 3 | **Foreign employers who price the local seat properly** | [RANGE] | [N] | [LOW/MEDIUM/HIGH] | [A published band for your city, read date] |
| 4 | **Location-independent pay, your country eligible** | [RANGE in the posting's currency] — re-derive at a fetched rate | [N] | [LOW/MEDIUM/HIGH] | [Posting naming your country as eligible, read date] |

**How often a figure is published at all:** [N of M postings in your corpus published any figure, and
when]. In markets where few postings publish a band, `CANNOT TELL` will be the salary analyst's
commonest verdict, and the tier — not a lookup — is the model.

**A band must contain its own evidence.** If a tier's data points sit below the band they are cited to
support, the band is describing the top of the tier while being labelled as the tier. Fix the band.

---

## The tier-2 benchmark — the derivation matters more than the number

**[FIGURE] gross / [FIGURE] net per month, for [DISCIPLINE].**

**Basis**, read verbatim from [SOURCE] on **[DATE]** (n=[N]):

- [The exact cut used, quoted from the page]
- [Any missing split the derivation has to bridge — name the weak link in the chain]

**Derivation:** [each step, with the FX rate, its source and its date].

**Settle a disputed figure from the page's own text, never from a summariser's paraphrase.** WebFetch
summaries can mislabel which section of a survey a figure comes from; one verbatim text extraction of
the page settles it. And a peso, euro or dollar figure recorded without its FX rate and date cannot be
trusted to judge whether a role clears a floor.

---

## Reference points

| Fact | Detail | Read |
|---|---|---|
| [A published cross-geography band, e.g. the same requisition priced in two cities] | [Both bands, and the ratio at a fetched rate] | [Source, date] |

**A cross-geography ratio is the most useful single number you can collect:** a company that publishes
bands for two locations tells you how it prices yours. Recompute it from fetched bands and a fetched rate
before relying on it.

---

## Payroll (nómina) versus contractor (honorarios / B2B)

**Not comparable without adjustment, and the gap runs in both directions.** The mechanics below are for
Mexico; replace them with your own country's if you work elsewhere.

- **Tax.** Under **RESICO** (persona física con actividad empresarial, while revenue stays under the
  annual cap) the ISR rate on gross receipts is low single digits — far below nómina's progressive
  withholding.
- **IVA.** Charged on top of the fee and remitted, so a pass-through, not income. Invoicing a
  **foreign** client can qualify as an **export of services at 0% IVA**. Confirm which side of the fee
  the IVA sits on, and whether the export treatment applies, against the actual contract — never a
  recruiter's summary.
- **What is forgone.** No IMSS (health cover and pension contribution become the contractor's), no
  aguinaldo, no PTU, no INFONAVIT, no statutory severance, and no vacation entitlement beyond what the
  contract grants. Contractual PTO is not the statutory kind. Price this bundle monthly so a
  contractor figure can be compared like-for-like with a nómina offer.
- **The honest summary is usually three-part:** the headline is higher, the net is higher still, and
  the protection is lower.

---

## Sources excluded, with the reason on record

Record every source you rule out, with the reason, so a later session does not re-fetch it. The
`salary-analyst` agent discards numbers from anything listed here.

- **Glassdoor** — fetches are routinely blocked, and its Mexico pages have returned euro figures.
  Units cannot be trusted.
- **Michael Page's Guía Salarial** — gated; a figure seen only in a search summary is unverified.
- **LaPieza** — a recruiter's own placement book; it describes what that recruiter places, not the
  market, and its floors have sat far above real published postings.
- **Any aggregator's modelled "estimated salary" widget, LinkedIn's included** — inferred, not
  observed. It launders a guess into a citation.
- [Add your own, with the reason]

---

## Market shape

[Observations from your own scrapes that change how you search — e.g. which titles barely exist in your
market, how fast shortlisted postings disappear. Date each one and give its corpus size.]

- **Posting rot.** [Share of shortlisted postings gone after N days, measured on DATE.] Whatever the
  figure, **a shortlist older than a fortnight needs re-verification before it is used.**
