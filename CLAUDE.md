# CLAUDE.md

Claude-specific guidance for this project. Universal agent instructions live in [AGENTS.md](AGENTS.md). Read that first: the rules below are additions, not replacements.

## Project shorthand

- **Name**: Voting System Metrics (VSM)
- **Stack**: Rust, Python (`uv`), SQLite, SvelteKit static site
- **Specs entry point**: [`docs/00_INDEX.md`](docs/00_INDEX.md)
- **Methodology entry point**: [`research/new-metrics.md`](research/new-metrics.md), plus its addenda `weight-profiles.md`, `international-evidence.md` and `additional-research.md`

## Working style

<!-- TODO: the maintainer to confirm or replace. Drafted from known preferences: -->

- UK English throughout. Introduce abbreviations in brackets at first use.
- Choose the best tool for the problem and let each proposal justify itself against alternatives. The stack preference (Rust, Svelte, SQLite) is a default, not a rule.
- Do not treat popularity as evidence of merit when recommending libraries or methods.
- Keep documents in manageable pieces. Do not produce single files of 1,000+ lines.

## Project-specific context Claude tends to need

- **The project exists to be neutral.** It replaces the Electoral Reform Society (ERS) star ratings, which favour the system the ERS campaigns for. Never write copy, defaults or examples that favour a voting system. No "overall winner" is published by default (principle P8).
- **Primary target is the Commons profile** (C01–C11). Devolved, council and executive profiles are mainly evidence that raises Commons grades.
- **Evidence grades matter as much as scores.** A, B, B-int, C. Stars are always shown with the grade.
- **S0 is a lower bound.** Static re-runs carry First Past the Post (FPTP) tactical voting into the baseline. Say so wherever S0 results appear.
- **The research documents also live in a claude.ai Project** ("PROJ: Voting System Metrics"). Keep `research/` in the repository in sync with it; the Project copy is the working draft until the spec is frozen.
- Machines: the M1 MacBook Pro ("Kirk") is the daily driver and runs the pipeline; the 2015 MacBook Pro ("SpocksPad") is the lid-down server, available for long S1 batches.

## Tools and integrations on this project

<!-- TODO: list MCP servers and CLIs used when working on this repository (for example the Svelte MCP server for SvelteKit documentation, context7 for library docs). -->

## Things Claude has got wrong before

Errors corrected during research, worth not repeating:

- Scottish council Single Transferable Vote (STV) wards are **not** "3–4 members". The 2022 pattern is 355 wards of 1–5 members.
- Wrong-winner reference cases are **1929**, 1951 and February 1974, not only the last two.
- Senedd 2026 is **not** modelled: the election took place on 2026-05-07 (16 six-member districts, closed lists, D'Hondt), so C09 is grade A for the devolved profile.
- Mayors and Police and Crime Commissioners (PCCs) changed system twice: Supplementary Vote (SV) to 2021, FPTP 2024–2026, SV restored from 2027. Do not describe either as "the" current system without a date.
- Binary criteria compliance (sub-metric S1) rewards count rules that ignore most of the ballot. Do not present S1 alone as "tactical-voting resistance"; S2 is the main measure.

## Secrets Management

This project uses SpockLock for secrets. See [`SPOCKLOCK.md`](./SPOCKLOCK.md) for how secrets are managed here — what to touch, what not to touch.

<!-- spocklock-rules-import:start (managed by the SpockLock global pre-commit hook) -->
@~/Projects/MyMCPs/MCP-SpockLock/docs/SPOCKLOCK-RULES.md
<!-- spocklock-rules-import:end -->
