//! Golden test: Scottish council elections, 5 May 2022. Single Transferable Vote (STV),
//! Weighted Inclusive Gregory Method (WIGM), Droop quota, five decimal places (Scottish Local
//! Government Elections Order 2007, rule 48(3)). For every contested ward, `stv_wigm_droop` over
//! the returning officer's preference profile must elect exactly the declared councillors, each
//! at the declared stage; wherever declared stage totals are loaded (City of Edinburgh), every
//! candidate's total and the non-transferable total must match at every stage, to 10^-5.
//! Uncontested wards (no poll) are checked and named. Needs `data/reference.sqlite` from
//! `just ingest`.

use rusqlite::Connection;
use std::collections::{BTreeMap, BTreeSet};
use std::path::PathBuf;
use vsm_count::{stv_wigm_droop, CountEvent, RankedBallot, StvParams, TieBreak};

const ELECTION: &str = "LG2022S";

fn reference_db() -> Connection {
    let path = std::env::var_os("VSM_REFERENCE_DB")
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../data/reference.sqlite")
        });
    assert!(
        path.exists(),
        "{} missing: run `just ingest` first",
        path.display()
    );
    Connection::open_with_flags(path, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)
        .expect("open reference.sqlite")
}

#[derive(Default)]
struct Ward {
    name: String,
    seats: u32,
    /// candidate_seq (as text) -> declared stage of election, if elected.
    declared: BTreeMap<String, Option<u32>>,
    ballots: Vec<RankedBallot>,
    /// stage -> candidate_seq (0 = non-transferable) -> declared total, 10^-5 units.
    stages: BTreeMap<u32, BTreeMap<i64, u64>>,
}

fn load(db: &Connection) -> BTreeMap<String, Ward> {
    let mut wards: BTreeMap<String, Ward> = BTreeMap::new();
    let mut stmt = db
        .prepare(
            "SELECT c.gss_code, a.name, c.seats FROM contest c
             JOIN area a ON a.layer_id = 'WD2022S' AND a.gss_code = c.gss_code
             WHERE c.election_id = ?1",
        )
        .unwrap();
    for row in stmt
        .query_map([ELECTION], |r| {
            Ok((r.get::<_, String>(0)?, r.get::<_, String>(1)?, r.get(2)?))
        })
        .unwrap()
    {
        let (gss, name, seats): (String, String, u32) = row.unwrap();
        let w = wards.entry(gss).or_default();
        w.name = name;
        w.seats = seats;
    }
    let mut stmt = db
        .prepare(
            "SELECT gss_code, candidate_seq, stage_elected FROM stv_candidate
             WHERE election_id = ?1",
        )
        .unwrap();
    for row in stmt
        .query_map([ELECTION], |r| {
            Ok((
                r.get::<_, String>(0)?,
                r.get::<_, i64>(1)?,
                r.get::<_, Option<u32>>(2)?,
            ))
        })
        .unwrap()
    {
        let (gss, seq, stage) = row.unwrap();
        wards
            .get_mut(&gss)
            .unwrap()
            .declared
            .insert(seq.to_string(), stage);
    }
    let mut stmt = db
        .prepare(
            "SELECT gss_code, weight, ranking FROM stv_ballot WHERE election_id = ?1
             ORDER BY gss_code, ballot_seq",
        )
        .unwrap();
    for row in stmt
        .query_map([ELECTION], |r| {
            Ok((
                r.get::<_, String>(0)?,
                r.get::<_, i64>(1)?,
                r.get::<_, String>(2)?,
            ))
        })
        .unwrap()
    {
        let (gss, weight, ranking) = row.unwrap();
        wards.get_mut(&gss).unwrap().ballots.push(RankedBallot {
            ranking: ranking.split(' ').map(str::to_string).collect(),
            weight: weight as u64,
        });
    }
    let mut stmt = db
        .prepare(
            "SELECT gss_code, stage, candidate_seq, votes_e5 FROM stv_stage
             WHERE election_id = ?1",
        )
        .unwrap();
    for row in stmt
        .query_map([ELECTION], |r| {
            Ok((
                r.get::<_, String>(0)?,
                r.get::<_, u32>(1)?,
                r.get::<_, i64>(2)?,
                r.get::<_, i64>(3)?,
            ))
        })
        .unwrap()
    {
        let (gss, stage, seq, votes) = row.unwrap();
        wards
            .get_mut(&gss)
            .unwrap()
            .stages
            .entry(stage)
            .or_default()
            .insert(seq, votes as u64);
    }
    wards
}

