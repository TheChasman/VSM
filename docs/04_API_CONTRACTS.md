# API Contracts

Voting System Metrics (VSM) has no network API. Its contracts are of three kinds:

1. the **command-line interface (CLI)** that runs the pipeline,
2. the **spec-file schemas** that the frozen methodology must satisfy, and
3. the **published data bundle**: the JSON that the static site and any third party consume.

The bundle is the public contract. The CLI and spec files are contracts for contributors.

## Conventions

- **Transport**: Local files. The bundle is served over HTTPS as static JSON.
- **Authentication**: None. Everything published is public.
- **Versioning**: The bundle carries `bundle_schema` (Semantic Versioning (SemVer)) and `spec_version`. Breaking schema changes bump the major version and move to a new path: `/data/v{major}/…`.
- **Encoding**: UTF-8 JSON, numbers as JSON numbers. Scores are rounded to one decimal place in the bundle and kept at full precision in `runs.sqlite`.
- **Error model (CLI)**: Exit code 0 on success, 1 on a pipeline error, 2 on an invariant violation, 3 on a spec-hash mismatch, 64 on bad usage. Errors are printed to stderr as one JSON line: `{"level":"error","code":"…","msg":"…","context":{…}}`.
- **Idempotency**: Every stage is idempotent for a given spec hash and input hash. A re-run skips runs whose `run_id` already exists with status `ok`, unless `--force` is given.

## Command-line interface

The Rust binary is `vsm`. Python stages are invoked as `vsm-py <stage>` (a console script installed by `uv`). The two are orchestrated with `just` recipes ([08_DEPLOYMENT.md](08_DEPLOYMENT.md)).

| Command | Purpose | Reads | Writes |
|---------|---------|-------|--------|
| `vsm-py ingest [--only SOURCE]` | Download, verify checksums, normalise | `data/sources.toml` | `data/raw/`, `reference.sqlite` |
| `vsm-py geography` | Areas, adjacency, local-authority overlap | Boundary files | `reference.sqlite` |
| `vsm-py preferences [--draws N]` | S1 ballot profiles through MRP and calibration | BES (private), results, `spec/scenarios.toml` | `ballot_profile` |
| `vsm spec check` | Validate spec TOML against the schema | `spec/` | — |
| `vsm spec freeze --version X.Y` | Canonicalise, hash, write `spec/FROZEN` | `spec/` | `spec/FROZEN` |
| `vsm districts --config C04 [--plans 20]` | Generate seeded plans | reference, spec | `district_plan` |
| `vsm run --profile commons [--config …] [--election …] [--scenario …]` | Expand and count the run matrix | reference, plans, spec | `run`, `seat_outcome`, `count_log` |
| `vsm metrics [--aggregate]` | Sub-metrics per run, then summaries | runs, reference, spec | `submetric_value`, `score_summary` |
| `vsm views --profile commons` | Pareto, Punter, Fair Fight, weight profiles, sensitivity, correlation audit | summaries, spec | `view_result` |
| `vsm publish --out bundle/` | Export the site bundle and manifest | all | `bundle/` |
| `vsm check [refs|invariants|all]` | Invariant suite | all | — |
| `vsm verify --manifest bundle/manifest.json` | Rebuild and compare hashes | all | report |

Plain-text output is the default. Every command also accepts `--json` for machine-readable output.

## Spec-file schemas

Schemas live in `spec/schema/*.json` (JSON Schema, draft 2020-12) and are applied to the TOML after parsing. Representative shapes:

```toml
# spec/configurations.toml
[[configuration]]
id = "C06"
label = "AMS, Holyrood ratio, regional D'Hondt, closed lists"
family = "AMS"
office = "commons"
compensatory = true
tier_ratio = [57, 43]
formula = "dhondt"
list_type = "closed"
threshold = { pct = 0.0, level = "region" }
preferences = 1
transfer_rule = "na"
votes_per_ballot = 1
districting = { list_regions = "nuts1_and_nations" }   # TODO: confirm the region set for the Commons
```

```toml
# spec/anchors.toml
[P1]
function = "lin"        # lin(x; a, b): x = a scores 100, x = b scores 0
best = 0.0
worst = 25.0
rationale = "Just above the highest post-war UK value (about 24, in 2024)"
```

