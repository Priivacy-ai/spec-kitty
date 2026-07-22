# Tasks: OSS Fork Packaging Hooks

**Mission**: `oss-fork-packaging-hooks-01KY2JFM`  
**Planning branch**: `feat/oss-fork-packaging-hooks`  
**Mission merge target**: `feat/oss-fork-packaging-hooks`  
**Generated**: 2026-07-21T15:03:00Z

## Planning Inputs

- [Specification](spec.md)
- [Implementation plan](plan.md)
- [Research decisions](research.md)
- [Data model](data-model.md)
- [Entry-point contract](contracts/entry-points.md)
- [Distribution profile contract](contracts/distribution-profile.md)
- [SimpleIndexProvider contract](contracts/simple-index-provider.md)
- [Developer quickstart](quickstart.md)

## Delivery Strategy

```text
WP01 → WP02
WP01 → WP03 → WP04
WP02 + WP04 → WP05
```

WP01 builds shared resolvers. WP02 wires Phase 1 call sites (can start after WP01). WP03 adds profile + SimpleIndexProvider. WP04 wires compat/remediation/notifier (needs WP03). WP05 finishes packager docs (needs Phase 1 stub from WP02 and stable APIs from WP04).

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Create `specify_cli.distribution` package skeleton with `__all__` | WP01 | — |
| T002 | RED tests for `resolve_cli_package_name` precedence | WP01 | [P] |
| T003 | Implement `resolve_cli_package_name` (entry point → packages_distributions → default) | WP01 | — |
| T004 | RED tests for `resolve_upgrade_provider` (none/one/many/env/fail-closed) | WP01 | [P] |
| T005 | Implement `resolve_upgrade_provider` with process memo + stock PyPI fallback | WP01 | — |
| T006 | Focused ruff/mypy/pytest gates for distribution package | WP01 | — |
| T007 | RED tests: session-presence refresh uses resolved provider + package name | WP02 | — |
| T008 | Wire session-presence upgrade refresh to distribution resolvers | WP02 | — |
| T009 | Wire `version_utils.get_version` to resolved name (+ alias hook stub) | WP02 | — |
| T010 | Wire `--version` banner label to resolved package name | WP02 | — |
| T012 | Stock-path regression: no entry points ⇒ public PyPI / spec-kitty-cli behaviour | WP02 | — |
| T013 | RED tests + implement `DistributionProfile` + `resolve_distribution_profile` | WP03 | — |
| T014 | Extend `LatestVersionResult.source` with `simple_index` + tests | WP03 | [P] |
| T015 | Implement `SimpleIndexProvider` (PEP 503 HTML, never raises) | WP03 | — |
| T016 | Focused gates for profile + simple index modules | WP03 | — |
| T017 | Wire compat planner to resolvers + optional `data_freshness_seconds` | WP04 | — |
| T018 | Wire remediation + upgrade_hint package name, index argv, CHK028=512 | WP04 | — |
| T019 | Gate `maybe_emit_no_upgrade_notice` on `disable_public_pypi_notifier` | WP04 | — |
| T020 | Alias-aware installed version lookup in planner/compat (distribution helper; not version_utils) | WP04 | — |
| T021 | Integration tests for private-index profile scenario + stock notifier | WP04 | — |
| T011 | Document Phase 1–3 packager entry-point registration in fork-packaging guide | WP05 | — |
| T022 | Complete packager publish-flow documentation (Phases 1–3 end state) | WP05 | — |
| T023 | Link guide from existing upgrade/install docs | WP05 | [P] |
| T024 | CHANGELOG note for packager hooks (additive, stock unchanged) | WP05 | — |
| T025 | Cross-WP quality sweep + terminology guard for docs | WP05 | — |

## Phase 1 — Shared resolvers

### WP01 — Distribution package name + upgrade provider resolvers

**Prompt**: [tasks/WP01-distribution-resolvers.md](tasks/WP01-distribution-resolvers.md)  
**Priority**: P0  
**Independent test**: With no entry points, resolvers return `spec-kitty-cli` + `PyPIProvider`; with fake entry points, name and provider match registration; load failures never raise.  
**Dependencies**: None

