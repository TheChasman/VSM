# Voting System Metrics: Specification v0.1

Written: 11 November 2026. Built from `research/ers-critique.md`, which diagnoses the Electoral Reform Society (ERS) star ratings and proposes ten axes. This document turns those axes into measurable metrics: each has a definition, a formula, a data source, fixed normalisation anchors and an office applicability rule.

Status: draft specification. Nothing here has been computed on real data yet, except the ballot expressiveness worked example (§4.4), which is pure arithmetic.

Changelog: 11 Nov 2026, E3 Contestability added to axis 2 (26 sub-metrics). Fair Fight view added (see `research/weight-profiles.md` §5).

---

## 1. Design principles

Each principle answers a specific fault in the critique (section numbers refer to `ers-critique.md`).

| # | Principle | Fixes |
|---|---|---|
| P1 | **Every score comes from a formula and named data.** No editorial scores. Where judgement cannot be avoided (a rubric), the rubric items are binary and published. | 1.1, 1.9 |
| P2 | **Score configurations, not families.** "STV" is not scorable; "STV, 3–5 member districts, Droop quota, Weighted Inclusive Gregory transfers" is. | 1.2 |
| P3 | **One concept, one axis.** Each property of a system is measured once. A correlation audit (§6.4) flags axes that turn out to measure the same thing. | 1.3, 1.4 |
| P4 | **Three kinds of fairness, shown side by side.** Fairness to parties (axis 1), to voters (axes 2, 3, 5) and to places (axis 7). None is privileged. | 1.10 |
| P5 | **Fixed anchors, not relative ranking.** Scores are normalised against fixed, published anchors, so adding or removing a system never changes another system's score. | 1.6 |
| P6 | **Uncertainty and evidence are part of the score.** Every score is a median with a 10th–90th percentile band and an evidence grade. | 1.6 |
| P7 | **N/A is not zero.** Axes that do not apply to an office are excluded, not penalised. | 1.7 |
| P8 | **No default total.** Users choose weights; the specification reports Pareto sets and weight-sensitivity instead of a single ranking. | 1.9 |
| P9 | **Descriptive properties are not scored as good or bad** unless almost everyone would agree on the direction. | 1.5 |
| P10 | **Pre-registration.** Methods, anchors and reference data are fixed and published *before* any configuration is scored. Changes after that are versioned and logged. | 1.9 |

---

## 2. Configuration schema

Every scored system is a configuration with these parameters. A parameter that does not apply is recorded as `null`.

| Parameter | Values | Notes |
|---|---|---|
| `family` | FPTP, AV, SV, TRS, Bloc, Limited, STV, List, AMS, AV+, Parallel | Parallel (mixed-member majoritarian) is included for completeness |
| `office` | commons, devolved, council, executive | Drives the profile (§5) |
| `magnitude` | integer or range (e.g. 3–5) | Seats per district, per tier |
| `tiers` | list of tier objects | Mixed systems have a constituency tier and a list tier |
| `tier_ratio` | e.g. 57:43 | Constituency seats : list seats |
| `compensatory` | true / false | AMS true; Parallel false |
| `list_type` | closed, open, semi-open (with quota rule) | |
| `formula` | D'Hondt, Sainte-Laguë, modified Sainte-Laguë, Hare-LR, Droop quota | |
| `threshold` | % and level (district, region, national) | Legal threshold, if any |
| `preferences` | 1, 2, n, unlimited | Max preferences per ballot |
| `transfer_rule` | WIGM, Gregory, random sample, n/a | STV surplus transfer method |
| `votes_per_ballot` | integer | Bloc Vote and Limited Vote |

### 2.1 Default UK configurations (initial scoring set)

