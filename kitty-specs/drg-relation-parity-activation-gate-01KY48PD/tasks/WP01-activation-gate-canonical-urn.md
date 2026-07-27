---
work_package_id: WP01
title: Activation-gate canonical-URN correctness
dependencies: []
requirement_refs:
- C-002
- C-003
- C-004
- FR-001
- FR-002
- FR-004
- NFR-001
planning_base_branch: doctrine/drg-completeness-2843
merge_target_branch: doctrine/drg-completeness-2843
branch_strategy: Planning artifacts for this mission were generated on doctrine/drg-completeness-2843. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/drg-completeness-2843 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-drg-relation-parity-activation-gate-01KY48PD
base_commit: 71a780a19f8799d12dbb749710242d240e278a2c
created_at: '2026-07-22T09:01:37.549912+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
history:
- timestamp: '2026-07-22T08:11:16Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/drg.py
create_intent:
- tests/charter/test_drg_activation_gate.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/charter/drg.py
- src/charter/pack_context.py
- tests/charter/test_drg_activation_gate.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

**Before reading any further**, load the `python-pedro` implementer profile via the
`/ad-hoc-profile-load` skill. Adopt its identity, governance scope, boundaries, and the
initialization declaration it prints. Everything below is authored for that profile: TDD-first
(red-first), type-safe Python 3.11+, complexity ≤15, zero suppressions. Do not begin editing until
the profile is loaded and its init declaration is on the record.

## Objective

Fix the **live** activation-gate correctness bug (research.md D1): `_node_is_activated` Step 3
(`src/charter/drg.py:319`) compares a node's **canonical** id (`DIRECTIVE_001`) against
`PackContext.activated_directives`, which holds config **stems** (`001-architectural-integrity-standard`).
They never match, so a populated list drops every directive node. Route the gate through the
**existing** `charter.kind_vocabulary.resolve_artifact_urn` (stem→canonical), resolving **once per
filter call**, with the public gate signature unchanged. Red-first.

Read before editing: `research.md` (D1, D2), `contracts/activation-gate-contract.md` (the behavioral
table + the three binding "Implementation notes"). The contract is authoritative — obey it exactly.

## Context

- The bug is LIVE in this repo: `.kittify/config.yaml:22` populates `activated_directives` with 26
  stems; `pack_context.py:364` stores them un-normalized; three live callers run the filter
  (`executor.py:182`, `reference_resolver.py:67`, `consistency_check.py:424`). The main
  `DoctrineService.get()` path is exempt, so it silently under-resolves rather than crashing.
- The **template** for correct per-ID resolution already exists in the code WP02 will delete:
  `_build_tension_active_urns` (`consistency_check.py:932-956`) resolves a per-kind canonical-URN set
  **once**, then `_node_is_tension_scan_active` (`:908-929`) does a pure `urn in per_id_urns` test.
  Lift that pattern into `drg.py`.

## Subtasks

### T001 — Red-first characterization test (WP01) [P]

**Purpose**: Prove the defect through the pre-existing entry point before any fix (NFR-001, C-003).

**Steps**:
1. New file `tests/charter/test_drg_activation_gate.py`.
2. Build a real `PackContext` (it is a frozen dataclass, `pack_context.py:83`) with `pack_roots`
   pointed at the real `src/doctrine` and `activated_directives={"001-architectural-integrity-standard"}`
   (a **stem**), `activated_kinds` including `"directives"`. Build the real built-in DRG graph.
3. **RED assertion (stem form)**: run `filter_graph_by_activation(graph, pack_context)` and assert the
   node `directive:DIRECTIVE_001` **survives**. On merge-base this FAILS (node dropped) — the red-first
   teeth. It must fail for the stem≠canonical reason, not an import/fixture error.
4. **GREEN control (canonical form)**: a sibling test with `activated_directives={"DIRECTIVE_001"}`
   asserts the node survives — this passes on merge-base (canonical matches canonical at `:319`),
   isolating the cause. See existing `tests/doctrine/test_activation_parity_guard.py` for the
   RED/GREEN-sibling idiom.
