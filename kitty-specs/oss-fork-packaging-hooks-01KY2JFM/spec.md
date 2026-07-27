# OSS Fork Packaging Hooks

**Mission ID:** 01KY2JFMVQFA4Z4PHR5RDMMVCW  
**Mission slug:** oss-fork-packaging-hooks-01KY2JFM  
**Mission type:** software-dev  
**Status:** Proposed

## Purpose

Fork packagers who publish Spec Kitty under a different distribution name and/or a private PyPI-compatible simple index today must rewrite core source before `python -m build` so upgrade checks, version resolution, and remediation commands stay correct. Typical overlays replace session-presence upgrade checks, `version_utils`, compat provider/planner/remediation, the public-PyPI “no upgrade” notifier, and `--version` banner metadata.

This mission adds **entry-point plugins and a shared distribution profile** so those overlays become unnecessary. Stock Spec Kitty registers nothing; absence of hooks preserves today’s public-PyPI / `spec-kitty-cli` behaviour. Packager CI, private-registry credentials, and agent Docker workarounds stay packager-owned.

## Domain Language

| Canonical term | Meaning | Synonyms to avoid |
|---|---|---|
| packager hook | Install-time entry point that customizes fork identity or upgrade channel | “overlay”, “patch”, “monkeypatch” |
| distribution profile | Single packager-facing object describing package name, aliases, index URLs, freshness, and notifier flags | “config.yaml fork settings”, “runtime env package name” |
| upgrade provider | Zero-arg constructible object implementing `LatestVersionProvider.get_latest` without raising | “PyPI client”, “version fetcher” (ambiguous) |
| simple index | PEP 503 HTML simple repository API used by private indexes | “private PyPI” alone when the API surface is HTML simple |
| stock install | Unmodified `spec-kitty-cli` from public PyPI with no packager entry points | “upstream build”, “vanilla” |

## Functional Requirements

### Phase 1 — Package identity + pluggable upgrade source

| ID | Description | Status |
|---|---|---|
| FR-001 | The system resolves the CLI distribution package name via `resolve_cli_package_name()` in this order: (1) `spec_kitty.cli_package` entry point (string, callable, or object with `package_name` / `name`); (2) the distribution that owns the `specify_cli` import package via `packages_distributions`; (3) default `spec-kitty-cli`. | Proposed |
| FR-002 | The resolved CLI package name MUST NOT be controlled by a runtime environment variable that sets the distribution name. | Proposed |
| FR-003 | The system resolves a `LatestVersionProvider` from the `spec_kitty.upgrade_provider` entry-point group. Providers MUST be zero-arg constructible; `get_latest` MUST never raise. When no entry point is registered, the built-in public-PyPI provider is used. | Proposed |
| FR-004 | When multiple upgrade providers are registered, an optional `SPEC_KITTY_UPGRADE_PROVIDER=<name>` MAY select among them; it MUST NOT invent a provider that is not registered. | Proposed |
| FR-005 | Session-presence background upgrade refresh uses the resolved upgrade provider and the resolved CLI package name instead of hardcoding public PyPI / `spec-kitty-cli`. | Proposed |
| FR-006 | `version_utils.get_version()` resolves installed version using the resolved CLI package name (and later profile aliases when Phase 2 lands). | Proposed |
| FR-007 | The `--version` banner label uses the resolved package name (or profile `version_label` once Phase 2 lands) instead of a hardcoded `spec-kitty-cli` string. | Proposed |
| FR-008 | Operator-facing documentation describes how a packager registers `spec_kitty.cli_package` and `spec_kitty.upgrade_provider` without modifying core `specify_cli` sources. | Proposed |

### Phase 2 — Distribution profile (compat / remediation / notifier)

