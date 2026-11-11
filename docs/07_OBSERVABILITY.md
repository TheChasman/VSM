# Observability

Voting System Metrics (VSM) is a batch pipeline plus a static site, so observability here means three things: knowing exactly what produced a published number, catching wrong numbers before they ship, and seeing where run time goes. There is no on-call rotation.

## Logging

- **Format**: JSON Lines (JSONL). Rust uses `tracing` with `tracing-subscriber`'s JSON layer; Python uses the standard `logging` module with a JSON formatter. Common fields are `ts`, `level`, `stage`, `run_id`, `config_id`, `msg`.
- **Sink**: `logs/{stage}-{yyyymmdd-hhmmss}.jsonl`, plus human-readable stderr. Logs are not shipped anywhere.
- **Retention**: Kept locally. The logs from each tagged release's full rebuild are attached to that release.
- **Sampling**: None. Per-run debug logs are off by default (`VSM_LOG=debug` turns them on).
- **Correlation ID propagation**: `run_id` is the correlation ID from `runs` through `metrics`. `spec_hash` and `model_version` appear in the first log line of every stage.
- **Never logged**: Respondent-level British Election Study (BES) fields. The preferences stage logs counts and fit statistics only.

## Metrics

Collected per pipeline invocation into `reports/pipeline-{date}.json`. There is no time-series database.

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `runs_total` | counter | profile, config, scenario, status | Completeness: a configuration aggregates only when all its runs are `ok` |
| `run_duration_seconds` | histogram | config, scenario | Finds slow configurations (S2 for STV is the expected hot spot) |
| `stage_duration_seconds` | gauge | stage | End-to-end time budget |
| `anchor_clamps_total` | counter | submetric | How often raw values fall outside anchors; feeds the anchor sensitivity check |
| `invariant_failures_total` | counter | invariant | Must be zero to publish |
| `tie_breaks_total` | counter | config, rule, kind | How often seeded lots decided a seat; reported in the method notes |
| `pref_tie_share` | gauge | wave set | Share of BES respondents with tied top parties |
| `calibration_error` | gauge | target (exhaustion, transfer) | Preference-model fit against observed ballots |
| `district_plan_retries` | histogram | config, nation | Generator health; a rise flags a near-infeasible constraint |
| `bundle_bytes` | gauge | file | Site performance budget |

## Tracing

Not used. Stages are coarse and sequential, and `tracing` spans with timing in the JSONL logs are enough.

## Service Level Objectives (SLOs)

| SLO | Target | Measurement window |
|-----|--------|--------------------|
| Reproducibility: rebuild from a tagged release matches every `manifest.json` file hash | 100 % | Every release, and monthly on the latest release |
| Invariant suite passes before publish | 100 % | Every publish |
| Full Commons rebuild (S0 and S1) on the maintainer's M1 MacBook Pro | <!-- TODO: set after the first full run --> | Per release |
| Site Largest Contentful Paint (LCP) on a mid-range phone | Under 2.5 s | Per release (Lighthouse in CI) |

## Alerts

| Alert | Condition | Severity | Runbook |
|-------|-----------|----------|---------|
| Reproducibility drift | Monthly CI rebuild hash ≠ published hash | High | Bisect between the release commit and the rebuild environment; check toolchain and lockfile drift first. Publish a notice if a published number is affected |
| Source changed upstream | `ingest` checksum mismatch | Medium | Do not overwrite. Diff the files, decide whether to adopt, record a new source version |
| Dependency advisory | `cargo audit`, `pip-audit` or `npm audit` finding | Medium | Patch, rebuild, check the hashes are unchanged |

Alerts are delivered as CI failure notifications. There is no paging.

## Dashboards

- **`reports/pipeline-{date}.md`**: rendered from the metrics JSON after each full run (run counts, durations, clamps, tie-breaks, calibration error). Its purpose is to answer "is this run fit to publish?".
- **Method page on the site**: public extracts of clamp counts, tie-break counts, calibration error and the correlation audit, so readers see the same health signals as the maintainer.

## On-call

Not applicable. Single maintainer, no live service.
