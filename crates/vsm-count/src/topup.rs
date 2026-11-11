use crate::{
    highest_averages, CountError, CountEvent, CountResult, Divisor, Party, Seats, TieBreak,
};
use serde::Serialize;
use std::collections::BTreeMap;

/// What to do when a party wins more constituency seats than its list-vote entitlement.
/// Configurations must declare this: there is no default.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Overhang {
    /// Keep overhang seats; the top-up tier stays at its fixed size (Holyrood, Senedd to 2021).
    Keep,
    /// Add levelling seats to the top-up tier until no party's entitlement is below its
    /// constituency seats. `max_extra` bounds the growth.
    Level { max_extra: u32 },
}

/// Compensatory top-up tier for AMS and AV+.
///
/// `constituency_seats` are seats already won in the constituency tier. Returns the
/// top-up seats only. Parties without list votes (for example, independents) keep their
/// constituency seats and take no part in the top-up.
pub fn compensatory_topup(
    list_votes: &BTreeMap<Party, u64>,
    constituency_seats: &Seats,
    topup_seats: u32,
    divisor: Divisor,
    overhang: Overhang,
    tie: TieBreak,
) -> Result<CountResult, CountError> {
    match overhang {
        Overhang::Keep => {
            highest_averages(list_votes, topup_seats, divisor, constituency_seats, tie)
        }
        Overhang::Level { max_extra } => {
            let held = |p: &Party| constituency_seats.get(p).copied().unwrap_or(0);
            let base: u32 = list_votes.keys().map(held).sum();
            for extra in 0..=max_extra {
                let total = base + topup_seats + extra;
                let full = highest_averages(list_votes, total, divisor, &Seats::new(), tie)?;
                let fits = list_votes
                    .keys()
                    .all(|p| full.seats.get(p).copied().unwrap_or(0) >= held(p));
                if !fits {
                    continue;
                }
                let seats: Seats = list_votes
                    .keys()
                    .filter_map(|p| {
                        let n = full.seats.get(p).copied().unwrap_or(0) - held(p);
                        (n > 0).then(|| (p.clone(), n))
                    })
                    .collect();
                let mut log = vec![CountEvent::Totals {
                    round: 1,
                    totals: list_votes.clone(),
                    exhausted: 0,
                }];
                if extra > 0 {
                    log.push(CountEvent::LevellingSeats { added: extra });
                }
                log.extend(seats.keys().map(|p| CountEvent::Elected {
                    round: 1,
                    party: p.clone(),
                }));
                return Ok(CountResult {
                    seats,
                    margin: None,
                    log,
                });
            }
            Err(CountError::LevellingLimit)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn votes(v: &[(&str, u64)]) -> BTreeMap<Party, u64> {
        v.iter().map(|(p, n)| (p.to_string(), *n)).collect()
    }
    fn seats(v: &[(&str, u32)]) -> Seats {
        v.iter().map(|(p, n)| (p.to_string(), *n)).collect()
    }
    const LOT: TieBreak = TieBreak::Lot { seed: 1 };

    #[test]
    fn keep_matches_holyrood_style_dhondt() {
        // One region, 7 list seats. SNP sweeps 9 constituencies.
        let list = votes(&[
            ("SNP", 120_000),
            ("CON", 70_000),
            ("LAB", 60_000),
            ("GRN", 25_000),
            ("LD", 15_000),
        ]);
        let r = compensatory_topup(
            &list,
            &seats(&[("SNP", 9)]),
            7,
            Divisor::DHondt,
            Overhang::Keep,
            LOT,
        )
        .unwrap();
        assert_eq!(r.seats.values().sum::<u32>(), 7);
        assert!(!r.seats.contains_key("SNP"));
        assert_eq!(r.seats, seats(&[("CON", 3), ("LAB", 3), ("GRN", 1)]));
    }

    #[test]
    fn level_adds_seats_until_overhang_is_absorbed() {
        // A wins all 6 constituencies on 40 %; 4 top-up seats can't make it proportional.
        let list = votes(&[("A", 40), ("B", 35), ("C", 25)]);
        let cons = seats(&[("A", 6)]);
        let r = compensatory_topup(
            &list,
            &cons,
            4,
            Divisor::SainteLague,
            Overhang::Level { max_extra: 20 },
            LOT,
        )
        .unwrap();
        let added = r.log.iter().find_map(|e| match e {
            CountEvent::LevellingSeats { added } => Some(*added),
            _ => None,
        });
        assert!(added.is_some_and(|n| n > 0));
        // Final house is proportional: A's 6 seats are its entitlement.
        let total = 6 + r.seats.values().sum::<u32>();
        let b = r.seats["B"];
        assert!(b * 100 / total >= 30, "B {b} of {total}");
    }

    #[test]
    fn level_without_overhang_adds_nothing() {
        let list = votes(&[("A", 50), ("B", 50)]);
        let r = compensatory_topup(
            &list,
            &seats(&[("A", 2), ("B", 2)]),
            4,
            Divisor::DHondt,
            Overhang::Level { max_extra: 5 },
            LOT,
        )
        .unwrap();
        assert_eq!(r.seats, seats(&[("A", 2), ("B", 2)]));
        assert!(!r
            .log
            .iter()
            .any(|e| matches!(e, CountEvent::LevellingSeats { .. })));
    }

    #[test]
    fn level_limit_is_an_error_not_a_silent_default() {
        let list = votes(&[("A", 1), ("B", 99)]);
        let r = compensatory_topup(
            &list,
            &seats(&[("A", 10)]),
            2,
            Divisor::DHondt,
            Overhang::Level { max_extra: 3 },
            LOT,
        );
        assert_eq!(r, Err(CountError::LevellingLimit));
    }
}
