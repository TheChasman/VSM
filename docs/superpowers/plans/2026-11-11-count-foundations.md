# Plan: count foundations (Phase 1, slice 1)

**Goal**: The Rust workspace, the first electoral rules in `vsm-count`, and a `vsm` binary that reports its version. No I/O in `vsm-count` ([05_COMPONENTS.md](../../05_COMPONENTS.md#count)).

**Branch / worktree**: `feature/count-foundations` / `.worktrees/count-foundations`

## Tasks

1. **Workspace.** Root `Cargo.toml` (resolver 2, edition 2021, `license = "MIT OR Apache-2.0"`), `crates/vsm-count`, `crates/vsm-cli`. `.gitignore` gains `target/`.
2. **Count types.** `Party` (string code), `CountResult { seats, margins, log }`, `CountEvent` log entries, `TieBreak` (`EarlierStage` then seeded `Lot`). Deterministic seeded lot via SplitMix64: no third-party RNG.
3. **`plurality`.** One seat from party X-votes. Margin = winner minus runner-up. Ties go to the declared tie-break and are logged.
4. **`highest_averages`.** D'Hondt and Sainte-Laguë, with `prior_seats` so the same function serves top-up tiers later. Unit tests include a textbook D'Hondt example and a Sainte-Laguë example that differs from it.
5. **`irv`.** Alternative Vote over weighted ranked ballots (weights as integer units, so no floating point). Exhausted ballots are logged per round. Elimination ties use earlier-round totals, then the lot.
6. **`vsm` CLI.** `vsm --version`, `vsm -V` and `vsm version` print `{"version","environment","commit"}` as JSON. Commit is embedded at build time (`unknown` outside git); environment comes from `VSM_ENV` (`unknown` if unset).
7. **Local checks.** `justfile` (`fmt`, `lint`, `test`, `check`) and a `scripts/hooks/pre-commit` hook (installed by `just hooks`) running `cargo fmt --check`, `cargo clippy -D warnings` and `cargo test`. No hosted CI (owner standing order).

## Out of scope

STV (needs ADR-0006 fixed-point), contingent, compensatory top-up, golden tests against real data (need `ingest`).

## Checks

`cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test`

## Slice 2 tasks

8. **`contingent`.** SV, and the Two-Round System (TRS) under S1. If no first-round majority, the top two continue and every other ballot transfers to whichever of the two it ranks higher. Ties for second place go to the declared tie-break.
9. **`compensatory_topup`.** AMS and AV+ top-up tier over list votes, given constituency seats. The overhang rule is a required parameter (`Overhang::Keep`, Holyrood practice, or `Overhang::Level`, which adds levelling seats until no party's entitlement is below its constituency seats). No default: open question in [05_COMPONENTS.md](../../05_COMPONENTS.md#count).

## Slice 3 tasks

10. **`stv_wigm_droop`.** Scottish council STV (Scottish Local Government Elections Order 2007 counting rules), fixed point per ADR-0006 (accepted 2026-11-11): every value is an integer count of 10^-`decimals` units, truncated. Droop quota on whole first preferences. One surplus per stage, largest first; WIGM transfers every paper held by the elected candidate at `surplus × paper value ÷ total`, truncated per paper. No surplus left: exclude the lowest, papers move at their current value. Ties: most recent earlier stage, then the lot. Elect all continuing candidates once they equal the remaining vacancies. Hand-worked tests now; golden tests against the 2022 ward ballot files follow `ingest`.

## Slice 4: ingest (Commons results) and the first golden test

11. **`vsm-ingest`** (`py/vsm_py/ingest/`, `uv`). `data/sources.toml` pins URL, licence and SHA-256 per source; a file on disk is never overwritten, a mismatch or unpinned hash stops, an archived copy is used when offline, `manual` sources (BES) must be placed by hand. `data/parties.toml` registry: unmapped spellings stop ingest, all listed at once. Commons loader cross-checks each contest's candidate votes against its valid-vote count and the file's grand total, one transaction per source.
12. **Golden test** `crates/vsm-count/tests/golden_ge2024.rs` (`just golden`): FPTP reproduces all 650 GE2024 winners and the declared seat totals.

**Deviations recorded:**
- Source is electionresults.parliament.uk (Open Parliament Licence), not the Commons Library briefing CSVs: the briefing site serves a Cloudflare browser challenge to scripted downloads.
- `httpx` and the standard `csv` module only. `polars` is unnecessary at 4,500 rows; add it when a source needs it.
- New `contest` table (per-election electorate, valid and invalid votes, declaration time). `constituency.area_km2` is nullable until `geography` runs.

## Slice 5: geography (areas and contiguity)

13. **`vsm-geography`** (`py/vsm_py/geography/`). Reads the verified boundary source, writes `constituency.area_km2` (BNG; NI in Irish Grid) and `adjacency` (land edges where the shared boundary is longer than zero, plus `data/crossings.toml`). Fails unless Great Britain and Northern Ireland are each one connected graph, and checks areas against `data/area_reference.toml` (warn above 1 %, fail above 5 %).

**Deviations recorded:**
- Boundaries come from the ONS July 2024 UK BFC file, not OS Boundary-Line: it covers Northern Ireland as well, under the same licence. Queried as one GeoJSON (235 MB, about 10 minutes); a repeated query returned identical bytes, so the checksum pins.
- `la_overlap` (G3) is deferred: the coterminosity rule (area or electors) is an open methodology question and needs local-authority boundaries.
- Eight crossings are declared for the four island groups; this list is a methodology input to confirm before freeze.

## Slice 6: geography register (ADR-0014)

14. **Register in ingest.** `data/geographies.toml` loads into `geography_layer` on every run (`geography_link` table created, unused until the first lookup lands). Every source may name a `layer`; boundary sources must. Ingest stops if a layer is unregistered, a register entry is malformed or names an unknown source, or any GSS code in a results or boundary file falls outside its layer's prefixes. `reference.sqlite` schema version 2: rebuild with `just ingest && just geography`.

## Slice 7: wards and local authorities at polling day

15. **ONS ward lookup** (`ons_wd_pcon_lad_lookup`): the July 2024 Ward → PCON → LAD → UTLA lookup ("as at 4th July 2024"), pinned whole-file CSV. Layers `WD20240704` and `LAD20240704` registered. Writes `geography_link`: ward → local authority (exact, every ward nests), ward → constituency (exact, or `partial` with no share for the 388 split wards). Stops on wards in more than one local authority or split wards not flagged. Two wards flagged split but listed once (E05015879 St Mary's, S13003041 Irvine South) are recorded as `partial` with a warning. Schema version 3.

**Deviation recorded:** ADR-0014 amended with the `partial` relation (official membership, share NULL), because ONS publishes no shares for split wards. Constituency → local authority shares for G3 are not computed: that waits for the G3 rule (area or electors).

## Slice 8: Senedd 2026 golden test

16. **`highest_averages_capped`**: lists stop winning once they reach their candidate number (individual candidates cap at 1).
17. **Senedd ingest**: `arcgis_names_codes` loads the ONS SENC 2026 names and codes into `area`; `senedd_briefing_pdf` parses the Senedd Research briefing with `pypdf` into `contest`, `list_result` and `seat_order`, cross-checking list votes against valid votes, six seats, and seats against the elected-member order. Layer `SENC2026` registered. Schema version 4.
18. **Golden test** `golden_sen2026.rs`: capped D'Hondt reproduces every constituency's seats and declared allocation order, and the national 43/34/9/7/2/1.

**Deviations and findings recorded:**
- Results source is the Senedd Research briefing PDF: no machine-readable per-constituency results were found. Its reuse terms are unconfirmed, so it is stored in `data/private/` and not redistributed.
- Name matching to codes is a recorded ADR-0014 exception (amendment).
- `ensure()` now treats any non-200 response as a failed download (the ONS hub answers 202 while generating a file).
- `write_register` upserts: deleting all layers each run broke foreign keys once `area` rows existed.
