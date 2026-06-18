---
work_package_id: WP01
title: Canonical safe-segment validator + primitive wiring
dependencies: []
requirement_refs:
- FR-001
- FR-004
- NFR-002
- NFR-003
- NFR-006
tracker_refs:
- '#2022'
planning_base_branch: feat/canonical-seams-path-trust-guard-capability
merge_target_branch: feat/canonical-seams-path-trust-guard-capability
branch_strategy: Planning artifacts for this mission were generated on feat/canonical-seams-path-trust-guard-capability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/canonical-seams-path-trust-guard-capability unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3672923"
history:
- 2026-06-17 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/paths.py
create_intent:
- tests/specify_cli/core/test_safe_path_segment.py
- tests/specify_cli/missions/test_read_path_resolver_validation.py
execution_mode: code_change
owned_files:
- src/specify_cli/core/paths.py
- src/specify_cli/missions/_read_path_resolver.py
- tests/specify_cli/core/test_safe_path_segment.py
- tests/specify_cli/missions/test_read_path_resolver_validation.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before any code, load the implementer profile and the binding contracts. Run:

```
/ad-hoc-profile-load python-pedro
```

Then read, in this order:
1. `kitty-specs/canonical-seams-path-trust-guard-capability-01KVBBT6/spec.md` — **FR-001, FR-004, NFR-002,
   NFR-006** and **C-001** (bind to canonical seam, no parallel mechanism).
