# Voting System Metrics — Specification Index

This directory holds the Detailed Design Document (DDD) suite for Voting System Metrics (VSM). Read in numbered order for the full picture; jump to a specific file if you know what you need.

The DDD suite specifies the **software**. The **metric methodology** it implements (axes, sub-metrics, anchors, weight profiles, evidence grades) lives in the research documents under [`research/`](../research/), with `research/new-metrics.md` as the methodology specification. Where the two disagree, the methodology wins and the DDD is corrected.

| #  | File                                          | What it covers                                                      |
|----|-----------------------------------------------|---------------------------------------------------------------------|
| 00 | This file                                     | Index and reading order                                             |
| 01 | [Overview](01_OVERVIEW.md)                    | What, why, non-goals, glossary                                      |
| 02 | [Architecture](02_ARCHITECTURE.md)            | Pipeline stages, data flow, trust boundaries                        |
| 03 | [Data Model](03_DATA_MODEL.md)                | SQLite run store, frozen spec files, entities                       |
| 04 | [API Contracts](04_API_CONTRACTS.md)          | Command-line interface, spec-file schemas, published data bundle    |
| 05 | [Components](05_COMPONENTS.md)                | Per-stage detailed specs                                            |
| 06 | [Security](06_SECURITY.md)                    | Integrity, data licensing, survey-data handling                     |
| 07 | [Observability](07_OBSERVABILITY.md)          | Run manifests, invariant checks, logging                            |
| 08 | [Deployment](08_DEPLOYMENT.md)                | Build, release, static hosting                                      |
| 09 | [Testing](09_TESTING.md)                      | Golden counts, property tests, determinism                          |
| 10 | [Decisions](10_DECISIONS.md)                  | Architecture Decision Records (ADRs)                                |
| 11 | [Roadmap](11_ROADMAP.md)                      | Phases, milestones, open questions                                  |

Sibling context files (not part of the numbered suite):

- [AGENTS.md](../AGENTS.md) — universal AI agent guidance
- [CLAUDE.md](../CLAUDE.md) — Claude-specific project context
- [README.md](../README.md) — public-facing repository readme

## Methodology documents (inputs to this suite)

| File | Role |
|------|------|
| `research/voting-systems.md` | Electoral Reform Society (ERS) system descriptions and star scores — the baseline being replaced |
| `research/scoring-details.md` | How the ERS scores (it publishes no rubric) |
| `research/ers-critique.md` | Diagnosis of the ERS scores and the proposed ten-axis set |
| `research/new-metrics.md` | **Methodology specification v0.1** — axes, sub-metrics, anchors, configurations C01–C20 |
| `research/additional-research.md` | S1 criteria table, fact checks, data scoping, recommended v0.2 changes |
| `research/weight-profiles.md` | Star bands, Punter view, weight profiles, Fair Fight view, decisions of 2026-11-11 |
| `research/international-evidence.md` | B-int evidence grade, backward re-counts, AV+ proxy pipeline, arc and map display |

## Status

- Last revised: 2026-11-11
- Owner: Chas Newport (NRTFM Ltd)
- Stack: Rust (counting, simulation, metrics), Python (data ingest, preference modelling), SQLite (run store), SvelteKit static site
- Phase: design. No code exists yet. Methodology at v0.1 with v0.2 changes pending (see [11_ROADMAP.md](11_ROADMAP.md)).

## Conventions used throughout

- UK English
- Abbreviations introduced with brackets at first occurrence in each file: "Detailed Design Document (DDD)"
- Dates in ISO 8601 (`YYYY-MM-DD`)
- ADRs are append-only; supersede rather than rewrite
- Configuration IDs (C01–C20), axis letters (P, E, W, X, S, C, G, F, A, I) and sub-metric IDs (P1, E3, S2 …) are those of `research/new-metrics.md` and are never renumbered