```toml
# spec/weights.toml
[profile.jenkins_1998]
label = "Jenkins 1998"
weights = { P = 25, E = 0, W = 0, X = 12.5, S = 0, C = 12.5, G = 25, F = 12.5, A = 12.5, I = 0 }
rationale = { P = "Broad proportionality term of reference", G = "MP–constituency link term of reference" }
```

`vsm spec check` rejects a spec in which any of the following hold: the weights do not sum to 100; a scored sub-metric has no anchor; a configuration parameter is missing (as opposed to explicitly `null`); or a `criteria.toml` cell is `unresolved` for a configuration in a profile being frozen.

## Published data bundle

Root: `/data/v1/`. All files are static.

### `GET /data/v1/manifest.json`

- **Purpose**: Provenance for everything in the bundle.
- **Idempotent**: yes

```json
{
  "bundle_schema": "1.0.0",
  "spec_version": "1.0",
  "spec_hash": "sha256:…",
  "engine_version": "0.1.0",
  "git_commit": "…",
  "generated": "2026-11-11",
  "inputs": [{ "source_id": "cl_ge2024", "sha256": "…", "licence": "OGL-3.0" }],
  "preference_model_version": "…",
  "files": [{ "path": "commons/scores.json", "sha256": "…" }]
}
```

### `GET /data/v1/{profile}/scores.json`

- **Purpose**: Summary scores per configuration, axis and sub-metric.

```json
{
  "profile": "commons",
  "configurations": [{
    "id": "C04",
    "label": "STV, 3–5 member districts",
    "axes": {
      "P": { "median": 82.1, "p10": 76.4, "p90": 87.0, "grade": "C", "stars": 5,
             "submetrics": { "P1": { "median": 85.0, "p10": 80.2, "p90": 89.1, "grade": "C" } } },
      "G": { "…": "…" }
    },
    "reported": { "F2_ENPP": { "median": 3.9, "p10": 3.4, "p90": 4.5 } }
  }]
}
```

(The values above are illustrative of the shape only. No scores have been computed.)

N/A axes are **omitted** from `axes` and listed in `"not_applicable": ["…"]`. They are never sent as zero.

### `GET /data/v1/{profile}/runs.json`

- **Purpose**: Per-run axis scores, so the browser can apply user-chosen weights and compute a weighted median and band per run (methodology: the weighted score is computed per run, then summarised).

```json
{ "axes": ["P","E","W","X","S","C","G","F","A","I"],
  "runs": [{ "config": "C04", "election": "GE2024", "scenario": "S1", "plan": 7, "draw": 3,
             "scores": [82.0, 71.5, 90.2, 100.0, 48.0, 63.0, 55.1, 92.0, 61.0, 70.0] }] }
```

### `GET /data/v1/{profile}/views.json`

- **Purpose**: Pre-computed views: `pareto`, `punter.axis`, `punter.cluster` (each with `basic` and `confident` floors), `fair_fight`, `profile_ranks` (configuration × weight profile), `sensitivity` (share of sampled weightings in which each configuration ranks first, with the sampling method and sample count), and `correlation_audit`.

### `GET /data/v1/{profile}/seats/{config}.json` and `GET /data/v1/geo/hex.json`

- **Purpose**: Hemicycle data (for each seat position, its party and its frequency across runs) and hex-map data (per constituency: contestability frequency and the representative party distribution).

### Errors

Static files only, so the site handles a missing file (HTTP 404) by showing "data not yet published for this profile". It never falls back to stale numbers without saying so.

## Webhooks and outbound events

None.

## Rate limits

None imposed by VSM. Static hosting limits apply. <!-- TODO: note the host's limits once ADR-0010 is decided. -->

## Backwards compatibility

- **Non-breaking** changes (minor version): new optional fields, new views, new profiles.
- **Breaking** changes (major version): renamed or removed fields, changed units or score semantics. The previous major path stays online for at least one further major release.
- **A spec change is not a schema change.** A new `spec_version` publishes under the same bundle schema. The site shows the methodology changelog stating which scores moved (methodology §6.6).
- Published bundles are immutable. A correction is a new release, never an in-place edit.