- [x] T001 Create `specify_cli.distribution` package skeleton with `__all__` (WP01)
- [x] T002 RED tests for `resolve_cli_package_name` precedence (WP01)
- [x] T003 Implement `resolve_cli_package_name` (entry point → packages_distributions → default) (WP01)
- [x] T004 RED tests for `resolve_upgrade_provider` (none/one/many/env/fail-closed) (WP01)
- [x] T005 Implement `resolve_upgrade_provider` with process memo + stock PyPI fallback (WP01)
- [x] T006 Focused ruff/mypy/pytest gates for distribution package (WP01)

**Implementation sketch**: Port algorithm from sibling WIP `session_presence/upgrade_provider.py` into `distribution/`, add package-name resolver, memoize, never raise.

**Risks**: Duplicate homes if sibling code is also merged — this mission is canonical.

## Phase 2 — Phase 1 call-site wiring

### WP02 — Session-presence, version utils, banner + Phase 1 docs stub

**Prompt**: [tasks/WP02-phase1-call-site-wiring.md](tasks/WP02-phase1-call-site-wiring.md)  
**Priority**: P0  
**Independent test**: Stock install behaviour unchanged; with entry points, refresh/get_version/banner use fork identity/provider.  
**Dependencies**: WP01

- [x] T007 RED tests: session-presence refresh uses resolved provider + package name (WP02)
- [x] T008 Wire session-presence upgrade refresh to distribution resolvers (WP02)
- [x] T009 Wire `version_utils.get_version` to resolved name (+ alias hook stub) (WP02)
- [x] T010 Wire `--version` banner label to resolved package name (WP02)
- [x] T012 Stock-path regression: no entry points ⇒ public PyPI / spec-kitty-cli behaviour (WP02)

## Phase 3 — Profile + simple index

### WP03 — DistributionProfile + SimpleIndexProvider

**Prompt**: [tasks/WP03-distribution-profile-simple-index.md](tasks/WP03-distribution-profile-simple-index.md)  
**Priority**: P0  
**Independent test**: Profile resolves from entry point or synthesizes from Phase 1 aliases; SimpleIndexProvider parses fixture HTML and never raises.  
**Dependencies**: WP01

- [x] T013 RED tests + implement `DistributionProfile` + `resolve_distribution_profile` (WP03)
- [x] T014 Extend `LatestVersionResult.source` with `simple_index` + tests (WP03)
- [x] T015 Implement `SimpleIndexProvider` (PEP 503 HTML, never raises) (WP03)
- [x] T016 Focused gates for profile + simple index modules (WP03)

## Phase 4 — Compat / remediation / notifier

### WP04 — Planner, remediation, notifier, freshness wiring

**Prompt**: [tasks/WP04-compat-remediation-notifier.md](tasks/WP04-compat-remediation-notifier.md)  
**Priority**: P0  
**Independent test**: Profile with private index + notifier disabled drives planner/remediation/notifier correctly; CHK028 accepts 512-char commands with index URLs.  
**Dependencies**: WP03

- [x] T017 Wire compat planner to resolvers + optional `data_freshness_seconds` (WP04)
- [x] T018 Wire remediation + upgrade_hint package name, index argv, CHK028=512 (WP04)
- [x] T019 Gate `maybe_emit_no_upgrade_notice` on `disable_public_pypi_notifier` (WP04)
- [x] T020 Alias-aware installed version lookup in planner/compat (distribution helper; not version_utils) (WP04)
- [x] T021 Integration tests for private-index profile scenario + stock notifier (WP04)

## Phase 5 — Packager documentation

### WP05 — Packager publish-flow docs + changelog

**Prompt**: [tasks/WP05-packager-docs.md](tasks/WP05-packager-docs.md)  
**Priority**: P1  
**Independent test**: Guide describes end-state publish without core overlays; linked from upgrade-cli; no fork hostnames in stock defaults section.  
**Dependencies**: WP02, WP04

- [ ] T011 Document Phase 1–3 packager entry-point registration in fork-packaging guide (WP05)
- [ ] T022 Complete packager publish-flow documentation (Phases 1–3 end state) (WP05)
- [ ] T023 Link guide from existing upgrade/install docs (WP05)
- [ ] T024 CHANGELOG note for packager hooks (additive, stock unchanged) (WP05)
- [ ] T025 Cross-WP quality sweep + terminology guard for docs (WP05)
