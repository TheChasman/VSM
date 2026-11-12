# Components

A detailed spec per component. Each follows the same template so components are easy to compare. Python components live in `py/vsm_py/`, Rust crates in `crates/`, and the site in `site/`.

| Component | Language | Location |
|-----------|----------|----------|
| spec | Rust | `crates/vsm-spec` |
| ingest | Python | `py/vsm_py/ingest/` |
| geography | Python | `py/vsm_py/geography/` |
| preferences | Python | `py/vsm_py/preferences/` |
| districts | Rust | `crates/vsm-districts` |
| count | Rust | `crates/vsm-count` |
| runs | Rust | `crates/vsm-runs` |
| metrics | Rust | `crates/vsm-metrics` |
| views and publish | Rust | `crates/vsm-views` |
| CLI | Rust | `crates/vsm-cli` (binary `vsm`) |
| site | Svelte | `site/` |

---

## spec

### Purpose

Parses, validates, canonicalises and hashes the methodology files in `spec/`. Every other Rust crate gets configurations, anchors, profiles and weights from here, and only from here. Python stages read the same TOML through a thin loader that checks the hash. The component does **not** decide methodology. It enforces that whatever is frozen is complete and unchanged.

### Interfaces

- **Inbound**: `spec/*.toml`, `spec/schema/*.json`
- **Outbound**: Typed structs (`Configuration`, `Anchor`, `Profile`, `WeightProfile`, `CriteriaTable`, `GradeTable`). `spec_hash()`.

### State

Stateless. Reads files at start-up.

### Concurrency model

None. Loaded once and shared immutably (`Arc`).

### Failure modes

| Failure | Detection | Response |
|---------|-----------|----------|
| Spec edited after freeze | Hash differs from `spec/FROZEN` | Exit 3. The message names the changed file |
| Missing anchor or parameter | Schema validation | Exit 1 with the field path |
| `unresolved` criteria cell in a frozen profile | Validation | Freeze refused |

### Dependencies

`serde`, `toml`, `jsonschema`, `sha2`. Versions pinned in `Cargo.lock`.

### Configuration surface

`VSM_SPEC_DIR` (default `./spec`).

### Open questions

- Canonicalisation rule for hashing: sorted keys and normalised floats (proposed), or hashing the raw bytes (simpler, but whitespace-sensitive)?

---

## ingest

### Purpose

Fetches every source listed in `data/sources.toml`, verifies the SHA-256 checksum and normalises the data into `reference.sqlite`. It maps party names to the project registry and applies the "Other" grouping rule (each party under 0.5 % of the vote) as a **separate derived view**, never by overwriting raw parties. It does **not** model or impute anything.

### Interfaces

- **Inbound**: Commons Library results CSVs (2024, and notional 2019 on 2024 boundaries; 2010–2019 later); Office for National Statistics (ONS) and Boundary Commission electorates; Ordnance Survey (OS) Boundary-Line; British Election Study (BES) Internet Panel files (to `data/private/`); Senedd 2026 results; Scottish council Single Transferable Vote (STV) ballot files.
- **Outbound**: `election`, `constituency`, `party`, `candidate_result`, `source` tables.

### State

`data/raw/`, `data/private/`, `reference.sqlite`.

### Concurrency model

Downloads run concurrently (bounded at four). Database writes run in a single thread inside one transaction per source.

### Failure modes

| Failure | Detection | Response |
|---------|-----------|----------|
| Checksum mismatch | SHA-256 comparison | Stop. Never overwrite. Report the old and new hashes |
| Unknown party spelling | Not found in the registry | Stop and list the unmapped names. The maintainer adds aliases |
| Vote totals disagree with the source's own totals | Cross-check | Stop |
| Source offline | HTTP error | Fall back to the archived copy if present; otherwise stop |

### Dependencies

