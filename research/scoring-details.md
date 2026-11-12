# How the ERS Evaluates Voting Systems — Scoring Details

Retrieved: 11 November 2026. All text below is summarised in my own words.

## Headline finding

**The ERS does not publish a methodology for its star ratings.** The Types of Voting System page names the three criteria and says the stars are only a rough guide. None of the eight system pages explains why a system received its score. No page gives a rubric, an index or a weighting. The ERS appears to have set the scores by editorial judgement.

What the ERS *does* provide is:

1. Short definitions of each criterion, on three explainer pages.
2. Qualitative comparisons between systems on those pages.
3. An older, formal set of evaluation criteria in its 2007 report.

---

## 1. The three scored criteria, as the ERS defines them

### Proportionality
Source: <https://electoral-reform.org.uk/voting-systems/what-are-voting-systems/proportional-representation/>

- **Definition:** A party's share of seats should match its share of votes. The ERS benchmark is that about one-third of the votes should give about one-third of the seats.
- **Grouping:** The ERS sorts systems into two groups rather than ranking them on a scale:
  - **Designed to be proportional:** List PR, STV, AMS.
  - **Majoritarian:** FPTP, AV, SV. These are sometimes close to proportional, but often not. A party with a third of the vote could take half the seats, or none.
- **Factor named:** Proportional systems elect several members per area, so the members elected reflect the range of local opinion.
- **Not covered:** No quantitative measure (such as the Gallagher index or Loosemore–Hanby), and no discussion of thresholds, district magnitude or allocation formula. The List PR page does mention that D'Hondt slightly favours larger parties and that Sainte-Laguë does not.
- **Other system-page notes:**
  - AMS becomes less proportional as the share of constituency seats rises.
  - AV+ falls short because 80–85% of its seats are constituency seats.
  - AV can be less proportional than FPTP, as in 2015.
  - TRS boosts large parties.

### Voter choice
Source: <https://electoral-reform.org.uk/voting-systems/what-are-voting-systems/voter-choice/>

- **Definition:** Whether voters can choose between *individual candidates* rather than only between parties.
- **Implied ordering, from most to least choice:**
  1. STV and open-list PR: voters can choose between candidates of the same party.
  2. Closed-list PR: the party pre-selects and orders the candidates.
  3. FPTP and AV: one candidate per party, so a voter who supports a party but dislikes its candidate has no way to say so.
- **Not covered:** The voter-choice page does not mention ranked ballots, tactical voting or wasted votes. The individual system pages do raise tactical voting, for FPTP, TRS and AV.

### Local representation (constituency link)
Source: <https://electoral-reform.org.uk/voting-systems/what-are-voting-systems/constituency-link/>

- **Definition:** Members represent a local area and are directly accountable to it for their continued careers.
- **What strengthens the link:**
  - A smaller area per representative.
  - Members who are individually accountable.
  - A higher share of voters who have a representative they actually voted for.
- **Comparisons:**
  - **STV:** strong. Areas are relatively small, and most voters have a member they backed.
  - **FPTP:** the area is small, but the member often lacks majority support, so many constituents did not choose them.
  - **List PR:** weak. Regions are large, members cannot be held individually accountable, and the members may all live in one town.

---

## 2. The ERS's formal evaluation criteria (2007 report)

Source: *Britain's Experience of Electoral Systems*, ERS, 2007, prepared by Lewis Baston with Ken Ritchie.
<https://electoral-reform.org.uk/?p=894> · PDF: <https://electoral-reform.org.uk/wp-content/uploads/2017/06/Britains-experience-of-electoral-systems.pdf>

This is the closest the ERS comes to a stated evaluation framework. The report adopts the **Jenkins Commission (1998) terms of reference** as its main criteria and adds two supplementary criteria of its own.

**Principal (Jenkins) criteria**

