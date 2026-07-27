# Implementation Plan: Revive the compat-planner.json contract check (CI-portable) and fix the drift it surfaces

**Branch**: `fix/compat-planner-contract-ci-portable` | **Issue**: #2419 | **Spec**: [spec.md](./spec.md)

## Summary

Resurrect the dead `compat-planner.json` contract-conformance check in `tests/specify_cli/cli/commands/test_upgrade_command.py`. The shared helper `_validate_json_contract` resolves the contract via a worktree-relative path that only exists in a maintainer landing-worktree, so in CI `_CONTRACT` is `None` and `jsonschema.validate` early-`return`s at every call site — validating nothing. Fix: (1) anchor the path on the already-correct repo root and drop the silent `.exists()`/`suppress` fallback so a missing contract fails hard (FR-001/002/003, NFR-001); (2) because the revived check immediately catches one real pre-existing drift — `UnifiedBundleMigration.description` at 283 chars vs the contract's `maxLength: 256` — trim that description to ≤256 preserving meaning so the suite is green with validation genuinely live (FR-005), never by re-suppressing; (3) prove the check is non-vacuous (a schema-violating payload fails) and the full file is green (FR-004, SC-001–004). The post-spec squad empirically confirmed exactly one violation (48 pass / 1 fail). The post-plan squad surfaced a **second** dead enforcer of the same contract — `tests/specify_cli/compat/test_messages.py` (`parents[4]` overshoot, 5 `render_json` call sites) — so the mission closes the defect class by reviving it too, with the correct `parents[3]` anchor (empirically green, 28 pass) (FR-006, SC-005).

## Technical Context

**Language/Version**: Python 3.11 (repo pinned)
**Primary Dependencies**: `pytest`, `jsonschema` (hard dep, `pyproject.toml`), `typer.testing.CliRunner`; module-under-test is the `spec-kitty upgrade` CLI surface
**Storage**: n/a (reads the committed JSON contract file)
**Testing**: `tests/specify_cli/cli/commands/test_upgrade_command.py` (the ~12 `_validate_json_contract` call sites); target test `test_project_migration_needed_project_dry_run_json_contract`
**Target Platform**: CI (GitHub Actions `/home/runner/work/spec-kitty/spec-kitty`) + local + maintainer `.worktrees/<name>/`
**Project Type**: single project (test-infra fix + one production-string trim)
**Performance Goals**: n/a
**Constraints**: reuse `_WORKTREE_ROOT` (`Path(__file__).parents[4]`); no new `# type: ignore`/`# noqa`/silent `suppress`; contract file + `upgrade` runtime behavior unchanged; `mypy --strict` + `ruff` clean
**Scale/Scope**: 2 files — `test_upgrade_command.py` (path + fail-hard) and `m_3_2_0rc35_unified_bundle.py` (trim one description)

## Charter Check

*GATE: must pass before task decomposition.*

- **Evidence-first / non-vacuous (red-first)** — the fix is proven by a payload that FAILS validation pre-fix and passes post-fix; the revival itself is shown to catch the 283-char drift before FR-005 trims it. ✅
- **Never retry-to-green / no re-suppression** — green is reached by trimming the real drifted string, not by neutering the check, skipping, or gaming the fixture. ✅
- **Canonical sources** — anchor on the already-correct `_WORKTREE_ROOT`; do not invent a new root-finder; do not touch the stable contract. ✅
- **Draft-PR-first / operator decides** — lands as a cross-fork draft; operator merges. ✅
- **Quality gates** — `ruff` + `mypy --strict` clean, no new suppressions. ✅

No violations → Complexity Tracking not required.

## Project Structure

### Documentation (this mission)
```
kitty-specs/compat-planner-contract-ci-portable-01KWVKYH/
├── spec.md · plan.md · tasks.md
```

