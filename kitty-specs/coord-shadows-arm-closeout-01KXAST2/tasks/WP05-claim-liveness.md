---
work_package_id: WP05
title: "IC-LIVENESS — promote the liveness helper into core + wire the stale indicator"
dependencies: []
requirement_refs:
- FR-007
- NFR-004
tracker_refs: []
planning_base_branch: rework/ray-cluster-aggregation
merge_target_branch: rework/ray-cluster-aggregation
branch_strategy: Planning artifacts for this mission were generated on rework/ray-cluster-aggregation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rework/ray-cluster-aggregation unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
agent: "claude:sonnet:python-pedro:implementer"
shell_pid: "4168956"
history:
- created at planning (tasks) — parallel lane; promotes sync/daemon._is_process_alive into core/process_liveness.py and wires the stale indicator
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/process_liveness.py
create_intent:
- src/specify_cli/core/process_liveness.py
- tests/specify_cli/core/test_process_liveness.py
execution_mode: code_change
model: sonnet
owned_files:
- src/specify_cli/core/process_liveness.py
- src/specify_cli/core/stale_detection.py
- src/specify_cli/sync/daemon.py
- tests/specify_cli/core/test_process_liveness.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md) FR-007 +
NFR-004 + Scenario 3 + the edge case "a `shell_pid` that is unparseable, absent, or belongs to a
recycled PID → liveness check is conservative and never crashes", [plan.md](../plan.md)
§IC-LIVENESS (the explicit "**Do NOT import it from `sync/daemon` into `core/` and `lanes/`**"
warning — that would invert layering, dragging a 1500-line socket/HTTPServer module into a
low-level indicator), C-002 in spec.md (`core/process_liveness.is_process_alive` is the one
canonical liveness definition, promoted from `sync/daemon._is_process_alive`; no
`core → sync` layering inversion), and [research.md](../research.md) "Decision: reuse
`sync/daemon._is_process_alive`, do not add `os.kill`". **FR-008 (an allocator-side liveness
consult) has been withdrawn from this mission — WP04 does not import from this module and there
is no cross-WP relationship with WP04.** This module's actual consumers are
`core/stale_detection.py` (the sole NEW consumer, the staleness indicator wired in T025) and
`sync/daemon.py` (its existing call sites, repointed in T024, plus a thin re-export alias for the
out-of-mission `dashboard/lifecycle.py` importer — see T024's hard requirement). Do not let
speculative future consumers drive scope creep into this file beyond the one public
`is_process_alive`.

## Objective
A cross-platform, edge-hardened psutil liveness helper already exists as
`sync/daemon._is_process_alive` (~:320) — it correctly handles `NoSuchProcess` (→ `False`),
`AccessDenied` (→ `True`, conservative: cannot prove death), and any other exception (bare
`except Exception` → `False`), and never raises (this already satisfies NFR-004). It is,
however, private to a 1500-line daemon module that owns sockets and an `HTTPServer` — importing
it directly into `core/` or `lanes/` would invert the dependency layering those packages are
supposed to sit below. This WP **promotes** the helper verbatim into a new, dependency-light
`src/specify_cli/core/process_liveness.py` module (public `is_process_alive(pid: int) -> bool`,
importing only `psutil` + stdlib — no `specify_cli` imports, so no cycle risk), repoints
`sync/daemon.py` to import from the new home, and wires `core/stale_detection.py` (today
git-commit-timestamp based) to suppress the "stale" flag when the WP's claiming `shell_pid`
(read via the existing `task_utils` frontmatter readers) is a live process.

## Subtasks

### T023 — Create `core/process_liveness.py` with the promoted helper
Create `src/specify_cli/core/process_liveness.py`. Move the **body** of
`sync/daemon._is_process_alive` (currently ~:320, using only `psutil.Process(pid).is_running()`
with `except psutil.NoSuchProcess: return False`, `except psutil.AccessDenied: return True`, and
a final bare `except Exception: return False`) verbatim into a new public function:

```python
"""Cross-platform process liveness — the single canonical is-alive check (C-002).

Promoted from ``sync/daemon._is_process_alive`` so ``core`` and ``lanes`` can consult
process liveness without depending on the daemon's socket/HTTPServer machinery
(layering — do not import this from ``sync``). Never raises: NFR-004 requires a
conservative "not provably alive" (False) or "cannot prove dead" (True, AccessDenied)
result for every input, including absent, unparseable, dead, or recycled PIDs.
"""

from __future__ import annotations

import psutil


def is_process_alive(pid: int) -> bool:
    ...  # body moved verbatim from sync/daemon._is_process_alive
```

Import **only** `psutil` and stdlib — no `specify_cli.*` imports of any kind, so `core` stays the
lowest layer this module's consumers — `core/stale_detection.py` (the indicator) and
`sync/daemon.py` (via its repointed call sites and re-export alias) — can depend on without a
cycle. (WP04/the allocator is not a consumer; FR-008 was withdrawn.)
Do not "improve" the exception handling while moving it — the existing NoSuchProcess/AccessDenied/
bare-Exception triage is exactly what NFR-004 requires; a rewrite risks subtly changing the
conservative-default polarity.

### T024 — Repoint `sync/daemon.py`
Delete the local `_is_process_alive` function definition from `sync/daemon.py` (currently
~:320) and add `from specify_cli.core.process_liveness import is_process_alive`. Update all three
existing call sites in this file (~:628, ~:1226, ~:1280 — confirm exact lines at implementation
time, they may have shifted) to call `is_process_alive(...)` directly.

**HARD REQUIREMENT**: `sync/daemon.py` MUST keep re-exporting `_is_process_alive` as a thin
module-level alias — `_is_process_alive = is_process_alive` — regardless of whether the internal
call sites are updated to the new name or left referencing the old one. This is not optional
style guidance: `dashboard/lifecycle.py` (out of this mission's scope — do not touch it) does
`from specify_cli.sync.daemon import _is_process_alive`. Moving the symbol without leaving this
alias in place breaks that import at runtime. Add an explicit check (either a small unit test or
an assertion in `T026`'s test file) that `from specify_cli.sync.daemon import _is_process_alive`
still resolves and returns the promoted `core.process_liveness.is_process_alive` function after
this change — do not just eyeball the diff.

Do not keep both a private function **body** AND the new import (that would be the exact
parallel-implementation C-002 forbids) — the alias is a re-export binding, not a redefinition.

### T025 — Wire `core/stale_detection.py` to suppress "stale" for a live claim
`check_wp_staleness` (`core/stale_detection.py` ~:218-283) currently judges staleness **purely**
on git-commit-timestamp idle time via `get_last_meaningful_commit_time` — it has no awareness of
the WP's claiming process at all. Add a liveness check that runs before (or alongside) the
timestamp heuristic: read the claiming `shell_pid` via the **existing** `task_utils` frontmatter
reader (`specify_cli.task_utils.support.WorkPackage.shell_pid` — a property that already calls
`extract_scalar(self.frontmatter, "shell_pid")`; DO NOT re-derive a new frontmatter parse — reuse
this exact reader, per C-002's explicit "no new `os.kill` parse" and the general canonical-sources
rule). If a `shell_pid` is present, parseable as an int, and `is_process_alive(pid)` returns
`True`, the WP must **not** be flagged stale (`StaleState(status="fresh", ...)`), regardless of
what the timestamp heuristic would otherwise conclude. When no `shell_pid` is recorded, it is
unparseable, or `is_process_alive` returns `False`, fall back to the existing timestamp-based
logic unchanged — the liveness check is a **suppression**, not a replacement, of the timestamp
heuristic (per Scenario 3: "a live agent spending minutes reading and planning before its first
commit" must not be falsely flagged, but a genuinely dead process with an old commit still should
be). You will likely need to thread the WP's frontmatter (or its `WorkPackage` instance) into
`check_wp_staleness` — check its current call sites (`check_doing_wps_for_staleness` at ~:295 and
above) to see what's already available there before widening the function signature.

### T026 — Tests
Create `tests/specify_cli/core/test_process_liveness.py` — the NFR-004 matrix, driven through
the **production** `is_process_alive` entry point (not by re-implementing psutil semantics in the
test):
- Absent/nonexistent PID → `False` (mock `psutil.Process` to raise `NoSuchProcess`).
- Unparseable input (if the function's type allows it reaching this path — otherwise cover this
  at the `stale_detection` call site instead, since `is_process_alive`'s signature is `pid: int`).
- Dead PID → `False`.
- `AccessDenied` (permission-restricted process, e.g. a different user's process on some
  platforms) → `True` (conservative — cannot prove it's dead).
- A generic unexpected exception from psutil → `False` (never raises out of the function).
- Assert the function **never raises** for any of the above — wrap each case in a call that would
  fail the test if an exception propagates, not just an assertion on the boolean return.

Add a `core/stale_detection.py` test (in the existing stale-detection test file, or a new
narrowly-scoped one) proving: a WP with a live `shell_pid` recorded in frontmatter is **not**
flagged stale even when its last commit is well past the staleness threshold (monkeypatch
`is_process_alive` at the import site used inside `stale_detection.py`); and a WP with a dead/no
`shell_pid` still falls back to the existing timestamp-based staleness correctly (regression
guard — this WP must not accidentally make everything "always fresh").

Run `uv run pytest tests/specify_cli/core/ -q`, `uv run ruff check
src/specify_cli/core/process_liveness.py src/specify_cli/core/stale_detection.py
src/specify_cli/sync/daemon.py tests/specify_cli/core/test_process_liveness.py`, `uv run mypy
src/specify_cli/core/process_liveness.py src/specify_cli/core/stale_detection.py`. Confirm the
dead-code/layering architectural tests (search `tests/architectural/` for any import-boundary
check on `core → sync`) stay green — this WP must not introduce a `core` → `sync` import in
either direction beyond `sync/daemon.py` importing `core/process_liveness.py` (allowed: `sync`
depending on `core` is the correct direction).

## Branch Strategy
Planning base branch and merge target branch are both `rework/ray-cluster-aggregation`;
`spec-kitty implement WP05` allocates an execution worktree per the lane computed from
`lanes.json`. No WP dependency — fully parallel with the WP01→WP02→WP03 spine and with WP04/WP06.
No cross-WP relationship with WP04 (FR-008, the prior coupling, has been withdrawn) — implement
independently.

## Definition of Done
- `core/process_liveness.py` exists with a public `is_process_alive(pid: int) -> bool`, importing
  only `psutil` + stdlib, moved verbatim (behaviorally) from `sync/daemon._is_process_alive`.
- `sync/daemon.py` imports from the new module; no duplicate liveness definition remains in
  `sync/daemon.py`; `sync/daemon.py` still re-exports `_is_process_alive` (thin alias to
  `is_process_alive`) so `dashboard/lifecycle.py`'s existing `from specify_cli.sync.daemon import
  _is_process_alive` continues to resolve.
- `core/stale_detection.py` suppresses the "stale" flag when the claiming `shell_pid` (read via
  the existing `task_utils.support.WorkPackage.shell_pid` reader) is a live process; falls back to
  the timestamp heuristic otherwise.
- NFR-004 matrix green (absent/unparseable/dead/recycled/AccessDenied never raise; conservative
  not-provably-alive default); a stale_detection test proves a live-claim WP is not flagged stale.
- `uv run pytest tests/specify_cli/core/ -q` green; `uv run ruff check` + `uv run mypy` clean,
  zero new suppressions; full `tests/architectural/` 0-failed, including any `core`→`sync`
  layering guard.

## Risks
- **Re-deriving a frontmatter parse instead of reusing `task_utils`** — the temptation to read
  `shell_pid` with a fresh regex inside `stale_detection.py` must be resisted; C-002 explicitly
  forbids a second parse. Use `WorkPackage.shell_pid` (or the lower-level `extract_scalar`
  helper it wraps) from `task_utils`.
- **Widening `check_wp_staleness`'s signature carelessly** — it currently takes
  `(wp_id, worktree_path, threshold_minutes)` with no frontmatter access; threading in a
  `shell_pid` or `WorkPackage` argument touches every call site. Check
  `check_doing_wps_for_staleness` and any CLI-surface callers before deciding the cleanest
  signature change (new optional parameter with a safe default vs. a wrapper function) — prefer
  the smallest diff that still gets the WP file/frontmatter to this function.
- **`core → sync` inversion** — the whole point of promoting the helper is to avoid this; double
  check no new import of anything under `specify_cli.sync` appears in `core/process_liveness.py`
  or `core/stale_detection.py` after this WP.

## Reviewer Guidance
Confirm: `process_liveness.py` imports only `psutil`+stdlib (grep for any `specify_cli` import in
the file — should be zero); `sync/daemon.py`'s local `_is_process_alive` body is gone, replaced by
the import; `sync/daemon.py` still re-exports `_is_process_alive` as a thin alias and `from
specify_cli.sync.daemon import _is_process_alive` (the `dashboard/lifecycle.py` import) still
resolves; `stale_detection.py` reuses `task_utils`'s existing frontmatter reader (no new regex);
the suppression is correctly a "live → not stale" override, with the timestamp fallback intact for
dead/absent claims; NFR-004 matrix genuinely never raises (check the tests assert on absence of
exception, not just return value); no `core → sync` import introduced; this module's consumers
are `stale_detection.py` and `sync/daemon.py` only — WP04/the allocator is not a consumer
(FR-008 withdrawn); ruff/mypy clean; full arch suite 0-failed.

## Activity Log
- {{TIMESTAMP}} — system — Prompt created at planning (tasks).
- 2026-07-12T11:03:55Z – claude:sonnet:python-pedro:implementer – shell_pid=4168956 – Assigned agent via action command
- 2026-07-12T12:18:24Z – user – shell_pid=4168956 – APPROVE (opus renata): core/process_liveness.py psutil-only no-cycle; daemon re-export alias (dashboard import identity-verified); stale-indicator live-claim suppression via existing task_utils read; NFR-004 matrix; 311+48 tests green; no core->sync