| ID | Description | Status |
|---|---|---|
| FR-009 | The system loads at most one packager-facing `DistributionProfile` from `spec_kitty.distribution_profile` (or derives an equivalent profile from Phase 1 entry points when only those are registered). Stock installs with no profile keep public-PyPI defaults. | Proposed |
| FR-010 | A `DistributionProfile` exposes at least: `package_name`, optional `package_aliases`, optional upgrade-provider linkage, optional `index_url` / `extra_index_url`, optional `data_freshness_seconds`, `disable_public_pypi_notifier`, and optional `version_label`. | Proposed |
| FR-011 | Compat planner default provider comes from the upgrade-provider resolver; latest-version queries use the resolved package name; installed-version lookup tries `package_name` then `package_aliases`. | Proposed |
| FR-012 | When `data_freshness_seconds` is set on the profile, `has_fresh_data` (or equivalent “should we re-query the index?” gate) uses that TTL. Display/nag throttle behaviour remains unchanged unless separately specified. | Proposed |
| FR-013 | Remediation and upgrade-hint command composition use the profile package name and, when set, append index URL / env arguments from the profile so private-index installs get correct pip/pipx/uv remediation strings. | Proposed |
| FR-014 | CHK028 (or successor allowlist length) is raised or computed so composed remediation commands that include index URLs remain valid (target allowlist length at least 512 characters, or dynamic length derived from composed argv). | Proposed |
| FR-015 | `maybe_emit_no_upgrade_notice` (public-PyPI “no upgrade path” notifier) is gated off when `disable_public_pypi_notifier` is true. | Proposed |
| FR-016 | Upstream ships a built-in `SimpleIndexProvider` that parses PEP 503 HTML simple-index responses. Forks MAY subclass or wrap it with a zero-arg `__init__` that sets their index URL and distribution filename prefix. Upstream defaults MUST NOT embed fork hostnames or private index URLs. | Proposed |
| FR-017 | Phase 1 entry-point groups remain valid thin aliases that feed the same resolver as the distribution profile (packagers who only need session-presence + name need not adopt the full profile). | Proposed |

### Phase 3 — Packager publish flow documentation

| ID | Description | Status |
|---|---|---|
| FR-018 | Documentation describes an end-state packager publish flow where packagers keep ownership of tag→version mapping, `pyproject.toml` name/version, private-index upload, and CI triggers. | Proposed |
| FR-019 | Documentation shows replacing core file overlays with either a thin vendored packager module plus entry points in `pyproject.toml`, or generated entry-point lines plus one provider module at publish time — without rewriting `src/specify_cli/**`. | Proposed |
| FR-020 | Documentation states explicitly which concerns remain packager-owned (CI webhooks, VCS tag filters, private-registry credentials, agent Docker workarounds, SaaS/E2E release gates) versus which belong in Spec Kitty upstream (runtime fork identity / upgrade channel hooks). | Proposed |

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|---|---|---|---|
| NFR-001 | Stock public-PyPI installs with no packager entry points behave identically to today’s hardcoded public-PyPI / `spec-kitty-cli` paths for upgrade check, version resolution, remediation package name, and version banner. | Zero behavioural drift on a stock install in regression tests covering those call sites | Proposed |
| NFR-002 | Upgrade provider `get_latest` failures never crash session-presence or compat planner hot paths. | Provider returns a failure result object; no exception escapes the provider boundary | Proposed |
| NFR-003 | Entry-point resolution is deterministic and cached for the process lifetime after first successful resolve (or equivalent once-per-process memo). | At most one importlib metadata scan per process for each resolver unless tests explicitly clear cache | Proposed |
| NFR-004 | New public APIs and modules pass project static gates. | Zero ruff issues and zero mypy issues on new/changed code; no blanket suppressions | Proposed |
| NFR-005 | Packager documentation is discoverable from the existing upgrade/install guide family within one click from an index or related guide. | Guide exists under `docs/guides/` and is linked from at least one existing upgrade/install doc | Proposed |

## Constraints

| ID | Description | Status |
|---|---|---|
| C-001 | Distribution package name MUST NOT be set via a runtime environment variable. Optional `SPEC_KITTY_UPGRADE_PROVIDER` is allowed only to disambiguate among **registered** providers. | Proposed |
| C-002 | Upstream stock defaults MUST NOT commit fork hostnames, private index URLs, or fork package names. | Proposed |
| C-003 | Success criterion for packagers: a renamed private-index fork can publish without modifying any file under `src/specify_cli/**` except an optional small packager-owned module co-shipped in the package plus `pyproject.toml` metadata/entry points. | Proposed |
| C-004 | Packager CI webhooks, VCS tag filters, private-registry credentials, agent-specific Docker/build workarounds, and SaaS/E2E release gates in GitHub Actions are out of scope for Spec Kitty upstream. | Proposed |
| C-005 | `.kittify/config.yaml` is not the control plane for these hooks; hooks are build-time / install-metadata entry points only. | Proposed |

## User Scenarios & Testing

