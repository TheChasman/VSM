use crate::{CountError, CountEvent, CountResult, Party, Seats, TieBreak};
use serde::Serialize;
use std::collections::{BTreeMap, BTreeSet};

/// A ranked ballot. `weight` is in integer units (scale survey weights before counting).
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct RankedBallot {
    pub ranking: Vec<Party>,
    pub weight: u64,
}

/// Alternative Vote (AV), also called instant-runoff voting (IRV).
///
/// Each round counts every ballot for its highest-ranked continuing candidate. A
/// candidate with more than half the continuing vote, or the last one standing, is
/// elected. Otherwise the lowest is eliminated, ties settled by earlier-round totals
/// (lower goes) and then the lot. `candidates` lists everyone standing, including
/// candidates with no first preferences. Preferences for unlisted parties are ignored.
pub fn irv(
    ballots: &[RankedBallot],
    candidates: &[Party],
    tie: TieBreak,
) -> Result<CountResult, CountError> {
    let mut continuing: BTreeSet<Party> = candidates.iter().cloned().collect();
    if continuing.is_empty() {
        return Err(CountError::NoCandidates);
    }
    let mut log = Vec::new();
    let mut history: Vec<BTreeMap<Party, u64>> = Vec::new();

    for round in 1.. {
        let mut totals: BTreeMap<Party, u64> = continuing.iter().map(|p| (p.clone(), 0)).collect();
        let mut exhausted = 0;
        for b in ballots {
            match b.ranking.iter().find(|p| continuing.contains(*p)) {
                Some(p) => *totals.get_mut(p).expect("continuing") += b.weight,
                None => exhausted += b.weight,
            }
        }
        log.push(CountEvent::Totals {
            round,
            totals: totals.clone(),
            exhausted,
        });
        let live: u64 = totals.values().sum();
        if live == 0 && continuing.len() > 1 {
            return Err(CountError::NoValidVotes);
        }

        let top = *totals.values().max().expect("non-empty");
        if continuing.len() == 1 || top * 2 > live {
            // A strict majority is unique; the last-one-standing case has one candidate.
            let winner = totals
                .iter()
                .find(|(_, &v)| v == top)
                .map(|(p, _)| p.clone())
                .expect("non-empty");
            let runner_up = totals
                .iter()
                .filter(|(p, _)| **p != winner)
                .map(|(_, &v)| v)
                .max()
                .unwrap_or(0);
            log.push(CountEvent::Elected {
                round,
                party: winner.clone(),
            });
            return Ok(CountResult {
                seats: Seats::from([(winner, 1)]),
                margin: Some(top - runner_up),
                log,
            });
        }

        let bottom = *totals.values().min().expect("non-empty");
        let lowest: Vec<Party> = totals
            .iter()
            .filter(|(_, &v)| v == bottom)
            .map(|(p, _)| p.clone())
            .collect();
        let out = if lowest.len() == 1 {
            lowest[0].clone()
        } else {
            let (chosen, method) = tie.resolve(&lowest, &history, false, u64::from(round));
            log.push(CountEvent::Tie {
                round,
                tied: lowest,
                chosen: chosen.clone(),
                method,
            });
            chosen
        };
        continuing.remove(&out);
        log.push(CountEvent::Eliminated { round, party: out });
        history.push(totals);
    }
    unreachable!("each round elects or removes a candidate")
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::TieMethod;

    fn b(ranking: &[&str], weight: u64) -> RankedBallot {
        RankedBallot {
            ranking: ranking.iter().map(|s| s.to_string()).collect(),
            weight,
        }
    }
    fn cands(c: &[&str]) -> Vec<Party> {
        c.iter().map(|s| s.to_string()).collect()
    }
    const LOT: TieBreak = TieBreak::Lot { seed: 3 };

    #[test]
    fn first_round_majority_wins() {
        let r = irv(&[b(&["A"], 60), b(&["B"], 40)], &cands(&["A", "B"]), LOT).unwrap();
        assert_eq!(r.seats, Seats::from([("A".into(), 1)]));
        assert_eq!(r.margin, Some(20));
    }

    #[test]
    fn transfers_overturn_the_plurality_leader() {
        // A leads on firsts, but C's voters prefer B.
        let ballots = [b(&["A"], 40), b(&["B"], 35), b(&["C", "B"], 25)];
        let r = irv(&ballots, &cands(&["A", "B", "C"]), LOT).unwrap();
        assert_eq!(r.seats, Seats::from([("B".into(), 1)]));
        assert_eq!(r.margin, Some(20));
        assert!(r.log.contains(&CountEvent::Eliminated {
            round: 1,
            party: "C".into()
        }));
    }

    #[test]
    fn exhausted_ballots_are_logged_and_leave_the_quota() {
        // C's voters rank no one else: 40 v 35 after exhaustion is a majority of 75.
        let ballots = [b(&["A"], 40), b(&["B"], 35), b(&["C"], 25)];
        let r = irv(&ballots, &cands(&["A", "B", "C"]), LOT).unwrap();
        assert_eq!(r.seats, Seats::from([("A".into(), 1)]));
        assert!(r.log.iter().any(|e| matches!(
            e,
            CountEvent::Totals {
                round: 2,
                exhausted: 25,
                ..
            }
        )));
    }

    #[test]
    fn candidate_with_no_first_preferences_goes_first() {
        let ballots = [b(&["A"], 40), b(&["B"], 35), b(&["C", "A"], 25)];
        let r = irv(&ballots, &cands(&["A", "B", "C", "D"]), LOT).unwrap();
        assert!(r.log.contains(&CountEvent::Eliminated {
            round: 1,
            party: "D".into()
        }));
        assert_eq!(r.seats, Seats::from([("A".into(), 1)]));
    }

    #[test]
    fn elimination_tie_uses_earlier_round() {
        // Round 1: A 30, B 20, C 22, D 28 → B out. B transfers 8 to C: C 30.
        // Round 2: A 30, C 30, D 40 → A and C tie for last; earlier round had C 22 < A 30, so C goes.
        let ballots = [
            b(&["A"], 30),
            b(&["B", "C"], 8),
            b(&["B", "D"], 12),
            b(&["C"], 22),
            b(&["D"], 28),
        ];
        let tb = TieBreak::EarlierStageThenLot { seed: 0 };
        let r = irv(&ballots, &cands(&["A", "B", "C", "D"]), tb).unwrap();
        assert!(r.log.iter().any(|e| matches!(e, CountEvent::Tie { round: 2, method: TieMethod::EarlierStage, chosen, .. } if chosen == "C")));
    }

    #[test]
    fn all_empty_ballots_is_an_error() {
        assert_eq!(
            irv(&[b(&[], 10)], &cands(&["A", "B"]), LOT),
            Err(CountError::NoValidVotes)
        );
    }
}