| # | Criterion | Meaning |
|---|---|---|
| 1 | Broad proportionality | Seat share broadly reflects vote share |
| 2 | Stable government | Government can act decisively with a genuine mandate |
| 3 | Extension of voter choice | Voters choose people, not only parties |
| 4 | MP–constituency link | Members stay tied to geographic areas |

**Supplementary ERS criteria**

| # | Criterion | Meaning |
|---|---|---|
| 5 | Diversity | The system helps representation of women, ethnic minorities and similar groups |
| 6 | Participation | The system encourages turnout and engagement |

Three of the four Jenkins criteria became the current star-rating axes. *Stable government*, *diversity* and *participation* were dropped from the website scores.

**The report's verdicts, by system:**
- **FPTP (Westminster):** highly unrepresentative. It fails the Jenkins criteria, and the report finds the case for change compelling.
- **FPTP / multi-member non-transferable vote (MNTV) (local government):** highly disproportionate. The report recommends STV.
- **AMS (Scotland, Wales, London):** broadly representative and stable. However, it creates two classes of member, encourages tactical voting, and has problems with members switching parties.
- **STV (Northern Ireland):** close match between votes and seats, and high turnout. Women are under-represented. STV is the report's preferred system overall.
- **Closed-list PR (European Parliament):** proportional, but offers little voter choice. The report calls for a review and prefers STV.
- **SV (mayors):** often fails to produce a majority winner, and suffers from invalid and "double" votes. The report proposes replacing it with AV.
- **AV:** extends voter choice but is not proportional, so the report considers it an inadequate reform.

---

## 3. Related ERS framing

- **The general trade-off:** The ERS says every electoral system is a compromise between proportionality, voter choice and how local the representatives are.
- **Organisational stance:** Under the ERS 2025–29 strategy, the ERS campaigns for proportional representation, specifically STV, for UK public authorities. That should be kept in mind when reading its scores, since STV scores highest (14 out of 15).
- **Accountability:** The ERS overview pages mention accountability (whether voters can remove a government that performs badly) as a purpose of voting systems. It is not scored.

---

## 4. Observations for building a new metric system

- The ERS scores are **ordinal, unweighted and unexplained**. No one could reproduce them from a published rubric.
- **The criteria overlap.** "Voter choice" partly duplicates local representation: STV scores 5 on both, partly for the same reason, that voters choose individuals.
- **Proportionality has standard measures in the academic literature** that the ERS does not use:
  - the Gallagher least-squares index
  - the Loosemore–Hanby index
  - the Rose index (mentioned in a 1998 *Voting matters* paper, which notes it may be unsuitable for STV)
- **Voter choice has no standard measure.** The same *Voting matters* paper proposed an information-theoretic measure: the number of possible election outcomes.
- **Candidate extra axes** from the ERS's own past criteria:
  - stable government
  - diversity
  - participation/turnout
  - accountability ("can voters remove a government?")
- **Further axes from the ERS system pages:**
  - susceptibility to tactical voting
  - wasted or exhausted votes
  - simplicity of ballot and count
  - party control over who is elected

---

## Sources
- [ERS — Types of Voting System](https://electoral-reform.org.uk/voting-systems/types-of-voting-system/)
- [ERS — What are voting systems?](https://electoral-reform.org.uk/voting-systems/what-are-voting-systems/)
- [ERS — Proportional representation](https://electoral-reform.org.uk/voting-systems/what-are-voting-systems/proportional-representation/)
- [ERS — Voter choice](https://electoral-reform.org.uk/voting-systems/what-are-voting-systems/voter-choice/)
- [ERS — Constituency link](https://electoral-reform.org.uk/voting-systems/what-are-voting-systems/constituency-link/)
- [ERS — Britain's Experience of Electoral Systems (2007)](https://electoral-reform.org.uk/?p=894)
- [ERS — What we stand for](https://electoral-reform.org.uk/who-we-are/what-we-stand-for/)
- [Voting matters, Issue 9 — Voter Choice and Proportionality](https://www.votingmatters.org.uk/ISSUE9/P3.HTM)
