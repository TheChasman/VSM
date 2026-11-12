//! Methodology §4.4, worked example (docs/09_TESTING.md): X1 and X2 must reproduce the
//! published table exactly, ballot counts and scores, for every configuration.

use vsm_metrics::expressiveness::{x1, x2, BallotShape, Part, ReferenceContest};

struct Row {
    config: &'static str,
    x1_shape: BallotShape,
    x1_ballots: u128,
    x1: u32,
    x2_shape: BallotShape,
    x2_ballots: u128,
    x2: u32,
}

fn table() -> Vec<Row> {
    use BallotShape as B;
    use Part::*;
    let full_party_ranking = || B::at_least(vec![Ranking { max_ranks: 6 }]);
    vec![
        Row {
            config: "FPTP",
            x1_shape: B::exactly(vec![One]),
            x1_ballots: 6,
            x1: 24,
            x2_shape: B::none(),
            x2_ballots: 1,
            x2: 0,
        },
        Row {
            config: "TRS (two rounds)",
            // First round, then a choice between the two finalists.
            x1_shape: B::exactly(vec![One, Fixed { of: 2 }]),
            x1_ballots: 12,
            x1: 33,
            x2_shape: B::none(),
            x2_ballots: 1,
            x2: 0,
        },
        Row {
            config: "SV",
            // First preference, then blank or one of the other five.
            x1_shape: B::exactly(vec![Ranking { max_ranks: 2 }]),
            x1_ballots: 36,
            x1: 47,
            x2_shape: B::none(),
            x2_ballots: 1,
            x2: 0,
        },
        Row {
            config: "AMS, closed lists",
            // Constituency paper and list paper.
            x1_shape: B::exactly(vec![One, One]),
            x1_ballots: 36,
            x1: 47,
            x2_shape: B::none(),
            x2_ballots: 1,
            x2: 0,
        },
        Row {
            config: "AV",
            x1_shape: B::exactly(vec![Ranking { max_ranks: 6 }]),
            x1_ballots: 1_956,
            x1: 100,
            x2_shape: B::none(),
            x2_ballots: 1,
            x2: 0,
        },
        Row {
            config: "AV+ (personal list vote)",
            x1_shape: full_party_ranking(),
            x1_ballots: 1_956,
            x1: 100,
            x2_shape: B::exactly(vec![OneOrNone]),
            x2_ballots: 4,
            x2: 51,
        },
        Row {
            config: "Bloc Vote, 3 votes",
            x1_shape: B::exactly(vec![Votes {
                votes: 3,
                per_option: 3,
            }]),
            x1_ballots: 83,
            x1: 58,
            x2_shape: B::exactly(vec![Votes {
                votes: 3,
                per_option: 1,
            }]),
            x2_ballots: 7,
            x2: 72,
        },
        Row {
            config: "Limited Vote, 2 votes",
            x1_shape: B::exactly(vec![Votes {
                votes: 2,
                per_option: 2,
            }]),
            x1_ballots: 27,
            x1: 44,
            x2_shape: B::exactly(vec![Votes {
                votes: 2,
                per_option: 1,
            }]),
            x2_ballots: 6,
            x2: 66,
        },
        Row {
            config: "Closed-list PR",
            x1_shape: B::exactly(vec![One]),
            x1_ballots: 6,
            x1: 24,
            x2_shape: B::none(),
            x2_ballots: 1,
            x2: 0,
        },
        Row {
            config: "Open-list PR (one preference vote)",
            x1_shape: B::exactly(vec![One]),
            x1_ballots: 6,
            x1: 24,
            x2_shape: B::exactly(vec![OneOrNone]),
            x2_ballots: 4,
            x2: 51,
        },
        Row {
            config: "STV",
            x1_shape: full_party_ranking(),
            x1_ballots: 1_956,
            x1: 100,
            x2_shape: B::exactly(vec![Ranking { max_ranks: 3 }]),
            x2_ballots: 15,
            x2: 100,
        },
    ]
}

#[test]
fn reproduces_methodology_table_4_4() {
    let contest = ReferenceContest::METHODOLOGY;
    let mut wrong = Vec::new();
    for row in table() {
        let a = x1(&row.x1_shape, contest);
        let b = x2(&row.x2_shape, contest);
        let got = (a.ballots, a.score, b.ballots, b.score);
        let want = (row.x1_ballots, row.x1, row.x2_ballots, row.x2);
        if got != want {
            wrong.push(format!("{}: got {got:?}, want {want:?}", row.config));
        }
    }
    assert!(wrong.is_empty(), "§4.4 mismatches:\n{}", wrong.join("\n"));
}

#[test]
fn published_bits_to_two_decimals() {
    let contest = ReferenceContest::METHODOLOGY;
    let bits: Vec<String> = table()
        .iter()
        .map(|r| format!("{:.2}", x1(&r.x1_shape, contest).bits))
        .collect();
    assert_eq!(
        bits,
        [
            "2.58", "3.58", "5.17", "5.17", "10.93", "10.93", "6.38", "4.75", "2.58", "2.58",
            "10.93"
        ]
    );
}
