# Weight Profiles and the Star View: Addendum to Specification v0.1

Written: 11 November 2026. Extends `research/new-metrics.md` §6.5 (Aggregation). Nothing in the axis definitions, anchors or method changes. Decisions of 11 November recorded in §7.

---

## 0. Scope decision

**Primary target: replacing First-Past-the-Post (FPTP) for UK General Elections (House of Commons).**

- The **commons profile** (C01–C11) is the main output. Every view below is defined for it first.
- Devolved, council and executive profiles stay in the specification, but mainly as **UK evidence**: they are what lifts a Commons option from grade C (modelled) to grade B (observed elsewhere in the UK). Examples: Holyrood and Senedd for the Additional Member System (AMS) and list PR; Northern Ireland and Scottish councils for the Single Transferable Vote (STV). Non-UK evidence is graded B-int (see `research/international-evidence.md`).
- Executive-profile open decisions (for example the Condorcet double-count in S1) are deprioritised.

---

## 1. Principle: scores and priorities are kept apart

The Electoral Reform Society (ERS) star ratings blend two things into one number: **how a system performs** and **how much each property matters**. The second is a values judgement, and the ERS made it silently (three axes, equal weight, with stable government, accountability and practicality dropped).

This specification separates them:

| Layer | What it is | Who sets it |
|---|---|---|
| Axis scores (0–100, band, grade) | Measurement | Formula and data only (P1, P10) |
| Star bands | Display of the measurement | Fixed, pre-registered thresholds (§2) |
| Weight profiles | Priorities | Named, published presets (§4), or the user |

A configuration's axis scores are identical under every profile. Only the ranking changes.

---

## 2. Star bands (display only)

Each axis score is shown as stars as well as a number, using **fixed bands, the same for every axis** (decision 7.1):

| Stars | Axis score (median) |
|---|---|
| ★★★★★ | 80–100 |
| ★★★★ | 60–79 |
| ★★★ | 40–59 |
| ★★ | 20–39 |
| ★ | 0–19 |

- The bands are pre-registered with the anchors (P10) and included in the ±20% anchor sensitivity check (§7 of the spec). Fixed bands are only a level playing field if anchors are comparably calibrated; the sensitivity check reports any axis where stars flip.
- Stars are always shown **with the evidence grade**, e.g. `★★★★★ C`. A five-star score on grade C is a modelled claim, not an observed one.
- Stars lose information (61 and 79 are both four stars). The number, band and grade stay one click away.

---

## 3. The Punter view (no weights)

How most people read a ratings table: **look for the most five-star scores, but nothing below three stars.** This is formalised as a published decision rule, not a total score, so it is consistent with P8.

### 3.1 Rule

1. **Floor.** The floor (★★★, median ≥ 40) applies to **every scored axis**, labelled by evidence grade (decision 7.2):
   - Below floor on grade A, B or B-int: **fail**. The configuration is not eligible.
   - Below floor on grade C: **provisional fail**. The configuration stays in the table, flagged, and ranks below every configuration that passes cleanly.
   - At or above floor on grade C: **provisional pass**, shown with the C grade.
2. **Rank** eligible configurations by:
   1. number of ★★★★★ axes (more is better), then
   2. number of ★★★★ axes, then
   3. lowest axis score (higher is better).
   Remaining ties are shown as ties.
3. **No eligible configuration?** Report that as the headline finding, then list *near misses*: configurations with the fewest axes below three stars, naming each failing axis, its score and grade.

### 3.2 Confidence variant

The basic floor uses the median. The **confident floor** requires the 10th-percentile score (p10) on every axis to be ≥ 40 too. A configuration that passes the basic floor but fails the confident one is flagged "passes on a typical election, not on a bad one".

### 3.3 Hidden weighting in star-counting (must be shown)

Counting stars across axes treats every axis as equal. The ten axes are not spread evenly across concerns:

| Cluster | Axes | Count |
|---|---|---|
| A. Representation | P, E, W | 3 |
| B. Voter power | X, S, C | 3 |
| C. Locality | G | 1 |
| D. Governance | F, A | 2 |
| E. Practicality | I | 1 |

So star-counting gives representation and voter power three chances each to earn five stars, but locality and practicality only one. That is an implicit weighting of 30:30:10:20:10, and it tends to favour proportional and preferential systems.

**Mitigation:** the Punter view is always published at two levels side by side:

- **Axis level:** the rule above, over 10 axes.
- **Cluster level:** the same rule over 5 cluster scores (each cluster score = mean of its axes).

If the two levels pick different leaders, that is reported as a finding.

Pairs flagged by the correlation audit (spec §6.4, e.g. X2 with C2) are also noted beside the star count, since they can earn the same star twice.

---

## 4. Weight profiles (named presets)

Each profile is a published weight vector over the ten axes (weights sum to 100). The weighted score is computed **per simulation run** and then summarised, so it carries its own band.

