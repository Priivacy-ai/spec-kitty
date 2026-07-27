# Implementation Plan: OSS Fork Packaging Hooks

**Branch**: `feat/oss-fork-packaging-hooks` | **Date**: 2026-07-21 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `kitty-specs/oss-fork-packaging-hooks-01KY2JFM/spec.md`  
**Mission ID**: `01KY2JFMVQFA4Z4PHR5RDMMVCW`

## Summary

Add install-time packager hooks so renamed / private-index forks can customize CLI package identity, upgrade-source providers, remediation index URLs, notifier gating, and version-banner labels **without rewriting** `src/specify_cli/**` at publish time.

Approach: shared resolvers backed by `importlib.metadata` entry points, a single `DistributionProfile` aggregating packager knobs, a built-in `SimpleIndexProvider` (PEP 503 HTML), and call-site wiring across session-presence, `version_utils`, compat planner/remediation/hints, and the public-PyPI notifier. Stock installs with no entry points keep today’s public-PyPI / `spec-kitty-cli` behaviour.

Related WIP in mission `pluggable-upgrade-check-provider-01KXZDMC` already prototypes `resolve_upgrade_provider` under `session_presence/` — this mission **supersedes** that narrower scope by lifting resolvers into a shared distribution module and covering identity + profile + docs.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: importlib.metadata (stdlib entry points + packages_distributions), existing `specify_cli.compat.provider.LatestVersionProvider` / `PyPIProvider` / `LatestVersionResult`, httpx (existing; SimpleIndexProvider HTML fetch), packaging (existing where version parsing already used)  
**Storage**: N/A for profile itself (install metadata only). Existing `~/.kittify/last-cli-check.json` cache retained for session-presence.  
**Testing**: pytest; unit tests for resolvers with fake entry-point injection; stock-path regression tests proving no behavioural drift; SimpleIndexProvider HTML fixtures; remediation argv composition tests including index URL + CHK028 length  
**Target Platform**: Linux, macOS, Windows 10+ (CLI package)  
**Project Type**: Single Python package (`specify_cli`)  
**Performance Goals**: Resolver memoized once per process; provider `get_latest` never raises; session-presence hot path remains background-refresh only  
**Constraints**: No runtime env var for distribution **name**; `SPEC_KITTY_UPGRADE_PROVIDER` only disambiguates registered providers; no fork hostnames/URLs in stock defaults; no `.kittify/config.yaml` control plane for these hooks; complexity ≤15 on new functions  
**Scale/Scope**: Three phases — identity+provider wiring, distribution profile+compat surfaces, packager documentation; ~8–12 call sites; one new shared module family; one new guide

## Charter Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Directive | Status | Note |
|---|---|---|
| DIR-001 Cross-platform | ✅ Compliant | Stdlib metadata + httpx; no OS-specific paths in hooks |
| DIR-002 Python 3.11+ | ✅ Compliant | `importlib.metadata.entry_points(group=...)`, dataclasses, Protocol |
| DIR-004 PyPI distribution | ✅ Compliant | Hooks are the extensibility surface for fork publishes; stock PyPI unchanged |
| DIR-005 Tests added | ✅ Required | Resolver, provider, planner/remediation wiring, stock regression |
| DIR-006 Type annotations | ✅ Required | mypy --strict on new modules |
| DIR-007 Docstrings | ✅ Required | Public resolvers, profile, SimpleIndexProvider |
| DIR-008 No security issues | ✅ Compliant | CHK011–016 style TLS/size/redirect rules for SimpleIndexProvider; CHK028 character class retained (length raised) |
| DIR-009 Breaking changes | ✅ N/A for stock | Additive entry points; stock path unchanged |
| C-007 `__all__` | ⚠️ Required | New modules declare `__all__` |
| C-011 ATDD-first | ⚠️ Required | Failing tests for stock vs forked entry-point behaviour before wiring |

*Post-Phase-1 re-check: No new charter conflicts. Prior sibling mission WIP is documentation-only conflict risk — absorb or abandon that branch; do not leave two parallel upgrade_provider homes.*

## Project Structure

### Documentation (this mission)

```
kitty-specs/oss-fork-packaging-hooks-01KY2JFM/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── entry-points.md
│   ├── distribution-profile.md
│   └── simple-index-provider.md
└── tasks.md                 # produced by /spec-kitty.tasks
```

### Source Code (repository root)

