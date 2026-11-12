# Deployment

## Environments

| Environment | Purpose | URL | Auth |
|-------------|---------|-----|------|
| Local | Development, full pipeline runs, site dev server | `http://localhost:5173` | None |
| Preview | Per pull request site build against the committed fixture bundle | <!-- TODO: host-provided preview URLs --> | None (public, unlisted) |
| Production | Published results | <!-- TODO: domain not chosen --> | None |

There is no staging pipeline environment. A release candidate is a tagged pre-release (`vX.Y.Z-rc.N`) published to the preview environment first.

## Build

| Artefact | Command | Reproducible? |
|----------|---------|---------------|
| Rust binary `vsm` | `cargo build --release --locked` | Yes, for a given toolchain. The toolchain is pinned in `rust-toolchain.toml` |
| Python stages | `uv sync --frozen` | Yes. `uv.lock` pins every dependency |
| Data bundle | `just pipeline` then `vsm publish` | **Yes. This is a project requirement (goal G1).** Bit-identical given the same spec hash, inputs, seeds, toolchain and lockfiles |
| Site | `npm ci && npm run build` in `site/` | Yes, given `package-lock.json` |

Top-level orchestration uses `just` (ADR-0009, Proposed):

```bash
just setup        # uv sync --frozen; cargo build --release --locked; (cd site && npm ci)
just ingest       # vsm-py ingest && vsm-py geography
just prefs        # vsm-py preferences
just pipeline     # vsm spec check; vsm districts; vsm run; vsm metrics --aggregate; vsm views; vsm check all
just publish      # vsm publish --out bundle/
just site         # build the static site against bundle/
just verify       # rebuild from scratch and compare with bundle/manifest.json
just test         # cargo test; uv run pytest; (cd site && npm test)
```

**Determinism rules** (ADR-0005):

- All randomness uses `rand_chacha` (Rust) or `numpy.random.Generator(PCG64)` (Python), seeded from `sha256(spec_hash ‖ component ‖ config_id ‖ index)`.
- No `HashMap` iteration order reaches outputs; ordered maps are used.
- Floating-point summaries are computed in a fixed order.
- JSON output uses sorted keys and fixed decimal rounding.

## Release process

1. **Methodology freeze** (once per spec version): `vsm spec freeze --version X.Y`. Commit `spec/FROZEN` and push a signed tag `spec-vX.Y` **before** any scoring run is published (principle P10).
2. **Full run** on the maintainer's machine: `just ingest prefs pipeline publish`.
3. **Health review**: read `reports/pipeline-{date}.md`. Zero invariant failures is a hard gate. Clamp, tie-break and calibration figures are reviewed.
4. **Release candidate**: tag `vX.Y.Z-rc.N`. `just verify` rebuilds the S0 matrix from a clean checkout and compares hashes (S1 cannot be rebuilt without BES data; the check covers everything downstream of the published `ballot_profile`). The site deploys to preview.
5. **Release**: a signed tag `vX.Y.Z`. A local release script attaches the release archive (bundle, `reference.sqlite`, `runs.sqlite`, open-licence raw data, logs, checksums) and deploys the site.
6. **Rollback**: redeploy the previous tag's site build. Published bundles are immutable; a wrong number is corrected by a new release with a changelog entry, never by editing files in place.

## Infrastructure

- **Compute**: the maintainer's M1 MacBook Pro (32 GB). Long S1 batches may run on the 2015 MacBook Pro server. No cloud compute is needed for the Commons profile (assumption A4).
- **CI**: none hosted (owner standing order). Local `just` targets and the pre-commit hook do the work.
- **Static hosting**: <!-- TODO: ADR-0010 (Proposed) — Cloudflare Pages or GitHub Pages. -->
- **Archive**: release assets on the repository host. <!-- TODO: optional Zenodo deposit for a citable DOI. -->

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VSM_SPEC_DIR` | no | `./spec` | Frozen methodology files |
| `VSM_DATA_DIR` | no | `./data` | Raw and reference data |
| `VSM_PRIVATE_DIR` | no | `./data/private` | Restricted BES files. Must be git-ignored |
| `VSM_REF_DB` | no | `./data/reference.sqlite` | |
| `VSM_RUNS_DB` | no | `./data/runs.sqlite` | |
| `VSM_THREADS` | no | number of logical CPUs | Rayon pool size. Does not affect results |
| `VSM_LOG` | no | `info` | `error`, `warn`, `info`, `debug` |
| `PUBLIC_DATA_BASE` | no | `/data/v1` | Site: bundle base path |

## Secrets handling

The pipeline needs no secrets. The deploy token is held by SpockLock on the maintainer's machine only. See [06_SECURITY.md](06_SECURITY.md).

## Backups and disaster recovery

- **Backup schedule**: The git repository is the backup for code and spec. Each tagged release's archive is the backup for data and results. `data/private/` is backed up only as the BES terms allow (the original files can be re-downloaded).
- **Restore procedure**: Clone, check out the tag, then run `just setup && just verify`. <!-- TODO: last-tested date, after the first release -->
- **Recovery Time Objective (RTO)**: Site: minutes (redeploy a tag). Pipeline: one full rebuild.
- **Recovery Point Objective (RPO)**: The last pushed commit. Local uncommitted spec edits are the only things at risk.

## Cost notes

Expected to be nearly zero: free-tier static hosting. The dominant cost is the maintainer's machine time for S1 runs. A custom domain, if wanted, is the only fixed cost. <!-- TODO: confirm once host and domain are chosen -->