| Axis | Even | Proportional | Local link | Stable government | Voter power | Practical | Jenkins 1998 |
|---|--:|--:|--:|--:|--:|--:|--:|
| P Proportionality | 10 | 30 | 10 | 10 | 5 | 10 | 25 |
| E Vote effectiveness | 10 | 20 | 10 | 5 | 20 | 15 | 0 |
| W Equality of vote weight | 10 | 15 | 10 | 10 | 3 | 5 | 0 |
| X Ballot expressiveness | 10 | 5 | 5 | 2 | 25 | 0 | 12.5 |
| S Sincere-vote safety | 10 | 5 | 5 | 3 | 25 | 15 | 0 |
| C Voter vs party control | 10 | 5 | 15 | 5 | 15 | 0 | 12.5 |
| G Geographic link | 10 | 5 | 30 | 10 | 3 | 10 | 25 |
| F Government formation | 10 | 5 | 5 | 25 | 2 | 10 | 12.5 |
| A Accountability | 10 | 5 | 5 | 25 | 1 | 5 | 12.5 |
| I Simplicity and integrity | 10 | 5 | 5 | 5 | 1 | 30 | 0 |

Notes:

- **Jenkins 1998** is the only profile with official UK standing: the Jenkins Commission's four terms of reference (broad proportionality, stable government, extension of voter choice, MP–constituency link), each given 25 and split evenly where it maps to two axes. It is a historical reference, not an endorsement.
- **Stable government** may also switch on a target for the formation profile (F2, normally reported only), e.g. "probability of a single-party majority ≥ 50%", scored as distance from the target. The target is stated with the result.
- **Efficiency** in the sense of cost and count effort sits in the Practical profile (axis I). Cost per elector remains reported, not scored.
- **E3 Contestability** sits inside axis E, so axis weights are unchanged by its addition.
- **Transparency (decision 7.3):** each profile is published with a one-line rationale beside each of its two or three largest weights, so a reader who disagrees can see exactly what they disagree with. No external camp review is required before freezing.
- Weights here are first drafts. Once frozen, they are pre-registered like anchors.

### 4.1 Outputs per profile

For each profile: rank, weighted score with band, and stars per axis. Across all profiles: a single summary table showing each configuration's rank under every profile, so readers can see at a glance whether a system wins only under one set of priorities or across most of them.

The weight-space sensitivity analysis (spec §6.5, view 3) stays: the share of all possible weightings in which each configuration ranks first. This limits how much any single profile can decide.

---

## 5. The Fair Fight view

A named view for the grievance voters feel most directly: **"I had to vote tactically"** and **"my vote couldn't change anything here"** (decision 7.4).

### 5.1 Contents

For each configuration, three sub-metrics side by side, each with score, band, grade and stars:

| Question | Sub-metric | Viewpoint |
|---|---|---|
| Do I have to vote tactically? | **S2** Manipulable-voter share | Voter, at the ballot |
| Could my vote change who wins here? | **E3** Contestability | Voter, before the count |
| Can my area remove its member? | **C1** Safe seats | Member |

### 5.2 Rules

- **Not summed.** The three are shown side by side only. E3 and C1 are related (safe seats and uncontested districts overlap), so adding them would count the same thing twice. The correlation audit result for E3/C1 is printed with the view.
- **No new weights.** The view displays existing sub-metrics; it does not change any axis score or profile.
- **Map companion.** Shown with a constituency hex map shading each district by contestability across runs, so readers see *where* the fight is fair and where it is not. For FPTP, the map is expected to show the contest concentrated in a minority of marginals.
- **Validation printed alongside:** BES self-reported tactical voting (for S2) and the BES "will my vote make a difference" item (for E3), where the configuration is used in the UK.

---

## 6. Updated view list (replaces spec §6.5)

1. **Profile view:** all axis scores, bands, grades and stars.
2. **Pareto set:** configurations no other beats on every axis.
3. **Punter view:** floor of ★★★ (graded, with provisional results), then most ★★★★★; axis and cluster levels; basic and confident floors.
4. **Fair Fight view:** S2, E3 and C1 side by side, with the contestability map (§5).
5. **Weight profiles:** the seven presets above, plus user-defined weights.
6. **Weight-space sensitivity:** share of weightings in which each configuration ranks first.

No single "overall winner" is published. The headline is the combination of views 2, 3 and 6, with the Fair Fight view as the voter-facing summary.

---

## 7. Decisions (11 November 2026)

1. **Star bands:** fixed 80/60/40/20 for every axis. Intuitive and not tunable per axis; the anchor sensitivity check guards comparability.
2. **Punter floor:** applies to every axis. Failures on grade A, B or B-int are fails; failures on grade C are provisional fails, flagged and ranked below clean passes. An A/B-only floor was rejected because it would test FPTP on every axis but novel systems only where evidence exists.
3. **Weight review:** no external review; instead every weight vector is published with rationale lines for its largest weights.
4. **Contestability and Fair Fight:** contestability added as sub-metric E3 under vote effectiveness; Fair Fight adopted as a named, unsummed view of S2, E3 and C1.
