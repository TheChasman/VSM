# Overview

## Purpose

A reproducible, UK-grounded scoring engine and public results site that measures how candidate electoral systems would perform as a replacement for First Past the Post (FPTP) in UK General Elections.

The Electoral Reform Society (ERS) rates eight voting systems with integer stars on three criteria. Those stars cannot be reproduced. They score system families rather than concrete configurations, they count candidate-centred ballots twice, and they come from an organisation that campaigns for the system that scores highest. Voting System Metrics (VSM) replaces editorial stars with measurements. Every score comes from a published formula, named data and fixed anchors. Every score also carries an uncertainty band and an evidence grade.

The software has two halves. The **engine** is a batch pipeline. It ingests UK election, electorate, boundary and survey data. It builds multi-member district plans where a configuration needs them, rebuilds voter preferences from the British Election Study (BES), counts each configuration under each reference election and behavioural scenario, and computes the 26 sub-metrics across ten axes. The **site** is a static SvelteKit build that publishes the results. It shows the Profile, Pareto, Punter, Fair Fight, weight-profile and weight-sensitivity views, with hemicycle arcs and constituency hex maps.

The primary audience is anyone arguing about electoral reform in the UK: campaigners on every side, journalists, researchers and interested voters. The secondary audience is anyone who wants to check a score. They can clone the repository, run one command and get identical numbers.

The first release covers the Commons profile, configurations C01–C11. Devolved, council and executive profiles exist in the methodology mainly as UK evidence that lifts Commons configurations from grade C to grade B. They come later.

## Goals

- **G1 Reproducible.** Any published score can be regenerated bit-for-bit from the tagged repository, the frozen spec files and the public input data (or, for licensed inputs, the documented derived aggregates). Verified by a CI rebuild that compares output hashes.
- **G2 Pre-registered.** Anchors, star bands, reference contest, criteria table, configuration list and weight profiles are frozen and hashed before any configuration is scored. Every published result carries that hash.
- **G3 Configuration-level.** Every scored item is a fully parameterised configuration (methodology §2). The engine refuses to score an under-specified one.
- **G4 Honest uncertainty.** Every score is reported as median, p10–p90 band and evidence grade. Grade C results are never drawn as a single crisp arc.
- **G5 No hidden weighting.** No overall winner is published by default. Weighted results appear only under named, published profiles or user-chosen weights, alongside weight-space sensitivity.
- **G6 Commons MVP.** C01–C11 scored on 2024 data under S0 (static re-run, lower bound), then under S1 (sincere preferences), over 20 seeded district plans where needed.
- **G7 Readable.** A non-specialist can read the Punter and Fair Fight views without a glossary. The specialist can reach every number, band and grade within one click.

## Non-goals

- **Not an advocacy tool.** VSM does not recommend a system. It reports measurements and sets out the trade-offs.
- **No live server.** No accounts, no saved profiles, no server-side API. User weighting runs in the browser on pre-computed per-run axis scores.
- **No strategic-equilibrium modelling** in the first release (methodology §6.2). S0 and S1 only.
- **No forecasting of future elections.** Reference elections are historical: 2010, 2015, 2017, 2019 and 2024 (2024 first).
- **No scoring of diversity, turnout or cost.** These are reported observations only (methodology §4, "Reported observations").
- **No new electoral rules beyond the methodology's families** (FPTP, AV, SV, TRS, Bloc, Limited, STV, List, AMS, AV+, Parallel) without a methodology change.
- **No redistribution of respondent-level BES data** (see [06_SECURITY.md](06_SECURITY.md)).

## Glossary

