//! Golden test: D'Hondt over each Senedd 2026 constituency (six seats, closed lists capped at
//! their candidate numbers) reproduces the declared seats and the declared order in which they
//! were allocated (docs/09_TESTING.md). Needs `data/reference.sqlite` from `just ingest`.

use rusqlite::Connection;
use std::collections::BTreeMap;
use std::path::PathBuf;
use vsm_count::{highest_averages_capped, CountEvent, Divisor, Party, Seats, TieBreak};

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
struct Contest {
    votes: BTreeMap<Party, u64>,
    caps: Seats,
    declared: Seats,
    order: Vec<Party>,
}

#[test]
#[ignore = "needs data/reference.sqlite; run `just golden`"]
fn dhondt_reproduces_senedd_2026() {
    let db = reference_db();
    let mut contests: BTreeMap<String, Contest> = BTreeMap::new();
    let key = |seq: i64, party: &str| format!("{seq:02}:{party}");

    let mut lists = db
        .prepare("SELECT gss_code, list_seq, party_code, votes, seats, candidates FROM list_result WHERE election_id = 'SEN2026'")
        .unwrap();
    let rows = lists
        .query_map([], |r| {
            Ok((
                r.get::<_, String>(0)?,
                r.get::<_, i64>(1)?,
                r.get::<_, String>(2)?,
                r.get::<_, i64>(3)?,
                r.get::<_, i64>(4)?,
                r.get::<_, i64>(5)?,
            ))
        })
        .unwrap();
    for row in rows {
        let (gss, seq, party, votes, seats, candidates) = row.unwrap();
        let c = contests.entry(gss).or_default();
        let k = key(seq, &party);
        c.votes.insert(k.clone(), votes as u64);
        c.caps.insert(k.clone(), candidates as u32);
        if seats > 0 {
            c.declared.insert(k, seats as u32);
        }
    }
    let mut order = db
        .prepare("SELECT s.gss_code, s.list_seq, l.party_code FROM seat_order s JOIN list_result l USING (election_id, gss_code, list_seq) WHERE s.election_id = 'SEN2026' ORDER BY s.gss_code, s.position")
        .unwrap();
    for row in order
        .query_map([], |r| {
            Ok((
                r.get::<_, String>(0)?,
                r.get::<_, i64>(1)?,
                r.get::<_, String>(2)?,
            ))
        })
        .unwrap()
    {
        let (gss, seq, party) = row.unwrap();
        contests.get_mut(&gss).unwrap().order.push(key(seq, &party));
    }
    assert_eq!(contests.len(), 16);

    let mut national: BTreeMap<String, u32> = BTreeMap::new();
    for (gss, c) in &contests {
        let r = highest_averages_capped(
            &c.votes,
            6,
            Divisor::DHondt,
            &Seats::new(),
            &c.caps,
            TieBreak::Lot { seed: 0 },
        )
        .unwrap();
        assert!(
            !r.log.iter().any(|e| matches!(e, CountEvent::Tie { .. })),
            "{gss}: tie needed"
        );
        assert_eq!(r.seats, c.declared, "{gss}: seats");
        let allocated: Vec<Party> = r
            .log
            .iter()
            .filter_map(|e| match e {
                CountEvent::Elected { party, .. } => Some(party.clone()),
                _ => None,
            })
            .collect();
        assert_eq!(allocated, c.order, "{gss}: allocation order");
        for (k, n) in &r.seats {
            *national.entry(k[3..].to_string()).or_default() += n;
        }
    }

    // Declared result (Senedd Research, "Senedd election 2026: Research Briefing").
    let expected: BTreeMap<String, u32> = [
        ("PC", 43),
        ("REF", 34),
        ("LAB", 9),
        ("CON", 7),
        ("GRN", 2),
        ("LD", 1),
    ]
    .into_iter()
    .map(|(p, n)| (p.to_string(), n))
    .collect();
    assert_eq!(national, expected);
}
