# Trackers to File — DIRECTIVE_013 Pre-existing Debt

**Prepared by:** curator-carla (WP06 / T021)
**Date:** 2026-06-02
**Directive:** DIRECTIVE_013 — pre-existing failures and deferred items that are NOT absorbed by this mission must be tracked before merge.

**FINAL DISPOSITION (orchestrator, 2026-06-02):**
- **Group A (4 `git_repo` marker gaps) — ABSORBED, not filed.** Per operator decision, the pre-existing pytest-marker gate failures were fixed directly in this close-out (commit `7cdb3f5c5`) as a boyscout scope increase rather than tracker-only. The drafts below are retained for provenance.
- **Group B (upstream `status_service` debt) — FILED: [Priivacy-ai/spec-kitty#1622](https://github.com/Priivacy-ai/spec-kitty/issues/1622).** (The `lifecycle_events` pair was resolved in WP04, so the issue covers only the 5 `status_service` symbols.)
- **Group C (FR-012 doctor.py split) — FILED: [Priivacy-ai/spec-kitty#1623](https://github.com/Priivacy-ai/spec-kitty/issues/1623).**
- **Group D (FR-013 provenance typing) — FILED: [Priivacy-ai/spec-kitty#1624](https://github.com/Priivacy-ai/spec-kitty/issues/1624).** Reframed: the generic `TypeVar` fix (I-3 mypy class) landed in WP04; only the `Provenanced[T]` sidecar refactor is deferred.

---

## A. `git_repo` Marker Gaps — 4 Test Files {#git-repo-marker-gaps}

These four test files lack a `git_repo` / pytest-marker for the `git_repo` category (or lack the expected `pytestmark` decorator entirely), which means they are invisible to any CI profile that runs only `git_repo`-tagged tests.

### Issue A-1 — `tests/architectural/test_no_legacy_terminology.py`

**Title:** `[DIRECTIVE_013] test_no_legacy_terminology.py: missing pytestmark — invisible to marker-filtered CI runs`

**Body:**
```markdown
## Summary

`tests/architectural/test_no_legacy_terminology.py` has no `pytestmark` declaration.
Under `-m fast`, `-m contract`, or `-m architectural` CI profiles, this test does not run,
allowing forbidden legacy terms to reappear undetected in filtered runs.

Identified during: `org-doctrine-profile-integrity-activation-closure-01KT1TV1` close-out (WP06/T021).

## Steps to reproduce

```bash
grep -c pytestmark tests/architectural/test_no_legacy_terminology.py
# → 0
```

## Expected

`pytestmark = [pytest.mark.architectural]` (or appropriate category) added so the test
participates in the architectural marker profile.

## Labels

DIRECTIVE_013
```

---

### Issue A-2 — `tests/specify_cli/sync/test_local_commit_wiring.py`

**Title:** `[DIRECTIVE_013] test_local_commit_wiring.py: missing git_repo pytestmark`

**Body:**
```markdown
## Summary

`tests/specify_cli/sync/test_local_commit_wiring.py` does not carry a `git_repo` marker.
Tests in this file exercise real git operations and should be tagged so CI can selectively
skip them on non-git-available runners.

Identified during: `org-doctrine-profile-integrity-activation-closure-01KT1TV1` close-out (WP06/T021).

## Current state

```bash
grep pytestmark tests/specify_cli/sync/test_local_commit_wiring.py
# → pytestmark = [pytest.mark.unit]  ← no git_repo marker
```

## Expected

Add `pytest.mark.git_repo` to the pytestmark list so the file is correctly classified.

## Labels

DIRECTIVE_013
```

---

### Issue A-3 — `tests/specify_cli/test_sync_state_gitignore_migration.py`

**Title:** `[DIRECTIVE_013] test_sync_state_gitignore_migration.py: missing git_repo pytestmark`

**Body:**
```markdown
## Summary

`tests/specify_cli/test_sync_state_gitignore_migration.py` exercises gitignore-related
migration behaviour against real or mocked git operations but lacks the `git_repo` marker.

Identified during: `org-doctrine-profile-integrity-activation-closure-01KT1TV1` close-out (WP06/T021).

## Current state

```bash
grep pytestmark tests/specify_cli/test_sync_state_gitignore_migration.py
# → pytestmark = [pytest.mark.unit]  ← no git_repo marker
```

## Expected

Add `pytest.mark.git_repo` to the pytestmark list.

## Labels

DIRECTIVE_013
```

---

### Issue A-4 — `tests/status/test_bootstrap.py`

**Title:** `[DIRECTIVE_013] test_bootstrap.py: missing git_repo pytestmark`

**Body:**
```markdown
## Summary

`tests/status/test_bootstrap.py` exercises bootstrap logic that interacts with git-tracked
feature directories but lacks the `git_repo` marker.

Identified during: `org-doctrine-profile-integrity-activation-closure-01KT1TV1` close-out (WP06/T021).

## Current state

```bash
grep pytestmark tests/status/test_bootstrap.py
# → pytestmark = [pytest.mark.unit]  ← no git_repo marker
```

## Expected

Add `pytest.mark.git_repo` to the pytestmark list.

## Labels

DIRECTIVE_013
```

---

## B. Upstream `coordination.status_service` + `lifecycle_events` Dead-Symbol Debt {#upstream-status-service-debt}

### Issue B-1 — Upstream dead-symbol allowlist debt (status_service + lifecycle_events)

**Title:** `[DIRECTIVE_013] upstream dead symbols: specify_cli.coordination.status_service (5) + status.lifecycle_events (2) have no live callers`

**Body:**
```markdown
## Summary

Two groups of upstream public symbols landed on `upstream/main` via PR #1614 with no live
callers in the spec-kitty codebase. They are currently tracked in
`tests/architectural/_baselines.yaml` as:

- `category_c_upstream_status_service: 5` — five symbols under
  `specify_cli.coordination.status_service` (no direct importer on the import graph).
- The original two `status.lifecycle_events` symbols
  (`mission_event_log_path`, `read_lifecycle_events`) were removed from `__all__`
  in the close-out branch (org-doctrine WP04); however the upstream `status_service`
  group remains.

These are **not** introduced by the org-doctrine mission — they pre-exist on
`upstream/main` — but they surface in the close-out branch via the upstream rebase
and must be resolved before the baseline can shrink.

## Required action

One of:
1. Wire the 5 `coordination.status_service` symbols to a live call site, OR
2. Remove them from `__all__` / prune the dead code, AND
3. Remove or reduce `category_c_upstream_status_service` in `_baselines.yaml`.

## Context

- Allowlist entry added: `tests/architectural/_baselines.yaml::category_c_upstream_status_service`
- Allowlist comment: "5 pre-existing upstream specify_cli.coordination.status_service public symbols
  (landed on upstream/main via #1614, no live caller there)".

## Labels

DIRECTIVE_013
```

---

## C. Deferred FR-012 — `doctor.py` God-Module Split {#fr-012-doctor-py-split}

### Issue C-1 — `doctor.py` health-render helpers should move to `_doctrine_health.py`

**Title:** `[DIRECTIVE_013] doctor.py god-module: health-render helpers (~144 lines) should move beside _doctrine_health.py`

**Body:**
```markdown
## Summary

`src/specify_cli/cli/commands/doctor.py` grew by +454 lines during the
`org-doctrine-profile-integrity-activation-closure-01KT1TV1` mission (FR-008/FR-009
profile-diagnostic rendering, I-10 from adversarial review debrief). The health-render
helpers at approximately lines 1919–2062 are self-contained and belong beside
`_doctrine_health.py`.

This is **deferred** per the mission's adversarial review finding I-10: "Defer."
No refactor was attempted in this mission; the issue is filed for tracking per
DIRECTIVE_013.

## Scope of change

- Extract health-render helpers from `doctor.py` into a new module (e.g. `_profile_health_render.py`)
  alongside `_doctrine_health.py`.
- Update `doctor.py` to import from the new module.
- No behaviour change.

## Risk

Low — pure extraction; no logic change.

## Source

Adversarial review finding I-10 from debrief:
`kitty-specs/org-doctrine-profile-integrity-activation-closure-01KT1TV1/adversarial-review-debrief.md`

## Labels

DIRECTIVE_013
```

---

## D. Deferred FR-013 — Provenance Typing (`_tag_source` Generic Refactor) {#fr-013-provenance-typing}

### Issue D-1 — `_tag_source` should use a generic typed wrapper instead of object.__setattr__ sidecar

**Title:** `[DIRECTIVE_013] merge.py: _tag_source provenance sidecar should use a typed Provenanced[T] wrapper`

**Body:**
```markdown
## Summary

`src/doctrine/drg/merge.py::_tag_source` (line 191) attaches a `provenance` attribute to
frozen Pydantic models via `object.__setattr__(obj, "provenance", ...)`. This is the root
cause of the 4 strict-mypy errors identified in adversarial review finding I-3:
`_tag_source(obj: BaseModel) -> BaseModel` loses the concrete type, feeding
`dict[str, DRGNode]` / `list[DRGEdge]` containers.

The docstring at line 209 notes:

    .. note:: T013 (FR-013) — provenance sidecar typing.
    ...
    the typed-provenance refactor is deferred to a close-out WP, so the typed-provenance
    refactor is deferred to a future mission.

This issue is filed per DIRECTIVE_013 for tracking.

## Proposed fix

Make `_tag_source` generic:

```python
from typing import TypeVar
_ModelT = TypeVar("_ModelT", bound=BaseModel)

def _tag_source(obj: _ModelT, source: str) -> _ModelT:
    ...
```

Zero runtime change; clears all 4 mypy errors.

## Alternatively

Introduce a `Provenanced[T]` dataclass wrapper that carries the concrete type and
provenance string, replacing the sidecar pattern entirely.

## Source

- Adversarial review finding I-3 + I-11 from debrief:
  `kitty-specs/org-doctrine-profile-integrity-activation-closure-01KT1TV1/adversarial-review-debrief.md`
- Docstring note at `src/doctrine/drg/merge.py:209`

## Labels

DIRECTIVE_013
```

---

## Reference Index

| Anchor | Issue title (short) | Disposition |
|--------|---------------------|-------------|
| `#git-repo-marker-gaps` (A-1..A-4) | 4 missing `git_repo` pytestmarks | **ABSORBED** — fixed in commit `7cdb3f5c5` |
| `#upstream-status-service-debt` (B-1) | Upstream dead symbols: status_service (5) | **FILED** — #1622 |
| `#fr-012-doctor-py-split` (C-1) | doctor.py god-module split | **FILED** — #1623 |
| `#fr-013-provenance-typing` (D-1) | `_tag_source` provenance sidecar typing | **FILED** — #1624 |

All filed items labeled `deferred` + `priority:P3` (no `DIRECTIVE_013` label exists upstream; the token is carried in the issue title/body). None block this mission's merge.
