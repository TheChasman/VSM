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
