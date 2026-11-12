# AGENTS.md

Instructions for AI coding agents working in this repository. Read by Cursor, Aider, Codex, Continue, Claude Code, and any other agent that supports the AGENTS.md convention.

For Claude-specific additions, see [CLAUDE.md](CLAUDE.md).

## Project

- **Name**: Voting System Metrics (VSM)
- **Purpose**: A reproducible, UK-grounded scoring engine and public results site that measures how candidate electoral systems would perform as a replacement for First Past the Post (FPTP) in UK General Elections.
- **Stack**: Rust (counting, districts, metrics, views), Python 3.12+ via `uv` (ingest, geography, preference modelling), SQLite (run store), SvelteKit static site
- **Specs**: [`docs/00_INDEX.md`](docs/00_INDEX.md) for the software; [`research/new-metrics.md`](research/new-metrics.md) for the methodology

## Ground rules

- UK English in all generated text, comments and documentation.
- Match the project's existing style. Read a couple of nearby files before adding a new one.
- Prefer small, reviewable changes. If a task balloons, stop and ask.
- Never push to `main`. Open a branch and a pull request.
- Do not commit secrets. See [`docs/06_SECURITY.md`](docs/06_SECURITY.md).
- When in doubt about a design choice, check [`docs/10_DECISIONS.md`](docs/10_DECISIONS.md) before inventing a new approach.

### Rules specific to this project

1. **The methodology is not yours to change.** Anchors, star bands, weights, sub-metric definitions, applicability and grades live in `spec/*.toml`, derived from `research/`. Never hard-code any of them in Rust, Python or Svelte. If code needs a methodology value, read it from the spec crate or loader.
2. **Never edit a frozen spec file** without being explicitly asked. If `spec/FROZEN` exists, changes need a version bump and a methodology changelog entry. The pre-commit hook enforces this.
3. **N/A is not zero.** A sub-metric that does not apply is `null` or absent. Never write `0` to mean "not applicable".
4. **Determinism is a requirement.** All randomness goes through seeded streams derived from the spec hash (ADR-0005). No `HashMap` iteration into outputs, no wall-clock values in outputs, no thread-order dependence.
5. **No respondent-level British Election Study (BES) data** in commits, fixtures, logs, test output or examples. `data/private/` is off limits for anything except reading by the preferences stage.
6. **Electoral rules live only in `crates/vsm-count`.** Do not reimplement a count elsewhere, including in the site.
7. **Do not invent numbers.** No example scores in docs, comments or UI copy unless they come from a real run or the methodology's worked examples.
8. Use the methodology's identifiers exactly: configurations C01–C20, axes P E W X S C G F A I, sub-metrics such as P1 or E3.

## Build, test, run

```bash
# install
just setup

# run tests
just test

# run the pipeline and serve the site locally
just pipeline && just publish && (cd site && npm run dev)
```

## Code style

```bash
cargo fmt --all && cargo clippy --all-targets -- -D warnings
uv run ruff format && uv run ruff check --fix
(cd site && npm run format && npm run lint)
```

- Rust: no `unwrap()` outside tests. Return `Result` with `thiserror` error types. Prefer `BTreeMap` to `HashMap` where data reaches outputs.
- Python: type hints on public functions. `polars` rather than `pandas` for new code.
- Svelte: TypeScript. No third-party runtime scripts (ADR-0011).

## Repository layout

```
spec/          frozen methodology (TOML) + JSON Schemas + FROZEN hash file
research/      methodology documents (Markdown)
crates/        Rust workspace: vsm-spec, vsm-count, vsm-districts, vsm-runs, vsm-metrics, vsm-views, vsm-cli
py/            Python package vsm_py: ingest, geography, preferences
schema/        SQL migrations for reference.sqlite and runs.sqlite
data/          sources.toml, crossings.toml, raw/ (open data), private/ (git-ignored)
fixtures/      Wales subset, hand-built count cases
site/          SvelteKit static site
bundle/        published JSON output (generated)
docs/          this DDD suite
justfile
```

## What to read first

For non-trivial changes, read in this order:

1. [`docs/01_OVERVIEW.md`](docs/01_OVERVIEW.md): what the project does
2. [`docs/02_ARCHITECTURE.md`](docs/02_ARCHITECTURE.md): how it fits together
3. The relevant per-component spec in [`docs/05_COMPONENTS.md`](docs/05_COMPONENTS.md)
4. The relevant methodology section in [`research/new-metrics.md`](research/new-metrics.md)
5. Recent entries in [`docs/10_DECISIONS.md`](docs/10_DECISIONS.md): why things are the way they are

## Out of bounds

Do not touch these without explicit human direction:

- `spec/` once frozen, and `spec/FROZEN` at any time
- `research/` (methodology documents are maintained by the project owner)
- `data/private/`
- Published bundles and release tags
- Anchor, weight or band values anywhere
- Git hooks (`scripts/hooks/`) and the deploy script

## House conventions for generated output

- Introduce abbreviations in brackets at first occurrence ("Single Transferable Vote (STV)").
- ISO 8601 dates (`YYYY-MM-DD`).
- Active voice, present tense in documentation.
- No emoji unless functional (e.g. status indicators). Stars (★) in score displays are functional.

## Secrets Management

This project uses SpockLock for secrets. See [`SPOCKLOCK.md`](./SPOCKLOCK.md) for how secrets are managed here — what to touch, what not to touch.
