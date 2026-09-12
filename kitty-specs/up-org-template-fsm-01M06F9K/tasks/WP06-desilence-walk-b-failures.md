---
work_package_id: WP06
title: De-silence Walk B's swallowed FSM template-load failures
dependencies:
- WP04
requirement_refs:
- C-005
- FR-010
- FR-011
- NFR-003
planning_base_branch: up-org-template-fsm
merge_target_branch: up-org-template-fsm
branch_strategy: Planning artifacts for this mission were generated on up-org-template-fsm. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into up-org-template-fsm unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
- T034
- T035
- T036
phase: Phase 3 - Diagnostics
history:
- at: '2026-08-17T00:02:22Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/runtime/next/runtime_bridge_io.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/runtime/next/runtime_bridge_io.py
- tests/runtime/test_bridge_io.py
role: ''
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP06 – De-Silence Walk B's Swallowed FSM Template-Load Failures

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any
user-defined profile), and behave according to its guidance before parsing the rest of this
prompt.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for
`task_type: implement` and `authoritative_surface: src/runtime/next/runtime_bridge_io.py`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting if this WP was returned from review.
Address every feedback item and update the Activity Log as you go.

---

## ⚠️⚠️ FILE COLLISION WITH WP04 — READ BEFORE TOUCHING `runtime_bridge_io.py`

