# International Evidence and Projection Methods: Addendum to Specification v0.1

Written: 11 November 2026. Extends the evidence grades in `research/new-metrics.md` and the floor rule in `research/weight-profiles.md` §3.1.

---

## 0. Why look beyond the UK

The weak point of every Commons projection is the ballot. FPTP records one X, so any projection under a ranked or proportional system has to *invent* the missing preferences. Elections held elsewhere under those systems give us real ballots from real voters.

Rule: a non-UK corpus is admissible when it matches the UK on the **structural features that drive our metrics**, not when it matches "exactly" (nothing does).

### 0.1 Matching features

| Code | Feature |
|---|---|
| M1 | Single-member constituencies (or a single-member tier) |
| M2 | Westminster-style executive formation (government answerable to the lower house) |
| M3 | Voluntary voting |
| M4 | Multi-party competition with geographically concentrated support |
| M5 | Optional (not compulsory) full preferences, where the system is preferential |

Each borrowed data point records which features match. Fewer matches = weaker evidence.

---

## 1. Evidence grades (extended)

| Grade | Meaning |
|---|---|
| A | Observed in UK Commons elections |
| B | Observed in other UK elections (devolved, council, mayoral) |
| **B-int** | **New.** Observed abroad in a corpus matching at least M1, M2 and M4. Matches recorded per data point |
| C | Modelled |

B-int sits between B and C. It is never promoted to B, however good the match.

### 1.1 Floor rule by grade (decision, 11 Nov 2026)

The Punter floor (★★★, median ≥ 40) applies to **every axis**, labelled by evidence:

| Result | Grade A, B or B-int | Grade C |
|---|---|---|
| Below floor | **Fail** | **Provisional fail**: stays in the table, flagged, ranked below clean passes |
| At or above floor | **Pass** | **Provisional pass**: stars shown with the C grade |

Reason: an A/B-only floor would test FPTP (grade A almost everywhere) on all ten axes but test novel systems only where evidence exists. That favours the least-tested systems.

---

## 2. Three ways to get evidence

### 2.1 Backward re-counts: the mechanical effect

Take real ranked or two-vote ballots and re-count them under FPTP. **No preference is invented**: a ranked ballot already contains a first preference. Same voters, same ballots, two rules, so the difference is the system's **mechanical effect**.

**Caveat (always printed):** first preferences under AV/STV are more sincere than FPTP votes, because there is no need to vote tactically. The re-count shows "FPTP applied to what voters actually wanted", not a forecast of a real FPTP election there.

| Corpus | Grade | Re-count |
|---|---|---|
| Australian House of Representatives | B-int (M1, M2, M4; fails M3, M5) | First-preference leader vs AV winner, seat by seat, from published distributions of preferences |
| NSW and Queensland state elections | B-int (M1, M2, M4, M5; fails M3) | As above, with optional preferences, so "just vote 1" exhaustion is observed |
| Scottish Parliament; Senedd to 2021 | B | Constituency seats alone vs final allocation. The constituency tier *is* an FPTP result, within the same election |
| New Zealand MMP (1996 on) | B-int (M1, M2, M3, M4) | As Holyrood |
| Scottish council STV | B | Multi-member wards: needs a declared rule for collapsing to single-member results |
| Irish Dáil (2002 electronic-voting pilot constituencies) | B-int (M2, M3, M4) | Full ballot data |

### 2.2 Natural experiments: the behavioural effect

How voters and parties *change* after reform cannot come from a re-count. Main case: **New Zealand, FPTP to MMP in 1996**. Secondary: Holyrood and Senedd from 1999 versus Westminster results in the same areas.

### 2.3 Forward projections: only where unavoidable

FPTP votes to a ranked or proportional result. Graded C. Every projection must state that it carries FPTP's tactical voting into the baseline.

---

## 3. Benchmark: the ERS 2024 projections

Source: ERS, *A System Out of Step: The 2024 General Election* (methodology appendix).

- **Data:** one YouGov post-election poll, 8–12 July 2024, 8,426 GB adults, asking how people would have ranked **parties**.
- **STV:** FPTP seats merged into 3–6 member constituencies; first preferences rescaled by region from the poll; eliminations transferred using a formula based on the poll's second preferences; third preferences used only in a few cases.
- **AMS:** list votes rescaled by region from the poll; D'Hondt with a 5% regional threshold.
- **Limits:** party rankings, not candidate rankings; region-level, not constituency-level; no calibration against observed transfers; NI not modelled.

Our method must beat this on each limit.

---

## 4. AV+ proxy pipeline (forward, calibrated)

1. **Preferences.** British Election Study Internet Panel (BESIP), party like–dislike scales (0 = strongly dislike, 10 = strongly like) per respondent, with constituency identifiers. Rankings are derived from the scores.
2. **Ties.** Many respondents tie their top two parties. Tie rule (declared): break with the "closest party" item; otherwise split the ballot equally between orderings. Ties are reported as a share.
3. **Down to constituencies.** Multilevel regression and post-stratification (MRP) to estimate preference profiles per constituency.
4. **Count.** AV in each constituency; top-up seats from regional first preferences, Jenkins ratio as the default and other ratios as a sensitivity check.
5. **Calibrate.** Fit transfer and exhaustion rates against observed ranked ballots (Scottish council STV; NSW/Queensland optional preferences). The model is tested, not assumed.
6. **Simulate.** Repeat with sampling and model error to give score bands.

Grade: C, labelled "calibrated against B / B-int ballots".

Also usable from BESIP: the perceived chance of each party winning locally (0–100), and how likely the respondent thinks their vote is to make a difference (0–10). These validate the tactical-voting and contestability measures.

---

## 5. Display: the arc and the map

- **Hemicycle ("arc of dots")** for each configuration's seat result.
- **Uncertainty is shown:** dots shaded by how often each seat falls that way across runs, or a small spread of arcs. A single crisp arc for a grade C projection is not allowed.
- **Paired with a constituency hex map**, so readers see proportionality (arc) and that every constituency keeps an MP (map). This answers the "list PR breaks the constituency link" objection directly.
- **Backward re-counts** are shown as two arcs from the same ballots: the result as cast, and the same votes counted under FPTP.

---

## 6. Open decisions

1. Minimum match set for B-int: is M1 + M2 + M4 right?
2. Rule for collapsing multi-member STV wards to single-member results in backward re-counts.
3. Australian federal data fails M3 and M5. Use it for re-counts only (first preferences), not for calibrating transfer rates?
