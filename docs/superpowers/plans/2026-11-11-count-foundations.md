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
