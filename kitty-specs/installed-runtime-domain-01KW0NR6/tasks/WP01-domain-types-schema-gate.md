---
work_package_id: WP01
title: Domain types + history-store schema gate
dependencies: []
requirement_refs:
- FR-001
- FR-004
- FR-012
- FR-016
- C-004
- C-008
- NFR-007
- NFR-010
tracker_refs: []
planning_base_branch: feat/installed-runtime-domain
merge_target_branch: feat/installed-runtime-domain
branch_strategy: Planning artifacts for this mission were generated on feat/installed-runtime-domain. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/installed-runtime-domain unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-installed-runtime-domain-01KW0NR6
base_commit: 06f0a4639dbde0ee25df2757a02bb4a0961eaea7
created_at: '2026-06-26T01:23:35.690311+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Domain types (strangler step 1)
assignee: ''
agent: ''
shell_pid: '1001497'
history:
- at: '2026-06-26T00:00:00Z'
  actor: system
  action: Prompt generated via spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/compat/
create_intent:
- src/specify_cli/compat/_detect/runtime.py
- src/specify_cli/compat/remediation.py
- src/specify_cli/compat/history.py
- src/specify_cli/compat/install_events.py
- tests/specify_cli/compat/test_runtime.py
- tests/specify_cli/compat/test_install_events.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/compat/_detect/runtime.py
- src/specify_cli/compat/remediation.py
- src/specify_cli/compat/history.py
- src/specify_cli/compat/install_events.py
- tests/specify_cli/compat/test_runtime.py
- tests/specify_cli/compat/test_install_events.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Domain types + history-store schema gate

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: src/specify_cli/compat/`.

---

## Objective

Introduce all new frozen-dataclass types for the installed-CLI runtime domain.
This is a **types-only** WP — zero behavior change, zero new functions (no
`detect_runtime()`, no `plan_remediation()`, no `UpgradeAttemptStore`). Every
existing test must remain green after this WP is merged.

The history-store schema design and blast-radius assessment are already committed
in `kitty-specs/installed-runtime-domain-01KW0NR6/data-model.md` (§6) and
`research.md` (§4), satisfying the C-008 gate that must precede WP02.

## Context & Constraints

Ground truth — read before editing:
- [`spec.md`](../spec.md) FR-001, FR-004, FR-012, FR-016, C-004, C-008, NFR-007, NFR-010
- [`data-model.md`](../data-model.md) §1 (`InstalledCliRuntime`), §2 (`RemediationCommand`), §4 (`UvToolInstallationVerified`), §5 (`UpgradeAttemptRecord`)
- [`plan.md`](../plan.md) IC-01

**Conventions (C-004):**
- All new modules: `from __future__ import annotations` at the top
- All domain types: `@dataclass(frozen=True)`
- Deferred imports inside functions where needed to avoid circular imports
- No `Protocol` types (C-003 — no second impl exists yet)
- Zero `# noqa` / `# type: ignore` suppressions (NFR-010)

**Negative scope:**
- Do NOT implement `detect_runtime()` (that is WP02)
- Do NOT implement `plan_remediation()` (that is WP03)
- Do NOT implement `UpgradeAttemptStore` (that is WP02)
- Do NOT modify any existing files outside the new modules listed below

## Branch Strategy

- **Planning base branch**: `feat/installed-runtime-domain`
- **Merge target branch**: `feat/installed-runtime-domain`

## Subtasks & Detailed Guidance

### T001 — Create `src/specify_cli/compat/_detect/runtime.py`

Create this new module. It must contain exactly the types listed in
`data-model.md` §1 — nothing else.

