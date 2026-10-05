---
framework_version: 1.0.0
---

# Market facts — Mexico software compensation, with sources and dates

Reference data for the `salary-analyst` agent and for `04-job-evaluation.md` → Compensation Framework.
**Every figure here carries its basis and the date it was read.** The data was gathered during an
Aug–Sep 2026 search in Mexico that focused on frontend roles, so where a figure is frontend-specific it
says so. Extend the file with data for your own discipline as you gather it, under the same rule: no
figure without its source, its basis and its read date.

> **⚠ These rot.** FX moves, bands are re-published, the corpus ages. **Re-derive before quoting any
> conversion.** A figure without its basis is not usable — see `11-methodology.md`.

---

## Employer compensation tiers — gross MXN per month

**The employer tier sets the ceiling, not the national market.** The same title spanned roughly **5x**
across these four tiers in published bands fetched in Sep 2026. **Read the `n` and `Confidence`
columns before using any row** — three of the four rest on very little.

| Tier | Who | Gross MXN/month | n | Confidence | Evidence |
|---|---|---|---|---|---|
| 1 | **Mexican-owned employers** | typical **75,000–100,000**; observed ceiling **115,000–120,000** | 6 | **LOW** | OCC postings, Sep 2026: MROADS Lead Frontend 75–90k; AXITY 86–96k; Grupo Salinas Arquitectura 115–120k. A scraped LinkedIn corpus adds CRH Talento 40–44k, Zephyr 35–50k, Arrow Components 69,350–110,958 |
| 2 | **Foreign employers on Mexican payroll, median** | **~100,000 gross / ~71,600 net, for frontend** — derived, see below | 10,246 survey responses | **HIGH** on the survey, **LOW** on the frontend figure, which is derived | CodersLink 2026 salary report, read verbatim 10 Sep 2026. Postings agree directionally: Alia 100–105k, CRH 95–100k, a Hireline frontend posting 100–125k |
| 3 | **Foreign employers who price the Mexico seat properly** | **140,000–180,700** | **1** | **MEDIUM** | Justworks, Senior Developer Experience Engineer, Mexico City: **MXN 1,680,000–2,168,000/yr base, published** alongside New York USD 188–242k and Toronto CAD 167–215k (Greenhouse 7727631, refetched 9 and 10 Sep 2026, band verbatim identical). The band is real; its generality is not established |
| 4 | **Location-independent USD pay, Mexico eligible** | **USD 165,000–195,000/yr** — re-derive the peso figure at a fetched rate | **1** | **LOW** | Optimal Dynamics, Senior SWE Frontend, with Mexico named in the eligibility list (Aug 2026, **never reverified**). It was once carried as ~233,000–276,000 MXN/month with no rate or date recorded, which is exactly the failure the rule below exists to prevent |

**How often a figure is published at all:** in a 285-entry Mexico LinkedIn corpus (Aug–Sep 2026),
**6** postings published any figure. That is why `CANNOT TELL` is the salary analyst's commonest
verdict, and why the tier — not a lookup — is the model.

**Tier 1 was once stated as 95,000–120,000 and contradicted its own evidence.** Two of its three
original data points sat *below* the band they were cited to support. The band was describing the top
few per cent of the tier while being labelled as the tier. A band must contain its own evidence.

---

## The tier-2 benchmark — the derivation matters more than the number

**~100,000 MXN gross / ~71,600 MXN net per month, for frontend.**

**Basis**, read verbatim from `salaries.coderslink.com` on **10 Sep 2026** (n=10,246):

- The **Software Engineer** cut (n=924) shows *"US-employer premium: $4,985 / month median (vs $2,492 at
  Mexico-origin firms)"*.
- **There is no frontend employer-origin split** on that page. This is the weak link in the chain.
- The page states: *"Frontend is -15% below Senior Software Engineer at the same seniority, with the gap
  widening at Lead."*

**Derivation:** USD 4,985 less 15% ≈ **USD 4,237 net** ≈ **~71,600 MXN net** at USD/MXN **16.898727**
(open.er-api.com, 10 Sep 2026) ≈ **~100,000 MXN gross**.

**Frontend medians across all employers**, same source: Senior **USD 2,769** (n=243) · Lead **USD
3,783** (n=72) · Principal **USD 4,431** (n=25).
**All roles, by employer origin:** US-origin **USD 3,877** vs Mexican-origin **USD 2,303** — **+68%**.

**The single most useful consequence:** employer origin moves pay more than seniority does. A
US-employer Senior often beats a Mexico-origin Lead.

**This row was corrected twice in one day, and both corrections are the lesson:**

1. **FX-stale.** It read ~106,500 gross from a 78,900 net figure with no FX rate and no date recorded.
   That peso number implied USD/MXN ≈ 20.35 against 16.90 on the day — ~20% wrong while reading as
   authoritative, and it was being used to judge whether roles cleared a floor.
2. **Mislabelled.** The re-derivation then converted "frontend at US-headquartered employers, median
   USD 4,985" — but that pair sits in the page's *Software Engineer* section. A WebFetch summary had
   mislabelled it, and so had the agent explaining the error. One verbatim text extraction of the page
   settled it. **Settle a disputed figure from the page's own text, never from a summariser's
   paraphrase.**

---

## Reference points

| Fact | Detail | Read |
|---|---|---|
| **Justworks, Senior DevEx** | NYC USD 188–242k; CDMX MXN 1,680,000–2,168,000/yr. **~53% CDMX-to-NYC ratio** at the Sep 2026 rate | Greenhouse 7727631, refetched 10 Sep 2026 |
| **Degree title gates the upper domestic band** | Every OCC posting opened that published ≥70,000/month required *"Universitario **titulado**"*, including four Adecco roles at 140,000–220,000. The sole exception was AXITY at 86–96k. It may be boilerplate, but it recurs exactly at the upper band — **a candidate whose degree is not yet titulado (pasante) should treat it as a constraint on the search** | OCC, Sep 2026 |

**The Justworks ratio is the most useful single number here:** a US company that publishes both bands
paid CDMX roughly **half** of NYC for the same role. Use it to sanity-check any offer from a US
employer, and recompute it from fetched bands and a fetched rate before relying on it.

---

## Payroll (nómina) versus contractor (honorarios / B2B)

**Not comparable without adjustment, and the gap runs in both directions.**

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

- **Glassdoor** — every fetch was blocked on both domains, and its Mexico pages returned euro figures.
  Units cannot be trusted.
- **Michael Page's Guía Salarial** — gated; its "Líder Técnico 130–160k" figure has only ever come
  from a search summary and remains unverified.
- **LaPieza** — a recruiter's own placement book; its Senior floor sat above the 96th percentile of real
  published postings. Directionally right about tiers 3–4, wrong in its Mexican framing.
- **Any aggregator's modelled "estimated salary" widget, LinkedIn's included** — inferred, not
  observed. It launders a guess into a citation.

---

## Market shape (frontend search, Aug–Sep 2026)

- **Zero accessibility-titled roles** in a 1,247-entry scrape. Accessibility is a differentiator
  *inside* a frontend role, never a role to search for.
- **Design systems as a job title is an international play.** Of 23 postings containing "design
  system" in a 439-posting scrape (Aug 2026), roughly half were designer seats. In Mexico there were
  effectively one or two viable engineering ones; domestically the realistic shape is Senior/Staff
  Frontend with design systems as a named component.
- **Posting rot: 19% in two weeks**, measured across 16 shortlisted entries on 10 Sep 2026. **A
  shortlist older than a fortnight needs re-verification before it is used.**
