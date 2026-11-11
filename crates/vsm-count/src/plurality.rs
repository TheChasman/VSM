use crate::{CountError, CountEvent, CountResult, Party, Seats, TieBreak};
use std::collections::BTreeMap;

/// First Past the Post (FPTP): one seat to the party with most votes.
///
/// Used for FPTP and the constituency tier of AMS and Parallel. The margin is the
/// winner's lead over the runner-up (zero after a tie).
pub fn plurality(votes: &BTreeMap<Party, u64>, tie: TieBreak) -> Result<CountResult, CountError> {
    let top = *votes.values().max().ok_or(CountError::NoCandidates)?;
    let mut log = vec![CountEvent::Totals {
        round: 1,
        totals: votes.clone(),
        exhausted: 0,
    }];

    let leaders: Vec<Party> = votes
        .iter()
        .filter(|(_, &v)| v == top)
        .map(|(p, _)| p.clone())
        .collect();
    let winner = if leaders.len() == 1 {
        leaders[0].clone()
    } else {
        let (chosen, method) = tie.resolve(&leaders, &[], true, 0);
        log.push(CountEvent::Tie {
            round: 1,
            tied: leaders,
            chosen: chosen.clone(),
            method,
        });
        chosen
    };

    let runner_up = votes
        .iter()
        .filter(|(p, _)| **p != winner)
        .map(|(_, &v)| v)
        .max()
        .unwrap_or(0);
    log.push(CountEvent::Elected {
        round: 1,
        party: winner.clone(),
    });
    Ok(CountResult {
        seats: Seats::from([(winner, 1)]),
        margin: Some(top - runner_up),
        log,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::TieMethod;

    fn votes(v: &[(&str, u64)]) -> BTreeMap<Party, u64> {
        v.iter().map(|(p, n)| (p.to_string(), *n)).collect()
    }

    #[test]
    fn most_votes_wins_with_margin() {
        let r = plurality(
            &votes(&[("LAB", 18_000), ("CON", 12_500), ("LD", 9_000)]),
            TieBreak::Lot { seed: 1 },
        )
        .unwrap();
        assert_eq!(r.seats, Seats::from([("LAB".into(), 1)]));
        assert_eq!(r.margin, Some(5_500));
    }

    #[test]
    fn tie_is_resolved_by_lot_and_logged() {
        let r = plurality(
            &votes(&[("A", 100), ("B", 100), ("C", 5)]),
            TieBreak::Lot { seed: 9 },
        )
        .unwrap();
        assert_eq!(r.margin, Some(0));
        let tie = r
            .log
            .iter()
            .find(|e| matches!(e, CountEvent::Tie { .. }))
            .expect("tie logged");
        if let CountEvent::Tie { tied, method, .. } = tie {
            assert_eq!(tied, &vec!["A".to_string(), "B".to_string()]);
            assert_eq!(*method, TieMethod::Lot);
        }
    }

    #[test]
    fn no_candidates_is_an_error() {
        assert_eq!(
            plurality(&BTreeMap::new(), TieBreak::Lot { seed: 0 }),
            Err(CountError::NoCandidates)
        );
    }
}
