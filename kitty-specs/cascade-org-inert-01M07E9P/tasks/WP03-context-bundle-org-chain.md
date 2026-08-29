---
work_package_id: WP03
title: Context bundle — stop CLI truncation + route JSON path through the self-resolving wrapper
dependencies: []
requirement_refs:
- FR-002
planning_base_branch: pr/up-cascade-org-inert
merge_target_branch: pr/up-cascade-org-inert
branch_strategy: Planning artifacts for this mission were generated on pr/up-cascade-org-inert. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/up-cascade-org-inert unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-cascade-org-inert-01M07E9P
base_commit: 6b0e2c971d5612eb89303de758fdc6ea59110779
created_at: '2026-08-17T13:33:32.287949+00:00'
subtasks:
- T017
- T018
- T019
- T020
- T021
phase: Phase 1
history:
- timestamp: '2026-08-17T00:00:00Z'
  agent: phase-agent
  action: Prompt authored during tasks phase, cascade-org-inert-01M07E9P
authoritative_surface: src/charter/
create_intent:
- tests/charter/test_context_org_chain.py
execution_mode: code_change
owned_files:
- src/charter/activation/context.py
- src/specify_cli/cli/commands/charter/context.py
- tests/charter/test_context_org_chain.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP03 – Context bundle: stop CLI truncation + route JSON path through the self-resolving wrapper

## Read first — including the failure this WP must not repeat

- `kitty-specs/cascade-org-inert-01M07E9P/spec.md` — FR-002 (all 4 ACs + Design Notes), User
  Story 4 (all 5 scenarios — note the "Corrected scope" paragraph explaining the plain-text path
  is ALSO affected, not just JSON).
- `kitty-specs/cascade-org-inert-01M07E9P/plan.md` — IC-02 (its Risks note is written in capitals
  for a reason).
- `kitty-specs/cascade-org-inert-01M07E9P/reviews/spec-arch.findings.yaml` (finding
  `SPEC-ARCH-002`) — **this mission's own spec review caught the first drafted version of this
  exact fix as a no-op.** Read this finding before writing any code — it is the concrete failure
  mode T019 below exists to prevent from recurring.

## Why this WP exists, precisely

`src/specify_cli/cli/commands/charter/context.py`'s `context()` CLI command (lines ~84-134)
computes ONE truncated `org_root = org_roots[0] if org_roots else None` and passes that SAME
truncated value into BOTH `build_charter_context` (plain-text) and `build_charter_context_json`
(JSON). `build_charter_context` already routes through `charter.activation.action_doctrine_bundle
._resolve_action_bundle` — but that wrapper only self-resolves the full chain when it receives
`org_root=None`; an explicit (already-truncated) `org_root` is honoured verbatim (see
`_resolve_action_bundle`'s docstring, `action_doctrine_bundle.py:96-99`). So the PLAIN-TEXT path
is ALSO truncated to pack 1 today, despite already using the "correct" wrapper.
`build_charter_context_json` has a SECOND, independent defect: it calls the private
`_load_action_doctrine_bundle` directly, bypassing `_resolve_action_bundle` entirely.

**Both of the following changes are required TOGETHER. Neither alone fixes anything observable —
this is not a stylistic preference, it is the literal finding SPEC-ARCH-002 made against the first
drafted version of this fix.**

## T017 — Stop the CLI-level truncation

In `src/specify_cli/cli/commands/charter/context.py`'s `context()` function: stop precomputing
`org_root = org_roots[0] if org_roots else None` for the value passed to
`build_charter_context`/`build_charter_context_json`. Pass `org_root=None` through instead. **Keep
the separately-computed full `org_roots` list UNCHANGED** for
`load_org_charter_json_block(org_roots)` — that call is already correct and must not be touched.

## T018 — Route the JSON path through the self-resolving wrapper

In `src/charter/activation/context.py::build_charter_context_json`: swap the internal call from the private
`_load_action_doctrine_bundle` to `charter.activation.action_doctrine_bundle._resolve_action_bundle`
(mirroring what `build_charter_context`, the plain-text path, already does at
`src/charter/activation/context.py:270`).

## T019 — Empirical inertness proof (do this, do not skip it, do not treat it as optional)

Write FR-002 AC2's red-first test (two-pack chain, doctrine content in pack 2 only, must appear in
BOTH plain-text and JSON output). Then, before considering this WP done, run it at all THREE of
these points and record the result of each:

1. **Neither T017 nor T018 applied** — expected RED (today's actual behavior).
2. **ONLY T017 applied** (CLI stops truncating, JSON path still calls
   `_load_action_doctrine_bundle` directly) — expected RED. If this is unexpectedly GREEN, your
   understanding of the bug is wrong — stop and re-read `_load_action_doctrine_bundle`'s signature
   before proceeding.
3. **ONLY T018 applied** (JSON path calls `_resolve_action_bundle`, but the CLI still hands in the
   pre-truncated `org_root`) — expected RED. If this is unexpectedly GREEN, same instruction as
   above.
4. **Both T017 and T018 applied** — expected GREEN. This is the only state in which this WP is
   done.

Record all four outcomes (including the three "still red" checkpoints) in this WP's commit
message or PR notes — a WP that reports "fixed" without having run the intermediate checks has not
actually proven the fix is not itself inert.

## T020 — Regression tests

Two, both parallel to T019's implementation work: (i) single healthy org pack — both plain-text
and JSON already include pack-1 doctrine today and must not regress (FR-002 AC1); (ii) no org pack
configured — `org_root=None` path (both plain-text and JSON) unchanged from today (FR-002 AC4).

## T021 — Malformed-pack test (loud collapse is ACCEPTABLE — do not build a degrade mechanism here)

Per spec.md's "Out of Scope" and Constraint C-006: this WP must NOT change
`_load_action_doctrine_bundle`'s existing whole-bundle-collapse behavior for a malformed org pack
(that is PR #3401's territory). Assert only that T017/T018 do not WORSEN this pre-existing
behavior — a malformed pack still collapses the whole bundle exactly as it does today, before and
after this WP.

## Gates before calling this WP done

- `.venv/bin/python -m pytest tests/charter/ -v` (targeted surface, esp.
  `test_context.py`, `test_context_org_governance.py`, `test_org_activations_reach_context.py`) —
  baseline recorded before T019's first (red) run.
- `uvx --with-requirements pyproject.toml mypy --strict src/charter/activation/context.py
  src/specify_cli/cli/commands/charter/context.py` — before/after. **Known pre-existing baseline
  (already live-checked by plan.md, do not re-derive)**: `charter/context.py` carries 6
  `no-any-return` errors (lines 250/336/342/351/365/376); `cli/commands/charter/context.py:19`
  carries 1 `untyped-decorator` error. Confirm the count does not grow past this baseline.
- `uvx ruff check src/charter/activation/context.py src/specify_cli/cli/commands/charter/context.py`.