5. Also assert a **non-activated** directive is excluded (the gate still filters).
6. Build fixtures **inline** (construct `PackContext(...)` in the test, as existing charter tests do)
   — do NOT add shared fixtures to `tests/charter/conftest.py` (it is unowned and shared with
   WP02/WP03 lanes; co-writing it is a cross-lane collision).

**Validation**: on merge-base, the stem test is RED and the canonical control is GREEN. After T003/T004
both are GREEN.

### T002 — Add `drg.py`-local singular→`ArtifactKind` constant (WP01)

**Purpose**: `resolve_artifact_urn(kind, config_id, …)` needs an `ArtifactKind`; the existing
singular→kind map lives in `consistency_check.py` (`:89-100`), which **imports `drg`** — importing
back is circular. `drg.py` needs its own small constant.

**Steps**: use **`ArtifactKind.from_operator_token(node_kind)`** — already imported in `drg.py`
(`:54`) — to map the DRG singular node kind (e.g. `directive`, `agent_profile`, `mission_step_contract`)
to its `ArtifactKind`. `from_operator_token` tolerates the underscore DRG-singular form (verified in
`src/doctrine/artifact_kinds.py`), so no lifted constant is needed. (Do NOT copy `consistency_check.py`'s
`_CLI_KIND_TO_DRG_SINGULAR:89-100` — that is CLI-token→singular, a different map with hyphenated keys.)
The verbatim reference pattern is the soon-deleted `_resolve_activated_urns_for_kind:874-905`.

**Files**: `src/charter/drg.py`. **Validation**: mypy-clean; a directive node's kind maps to the
directive `ArtifactKind`.

### T003 — Resolve once in `filter_graph_by_activation` (WP01)

