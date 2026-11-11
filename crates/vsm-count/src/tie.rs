use crate::{Party, TieMethod};
use std::collections::BTreeMap;

/// The declared tie-break for a count.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TieBreak {
    /// Seeded lot only.
    Lot { seed: u64 },
    /// Prefer the party ahead at the most recent earlier stage that separates them,
    /// then fall back to a seeded lot. For single-stage rules this is the lot alone.
    EarlierStageThenLot { seed: u64 },
}

impl TieBreak {
    fn seed(self) -> u64 {
        match self {
            Self::Lot { seed } | Self::EarlierStageThenLot { seed } => seed,
        }
    }

    /// Choose one party from `tied` (sorted, at least two).
    ///
    /// `history` holds earlier-stage totals, oldest first. `prefer_high` selects the
    /// party with the higher earlier total (to elect) or the lower (to eliminate).
    /// `salt` makes repeated lots within one count independent.
    pub(crate) fn resolve(
        self,
        tied: &[Party],
        history: &[BTreeMap<Party, u64>],
        prefer_high: bool,
        salt: u64,
    ) -> (Party, TieMethod) {
        debug_assert!(tied.len() >= 2);
        if let Self::EarlierStageThenLot { .. } = self {
            for stage in history.iter().rev() {
                let total = |p: &Party| stage.get(p).copied().unwrap_or(0);
                let best = if prefer_high {
                    tied.iter().map(total).max()
                } else {
                    tied.iter().map(total).min()
                };
                let leaders: Vec<&Party> = tied.iter().filter(|p| Some(total(p)) == best).collect();
                if leaders.len() == 1 {
                    return (leaders[0].clone(), TieMethod::EarlierStage);
                }
            }
        }
        let mut sorted = tied.to_vec();
        sorted.sort();
        let index = (splitmix64(self.seed() ^ salt.wrapping_mul(0x9E37_79B9_7F4A_7C15))
            % sorted.len() as u64) as usize;
        (sorted[index].clone(), TieMethod::Lot)
    }
}

/// SplitMix64: a small, well-known, fully specified mixer. Stable across platforms.
fn splitmix64(mut x: u64) -> u64 {
    x = x.wrapping_add(0x9E37_79B9_7F4A_7C15);
    x = (x ^ (x >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    x = (x ^ (x >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    x ^ (x >> 31)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn p(s: &str) -> Party {
        s.to_string()
    }

    #[test]
    fn lot_is_deterministic_for_a_seed() {
        let tied = vec![p("A"), p("B"), p("C")];
        let a = TieBreak::Lot { seed: 42 }.resolve(&tied, &[], true, 0);
        let b = TieBreak::Lot { seed: 42 }.resolve(&tied, &[], true, 0);
        assert_eq!(a, b);
        assert_eq!(a.1, TieMethod::Lot);
    }

    #[test]
    fn lot_ignores_input_order() {
        let x = TieBreak::Lot { seed: 7 }.resolve(&[p("A"), p("B")], &[], true, 3);
        let y = TieBreak::Lot { seed: 7 }.resolve(&[p("B"), p("A")], &[], true, 3);
        assert_eq!(x, y);
    }

    #[test]
    fn earlier_stage_uses_most_recent_separating_stage() {
        let older = BTreeMap::from([(p("A"), 10), (p("B"), 20)]);
        let newer = BTreeMap::from([(p("A"), 30), (p("B"), 30)]);
        let tb = TieBreak::EarlierStageThenLot { seed: 0 };
        let (chosen, method) =
            tb.resolve(&[p("A"), p("B")], &[older.clone(), newer.clone()], true, 0);
        assert_eq!((chosen.as_str(), method), ("B", TieMethod::EarlierStage));
        let (chosen, _) = tb.resolve(&[p("A"), p("B")], &[older, newer], false, 0);
        assert_eq!(chosen, "A");
    }
}
