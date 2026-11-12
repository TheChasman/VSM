# Voting System Metrics: Additional Research (closing the v0.1 open items)

Written: 11 November 2026. Follows `research/new-metrics.md` (spec v0.1), §9 Known limitations and §10 Next steps. This document does the research parts of that list. The build-and-compute parts (district algorithm, scoring runs) are scoped here but not done.

Status summary:

| v0.1 item | Outcome |
|---|---|
| §10.1 Populate the S1 criteria table with citations | **Done** (§1). Two design problems found in S1 itself (§1.4). |
| §10.2 District-generation algorithm, test on Wales | Not built. Inputs confirmed (§3.1). Wales now has a real precedent to test against. |
| §10.3 Score the executive profile first | Not scored. **The executive voting system changed twice since 2022**, which changes the grades and the reference data (§2.1). |
| §10.4 Commons 2024, S0 lower bound | Not run. Data confirmed except count times (§3.2). |
| Factual claims and anchors in the spec | Checked. Two corrections, three updates (§2). |

---

## 1. S1 criteria compliance table (spec §10 item 1)

### 1.1 Rules used for the table

- ✓ = the count rule satisfies the criterion. ✗ = a counter-example exists. **N/A** = satisfied only because the ballot cannot express the thing the criterion tests (for example, later-no-harm on a single-mark ballot). N/A is excluded from the denominator, following principle P7.
- ? = not settled by a citation found so far. Must be resolved by citation or proof before the spec is frozen (P10).
- List-system criteria are applied **at party level**, since the voter chooses a party, not a ranking of candidates.

### 1.2 Single-winner rules (executive profile, and the constituency tier of AV and AV+)

| Criterion | FPTP | AV | SV | TRS | Source |
|---|:-:|:-:|:-:|:-:|---|
| Monotonicity | ✓ | ✗ | ✗ | ✗ | Woodall (1997) |
| Participation (no-show) | ✓ | ✗ | ✗ | ✗ | Moulin (1988); McCune & Wilson (2025); Graham-Squire & McCune (2023) |
| Later-no-harm | N/A | ✓ | ✓ | ✓¹ | Woodall (1994, 1997) |
| Favourite-betrayal resistance | ✗ | ✗ | ✗ | ✗ | Small (2010) |
| Independence of clones | ✗ | ✓ | ✗ | ✗ | Tideman (1987) |
| Condorcet winner | ✗ | ✗ | ✗ | ✗ | Standard; Woodall (1997) Table 1 |
| **S1 score** | **40** (2/5) | **33** (2/6) | **17** (1/6) | **17** (1/6) | |

¹ TRS voters re-vote in round two, so "later preference" has no direct meaning. Under the S1 scenario (sincere rankings from BES data), TRS behaves as a contingent vote and satisfies later-no-harm.

### 1.3 Multi-winner rules (Commons, devolved and council profiles)

| Criterion | STV (WIGM, Droop) | List, D'Hondt (closed or open) | List, Sainte-Laguë | Bloc Vote | Limited Vote | AMS / AV+ / Parallel | Source |
|---|:-:|:-:|:-:|:-:|:-:|:-:|---|
| House (committee-size) monotonicity | ✗ | ✓ | ✓ | ✓ | ✓ | ? | Elkind et al. (2017); Balinski & Young (1982) |
| Candidate monotonicity | ✗ | ✓ (party) | ✓ (party) | ✓ | ✓ | ? | Woodall (1997); McCune & Graham-Squire (2024) |
| Droop proportionality for solid coalitions | ✓ | ✓ (party)² | ✗ | ✗ | ✗ | ✗ | Woodall (1994); Tideman & Richardson (2000); Balinski & Young (1982) |
| Later-no-harm | ✓ | N/A | N/A | ✗ | ✗ | N/A (list vote) | Woodall (1994) |
| Independence of clones | ✓³ | ✗ | ✗ | ✗ | ✗ | ✗ (decoy lists) | Tideman (1987, 1995); Balinski & Young; Bochsler (2012) |
| Participation | ✗ | ✓ | ✓ | ✓ | ✓ | ? | McCune & Graham-Squire (2024); Balinski & Young |
| **S1 score** | **50** (3/6) | **80** (4/5) | **60** (3/5) | **50** (3/6) | **50** (3/6) | unresolved | |

