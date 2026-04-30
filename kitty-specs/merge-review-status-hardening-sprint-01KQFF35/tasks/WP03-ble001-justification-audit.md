---
work_package_id: WP03
title: BLE001 suppression justification audit
dependencies: []
requirement_refs:
- FR-012
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
agent: claude
history:
- date: '2026-04-30'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/helpers.py
- src/specify_cli/cli/commands/charter.py
- src/specify_cli/cli/commands/materialize.py
- src/specify_cli/cli/commands/tracker.py
- src/specify_cli/cli/commands/mission_type.py
- src/specify_cli/cli/commands/charter_bundle.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Every `# noqa: BLE001` suppression in `src/specify_cli/cli/commands/` and `src/specify_cli/cli/helpers.py` must carry an inline justification comment explaining why the exception swallow is safe. Suppressions that cannot be justified should be fixed (narrower exception type or propagating the exception).

`src/specify_cli/auth/` suppressions are already annotated and require no changes.
`src/specify_cli/cli/commands/merge.py` is owned by WP01 and not in scope here.

## Context

BLE001 (blind exception catch) is a ruff rule for bare `except Exception` or `except Exception as e` where `e` is unused. Suppressing it in security-adjacent paths (`auth/`, CLI commands that handle credentials) without explanation makes security audits harder and obscures whether the swallow is intentional.

The goal is not to remove suppressions — most are legitimately needed for robustness. The goal is to document WHY each one is safe so a future reader can verify the reasoning without re-deriving it.

**Pattern for justification**:
- Bad: `except Exception:  # noqa: BLE001`
- Good: `except Exception:  # noqa: BLE001 — fail-open on optional UI rendering; exception is logged above`

**Files with bare suppressions** (from grep at plan time):
- `src/specify_cli/cli/helpers.py:65,259,262` — 3 suppressions
- `src/specify_cli/cli/commands/charter.py:81,127,246,249,318,982` — 6 suppressions
- `src/specify_cli/cli/commands/materialize.py:110` — 1 suppression
- `src/specify_cli/cli/commands/tracker.py:103,120` — 2 suppressions
- `src/specify_cli/cli/commands/mission_type.py:339` — 1 suppression
- `src/specify_cli/cli/commands/charter_bundle.py:251,270` — 2 suppressions

**Important**: Line numbers may have shifted since plan time. Always re-run the grep before editing.

## Branch Strategy

- **Planning branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: resolved by `spec-kitty agent action implement WP03 --agent claude`

---

## Subtask T015 — Annotate `cli/helpers.py`

**Purpose**: Add justification to the 3 bare BLE001 suppressions in `src/specify_cli/cli/helpers.py`.

**Steps**:
1. Run: `grep -n "noqa: BLE001" src/specify_cli/cli/helpers.py`
2. For each match:
   - Read 10 lines of context above and below.
   - Determine what the `except Exception` is catching and why swallowing is safe.
   - Add a short explanation after `BLE001`: `# noqa: BLE001 — <reason>`
3. Common patterns and appropriate justifications:
   - Wrapping optional telemetry/analytics: `— telemetry must never crash the CLI`
   - Wrapping optional display logic: `— UI rendering is best-effort; failure is non-fatal`
   - Wrapping config reads: `— config may be absent or malformed; fall back to default`
4. If a suppression genuinely masks an error that should propagate (e.g., it would silently swallow a KeyboardInterrupt), remove the suppression instead and let it propagate.

**Files**: `src/specify_cli/cli/helpers.py`

**Validation**: `grep "noqa: BLE001" src/specify_cli/cli/helpers.py` — each line has text after `BLE001`.

---

## Subtask T016 — Annotate `cli/commands/charter.py`

**Purpose**: Add justification to the 6 bare BLE001 suppressions in `charter.py`.

**Steps**:
1. Run: `grep -n "noqa: BLE001" src/specify_cli/cli/commands/charter.py`
2. For each match, read context and add justification.
3. Charter commands typically suppress exceptions around:
   - SaaS network calls: `— SaaS unavailable; fall back to local operation`
   - Evidence gathering: `— evidence source unreachable; proceed with available data`
   - Synthesis steps: `— synthesis failure is non-fatal; continue with partial result`
   - CLI output formatting: `— output formatting must not break the interview flow`
