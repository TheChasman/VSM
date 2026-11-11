use crate::{CountError, CountEvent, CountResult, Party, Seats, TieBreak};
use std::cmp::Ordering;
use std::collections::BTreeMap;

/// Divisor series for highest-averages allocation.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Divisor {
    /// 1, 2, 3, …
    DHondt,
    /// 1, 3, 5, …
    SainteLague,
}

impl Divisor {
    fn of(self, seats_held: u32) -> u64 {
        match self {
            Self::DHondt => u64::from(seats_held) + 1,
            Self::SainteLague => 2 * u64::from(seats_held) + 1,
        }
    }
}

/// List PR and top-up tiers: allocate `seats` by highest averages.
///
/// `prior_seats` are seats a party already holds (for example, AMS constituency seats)
/// and count towards its divisor, so the same function serves compensatory top-ups.
/// Returned seats are those allocated **here** only. Quotients are compared exactly by
/// cross-multiplication. A tie for a seat is settled by higher votes, then the lot.
pub fn highest_averages(
    votes: &BTreeMap<Party, u64>,
    seats: u32,
    divisor: Divisor,
    prior_seats: &Seats,
    tie: TieBreak,
) -> Result<CountResult, CountError> {
    highest_averages_capped(votes, seats, divisor, prior_seats, &Seats::new(), tie)
}

/// As [`highest_averages`], but a list stops winning seats once it has won `caps[list]` here
/// (closed lists with fewer candidates than seats, or an individual candidate, whose cap is 1).
/// Lists missing from `caps` are uncapped. If every list is exhausted, `NoValidVotes`.
pub fn highest_averages_capped(
    votes: &BTreeMap<Party, u64>,
    seats: u32,
    divisor: Divisor,
    prior_seats: &Seats,
    caps: &Seats,
    tie: TieBreak,
) -> Result<CountResult, CountError> {
    if votes.is_empty() {
        return Err(CountError::NoCandidates);
    }
    if seats == 0 {
        return Err(CountError::NoSeats);
    }
    let mut log = vec![CountEvent::Totals {
        round: 1,
        totals: votes.clone(),
        exhausted: 0,
    }];
    let mut held: BTreeMap<&Party, u32> = votes
        .keys()
        .map(|p| (p, prior_seats.get(p).copied().unwrap_or(0)))
        .collect();
    let mut won = Seats::new();

    for seat in 1..=seats {
        // Quotient votes / d, compared as a/x vs b/y ⇔ a*y vs b*x.
        let cmp = |a: &Party, b: &Party| -> Ordering {
            let (va, da) = (u128::from(votes[a]), u128::from(divisor.of(held[a])));
            let (vb, db) = (u128::from(votes[b]), u128::from(divisor.of(held[b])));
            (va * db).cmp(&(vb * da))
        };
        let open = |p: &&Party| {
            caps.get(*p)
                .map_or(true, |&cap| won.get(*p).copied().unwrap_or(0) < cap)
        };
        let Some(best) = votes.keys().filter(open).max_by(|a, b| cmp(a, b)) else {
            return Err(CountError::NoValidVotes);
        };
        let tied: Vec<Party> = votes
            .keys()
            .filter(open)
            .filter(|p| cmp(p, best) == Ordering::Equal)
            .cloned()
            .collect();
        let winner = if tied.len() == 1 {
            tied[0].clone()
        } else {
            let (chosen, method) =
                tie.resolve(&tied, std::slice::from_ref(votes), true, u64::from(seat));
            log.push(CountEvent::Tie {
                round: seat,
                tied,
                chosen: chosen.clone(),
                method,
            });
            chosen
        };
        *held.get_mut(&winner).expect("known party") += 1;
        *won.entry(winner.clone()).or_insert(0) += 1;
        log.push(CountEvent::Elected {
            round: seat,
            party: winner,
        });
    }
    Ok(CountResult {
        seats: won,
        margin: None,
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
    fn seats(v: &[(&str, u32)]) -> Seats {
        v.iter().map(|(p, n)| (p.to_string(), *n)).collect()
    }
    const LOT: TieBreak = TieBreak::Lot { seed: 1 };

    // Textbook example: 100k/80k/30k/20k, 8 seats.
    fn example() -> BTreeMap<Party, u64> {
        votes(&[("A", 100_000), ("B", 80_000), ("C", 30_000), ("D", 20_000)])
    }

    #[test]
    fn dhondt_textbook() {
        let r = highest_averages(&example(), 8, Divisor::DHondt, &Seats::new(), LOT).unwrap();
        assert_eq!(r.seats, seats(&[("A", 4), ("B", 3), ("C", 1)]));
    }

    #[test]
    fn sainte_lague_differs_from_dhondt() {
        let r = highest_averages(&example(), 8, Divisor::SainteLague, &Seats::new(), LOT).unwrap();
        assert_eq!(r.seats, seats(&[("A", 3), ("B", 3), ("C", 1), ("D", 1)]));
    }

    #[test]
    fn prior_seats_make_a_compensatory_top_up() {
        // A already holds 4 constituency seats: the top-up favours others.
        let r = highest_averages(&example(), 4, Divisor::DHondt, &seats(&[("A", 4)]), LOT).unwrap();
        assert_eq!(r.seats, seats(&[("B", 3), ("C", 1)]));
    }

    #[test]
    fn exact_tie_falls_back_to_higher_votes_then_lot() {
        // A: 60/2 = 30 vs B: 30/1 = 30 for seat 2. A has higher votes.
        let tb = TieBreak::EarlierStageThenLot { seed: 0 };
        let r = highest_averages(
            &votes(&[("A", 60), ("B", 30)]),
            2,
            Divisor::DHondt,
            &Seats::new(),
            tb,
        )
        .unwrap();
        assert_eq!(r.seats, seats(&[("A", 2)]));
        assert!(r.log.iter().any(|e| matches!(
            e,
            CountEvent::Tie {
                method: TieMethod::EarlierStage,
                ..
            }
        )));
    }

    #[test]
    fn seats_always_sum_to_requested() {
        for n in 1..=20 {
            for d in [Divisor::DHondt, Divisor::SainteLague] {
                let r = highest_averages(&example(), n, d, &Seats::new(), LOT).unwrap();
                assert_eq!(r.seats.values().sum::<u32>(), n);
            }
        }
    }

    #[test]
    fn exhausted_lists_are_skipped() {
        // Without caps D'Hondt gives A 4, B 3, C 1. A has only 2 candidates; D is an individual.
        let caps = seats(&[("A", 2), ("D", 1)]);
        let r = highest_averages_capped(&example(), 8, Divisor::DHondt, &Seats::new(), &caps, LOT)
            .unwrap();
        assert_eq!(r.seats, seats(&[("A", 2), ("B", 4), ("C", 1), ("D", 1)]));
    }

    #[test]
    fn all_lists_exhausted_is_an_error() {
        let caps = seats(&[("A", 1), ("B", 1), ("C", 1), ("D", 1)]);
        let r = highest_averages_capped(&example(), 5, Divisor::DHondt, &Seats::new(), &caps, LOT);
        assert_eq!(r, Err(CountError::NoValidVotes));
    }

    #[test]
    fn zero_seats_is_an_error() {
        assert_eq!(
            highest_averages(&example(), 0, Divisor::DHondt, &Seats::new(), LOT),
            Err(CountError::NoSeats)
        );
    }
}