**WP04 also edits `src/runtime/next/runtime_bridge_io.py`.** This is the single `owned_files`
overlap in the whole mission (`plan.md`'s "owned_files note"). It is a **file collision, not a
functional dependency**:

- **WP04** edits `_build_discovery_context` and `_runtime_template_key`'s `project_tiers`
  construction.
- **This WP (WP06)** edits `_template_key_for_file` and `_resolve_runtime_template_in_root` —
  different functions in the same file.

This WP's dependency on WP04 exists **specifically so the two WPs never edit this file
concurrently**, not primarily because this WP's diagnostic logic has a deep functional need for
WP04's tier logic (though FR-011's Acceptance Scenario 1 — "a malformed `mission.yaml` at the org
tier" — does need the org tier to exist as a meaningful test fixture, which WP04 provides). **Do
not treat this as evidence WP04 and WP06 could otherwise run in parallel** — they cannot, because
they touch the same file. Confirm WP04 is merged/approved before starting this WP.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

This WP is **IC-06** from `plan.md`'s Implementation Concern Map. Walk A
(`discovery.py:discover_missions_with_warnings`) already produces a `DiscoveryWarning` on a
template load failure. Walk B (`runtime_bridge_io.py:_template_key_for_file`) currently swallows
the identical failure class via a bare `except Exception: return None`, and its caller
(`_runtime_template_key`) silently falls through to returning the bare `mission_type` string with
no warning anywhere.

**Success criteria** (FR-010, FR-011, SC-005):
- A malformed org-tier `mission.yaml` produces a named warning identifying the offending path and
  tier (through the same `DiscoveryWarning`-shaped channel Walk A already uses) — not silence.
- A non-built-in tier shipping both `mission.yaml` and `mission-runtime.yaml` for the same key
  produces a named diagnostic — but the four existing **built-in** mission directories (`plan`,
  `research`, `documentation`, `software-dev`), which already legitimately ship both files, MUST
  continue producing **zero** diagnostics.

## Context & Constraints

Read before starting:
- `kitty-specs/up-org-template-fsm-01M06F9K/spec.md` — User Story 4 (Independent Test, both
  Acceptance Scenarios), FR-010, FR-011, C-005, Key Entities (`DiscoveryWarning`).
- `kitty-specs/up-org-template-fsm-01M06F9K/plan.md` — IC-06's Purpose/Risks; the "NFR-003
  Compliance Without a Gate" section (reproduced below, same as WP04's); Plan-Time Verification's
  citations for `runtime_bridge_io.py:294-299` (`_template_key_for_file`) and `:302-319`
  (`_resolve_runtime_template_in_root`).

**This mission is dogfooded inside spec-kitty's own repository — a PUBLIC repo based on `main`.**
No host paths, no usernames, no absolute local paths in any committed file — sweep your diff before
finishing.

### NFR-003 — `src/runtime/next/**` has no automated gate for this discipline

Same discipline as WP04 (repeated here in full so this prompt is self-sufficient — a lane agent
reading only this file must see it without also reading WP04's prompt):
`tests/architectural/test_runtime_charter_doctrine_boundary.py`'s `_RUNTIME_ROOT` is hardcoded to
`src/specify_cli` and does **not** scan `src/runtime/next/**` (filed as **#3522**). A green CI run
on this WP's PR is **not evidence** that this WP's changes to `runtime_bridge_io.py` avoid a direct
`doctrine.*` import. This WP does not itself add a new `resolve_org_roots` call site (that was
WP04's job), but any code you add here that touches org-root data must still route through
`context.org_roots` or the lazy `charter.drg` facade, never a direct `doctrine.*` import. **Your PR
description MUST state explicitly** that this discipline was confirmed by manual review, not CI,
and **must name issue #3522**.

### Do not change `_runtime_template_key`'s return contract

`_runtime_template_key`'s existing fallback-to-`mission_type`-string behavior (the plain string
returned when nothing resolves) must be **preserved**. This WP adds a warning **alongside** that
fallback, not a new exception that would change the function's return type or raise where it
previously returned quietly. That would be a larger, out-of-scope behavior change.

### `_resolve_runtime_template_in_root`'s existing sidecar preference is unchanged (C-005)

`mission-runtime.yaml` outranking `mission.yaml` intra-directory is existing, correct behavior —
this WP only adds the **named diagnostic** when a non-built-in tier ships both, it does not change
which file wins.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

Implementation command (with dependencies):
```bash
spec-kitty agent action implement WP06 --agent <name>
```

## Subtasks & Detailed Guidance

### Subtask T031 – Red-first Walk B swallow test

**Purpose**: Prove the "before" state for FR-010/SC-005.

**Steps**:
1. In `tests/runtime/test_bridge_io.py`, build a fixture: a syntactically-invalid or
   schema-invalid `mission.yaml` at an org-tier position (or any tier — the swallow bug is
   position-independent; using the org tier ties the test to User Story 4's Acceptance Scenario 1).
2. Assert that (pre-fix) `_template_key_for_file` returns `None` on this fixture, and that
   `_runtime_template_key` falls through to returning the bare `mission_type` string with **zero**
   warnings recorded anywhere (no `DiscoveryWarning`-shaped object produced, no caller-visible
   diagnostic).
3. **Note the existing test**: `tests/runtime/test_bridge_io.py` already has
   `test_template_key_for_file_returns_none_on_load_failure` (currently around line 229), which
   asserts exactly this swallow behavior on a "bogus" fixture. Do not just add a new, separate
   red-first test alongside it and leave that one unchanged — after T032 lands, that existing
   test's assertion will need to be updated too (it will still return `None` from
   `_template_key_for_file` itself, most likely, since that function's *return value* contract may
   not change — only whether a warning is now also recorded. Read the existing test carefully
   before deciding exactly what changes; do not assume its assertion is simply wrong.)

**Files**: `tests/runtime/test_bridge_io.py`.

**Parallel?**: Yes, alongside drafting T033 (different function).

### Subtask T032 – Route the failure into a named diagnostic

**Purpose**: Implement FR-010.

**Steps**:
1. In `src/runtime/next/runtime_bridge_io.py:_template_key_for_file`, replace or augment the bare
   `except Exception: return None` so the failure is also routed into a named,
   `DiscoveryWarning`-shaped diagnostic — matching Walk A's existing warning channel/shape at
   `discovery.py`'s `discover_missions_with_warnings` (`DiscoveryWarning(path=..., tier=...,
   origin=..., error=...)`).
2. `_template_key_for_file` itself may need to keep returning `None` on failure (its callers may
   depend on that), but the **caller** (`_resolve_runtime_template_in_root` /
   `_runtime_template_key`) needs a way to know a warning occurred — thread it through via
   whatever mechanism keeps this WP's change additive and does not alter
   `_runtime_template_key`'s return type (see the "Do not change the return contract" constraint
   above). Consider a module-level or thread-through collection, an optional out-parameter, or
   returning a richer internal result type from `_template_key_for_file` that
   `_resolve_runtime_template_in_root`/`_runtime_template_key` unpack — pick the shape that best
   matches the existing codebase idiom in this file; do not invent a parallel warning system if a
   simpler thread-through mechanism already fits.
3. Confirm T031's test now shows a named warning identifying the offending file path and tier
   (not just "some warning happened").
4. Update the existing `test_template_key_for_file_returns_none_on_load_failure` test per T031's
   note — do not leave it silently contradicting the new behavior.

**Files**: `src/runtime/next/runtime_bridge_io.py`.

**Parallel?**: No — depends on T031.

### Subtask T033 – Red-first sidecar-pair diagnostic test

**Purpose**: Prove the "before" state for FR-011.

**Steps**:
1. Build a fixture: a **non-built-in** tier directory shipping both `mission.yaml` and
   `mission-runtime.yaml` for the same mission key.
2. Assert that (pre-fix) discovery produces **no** diagnostic for this — the existing intra-directory
   preference (`mission-runtime.yaml` wins) already resolves it silently.

**Files**: `tests/runtime/test_bridge_io.py`.

**Parallel?**: Yes, alongside T031 (different function, though same file — sequence your own
drafting to avoid merge noise per this WP's own Implementation Notes in `tasks.md`).

### Subtask T034 – Add the sidecar diagnostic

**Purpose**: Implement FR-011, scoped to non-built-in tiers only.

**Steps**:
1. In `src/runtime/next/runtime_bridge_io.py:_resolve_runtime_template_in_root`, detect when a
   directory being scanned provides **both** `mission.yaml` and `mission-runtime.yaml` sidecars for
   the same mission key.
2. Emit a named diagnostic (same `DiscoveryWarning`-shaped channel as T032, or a closely related
   shape — keep it consistent with T032's choice) **only** when this happens for a **non-built-in**
   tier. Determine "built-in" by checking whether the root being scanned is one of the four
   built-in mission directories (`src/specify_cli/missions/{plan,research,documentation,software-dev}/`
   or their resolved equivalent — check how `_resolve_runtime_template_in_root`'s caller already
   distinguishes tiers, and reuse that distinction rather than re-deriving "is this built-in" from
   scratch).
3. Do **not** raise an error — this is a diagnostic, not a hard failure; the existing
   `mission-runtime.yaml`-wins preference (C-005) is unchanged.
4. Confirm T033's test now shows the diagnostic firing.

**Files**: `src/runtime/next/runtime_bridge_io.py`.

**Parallel?**: No — depends on T033.

### Subtask T035 – Regression test: built-in directories stay silent

**Purpose**: The main correctness risk for FR-011 (per `plan.md`'s IC-06 risk note) — a positive
test alone is not sufficient; this is the explicit negative-case guard.

**Steps**:
1. For each of the four built-in mission directories
   (`src/specify_cli/missions/{plan,research,documentation,software-dev}/`, which already ship both
   `mission.yaml` and `mission-runtime.yaml`), run discovery through `_resolve_runtime_template_in_root`
   (or the full `_runtime_template_key` path) and assert **zero** diagnostics are produced — User
   Story 4, Acceptance Scenario 2's negative case.
2. This must genuinely exercise all four directories, not just one representative — the risk is
   specifically that the diagnostic might fire for a built-in tier by mistake.

**Files**: `tests/runtime/test_bridge_io.py`.

**Parallel?**: No — depends on T034.

### Subtask T036 – NFR-003 compliance confirmation

**Purpose**: Close out the review-based NFR-003 verification for this mission's `src/runtime/next/**`
changes (WP04's changes plus this WP's).

**Steps**:
1. Run:
   ```bash
   grep -n "^from doctrine\|^    from doctrine" \
     src/runtime/next/_internal_runtime/discovery.py \
     src/runtime/next/runtime_bridge_io.py
   ```
2. Confirm the only doctrine-adjacent imports present are the sanctioned `from charter.drg import
   resolve_org_roots` lazy pattern (or none, if this WP itself adds no such import). If this grep
   turns up a direct `doctrine.*` import in either file, stop and fix it before finishing this WP —
   do not let it ship silently just because no gate would catch it.
3. State this confirmation explicitly in the PR description, and link or name issue #3522.

**Files**: None (verification-only subtask; PR-description text is the deliverable).

**Parallel?**: No — do this last, as the mission's final review-gate confirmation for this
discipline.

## Test Strategy

```bash
pytest tests/runtime/test_bridge_io.py -q
```
`src/runtime/next/*` is an enforced diff-coverage critical path
(`.github/workflows/ci-quality.yml:3349`, `--fail-under=90` on changed lines).

## Risks & Mitigations

- **The built-in vs. non-built-in distinction is the main correctness risk** — T035 is the explicit
  regression guard; do not consider FR-011 done with only T033/T034 (positive case).
- **Return-contract risk**: do not let the diagnostic-threading mechanism (T032) accidentally
  change `_runtime_template_key`'s return type or raise where it previously returned the bare
  `mission_type` string.
- **File collision with WP04** — see the callout at the top of this prompt.

## Review Guidance

A reviewer should confirm:
1. `_runtime_template_key`'s fallback-to-`mission_type`-string return contract is unchanged.
2. T035 genuinely exercises all four built-in directories, not a subset.
3. The existing `test_template_key_for_file_returns_none_on_load_failure` test was updated
   consistently with T032's change, not left contradicting it.
4. `_resolve_runtime_template_in_root`'s sidecar preference (`mission-runtime.yaml` wins) is
   unchanged — only the diagnostic is new.
5. T036's grep was actually run and its result stated in the PR description, naming #3522.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Format**: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>`

- 2026-08-17T00:02:22Z – system – Prompt created.