4. For the line at ~982 (likely inside a loop), note if it's swallowing per-item errors in a collection — that pattern is usually safe: `— per-item failure must not abort the entire synthesis pass`.

**Files**: `src/specify_cli/cli/commands/charter.py`

---

## Subtask T017 — Annotate `materialize.py`, `tracker.py`, `mission_type.py`

**Purpose**: Add justification to the 4 bare suppressions across these three files.

**Steps**:
1. Run grep on each:
   ```bash
   grep -n "noqa: BLE001" src/specify_cli/cli/commands/materialize.py
   grep -n "noqa: BLE001" src/specify_cli/cli/commands/tracker.py
   grep -n "noqa: BLE001" src/specify_cli/cli/commands/mission_type.py
   ```
2. Read context and add justifications:
   - `materialize.py:110`: likely wraps a template rendering step — `— template rendering failure is non-fatal; skip and continue`
   - `tracker.py:103,120`: likely wraps tracker API calls — `— tracker API may be unavailable; CLI must remain functional`
   - `mission_type.py:339`: likely wraps an optional metadata read — determine from context

**Files**: `src/specify_cli/cli/commands/materialize.py`, `src/specify_cli/cli/commands/tracker.py`, `src/specify_cli/cli/commands/mission_type.py`

---

## Subtask T018 — Annotate `charter_bundle.py`

**Purpose**: Add justification to the 2 bare suppressions in `charter_bundle.py`.

**Steps**:
1. Run: `grep -n "noqa: BLE001" src/specify_cli/cli/commands/charter_bundle.py`
2. Read context for lines ~251 and ~270. Charter bundle typically wraps:
   - File bundle I/O: `— bundle file may be missing or corrupted; skip and continue`
   - Per-item processing: `— per-bundle-item failure must not abort the full bundle export`
3. Add appropriate justification.

**Files**: `src/specify_cli/cli/commands/charter_bundle.py`

---

## Subtask T019 — End-to-end ruff verification

**Purpose**: Confirm all suppressions are correctly annotated and ruff passes.

**Steps**:
1. Run: `grep -rn "noqa: BLE001" src/specify_cli/cli/helpers.py src/specify_cli/cli/commands/`
2. Verify EVERY match has text after `BLE001` on the same line. If any bare suppressions remain, go back and annotate them.
3. Run: `uv run ruff check src/specify_cli/cli/`
4. Confirm zero errors. If ruff reports new errors introduced by your edits, fix them.
5. Run: `uv run mypy --strict src/specify_cli/cli/helpers.py src/specify_cli/cli/commands/charter.py src/specify_cli/cli/commands/materialize.py src/specify_cli/cli/commands/tracker.py src/specify_cli/cli/commands/mission_type.py src/specify_cli/cli/commands/charter_bundle.py`
6. Confirm zero type errors (justification comments do not introduce type issues).

**Files**: all files modified in T015-T018

---

## Definition of Done

- [ ] `grep "noqa: BLE001" src/specify_cli/cli/helpers.py src/specify_cli/cli/commands/` — every match has justification text after `BLE001`
- [ ] No suppressions were left bare (re-run grep to confirm)
- [ ] `uv run ruff check src/specify_cli/cli/` passes with zero errors
- [ ] `uv run mypy --strict` passes on all modified files
- [ ] Auth directory suppressions were NOT modified (not in scope)
- [ ] `merge.py` suppressions were NOT modified (owned by WP01)

## Reviewer Guidance

- Run `grep -rn "noqa: BLE001" src/specify_cli/cli/` and scan every line. Any line without text after `BLE001` is a miss.
- Spot-check 3-4 justifications for accuracy: do they actually explain WHY the swallow is safe, or are they just renaming the exception? A justification like `— exception caught` is not sufficient.
- No tests needed for this WP — the grep + ruff + mypy checks are the validation surface.