**Required types:**

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from specify_cli.compat._detect.install_method import InstallMethod
```

1. `PackageSource(StrEnum)` — 7 members: `PYPI_SPECIFIER`, `GIT`, `URL`, `DIRECTORY`, `EDITABLE`, `PATH`, `UNKNOWN`. See `data-model.md` §1 for string values.

2. `@dataclass(frozen=True) UvRequirement` — fields: `name: str`; optional: `specifier`, `directory`, `editable`, `path`, `git`, `url` (all `str | None = None`).

3. `@dataclass(frozen=True) InstalledCliRuntime` — all 12 fields from `data-model.md` §1. Use `tuple[UvRequirement, ...]` for `requirements`. Follow field invariants table exactly (some are `bool | None`, not just `bool`).

**Important**: `install_method` uses a deferred import (`InstallMethod` from `_detect/install_method.py`) to avoid circular imports. Use `TYPE_CHECKING` guard for the annotation; at runtime pass `InstallMethod` values normally. Alternatively, if `InstallMethod` is already importable at module load without circularity (inspect the existing import graph first), import it directly.

Verify: `from specify_cli.compat._detect.runtime import InstalledCliRuntime, UvRequirement, PackageSource` works without importing anything from `review/`, `upgrade_ux/`, or `planner.py`.

### T002 — Create `src/specify_cli/compat/remediation.py` (types only)

Create this module with **only the type definitions** from `data-model.md` §2.

Required:
1. `_COMMAND_RE = re.compile(r"^[A-Za-z0-9 .\-+_/=:]{1,128}$")` — the CHK028 regex. This **must** be the identical character class as in `compat/upgrade_hint.py` (currently at line 29). Copy it exactly, do not paraphrase.
2. `RemediationIntent(StrEnum)` — 3 members: `UPGRADE`, `REINSTALL_WITH_TEST`, `MANUAL_GUIDANCE` with their lowercase string values.
3. `@dataclass(frozen=True) RemediationCommand` — fields: `intent: RemediationIntent`, `argv: tuple[str, ...] | None`, `env: Mapping[str, str]`, `note: str | None`.
4. Stub `render()` method raising `NotImplementedError` — the full implementation is in WP03.

Do NOT implement `plan_remediation()` in this WP. The module ends after the `RemediationCommand` dataclass.

### T003 — Create `src/specify_cli/compat/history.py` (dataclass only)

Create this module with **only the dataclass definitions** from `data-model.md` §5.

Required:
1. `UpgradeAttemptOutcome(StrEnum)` — 3 members: `SUCCESS`, `FAILURE`, `ABORTED` with lowercase values.
2. `@dataclass(frozen=True) UpgradeAttemptRecord` — fields from `data-model.md` §5: `attempt_id: str`, `timestamp: datetime`, `install_method: InstallMethod`, `intent: str`, `outcome: UpgradeAttemptOutcome`, `exit_code: int | None`, `target_version: str | None`.

Do NOT implement `UpgradeAttemptStore` in this WP. The module ends after `UpgradeAttemptRecord`.

NFR-007 docstring: note that no user paths, project slugs, hostnames, or machine IDs may be stored.

### T004 — Create `src/specify_cli/compat/install_events.py`

Create this module from `data-model.md` §4.

Required:
1. `VerificationConfidence(StrEnum)` — 3 members: `LOW`, `MEDIUM`, `HIGH`.
2. `@dataclass(frozen=True) UvToolInstallationVerified` — fields: `receipt_path: Path | None`, `entrypoint_match: bool`, `package_binding: str`, `confidence: VerificationConfidence`.

Include the docstring confidence derivation table from `data-model.md` §4:
- HIGH: exit_code == 0 AND entrypoint_match == True
- MEDIUM: exit_code == 0 AND entrypoint_match == False
- LOW: exit_code != 0

NFR-007 note: the event consumer MUST NOT log or transmit `receipt_path`.

### T005 — Write construction tests

Create `tests/specify_cli/compat/test_runtime.py`:
- Test `InstalledCliRuntime` constructs with all fields populated
- Test `InstalledCliRuntime` constructs with all optional fields None/empty
- Test `UvRequirement` constructs with only `name`
- Test `PackageSource` enum has all 7 members with correct string values
- Test frozen constraint: assigning to a field raises `FrozenInstanceError`

Create `tests/specify_cli/compat/test_install_events.py`:
- Test `UvToolInstallationVerified` constructs with all 4 fields
- Test `VerificationConfidence` has LOW/MEDIUM/HIGH members
- Test frozen constraint

All tests use only stdlib; no mocking of filesystems required in this WP.

### T006 — Green-gate verification

Run the full test suite:
```bash
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -q
```

Expected: zero failures, zero ruff/mypy issues on new files.

Also run:
```bash
ruff check src/specify_cli/compat/_detect/runtime.py src/specify_cli/compat/remediation.py src/specify_cli/compat/history.py src/specify_cli/compat/install_events.py
mypy src/specify_cli/compat/_detect/runtime.py src/specify_cli/compat/remediation.py src/specify_cli/compat/history.py src/specify_cli/compat/install_events.py
```

Zero issues required before committing.

## Success Criteria

- [ ] All 4 new modules created: `runtime.py`, `remediation.py`, `history.py`, `install_events.py`
- [ ] All types are frozen dataclasses with `from __future__ import annotations`
- [ ] `render()` is a stub raising `NotImplementedError` (WP03 completes it)
- [ ] `UpgradeAttemptStore` is absent (WP02 adds it)
- [ ] `detect_runtime()` is absent (WP02 adds it)
- [ ] Full test suite green
- [ ] Zero ruff / mypy issues on new files
- [ ] No existing files modified outside the 4 new modules + 2 test files

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Circular import between `runtime.py` and `install_method.py` | Use `TYPE_CHECKING` guard for `InstallMethod` annotation; test import order at module load |
| CHK028 regex diverges from `upgrade_hint.py` | Copy from `compat/upgrade_hint.py` line 29 verbatim; add an assertion test comparing the two compile patterns |
| `requirements: tuple` field defaults to `None` | Default must be `field(default_factory=tuple)` or `= ()` — do NOT use `None` as default |
