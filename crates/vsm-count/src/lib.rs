//! Electoral count rules for Voting System Metrics (VSM).
//!
//! Every rule is a pure, deterministic function from ballots and parameters to a
//! [`CountResult`]. This crate does no I/O. It is the only place electoral rules exist.
//!
//! Votes and ballot weights are integers. Callers scale fractional survey weights to
//! integer units before counting, so results never depend on floating-point order.

mod highest_averages;
mod irv;
mod plurality;
mod tie;

pub use highest_averages::{highest_averages, Divisor};
pub use irv::{irv, RankedBallot};
pub use plurality::plurality;
pub use tie::TieBreak;

use serde::Serialize;
use std::collections::BTreeMap;

/// A party (or independent candidate) code, such as `"LAB"`.
pub type Party = String;

/// Seats won per party. Parties with no seats are omitted.
pub type Seats = BTreeMap<Party, u32>;

/// The outcome of one count.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct CountResult {
    pub seats: Seats,
    /// For single-winner rules, the winner's final margin over the runner-up, in vote units.
    /// For multi-seat rules, `None`.
    pub margin: Option<u64>,
    pub log: Vec<CountEvent>,
}

/// One step of a count, kept so every result can be audited.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(tag = "event", rename_all = "snake_case")]
pub enum CountEvent {
    /// Totals at the start of a round (IRV) or for the whole count (plurality).
    Totals {
        round: u32,
        totals: BTreeMap<Party, u64>,
        exhausted: u64,
    },
    Elected {
        round: u32,
        party: Party,
    },
    Eliminated {
        round: u32,
        party: Party,
    },
    /// A tie resolved by the declared tie-break.
    Tie {
        round: u32,
        tied: Vec<Party>,
        chosen: Party,
        method: TieMethod,
    },
}

/// How a tie was settled.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum TieMethod {
    EarlierStage,
    Lot,
}

/// Count errors. These are caller errors, never silent defaults.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CountError {
    NoCandidates,
    NoSeats,
    /// Every ballot is empty or exhausted before a winner is found.
    NoValidVotes,
}

impl std::fmt::Display for CountError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NoCandidates => write!(f, "no candidates"),
            Self::NoSeats => write!(f, "no seats to fill"),
            Self::NoValidVotes => write!(f, "no valid votes"),
        }
    }
}

impl std::error::Error for CountError {}
