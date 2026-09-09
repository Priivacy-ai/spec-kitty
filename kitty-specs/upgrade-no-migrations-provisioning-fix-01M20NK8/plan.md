# Implementation Plan: Upgrade No-Migrations Provisioning Fix + `upgrade()` Tidy-First

**Branch**: `issue-1931-ci-rework-test-remainders` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/upgrade-no-migrations-provisioning-fix-01M20NK8/spec.md` (#4032, epic #1931)

## Summary

`spec-kitty upgrade` fails (`failed` outcome, `"Managed skill provisioning requires an existing authority"`) on any project whose `.kittify/config.yaml` authority is absent at assessment time. The post-spec adversarial squad corrected the fix location: the guard `ValueError` is already caught and converted to an `error`-severity diagnostic that poisons `complete`, and a second, decoupled raw provisioning descriptor is applied by the finalizer — so a naive benign guard would silently *create* the authority (the deferred #4047 behavior). The approach is therefore: **decide the deferral once, at the assessment/compiler layer**, by making `PreparedUpgradeRepairs.provisioning` Optional and nulling it when the authority is absent; surface a **non-error** `deferred_provisioning` diagnostic; reduce the installer guard to a pure integrity validator. The ~345-line `upgrade()` entry is decomposed first (tidy-first, behavior-preserving), then the fix lands, then each failing test is re-evaluated (keep config-absent witnesses, re-pin the oracle to the apply path, redesign the two-subsystem monkeypatch test, consolidate the triplicated fixture).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml (config-authority round-trip). **No new dependencies added** (see Supply-Chain note).
**Storage**: Filesystem — `.kittify/config.yaml` (or a `charter:`-pointed `charter.yaml`) is the provisioning authority; presence/absence drives `write.before_bytes is None`.
**Testing**: pytest (`tests/upgrade/`), Ruff (`C901` complexity gate), mypy; `PWHEADLESS=1` for any UI-adjacent runs (none here).
**Target Platform**: Linux/macOS CLI (also exercised by `ci-windows.yml`).
**Project Type**: single.
**Performance Goals**: N/A — correctness/maintainability mission; `upgrade` latency is unaffected.
**Constraints**: behavior-preserving decomposition; no added blanket suppressions (`# noqa`/`# type: ignore`/per-file ignore); C-001 — the finalizer raw `.apply()` must NOT create the authority; C-006 — present-but-degenerate (`b""`) authority out of scope.
**Scale/Scope**: ~4 source files (`skills/installer.py`, `upgrade/assessment.py`, `cli/commands/upgrade.py`, `upgrade/finalize.py`), the ~40-test frozen Group A list, 1 new shared fixture builder, 1 new guard-aligned test.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter (`.kittify/charter/charter.md`) gates relevant to this mission:

- **Single canonical authority (Governing Principle; DIRECTIVE_044).** ✅ The deferral decision is made in exactly one place (the assessment/compiler layer, an Optional descriptor) and consumed by guard, recheck, effects, and finalizer. We do NOT add a second policy site in the installer guard — the guard is reduced to integrity validation. PASS by design.
- **ATDD-first / red-first (Standing Order #4; DIRECTIVE_041/034).** ✅ FR-011 — each root fix carries a RED-first repro reproducing the exact `"requires an existing authority"` signal via the config-absent path through the pre-existing `upgrade()` entry, ideally adopting a pre-existing failing test as witness.
- **Tidy-first / campsite (Standing Order #2; DIRECTIVE_025).** ✅ WP01 decomposition is a distinct, behavior-preserving step preceding the functional change (C-004).
- **Tiered rigour (domain-driven-design paradigm).** ✅ High rigour on the provisioning/guard domain logic (the fix); behavior-preserving, test-anchored rigour on the CLI glue (the decomposition).
- **Architectural gate discipline (Standing Order #5; DIRECTIVE_043).** ✅ Reducing the guard to an integrity validator must stay NON-vacuous — it still raises on a genuinely malformed/non-canonical descriptor; a guard-aligned test asserts both the benign-skip and the malformed-raise arms.
- **Test remediation discipline (Standing Order #4).** ✅ FR-008/FR-009 judge each test (keep / redesign / re-pin-with-evidence / delete), never blanket-update.
- **Terminology canon.** ✅ No Mission/Feature rename involved; prose uses canonical terms.
- **No version prescription in scope (DIRECTIVE_045).** ✅ No patch number assigned.

No violations requiring Complexity Tracking.

## Supply-Chain Security & Adversarial Evidence

- **Dependencies**: this mission adds/upgrades/removes **no** dependency. Registry-authenticity / lifecycle-script / freshness checks are N/A. Recorded here per the `plan` step contract (silence is not compliance).
- **Adversarial evidence**: the post-spec adversarial squad (3 lenses) ran before plan readiness; every contested finding's disposition (`accepted` / `changed` / `deferred_with_rationale`) is recorded in [research.md](./research.md) §Adversarial Evidence. No contested finding was silently dropped.

## Project Structure

### Documentation (this mission)

```
kitty-specs/upgrade-no-migrations-provisioning-fix-01M20NK8/
├── plan.md              # This file
├── research.md          # Phase 0: architecture decision + adversarial-evidence dispositions
├── data-model.md        # Phase 1: the provisioning-decision state model
├── quickstart.md        # Phase 1: how to reproduce + verify
├── contracts/           # Phase 1: the deferred-provisioning diagnostic contract
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── skills/
│   └── installer.py          # _prepare_skill_provisioning (guard → integrity validator),
│                             #   _recheck_skill_provisioning (:445-473, in-place only — untouched for create)
├── upgrade/
│   ├── assessment.py         # PreparedUpgradeRepairs.provisioning → Optional; null on absent authority;
│   │                         #   provisioning_effects / completeness / diagnostic severity
│   └── finalize.py           # finalize_upgrade — must not apply a create when descriptor is None
└── cli/commands/
    └── upgrade.py            # upgrade() decomposition (:1421, drop # noqa: C901);
                              #   preserve repair_preflight `with` span

tests/upgrade/
├── _fixtures.py (NEW)        # shared project-shape builder (real init + absent-authority variant)
├── test_upgrade_assessment.py         # existing guard-aligned (present authority) — keep
├── test_upgrade_guard_absent.py (NEW) # guard-aligned config-ABSENT path (FR-007)
├── test_upgrade_char_net.py           # oracle — re-pin fixture to real init-ed (FR-006)
├── test_upgrade_integration.py        # KEEP config-absent fixtures; redesign monkeypatch test (FR-009)
├── test_upgrade_idempotency.py        # KEEP config-absent fixtures
└── (frozen Group A list enumerated in tasks.md)
```

**Structure Decision**: Single project. Four source files across three packages (`skills`, `upgrade`, `cli/commands`) plus the `tests/upgrade/` tree. The fix is concentrated in `upgrade/assessment.py` (the single decision seam); `installer.py` is *reduced*; `finalize.py` is guarded against applying a None descriptor; `upgrade.py` is decomposed.

## Complexity Tracking

No Constitution Check violations — section intentionally empty.

## Parallel Work Analysis

### Dependency Graph

```
WP01 (tidy-first decomposition) ──► WP02 (functional fix + red-first) ──► WP03 (test re-evaluation & consolidation)
     behavior-preserving;              Optional descriptor + non-error        frozen Group A green; oracle re-pin;
     un-suppress C901;                 diagnostic; guard→validator;           monkeypatch redesign; shared fixture;
     preserve preflight `with`         C-001 no-create assertion              dispositions recorded
```

Largely **sequential** — a small, high-judgment mission. WP01 must land first (testable surface); WP02's red-first repro must witness the pre-existing signal before the fix; WP03 validates and pays down test debt after the seam is correct.

### Work Distribution

- **Sequential work**: WP01 → WP02 → WP03 (each depends on the prior).
- **Parallel streams**: within WP03, the oracle re-pin, the monkeypatch redesign, and the shared-fixture consolidation are independent file edits that may proceed in parallel once WP02 lands.
- **Agent assignments**: implementer = python-pedro (core domain rigour); reviewer = reviewer-renata (distinct role). Profiles LOADED, not named.

### Coordination Points

- **Sync**: WP02 must publish the final diagnostic-channel shape (the `deferred_provisioning` key + human-mode `Note:` line) before WP03 writes assertions against it.
- **Integration tests**: the frozen Group A list is the integration oracle; `test_upgrade_char_net.py` (re-pinned) is the behavior-preservation oracle; `test_no_stray_noqa_c901_marker` gates the decomposition.
