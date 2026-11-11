# Security

Voting System Metrics (VSM) publishes static data with no user accounts, so classic access-control risks are small. The real assets are **credibility** (the scores must be demonstrably untampered and unbiased) and **licence compliance** (survey data must not leak). This file is written around those two assets.

## Threat model

| Adversary | Wants | Can reach | Main control |
|-----------|-------|-----------|--------------|
| Partisan critic (any side) | To discredit results as rigged towards a system | Public repository, site, bundle | Pre-registration hash, public code and data, one-command rebuild, published sensitivity analysis |
| Motivated misquoter | To publish a screenshot that misrepresents a score (for example, a grade C score shown as observed) | The site | Every chart is stamped with grade, band and spec version; there is no single "overall winner" to crop |
| Maintainer bias, including unintended | To tune anchors or weights after seeing results | `spec/` | Freeze before scoring. Any post-freeze change is versioned, logged and shows which scores moved (methodology §6.6). Campaign affiliations declared |
| Supply-chain attacker | To alter results through a compromised dependency | Package registries, CI | Lockfiles, `cargo audit`, `pip-audit`, `npm audit`, pinned CI actions, reproducibility check by an independent CI runner |
| Repository or host account takeover | To swap the bundle or site for doctored numbers | Repository and host accounts | Multi-factor authentication (MFA) on all accounts; tagged releases signed; manifest hashes published in the release notes, so a swapped bundle is detectable |
| Accidental leak by the maintainer | — | `data/private/` | Git-ignored path, a pre-commit hook that blocks BES file patterns, a CI check that scans the release archive |

Not considered credible enough to design for: denial of service against a static host (the host handles it), and theft of non-public data (none exists except BES files, covered above).

## Identity and authentication

- **Users**: None. The site is anonymous and read-only.
- **Services**: CI deploys to the static host with a scoped deploy token.
- **Tokens**: One deploy token, stored as a CI secret, limited to the site project. Rotated yearly or when a maintainer leaves.

## Authorisation

- Writes to `main` and tags: maintainer only, through protected branches.
- Changes to `spec/` after a freeze need an Architecture Decision Record (ADR) or methodology changelog entry in the same pull request. CI fails a pull request that changes frozen spec files without bumping `spec/FROZEN` and adding a changelog line.

## Secrets

| Secret | Storage | Rotation cadence | Accessed by |
|--------|---------|------------------|-------------|
| Static-host deploy token | CI secret store | Yearly | Deploy job only |
| Release-signing key | <!-- TODO: GPG or SSH signing key location; the maintainer may keep it in SpockLock --> | On compromise | Maintainer |
| BES download credentials | Not stored. Downloads are manual after registration | n/a | Maintainer |

No secret is needed to run the pipeline or build the site.

## Data classification

| Tier | Data | Handling |
|------|------|----------|
| Public, open licence | UK Parliament election results (Open Parliament Licence), Commons Library results, Office for National Statistics (ONS) electorates, Ordnance Survey (OS) Boundary-Line, Senedd results (Open Government Licence (OGL)) | Republished with attribution in the release archive |
| Public, other licence | Scottish council ballot collections, hex layouts, Chapel Hill Expert Survey (CHES) and BES expert-survey party positions | Republished only if the licence allows; otherwise fetched at build time. <!-- TODO: confirm each licence --> |
| **Restricted** | British Election Study (BES) respondent-level panel data | **Personal data under UK GDPR, although pseudonymised.** Kept only in `data/private/`. Never committed, never in a release, never in logs. Used only under the BES terms of use |
| Derived aggregate | `ballot_profile` (weighted rankings per constituency and draw) | Published, **subject to confirming** that the BES terms permit derived aggregates (open question Q-S1). Small-cell rule: no ranking row whose weight rests on fewer than <!-- TODO: minimum respondents --> respondents is published; such rows are pooled |

Retention of restricted data follows the BES terms. See [03_DATA_MODEL.md](03_DATA_MODEL.md).

## Transport and at-rest encryption

- The site is served over HTTPS only (the host's certificate), with HTTP Strict Transport Security (HSTS) enabled.
- `data/private/` sits on the maintainer's FileVault-encrypted disk. It is not synced to cloud storage.
- Release artefacts carry SHA-256 checksums and are signed.

## Audit

- Git history and signed tags are the audit trail for code and spec.
- `manifest.json` records every input hash, the spec hash, the engine version and the commit for each published bundle.
- The methodology changelog lists every post-freeze change and the scores it moved.
- Content Security Policy (CSP) on the site is strict: no third-party scripts, and `connect-src 'self'`.

## Known residual risks

- **Synthetic S1 ballots** are a methodological weakness rather than a security one, but they are the likeliest target of "rigged" accusations. Accepted. Mitigated by publishing the calibration report and showing S0 and S1 side by side.
- **Reproducibility of S1 depends on BES access.** Anyone without BES registration can reproduce everything downstream of `ballot_profile`, but not the profiles themselves. Accepted, if Q-S1 confirms that aggregates are publishable.
- **Single maintainer.** One person controls the spec, code and release keys. Mitigated by declared affiliations, freeze-before-score, and inviting third-party rebuilds. A second reviewer for spec changes would be better; deferred.
