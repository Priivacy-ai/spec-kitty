---
work_package_id: WP02
title: '#2758 references.yaml fail-closed preflight'
dependencies: []
requirement_refs:
- FR-005
tracker_refs:
- '#2758'
planning_base_branch: feat/doctrine-activation-freshness
merge_target_branch: feat/doctrine-activation-freshness
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-activation-freshness. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-activation-freshness unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- tests/charter/test_references_missing_failclosed.py
execution_mode: code_change
owned_files:
- src/charter/bundle.py
- src/specify_cli/cli/commands/charter/synthesize.py
- src/specify_cli/cli/commands/charter/_synthesis.py
- tests/charter/test_references_missing_failclosed.py
role: implementer
tags: []
shell_pid: "3362803"
shell_pid_created_at: "1784323485.61"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via `/ad-hoc-profile-load python-pedro` (implementer). Do not act on the persona name alone — load the YAML.

## Objective

Fix the **permanent-stale dead-end** (#2758). `compute_bundle_content_hash` hashes four files
including `references.yaml`, and returns `None` when any is absent (`bundle.py:~170-171`). But
`sync` never writes `references.yaml` (`_SYNC_OUTPUT_FILES` omits it — it is compiled only by
`charter generate`), so a synced-but-not-generated project gets a `None` that maps to `stale`
(`computer.py:~428`) and that `synthesize` **cannot self-heal**.

**Resolution (Q1, operator decision `01KXRVT2KA1Y3M4XQAYVQ3HHXF`): fail-closed preflight.**
Keep the 4-file hash. When `references.yaml` is absent at the point `synthesize` needs a
complete bundle, **fail closed** with a single actionable message naming `charter generate` —
instead of silently producing a dead-end `None`.

**Anchor convention**: line numbers are indicative — resolve by symbol name.

## Hard constraints

- **NO hash-narrowing.** Do NOT touch `bundle.py:BUNDLE_CONTENT_HASH_FILES`,
  `computer.py:_BUNDLE_FILES`, or `CANONICAL_MANIFEST.derived_files`. The narrow-to-triad fork
  was rejected to keep #2773 (references.yaml deprecation) clean — **no `references.yaml`
  stopgap**. (Q5 dual-edit is moot under this fork.)
- **NFR-002 preserve**: a **complete** bundle's `compute_bundle_content_hash` must be
  byte-identical to before this change. You are adding a guard *before* the None-return path,
  not changing the recipe.
- `computer.py` is owned by WP03 — **do not edit it**. Your preflight lives in the charter
  synthesize surface + `bundle.py`.
- **SUPPRESSION TRAP (NFR-005)**: `charter_synthesize` (`synthesize.py:~56`) already carries a
  pre-existing `# noqa: C901` (it is over-15). Land the fail-closed preflight as a **separate
  helper function**, NOT inline in `charter_synthesize` — piling logic into that function
  deepens a suppressed complexity hotspot and trips "zero new suppressions / ≤15". Treat the
  pre-existing `# noqa: C901` as **ADJACENT/OUT** (do not remove it, do not refactor
  `charter_synthesize` wholesale — that is out of this WP's scope; leave it tracked).
- **No pre-existing completeness gate to extend**: today `synthesize` only guards `charter.md`
  existence (`synthesize.py:~120`) and interview answers (`_synthesis.py:~45`). Your preflight
  is **net-new** — do not go hunting for an existing bundle-completeness checkpoint. Note also
  `_SYNC_OUTPUT_FILES` lives in `src/charter/sync.py` (the library), not the CLI `sync.py`.

## Subtasks

### T005 — Red-first repro
- Write `tests/charter/test_references_missing_failclosed.py`. Construct a project with
  `governance.yaml` + `directives.yaml` + `metadata.yaml` present but `references.yaml` absent
  (mirror the real `.kittify/charter/` layout).
- Assert the CURRENT behavior is the dead-end: `compute_bundle_content_hash` → `None`, and the
  synthesize path treats it as an un-healable stale. This test is RED against the desired
  fail-closed behavior (it will assert the actionable failure once T006 lands).

### T006 — Fail-closed preflight (as a separate helper)
- Add a **new helper** (in `bundle.py` or the synthesize surface) that checks bundle
  completeness and, when `references.yaml` is missing, raises a fail-closed error (Typer
  `Exit`/domain error) with a **single hoisted message constant**, e.g.
  `references.yaml missing — run 'spec-kitty charter generate' first`. Call it from
  `charter_synthesize` as a one-line guard — do NOT inline the logic (see suppression trap).
- Rationale it is non-circular: `synthesize` does not itself compile `references.yaml` (only
  `charter generate`/`compile_charter` does), so running synthesize can never self-heal the
  missing file — failing closed toward `charter generate` is correct.
- If a small helper in `bundle.py` is the right home for "is the bundle complete + which file
  is missing", add it there (that is your owned surface) and consume it from synthesize. Keep
  `compute_bundle_content_hash`'s own contract unchanged (still returns `None` on missing —
  the preflight makes that path unreachable in the synthesize flow).
- Keep complexity ≤15; hoist the message (used in the raise + the test).

### T007 — Tests
- Extend the T005 test: after the fix, the synthesize preflight fails closed with the
  actionable message (assert the message text via the constant).
- Add an NFR-002 assertion: a **complete** 4-file bundle hashes to a stable value unchanged by
  this WP (compute twice / compare to a pinned expectation for a fixture bundle).

### T008 — Gate
- `PWHEADLESS=1 uv run pytest tests/charter/ -q` green.
- `ruff check src/charter src/specify_cli/cli/commands/charter/synthesize.py src/specify_cli/cli/commands/charter/_synthesis.py` clean.
- `uv run mypy --strict src/charter` clean (re-verify under the project invocation, not in isolation).

## Branch Strategy

Planning base + merge target: `feat/doctrine-activation-freshness`. Worktree from `lanes.json`.
No dependencies; sequenced before WP03 among the seam concerns.

## Definition of Done

- [ ] Red-first test written and now green with the fail-closed behavior.
- [ ] Missing `references.yaml` → actionable "run `charter generate`" (hoisted constant), not dead-end `None`.
- [ ] Hash set UNCHANGED (bundle.py:47 / computer.py:137 / CANONICAL_MANIFEST.derived_files untouched).
- [ ] Complete-bundle hash byte-unchanged (NFR-002).
- [ ] ruff + mypy --strict clean; complexity ≤15.

## Risks

- **Accidentally narrowing the hash** → collides with #2773. Mitigation: the constraint above; diff-review.
- **Editing computer.py** (WP03's surface) → ownership overlap. Mitigation: preflight lives in synthesize + bundle.py only.

## Reviewer guidance (reviewer-renata, opus)

Confirm: no hash-set change; the fail-closed message is a hoisted constant and actionable;
complete-bundle hash provably unchanged; the red-first test genuinely exercised the dead-end
before the fix; no edit to `computer.py`.

## Activity Log

- 2026-07-17T21:11:35Z – claude:sonnet:python-pedro:implementer – shell_pid=3330116 – Assigned agent via action command
- 2026-07-17T21:23:39Z – claude:sonnet:python-pedro:implementer – shell_pid=3330116 – Fail-closed preflight as separate helper; hash-set untouched; complete-bundle hash preserved; gates green
- 2026-07-17T21:24:48Z – claude:opus:reviewer-renata:reviewer – shell_pid=3362803 – Started review via action command
- 2026-07-17T21:27:14Z – user – shell_pid=3362803 – Review passed: fail-closed preflight for missing references.yaml (#2758). No hash-narrowing (BUNDLE_CONTENT_HASH_FILES/computer.py/_BUNDLE_FILES untouched); separate helper _raise_if_bundle_incomplete (pre-existing noqa:C901 left as-is); hoisted BUNDLE_INCOMPLETE_MESSAGE names charter generate; NFR-002 pinned-hash test green; computer.py not edited; dry-run correctly not gated; red-first genuine (fix symbols absent on base). 12/12 tests pass, ruff clean, mypy owned files clean (7 pre-existing errors in unowned files).
