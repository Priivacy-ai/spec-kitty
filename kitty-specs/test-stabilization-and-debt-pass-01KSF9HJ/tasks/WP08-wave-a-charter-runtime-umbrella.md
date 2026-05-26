---
work_package_id: WP08
title: 'Wave A LD-5: group charter_* packages under charter_runtime/ umbrella (FR-014)'
dependencies:
- WP07
requirement_refs:
- FR-014
planning_base_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
merge_target_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
base_commit: dde23795ec9f1327d9f7af9a30dc69a09f5f127d
created_at: '2026-05-25T15:59:37.459170+00:00'
subtasks:
- T028
- T029
- T030
- T031
- T032
- T033
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "2458199"
history:
- by: claude
  at: '2026-05-25T14:00:00+00:00'
  action: generated
agent_profile: python-pedro
authoritative_surface: src/specify_cli/charter_runtime/
execution_mode: code_change
mission_id: 01KSF9HJBFKRBC617JVHKZXNE2
mission_slug: test-stabilization-and-debt-pass-01KSF9HJ
owned_files:
- src/specify_cli/charter_runtime/**
- src/specify_cli/charter_lint/__init__.py
- src/specify_cli/charter_freshness/__init__.py
- src/specify_cli/charter_preflight/__init__.py
- src/specify_cli/charter/__init__.py
- CHANGELOG.md
- tests/architectural/test_charter_runtime_shim_paths.py
priority: P1
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Invoke `/ad-hoc-profile-load` with argument `python-pedro` before reading further. Behaviour-preserving package move with shim re-exports.

## Objective

Group four charter-runtime-adjacent packages under a single `src/specify_cli/charter_runtime/` umbrella:

- `src/specify_cli/charter_lint/` → `src/specify_cli/charter_runtime/lint/`
- `src/specify_cli/charter_freshness/` → `src/specify_cli/charter_runtime/freshness/`
- `src/specify_cli/charter_preflight/` → `src/specify_cli/charter_runtime/preflight/`
- `src/specify_cli/charter/` → `src/specify_cli/charter_runtime/facade/`

Each old path keeps a 5-line shim `__init__.py` that re-exports the new canonical symbols. External importers continue to work for one deprecation window (spec C-008).

Closes LD-5 from the architect's deep-dive review.

## Branch strategy

- Planning base branch: mission lane branch (post-WP07)
- Merge target branch: `main`
- Execution: lane workspace allocated by `finalize-tasks`.

## Context

- [`spec.md`](../spec.md) FR-014 + C-008.
- [`plan.md`](../plan.md) Wave A § WP08.
- [`docs/engineering_notes/architectural-review/2026-05-25-deep-dive-architectural-review.md`](../../../docs/engineering_notes/architectural-review/2026-05-25-deep-dive-architectural-review.md) §2 LD-5.

## Subtask details

### T028 — Create the umbrella package skeleton

```bash
mkdir -p src/specify_cli/charter_runtime/{lint,freshness,preflight,facade}
```

Create `src/specify_cli/charter_runtime/__init__.py`:
```python
"""Charter-runtime umbrella package.

Groups the four runtime concerns that compose the spec-kitty charter surface:

- ``charter_runtime.lint`` — decay-detection (formerly ``specify_cli.charter_lint``)
- ``charter_runtime.freshness`` — staleness / hash-comparison (formerly ``charter_freshness``)
- ``charter_runtime.preflight`` — pre-session readiness check (formerly ``charter_preflight``)
- ``charter_runtime.facade`` — the existing charter facade (formerly ``charter``)

The legacy import paths (``specify_cli.charter_lint``, etc.) continue to resolve
via shim re-exports at the old locations for one deprecation window per spec C-008.
"""
__all__: list[str] = []
```

### T029 — Move package contents

For each of the four old packages, `git mv` the contents into the new location:

```bash
git mv src/specify_cli/charter_lint/* src/specify_cli/charter_runtime/lint/
git mv src/specify_cli/charter_freshness/* src/specify_cli/charter_runtime/freshness/
git mv src/specify_cli/charter_preflight/* src/specify_cli/charter_runtime/preflight/
git mv src/specify_cli/charter/* src/specify_cli/charter_runtime/facade/
```

(Then handle the four `__init__.py` files specially — they become shims in T030.)

Update intra-package imports inside the moved files:
- `from specify_cli.charter_lint.engine import ...` → `from specify_cli.charter_runtime.lint.engine import ...`
- etc.

Use grep + sed (carefully — bulk-edit gate is NOT engaged because this is one-file-at-a-time directory move).

### T030 — Add shim re-exports at old paths

At each of the four old `__init__.py` locations, create:

```python
# src/specify_cli/charter_lint/__init__.py
"""Deprecated import path — use ``specify_cli.charter_runtime.lint``.

This shim re-exports the canonical module's public symbols for one
deprecation window per spec test-stabilization-and-debt-pass-01KSF9HJ C-008.
"""
from specify_cli.charter_runtime.lint import *  # noqa: F401,F403
from specify_cli.charter_runtime.lint import __all__  # noqa: F401
```

Same pattern for `charter_freshness/__init__.py`, `charter_preflight/__init__.py`, `charter/__init__.py`.

### T031 — CHANGELOG entry per C-008

Add under `[Unreleased]` in `CHANGELOG.md`:

```markdown
### Changed

- **Charter-runtime packages grouped under `specify_cli.charter_runtime/`**.
  The four packages `charter`, `charter_lint`, `charter_freshness`, `charter_preflight`
  are now submodules of `charter_runtime`. Canonical import paths:
  - `from specify_cli.charter_runtime.lint import LintEngine`
  - `from specify_cli.charter_runtime.freshness import compute_freshness, CharterFreshness`
  - `from specify_cli.charter_runtime.preflight import run_charter_preflight, CharterPreflightResult`
  - `from specify_cli.charter_runtime.facade import ...`
  
  The old import paths continue to resolve via re-export shims for one
  release cycle. Migrate to the canonical paths before the next major
  release; the shims will be removed in 3.3.0.
  
  Related: architectural review LD-5 in
  `docs/engineering_notes/architectural-review/2026-05-25-deep-dive-architectural-review.md`.
```

### T032 — Architectural shim-path regression test

Create `tests/architectural/test_charter_runtime_shim_paths.py`:

```python
"""Lock the LD-5 shim re-export contract: the old import paths still resolve.

Closes FR-014 + C-008 of mission 01KSF9HJ. Removing this test (or weakening
the assertions) before the deprecation window closes is a regression.
"""

def test_charter_lint_shim_resolves():
    from specify_cli.charter_lint import LintEngine
    from specify_cli.charter_runtime.lint import LintEngine as CanonicalLintEngine
    assert LintEngine is CanonicalLintEngine

def test_charter_freshness_shim_resolves():
    from specify_cli.charter_freshness import compute_freshness, CharterFreshness
    from specify_cli.charter_runtime.freshness import (
        compute_freshness as canonical_compute_freshness,
        CharterFreshness as CanonicalCharterFreshness,
    )
    assert compute_freshness is canonical_compute_freshness
    assert CharterFreshness is CanonicalCharterFreshness

def test_charter_preflight_shim_resolves():
    from specify_cli.charter_preflight import run_charter_preflight, CharterPreflightResult
    from specify_cli.charter_runtime.preflight import (
        run_charter_preflight as canonical_run_charter_preflight,
        CharterPreflightResult as CanonicalCharterPreflightResult,
    )
    assert run_charter_preflight is canonical_run_charter_preflight
    assert CharterPreflightResult is CanonicalCharterPreflightResult

def test_charter_facade_shim_resolves():
    # Adjust to the actual public symbol of the charter facade package.
    import specify_cli.charter
    import specify_cli.charter_runtime.facade as canonical
    assert specify_cli.charter.__dict__ is not None  # smoke check
    # If a specific symbol is exported, lock its identity here.
```

### T033 — Verify ~120-test charter-runtime smoke suite

```bash
PWHEADLESS=1 .venv/bin/pytest \
  tests/specify_cli/charter_lint/ \
  tests/specify_cli/charter_freshness/ \
  tests/specify_cli/charter_preflight/ \
  tests/architectural/test_charter_runtime_shim_paths.py \
  -q
```

Expected: 0 failures across the combined suite (~120 tests + the 4 new shim tests).

## Definition of Done

- [ ] `src/specify_cli/charter_runtime/` exists with 4 submodule directories.
- [ ] Each old path (`charter_lint`, `charter_freshness`, `charter_preflight`, `charter`) has a shim `__init__.py` that re-exports the new canonical symbols.
- [ ] `test_charter_runtime_shim_paths.py` passes — all 4 shim paths resolve.
- [ ] ~120-test charter-runtime smoke suite green via BOTH old and new import paths.
- [ ] CHANGELOG entry exists under `[Unreleased]` per C-008.
- [ ] Success criterion 6 (spec) verified: `ls -d src/specify_cli/charter_runtime/*/` shows the 4 submodules.
- [ ] `mypy --strict` clean on `charter_runtime/`.

## Risks

- **Intra-package import drift**: the moved files reference each other via `from specify_cli.charter_lint.engine import ...`. All such imports must be updated to the new `charter_runtime.lint.engine` paths.
- **Sibling-package consumers**: `src/specify_cli/cli/commands/charter/` (from WP06) imports from `specify_cli.charter_lint`. Those imports continue to resolve via the shims, so behaviour is preserved — but a future cleanup mission should migrate the call sites to the canonical paths before the shim window closes.
- **CHANGELOG conflict**: another mission may be staging a CHANGELOG entry. Coordinate at merge time.

## Reviewer guidance

1. Verify the 4 shim modules `is`-equal the canonical symbols (`test_charter_runtime_shim_paths.py` enforces this).
2. Verify CHANGELOG entry mentions the deprecation window explicitly.
3. Spot-check that `from specify_cli.charter_lint import LintEngine` still works at the Python REPL.

## Activity Log

- 2026-05-25T15:59:38Z – claude:opus-4-7:python-pedro:implementer – shell_pid=2253175 – Assigned agent via action command
- 2026-05-26T04:18:13Z – claude:opus-4-7:python-pedro:implementer – shell_pid=2253175 – LD-5 closed: 3 packages under charter_runtime/, sys.modules shims preserve legacy dotted paths, CHANGELOG entry, 3-test arch guard. Charter slice: 5/1105 fails vs 10 baseline.
- 2026-05-26T04:18:25Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=2458199 – Started review via action command
- 2026-05-26T04:18:48Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=2458199 – Self-review (arbiter): canonical+legacy paths import, sys.modules submodule shims verified by tests/architectural/test_charter_runtime_shim_paths.py (3/3 PASS). CHANGELOG entry per C-008. Charter slice 5/1105 fails (improvement from 10 baseline). Ruff clean.
