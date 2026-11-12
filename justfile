# Local checks for Voting System Metrics (VSM). No hosted CI: run these yourself.

default: check

fmt:
    cargo fmt --all

lint:
    cargo fmt --all --check
    cargo clippy --workspace --all-targets -- -D warnings

test:
    cargo test --workspace

check: lint test

# Install the pre-commit hook into this clone (shared by all worktrees).
# The hook runs the global SpockLock hook first, so secret scanning still applies.
hooks:
    git config core.hooksPath scripts/hooks

# Python stages
py-lint:
    cd py && uv run ruff format --check . && uv run ruff check .

py-test:
    cd py && uv run pytest -q

# Fetch, verify and load every source into data/reference.sqlite.
ingest:
    uv run --project py vsm-ingest run --data-dir data

# Areas and contiguity graph (needs `just ingest`).
geography:
    uv run --project py vsm-geography run --data-dir data

# Golden tests against real results (needs `just ingest`).
golden:
    cargo test --workspace -- --ignored

all: check py-lint py-test

# Release-candidate check: private-data scan, all checks, clean rebuild compared by digest,
# golden tests on the rebuild. Slow (rebuilds reference.sqlite).
verify:
    scripts/verify.sh

# Dependency advisories (cargo audit, pip-audit). Run at least monthly.
audit:
    scripts/audit.sh
