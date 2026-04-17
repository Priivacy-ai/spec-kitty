# Charter Ownership Consolidation and Neutrality Hardening

**Mission ID**: `01KPD8804H8XZR8NJVJKV12HCW`
**Mission slug**: `charter-ownership-consolidation-and-neutrality-hardening-01KPD880`
**Mission type**: `software-dev`
**Change mode**: `bulk_edit` (import-path migration across internal callers)
**Target branch**: `main`
**Created**: 2026-04-17
**Trackers**: [#611 — Consolidate charter ownership](https://github.com/Priivacy-ai/spec-kitty/issues/611), [#653 — Shipped defaults leak Python/pytest bias](https://github.com/Priivacy-ai/spec-kitty/issues/653)
**Umbrella epic**: [#461 — Charter as Synthesis & Doctrine Reference Graph](https://github.com/Priivacy-ai/spec-kitty/issues/461)

---

## Primary Intent

Spec Kitty currently ships two overlapping charter package surfaces: `src/charter/*` and `src/specify_cli/charter/*`. Some modules in the legacy surface are already thin re-export shims, but others still carry real implementation, and live code continues to import from both paths. This duplicate ownership makes future synthesizer work (Phase 3, tracker #465) harder to reason about and it is the structural reason a class of neutrality regressions — most recently the Python/pytest/junit bias addressed in v3.1.5 — has been easy to re-introduce.

This mission does two things in one coherent pass, as the cleanup tranche that must land before or alongside Phase 3:

1. **Consolidate charter ownership** so `src/charter` is the single canonical implementation owner. The legacy `src/specify_cli/charter/*` surface is either deleted (for clearly internal modules) or reduced to deprecated thin re-export shims (where an external Python import surface may plausibly be relied on), with an explicit sunset plan for the shims.
2. **Finish the remaining neutrality hardening** started in v3.1.5 and install automated tripwires that prevent silent regression of language/tool-specific bias in generic shipped artifacts.

This mission renames the internal canonical import path for charter services — callers that import from `specify_cli.charter.*` migrate to `charter.*`. That is a cross-file same-string rewrite, so the mission runs under `change_mode: bulk_edit` and produces `occurrence_map.yaml` during planning.

---

## User Scenarios & Testing

### Primary actors

- **Spec Kitty contributors** (feature authors, refactorers, reviewers) — primary beneficiaries of canonical ownership.
- **End users running `spec-kitty`** — primary beneficiaries of preserved CLI behavior and absence of Python-specific pollution in generic projects.
- **Future mission authors** (especially Phase 3 synthesizer work) — primary beneficiaries of a single, clean charter substrate to build on.
- **External downstream consumers** of Python imports from `specify_cli.charter.*`, if any — must not experience a hard break without a deprecation window.

### Acceptance scenarios

1. **Canonical import for new charter work**
   - **Given** a contributor adds a new CLI command that needs charter context
   - **When** they consult docs and source code for the canonical import
   - **Then** the documented and discoverable path is `from charter.* import …`, and `specify_cli.charter.*` is either absent or clearly marked deprecated

2. **Ownership test rejects duplicate implementation**
   - **Given** an automated ownership test is in place
   - **When** a PR adds or retains a second real implementation of `build_charter_context()` or `ensure_charter_bundle_fresh()` in either package
   - **Then** CI fails with a clear message naming the canonical location

3. **Neutrality lint rejects Python-specific vocabulary in generic artifacts**
   - **Given** the content-lint regression test is active
   - **When** a PR introduces `pytest`, `junit`, `pip install`, `python -m`, or another registered banned term into a doctrine artifact that is not in the language-scoped allowlist
   - **Then** CI fails with an error message pointing to the specific file, the banned term, and instructions to either remove the term or register the file as language-scoped

4. **Legitimate Python-scoped doctrine is supported**
   - **Given** a contributor authors a new Python-scoped doctrine artifact intentionally containing `pytest` guidance
   - **When** they add the artifact path to the language-scoped allowlist
   - **Then** lint passes for that file and continues to gate all other generic-scoped files

5. **Deprecation warning for surviving shims**
   - **Given** external code imports from `specify_cli.charter.X` for a symbol that survives as a re-export shim
   - **When** the import executes under the post-mission release
   - **Then** the import resolves correctly and emits a `DeprecationWarning` naming the canonical import path and the planned removal release

6. **No surprise Python execution in unconfigured projects**
   - **Given** a fresh non-Python project with no explicit Python configuration
   - **When** the user runs any `spec-kitty` command that reads charter defaults
   - **Then** no Python-specific command (e.g., pytest invocation, pip install) is suggested or executed by default, and all surfaced suggestions are language/tool neutral

7. **CLI behavioral invariance**
   - **Given** the existing CLI integration test suite
   - **When** it runs against the post-mission codebase
   - **Then** every currently-passing test continues to pass with no changes to expected output

### Edge cases

- A doctrine file that mentions Python **as an example of what not to assume** (meta-commentary about neutrality). Resolution: allowlist is path-based, so such files are either Python-scoped, or the meta-commentary lives in a dedicated allowlisted location — the lint does not attempt phrase-level context analysis.
- A command-layer thin wrapper function that delegates to a canonical charter service but adds lightweight annotation (e.g., adds CLI-specific logging). Resolution: this is acceptable because the hard success criterion is "one real implementation," not "only one callable with the same name." The spec distinguishes implementation from wrapping.
- A legacy module whose name plausibly exists in third-party code as an import (e.g., `specify_cli/charter/bundle.py`). Resolution: retained as a deprecated shim, not deleted, with the removal release documented.
- A surviving shim that re-exports a symbol whose canonical name has also changed in the canonical location. Resolution: the shim preserves the old name at the legacy import path; the canonical location can rename freely.

---

## Functional Requirements

| ID      | Requirement                                                                                                                                                                                                                          | Status   |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------- |
| FR-001  | The system MUST contain exactly one real implementation of `build_charter_context()`, located in `src/charter`.                                                                                                                      | Required |
| FR-002  | The system MUST contain exactly one real implementation of `ensure_charter_bundle_fresh()`, located in `src/charter`.                                                                                                                | Required |
| FR-003  | All live internal callers of charter/governance services MUST import from the canonical `charter.*` package rather than `specify_cli.charter.*`.                                                                                     | Required |
| FR-004  | Any modules that remain under `src/specify_cli/charter/` after this mission MUST consist only of thin re-export shims that delegate to `charter.*` and contain no original implementation.                                           | Required |
| FR-005  | Every surviving re-export shim MUST emit a `DeprecationWarning` on import that names the canonical replacement path and a documented target removal release.                                                                         | Required |
| FR-006  | Modules under `src/specify_cli/charter/` that are verified as internal-only (no plausible external import surface) MUST be deleted after their callers are migrated.                                                                 | Required |
| FR-007  | The public CLI surface of `spec-kitty` MUST behave identically to the v3.1.5 baseline after this mission, as verified by the existing CLI integration test suite passing unchanged.                                                  | Required |
| FR-008  | Generic-scoped shipped charter and doctrine artifacts MUST NOT contain any registered banned term (initial list includes: `pytest`, `junit`, `pip install`, `python -m`, `.py` filename literal, and `pytest.ini`/`pyproject.toml` references in example commands). | Required |
| FR-009  | The system MUST provide an explicit allowlist of intentionally language-scoped doctrine artifact paths, editable in a single file.                                                                                                   | Required |
| FR-010  | The system MUST provide an automated regression test that fails when a generic-scoped artifact gains a banned term, or when a new artifact containing banned terms is added without appearing in the language-scoped allowlist.     | Required |
| FR-011  | The regression test described in FR-010 MUST produce an error message naming the offending file, the offending term, and the two remediation options (remove term, or register the path in the allowlist).                          | Required |
| FR-012  | Unconfigured/generic projects MUST NOT trigger any Python-specific runtime command (pytest invocation, pip install, python module execution) as a default from charter-driven flows.                                                 | Required |
| FR-013  | Python-specific doctrine guidance that exists in the repository MUST reside in artifacts registered on the language-scoped allowlist.                                                                                                | Required |
| FR-014  | The banned-terms list used by the neutrality lint MUST be maintained in a single, version-controlled, human-readable file; adding a term MUST not require code changes beyond editing that file.                                     | Required |
| FR-015  | The sunset plan for surviving shim modules MUST be recorded in a contributor-facing location (CHANGELOG.md entry, ADR, or dedicated migration doc) that names the target removal release.                                            | Required |
| FR-016  | The mission's `occurrence_map.yaml` MUST classify all 8 standard bulk-edit categories and be approved before any import-path changes are made, per DIRECTIVE_035.                                                                    | Required |

## Non-Functional Requirements

| ID       | Requirement                                                                                                                                                 | Status   |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| NFR-001  | The neutrality lint test MUST complete in under 5 seconds on typical developer hardware (measured on a baseline dev machine: ≤ 4-core CPU, SSD storage).    | Required |
| NFR-002  | Test coverage for newly authored code in this mission MUST be ≥ 90%, per project charter.                                                                   | Required |
| NFR-003  | `mypy --strict` MUST pass on all changed modules after this mission, per project charter.                                                                   | Required |
| NFR-004  | Deprecation warnings emitted by surviving shims MUST be standard `DeprecationWarning` instances catchable via `warnings.catch_warnings()` in user code.     | Required |
| NFR-005  | The charter consolidation MUST NOT increase cold-import time of `spec-kitty` CLI startup by more than 5% versus the v3.1.5 baseline (measured by existing CLI startup benchmark, or a new microbenchmark if none exists). | Required |
| NFR-006  | The neutrality allowlist file format MUST be self-documenting: a contributor opening it for the first time MUST be able to add a new language-scoped path without reading external docs.                                 | Required |

## Constraints

| ID    | Constraint                                                                                                                                                                                | Status   |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| C-001 | No on-disk migration of user projects' `.kittify/charter/bundle/*` layout. The Phase 2 bundle layout on user disk stays as-is.                                                            | Required |
| C-002 | No new agent profiles (PHP, Java, QA, Frontend/Webdev, Planning, etc.) are introduced in this mission. That work is deferred to Phase 4 (#466) or a separate mission.                     | Required |
| C-003 | No schema redesign of doctrine artifacts. Neutrality tripwires are implemented as content lint plus a path allowlist — no new `scope:` field or structural schema changes.                | Required |
| C-004 | No changes to the public `spec-kitty` CLI surface (command names, flags, exit codes, or documented output formats).                                                                       | Required |
| C-005 | Any external Python code importing documented symbols from `specify_cli.charter.*` MUST continue to resolve correctly for at least one release cycle after this mission merges, emitting only a `DeprecationWarning`. | Required |
| C-006 | No removal of currently-passing CLI integration tests; existing coverage must continue to hold.                                                                                            | Required |
| C-007 | Neutrality hardening scope is narrow (per user confirmation): tripwire installation and Python-scope isolation only. Extraction of per-language styleguides/toolguides is out of scope.   | Required |

---

## Success Criteria

- **SC-001**: An automated ownership test confirms exactly one real implementation of `build_charter_context()` and `ensure_charter_bundle_fresh()` in the codebase, both located under `src/charter`.
- **SC-002**: The existing CLI integration test suite passes with zero failures and zero test modifications that reduce coverage.
- **SC-003**: On a clean checkout at merge, the neutrality lint passes: zero banned-term occurrences in any generic-scoped doctrine artifact.
- **SC-004**: A static import scan shows 100% of live internal callers of charter services import from `charter.*`; `specify_cli.charter.*` imports survive only in (a) the shim modules themselves and (b) documented backward-compat test cases.
- **SC-005**: A deliberate CI fault-injection test confirms the neutrality tripwire catches a regression: adding `pytest` to a currently-generic artifact produces a failing CI run with a clear, actionable error message.
- **SC-006**: Every surviving shim module in `src/specify_cli/charter/` emits a `DeprecationWarning` on first import and documents its target removal release in a docstring; the same removal release is recorded in `CHANGELOG.md` or an ADR.
- **SC-007**: Running a representative `spec-kitty` command (`spec-kitty charter context`, `spec-kitty charter status`, or equivalent) in a freshly-initialized non-Python project produces output with no Python-specific commands, tool names, or file references.
- **SC-008**: The mission's `occurrence_map.yaml` is authored, reviewed, and approved before any cross-file import-path changes are committed, and the bulk-edit review gate passes at merge.

---

## Key Entities

- **Canonical charter package** (`src/charter/*`): the sole owner of charter/governance implementation after this mission.
- **Legacy charter package** (`src/specify_cli/charter/*`): contains only deprecated thin re-export shims after this mission, scheduled for full removal in a documented future release.
- **Live charter services**: `build_charter_context()`, `ensure_charter_bundle_fresh()`, bundle manifest resolution, canonical-root resolution, and any other functions currently straddling the two packages.
- **Generic-scoped doctrine artifact**: a shipped YAML/Markdown/template file intended to apply to any project regardless of language or tooling.
- **Language-scoped doctrine artifact**: a shipped file explicitly scoped to a particular language/toolchain (initially: Python), registered in the language-scoped allowlist.
- **Neutrality allowlist**: a single version-controlled file listing every path that is permitted to contain language/tool-specific vocabulary.
- **Banned-terms list**: a single version-controlled file enumerating regex patterns (or literal strings) that indicate Python/pytest-specific bias in a generic artifact.
- **Deprecation shim**: a module under `src/specify_cli/charter/` that re-exports symbols from `charter.*` and emits a `DeprecationWarning` on import.
- **Occurrence map** (`occurrence_map.yaml`): the bulk-edit classification artifact produced during planning that governs which categories of `specify_cli.charter.*` → `charter.*` occurrences get renamed, reviewed, or left alone.

---

## Assumptions

- The public stability contract of `spec-kitty` is the CLI surface, not the Python import surface. External consumers of `from specify_cli.charter.* import …` are rare; a one-release deprecation window with runtime `DeprecationWarning` is sufficient notification.
- `src/charter` already contains the architectural primitives required to host the consolidated implementation; this mission is primarily a migration of real implementation that currently lives in `specify_cli.charter` plus updates to internal callers, not a greenfield redesign.
- The Phase 2 bundle layout on user disk (canonical-root resolution, `ensure_charter_bundle_fresh()` chokepoint, manifest format) is stable. No user-facing disk migration is required.
- The initial banned-terms list (`pytest`, `junit`, `pip install`, `python -m`, `.py` filename literals, `pyproject.toml`, `pytest.ini` as example commands) is sufficient to catch the documented bias classes. Adding new terms in future is a lightweight edit to the terms file, not a schema change.
- Existing CLI integration tests provide adequate behavioral-regression coverage; this mission does not require net-new behavioral tests beyond those validating the ownership invariant and the neutrality lint itself.
- A path-based allowlist is sufficient for neutrality gating; phrase-level or AST-level analysis is not required.
- The occurrence map's default postures are appropriate starting points (code_symbols: rename, import_paths: rename, filesystem_paths: manual_review, serialized_keys: do_not_change, cli_commands: do_not_change, user_facing_strings: rename_if_user_visible, tests_fixtures: rename, logs_telemetry: do_not_change) and will be refined per-category during planning with user review.
- Deprecation target removal release is one minor version beyond the release that lands this mission (e.g., if this ships in 3.2.0, shim removal is targeted for 3.3.0); concrete release numbers are finalized in planning.

---

## Out of Scope

- Introduction of new agent profiles (PHP, Java, Planning, QA, Frontend/Webdev) — deferred to Phase 4 (#466) or a dedicated mission.
- Extraction of per-language styleguides/toolguides as a general pattern — deferred.
- Phase 3 charter synthesizer pipeline (#465) — separate mission, to start after this one lands.
- On-disk migration of user projects' charter bundle layout — already stable under Phase 2 baseline.
- Any changes to the public `spec-kitty` CLI surface (command names, flags, output schemas).
- Schema-level neutrality enforcement via new artifact fields (e.g., declared `scope:` field) — deferred pending explicit product decision.
- Internationalization or localization of doctrine content.
- Performance optimization of charter services beyond the no-regression baseline of NFR-005.

---

## Dependencies and References

- **Umbrella epic**: [#461 — Charter as Synthesis & Doctrine Reference Graph](https://github.com/Priivacy-ai/spec-kitty/issues/461)
- **Primary trackers**: [#611](https://github.com/Priivacy-ai/spec-kitty/issues/611), [#653](https://github.com/Priivacy-ai/spec-kitty/issues/653)
- **Baseline**: v3.1.5 on `main`. Phase 0 (#462), Phase 1 (#463), and Phase 2 (#464) are complete. Worst prompt/default bias removed in v3.1.5 / PR #656.
- **Downstream blocker relationship**: Phase 3 synthesizer work (#465) should be spec'd and implemented on the canonical charter stack produced by this mission.
- **Directive governance**: DIRECTIVE_003 (Decision Documentation), DIRECTIVE_010 (Specification Fidelity), DIRECTIVE_035 (Bulk-edit classification via `occurrence_map.yaml`).
- **Project charter policy**: Python 3.11+, typer + rich + ruamel.yaml, 90%+ coverage for new code, `mypy --strict`, integration tests for CLI commands.
