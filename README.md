# Voting System Metrics

A reproducible, UK-grounded scoring engine and public results site that measures how candidate electoral systems would perform as a replacement for First Past the Post (FPTP) in UK General Elections.

Most comparisons of voting systems rely on editorial ratings: a few stars per system, with no published method. This project measures instead. It re-counts real UK election data under fully specified systems, including Single Transferable Vote (STV), the Additional Member System (AMS), list proportional representation, the Alternative Vote (AV), AV+ and Parallel. It then scores each one on ten axes and 26 sub-metrics, from proportionality and wasted votes to tactical-voting pressure, the constituency link and count integrity.

Every score shows a median, an uncertainty band and an evidence grade (observed in the UK, observed abroad, or modelled). The method is frozen and published before any system is scored. No overall winner is declared. Instead you can see which systems are never beaten on every axis, which pass a three-star floor everywhere, how the ranking changes under different priorities, and how often each system comes first across all possible weightings.

## Status

Design stage. The methodology is at draft v0.1, and no scores have been computed. See [`docs/11_ROADMAP.md`](docs/11_ROADMAP.md).

## Quick start

Requires Rust (stable, pinned in `rust-toolchain.toml`), Python 3.12+ with [`uv`](https://docs.astral.sh/uv/), Node.js, and [`just`](https://github.com/casey/just).

```bash
just setup
just pipeline && just publish
(cd site && npm run dev)
```

To check that published numbers are reproducible:

```bash
just verify
```

Rebuilding the sincere-preference scenario (S1) from scratch needs British Election Study (BES) data, which you must obtain yourself under the BES terms. Everything downstream of the published preference profiles rebuilds without it.

## How it works

A batch pipeline turns public data into scores:

1. Python stages ingest election results, electorates and boundaries, and rebuild sincere voter preferences from the BES.
2. Rust stages generate seeded multi-member district plans and count every configuration under every reference election and behavioural scenario.
3. The Rust stages then compute the metrics against fixed, pre-registered anchors.
4. Finally they build the published views.

The output is a versioned JSON bundle, which a static SvelteKit site renders as star tables, hemicycle seat charts and constituency hex maps. User re-weighting happens in your browser.

The full design is in [`docs/02_ARCHITECTURE.md`](docs/02_ARCHITECTURE.md). The measurement method is in [`research/new-metrics.md`](research/new-metrics.md).

## Documentation

Full design documentation is in [`docs/`](docs/). Start with [`docs/00_INDEX.md`](docs/00_INDEX.md).

For AI coding agents working in this repository, see [`AGENTS.md`](AGENTS.md). For Claude specifically, see [`CLAUDE.md`](CLAUDE.md).

## Contributing

Issues are welcome, especially:

- Reproducibility failures: a rebuild that does not match a published hash.
- Errors in a count rule or metric, with a reference.
- Methodology challenges, with evidence.

Changes to frozen methodology go through a versioned changelog, not ordinary pull requests. Contributors are asked to declare any campaign affiliation on methodology issues. <!-- TODO: contact route for the maintainer -->

## Licence

Code is licensed under either of [MIT](LICENSE-MIT) or [Apache-2.0](LICENSE-APACHE), at your option. Project-produced data (scores, bundles, `runs.sqlite`) is licensed under [CC BY 4.0](LICENSE-DATA). Upstream data keeps its own licence; see [`data/LICENCES.md`](data/LICENCES.md). Decision record: ADR-0012.

Unless you state otherwise, any contribution you intentionally submit for inclusion is dual licensed as above, without additional terms or conditions.

## Secrets Management

This project uses SpockLock for secrets. See [`SPOCKLOCK.md`](./SPOCKLOCK.md) for how secrets are managed here — what to touch, what not to touch.
