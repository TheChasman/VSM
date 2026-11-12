# Roadmap

Effort estimates are left as TODO. No code exists yet, and estimates would be guesses.

## Phases

### Phase 0: Methodology v0.2 and pre-registration readiness

- **Goal**: Bring the methodology to a freezable state for the Commons profile, and encode it as `spec/*.toml`.
- **Exit criteria**:
  - The v0.2 changes from `additional-research.md` §4 are applied: C09 grade A (devolved); C16 rewording; 1929 added to the wrong-winner reference cases; G2 note on the largest real seat (11,632 km²); S1 table referenced, with the N/A rule.
  - The Commons-relevant open methodology decisions are resolved (M-1 to M-6 below).
  - `vsm spec check` passes on the full Commons spec.
  - The software decisions marked Proposed in [10_DECISIONS.md](10_DECISIONS.md) are accepted or rejected.
- **Estimated effort**: <!-- TODO -->
- **Status**: In progress (research complete to 2026-11-11)

### Phase 1: Foundations

- **Goal**: Repository, toolchains, ingest and the count library, proven against real results.
- **Exit criteria**:
  - The repository is public, with the licence files and the `justfile`.
  - `ingest` and `geography` build `reference.sqlite` for 2024 (and notional 2019), with checksums.
  - `count` passes the golden tests: 2024 First Past the Post (FPTP), Senedd 2026 D'Hondt, Holyrood 2021 Additional Member System (AMS), and Scottish 2022 Single Transferable Vote (STV) wards.
  - X1 and X2 reproduce methodology table §4.4.
  - The local checks (`just all`, pre-commit hook) run the fixture pipeline. No hosted CI (owner standing order).
- **Estimated effort**: <!-- TODO -->
- **Status**: Done except the fixture pipeline (2026-11-12, merged to `main`). Met: public repository (history audited: no private data, no secrets), `justfile` and licence files; `reference.sqlite` built from pinned checksums and reproduced by `just verify`; all four golden tests; X1 and X2. Deferred: the fixture pipeline, because the stages it runs (`districts`, `run`, `metrics`, `views`, `publish`) are built in Phase 2. It becomes a Phase 2 exit criterion.

### Phase 2: Freeze, then Commons S0 lower bound

- **Goal**: The first published scores.
- **Exit criteria**:
  - Spec v1.0 is frozen and tagged **before** any scoring run is published.
  - The district generator is validated on Wales.
  - C01–C11 are scored on GE2024 under S0 across 20 plans, with preferential configurations handled as ADR-0008 decides.
  - Pareto, Punter and Fair Fight views are generated.
  - A minimal site is published, with S0 results clearly labelled as lower bounds.
  - The local checks (`just all`) run the Wales fixture pipeline (carried over from Phase 1).
- **Estimated effort**: <!-- TODO -->
- **Status**: Not started

### Phase 3: Sincere preferences (S1) and more reference elections

- **Goal**: Credible results for preferential configurations.
- **Exit criteria**:
  - The British Election Study (BES) pipeline is complete: ranking derivation, declared tie rule, multilevel regression and post-stratification (MRP), calibration against Scottish council ballots, and a calibration report.
  - S2 manipulability search is implemented and validated against BES self-reported tactical voting (within 10 points, as methodology axis 5 requires).
  - E3 is validated against the BES "will my vote make a difference" item.
  - Reference elections 2010–2019 are added (subject to notional results availability).
  - Weight profiles and weight-space sensitivity are published.
  - Hemicycle arcs with uncertainty shading and hex maps are complete.
- **Estimated effort**: <!-- TODO -->
- **Status**: Not started

### Phase 4: Release 1.0

- **Goal**: A complete, verifiable public release of the Commons profile.
- **Exit criteria**:
  - The anchor ±20 % sensitivity check and the E3 margin sensitivity (5 and 15 points) are published.
  - The correlation audit is published.
  - `just verify` passes from a clean checkout on a second machine.
  - The release archive is signed.
  - The method page is complete, with the comparison against the Electoral Reform Society (ERS) stars.
- **Estimated effort**: <!-- TODO -->
- **Status**: Not started

### Phase 5: Evidence profiles and international corpora

