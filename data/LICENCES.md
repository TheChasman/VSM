# Data licences

Voting System Metrics (VSM) uses three licensing layers (ADR-0012 in [`docs/10_DECISIONS.md`](../docs/10_DECISIONS.md)).

| Layer | Licence | File |
|---|---|---|
| Code | `MIT OR Apache-2.0`, at your option | [`LICENSE-MIT`](../LICENSE-MIT), [`LICENSE-APACHE`](../LICENSE-APACHE) |
| Project-produced data (scores, bundles, `runs.sqlite`) | Creative Commons Attribution 4.0 International (CC BY 4.0) | [`LICENSE-DATA`](../LICENSE-DATA) |
| Redistributed upstream data | The upstream licence, with its attribution | This file, per source |

British Election Study (BES) respondent-level data is never redistributed. BES-derived aggregates are published only within the BES terms (ADR-0013, open question Q-S1).

## Upstream sources

Each source in `data/sources.toml` needs an entry here before its files ship in a release archive.

| Source | Licence | Attribution | Redistributed |
|---|---|---|---|
| UK Parliament election results (electionresults.parliament.uk): GE2024 and notional GE2019 | Open Parliament Licence v3.0 (OPL) | Contains Parliamentary information licensed under the Open Parliament Licence v3.0 | Yes |
| Office for National Statistics (ONS) electorate statistics | OGL v3.0 | <!-- TODO --> | Yes |
| ONS Westminster Parliamentary Constituencies (July 2024) Boundaries UK BFC | OGL v3.0 | Source: Office for National Statistics licensed under the Open Government Licence v3.0. Contains OS data © Crown copyright and database right 2024 | Yes |
| Ordnance Survey (OS) Boundary-Line | OGL v3.0 | <!-- TODO: OS copyright and database right statement --> | Yes (not yet used) |
| Senedd Research, "Senedd election 2026: Research Briefing" (Senedd 2026 results) | Copyright Welsh Parliament 2026; reuse terms not confirmed | <!-- TODO: confirm reuse terms with Senedd Research --> | **No**, until terms are confirmed (kept in `data/private/`) |
| ONS Senedd Cymru Constituencies (May 2026) Names and Codes | OGL v3.0 | Source: Office for National Statistics licensed under the Open Government Licence v3.0 | Yes |
| Scottish council ballot collections | <!-- TODO: confirm --> | <!-- TODO --> | Only if the licence allows |
| 2024 constituency hex layout | <!-- TODO: confirm (Q-H2) --> | <!-- TODO --> | Only if the licence allows |
| Chapel Hill Expert Survey (CHES) | <!-- TODO: confirm --> | <!-- TODO --> | Only if the licence allows |
| BES respondent-level panel | BES terms of use | n/a | **Never** |
