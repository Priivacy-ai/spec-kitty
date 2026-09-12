---
work_package_id: WP02
title: Cascade org-roots threading + layer-roots ID-mapping widening
dependencies: []
requirement_refs:
- FR-001
- NFR-001
- NFR-002
- C-001
- C-002
planning_base_branch: pr/up-cascade-org-inert
merge_target_branch: pr/up-cascade-org-inert
branch_strategy: Planning artifacts for this mission were generated on pr/up-cascade-org-inert. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/up-cascade-org-inert unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-cascade-org-inert-01M07E9P
base_commit: 6b0e2c971d5612eb89303de758fdc6ea59110779
created_at: '2026-08-17T13:32:55.226666+00:00'
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
- T014
- T015
- T016
phase: Phase 1
history:
- timestamp: '2026-08-17T00:00:00Z'
  agent: phase-agent
  action: Prompt authored during tasks phase, cascade-org-inert-01M07E9P
authoritative_surface: src/specify_cli/cli/commands/charter/
create_intent:
- tests/specify_cli/cli/commands/charter/test_org_cascade_chain.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/charter/activate.py
- src/specify_cli/cli/commands/charter/deactivate.py
- src/specify_cli/cli/commands/charter/_layer_roots.py
- tests/specify_cli/cli/commands/charter/test_charter_activate_commands_cascade_flags.py
- tests/specify_cli/cli/commands/charter/test_charter_deactivate_commands.py
- tests/specify_cli/cli/commands/charter/test_org_cascade_chain.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP02 – Cascade org-roots threading + layer-roots ID-mapping widening

## Read first

- `kitty-specs/cascade-org-inert-01M07E9P/spec.md` — FR-001 (all 7 ACs), User Stories 1-3,
  "Out of Scope" section (item 4 / malformed-pack handling is NOT this WP's job), C-001, C-006.
- `kitty-specs/cascade-org-inert-01M07E9P/plan.md` — IC-01, Test Strategy's FR-001 bullet.

## Why this WP exists

Three call sites walk `load_validated_graph(repo_root)` with NO org roots at all:
`src/specify_cli/cli/commands/charter/activate.py:226` (`_render_cascade_activation`), `:317`
(`_render_no_cascade_warning`), `src/specify_cli/cli/commands/charter/deactivate.py:139`
(`_render_cascade_deactivation`). Separately, `_layer_roots.py::resolve_layer_roots` takes only
the FIRST org root (`break` after one iteration) into a single-value `dict[str, Path]` slot used
for ID-mapping — so even once the DRG walk sees pack 2..N, `_drg_id_to_config_id` still only
consults pack 1.

**Do NOT modify `src/charter/_drg_helpers.py::_resolve_org_root`** — it is intentionally inert
(its own docstring), enforced by `tests/architectural/test_layer_rules.py`. All fixes go in the
`specify_cli`-layer callers below.

## T008 — Widen `resolve_layer_roots` (implement FIRST, its own commit)

In `src/specify_cli/cli/commands/charter/_layer_roots.py::resolve_layer_roots`: change the shape
ADDITIVELY. Keep the existing `roots["org"]` key holding a single representative `Path` (pack 1,
unchanged) — `charter list --all-layers` (`list_cmd.py:165`) already consumes this key via
`CharterPackManager.list_available_detailed`'s `layer_roots: dict[str, Path] | None` contract and
must NOT regress. Add a NEW key carrying the full declaration-ordered chain (e.g.
`roots["org_chain"]: list[Path]`, exact name is your call — document it). This mirrors the
established `effective_org_root`/`effective_org_roots` dual-field pattern already in
`charter.action_doctrine_bundle._resolve_action_bundle`.

## T009 — Thread org roots into `activate.py` (depends on T008)

Both `_render_cascade_activation` (line 226) and `_render_no_cascade_warning` (line 317) call
`load_validated_graph(repo_root)` with nothing else. Change to pass
`org_roots=resolve_existing_org_roots(repo_root)` (from `doctrine.drg.org_pack_config`). Use
T008's new chain field, not the back-compat `roots["org"]`, wherever `_drg_id_to_config_id` needs
the full chain for ID-mapping.

## T010 — Thread org roots into `deactivate.py` (depends on T008)

Same pattern for `_render_cascade_deactivation` (line 139).

## T011 — Red-first tests

Two tests, both RED on this WP's starting commit, both GREEN after T008-T010:

1. **Single healthy org pack** (FR-001 AC1): artifact `A` in the pack with a `requires` edge to
   artifact `B` (same pack) — `charter activate <kind-of-A> <A> --cascade all` activates `B` in the
   same run. This is the baseline positive case and was previously untested at this call site,
   since org roots were never threaded at all before this WP — do not skip it just because AC2's
   two-pack case is the more interesting bug.
2. **Two-pack chain** (FR-001 AC2 / User Story 1 AC2): artifact `A` (pack 1) `requires` artifact
   `C` (pack 2). `charter activate <kind-of-A> <A> --cascade all` must activate `C` in the same
   run — proving the fix walks the full chain, not just pack 1.

## T012 — Revert-test (proves the ID-mapping widening matters, not just the threading)

Temporarily revert ONLY T008 (keep T009/T010's org-roots threading in place) and confirm T011's
test STILL FAILS. This proves `resolve_layer_roots`'s widening is what the test actually exercises
— not merely the DRG-visibility half of the fix. Do not skip this; a whole-change-only test would
not catch a WP that gets the ID-mapping half wrong.

## T013 — `charter list --all-layers` back-compat regression test

Over the SAME two-pack chain used in T011, confirm `charter list --all-layers` does not crash or
type-error, and `roots["org"]` still resolves to a single `Path` exactly as before T008 (User
Story 3 AC4, FR-001 AC7). `list_cmd.py` itself is not edited by this WP — this test is what proves
that claim rather than asserting it.

## T014 — No-org-pack regression test

Both `activate`/`deactivate --cascade` behavior byte-for-byte unchanged when zero org packs are
configured (FR-001 AC4).

## T015 — `referenced_but_not_cascaded` report test

Confirms `_render_no_cascade_warning`'s report correctly names org-pack artifacts that were
referenced-but-excluded by scope (FR-001 AC5) — proving the DRG it warns from now contains
org-pack nodes at all (pre-fix, it structurally could not).

## T016 — Malformed-pack test (loud failure is ACCEPTABLE — do not build a degrade mechanism here)

Per spec.md's "Out of Scope" and Constraint C-006: this WP must NOT implement per-root-degrade
logic (that is PR #3401's territory, already fixed there, not duplicated here). A malformed org
pack MAY raise `DRGLoadError` uncaught — assert only that it does not silently succeed with wrong
data (consistent with NFR-002).

## Gates before calling this WP done

- `.venv/bin/python -m pytest tests/charter/ tests/specify_cli/cli/commands/charter/ -v` (targeted
  surface per plan.md) — baseline recorded before T011's red-first commit.
- `uvx --with-requirements pyproject.toml mypy --strict
  src/specify_cli/cli/commands/charter/activate.py
  src/specify_cli/cli/commands/charter/deactivate.py
  src/specify_cli/cli/commands/charter/_layer_roots.py` — before/after, establish this WP's own
  baseline (plan.md did not live-check these three specifically).
- `uvx ruff check` on all three touched files.