Python 3.12+, `httpx`, `polars`, `geopandas` (shapefiles), `pyreadstat` (BES `.sav` and `.dta` files). Managed by `uv` with `uv.lock`.

### Configuration surface

`VSM_DATA_DIR`. BES files are placed manually after registration. There are no credentials in configuration ([06_SECURITY.md](06_SECURITY.md)).

### Open questions

- Source for count times (sub-metric I2): Press Association (PA) declaration logs or returning-officer notices (methodology gap §3.2.1).
- Whether Northern Ireland (NI) STV ballot-level data exists (gap §3.2.3).

---

## geography

### Purpose

Derives each constituency's area (km²), the contiguity graph, declared water crossings and local-authority overlap from OS Boundary-Line. It serves sub-metrics G1–G3 and the district generator.

### Interfaces

- **Inbound**: Boundary polygons in `data/raw/`
- **Outbound**: `constituency.area_km2`, `adjacency`, `la_overlap`

### State

Writes to `reference.sqlite` only.

### Concurrency model

Single-threaded. The work runs once per boundary set.

### Failure modes

| Failure | Detection | Response |
|---------|-----------|----------|
| Island seat has no land neighbour | Graph has a disconnected component | Requires an entry in `data/crossings.toml` (for example Na h-Eileanan an Iar, Orkney and Shetland, Isle of Wight, Ynys Môn) |
| Area differs from the published figure | Within ±1 % of reference figures for test seats | Warn above 1 %, fail above 5 % |

### Dependencies

`geopandas`, `shapely`, `pyproj`. Areas are computed in British National Grid (EPSG:27700); NI uses Irish Grid (EPSG:29902).

### Configuration surface

`data/crossings.toml`

### Open questions

- Coterminosity measure for G3: share of area or share of electors? It must be declared in the spec before freeze.

---

## preferences

### Purpose

Builds S1 sincere ballot profiles per constituency. The method follows `research/international-evidence.md` §4:

1. Derive party rankings from BES like–dislike scores (0–10).
2. Break ties with the "closest party" item; otherwise split the ballot equally between orderings. The tie share is reported.
3. Estimate constituency profiles through multilevel regression and post-stratification (MRP), post-stratified to the actual result in each nation.
4. Model truncation and exhaustion, calibrated against observed ranked ballots (Scottish council STV first).
5. Emit N posterior draws so model uncertainty reaches the score band.

It does **not** count elections or compute metrics.

### Interfaces

- **Inbound**: BES respondent files (private), `candidate_result`, `constituency`, post-stratification frame, `spec/scenarios.toml`
- **Outbound**: `ballot_profile` (aggregated only), a calibration report (`reports/calibration.md`) and the model version hash

### State

Model artefacts in `data/private/models/`. These are not published, because they may encode respondent-level information. Published outputs are aggregates only.

### Concurrency model

Model fitting uses the statistical library's own parallelism. Drawing profiles per constituency runs in parallel across processes.

### Failure modes

| Failure | Detection | Response |
|---------|-----------|----------|
| Model fails to converge | R-hat above 1.01 or divergences | Stop. Never emit profiles |
| Calibration miss | Simulated exhaustion or transfer rates outside tolerance against Scottish ballots | Stop. Report the figures. The tolerance is fixed in the spec |
| Party missing from early BES waves (for example Reform UK) | Coverage check | Use the declared wave set. The coverage note travels with the model version |

### Dependencies

`polars`, plus one modelling library. <!-- TODO: choose between PyMC, bambi and a frequentist multilevel model (statsmodels or glmmTMB via R). See open question Q-P1. -->

### Configuration surface

`--draws` (default <!-- TODO: number of posterior draws; it trades runtime against band stability -->), `VSM_PRIVATE_DIR`

### Open questions

- Q-P1: modelling library and model form.
- Calibration tolerance values for transfer and exhaustion rates.
- Whether Australian federal data (which fails matching features M3 and M5) is used only for re-counts, not calibration (`international-evidence.md` §6.3).