| Term | Definition |
|------|------------|
| Axis | One of ten measured properties: P Proportionality, E Vote effectiveness, W Equality of vote weight, X Ballot expressiveness, S Sincere-vote safety, C Voter vs party control, G Geographic link, F Government formation, A Accountability, I Simplicity and integrity |
| Sub-metric | A computed measure within an axis (26 in total, e.g. P1 Gallagher index UK-wide, E3 Contestability). Axis score is the mean of its scored sub-metrics |
| Configuration | A fully parameterised voting system (family, office, magnitude, tiers, formula, threshold and so on). IDs C01–C20 |
| Family | The generic system name: FPTP, Alternative Vote (AV), Supplementary Vote (SV), Two-Round System (TRS), Bloc Vote, Limited Vote, Single Transferable Vote (STV), List PR, Additional Member System (AMS), AV+, Parallel |
| Office profile | Commons, devolved, council or executive. Determines which sub-metrics apply. Configurations are compared only within a profile |
| Reference election | A real UK election whose data is re-counted under each configuration |
| Behavioural scenario | S0: static re-run of actual votes (lower bound). S1: sincere ballots rebuilt from BES like–dislike scores |
| District plan | A seeded, valid grouping of whole 2023 constituencies into multi-member districts. 20 per configuration that needs them |
| Run | One count of one configuration × one reference election × one scenario × one district plan |
| Anchor | The fixed raw values that map a sub-metric to 100 and to 0 (methodology §7) |
| Band | 10th to 90th percentile (p10–p90) of a score across all runs |
| Evidence grade | A (UK Commons observed), B (other UK observed), B-int (abroad, structurally matching), C (modelled). An axis takes its lowest sub-metric grade |
| Star band | Display mapping of a score: 80–100 five stars, 60–79 four, 40–59 three, 20–39 two, 0–19 one |
| Punter view | Published decision rule: three-star floor on every axis, then rank by count of five-star axes |
| Fair Fight view | S2, E3 and C1 shown side by side, unsummed, with a contestability hex map |
| Weight profile | A named, published weight vector over the ten axes (Even, Proportional, Local link, Stable government, Voter power, Practical, Jenkins 1998) |
| Pre-registration | Freezing the spec files and publishing their hash before scoring |
| Spec hash | SHA-256 over the canonicalised frozen spec files. Printed on every result |
| Reference contest | Six parties, three candidates each in multi-member configurations. Used for axis X |
| MRP | Multilevel regression and post-stratification: estimating constituency preference profiles from a national survey |
| Backward re-count | Re-counting real ranked or two-vote ballots under FPTP to isolate the mechanical effect |
| Hemicycle (arc) | Arc-of-dots seat chart, with dots shaded by how often each seat falls that way across runs |

## Assumptions

- **A1.** The 2023 Westminster constituency boundaries remain the building blocks for district plans for the life of the first release.
- **A2.** UK Parliament election results (Open Parliament Licence), Office for National Statistics (ONS) electorate statistics and Ordnance Survey (OS) Boundary-Line (Open Government Licence) remain openly licensed and downloadable.
- **A3.** BES Internet Panel data is obtainable for research use, and **derived, aggregated** preference profiles at constituency level may be published even where respondent-level data may not. This needs confirming against the BES licence (open question Q-S1 in [11_ROADMAP.md](11_ROADMAP.md)). If it is wrong, G1 weakens for S1 results to "reproducible from the published aggregates" only.
- **A4.** The full Commons run matrix (11 configurations × up to 5 elections × 2 scenarios × up to 20 plans, i.e. at most 2,200 runs) fits comfortably on a laptop (the M1 MacBook Pro). No cloud compute is assumed.
- **A5.** Per-run axis scores for the Commons profile are small enough (a few megabytes) to ship to the browser, so client-side re-weighting needs no server.
- **A6.** Methodology v0.1 is substantially stable. The v0.2 changes listed in `research/additional-research.md` §4 alter configuration details and the S1 table, not the axis structure.

## Out of context

A reader does not need any of the following before continuing:

- The devolved, council and executive profiles (C12–C20). They are specified in the methodology and deferred in [11_ROADMAP.md](11_ROADMAP.md).
- International backward re-counts and the B-int grade pipeline. They are designed in `research/international-evidence.md` and deferred to Phase 5.
- The AV+ proxy pipeline's calibration against New South Wales (NSW) and Queensland ballots. It belongs to Phase 3.
- Strategic-equilibrium modelling. Out of scope.
- The ERS's own scores, except as a comparison column on the site.
