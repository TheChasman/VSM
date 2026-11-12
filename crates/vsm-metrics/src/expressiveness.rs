//! Axis X, ballot expressiveness (methodology §4, axis 4).
//!
//! X1 and X2 are bits: log₂ of the number of distinct valid ballots a voter can cast in the
//! fixed reference contest (6 parties, 3 candidates each in multi-member configurations,
//! blank ballots excluded). Ballot counts are derived here from the ballot's structure, not
//! copied from the methodology table, so the worked example (§4.4) is a real test.

use serde::Serialize;

/// The pre-registered reference contest (P10).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct ReferenceContest {
    pub parties: u32,
    pub candidates_per_party: u32,
}

impl ReferenceContest {
    pub const METHODOLOGY: Self = Self {
        parties: 6,
        candidates_per_party: 3,
    };
}

/// Score denominators exactly as written in the methodology (§4, axis 4): "100 × bits ÷ 10.93"
/// and "100 × bits ÷ 3.91". They are the rounded bits of a complete optional ranking of 6 and
/// of 3 options. The rounded constants are used, not log₂(1956) and log₂(15): the published
/// table depends on it (Limited Vote X1 is 44 with 10.93, 43 with the exact value).
pub const X1_DENOMINATOR: f64 = 10.93;
pub const X2_DENOMINATOR: f64 = 3.91;

/// One part of a ballot. A ballot made of several parts (two papers, two rounds) has the
/// product of its parts' counts.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case", tag = "kind")]
pub enum Part {
    /// Exactly one of `options` (a single X vote).
    One,
    /// One of `of` already-determined options (a run-off between two finalists).
    Fixed { of: u32 },
    /// Optionally one of the options: blank allowed (an open-list preference vote).
    OneOrNone,
    /// A ranking of 1 to `max_ranks` distinct options (AV, STV, SV with `max_ranks = 2`).
    Ranking { max_ranks: u32 },
    /// Between 1 and `votes` votes, each for an option, at most `per_option` per option.
    /// Counts multisets (Bloc and Limited Vote at party level).
    Votes { votes: u32, per_option: u32 },
}

/// A ballot as seen at one level (parties for X1, one party's candidates for X2).
/// `at_least` marks a lower bound: the real ballot permits more (ranking 18 STV candidates
/// covers every party ranking). The score caps at 100, so a lower bound at the cap is exact.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct BallotShape {
    pub parts: Vec<Part>,
    pub at_least: bool,
}

impl BallotShape {
    pub fn exactly(parts: Vec<Part>) -> Self {
        Self {
            parts,
            at_least: false,
        }
    }
    pub fn at_least(parts: Vec<Part>) -> Self {
        Self {
            parts,
            at_least: true,
        }
    }
    /// No choice at this level: one ballot, zero bits.
    pub fn none() -> Self {
        Self::exactly(Vec::new())
    }
}

/// Number of distinct valid ballots over `options` options.
pub fn ballots(shape: &BallotShape, options: u32) -> u128 {
    shape
        .parts
        .iter()
        .map(|p| part_count(*p, options))
        .product()
}

fn part_count(part: Part, n: u32) -> u128 {
    let n = u128::from(n);
    match part {
        Part::One => n,
        Part::Fixed { of } => u128::from(of),
        Part::OneOrNone => n + 1,
        Part::Ranking { max_ranks } => {
            // Σ_{k=1..m} n!/(n−k)!
            let mut total = 0;
            let mut perms = 1;
            for k in 0..u128::from(max_ranks).min(n) {
                perms *= n - k;
                total += perms;
            }
            total
        }
        Part::Votes { votes, per_option } => multisets(n, votes, per_option),
    }
}

/// Multisets of size 1..=`votes` over `n` options, each option used at most `cap` times.
fn multisets(n: u128, votes: u32, cap: u32) -> u128 {
    // ways[s] = multisets of size s over the options seen so far.
    let size = votes as usize;
    let mut ways = vec![0u128; size + 1];
    ways[0] = 1;
    for _ in 0..n {
        let mut next = vec![0u128; size + 1];
        for (s, w) in ways.iter().enumerate() {
            for use_ in 0..=cap as usize {
                if s + use_ <= size {
                    next[s + use_] += w;
                }
            }
        }
        ways = next;
    }
    ways[1..].iter().sum()
}

/// One sub-metric value with its working, as reported in the method notes.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Expressiveness {
    pub ballots: u128,
    pub at_least: bool,
    pub bits: f64,
    pub score: u32,
}

fn score(shape: &BallotShape, options: u32, denominator: f64) -> Expressiveness {
    let ballots = ballots(shape, options);
    // Blank ballots are excluded, so a valid ballot always exists.
    let bits = (ballots as f64).log2();
    let raw = (100.0 * bits / denominator).min(100.0);
    Expressiveness {
        ballots,
        at_least: shape.at_least,
        bits,
        score: raw.round() as u32,
    }
}

/// X1, inter-party expressiveness: the ballot over the parties, each treated as one option.
pub fn x1(shape: &BallotShape, contest: ReferenceContest) -> Expressiveness {
    score(shape, contest.parties, X1_DENOMINATOR)
}

/// X2, intra-party expressiveness: the ballot over one party's candidates.
pub fn x2(shape: &BallotShape, contest: ReferenceContest) -> Expressiveness {
    score(shape, contest.candidates_per_party, X2_DENOMINATOR)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn complete_optional_ranking_matches_denominators() {
        let full = |n| BallotShape::exactly(vec![Part::Ranking { max_ranks: n }]);
        assert_eq!(ballots(&full(6), 6), 1_956);
        assert_eq!(ballots(&full(3), 3), 15);
    }

    #[test]
    fn capped_multisets() {
        // Sizes 1..=3 over 6 options, up to 3 each: 6 + 21 + 56.
        assert_eq!(multisets(6, 3, 3), 83);
        // A cap below the vote count removes the repeated patterns: no option thrice.
        assert_eq!(multisets(6, 3, 2), 83 - 6);
        // Subsets (cap 1) of up to 2 of 3 candidates: 3 + 3.
        assert_eq!(multisets(3, 2, 1), 6);
    }

    #[test]
    fn score_caps_at_one_hundred() {
        let stv = BallotShape::at_least(vec![Part::Ranking { max_ranks: 6 }]);
        let x = x1(&stv, ReferenceContest::METHODOLOGY);
        assert_eq!(x.score, 100);
        assert!(x.at_least);
    }
}