---

## districts

### Purpose

Generates seeded, valid multi-member district plans for configurations whose magnitude is greater than one (Single Transferable Vote (STV), list Proportional Representation (PR), and the list tiers of mixed systems). It follows methodology §6.3: join whole 2023 constituencies that are adjacent and within one nation, keeping within one county or region where possible. It produces 20 plans per configuration.

### Interfaces

- **Inbound**: `constituency`, `adjacency`, the configuration's magnitude rule, a seed
- **Outbound**: `district_plan`, `district_member`

### State

Writes plans to `runs.sqlite`.

### Concurrency model

Plans are generated in parallel with `rayon`. Each plan has its own derived seed, so the result is independent of thread scheduling.

### Algorithm (proposed, ADR-0007)

A seeded randomised region-growing search with constraints. Steps:

1. Choose a seed constituency at random within a nation.
2. Grow the district by adding adjacent constituencies, preferring those in the same county, until it reaches the target magnitude.
3. Repeat with the remaining constituencies.
4. Repair leftovers by swapping constituencies at district boundaries.
5. Reject plans that break any hard constraint and retry.

Hard constraints: contiguity, single nation, magnitude within the configured range, and the seat total per nation preserved. Soft preferences: same county, and compactness by perimeter ratio. Validated on Wales first, against the Senedd 2026 pairing of 32 Westminster seats into 16 districts.

### Failure modes