```
src/specify_cli/
├── distribution/                      # NEW shared package
│   ├── __init__.py
│   ├── package_name.py                # resolve_cli_package_name()
│   ├── upgrade_provider.py            # resolve_upgrade_provider()
│   ├── profile.py                     # DistributionProfile + resolve_distribution_profile()
│   └── simple_index.py                # SimpleIndexProvider
├── session_presence/
│   ├── upgrade_check.py               # consume resolved provider + package name
│   └── _upgrade_refresh.py            # same
├── version_utils.py                   # aliases-aware get_version()
├── __init__.py                        # --version banner label
├── core/version_checker.py            # gate maybe_emit_no_upgrade_notice
└── compat/
    ├── provider.py                    # export SimpleIndexProvider if co-located preferred; else re-export
    ├── planner.py                     # provider + package + freshness TTL
    ├── remediation.py                 # package name + index argv + CHK028
    └── upgrade_hint.py                # CHK028 length alignment

docs/guides/
└── fork-packaging-hooks.md            # Phase 3 packager publish flow
docs/guides/upgrade-cli.md             # link to new guide (one click)

tests/
├── specify_cli/distribution/
│   ├── test_package_name.py
│   ├── test_upgrade_provider.py
│   ├── test_profile.py
│   └── test_simple_index.py
├── specify_cli/session_presence/test_upgrade_refresh.py  # extend
├── specify_cli/compat/                                   # planner/remediation wiring tests
└── core/test_resolve_cli_package_name.py                 # if preferred location for name resolver
```

**Structure Decision**: New `specify_cli.distribution` package owns all resolvers and the profile. Session-presence keeps refresh orchestration but must not own the only copy of `resolve_upgrade_provider` (avoids duplicating the sibling WIP layout). Compat continues to own the `LatestVersionProvider` protocol; `SimpleIndexProvider` may live in `distribution/simple_index.py` and be re-exported from `compat` for discoverability.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New `distribution/` package vs stuffing into `session_presence/` | Profile + remediation + version_utils all need the same resolvers | Session-presence-only home recreates the sibling WIP footgun and forces compat to import session_presence |
| Three entry-point groups (`cli_package`, `upgrade_provider`, `distribution_profile`) | Phase 1 packagers need thin aliases; Phase 2 prefers one profile | Collapsing to profile-only breaks FR-017 thin-alias requirement |

## Implementation Concern Map

### IC-01 — Package name + upgrade provider resolvers

- **Purpose**: Canonical `resolve_cli_package_name()` and `resolve_upgrade_provider()` with process-level memo and stock fallbacks.
- **Relevant requirements**: FR-001–FR-004, FR-017, NFR-001–NFR-003, C-001
- **Affected surfaces**: `src/specify_cli/distribution/package_name.py`, `upgrade_provider.py`, tests
- **Sequencing/depends-on**: none
- **Risks**: Sibling WIP already has a session_presence copy — delete/redirect that path if merging; entry-point loading must never raise into callers

### IC-02 — Phase 1 call-site wiring + guide stub

- **Purpose**: Wire session-presence refresh, `version_utils.get_version()`, and `--version` banner to resolvers; document Phase 1 registration.
- **Relevant requirements**: FR-005–FR-008
- **Affected surfaces**: `session_presence/*`, `version_utils.py`, `__init__.py` / CLI version path, `docs/guides/fork-packaging-hooks.md` (Phase 1 section)
- **Sequencing/depends-on**: IC-01
- **Risks**: Banner path may live in multiple places — grep for hardcoded `spec-kitty-cli` labels

### IC-03 — DistributionProfile + SimpleIndexProvider

- **Purpose**: Single packager profile object + PEP 503 HTML provider helper without embedding fork URLs in defaults.
- **Relevant requirements**: FR-009–FR-010, FR-016–FR-017, C-002
- **Affected surfaces**: `distribution/profile.py`, `distribution/simple_index.py`, contracts
- **Sequencing/depends-on**: IC-01
- **Risks**: `LatestVersionResult.source` is Literal `"pypi"|"none"` today — extend carefully (e.g. `"simple_index"`) or map private index success to an existing source token without lying; prefer extending the Literal with tests

### IC-04 — Compat / remediation / notifier / freshness wiring

- **Purpose**: Consume profile at planner, remediation, upgrade_hint, and `maybe_emit_no_upgrade_notice`; raise CHK028 length; optional data freshness TTL.
- **Relevant requirements**: FR-011–FR-015, NFR-001
- **Affected surfaces**: `compat/planner.py`, `compat/remediation.py`, `compat/upgrade_hint.py`, `compat/cache.py` (if freshness API needs param), `core/version_checker.py`
- **Sequencing/depends-on**: IC-01, IC-03
- **Risks**: CHK028 shared regex between remediation and upgrade_hint must stay in sync; display throttle vs data freshness must not be conflated

### IC-05 — Packager publish documentation (Phase 3)

- **Purpose**: End-state publish flow docs + link from existing upgrade/install guides.
- **Relevant requirements**: FR-018–FR-020, NFR-005, C-003–C-005
- **Affected surfaces**: `docs/guides/fork-packaging-hooks.md`, link from `docs/guides/upgrade-cli.md` (and/or install guide)
- **Sequencing/depends-on**: IC-02 (stub ok), completes after IC-04 APIs are stable
- **Risks**: Must not document fork-specific hostnames as upstream defaults

## Approach (SPDD)

**Chosen**: Entry-point plugins + shared `DistributionProfile` consumed by existing call sites; stock = no registrations.

**Rejected**:
- `.kittify/config.yaml` fork settings — wrong lifetime (project runtime vs install metadata); violates C-005.
- Continue packager sed/cp overlays — works but is the problem statement.
- Many separate entry-point groups per call site — harder for packagers than one profile + thin Phase 1 aliases.
