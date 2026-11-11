use crate::{CountError, CountEvent, CountResult, Party, RankedBallot, Seats, TieBreak};
use std::collections::BTreeMap;

/// Supplementary Vote (SV) and contingent vote; also TRS under sincere rankings (S1).
///
/// A first-round majority of valid first preferences wins. Otherwise only the top two
/// continue, and each other ballot moves to whichever of them it ranks higher (it
/// exhausts if it ranks neither). Ballots should already be truncated to the
/// preferences the rule allows (two for SV). A tie for a top-two place is settled by
/// the declared tie-break, as is a final tie.
pub fn contingent(
    ballots: &[RankedBallot],
    candidates: &[Party],
    tie: TieBreak,
) -> Result<CountResult, CountError> {
    if candidates.is_empty() {
        return Err(CountError::NoCandidates);
    }
    let tally = |continuing: &[Party]| {
        let mut totals: BTreeMap<Party, u64> = continuing.iter().map(|p| (p.clone(), 0)).collect();
        let mut exhausted = 0;
        for b in ballots {
            match b.ranking.iter().find(|p| totals.contains_key(*p)) {
                Some(p) => *totals.get_mut(p).expect("continuing") += b.weight,
                None => exhausted += b.weight,
            }
        }
        (totals, exhausted)
    };

    let mut log = Vec::new();
    let (first, exhausted) = tally(candidates);
    log.push(CountEvent::Totals {
        round: 1,
        totals: first.clone(),
        exhausted,
    });
    let live: u64 = first.values().sum();
    if live == 0 {
        return Err(CountError::NoValidVotes);
    }

    // Order by first-preference total, highest first; equal totals stay grouped for the tie-break.
    let mut ranked: Vec<(Party, u64)> = first.iter().map(|(p, v)| (p.clone(), *v)).collect();
    ranked.sort_by(|a, b| b.1.cmp(&a.1).then_with(|| a.0.cmp(&b.0)));

    if candidates.len() == 1 || ranked[0].1 * 2 > live {
        let (winner, top) = ranked[0].clone();
        let second = ranked.get(1).map_or(0, |r| r.1);
        log.push(CountEvent::Elected {
            round: 1,
            party: winner.clone(),
        });
        return Ok(CountResult {
            seats: Seats::from([(winner, 1)]),
            margin: Some(top - second),
            log,
        });
    }

    let finalists = pick(&ranked, 2, tie, &mut log);
    for (p, _) in &ranked {
        if !finalists.contains(p) {
            log.push(CountEvent::Eliminated {
                round: 1,
                party: p.clone(),
            });
        }
    }

    let (second, exhausted) = tally(&finalists);
    log.push(CountEvent::Totals {
        round: 2,
        totals: second.clone(),
        exhausted,
    });
    let mut ranked2: Vec<(Party, u64)> = second.iter().map(|(p, v)| (p.clone(), *v)).collect();
    ranked2.sort_by(|a, b| b.1.cmp(&a.1).then_with(|| a.0.cmp(&b.0)));
    let margin = ranked2[0].1 - ranked2[1].1;
    let winner = if margin == 0 {
        let tied = vec![ranked2[0].0.clone(), ranked2[1].0.clone()];
        let (chosen, method) = tie.resolve(&tied, std::slice::from_ref(&first), true, 2);
        log.push(CountEvent::Tie {
            round: 2,
            tied,
            chosen: chosen.clone(),
            method,
        });
        chosen
    } else {
        ranked2[0].0.clone()
    };
    log.push(CountEvent::Elected {
        round: 2,
        party: winner.clone(),
    });
    Ok(CountResult {
        seats: Seats::from([(winner, 1)]),
        margin: Some(margin),
        log,
    })
}

/// Take the top `n` of a descending ranking, settling a tie across the cut-off.
fn pick(ranked: &[(Party, u64)], n: usize, tie: TieBreak, log: &mut Vec<CountEvent>) -> Vec<Party> {
    let cutoff = ranked[n - 1].1;
    let mut chosen: Vec<Party> = ranked
        .iter()
        .filter(|r| r.1 > cutoff)
        .map(|r| r.0.clone())
        .collect();
    let mut tied: Vec<Party> = ranked
        .iter()
        .filter(|r| r.1 == cutoff)
        .map(|r| r.0.clone())
        .collect();
    let mut salt = 0;
    while chosen.len() < n {
        if tied.len() + chosen.len() == n {
            chosen.append(&mut tied);
            break;
        }
        salt += 1;
        let (p, method) = tie.resolve(&tied, &[], true, salt);
        log.push(CountEvent::Tie {
            round: 1,
            tied: tied.clone(),
            chosen: p.clone(),
            method,
        });
        tied.retain(|t| *t != p);
        chosen.push(p);
    }
    chosen
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
    const LOT: TieBreak = TieBreak::Lot { seed: 5 };

    #[test]
    fn first_round_majority_wins() {
        let r = contingent(
            &[b(&["A"], 51), b(&["B"], 30), b(&["C"], 19)],
            &cands(&["A", "B", "C"]),
            LOT,
        )
        .unwrap();
        assert_eq!(r.seats, Seats::from([("A".into(), 1)]));
        assert_eq!(r.margin, Some(21));
    }

    #[test]
    fn only_top_two_receive_transfers() {
        // A 40, B 32, C 18 (→D), D 10 (→B). Top two A, B. D's ballots reach B; C's
        // second preferences are for D, who is out, so they exhaust. B wins 42–40.
        let ballots = [
            b(&["A"], 40),
            b(&["B"], 32),
            b(&["C", "D"], 18),
            b(&["D", "B"], 10),
        ];
        let r = contingent(&ballots, &cands(&["A", "B", "C", "D"]), LOT).unwrap();
        assert_eq!(r.seats, Seats::from([("B".into(), 1)]));
        assert!(r.log.iter().any(|e| matches!(
            e,
            CountEvent::Totals {
                round: 2,
                exhausted: 18,
                ..
            }
        )));
        assert_eq!(r.margin, Some(2));
    }

    #[test]
    fn third_place_transfers_decide_the_winner() {
        // A 35, B 33, C 32 (→B). B wins 65–35.
        let ballots = [b(&["A"], 35), b(&["B"], 33), b(&["C", "B"], 32)];
        let r = contingent(&ballots, &cands(&["A", "B", "C"]), LOT).unwrap();
        assert_eq!(r.seats, Seats::from([("B".into(), 1)]));
        assert_eq!(r.margin, Some(30));
    }

    #[test]
    fn tie_for_second_place_is_logged() {
        let ballots = [b(&["A"], 40), b(&["B"], 30), b(&["C"], 30)];
        let r = contingent(&ballots, &cands(&["A", "B", "C"]), LOT).unwrap();
        assert!(r
            .log
            .iter()
            .any(|e| matches!(e, CountEvent::Tie { round: 1, .. })));
    }

    #[test]
    fn no_valid_votes_is_an_error() {
        assert_eq!(
            contingent(&[b(&[], 5)], &cands(&["A", "B"]), LOT),
            Err(CountError::NoValidVotes)
        );
    }
}