| Failure | Detection | Response |
|---------|-----------|----------|
| No valid plan within the retry budget | Counter | Fail the configuration with a diagnostic (for example, Northern Ireland's 18 seats cannot be split into a magnitude range) |
| Duplicate plans | Hash of membership | Regenerate with the next seed. Report the duplicate rate |

### Dependencies

`rayon`, `rand_chacha` (seedable and portable), `petgraph`.

### Configuration surface

`--plans`, the retry budget in `spec/scenarios.toml`.

### Open questions

- The generator's distribution over plans is not uniform. Should a Markov chain sampler (ReCom-style) replace region-growing? This decides how far the band represents "any reasonable map".
- How to handle magnitude ranges such as 3–5: is the distribution of magnitudes fixed per nation, or sampled?

---

## count

### Purpose

A pure library implementing each electoral rule as a deterministic function from ballots and parameters to seats plus a count log. It is the only place electoral rules exist. It holds no I/O.

### Interfaces

- **Inbound**: `Ballots` (party X-votes, ranked ballots with weights, or two-ballot mixed), `RuleParams`
- **Outbound**: `CountResult { seats, margins, log }`

| Function | Families |
|----------|----------|
| `plurality` | FPTP, constituency tier of AMS and Parallel |
| `irv` | AV, constituency tier of AV+ |
| `contingent` | SV, and TRS under S1 (methodology note: TRS behaves as a contingent vote with sincere rankings) |
| `stv_wigm_droop` | STV |
| `highest_averages(dhondt or sainte_lague)` | List PR, top-up tiers |
| `compensatory_topup` | AMS, AV+ |
| `bloc`, `limited` | Council profile (later) |

### State

Stateless.

### Concurrency model

Pure functions, so callers parallelise freely.

### Failure modes

| Failure | Detection | Response |
|---------|-----------|----------|
| Exact tie for a seat | Rule detects it | Resolve by the rule's declared tie-break (for example, earlier-stage totals). Fall back to a seeded lot and log it |
| Floating-point drift in WIGM transfers | Fixed-point arithmetic | Use fixed-point arithmetic (ADR-0006). Golden tests against official Scottish counts |
| Overhang in compensatory allocation | Detected | Apply the configuration's declared overhang rule. Never an implicit default |

### Dependencies

No third-party crates beyond `serde` for logs.

### Configuration surface

None. Everything arrives through `RuleParams`.

### Open questions

- AMS overhang rule for the Commons configurations (C06, C07): keep overhang seats (Holyrood practice) or levelling seats?
- Rule for collapsing multi-member STV wards to single-member results in backward re-counts (`international-evidence.md` §6.2). This is needed in Phase 5 only.

---

## runs

### Purpose

Expands the run matrix for a profile, builds district-level ballots for each run, calls `count` and persists the outcomes. Under S0 it uses the actual X-votes, and preferential rules degenerate to the votes cast. Under S1 it expands `ballot_profile` rows into district ballots, applying the nomination rule (how many candidates each party fields) and the intra-party ordering rule from the spec.

### Interfaces

- **Inbound**: reference, plans, spec
- **Outbound**: `run`, `seat_outcome`, `count_log`

### State

`runs.sqlite`

### Concurrency model

Runs execute in parallel with `rayon`. A single writer thread receives results over a channel and commits in batches. SQLite uses write-ahead logging (WAL) mode.

### Failure modes

| Failure | Detection | Response |
|---------|-----------|----------|
| Count error | `Result::Err` | Mark the run `failed` with the reason. Aggregation refuses to proceed while any run for that configuration has failed, unless `--allow-partial` is given, and the bundle then states the shortfall |
| Invariant violation (seat total) | `vsm check` | Exit 2 |

### Dependencies

`rusqlite` (bundled SQLite), `rayon`, `crossbeam-channel`.

### Configuration surface

`--profile`, `--config`, `--election`, `--scenario`, `VSM_THREADS`.

### Open questions

- Nomination rule for STV and open-list runs under S1. How many candidates does each party field? Proposed: enough to win one more seat than its Droop entitlement, capped at the magnitude.

---

## metrics

### Purpose

Computes all 26 sub-metrics and the reported-only measures per run, applies the anchor functions, then aggregates per configuration (median, p10, p90) and assigns grades and stars. It also runs the correlation audit (methodology §6.4: flag |r| above 0.8). It implements methodology §4 literally. Any ambiguity found is raised as a methodology issue, not resolved in code.

### Interfaces

- **Inbound**: runs, reference, spec (anchors, profiles, grades, stars, criteria, reference contest)
- **Outbound**: `submetric_value`, `score_summary`, the correlation audit inside `view_result`

### Sub-metric implementation notes

| Group | Needs |
|-------|-------|
| P1, P2 | Party vote and seat shares UK-wide and per nation, after "Other" grouping |
| E1, E2, E3 | Count logs (for exhaustion and last-seat margin). E3 per tier, weighted by seat share, with the 10-point threshold and 5 and 15 point sensitivity |
| W1, W2 | District electorates. Uniform-swing equalisation of the two largest parties' vote shares, then a re-count |
| X1, X2 | Pure arithmetic over the reference contest. Must reproduce methodology table §4.4 exactly |
| S1 | Lookup in `criteria.toml`, with N/A excluded from the denominator |
| S2 | Per-voter manipulability search under S1, holding other ballots fixed. **The most expensive metric**; see the open question below |
| C1 | A re-count after a 10-point uniform swing against each member's party |
| C2 | A comparison of the candidate-level result with the party-order-only result (open lists and STV) |
| G1–G3 | District electorate and area, coterminosity. Tier-weighted for mixed systems |
| F1 | Share of runs with a wrong winner. Computed at aggregation, not per run |
| A1 | Requires the coalition model (minimum connected winning coalition on a left–right scale). Grade capped at B |
| I1–I3 | Observed figures from Electoral Commission data. Borrowed from the nearest observed configuration for grade C, with that noted |

### State

`runs.sqlite`

### Concurrency model

Per-run metrics in parallel. Aggregation is single-threaded per configuration.

### Failure modes

| Failure | Detection | Response |
|---------|-----------|----------|
| Raw value outside the anchor range | Clamp | Clamp and count clamps per sub-metric. Reported (the anchor sensitivity check uses this) |
| N/A sub-metric computed | Profile check | Error. N/A must stay null |

### Dependencies

`statrs` (quantiles, correlation).

### Configuration surface

None beyond the spec.

### Open questions

- S2 is computationally heavy. The proposal is to search a bounded strategy space per voter type (each distinct ranking in a district) rather than per voter, weighting by profile weight. This needs a methodology note before freeze.
- Removal responsiveness (A1) under S0: runs that lose 5 or more points of vote share do not occur naturally within one election. Proposed: synthetic uniform swings, declared in the spec.

---

## views and publish

### Purpose

Builds every published view from `score_summary` and per-run axis scores:

- Profile view
- Pareto set
- Punter view: axis and cluster level, basic and confident floors, with grade-C provisional handling
- Fair Fight view: S2, E3 and C1, unsummed, plus contestability map data
- Weight-profile ranks
- Weight-space sensitivity

It then exports the bundle described in [04_API_CONTRACTS.md](04_API_CONTRACTS.md).

### Interfaces

- **Inbound**: `score_summary`, `submetric_value`, `seat_outcome`, spec
- **Outbound**: `view_result`, `bundle/`

### Weight-space sensitivity

Uniform sampling of the 10-dimensional weight simplex (a flat Dirichlet distribution) with a fixed seed and sample count. For each sample, take each configuration's rank on per-run weighted medians; report the share of samples in which each configuration ranks first. The sample count is fixed in the spec.

### State

Stateless apart from its outputs.

### Concurrency model

Sampling runs in parallel with independent seeded streams.

### Failure modes

| Failure | Detection | Response |
|---------|-----------|----------|
| No configuration passes the Punter floor | Rule outcome | A valid headline, not an error. Publish near misses as the methodology specifies |
| Axis-level and cluster-level Punter leaders differ | Comparison | Publish as a finding |

### Dependencies

`serde_json`, `rand_chacha`.

### Configuration surface

`--out`.

### Open questions

None beyond the methodology's open decisions.

---

## site

### Purpose

A static SvelteKit site (`adapter-static`) that renders the bundle. It has no server and needs no build-time secrets.

### Pages

- **Home**: Punter view headline and Fair Fight summary
- **Configuration page**: axis stars with grade, band bars, hemicycle with uncertainty shading, hex map
- **Compare**: Profile view and Pareto set
- **Weights**: presets plus user sliders, recomputed in the browser from `runs.json`; shows the sensitivity chart
- **Method**: methodology documents, spec hash, changelog, downloads
- **ERS comparison**: the ERS stars beside VSM axes, clearly labelled as the old scheme

### Interfaces

- **Inbound**: `/data/v1/**` at build time (pre-rendered) and at run time (for the weights page)
- **Outbound**: None. No analytics by default (ADR-0011, Proposed)

### State

In-browser only. Slider positions live in the URL query string, so a view can be shared. Optionally they are also kept in `localStorage`.

### Display rules (from the methodology)

- Stars always show the grade beside them (for example `★★★★★ C`).
- A grade C configuration never shows a single crisp arc: dots are shaded by frequency.
- Backward re-counts show two arcs from the same ballots.
- Every chart carries a small footer with the spec version and short hash, so screenshots stay attributable.

### Dependencies

SvelteKit, `d3-shape` and `d3-scale` for arcs and bands. Hex layout uses HexJSON. <!-- TODO: source for the 2024 constituency hex layout (Open Innovations HexJSON is a candidate; confirm licence). -->

### Failure modes

| Failure | Detection | Response |
|---------|-----------|----------|
| Bundle schema major version unknown | Version check | Show a clear incompatibility message |
| `runs.json` too large for mobile | Size budget in `just verify` | Fail the local check above the budget. <!-- TODO: set the budget --> |

### Open questions

- Accessibility target: Web Content Accessibility Guidelines (WCAG) 2.2 AA is proposed. Stars and colour must never be the only carriers of meaning.
