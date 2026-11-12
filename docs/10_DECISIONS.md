# Architecture Decision Records (ADRs)

Append-only log of significant design decisions. Format adapted from Michael Nygard's ADR template.

Rules:

- Each entry is dated and numbered sequentially.
- To reverse a decision, add a new ADR that supersedes the old one. Do not edit history.
- Keep decisions atomic: one ADR per decision.
- Write the consequences honestly, including the ones you don't like.
- **Methodology decisions** (axes, anchors, bands, floors, weights) are not recorded here. They live in the research documents and the methodology changelog. ADR-0004 records how the two logs relate.

Status key: **Accepted** means confirmed by the maintainer. **Proposed** means drafted with this suite and awaiting confirmation.

---

## ADR-0001: Batch engine plus static site, no server

- **Date**: 2026-11-11
- **Status**: Accepted

### Context

The results change only when the methodology or data changes. The methodology demands reproducibility and public code and data (§6.6). User re-weighting is the only interactive feature, and it is cheap arithmetic over a few thousand per-run axis-score vectors.

### Decision

Voting System Metrics (VSM) is a batch scoring pipeline that publishes a versioned JSON bundle, rendered by a static site. User weights are applied in the browser. There is no application server, database server or user account.

### Consequences

- Hosting is near-free and has almost no attack surface.
- Every published number is a file with a hash, which makes integrity checks simple.
- Features needing a server (saved profiles, comments, live re-runs with new parameters) are excluded. A user cannot change anchors or scenarios without running the pipeline locally.
- The per-run bundle must stay small enough for mobile browsers.

---

## ADR-0002: Rust for counting and metrics, Python for ingest and preference modelling

- **Date**: 2026-11-11
- **Status**: Accepted

### Context

Counting, district generation and the S2 manipulability search are compute-heavy, must be exactly deterministic and benefit from strong typing. Ingesting SPSS and Stata files from the British Election Study (BES), handling shapefiles, and fitting multilevel regression and post-stratification (MRP) models are far better supported in Python than in Rust.

### Decision

Rust implements spec handling, districts, count rules, the run matrix, metrics and views. Python implements ingest, geography and preferences. Svelte (SvelteKit) implements the site.

### Consequences

- Each language is used where its ecosystem is strongest.
- Two toolchains and two lockfiles to maintain, and contributors need both.
- The language boundary must be a clean data contract (ADR-0003), not a foreign-function interface.

---

## ADR-0003: SQLite files as the hand-off between stages; no foreign-function interface

- **Date**: 2026-11-11
- **Status**: Proposed

### Context

Python and Rust stages must exchange data. The options were PyO3 bindings, Arrow or Parquet files, or SQLite. The workload is single-user, local and batch.

### Decision

Stages communicate only through two SQLite files: `reference.sqlite`, written by Python, and `runs.sqlite`, written by Rust. Each file has a versioned schema and a single writing language. There are no PyO3 bindings.

### Consequences

- Any stage can be re-run, inspected with the `sqlite3` command-line tool, or replaced in isolation.
- Both databases ship with each release, so third parties can query the results directly.
- Writing large S1 ballot profiles is slower than with Parquet. Acceptable at Commons scale. Revisit if profiles exceed a few gigabytes.
- Foreign keys across the two files are checked in code (`vsm check refs`), not by SQLite.

---

## ADR-0004: Methodology and engine are versioned separately; the frozen spec is the only bridge

- **Date**: 2026-11-11
- **Status**: Proposed

### Context

The methodology (research documents) changes on its own schedule and must be pre-registered (principle P10). Engine code changes more often. Mixing them makes it impossible to tell whether a score moved because of a method change or a bug fix.

### Decision

The methodology is encoded once, as machine-readable TOML in `spec/`, frozen with a SHA-256 hash and a `spec-vX.Y` tag. The engine reads only `spec/` and never hard-codes anchors, weights, applicability or grades. Methodology changes are logged in the methodology changelog; engine changes are logged here and in the release notes. Every published result carries both versions.

### Consequences

- "Which scores moved and why" can always be answered by diffing the spec or the engine.
- The research Markdown and the TOML can disagree. `vsm spec check` cannot detect that, so the release checklist includes a manual cross-read.

---

## ADR-0005: Determinism through derived seeds and ordered computation

- **Date**: 2026-11-11
- **Status**: Proposed

### Context

Goal G1 needs bit-identical rebuilds. District plans, MRP posterior draws, tie-break lots and weight-space sampling all involve randomness, and the work runs in parallel.

### Decision

Every random stream is seeded from `sha256(spec_hash ‖ component ‖ config_id ‖ index)`, using ChaCha (Rust) or PCG64 (Python). Parallel work uses independent per-item streams. Outputs use ordered collections, a fixed summation order and canonical JSON.