### Source / deliverables (repository root)
```
tests/specify_cli/cli/commands/test_upgrade_command.py                  # repo-root-anchored path + hard-fail (no skip); FR-001/002/003
tests/specify_cli/compat/test_messages.py                              # parents[3] anchor + hard-fail; activate 5 render_json checks; FR-006
src/specify_cli/upgrade/migrations/m_3_2_0rc35_unified_bundle.py        # trim UnifiedBundleMigration.description to <=256; FR-005
```

**Structure Decision**: single project; the fix spans two dead-check test files and one production description string.

## Implementation Concern Map

### IC-01 — CI-portable contract resolution + always-validate + fail-hard
- **Purpose**: make the shared `_validate_json_contract` helper load the real contract in any checkout and validate unconditionally; a missing/unreadable contract fails hard.
- **Relevant requirements**: FR-001, FR-002, FR-003; NFR-001; SC-001, SC-003.
- **Affected surfaces**: `test_upgrade_command.py` module-level `_CONTRACT_PATH`/`_CONTRACT` (lines ~61-75) and the helper `_validate_json_contract` (lines ~107-124). Resolve `_CONTRACT_PATH = _WORKTREE_ROOT / "kitty-specs" / "cli-upgrade-nag-lazy-project-migrations-01KQ6YDN" / "contracts" / "compat-planner.json"`; load the contract at import (or first use) and let a load failure raise with a clear message (drop `.exists()` + `contextlib.suppress`); remove the `if _CONTRACT is not None:` guard so validation always runs.
- **Sequencing/depends-on**: none (root change).
- **Risks**: activating validation at ~12 call sites surfaces real non-conformances — expected; the one known is handled in IC-02, any other is a real violation to triage (not re-suppress).

### IC-02 — Remediate the drift the revived check surfaces
- **Purpose**: bring the one over-cap description into compliance so the live check is green.
- **Relevant requirements**: FR-005; SC-002, SC-004.
- **Affected surfaces**: `m_3_2_0rc35_unified_bundle.py` `UnifiedBundleMigration.description` — trim from 283 to ≤256 chars preserving meaning (e.g. condense the trailing "Does NOT scan worktrees, remove symlinks, or reconcile .gitignore." clause). Do NOT change the contract's `maxLength: 256`.
- **Sequencing/depends-on**: IC-01 (the check must be live to witness the fix).
- **Risks**: over-trimming loses meaning — keep the substantive "validate bundle / refresh derivatives / structured report / idempotent" content.

### IC-03 — Non-vacuous witness + full-file green
- **Purpose**: prove the check genuinely fires and the whole file is green with validation live.
- **Relevant requirements**: FR-004; SC-001, SC-002, SC-004.
- **Affected surfaces**: a focused assertion that a deliberately schema-violating payload raises `jsonschema.ValidationError` (the non-vacuous witness), plus a simulated-CI-layout check that `_CONTRACT` loads; run the full `test_upgrade_command.py` green after IC-01+IC-02.
- **Sequencing/depends-on**: IC-01, IC-02.
- **Risks**: the witness must assert on the real helper/contract, not a stubbed schema, or it proves nothing.

### IC-04 — Close the class: revive the sibling render_json check
- **Purpose**: revive the second dead enforcer of the same contract so no vacuous-green check survives the mission.
- **Relevant requirements**: FR-006; SC-004, SC-005.
- **Affected surfaces**: `test_messages.py` `_CONTRACT_PATH` (lines ~44-50) → anchor on `Path(__file__).parents[3]` (this file is 3-deep, so parents[3] is the repo root — NOT parents[4]); `_get_contract` / `_validate_against_schema` (lines ~279-292) → drop the `.exists()→None` + `except Exception: return None` + `if contract is None: return` silent-skip so a missing/unreadable contract fails hard; the 5 `render_json` call sites (311,325,340,353,366) then validate for real (empirically green, 28 pass).
- **Sequencing/depends-on**: none (independent of IC-01/02/03; same class, different file).
- **Risks**: depth differs from the sibling — use `parents[3]` here vs `parents[4]` in `test_upgrade_command.py`; do not copy the sibling's index. Keep the `jsonschema`-absent fallback branch honest (fail-hard, not silent-return).
