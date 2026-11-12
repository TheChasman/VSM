# Critique of the ERS Metrics and Proposed Changes

Written: 11 November 2026. Based on `research/voting-systems.md` and `research/scoring-details.md`.

---

## 1. Diagnosis: what is wrong with the ERS scores

### 1.1 They cannot be reproduced
The ERS publishes no rubric, weighting or data. The scores are editorial judgement. Nobody can check a score, dispute it on evidence, or apply it to a new system.

### 1.2 They score system *families*, not *configurations*
The same name can describe very different systems:
- **STV:** 3-member districts are far less proportional than 7-member districts. The ERS gives one score.
- **List PR:** closed and open lists differ sharply on voter choice. Both get C3.
- **AMS:** Holyrood (73 constituency : 56 list), London (14 : 11) and Germany (roughly 50 : 50) give different proportionality. All get P4.
- **Thresholds and allocation formula** (D'Hondt vs Sainte-Laguë) are not scored at all, although the ERS mentions the difference.

### 1.3 Scores contradict the ERS's own definitions
- **Voter choice** is defined as choosing between *individual candidates*. AV, SV and TRS offer one candidate per party, exactly like FPTP, yet score 3 against FPTP's 2. The extra point is evidently for ranking or a second round, which is an unstated second criterion.
- **SV equals AV on choice (3)**, although SV allows only two preferences and exhausts ballots whose second choice misses the run-off.
- **Local representation:** AV gets L4, but SV and TRS get L3. All three are single-member systems aiming at majority winners.
- **AV+ gets L4 but AMS gets L3**, though they have almost the same structure (constituency seats plus county or regional top-ups).
- **STV gets L5**, although the ERS names smaller area per representative as a strengthening factor. Multi-member STV seats in rural Scotland or Wales would be very large geographically.

### 1.4 Criteria overlap
A candidate-centred ballot is rewarded twice: under voter choice and again under local representation (as "individual accountability" and "a representative you voted for"). STV benefits most from the double count.

### 1.5 Missing criteria
The ERS's own 2007 framework included stable government, diversity and participation. Its overview pages mention accountability. None is scored. Other gaps: wasted votes, tactical-voting pressure, wrong-winner risk, equality of vote weight, simplicity, and party control over who is elected.

### 1.6 The scale is too coarse
Integer stars from 1 to 5 hide real differences and show no uncertainty. Totals run only from 7 to 14.

### 1.7 Offices are mixed together
Proportionality has no meaning for a single post. The table puts mayoral systems (SV, TRS) beside legislative systems on the same proportionality axis.

### 1.8 A major UK system is unscored
**Bloc Vote** (multi-member FPTP) is used in many English and Welsh multi-member council wards. The ERS lists it only as an unscored submenu item.

### 1.9 Conflict of interest
The ERS campaigns for STV, and STV scores highest (14/15). The scorer and the advocate are the same body. That does not make the scores wrong, but it makes independent, published methodology essential.

### 1.10 "Fairness" is defined narrowly
The ERS treats fairness as proportionality to parties. There are at least three competing fairness ideas:
- fairness to **parties** (seats match votes)
- fairness to **voters** (each vote has equal weight and equal chance of counting)
- fairness to **places** (each area has an identifiable representative)

A neutral system should show all three rather than choose one.

---

## 2. Proposed axis set (UK-grounded)

Ten axes in five groups. Each has a defined measure, so scores can be reproduced.

### A. Representation
| # | Axis | Measure |
|---|---|---|
| 1 | **Proportionality** | Gallagher least-squares index, from UK vote data re-run under each configuration. Reported UK-wide and per nation. |
| 2 | **Vote effectiveness** | Share of votes that helped elect someone (the inverse of wasted votes). Share of voters with a representative they voted for or ranked. |
| 3 | **Equality of vote weight** | Variance of electorate per representative (against the Boundary Commission ±5% quota rule), plus partisan symmetry (seats–votes bias between the main parties). |

### B. Voter power
| # | Axis | Measure |
|---|---|---|
| 4 | **Ballot expressiveness** | Ordinal rubric with two sub-scores. *Inter-party:* single X → two preferences (SV) → two ballots (AMS) → full ranking. *Intra-party:* none → open list → STV. |
| 5 | **Sincere-vote safety** | Tactical-voting incentive, spoiler effect, non-monotonicity. Scored from social-choice criteria compliance plus observed tactical-voting rates (British Election Study, BES). |
| 6 | **Voter vs party control** | Share of seats where party list order, rather than voters, decides who is elected. Share of safe seats. |

### C. Locality
| # | Axis | Measure |
|---|---|---|
| 7 | **Geographic link** | Electorate and area per representative, maximum district area (a "Highlands test"), and coterminosity with local-authority or recognisable community boundaries. |

"Having a representative you voted for" moves to axis 2, which removes the double count.

### D. Governance (descriptive, not good or bad in itself)
| # | Axis | Measure |
|---|---|---|
| 8 | **Government formation** | Effective number of parliamentary parties (ENPP), probability of a single-party majority, and wrong-winner risk (UK 1951 and February 1974 are the reference cases). |
| 9 | **Accountability** | Clarity of responsibility: can voters remove a government by changing their votes? |

### E. Practicality
| # | Axis | Measure |
|---|---|---|
| 10 | **Simplicity and integrity** | Rejected-ballot rate, count time, cost and auditability. UK reference points include the 2007 Scottish Parliament combined-ballot problems and Northern Ireland's STV counts. |

### Reported but not scored
- **Diversity** and **turnout**. The evidence linking them to the voting system is heavily confounded by party candidate selection, culture and other factors. Report observed figures; do not award points.

---

## 3. Scoring rules

1. **Score configurations, not families.** Each system carries parameters: district magnitude, list type, threshold, constituency-to-list ratio and allocation formula. Specify default UK configurations, for example:
   - STV for the Commons with 3–5 member districts
   - AMS on the Holyrood ratio
   - Closed-list PR on the Senedd model (six-member constituencies, D'Hondt)
2. **Use a 0–100 scale with an uncertainty band** in place of stars.
3. **Grade the evidence** for each score: observed in UK use, observed abroad, or modelled only. AV+ has never been used, so its scores are modelled.
4. **No composite total by default.** Offer user-chosen weights, and publish a sensitivity analysis showing how often each system ranks first across the range of weightings.
5. **Office-type profiles.** Separate profiles for the Commons, devolved legislatures, councils and single executives (mayors, Police and Crime Commissioners, PCCs). Axes that do not apply are marked N/A, not scored zero.
6. **Publish the rubric, data and code** so any score can be reproduced.
7. **Correct for behavioural bias in simulation.** Re-running FPTP votes through a PR count understates change, because voters cast those ballots tactically under FPTP. Use BES preference and ranking data where possible, and label static re-runs as lower-bound estimates.

---

## 4. Summary: alter, add, eliminate

| Action | Item |
|---|---|
| **Alter** | Proportionality → Gallagher index from UK data |
| **Alter** | Voter choice → split into expressiveness (4) and sincere-vote safety (5) |
| **Alter** | Local representation → purely geographic (7); "rep you voted for" moves to (2) |
| **Alter** | Stars → 0–100 with uncertainty and evidence grade |
| **Alter** | Family-level scores → configuration-level scores |
| **Add** | Vote effectiveness, equality of vote weight, voter vs party control, government formation, accountability, simplicity |
| **Add** | Bloc Vote and Limited Vote to the scored list |
| **Add** | Office-type profiles and user weighting with sensitivity analysis |
| **Eliminate** | The unweighted sum and editorial stars |
| **Eliminate** | Double-counting of candidate-centred ballots |
| **Eliminate** | Diversity and turnout as *scored* axes (keep as reported observations) |