#[test]
#[ignore = "needs data/reference.sqlite; run `just golden`"]
fn stv_reproduces_scottish_councils_2022() {
    let db = reference_db();
    let wards = load(&db);
    assert_eq!(wards.len(), 355, "wards");
    assert_eq!(
        wards.values().map(|w| w.seats).sum::<u32>(),
        1226,
        "vacancies"
    );

    let mut failures: Vec<String> = Vec::new();
    let mut uncontested: Vec<String> = Vec::new();
    let (mut contested, mut stage_checked, mut stage_values) = (0usize, 0usize, 0usize);
    for (gss, w) in &wards {
        let declared: BTreeSet<&String> = w
            .declared
            .iter()
            .filter(|(_, s)| s.is_some())
            .map(|(c, _)| c)
            .collect();
        let candidates: Vec<String> = w.declared.keys().cloned().collect();
        if w.ballots.is_empty() {
            // No poll: every candidate is returned, and any vacancy left is unfilled.
            assert!(candidates.len() as u32 <= w.seats, "{gss}: no ballots");
            assert_eq!(declared.len(), candidates.len(), "{gss}: uncontested");
            uncontested.push(format!(
                "{gss} {} ({} candidates, {} seats)",
                w.name,
                candidates.len(),
                w.seats
            ));
            continue;
        }
        contested += 1;
        let r = stv_wigm_droop(
            &w.ballots,
            &candidates,
            w.seats,
            StvParams::SCOTTISH,
            TieBreak::EarlierStageThenLot { seed: 0 },
        )
        .unwrap();
        let mut elected_at: BTreeMap<String, u32> = BTreeMap::new();
        let mut totals: BTreeMap<u32, (BTreeMap<String, u64>, u64)> = BTreeMap::new();
        for e in &r.log {
            match e {
                CountEvent::Elected { round, party } => {
                    elected_at.insert(party.clone(), *round);
                }
                CountEvent::Totals {
                    round,
                    totals: t,
                    exhausted,
                } => {
                    totals.insert(*round, (t.clone(), *exhausted));
                }
                CountEvent::Tie { round, method, .. } => failures.push(format!(
                    "{gss} {}: tie at stage {round} settled by {method:?}",
                    w.name
                )),
                _ => {}
            }
        }
        let won: BTreeSet<&String> = r.seats.keys().collect();
        if won != declared {
            failures.push(format!(
                "{gss} {}: elected {won:?}, declared {declared:?}",
                w.name
            ));
            continue;
        }
        for (c, stage) in &w.declared {
            if let Some(s) = stage {
                if elected_at.get(c) != Some(s) {
                    failures.push(format!(
                        "{gss} {}: candidate {c} elected at stage {:?}, declared {s}",
                        w.name,
                        elected_at.get(c)
                    ));
                }
            }
        }
        if !w.stages.is_empty() {
            stage_checked += 1;
        }
        for (stage, want) in &w.stages {
            let Some((got, exhausted)) = totals.get(stage) else {
                failures.push(format!(
                    "{gss} {}: declared stage {stage} not reached (count ended at {})",
                    w.name,
                    totals.len()
                ));
                continue;
            };
            for (seq, v) in want {
                stage_values += 1;
                let mine = if *seq == 0 {
                    *exhausted
                } else {
                    got[&seq.to_string()]
                };
                if mine != *v {
                    failures.push(format!(
                        "{gss} {}: stage {stage} candidate {seq}: {mine}, declared {v} (10^-5)",
                        w.name
                    ));
                }
            }
        }
    }
    println!(
        "LG2022S: {contested} contested wards counted; {} uncontested (no poll):",
        uncontested.len()
    );
    for u in &uncontested {
        println!("  {u}");
    }
    println!("declared stage totals checked in {stage_checked} wards ({stage_values} values)");
    assert_eq!(contested + uncontested.len(), 355);
    assert!(
        failures.is_empty(),
        "{} mismatches:\n{}",
        failures.len(),
        failures.join("\n")
    );
}