2. `kitty-specs/canonical-seams-path-trust-guard-capability-01KVBBT6/research.md` — **decision D-1** (general
   safe-segment validator in `core/paths.py`, raise `ValueError`) and the validator census **§(a)** (3 validators
   here; a 4th — `review/cycle.py` — is in `plan.md` → Post-Planning Brownfield Check, and is WP02's concern, not
   this WP's).
3. `kitty-specs/canonical-seams-path-trust-guard-capability-01KVBBT6/contracts/seam-signatures.md` — the
   `assert_safe_path_segment` contract.

## Objective

Create the **single canonical safe-path-segment validator** in `src/specify_cli/core/paths.py` and wire it into
the two read primitives so all ~75–143 path-assembly callers inherit validation. This is the seam WP02 and WP04
delegate to — **it lands first**. The win: the next would-be path-traversal bypass becomes a test failure at the
authority, not a silent bad path.

**This is a general *segment* validator, not slug-only** — `coordination/transaction.py::_validate_safe_segment`
applies the same check to `mission_id` and `mid8` too (WP02 migrates those). Name it for what it does:
`assert_safe_path_segment(value: str) -> str`.

## Subtasks

### T001 — TDD: union-of-real-format-slugs + traversal-reject tests (RED first)
**Purpose:** pin NFR-006 (no regression on real values) and the traversal guard BEFORE implementing.
Create `tests/specify_cli/core/test_safe_path_segment.py`:
- **Accept (the union — every currently-valid real-format value MUST pass):**
  - full 26-char ULID, e.g. `01KVBBT6FEQ01NHNSQD7X8JTPE`
  - `<slug>-<mid8>` dir name, e.g. `canonical-seams-path-trust-guard-capability-01KVBBT6`
  - numeric-prefix slug, e.g. `034-feature-status-state-model`
  - bare mid8, e.g. `01KVBBT6`
  - simple kebab, e.g. `my-feature`
- **Reject (traversal guard — MUST raise `ValueError`):** `""`, `"   "`, `"."`, `".."`, `"a/b"`, `"a\\b"`,
  `"../escape"`, a non-ASCII value (e.g. `"naïve"`), a leading/trailing-slash value, **and the dotted-traversal
  forms `"..foo"`, `"foo.."`, `"a..b"`, `".hidden"`** (these are NOT in the literal `{".", ".."}` set and a lazy
  grammar that only special-cases the two literal tokens would wrongly ACCEPT them — the squad flagged this as the
  gaming path). Assert rejection of ANY value whose stripped form contains `..` as a substring OR begins with `.`.
- Assert the raised type is `ValueError` and the message names a "safe path segment".
Run it — it MUST fail (no validator yet). Paste the red output into the handoff note.

**Dot-policy decision (state it explicitly in the prompt + a code comment):** today `merge.py` rejects dots
(`^[A-Za-z0-9_-]+$`) while `transaction.py` accepts interior dots (`^[A-Za-z0-9][A-Za-z0-9._-]*$`). The canonical
grammar adopts the **interior-dot-allowed** form (so transaction's real accepts survive) BUT rejects leading-dot
and any `..` substring (traversal guard). This **widens** merge.py's slug acceptance to allow interior dots — that
is intentional; confirm (and note in the handoff) that no caller relies on merge.py rejecting a dotted slug.

### T002 — Implement `assert_safe_path_segment` in core/paths.py
**Purpose:** the authority. Reconcile the three existing regexes into one that preserves the traversal guard and
admits every real-format value.
- Existing regexes (research.md §(a)): merge `^[A-Za-z0-9_-]+$` (no dots), transaction `^[A-Za-z0-9][A-Za-z0-9._-]*$`
  (dots ok, anchored first char), aggregate `^[A-Za-z0-9_-]+$`. `KEBAB_CASE_PATTERN` is a subset of all.
- The reconciled grammar MUST: reject empty/whitespace, `.`, `..`, any `/` or `\`, non-ASCII; and accept the
  union in T001. A safe choice: strip, then reject the explicit traversal tokens, then `fullmatch` a single
  anchored ASCII segment pattern that admits `[A-Za-z0-9]` plus `._-` interior (dots are needed by transaction's
  existing accepts — but `.`/`..`-only and any `/`/`\` are already rejected). **Return the validated value.**
- Signature exactly: `def assert_safe_path_segment(value: str) -> str:` raising `ValueError`.
- Keep complexity ≤ 15; no `# noqa`/`# type: ignore`.
- Add a module constant for the compiled regex (S1192 — no inline literal reuse).

### T003 — Wire the validator into the read primitives
**Purpose:** inheritance — every caller of the primitives is now guarded (NFR-002), WITHOUT re-routing callers
(C-007). In `src/specify_cli/missions/_read_path_resolver.py`:
- Call `assert_safe_path_segment(mission_slug)` inside `primary_feature_dir_for_mission` (~:397) before composing
  `… / KITTY_SPECS_DIR / mission_slug`.
- In `resolve_mission_read_path` (~:226), the validator call MUST be the **first executable statement** — BEFORE
  `_resolve_existing_for_slug(...)` (~:275), which composes a directory from the raw slug. A guard placed *after*
  that composition literally satisfies "called in resolve_mission_read_path" while a malformed slug already flowed
  through path composition — that defeats NFR-002. (The squad flagged this exact gaming path.)
- Import from `specify_cli.core.paths`. NOTE: `primary_feature_dir_for_mission` already imports `get_main_repo_root`
  **locally** (function-body import at ~:413) — a deliberate cycle-break. Match that precedent: prefer a
  function-local import of `assert_safe_path_segment` over a module-top import (the squad flagged module-top as a
  possible cycle). Do NOT change the primitives' signatures or return types (behavior-preserving for valid input).

### T004 — NFR-002 test: rejection fires INSIDE the primitive (topology-true)
**Purpose:** prove the guarantee at the authority, not at a caller. Create
`tests/specify_cli/missions/test_read_path_resolver_validation.py`:
- Call `primary_feature_dir_for_mission(repo_root, "../escape")` and `resolve_mission_read_path(...)` directly with
  malformed segments; assert `ValueError`.
- **Guard-fires-before-composition assertion (un-fakeable NFR-002):** spy/monkeypatch `_resolve_existing_for_slug`
  and assert it is **never called** when `resolve_mission_read_path` is handed a malformed slug — a late-placed
  guard (after composition) fails this. This is what forces the guard to the front.
- Use a topology-true fixture: a real temp git repo, a full-ULID-bearing real-format slug for the happy path.
- Assert a valid real-format slug still returns the composed `kitty-specs/<slug>` path unchanged.

### T005 — Quality gate + no-re-routing confirmation
- `ruff check` + `mypy` clean on the two source files (complexity ≤ 15, no suppressions).
- Confirm (and note in the handoff) that NO caller of the primitives was re-routed or had its signature changed —
  only the two primitive bodies gained a validation call (C-007 / NFR-001).
- Run the new tests + the existing `_read_path_resolver` suite green.

## Branch Strategy

Planning base: `feat/canonical-seams-path-trust-guard-capability`. Merge target: `feat/canonical-seams-path-trust-guard-capability`
(PR → main). Execution worktrees are allocated per the computed lane in `lanes.json` during
`/spec-kitty.implement`; this WP has no dependencies so it starts the first lane.

## Definition of Done

- [ ] `assert_safe_path_segment` exists in `core/paths.py`, raises `ValueError`, complexity ≤ 15, no suppressions.
- [ ] Both read primitives call it; no caller re-routed; signatures unchanged.
- [ ] T001 union test green (every real-format value validates) + traversal-reject cases green.
- [ ] T004 proves rejection at the primitive directly (topology-true).
- [ ] `ruff`+`mypy` clean; new + existing resolver suites green.

## Risks / reviewer guidance

- **Regex reconciliation is the real risk.** A too-strict grammar rejects a real on-disk mission (NFR-006
  regression); a too-loose one drops the traversal guard. The reviewer MUST verify the union test covers ULID +
  `<slug>-<mid8>` + numeric-prefix + bare mid8, and that `.`/`..`/`/`/`\`/non-ASCII all reject.
- **Circular import:** importing `assert_safe_path_segment` into `_read_path_resolver` must not cycle — `core.paths`
  is already a dependency of that module, so import at module top is fine; if a cycle appears, import locally
  inside the function (with a one-line rationale), not via a new shim.
- Reviewer: confirm this is `assert_safe_path_segment` (general segment) not a slug-only name — WP02 reuses it for
  `mission_id`/`mid8`.

## Activity Log

- 2026-06-17T20:15:44Z – claude:sonnet:python-pedro:implementer – shell_pid=3631470 – Assigned agent via action command
- 2026-06-17T20:25:55Z – claude:sonnet:python-pedro:implementer – shell_pid=3631470 – Ready for review: assert_safe_path_segment in core/paths.py + wired into both primitives; ruff+mypy exit 0; 157 tests green (new+existing resolver suite)
- 2026-06-17T20:27:00Z – claude:opus:reviewer-renata:reviewer – shell_pid=3672923 – Started review via action command
- 2026-06-17T20:35:31Z – user – shell_pid=3672923 – Review passed (opus/reviewer-renata): code-clean; matrix verdicts filled