² **D'Hondt is Droop-proportional for parties.** Proof sketch: let q be the (S+1)th largest D'Hondt quotient. A party with c quotients at or above q has at least c·q votes, so V ≥ (S+1)·q, giving q ≤ V/(S+1). A party with more than k·V/(S+1) votes has a k-th quotient above q, so it wins at least k seats. Sainte-Laguë fails the weaker lower-quota condition (Balinski & Young), so it fails this one too.

³ Tideman (1987) proves independence of clones for AV and treats STV as clone-independent. McCune & Wilson (2024) show that in multi-winner elections STV is not spoiler-proof against *near*-clones, using Scottish ballot data. Scored ✓ for perfect clones, with that caveat recorded.

**Unresolved cells (AMS, AV+, Parallel).** The constituency tier inherits the FPTP or AV rows. The compensatory link adds known manipulation (decoy lists: Albania 2005, Lesotho 2007, Italy 2001). Whether UK AMS can show negative vote weight (as Germany's overhang rules did) has not been settled by any source found. These cells need a proof or a published example before freeze.

### 1.4 Problems with S1 found while building the table

1. **S1 rewards inexpressive count rules.** Binary criteria are easiest to pass for rules that ignore most of the ballot. Even with the N/A rule, FPTP (40) beats AV (33), and closed-list D'Hondt (80) beats STV (50). This is not an error in the table; it is what binary criteria measure. It supports the spec's own position that S2 (how often manipulation pays) is the main measure. **Open decision:** keep S1 as a scored half of axis 5, down-weight it, or move it to "reported, not scored".
2. **S1 double-counts F1′ for executives.** The single-winner list includes the Condorcet winner criterion, and axis 8 scores Condorcet efficiency (F1′). That breaks principle P3 (one concept, one axis). **Suggested fix:** drop the Condorcet criterion from S1. Single-winner scores would then be FPTP 50 (2/4), AV 40 (2/5), SV 20 (1/5), TRS 20 (1/5).
3. **Closed-list "candidate monotonicity" is close to vacuous.** Voters cannot rank candidates, so the criterion is tested at party level only. Recorded as "(party)" so readers know.

### 1.5 Evidence for S2 calibration (how often failures happen)

- Scottish council STV, 1,079 elections (30 single-winner, 1,049 multi-winner): 62 showed at least one monotonicity anomaly, about 5.7% of elections (McCune & Graham-Squire 2024).
- US IRV elections that reached a second round: anomaly rates of 2.2% (upward), 1.6% (downward) and 0.5% (no-show) (Graham-Squire & McCune 2023).
- These are shares of *elections*, not of *voters*. S2 is defined per voter, so these figures validate the direction of the S2 simulation, not its level. The S2 anchor (0 at 30%) is not challenged by them.

---

## 2. Fact checks on the spec

### 2.1 Executive profile: the system changed twice (affects C17–C20)

| Period | Mayors (England) and PCCs (England and Wales) | Source |
|---|---|---|
| 2000–2021 (mayors), 2012–2021 (PCCs) | Supplementary Vote | Elections Act 2022 impact assessment |
| 2024–2026 | FPTP, under the Elections Act 2022 | Same |
| From 2027 | SV restored by the English Devolution and Community Empowerment Act 2026 (Royal Assent 29 April 2026). PCC functions are moving to mayors. | Act; ministerial commencement statement 21 May 2026 |

Consequences for the spec:
- **C17 (FPTP) and C18 (SV) both get grade A** for the executive profile, from 2024–2025 and 2000–2021 results respectively. This is a rare natural experiment: the same offices, same areas, under both rules.
- **C19 (AV)** has UK use only in Scottish single-seat council by-elections (counted as one-winner STV), so grade B.
- **C20 (TRS)** has no UK use; grade B at best (used for executives abroad).
- **E1 for SV is directly observable.** SV second-count statements give votes for eliminated candidates and ballots "unmarked as to second preference", which is exactly the exhaustion E1 measures. No central dataset was found; figures sit on local authority sites (for example Coventry, Wiltshire, Welwyn Hatfield for 2021).

### 2.2 Other checks

| Spec claim | Finding | Action |
|---|---|---|
| P1 anchor: highest post-war Gallagher about 24, in 2024 | Confirmed: published values 23.6 to 24.0. Previous high 20.6 in 1983. | None |
| G2 anchor: 13,000 km² statutory maximum | Confirmed (rule 4, Schedule 2 to the 1986 Act). Largest actual seat: Caithness, Sutherland and Easter Ross, 11,632 km². | Note that every current single-member seat scores 100 on G2 after clamping |
| G1 anchor: 2023 quota about 73,400 | Confirmed: 73,393; permitted range 69,724 to 77,062 | None |
| W1: five protected seats | Confirmed: two Isle of Wight seats, Orkney and Shetland, Na h-Eileanan an Iar, Ynys Môn | None |
| C09 "Senedd 2026 model" | Confirmed, and **the election has now happened** (7 May 2026): 16 six-member constituencies made by pairing the 32 Westminster seats, closed lists, D'Hondt, parties may list up to 8 candidates | **C09 is grade A for the devolved profile**, not modelled |
| C06 and C12 Holyrood ratios | Confirmed: 73 constituency and 56 list seats (57:43) | None |
| C13 London Assembly 14:11 | Confirmed | None |
| C08 Jenkins AV+ about 83% constituency | Confirmed: the Commission recommended 15–20% top-up members, in about 80 top-up areas, mostly 1 or 2 seats each | Add: top-up area magnitude is very small, which caps AV+ proportionality |
| C16 "3–4 member wards (Scottish council model)" | **Out of date.** Scottish Government's 2022 factsheet gives 355 wards of between 1 and 5 members (island wards smaller). | Change C16 to "STV, 2022 Scottish ward pattern (1–5 members)", or keep 3–4 as a stylised model and say so |
| Reference cases for wrong winner: 1951, February 1974 | Correct but incomplete: 1929 is also a wrong-winner election | Add 1929 |

---

## 3. Data scoping for the remaining build steps

### 3.1 Available, open

| Data | Source | Use | Note |
|---|---|---|---|
| 2024 GE results by candidate (CSV) | Commons Library election results site | P, E, W, C, F (Commons) | Also has notional 2019 results on 2024 boundaries |
| Full STV preference ballots, Scottish councils 2007 (two councils), 2012, 2017, 2022 | Returning officers; collated by Mollison (Heriot-Watt) and Teale (LEAP) | E1 exhaustion, S2 validation, I3 | Counted by Weighted Inclusive Gregory; good test bed for C16 |
| BES Internet Panel like/dislike 0–10 for parties | BES (waves to 30, May 2025) | S1 scenario ballots, S2, F1′ | Reform UK coverage starts in later waves; **ties are common on a 0–10 scale**, so the method must pre-register a tie rule |
| Party positions | CHES 2024 (includes the UK) and the 2024 BES Expert Survey (all GB parties) | A1 coalition model | The BES expert survey covers more UK parties and is the better UK source |
| Senedd 2026 results | Senedd Research briefing (September 2026) | Devolved profile, grade A for C09 | Also a ready-made precedent for pairing Westminster seats into multi-member districts (§10.2 test) |
| Boundaries | OS Boundary-Line (open data) | G2, G3, district building | Not verified in this pass; widely used open product |

### 3.2 Gaps

1. **Count times (I2).** The Commons Library results site shows declaration times for earlier elections but says they are not yet available for 2024. Alternatives: PA declaration logs or returning officer notices. Needs a decision on source before pre-registration.
2. **SV second-preference data (E1 for C18).** Published locally, not centrally. Needs collation, or a check of Electoral Commission results files (not checked in this pass).
3. **Northern Ireland STV ballot data.** Not checked in this pass. Stage-by-stage transfer sheets exist; whether full ballot-level data is published is unconfirmed.

---

## 4. Recommended changes to the spec (for v0.2)

1. §2.1: update C09, C16 and the executive configurations as in §2.
2. §4 axis 5: add the S1 table by reference to this document; adopt the N/A rule; resolve the Condorcet overlap with F1′; record the open decision on S1 weight.
3. §4 axis 8: add 1929 to the wrong-winner reference cases.
4. §7: note the actual largest seat (11,632 km²) against the G2 anchor.
5. §10: mark item 1 done; add the three data gaps in §3.2 as blockers; add "resolve AMS / AV+ / Parallel S1 cells" before freeze.

---

## Sources

**Criteria and social choice**
- Woodall, D. R. (1994) Properties of preferential election rules. *Voting matters* 3. <https://www.votingmatters.org.uk/ISSUE3/P5.HTM>
- Woodall, D. R. (1997) Monotonicity of single-seat preferential election rules. *Discrete Applied Mathematics* 77, 81–98. <https://rangevoting.org/Woodall97.pdf>
- Tideman, T. N. (1987) Independence of clones as a criterion for voting rules. *Social Choice and Welfare* 4, 185–206. <https://condorcet.vote/assets/DOCS/IndependenceofClones.pdf>
- Small, A. (2010) Geometric construction of voting methods that protect voters' first choices. arXiv:1008.4331. <https://arxiv.org/abs/1008.4331>
- Balinski, M. L. and Young, H. P. (1976) The Jefferson method of apportionment. IIASA. <https://pure.iiasa.ac.at/id/file/182847>
- Balinski and Young summary of apportionment properties, AMS Feature Column. <https://www.ams.org/featurecolumn/archive/apportionII3.html>
- Aziz, Lederer, Peters, Peters and Ritossa, Committee monotonicity and proportional representation for ranked preferences (cites Elkind et al. 2017 for STV failing committee monotonicity). <https://arxiv.org/html/2406.19689v1>
- McCune, D. and Graham-Squire, A. (2024) Monotonicity anomalies in Scottish local government elections. *Social Choice and Welfare* 63, 69–101. <https://link.springer.com/article/10.1007/s00355-024-01522-5>
- McCune, D. and Wilson, J. (2024) Multiwinner elections and the spoiler effect (abstract, listed under related papers). <https://arxiv.deeppaper.ai/papers/2305.17741v3>
- Moulin (1988), Graham-Squire & McCune (2023), McCune & Wilson (2025), Ornstein & Norman (2014): reference list of McCune & Graham-Squire on IDEAS. <https://ideas.repec.org/p/arx/papers/2305.17741.html>
- Tideman & Richardson (2000) and Elkind et al. (2017) are cited at second hand via Aziz et al. above; read the originals before freeze.
- Bochsler, D. (2012) A quasi-proportional electoral system 'only for honest men'? *International Political Science Review* 33(4). <https://research.ceu.edu/en/publications/a-quasi-proportional-electoral-system-only-for-honest-men-the-hid/>

**UK facts**
- Boundary Commission for England, Guide to the 2023 Review. <https://boundarycommissionforengland.independent.gov.uk/2023-review/guide-to-the-2023-review-of-parliamentary-constituencies/page/3/>
- Parliamentary Constituencies Act 1986, Schedule 2 (as amended). <https://legislation.gov.uk/ukpga/1986/56/schedule/2/2020-12-14?view=plain>
- Caithness, Sutherland and Easter Ross constituency area. <https://en.wikipedia.org/wiki/Caithness,_Sutherland_and_Easter_Ross_(UK_Parliament_constituency)> (single-figure source; confirm against OS Boundary-Line when built)
- Senedd Research, Closed lists and D'Hondt (April 2026). <https://research.senedd.wales/research-articles/closed-lists-d-hondt-how-are-seats-allocated/>
- Senedd Research, Senedd Election 2026 briefing (September 2026). <https://research.senedd.wales/media/v4njg01m/senedd-election-2026.pdf>
- Elections Act 2022, FPTP impact assessment addendum. <https://bills.parliament.uk/publications/47852/documents/2292>
- English Devolution and Community Empowerment Act 2026: commencement statement. <https://parallelparliament.co.uk/debate/2026-05-21/commons/written-statements/english-devolution-and-community-empowerment-act-2026-commencement>
- Local Government Lawyer, The English Devolution and Community Empowerment Act 2026. <https://www.localgovernmentlawyer.co.uk/governance/314-governance-a-risk-articles/100441-the-english-devolution-and-community-empowerment-act-2026>
- Jenkins Commission recommendations (summary). <https://www.mail-archive.com/election-methods-list@eskimo.com/msg04303.html>
- Dunleavy and Margetts, British AMS systems (seat ratios). <https://eprints.lse.ac.uk/709/1/BritishAMSSystems04.pdf>
- Scottish Government eCounting, STV factsheet 2022. <https://www.edinburgh.gov.uk/downloads/file/30610/ecounting-2022---stv-factsheet>
- Gallagher index 2024: Europe Elects; Herald Scotland (previous high 1983). <https://europeelects.eu/2024/07/13/uk-labours-wide-majority-pushing-first-past-the-post-to-breaking-point/>

**Data**
- Commons Library election results. <https://electionresults.parliament.uk/>
- Scottish council STV ballot data (Mollison). <https://www.macs.hw.ac.uk/~denis/stv_elections.html>
- BES Internet Panel. <https://britishelectionstudy.com/data-object/wave-28-of-the-2014-2024-british-election-study-internet-panel>
- BES 2024 Expert Survey. <https://britishelectionstudy.com/bes-resources/release-of-the-2024-bes-expert-survey>
- CHES 2024. <https://www.maxwell.syr.edu/research/article/the-2024-chapel-hill-expert-survey-on-political-party-positioning-in-europe>
