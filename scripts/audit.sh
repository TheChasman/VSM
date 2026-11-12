#!/usr/bin/env bash
# `just audit`: dependency advisories. Run by hand at least monthly (docs/09_TESTING.md).
# Upgrade path: `npm audit` for site/ once the site exists; the monthly rebuild of the latest
# release (reproducibility drift) joins once releases are tagged.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

printf '== cargo audit\n'
cargo audit

printf '\n== pip-audit (py/uv.lock)\n'
reqs="$(mktemp "${TMPDIR:-/tmp}/vsm-audit.XXXXXX")"
trap 'rm -f "${reqs}"' EXIT
(cd py && uv export -q --frozen --no-emit-project --format requirements-txt -o "${reqs}")
uv tool run -q pip-audit --disable-pip --require-hashes -r "${reqs}"

if [[ -d site ]]; then
  printf '\n== npm audit\n'
  (cd site && npm audit)
fi