**Purpose**: Build the resolved canonical-URN map **once per filter call** (contract "Implementation
notes"), never per-node.

**Steps**:
1. In `filter_graph_by_activation` (`drg.py:325`), before the node comprehension, build
   `resolved: dict[str, frozenset[str] | None]` keyed by DRG singular kind — for each kind whose
   per-kind activated set is populated, resolve each **stem → full canonical URN** via
   `resolve_artifact_urn(kind, stem, doctrine_root=<root>, org_roots=<roots>)`. `None` set → keep
   `None` (default-allow).
2. **Roots (contract, binding)**: `doctrine_root = resolve_doctrine_root()` (from `charter.catalog`
   — the SAME source the compiler `references.yaml` projection uses; NOT `pack_roots[0]`).
   `org_roots = list(pack_context.pack_roots[1:])`. Prefer adding a named `PackContext` accessor
   (e.g. `pack_context.org_roots` / `.doctrine_root`) in `pack_context.py` so the gate is not a third
   open-coded `pack_roots[1:]` copy (compiler `:144`, tension-scan `:940` are the two existing) — if
   you add the accessor, route the compiler/tension uses through it is OUT of scope (WP02/left as-is);
   just add the accessor and use it here.
3. **Unknown stem → skip-with-report (contract, binding)**: wrap each `resolve_artifact_urn` call in
   a **narrow** `try/except UnknownArtifactIdError: continue` — exactly as `consistency_check.py:734-735`
   and `:902-903` do (if you resolve the kind via `from_operator_token`, also catch
   `MissionTypeNotAnArtifactKind` as the reference does at `:892-894`; harmless for the gate's fixed
   kind domain). **Do NOT use a broad `except Exception`** — that would mask real errors as config
   drift. The gate **MUST NOT raise** (it is consumed by five callers incl. the fail-closed
   `_check_graph_kind_parity`).

**Files**: `src/charter/drg.py`, optionally `src/charter/pack_context.py` (accessor). **Validation**:
mypy/ruff clean; resolution happens O(kinds×stems), not O(nodes×stems); complexity of the new helper ≤15.

### T004 — `_node_is_activated` consumes the pre-resolved map (WP01)

**Purpose**: Keep `_node_is_activated` a pure membership check (no filesystem IO, complexity ≤15).

**Steps**:
1. Change Step 3 (`drg.py:314-320`) so it looks up the pre-resolved canonical-URN set for the node's
   kind and tests `node_full_urn in resolved_set` — comparing on the **full URN**
   (`"directive:DIRECTIVE_001"`, as `resolve_artifact_urn` returns and as the tension-scan compares at
   `:929`), NOT the bare `artifact_id`. Thread the resolved map into `_node_is_activated` via an
   internal parameter (the **public** `filter_graph_by_activation` signature stays unchanged).
2. Preserve the three-state semantics: `None` → default-allow; empty → allow-none; populated →
   canonical membership.

**Files**: `src/charter/drg.py`. **Validation**: T001's stem test now GREEN; canonical control still GREEN.

### T005 — Root-source pinning test + green + gates (WP01)

**Purpose**: Prevent the install-layout divergence paula flagged (research.md D2) and close the WP.

**Steps**:
1. **Root-divergence test (not a tautology)**: `assert resolve_doctrine_root() == resolve_doctrine_root()`
   proves nothing. Instead construct a `PackContext` whose `pack_roots[0] != resolve_doctrine_root()`
   (or monkeypatch `resolve_doctrine_root`), then assert the gate's resolution **follows
   `resolve_doctrine_root()`** — i.e. a directive node still resolves via the projection root and
   would NOT have resolved via `pack_roots[0]`. This is the install-layout guard (research.md D2).
2. **Batched-once test**: spy/monkeypatch `resolve_artifact_urn` and assert it is called **O(kinds),
   not O(nodes)** for a graph with many nodes of one activated kind (proves the resolution is hoisted
   into `filter_graph_by_activation`, not called per-node in `_node_is_activated`).
3. Run `uv run pytest tests/charter/test_drg_activation_gate.py -q` (all green), then
   `uv run ruff check src/charter/drg.py src/charter/pack_context.py` and
   `uv run python -m mypy --strict src/charter`.

**Validation**: all WP01 tests green; the root-divergence and batched-once tests are discriminating
(fail on a `pack_roots[0]`-sourced or per-node implementation); ruff/mypy clean; complexity ≤15; no new suppressions.

## Branch Strategy

Planning artifacts were generated on **`doctrine/drg-completeness-2843`**; completed changes merge
back into **`doctrine/drg-completeness-2843`** (the operator PRs the branch to main). Execution
worktrees are allocated per computed lane from `lanes.json`. Do not redirect the landing branch.

## Definition of Done

- [ ] T001 red-first test committed and demonstrably RED on merge-base (stem) / GREEN (canonical control).
- [ ] Gate resolves stems→canonical once per call via reused `resolve_artifact_urn`; public signature unchanged.
- [ ] `doctrine_root` from `resolve_doctrine_root()`; unknown stems skipped-with-report (never raise).
- [ ] Full-URN comparison; `_node_is_activated` pure + complexity ≤15.
- [ ] Root-**divergence** test (pack_roots[0] ≠ resolve_doctrine_root(), gate follows the latter) + batched-once spy test (O(kinds) not O(nodes)) — both discriminating, green; ruff + mypy --strict clean; no new suppressions.

## Risks

- **Behavior-changing** in this repo's charter-mediated paths (26 directives now retained) — expected;
  WP03 characterizes the corrected observables. Do not "preserve" any test asserting the buggy output.
- Do NOT touch `charter/compiler.py`'s `references.yaml` projection (C-001, WP02/left as-is) or
  `consistency_check.py` (WP02 owns it).

## Reviewer Guidance (reviewer-renata / opus)

Verify: red-first genuinely fails for the stem≠canonical reason (not incidental); resolution is
batched once (grep for `resolve_artifact_urn` inside `_node_is_activated` = smell); `doctrine_root`
is `resolve_doctrine_root()` not `pack_roots[0]`; unknown-stem path is `except UnknownArtifactIdError:
continue`, not a raise; full-URN comparison; public gate signature unchanged.
