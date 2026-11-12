//! Golden test: Scottish Parliament 2021, Additional Member System (AMS). FPTP reproduces all 73
//! constituency winners; the compensatory top-up (D'Hondt, overhang kept, seven list seats per
//! region, constituency seats won in the region counted first) reproduces every region's
//! declared list seats and the national totals (docs/09_TESTING.md). Needs
//! `data/reference.sqlite` from `just ingest`.

use rusqlite::Connection;
use std::collections::BTreeMap;
use std::path::PathBuf;
use vsm_count::{
    compensatory_topup, plurality, CountEvent, Divisor, Overhang, Party, Seats, TieBreak,
};

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
struct Region {
    list_votes: BTreeMap<Party, u64>,
    declared: Seats,
    constituency_seats: Seats,
}

#[test]
#[ignore = "needs data/reference.sqlite; run `just golden`"]
fn ams_reproduces_holyrood_2021() {
    let db = reference_db();

    // Constituency tier: candidate votes, declared winner, and the region it sits in.
    let mut contests: BTreeMap<String, (String, BTreeMap<Party, u64>, Party)> = BTreeMap::new();
    let mut stmt = db
        .prepare(
            "SELECT c.gss_code, l.to_code, c.candidate_seq, c.party_code, c.votes, c.elected
             FROM candidate_result c
             JOIN geography_link l ON l.from_layer = 'SPC2021' AND l.from_code = c.gss_code
                                   AND l.to_layer = 'SPR2021'
             WHERE c.election_id = 'SP2021'",
        )
        .unwrap();
    let rows = stmt
        .query_map([], |r| {
            Ok((
                r.get::<_, String>(0)?,
                r.get::<_, String>(1)?,
                r.get::<_, i64>(2)?,
                r.get::<_, String>(3)?,
                r.get::<_, i64>(4)?,
                r.get::<_, i64>(5)?,
            ))
        })
        .unwrap();
    for row in rows {
        let (gss, region, seq, party, votes, elected) = row.unwrap();
        let c = contests.entry(gss).or_default();
        c.0 = region;
        // Key by sequence so two independents in one seat never merge.
        let key = format!("{seq:02}:{party}");
        c.1.insert(key.clone(), votes as u64);
        if elected == 1 {
            c.2 = key;
        }
    }
    assert_eq!(contests.len(), 73);

    let mut regions: BTreeMap<String, Region> = BTreeMap::new();
    let mut national: BTreeMap<String, u32> = BTreeMap::new();
    for (gss, (region, votes, declared)) in &contests {
        let r = plurality(votes, TieBreak::Lot { seed: 0 }).unwrap();
        assert!(
            !r.log.iter().any(|e| matches!(e, CountEvent::Tie { .. })),
            "{gss}: tie needed"
        );
        let winner = r.seats.keys().next().unwrap().clone();
        assert_eq!(&winner, declared, "{gss}: winner");
        let party = winner[3..].to_string();
        *regions
            .entry(region.clone())
            .or_default()
            .constituency_seats
            .entry(party.clone())
            .or_default() += 1;
        *national.entry(party).or_default() += 1;
    }

    // Regional tier: list votes and declared list seats. Individual candidates are their own
    // "party" (keyed by name), so they never pool votes.
    let mut stmt = db
        .prepare(
            "SELECT gss_code, party_code, individual_name, votes, seats FROM list_result
             WHERE election_id = 'SP2021'",
        )
        .unwrap();
    let rows = stmt
        .query_map([], |r| {
            Ok((
                r.get::<_, String>(0)?,
                r.get::<_, String>(1)?,
                r.get::<_, Option<String>>(2)?,
                r.get::<_, i64>(3)?,
                r.get::<_, i64>(4)?,
            ))
        })
        .unwrap();
    for row in rows {
        let (gss, party, individual, votes, seats) = row.unwrap();
        let key = individual.map_or(party, |n| format!("IND:{n}"));
        let g = regions.entry(gss).or_default();
        g.list_votes.insert(key.clone(), votes as u64);
        if seats > 0 {
            g.declared.insert(key, seats as u32);
        }
    }
    assert_eq!(regions.len(), 8);

    for (gss, g) in &regions {
        assert!(!g.list_votes.is_empty(), "{gss}: no list votes");
        let r = compensatory_topup(
            &g.list_votes,
            &g.constituency_seats,
            7,
            Divisor::DHondt,
            Overhang::Keep,
            TieBreak::Lot { seed: 0 },
        )
        .unwrap();
        assert!(
            !r.log.iter().any(|e| matches!(e, CountEvent::Tie { .. })),
            "{gss}: tie needed"
        );
        assert_eq!(r.seats, g.declared, "{gss}: list seats");
        for (p, n) in &r.seats {
            *national.entry(p.clone()).or_default() += n;
        }
    }

    // Declared result (EMB for Scotland, "SPE21 - Full Votes and Seats by Party/Candidate").
    let expected: BTreeMap<String, u32> =
        [("SNP", 64), ("CON", 31), ("LAB", 22), ("SGP", 8), ("LD", 4)]
            .into_iter()
            .map(|(p, n)| (p.to_string(), n))
            .collect();
    assert_eq!(national, expected);
}