| ID | Configuration | Office |
|---|---|---|
| C01 | FPTP, 650 single-member seats, 2023 boundaries | commons |
| C02 | AV, same 650 seats | commons |
| C03 | TRS, top-two run-off, same 650 seats | commons |
| C04 | STV, 3–5 member districts built from whole 2023 constituencies | commons |
| C05 | STV, 5–7 member districts | commons |
| C06 | AMS, Holyrood ratio (57:43), regional D'Hondt, closed lists | commons |
| C07 | AMS, 50:50, national compensation, Sainte-Laguë, closed lists | commons |
| C08 | AV+, Jenkins model (about 83% constituency, county top-ups, personal vote) | commons |
| C09 | Closed-list PR, Senedd 2026 model (6-member districts, D'Hondt) | commons, devolved |
| C10 | Open-list PR, same districts as C09 | commons |
| C11 | Parallel, 50:50, non-compensatory | commons |
| C12 | AMS as used for the Scottish Parliament (73:56) | devolved |
| C13 | AMS as used for the London Assembly (14:11) | devolved |
| C14 | Bloc Vote, 2–3 member wards | council |
| C15 | Limited Vote, 3-member wards, 2 votes each | council |
| C16 | STV, 3–4 member wards (Scottish council model) | council |
| C17 | FPTP | executive |
| C18 | SV | executive |
| C19 | AV | executive |
| C20 | TRS | executive |

---

## 3. Score format

Every metric on every configuration is reported as:

```
score_median  [p10 – p90]  grade
e.g.  62  [55 – 70]  B
```

### 3.1 Uncertainty band
The band covers three sources of variation. Each configuration is run over every combination:

1. **Reference elections:** UK general elections of 2010, 2015, 2017, 2019 and 2024 (devolved and council profiles use their own recent elections).
2. **Behavioural scenario** (§6.2): S0 static re-run, S1 sincere preferences from BES data.
3. **District plans:** for any configuration that needs new districts, 20 valid plans generated by a published, seeded algorithm (§6.3).

The band is the 10th–90th percentile across all runs. A wide band is a finding, not a defect.

### 3.2 Evidence grade

| Grade | Meaning |
|---|---|
| **A** | This configuration has been used in the UK for this office, and the metric is computed from real results. |
| **B** | Used in the UK for another office. Metric partly observed. |
| **B-int** | Observed abroad in a corpus matching the UK on key structural features (see `research/international-evidence.md`). |
| **C** | Modelled only (e.g. AV+, STV for the Commons). |

Where sub-metrics have different grades, the axis takes the **lowest** grade.

---

## 4. The metrics

Ten axes, 26 sub-metrics. Unless stated otherwise, sub-metrics within an axis are equally weighted, and the axis score is their mean. All normalisation anchors are collected in §7.

Notation: `clamp(x)` limits x to the range 0–100. `lin(x; a, b)` maps x linearly so that x = a gives 100 and x = b gives 0. `log(x; a, b)` does the same on a log₁₀ scale.

### A. Representation

#### Axis 1. Proportionality (P): fairness to parties

| ID | Sub-metric | Formula | Score |
|---|---|---|---|
| P1 | Gallagher least-squares index (LSq), UK-wide | √(½ Σ (vᵢ − sᵢ)²), vᵢ and sᵢ = party vote and seat percentages | lin(LSq; 0, 25) |
| P2 | Gallagher LSq, worst nation | Max of LSq computed separately for England, Scotland, Wales and Northern Ireland | lin(LSq; 0, 25) |

- **Why two:** a system can be proportional UK-wide while badly distorting one nation (the critique asks for both views).
- **"Other" parties:** grouped as a single party only if each has under 0.5% of the vote. The grouping rule is fixed in advance because LSq is sensitive to it.
- **Reported, not scored:** Loosemore–Hanby index (cross-check), effective threshold Tₑ = 75% ÷ (M + 1) (Taagepera), which predicts proportionality from district magnitude before any simulation.
- **Data:** House of Commons Library election results.
- **Office:** N/A for executive.

#### Axis 2. Vote effectiveness (E): fairness to voters (does my vote count?)

| ID | Sub-metric | Definition | Score |
|---|---|---|---|
| E1 | Effective ballots | Share of valid ballots that, at any preference or on any ballot paper, were counted for a candidate or list that won a seat in the voter's district or region | % directly |
| E2 | First-preference representation | Share of voters whose first-preference candidate or party won a seat in their district or region | % directly |
| E3 | Contestability | Share of voters living in a *contested* district: one where the margin for the last seat filled is 10 percentage points of the district's valid votes or less | % directly |

- E1 captures **exhaustion**: an SV ballot whose second choice misses the run-off, or an AV ballot that stops ranking before the final round, is ineffective. This is where SV's weakness against AV appears (critique 1.3), not under ballot expressiveness.
- E2 measures whether a voter got their *first* choice; E1 whether their vote did anything at all. For FPTP the two are equal.
- **E3 is the before-the-vote counterpart of E1:** not "did my vote count?" but "could my vote have changed anything?". It is the "not a fair fight" measure.
  - *Margin for the last seat:* single-member, the winner's lead over the runner-up at the final count; multi-member (STV, list), the gap between the last candidate or list elected and the first not elected, at the final stage or quotient comparison.
  - *Mixed systems:* each voter is counted per tier and weighted by the tier's share of seats. A compensatory list tier counts as contested if the last list seat in the region is within the margin.
  - The 10-point threshold is pre-registered (P10) and included in the anchor sensitivity check (5 and 15 points).
  - **Validation, not scoring:** compared with the BES item "How likely is it that your vote will make a difference in terms of which party wins the election in your local constituency?" (0–10), where the configuration is used in the UK.
- Surplus votes for a winner count as effective. An alternative "Droop-wasted" definition (votes beyond a quota count as wasted) is reported, not scored.
- **This is where "having a representative you voted for" now lives.** It is removed from the locality axis (critique 1.4).
- **Data:** results and, for preferential systems, transfer data or BES-simulated ballots.
- **Office:** all. For executive, the "seat" is the single office and the district is the whole area.

#### Axis 3. Equality of vote weight (W): fairness to voters (is my vote worth the same?)

| ID | Sub-metric | Definition | Score |
|---|---|---|---|
| W1 | Malapportionment (MAL) | Samuels–Snyder: ½ Σ \|sᵢ − eᵢ\|, sᵢ = district's share of seats, eᵢ = district's share of registered electors | lin(MAL; 0, 0.10) |
| W2 | Partisan bias | Absolute gap in seat share between the two largest parties when their UK vote shares are equalised by uniform swing, in percentage points | lin(bias; 0, 20) |

- W1 picks up protected constituencies (Orkney and Shetland, Na h-Eileanan an Iar, Ynys Môn, the two Isle of Wight seats) and any magnitude imbalance between multi-member districts.
- W2 measures whether the system treats the main parties symmetrically: equal votes should give equal seats.
- **Data:** ONS and Boundary Commission electorate figures; results.
- **Office:** W1 N/A for executive (one district). W2 N/A for executive.

### B. Voter power

#### Axis 4. Ballot expressiveness (X): what the ballot lets you say

Measured in **bits**: log₂ of the number of distinct valid ballots a voter can cast in a fixed **reference contest**. This replaces an ordinal rubric with a count anyone can reproduce.

**Reference contest:** 6 parties stand. In multi-member configurations, each party fields 3 candidates. Blank ballots are excluded.

| ID | Sub-metric | Definition | Score |
|---|---|---|---|
| X1 | Inter-party expressiveness | Bits of preference over the 6 parties (treating each party as one option) | 100 × bits ÷ 10.93, capped at 100 |
| X2 | Intra-party expressiveness | Bits of preference among the 3 candidates of one party | 100 × bits ÷ 3.91 |

The denominators are the bits of a complete optional ranking (6 options: 1,956 ballots; 3 options: 15 ballots). The cap at 100 means "can express a full ordering"; extra ballot papers beyond that add redundancy, not expressiveness.

- **Ballot-level only.** X measures what the ballot *permits*. Whether that choice actually decides anything is measured under axis 6 (C2). Exhaustion is measured under axis 2.
- **Office:** X2 N/A for executive.

#### 4.4 Worked example (computed)

| Configuration | X1 ballots | X1 bits | **X1** | X2 ballots | X2 bits | **X2** |
|---|--:|--:|--:|--:|--:|--:|
| FPTP | 6 | 2.58 | **24** | 1 | 0 | **0** |
| TRS (two rounds) | 12 | 3.58 | **33** | 1 | 0 | **0** |
| SV | 36 | 5.17 | **47** | 1 | 0 | **0** |
| AMS, closed lists | 36 | 5.17 | **47** | 1 | 0 | **0** |
| AV | 1,956 | 10.93 | **100** | 1 | 0 | **0** |
| AV+ (personal list vote) | ≥1,956 | ≥10.93 | **100** | 4 | 2.00 | **51** |
| Bloc Vote, 3 votes | 83 | 6.38 | **58** | 7 | 2.81 | **72** |
| Limited Vote, 2 votes | 27 | 4.75 | **44** | 6* | 2.58 | **66*** |
| Closed-list PR | 6 | 2.58 | **24** | 1 | 0 | **0** |
| Open-list PR (one preference vote) | 6 | 2.58 | **24** | 4 | 2.00 | **51** |
| STV | ≥1,956 | ≥10.93 | **100** | 15 | 3.91 | **100** |

*Limited Vote X2: any non-empty subset of up to 2 of the 3 party candidates = 6 ballots.

Notes:
- Bloc and Limited Vote X1 count the multisets of parties that can be supported (voting for 2 Labour and 1 Green is one pattern).
- These numbers depend on the reference contest. The contest is fixed by pre-registration (P10); a sensitivity table with 4 and 8 parties will be published alongside.
- Compare the ERS "voter choice" stars: FPTP 2, AV/SV/TRS 3, List 3, AMS 3, STV 5. The bit count separates SV from AV, and closed from open lists, which the stars did not.

#### Axis 5. Sincere-vote safety (S): can you vote honestly without regret?

| ID | Sub-metric | Definition | Score |
|---|---|---|---|
| S1 | Criteria compliance | Share of the criteria below that the configuration's count rule satisfies (binary each) | % directly |
| S2 | Manipulable-voter share | In S1-scenario simulations, share of voters for whom some insincere ballot would have produced an outcome they prefer, holding all other ballots fixed | lin(share; 0, 30%) |

**Criteria list for S1** (fixed; each must be backed by a published citation in the scoring file):

- *Single-winner:* monotonicity, participation, later-no-harm, favourite-betrayal resistance, independence of clones, Condorcet winner.
- *Multi-winner:* house monotonicity, candidate monotonicity, proportionality for solid coalitions (Droop), later-no-harm, independence of clones, participation.

**Validation, not scoring:** where the configuration is used in the UK, S2 is compared with self-reported tactical voting in the British Election Study (BES). If they diverge by more than 10 percentage points, the simulation model is reviewed before publication.

- S1 says whether a failure is *possible*; S2 says how often it *matters* in UK-like conditions. A rule that fails monotonicity in one election in a thousand is not as bad as one that rewards tactical voting in every seat. S2 is the main measure for that reason.
- No system removes tactical voting entirely (Gibbard–Satterthwaite). Proportional systems move the incentive to thresholds; AV removes most compromise voting but can squeeze a centrist out early. S2 measures how often it pays.
- **Candidate upgrade for S2:** the Eggers–Vivyan scalar tactical-incentive measure, computed per BES respondent from like–dislike scores and a model of counterfactual outcomes.
- **Office:** all, using the single- or multi-winner criteria list as appropriate.

#### Axis 6. Voter vs party control (C): who really chooses the person elected?

| ID | Sub-metric | Definition | Score |
|---|---|---|---|
| C1 | Safe seats | Share of members who would still be elected after a 10-point uniform swing against their party (for list members, at their list position; for STV, on the resulting count) | 100 − share |
| C2 | Personal-vote binding rate | Share of seats where voters' candidate-level choices elected a different person from the one party order alone would have elected | % directly |

- C1 measures whether the electorate can remove an individual member. A safe FPTP seat and a top-of-list closed-list place both score as safe.
- C1 (members' view) and E3 (voters' view) are related but not identical: a closed-list district can be contested for its last seat while its top-of-list members are safe. The correlation audit watches the pair.
- C2 is the *outcome* counterpart of X2. Open lists often permit personal votes that rarely change who is elected; this catches that. C2 is 0 by construction for single-member and closed-list seats.
- **Office:** C1 applies to executive (safe office); C2 N/A for executive.

### C. Locality

#### Axis 7. Geographic link (G): fairness to places

| ID | Sub-metric | Definition | Score |
|---|---|---|---|
| G1 | District electorate | Median registered electorate of the voter's district, seat-weighted across tiers | log(electors; 75,000, 7,500,000) |
| G2 | Largest district area | Area in km² of the largest district ("Highlands test") | log(km²; 13,000, 130,000) |
| G3 | Coterminosity | Share of districts that lie wholly within one principal local authority, or consist of whole principal authorities | % directly |

- **Mixed systems:** compute each sub-metric per tier and weight by the tier's share of seats. AMS on the Holyrood ratio gets 57% of its locality from constituencies and 43% from regions.
- **Nothing about who voters supported appears here.** That moved to axis 2.
- STV's locality is now measured, not asserted: a 5-member district in the Highlands will lose points on G2; a 5-member district covering one city may gain on G3.
- **Data:** Ordnance Survey Boundary-Line, ONS electorate statistics, local authority boundaries.
- **Office:** N/A for executive.

### D. Governance

#### Axis 8. Government formation (F)

| ID | Sub-metric | Definition | Score |
|---|---|---|---|
| F1 | Wrong-winner frequency (legislatures) | Share of runs in which the party with most votes does not win most seats | lin(freq; 0, 25%) |
| F1′ | Condorcet efficiency (executives) | Share of BES-simulated runs in which the Condorcet winner, if one exists, is elected | % directly |
| F2 | Formation profile | Effective number of parliamentary parties (ENPP), probability of a single-party majority, probability of a manufactured majority (majority of seats on under 50% of votes) | **Reported, not scored** |

- F1 is scored because almost nobody defends a wrong-winner outcome. UK reference cases: 1951 and February 1974.
- F2 is **descriptive** (P9). Some people value single-party majorities; others value coalitions. A user can set a target (for example "ENPP near 3") and the tool will score distance from it, but no default direction is imposed.

#### Axis 9. Accountability (A)

| ID | Sub-metric | Definition | Score |
|---|---|---|---|
| A1 | Removal responsiveness | Across runs where the largest governing party loses 5 or more points of vote share, the share in which it leaves government | % directly |

- Requires a government-formation model. **Default model:** minimum connected winning coalition on a left–right scale from Chapel Hill Expert Survey party positions. The model is a declared assumption and the evidence grade for A1 is never higher than B.
- Individual accountability (can voters remove a *member*) is already in C1 and is not counted again.
- **Office:** applies to all; for executive, "government" is the office-holder's party.

### E. Practicality

#### Axis 10. Simplicity and integrity (I)

| ID | Sub-metric | Definition | Score |
|---|---|---|---|
| I1 | Rejected ballots | Rejected ballots as a share of all ballots cast | lin(%; 0, 5%) |
| I2 | Count time | Median hours from close of poll to final declaration, per district | log(hours; 6, 72) |
| I3 | Auditability | Share of five binary items met (below) | % directly |

**I3 items:**
1. Ballot-level or preference-level data is published, so anyone can re-run the count.
2. The count can be done by hand without software.
3. The count is deterministic (no random selection of surplus papers).
4. A recount of the same papers must give an identical result.
5. District results can be verified without waiting for central aggregation.

- **Data:** Electoral Commission post-election reports, returning officer declarations, Scottish council and Northern Ireland count records. UK reference points: the 2007 Scottish Parliament combined-ballot problems; Northern Ireland STV counts.
- For grade C configurations, I1 and I2 borrow figures from the closest observed configuration and the grade is noted.
- **Reported, not scored:** cost per elector (data too patchy to compare fairly).

### Reported observations (never scored)

| Observation | Source | Reason not scored |
|---|---|---|
| Diversity: share of women and ethnic-minority members vs population | House of Commons Library, devolved parliaments | Driven mainly by party candidate selection |
| Turnout | Electoral Commission | Confounded by culture, competitiveness and era |
| Cost per elector | Electoral Commission, local authority accounts | Inconsistent accounting across bodies |
| ENPP and majority probabilities | Simulation | Descriptive (axis 8, F2) |
| Loosemore–Hanby index, effective threshold | Simulation | Cross-checks on axis 1 |

---

## 5. Office profiles

✓ = scored, — = N/A (excluded, not zero), R = reported only.

| Sub-metric | Commons | Devolved | Council | Executive |
|---|:-:|:-:|:-:|:-:|
| P1 Gallagher UK-wide | ✓ | ✓ (nation-wide) | ✓ (authority-wide) | — |
| P2 Gallagher worst nation | ✓ | — | — | — |
| E1 Effective ballots | ✓ | ✓ | ✓ | ✓ |
| E2 First-preference representation | ✓ | ✓ | ✓ | ✓ |
| E3 Contestability | ✓ | ✓ | ✓ | ✓ |
| W1 Malapportionment | ✓ | ✓ | ✓ | — |
| W2 Partisan bias | ✓ | ✓ | ✓ | — |
| X1 Inter-party | ✓ | ✓ | ✓ | ✓ |
| X2 Intra-party | ✓ | ✓ | ✓ | — |
| S1 Criteria | ✓ | ✓ | ✓ | ✓ (single-winner list) |
| S2 Manipulable voters | ✓ | ✓ | ✓ | ✓ |
| C1 Safe seats | ✓ | ✓ | ✓ | ✓ |
| C2 Personal-vote binding | ✓ | ✓ | ✓ | — |
| G1–G3 Locality | ✓ | ✓ | ✓ | — |
| F1 Wrong winner | ✓ | ✓ | ✓ | — |
| F1′ Condorcet efficiency | — | — | — | ✓ |
| F2 Formation profile | R | R | R | — |
| A1 Removal responsiveness | ✓ | ✓ | ✓ | ✓ |
| I1–I3 Practicality | ✓ | ✓ | ✓ | ✓ |

Executive covers elected mayors and Police and Crime Commissioners (PCCs). Configurations are compared only within an office profile.

---

## 6. Method

### 6.1 Data sources

| Source | Used for |
|---|---|
| House of Commons Library election results | Votes and seats, all reference elections |
| British Election Study (BES) Internet Panel | Party like/dislike scales → simulated rankings (S1 scenario); tactical-voting self-reports (S2 validation); "will my vote make a difference" (E3 validation) |
| ONS electoral statistics; Boundary Commissions | Electorates (W1, G1) |
| Ordnance Survey Boundary-Line | Areas and boundaries (G2, G3, district building) |
| Scottish council STV ballot data; Electoral Office for Northern Ireland | Observed preferential behaviour, exhaustion, transfer patterns |
| Electoral Commission reports | Rejected ballots, count times (I1, I2) |
| Chapel Hill Expert Survey | Party positions for the coalition model (A1) |
| International corpora | See `research/international-evidence.md` |

### 6.2 Behavioural scenarios

- **S0, static re-run:** the actual votes, counted under the new rules. Voters cast those votes tactically for FPTP, so S0 understates change. Labelled a **lower bound**.
- **S1, sincere preferences:** each BES respondent's ballot is rebuilt from their party like/dislike scores, weighted to the actual result in each nation. Used for all preferential and multi-ballot configurations, and for S2 and F1′.
- A strategic-equilibrium scenario is out of scope for v0.1; noted as a known limitation.

### 6.3 Building new districts

Multi-member districts are built by joining whole 2023 constituencies that are adjacent and within the same nation and, where possible, the same county or region. The algorithm is published and seeded. Twenty valid plans per configuration feed the uncertainty band, so no single map choice drives the result.

### 6.4 Correlation audit

After scoring, compute the correlation between every pair of axes across all configurations in a profile. Any pair with |r| > 0.8 is flagged as possibly measuring the same thing, and the finding is published. Expected candidates to watch: X2 with C2; E2 with P1; E3 with C1.

### 6.5 Aggregation (optional, user-driven)

Superseded by `research/weight-profiles.md` §5, which lists the published views (including the Fair Fight view). No total score is published by default.

### 6.6 Governance

- The specification, anchors, reference contest and data list are frozen and published before scoring (P10).
- Any later change gets a version number and a changelog entry stating which scores moved.
- Scorers declare any campaign affiliation. A configuration's sponsor cannot be its only scorer.
- Code and intermediate data are public, so any score can be reproduced.

---

## 7. Anchor register

Anchors are conventions, so they are listed in one place with a reason. A sensitivity check (anchor ±20%) is published with the first results.

| Sub-metric | Scores 100 at | Scores 0 at | Rationale |
|---|---|---|---|
| P1, P2 Gallagher LSq | 0 | 25 | Just above the highest post-war UK value (about 24, in 2024) |
| W1 MAL | 0 | 0.10 | Well outside the UK ±5% quota rule; typical of strongly malapportioned systems |
| W2 Partisan bias | 0 pts | 20 pts | A 20-point seat gap at equal votes is a decisive bias |
| X1, X2 | Full optional ranking | One option | Defined by the reference contest |
| S2 Manipulable voters | 0% | 30% | Nearly a third of voters with an incentive to vote insincerely |
| G1 District electorate | 75,000 | 7,500,000 | Roughly the 2023 UK quota (about 73,400); and roughly a large English region |
| G2 Largest district area | 13,000 km² | 130,000 km² | Statutory maximum constituency area (Parliamentary Constituencies Act 2020); and roughly the area of England |
| F1 Wrong winner | 0% | 25% | One election in four |
| I1 Rejected ballots | 0% | 5% | Above any recent UK election |
| I2 Count time | 6 h | 72 h | Overnight count vs three days |

Percentage-based sub-metrics (E1, E2, E3, S1, C2, G3, F1′, A1, I3) need no anchors. E3's contested-margin threshold (10 points) is a convention, tested at 5 and 15 points. C1 is scored as 100 minus the safe-seat share.

---

## 8. Mapping back to the critique

| Critique finding | Where it is addressed |
|---|---|
| 1.1 Not reproducible | P1, P10, §6.6 |
| 1.2 Families not configurations | §2 schema, §2.1 defaults |
| 1.3 Contradictions (AV vs SV, AMS vs AV+, STV locality) | X1 separates SV from AV; E1 captures SV exhaustion; G measures AMS and AV+ tier by tier; G2 tests STV districts |
| 1.4 Double counting | "Rep you voted for" only in E; locality purely geographic; correlation audit |
| 1.5 Missing criteria | Axes 2, 3, 5, 6, 8, 9, 10 |
| 1.6 Coarse scale | 0–100, bands, grades |
| 1.7 Offices mixed | §5 office profiles |
| 1.8 Bloc Vote unscored | C14, C15 |
| 1.9 Conflict of interest | P10, §6.6 |
| 1.10 Narrow fairness | P4: parties (1), voters (2, 3, 5), places (7) |

---

## 9. Known limitations

- **S1 sincere ballots are synthetic.** BES like/dislike scales are a proxy for rankings, and long ballots are thinner in the data. Many respondents tie their top two parties; the tie rule is declared.
- **No strategic equilibrium.** Real voters and parties adapt to a new system over several elections; neither scenario models that.
- **A1 depends on a coalition model.** Different models could change the scores; the model is declared and graded B at best.
- **Reference contest choices** (6 parties, 3 candidates) shape X. Sensitivity tables mitigate but do not remove this.
- **E3 depends on a margin threshold.** Sensitivity at 5 and 15 points mitigates this.
- **Grade C configurations** (AV+, STV and List PR for the Commons) rest on simulation; their bands should be read as wide.

## 10. Next steps

1. Populate the S1 criteria table with citations.
2. Build the district-generation algorithm and test it on Wales (small, mixed urban and rural).
3. Score the executive profile first (C17–C20): fewest axes, most observed data.
4. Run the commons profile on 2024 data under S0 as a first lower-bound pass.