### Consequences

- Rebuilds are verifiable in CI.
- Changing the spec changes every seed, even for unaffected configurations. That is acceptable, because any spec change is a new version anyway.
- Developers must avoid `HashMap` iteration order and thread-order dependence. Clippy lints and the determinism test catch some of this, not all.

---

## ADR-0006: Fixed-point arithmetic for Single Transferable Vote transfers

- **Date**: 2026-11-11
- **Status**: Accepted

### Context

Weighted Inclusive Gregory Method (WIGM) transfers multiply fractional values over many stages. Official Scottish counts truncate to a fixed number of decimal places. Floating-point arithmetic could diverge from declared results and across platforms.

### Decision

The STV count uses fixed-point integers with the declared precision of the Scottish rules (five decimal places, truncated), configurable per configuration in the spec.

### Consequences

- Golden tests against official counts can require exact matches.
- Precision becomes a spec parameter that needs documenting.

---

## ADR-0007: District plans by seeded constrained region-growing (initial generator)

- **Date**: 2026-11-11
- **Status**: Proposed

### Context

Methodology §6.3 requires 20 valid, seeded plans joining whole adjacent 2023 constituencies within a nation. Options: region-growing with repair (simple, fast, but not a uniform sample), or a Markov chain sampler such as ReCom (better coverage of the plan space, more complex).

### Decision

Ship region-growing with repair in Phase 2, validated on Wales against the Senedd 2026 pairing. Keep the generator behind a trait so a Markov chain sampler can replace it without touching the other stages.

### Consequences

- Phase 2 is unblocked quickly.
- The score band reflects "plans this generator finds", which is narrower than "any reasonable map". The method page must say so until a better sampler is adopted.

---

## ADR-0008: First release scope is the Commons profile, S0 before S1

- **Date**: 2026-11-11
- **Status**: Accepted

### Context

The primary aim is replacing First Past the Post (FPTP) for UK General Elections (`weight-profiles.md` §0). S0 (static re-run) needs no preference model; S1 needs the full BES and MRP pipeline.

### Decision

Release 1 scores configurations C01–C11 in the Commons profile. Phase 2 publishes S0 results on 2024 data, labelled as lower bounds. Phase 3 adds S1 and further reference elections. Devolved, council and executive profiles follow, mainly as evidence for Commons grades.

### Consequences

- An end-to-end result arrives early.
- Under S0, preferential configurations (AV, STV, AV+, TRS) degenerate to first preferences only. Their S0 results must be flagged as uninformative on the preference axes, or withheld until S1. See open question Q-R1.
- Grades for Commons configurations stay at C until evidence profiles land, apart from the A grade observed for FPTP.

---

## ADR-0009: `just` as the task runner

- **Date**: 2026-11-11
- **Status**: Proposed

### Context

Two languages and a site need one entry point for setup, pipeline, tests and verification.

### Decision

A `justfile` at the repository root holds the canonical commands.

### Consequences

- Readable recipes and one command to learn.
- Adds a small dependency (`brew install just`). A Makefile is the fallback if this is unwelcome.

---

## ADR-0010: Static host

- **Date**: 2026-11-11
- **Status**: Proposed (undecided)

### Context

Any static host will do. Candidates are Cloudflare Pages and GitHub Pages.

### Decision

<!-- TODO: choose. -->

### Consequences

<!-- TODO -->

---

## ADR-0011: No third-party analytics or scripts on the site

- **Date**: 2026-11-11
- **Status**: Proposed

### Context

The site's credibility depends on neutrality and a strict Content Security Policy (CSP). Analytics add trackers, cookie notices and a third-party script.

### Decision

No analytics scripts, no external fonts and no third-party requests. If traffic figures are wanted, use the host's server-side, cookie-free statistics.

### Consequences

- Simpler privacy posture and no cookie banner.
- Little insight into how readers use the views.

---

## ADR-0012: Licences: dual MIT / Apache-2.0 for code, CC BY 4.0 for derived data

- **Date**: 2026-11-11
- **Status**: Accepted

### Context

The maintainer chose a public repository with a permissive code licence and an open data licence. Upstream data is mostly under the Open Government Licence (OGL). BES terms apply to anything derived from the survey.

### Decision

Code: `MIT OR Apache-2.0` (the Rust ecosystem convention). Project-produced data (scores, bundles, `runs.sqlite`): Creative Commons Attribution 4.0 (CC BY 4.0). Redistributed upstream data keeps its own licence and attribution. BES-derived aggregates are published only within the BES terms (ADR-0013).

### Consequences

- Maximum reuse by researchers and journalists, with attribution.
- Licence notices must be assembled per source in `data/LICENCES.md`.

