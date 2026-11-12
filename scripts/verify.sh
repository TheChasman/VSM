#!/usr/bin/env bash
# `just verify`: the release-candidate check (docs/09_TESTING.md, "Local checks").
# No hosted CI: this runs on the maintainer's machine.
#
#   1. Private-data scan: nothing under data/private/, and no BES-style or .sav/.dta file, is tracked.
#   2. Every local check (`just all`).
#   3. Clean rebuild: export HEAD to a scratch directory, rebuild reference.sqlite there from the
#      pinned sources (local copies of data/raw and data/private, checked against their SHA-256),
#      and compare its content digest with the working data/reference.sqlite.
#   4. Golden tests against the clean rebuild.
#
# Upgrade path (stages not built yet): S0 matrix rebuild against manifest.json, the runs.json size
# budget, the Lighthouse budget and Playwright smoke tests join here as those stages land.
set -euo pipefail
root="$(git rev-parse --show-toplevel)"
cd "${root}"

step() { printf '\n== %s\n' "$1"; }

step "private-data scan"
leaks="$(git ls-files | grep -E '^data/private/|\.(sav|dta)$|(^|/)BES[^/]*\.(csv|zip)$' || true)"
if [[ -n "${leaks}" ]]; then
  printf 'tracked private or BES-style files:\n%s\n' "${leaks}" >&2
  exit 1
fi
echo "clean"

step "local checks"
just all

step "clean rebuild of reference.sqlite"
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "note: uncommitted changes to tracked files are not in the clean rebuild (it uses HEAD)"
fi
scratch="$(mktemp -d "${TMPDIR:-/tmp}/vsm-verify.XXXXXX")"
trap 'rm -rf "${scratch}"' EXIT
git archive HEAD | tar -x -C "${scratch}"
# Inputs only: every file is re-checked against its pinned hash by ingest.
mkdir -p "${scratch}/data"
cp -R data/raw "${scratch}/data/raw"
[[ -d data/private ]] && cp -R data/private "${scratch}/data/private"
(
  cd "${scratch}"
  uv run -q --project py vsm-ingest run --data-dir data
  uv run -q --project py vsm-geography run --data-dir data
)
fresh="$(uv run -q --project py vsm-ingest digest "${scratch}/data/reference.sqlite")"
working="$(uv run -q --project py vsm-ingest digest data/reference.sqlite)"
echo "clean rebuild: ${fresh}"
echo "working copy:  ${working}"
if [[ "${fresh}" != "${working}" ]]; then
  echo "reference.sqlite differs from a clean rebuild of HEAD: run \`just ingest && just geography\`, or find the nondeterminism" >&2
  exit 1
fi

step "golden tests against the clean rebuild"
VSM_REFERENCE_DB="${scratch}/data/reference.sqlite" cargo test --workspace --quiet -- --ignored

step "verify passed (HEAD $(git rev-parse --short=7 HEAD), reference digest ${fresh:0:12})"
