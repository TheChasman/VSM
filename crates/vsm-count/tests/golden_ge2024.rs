//! Golden test: FPTP over every GE2024 constituency reproduces the declared winners and
//! seat totals (docs/09_TESTING.md). Needs `data/reference.sqlite` from `just ingest`,
//! so it is ignored by default; run it with `just golden`.

use rusqlite::Connection;
use std::collections::BTreeMap;
use std::path::PathBuf;
use vsm_count::{plurality, Party, TieBreak};

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

#[test]
#[ignore = "needs data/reference.sqlite; run `just golden`"]
fn fptp_reproduces_ge2024() {
    let db = reference_db();
    let mut stmt = db
        .prepare("SELECT gss_code, candidate_seq, party_code, votes, elected FROM candidate_result WHERE election_id = 'GE2024' ORDER BY gss_code, candidate_seq")
        .unwrap();
    // Per constituency: votes keyed by candidate (party codes repeat, e.g. several independents).
    let mut contests: BTreeMap<String, (BTreeMap<Party, u64>, String)> = BTreeMap::new();
    let rows = stmt
        .query_map([], |r| {
            Ok((
                r.get::<_, String>(0)?,
                r.get::<_, i64>(1)?,
                r.get::<_, String>(2)?,
                r.get::<_, i64>(3)?,
                r.get::<_, i64>(4)?,
            ))
        })
        .unwrap();
    for row in rows {
        let (gss, seq, party, votes, elected) = row.unwrap();
        let candidate = format!("{seq}:{party}");
        let entry = contests.entry(gss).or_default();
        entry.0.insert(candidate.clone(), votes as u64);
        if elected == 1 {
            entry.1 = candidate;
        }
    }
    assert_eq!(contests.len(), 650);

    let mut seats: BTreeMap<String, u32> = BTreeMap::new();
    for (gss, (votes, declared)) in &contests {
        let result = plurality(votes, TieBreak::Lot { seed: 0 }).unwrap();
        let winner = result.seats.keys().next().unwrap();
        assert_eq!(
            winner, declared,
            "{gss}: counted {winner}, declared {declared}"
        );
        assert!(result.margin.unwrap() > 0, "{gss}: tie");
        *seats
            .entry(winner.split_once(':').unwrap().1.to_string())
            .or_default() += 1;
    }

    // Declared GE2024 result (House of Commons, 4 July 2024).
    let expected: BTreeMap<String, u32> = [
        ("LAB", 411),
        ("CON", 121),
        ("LD", 72),
        ("SNP", 9),
        ("SF", 7),
        ("IND", 6),
        ("REF", 5),
        ("DUP", 5),
        ("GRN", 4),
        ("PC", 4),
        ("SDLP", 2),
        ("APNI", 1),
        ("UUP", 1),
        ("TUV", 1),
        ("SPK", 1),
    ]
    .into_iter()
    .map(|(p, n)| (p.to_string(), n))
    .collect();
    assert_eq!(seats, expected);
}