### Scenario 1 — Stock install unchanged
An operator installs stock `spec-kitty-cli` from public PyPI with no packager entry points. Session-presence upgrade refresh, compat planner, remediation commands, and `--version` behave as they do today against public PyPI and `spec-kitty-cli`.

### Scenario 2 — Renamed public-index fork (Phase 1)
A packager publishes `acme-spec-kitty-cli` and registers `spec_kitty.cli_package` plus (optionally) keeps the default PyPI provider. `--version` and `get_version()` report the fork package; session-presence queries the fork package name on public PyPI.

### Scenario 3 — Private simple-index fork (Phases 1–2)
A packager registers a `SimpleIndexProvider` subclass (or profile with `upgrade_provider` + `index_url`) pointing at their private simple index. Session-presence and compat planner fetch latest versions from that index. Remediation strings include the index URL. The public-PyPI “no upgrade” notifier does not fire when `disable_public_pypi_notifier` is true.

### Scenario 4 — Editable / multi-name installs
A developer has an editable or transitional install where either the fork name or `spec-kitty-cli` may own the metadata. Version resolution tries `package_name` then `package_aliases` and returns the first found version.

### Scenario 5 — Multiple registered providers
Two upgrade providers are registered. Setting `SPEC_KITTY_UPGRADE_PROVIDER` to one registered name selects it. An unknown name does not invent a provider; resolution fails closed to a documented fallback (stock provider or error result — documented in plan).

### Scenario 6 — Packager publish without core overlays
A packager clones a release tag, sets `pyproject.toml` name/version, adds a thin `*_dist.py` module and entry points, runs `python -m build`, and uploads to a private index. No sed/cp overlays touch `session_presence/upgrade_check.py`, `version_utils.py`, `compat/provider.py`, `compat/planner.py`, `compat/remediation.py`, or `core/version_checker.py`.

### Scenario 7 — Freshness vs display throttle
A profile sets `data_freshness_seconds` to one hour. Index re-queries happen on that cadence while any longer display/nag throttle remains at its existing stock value.

## Success Criteria

1. A renamed private-index fork can publish without modifying any file under `src/specify_cli/**` except an optional small packager-owned module plus `pyproject.toml`.
2. Stock `spec-kitty-cli` on public PyPI is behaviourally unchanged when no entry points are registered (verified by regression tests).
3. Packager publish scripts need only metadata + optional entry-point injection — not core source overlays.
4. Phase 1 alone unblocks session-presence upgrade source, installed package name, and version banner for entry-point-registered forks.
5. Phase 2 alone removes the remaining overlay need for planner, remediation/hints, notifier, and data-freshness TTL.
6. Phase 3 documentation is sufficient for a packager who has never patched Spec Kitty core to adopt the hooks.

## Key Entities

| Entity | Description |
|---|---|
| `resolve_cli_package_name()` | Resolver for the installed CLI distribution name (entry point → owning dist → default). |
| `spec_kitty.cli_package` | Entry-point group for package identity. |
| `spec_kitty.upgrade_provider` | Entry-point group for `LatestVersionProvider` implementations. |
| `DistributionProfile` | Packager-facing profile aggregating name, aliases, provider, index URLs, freshness, notifier flag, version label. |
| `spec_kitty.distribution_profile` | Entry-point group loading the profile. |
| `SimpleIndexProvider` | Built-in PEP 503 HTML simple-index `LatestVersionProvider` for forks to subclass/wrap. |
| `LatestVersionProvider` | Existing protocol: `get_latest(package) -> LatestVersionResult`; must not raise. |

## Assumptions

1. Existing `LatestVersionProvider` / `PyPIProvider` / `LatestVersionResult` contracts in `compat/provider.py` remain the provider interface; this mission extends discovery and call-site wiring rather than inventing a second protocol.
2. Entry points are sufficient for both wheel installs and editable installs used by packagers during local verification.
3. Raising CHK028’s character limit (or computing it from argv) is acceptable for security posture because the allowlist character class stays restricted.
4. Phase 1 may land before Phase 2 without breaking stock installs; Phase 2 consumes Phase 1 resolvers.

## Out of Scope

- Packager CI webhooks, VCS tag filters, private-registry credentials
- Agent-specific Docker/build workarounds
- SaaS / E2E release gates in GitHub Actions
- Committing any fork hostnames or index URLs into stock defaults
- Changing `.kittify/config.yaml` into a fork packaging control plane