- **Goal**: Raise Commons grades from C towards B and B-int.
- **Exit criteria**:
  - Devolved (C09, C12, C13), council (C14–C16) and executive (C17–C20) profiles are scored. The executive profile uses the 2000–2021 Supplementary Vote (SV) and 2024–2025 FPTP natural experiment.
  - Backward re-counts are complete for Australia, New South Wales (NSW) and Queensland, New Zealand Mixed Member Proportional (MMP), and Holyrood and Senedd.
  - The AV+ proxy pipeline is calibrated against B and B-int ballots.
- **Estimated effort**: <!-- TODO -->
- **Status**: Not started

## Open questions

### Methodology (must resolve before the Commons freeze)

| ID | Question | Source |
|----|----------|--------|
| M-1 | Keep S1 criteria compliance as a scored half of axis S, down-weight it, or move it to reported-only? | `additional-research.md` §1.4.1 |
| M-2 | Resolve the S1 cells for AMS, AV+ and Parallel (decoy lists; possible negative vote weight) | §1.3 |
| M-3 | Commons list regions and the overhang rule for C06 and C07 | [05_COMPONENTS.md](05_COMPONENTS.md), count |
| M-4 | S2 computation method (search over voter types rather than individual voters) and A1 swing method under S0 | 05, metrics |
| M-5 | G3 coterminosity basis (area or electors) | 05, geography |
| M-6 | STV nomination rule and intra-party ordering under S1 | 05, runs |
| M-7 | Condorcet double-count between S1 and F1′ (executive only; deprioritised) | §1.4.2 |
| M-8 | Minimum matching-feature set for B-int (M1 + M2 + M4?); STV ward collapse rule; Australian data use | `international-evidence.md` §6 |

### Software and data

| ID | Question |
|----|----------|
| Q-R1 | Under S0, publish preferential configurations flagged as uninformative, or withhold them until S1? |
| Q-S1 | Do BES terms permit publishing constituency-level derived preference profiles? What small-cell threshold applies? |
| Q-P1 | Preference-model library and form (PyMC, bambi, statsmodels, or R's glmmTMB) |
| Q-D1 | District generator: keep region-growing or move to a Markov chain sampler; magnitude distribution for ranges such as 3–5 |
| Q-H1 | Static host and domain (ADR-0010) |
| Q-H2 | Source and licence of the 2024 constituency hex layout |
| Q-I2 | Count-time source for I2 (Press Association (PA) logs or returning-officer notices) |
| Q-N1 | Northern Ireland: STV ballot-level data availability; how Northern Ireland's 18 seats are districted under each configuration |

## Deferred ideas

- Strategic-equilibrium behavioural scenario. Out of scope for v1.
- Zenodo deposit with a Digital Object Identifier (DOI) for each release.
- A second, independent spec reviewer for post-freeze changes.
- User-defined configurations on the site. This would need a WebAssembly (Wasm) build of `vsm-count`; the static-only principle allows it.
- Formation-target scoring (for example, "probability of a single-party majority at or above 50 %") as an opt-in on the Stable government profile.

## Dependencies on external work

- **BES Internet Panel** wave releases (Reform UK coverage is better in later waves).
- **Commons Library** publishing 2024 declaration times (blocks I2 for GE2024).
- **Notional results** on 2023 boundaries for 2010–2017 (needed before those elections can be reference elections under the same boundaries).
- **Local-authority SV second-count statements** being collated (Phase 5, E1 for SV).

## Known risks to the plan

| Risk | Early warning | Response |
|------|---------------|----------|
| BES terms forbid publishing aggregates | Q-S1 answer | Supersede ADR-0013; narrow G1 for S1 |
| Preference model fails calibration against Scottish ballots | `calibration_error` above tolerance | Publish S0 only, with S1 marked experimental; widen bands |
| S2 too slow at Commons scale | Benchmark in Phase 3 | Reduce to voter-type search; sample districts; declare the approximation |
| District generator cannot satisfy Northern Ireland or Highlands constraints | Retry counts | Configuration-specific magnitude exceptions, declared in the spec |
| Scope creep into other profiles before the Commons release | Phase 2 slipping | Hold to ADR-0008 |
| Accusations of bias | Public reaction | Lean on pre-registration, sensitivity analysis and the absence of an overall winner. Invite rebuilds |