---

## ADR-0013: Publish only aggregated preference profiles derived from the BES

- **Date**: 2026-11-11
- **Status**: Proposed (depends on open question Q-S1)

### Context

S1 depends on BES respondent-level data, which is pseudonymised personal data under research terms. Goal G1 wants everything reproducible.

### Decision

Publish `ballot_profile` (constituency-level weighted rankings per posterior draw) with a small-cell pooling rule. Never publish respondent-level data or fitted model artefacts. Reproducibility for S1 is defined as reproducible from the published profiles onward, plus reproducible from scratch for anyone with BES access.

### Consequences

- Most of the pipeline remains fully checkable by anyone.
- Profiles are a step removed from raw data, which critics may attack. The calibration report must be thorough.
- If the BES terms forbid even aggregates, S1 reproducibility drops to "BES-registered users only", and this ADR is superseded.

---

## ADR-0014: Geography register: GSS codes, frozen vintages and typed relationships

- **Date**: 2026-11-11
- **Status**: Accepted

### Context

UK geography is a mosaic with no common nesting. Westminster constituencies are drawn by four boundary commissions (England, Scotland, Wales, Northern Ireland). Devolved seats, council wards and electoral divisions are drawn by further bodies, and statistical geographies come from three census agencies (ONS for England and Wales 2021, NRS for Scotland 2022, NISRA for Northern Ireland 2021). Every layer has vintages, and English local government reorganisation keeps moving council boundaries. Postcodes nest in nothing. Joining layers by name, or mixing vintages silently, would corrupt the MRP post-stratification frame and sub-metric G3 without any visible error.

### Decision

1. **Identity is GSS code plus vintage.** No join by name anywhere. Names are display data only.
2. **Geography register.** Every area type the project uses is declared in `data/geographies.toml` and the `geography_layer` table: layer ID, GSS entity prefixes, drawing body, vintage (valid from and to), source and licence.
3. **Typed relationships.** Every cross-layer link is `exact` (nests), `best_fit_population` (built from census output areas or data zones) or `area_weighted` (split by land area). Each derived value records the relationship type it rests on.
4. **Official lookups first.** Use ONS, NRS and NISRA published lookups. Compute a spatial overlay only where no official lookup exists, and mark the result as derived.
5. **One frozen vintage per profile.** The spec fixes each profile's layers. For the Commons profile: constituencies PCON 2024; local authorities **as at the GE2024 polling day (2024-07-04)** for G3; census England and Wales 2021, Scotland 2022, Northern Ireland 2021 for MRP.
6. **Each contest counts on its own boundaries.** Devolved and council golden tests use their own layer and vintage. No mapping to constituencies is needed to count them.
7. **Postcodes are out of the pipeline.** If the site ever offers "find my constituency", it uses the ONS postcode directory's best fit and labels it as approximate.

### Consequences

- G3 is reproducible but describes councils as they were in July 2024. Later reorganisations are a known limitation, stated wherever G3 appears.
- The MRP frame needs three nation-specific census-to-constituency fits, each recorded with its relationship type.
- Adding any new layer (Holyrood 2026, Senedd 2026, council wards, police force areas) starts with a register entry.

### Amendment (2026-11-11): `partial` links

The ONS ward → constituency lookup (July 2024) flags 388 wards as split between constituencies but publishes no shares. Such links are recorded as `relation = 'partial'` with `share` NULL: an official statement that part of the area lies in the target, nothing more. A share may be added later only as a separate, derived `area_weighted` or `best_fit_population` link. No share is ever guessed.

### Amendment (2026-11-11): sources without codes

Some results sources publish names only (the Senedd Research 2026 briefing). Such a source is matched to the official names and codes of its layer (the `area` table, loaded from an ONS names-and-codes file) once, at ingest. The match ignores only case and spacing, must pair every area exactly once, and stops ingest otherwise. Nothing downstream joins by name.

Where a source's spelling differs from the official name by more than case and spacing, the loader lists the pair explicitly (the EMB Holyrood 2021 workbook: "Orkney", "Shetland", "South of Scotland", "West of Scotland"). No fuzzy matching.

Scottish council wards (2022): the EMB results workbook names wards with council-specific decoration ("Ward 1 - Boness and Blackness", "Airyhall/Broomhill/Garthdee Ward"). The match is made within each council, after a fixed normalisation that also drops a "Ward N" prefix or "Ward" suffix, punctuation, and reads "&" as "and"; it must still pair all 355 wards one-to-one. Two names differ by more and are listed (EMB "Sgìr’ Ùige agus Carlabhagh", "Eilean a' Cheò"). Ballot files are tied to wards by their candidate names, not ward names, and each pairing is then confirmed by ballot and first-preference totals.
