use crate::{CountError, CountEvent, CountResult, Party, RankedBallot, Seats, TieBreak};
use serde::Serialize;
use std::collections::{BTreeMap, BTreeSet};

/// Fixed-point parameters for STV (ADR-0006).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct StvParams {
    /// Decimal places kept in vote values, truncated. Scottish rules: 5.
    pub decimals: u32,
}

impl StvParams {
    /// Scottish Local Government Elections Order 2007: five decimal places.
    pub const SCOTTISH: Self = Self { decimals: 5 };
}

/// A bundle of identical ballot papers at one value.
struct Paper {
    ranking: usize,
    count: u64,
    /// Value of each paper, in units of 10^-decimals.
    value: u64,
    holder: Option<Party>,
}

/// Single Transferable Vote (STV), Weighted Inclusive Gregory Method (WIGM), Droop quota.
///
/// Follows the Scottish council counting rules. `candidates` here are **candidate**
/// identifiers, not parties: map them to parties outside the count. `RankedBallot::weight`
/// is a whole number of identical papers. All vote totals in the log are fixed-point
/// units of 10^-`decimals`; the quota appears in the `Quota` event in the same units.
pub fn stv_wigm_droop(
    ballots: &[RankedBallot],
    candidates: &[Party],
    seats: u32,
    params: StvParams,
    tie: TieBreak,
) -> Result<CountResult, CountError> {
    if candidates.is_empty() {
        return Err(CountError::NoCandidates);
    }
    if seats == 0 {
        return Err(CountError::NoSeats);
    }
    let scale = 10u64.pow(params.decimals);
    let standing: BTreeSet<&Party> = candidates.iter().collect();
    let mut log = Vec::new();

    // Stage 1: each paper to its first listed candidate.
    let mut papers: Vec<Paper> = Vec::new();
    let mut valid = 0u64;
    for (i, b) in ballots.iter().enumerate() {
        if let Some(first) = b.ranking.iter().find(|p| standing.contains(p)) {
            valid += b.weight;
            papers.push(Paper {
                ranking: i,
                count: b.weight,
                value: scale,
                holder: Some(first.clone()),
            });
        }
    }
    if valid == 0 {
        return Err(CountError::NoValidVotes);
    }
    let quota = (valid / (u64::from(seats) + 1) + 1) * scale;
    log.push(CountEvent::Quota {
        quota,
        decimals: params.decimals,
    });

    let mut continuing: BTreeSet<Party> = candidates.iter().cloned().collect();
    let mut elected: Vec<Party> = Vec::new();
    // Elected candidates whose surplus is still to transfer, with their total when elected.
    let mut pending: BTreeMap<Party, u64> = BTreeMap::new();
    // Frozen totals of elected candidates whose surplus has gone (they keep the quota).
    let mut frozen: BTreeMap<Party, u64> = BTreeMap::new();
    let mut history: Vec<BTreeMap<Party, u64>> = Vec::new();
    let total_valid = valid * scale;

    for stage in 1u32.. {
        let mut totals: BTreeMap<Party, u64> = candidates.iter().map(|c| (c.clone(), 0)).collect();
        for p in &papers {
            if let Some(h) = &p.holder {
                *totals.get_mut(h).expect("standing") += p.count * p.value;
            }
        }
        for (c, v) in &frozen {
            totals.insert(c.clone(), *v);
        }
        let held: u64 = totals.values().sum();
        log.push(CountEvent::Totals {
            round: stage,
            totals: totals.clone(),
            exhausted: total_valid - held,
        });

        // Elect everyone at or above the quota, highest first.
        let mut reached: Vec<Party> = continuing
            .iter()
            .filter(|c| totals[*c] >= quota)
            .cloned()
            .collect();
        while !reached.is_empty() && (elected.len() as u32) < seats {
            let top = reached.iter().map(|c| totals[c]).max().expect("non-empty");
            let tied: Vec<Party> = reached
                .iter()
                .filter(|c| totals[*c] == top)
                .cloned()
                .collect();
            let next = if tied.len() == 1 {
                tied[0].clone()
            } else {
                let (chosen, method) = tie.resolve(
                    &tied,
                    &history,
                    true,
                    u64::from(stage) << 16 | reached.len() as u64,
                );
                log.push(CountEvent::Tie {
                    round: stage,
                    tied,
                    chosen: chosen.clone(),
                    method,
                });
                chosen
            };
            reached.retain(|c| *c != next);
            continuing.remove(&next);
            elected.push(next.clone());
            pending.insert(next.clone(), totals[&next]);
            log.push(CountEvent::Elected {
                round: stage,
                party: next,
            });
        }

        let vacancies = seats - elected.len() as u32;
        if vacancies == 0 {
            break;
        }
        if continuing.len() as u32 <= vacancies {
            // Remaining candidates fill the remaining seats, highest first for the log.
            let mut rest: Vec<Party> = continuing.iter().cloned().collect();
            rest.sort_by(|a, b| totals[b].cmp(&totals[a]).then_with(|| a.cmp(b)));
            for c in rest {
                elected.push(c.clone());
                log.push(CountEvent::Elected {
                    round: stage,
                    party: c,
                });
            }
            break;
        }

        // Largest outstanding surplus first.
        let surpluses: Vec<(Party, u64)> = pending
            .iter()
            .map(|(c, t)| (c.clone(), t - quota))
            .filter(|(_, s)| *s > 0)
            .collect();
        if let Some(biggest) = surpluses.iter().map(|(_, s)| *s).max() {
            let tied: Vec<Party> = surpluses
                .iter()
                .filter(|(_, s)| *s == biggest)
                .map(|(c, _)| c.clone())
                .collect();
            let from = if tied.len() == 1 {
                tied[0].clone()
            } else {
                let (chosen, method) =
                    tie.resolve(&tied, &history, true, u64::from(stage) << 16 | 0xFFFF);
                log.push(CountEvent::Tie {
                    round: stage,
                    tied,
                    chosen: chosen.clone(),
                    method,
                });
                chosen
            };
            let total = pending.remove(&from).expect("pending");
            log.push(CountEvent::Surplus {
                round: stage,
                party: from.clone(),
                surplus: biggest,
            });
            for p in papers
                .iter_mut()
                .filter(|p| p.holder.as_ref() == Some(&from))
            {
                // Truncated per paper (rule 48): surplus × value ÷ total.
                p.value = (u128::from(biggest) * u128::from(p.value) / u128::from(total)) as u64;
                p.holder = next_preference(&ballots[p.ranking], &continuing);
            }
            frozen.insert(from, quota);
        } else {
            // Any zero surpluses are settled; freeze them at the quota.
            for (c, t) in std::mem::take(&mut pending) {
                frozen.insert(c, t);
            }
            let low = continuing
                .iter()
                .map(|c| totals[c])
                .min()
                .expect("continuing");
            let tied: Vec<Party> = continuing
                .iter()
                .filter(|c| totals[*c] == low)
                .cloned()
                .collect();
            let out = if tied.len() == 1 {
                tied[0].clone()
            } else {
                let (chosen, method) = tie.resolve(&tied, &history, false, u64::from(stage));
                log.push(CountEvent::Tie {
                    round: stage,
                    tied,
                    chosen: chosen.clone(),
                    method,
                });
                chosen
            };
            continuing.remove(&out);
            log.push(CountEvent::Eliminated {
                round: stage,
                party: out.clone(),
            });
            for p in papers
                .iter_mut()
                .filter(|p| p.holder.as_ref() == Some(&out))
            {
                p.holder = next_preference(&ballots[p.ranking], &continuing);
            }
        }
        history.push(totals);
    }

    let seats_won: Seats = elected.into_iter().map(|c| (c, 1)).collect();
    Ok(CountResult {
        seats: seats_won,
        margin: None,
        log,
    })
}

/// The next preference on the ballot that is still continuing, if any.
fn next_preference(ballot: &RankedBallot, continuing: &BTreeSet<Party>) -> Option<Party> {
    ballot
        .ranking
        .iter()
        .find(|c| continuing.contains(*c))
        .cloned()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn b(ranking: &[&str], weight: u64) -> RankedBallot {
        RankedBallot {
            ranking: ranking.iter().map(|s| s.to_string()).collect(),
            weight,
        }
    }
    fn cands(c: &[&str]) -> Vec<Party> {
        c.iter().map(|s| s.to_string()).collect()
    }
    fn won(r: &CountResult) -> Vec<&str> {
        r.seats.keys().map(String::as_str).collect()
    }
    fn stage_total(r: &CountResult, stage: u32, who: &str) -> u64 {
        r.log
            .iter()
            .find_map(|e| match e {
                CountEvent::Totals { round, totals, .. } if *round == stage => Some(totals[who]),
                _ => None,
            })
            .expect("stage logged")
    }
    const LOT: TieBreak = TieBreak::EarlierStageThenLot { seed: 11 };
    const S: StvParams = StvParams::SCOTTISH;

    #[test]
    fn surplus_then_exclusion() {
        // 100 valid, 2 seats: quota 34. A 50 elected, surplus 16 at 0.32000 → B.
        // Stage 2: B 31, C 20, D 15. Exclude D → C 35, elected.
        let ballots = [
            b(&["A", "B"], 50),
            b(&["C"], 20),
            b(&["D", "C"], 15),
            b(&["B"], 15),
        ];
        let r = stv_wigm_droop(&ballots, &cands(&["A", "B", "C", "D"]), 2, S, LOT).unwrap();
        assert!(r.log.contains(&CountEvent::Quota {
            quota: 34_00000,
            decimals: 5
        }));
        assert_eq!(stage_total(&r, 2, "B"), 31_00000);
        assert_eq!(stage_total(&r, 2, "A"), 34_00000);
        assert_eq!(won(&r), ["A", "C"]);
        assert!(r.log.contains(&CountEvent::Eliminated {
            round: 2,
            party: "D".into()
        }));
    }

    #[test]
    fn transfer_values_truncate_per_paper() {
        // 7 valid, 3 seats: quota 2. A 3 (surplus 1) → B at 1/3 = 0.33333 each, so 0.99999.
        let ballots = [b(&["A", "B"], 3), b(&["C"], 2), b(&["D"], 1), b(&["B"], 1)];
        let r = stv_wigm_droop(&ballots, &cands(&["A", "B", "C", "D"]), 3, S, LOT).unwrap();
        assert_eq!(stage_total(&r, 2, "B"), 1_99999);
        assert_eq!(won(&r), ["A", "B", "C"]);
        // One unit lost to truncation shows as non-transferable.
        assert!(r.log.iter().any(|e| matches!(
            e,
            CountEvent::Totals {
                round: 2,
                exhausted: 1,
                ..
            }
        )));
    }

    #[test]
    fn inclusive_gregory_uses_the_value_each_paper_arrived_with() {
        // 3 seats, 400 valid: quota 101. A 150 → surplus 49 at 49/150 to B.
        // B then holds 80 whole papers + 150 papers at 0.32666 = 80 + 48.999 = 128.999 → elected.
        // B's surplus 27.999 transfers from all 230 papers, each at its own value.
        let ballots = [
            b(&["A", "B", "C"], 150),
            b(&["B", "D"], 80),
            b(&["C"], 90),
            b(&["D"], 80),
        ];
        let r = stv_wigm_droop(&ballots, &cands(&["A", "B", "C", "D"]), 3, S, LOT).unwrap();
        assert_eq!(stage_total(&r, 2, "B"), 80_00000 + 150 * 32666);
        let b_total: u64 = 80_00000 + 150 * 32666;
        let surplus = b_total - 101_00000;
        let to_c = 150 * (u128::from(surplus) * 32666 / u128::from(b_total)) as u64;
        let to_d = 80 * (u128::from(surplus) * 100000 / u128::from(b_total)) as u64;
        assert_eq!(stage_total(&r, 3, "C"), 90_00000 + to_c);
        assert_eq!(stage_total(&r, 3, "D"), 80_00000 + to_d);
    }

    #[test]
    fn last_candidates_fill_remaining_seats() {
        let r = stv_wigm_droop(
            &[b(&["A"], 5), b(&["B"], 3)],
            &cands(&["A", "B"]),
            2,
            S,
            LOT,
        )
        .unwrap();
        assert_eq!(won(&r), ["A", "B"]);
    }

    #[test]
    fn surplus_goes_before_exclusion() {
        // 2 seats, 60 valid, quota 21.
        // Stage 1: A 30 (elected), B 10, C 12, D 8. A's surplus 9 → all to D (0.30000 × 30 = 9).
        // Stage 2: B 10, C 12, D 17. No surplus. Exclude B (lowest 10).
        let ballots = [
            b(&["A", "D"], 30),
            b(&["B"], 10),
            b(&["C"], 12),
            b(&["D"], 8),
        ];
        let r = stv_wigm_droop(&ballots, &cands(&["A", "B", "C", "D"]), 2, S, LOT).unwrap();
        assert!(r.log.contains(&CountEvent::Eliminated {
            round: 2,
            party: "B".into()
        }));
        // Stage 3: C 12, D 17; continuing 2 > 1 vacancy, exclude C, D elected.
        assert_eq!(won(&r), ["A", "D"]);
    }

    #[test]
    fn tied_exclusion_uses_earlier_stage() {
        // 2 seats, 87 valid, quota 30. Stage 1: A 40, B 22, C 13, D 12.
        // A's surplus 10 at 0.25000: 4 A>D papers give D 1, the 36 A-only papers exhaust.
        let ballots = [
            b(&["A", "D"], 4),
            b(&["A"], 36),
            b(&["B"], 22),
            b(&["C"], 13),
            b(&["D"], 12),
        ];
        let r = stv_wigm_droop(&ballots, &cands(&["A", "B", "C", "D"]), 2, S, LOT).unwrap();
        assert_eq!(stage_total(&r, 2, "C"), 13_00000);
        assert_eq!(stage_total(&r, 2, "D"), 13_00000);
        // Stage 1 had D 12 < C 13, so D is excluded.
        assert!(r.log.iter().any(|e| matches!(e, CountEvent::Tie { method: crate::TieMethod::EarlierStage, chosen, .. } if chosen == "D")));
    }

    #[test]
    fn errors() {
        assert_eq!(
            stv_wigm_droop(&[], &[], 1, S, LOT),
            Err(CountError::NoCandidates)
        );
        assert_eq!(
            stv_wigm_droop(&[], &cands(&["A"]), 0, S, LOT),
            Err(CountError::NoSeats)
        );
        assert_eq!(
            stv_wigm_droop(&[b(&["Z"], 3)], &cands(&["A"]), 1, S, LOT),
            Err(CountError::NoValidVotes)
        );
    }
}
