---
description: "Work package task list template for mission implementation"
---

# Work Packages: Cascade Org Inert

**Inputs**: `kitty-specs/cascade-org-inert-01M07E9P/spec.md`, `kitty-specs/cascade-org-inert-01M07E9P/plan.md`
**Prerequisites**: plan.md (committed `de19ac249`), spec.md (committed `63e9da4c9`, 3 FRs after item-4 retirement). No `research.md`/`data-model.md`/`contracts/`/`quickstart.md` — plan.md explains why none are needed for this mission.

**PR shape**: **ONE PR for the whole mission** (spec-kitty's default — unlike Team Kitty's
one-PR-per-WP; see `~/.hermes/skills/sk-design/references/design-pipeline.md` §3a). All three WPs
below land on `pr/up-cascade-org-inert` and ship together as this mission's single PR. This is
appropriate here: the mission is small (7 files total across all three WPs, all disjoint), and the
three WPs, while independently deliverable and testable, are not independently *valuable* enough
to justify separate PRs — they are three facets of "thread org roots where they're currently
missing," reviewed together for exactly that reason. No split recommended.

**Topology**: `single_branch` (chosen at specify time — this mission works directly on
`pr/up-cascade-org-inert`, no per-WP lane worktrees). `lanes.json` is still required per
CLAUDE.md's Execution Workspace Strategy even under `single_branch` — `spec-kitty agent mission
finalize-tasks` generates it from this file's `dependencies` fields.

**Tests**: Explicit testing work is included in every WP — ATDD/red-first is charter-binding
(C-011), not optional, for this mission.

**Sequencing note (read before assuming FR-number order = WP order)**: WPs are numbered by
**execution risk**, not by the FR-001/002/003 numbering in spec.md/plan.md. WP01 = FR-003
(rebaseline) because plan.md's IC-03 carries the mission's only unresolved unknown (the worktree
question) and the charter's phasing principle says risky/unknown work is front-loaded. WP02 = FR-001
(cascade), WP03 = FR-002 (context). All three are structurally independent (disjoint files,
verified in plan.md's seq-lens review) — this ordering is a risk-management choice, not a hard
dependency chain; a reviewer or implementer MAY reorder if WP01's investigation is resolved out of
band, but should not do so silently.

---

## Work Package WP01: Rebaseline org-awareness + worktree investigation (Priority: P2, execute first)

**Goal**: Make `migrate rebaseline` derive `repo_root` per-snapshot and thread it into `Indexer`,
after first determining whether spec-kitty execution worktrees can carry their own dossier
snapshots (a prerequisite investigation, not optional).
**Independent Test**: A snapshot recorded under a project with a configured, healthy org pack —
rebaseline re-indexes with that org pack's `expected-artifacts.yaml` override actually consulted
(verifiable via `Indexer` receiving a non-`None` `repo_root` matching the project root).
**Prompt**: `tasks/WP01-rebaseline-org-awareness.md`
**Requirement Refs**: FR-003 (all 5 ACs + Design Notes), User Story 5, SC-005.

### Included Subtasks

T001 Investigate: does a spec-kitty execution worktree (`.worktrees/<slug>-<mid8>-lane-<id>/`)
ever carry its own `kitty-specs/<slug>/.kittify/dossiers/...` tree distinct from the primary
checkout's? Read `src/specify_cli/workspace/context.py::resolve_workspace_for_wp` and trace how
`migrate rebaseline`'s sole caller (`migrate_cmd.py`) resolves `repo_root`. Document the finding
with file:line evidence in this WP's own notes (not silently assumed).
T002 [depends on T001] If outcome (a) — worktrees never carry snapshots — implement derivation (B)
as specced: in `src/specify_cli/dossier/rebaseline.py::rebaseline_snapshot_file`, derive
`repo_root = feature_dir.parent.parent` (feature_dir already resolved via `_resolve_feature_dir`)
and pass `Indexer(ManifestRegistry(), repo_root=repo_root)` instead of the current
`Indexer(ManifestRegistry())`.
T003 [depends on T001] If outcome (b) — worktrees CAN carry snapshots — design and implement a
worktree-aware correction instead (e.g. resolve the git common-dir / superproject root) and
document why derivation (B) alone was insufficient. (T002 and T003 are mutually exclusive branches
of the same investigation outcome — only one is actually implemented, per T001's finding.)
T004 [P] Red-first test: assert `Indexer` receives a non-`None` `repo_root` matching the project
root after `rebaseline_snapshot_file` runs on a project with a healthy org pack (SC-005) — must be
committed RED against this WP's own starting commit (current `Indexer(ManifestRegistry())` with no
`repo_root`) before T002/T003's fix commit.
T005 [P] Regression test: no-org-pack case stays green throughout (FR-003 AC2) — the
revert-discipline companion per plan.md's Test Strategy.
T006 Malformed-org-pack test: confirm rebaseline does not raise an unhandled exception to the
`migrate` command (FR-003 AC4) — degrade specifics are this WP's own judgment call, documented,
not deferred further.
T007 [P] Multi-pack-chain check (FR-003 AC3): confirm `ManifestRegistry.load_manifest`'s existing
`_resolve_existing_org_roots(repo_root)` call (src/specify_cli/dossier/manifest.py:253) actually
delivers pack-2 content once `repo_root` is threaded — a two-pack regression test IS required if
this inheritance does not hold on inspection; state the finding either way.

### Implementation Notes

- T001 gates T002/T003 — do not skip to "just derive it and hope" (spec.md's explicit instruction,
  restated in plan.md's IC-03).
- Baseline discipline: run `tests/dossier/test_rebaseline.py` on `pr/up-cascade-org-inert`'s HEAD
  BEFORE T004's red-first commit; record the actual pre-existing red count (if any) — do not cite
  #3284's repo-wide 23/2 figure as this WP's own baseline.
- `mypy --strict` via `uvx --with-requirements pyproject.toml mypy --strict
  src/specify_cli/dossier/rebaseline.py` — run before/after; `rebaseline.py` was not part of
  plan.md's live-checked pre-existing-baseline files (`charter/context.py`,
  `cli/commands/charter/context.py`), so this WP must establish its OWN baseline the same way
  those two files' baseline was established.

### Parallel Opportunities

- T004, T005, T007 (test-writing) can proceed in parallel with each other once T001's investigation
  concludes; T002/T003 (the actual fix) is a single sequential step depending on T001's outcome.

### Dependencies

- None (this mission's WPs are structurally independent) — sequenced first by risk, not by a hard
  blocking dependency on WP02/WP03.

### Risks & Mitigations

- Risk: T001's investigation finds outcome (b) (worktrees CAN carry snapshots), requiring a more
  involved fix than derivation (B) alone. Mitigation: T001 is scoped as its own subtask precisely
  so this risk surfaces before implementation time is sunk into the wrong derivation.

---

## Work Package WP02: Cascade org-roots threading + layer-roots ID-mapping widening (Priority: P1)

**Goal**: `charter activate/deactivate --cascade` sees and correctly ID-maps `requires`/`suggests`
edges in or targeting any configured org pack, including pack 2+ of a chain, without breaking
`charter list --all-layers`'s existing pack-1-only consumption.
**Independent Test**: Two-pack org chain, artifact `A` (pack 1) `requires` artifact `C` (pack 2);
`charter activate <kind-of-A> <A> --cascade all` activates `C` in the same run.
**Prompt**: `tasks/WP02-cascade-org-roots-threading.md`
**Requirement Refs**: FR-001 (all 7 ACs), User Stories 1-3, NFR-001, NFR-002, C-001, C-002.

### Included Subtasks

T008 Widen `resolve_layer_roots` (`src/specify_cli/cli/commands/charter/_layer_roots.py`) to an
ADDITIVE shape: keep `roots["org"]` as a single representative `Path` (pack 1, unchanged, for
`list_cmd.py`'s back-compat) and add a NEW key carrying the full declaration-ordered chain (shape
left to this WP, e.g. `roots["org_chain"]: list[Path]`) — implement this FIRST, in its own commit,
before T009/T010 (per plan.md IC-01's Risks note: the cascade call sites need a stable target).
T009 [depends on T008] Thread `resolve_existing_org_roots(repo_root)` into
`activate.py::_render_cascade_activation` (line 226) and `_render_no_cascade_warning` (line 317),
using the new chain field from T008 for `_drg_id_to_config_id`'s ID-mapping.
T010 [depends on T008] Same threading for `deactivate.py::_render_cascade_deactivation` (line 139).
T011 [P] Red-first tests: (i) single healthy org pack, `requires` edge within that pack is seen and
activated (FR-001 AC1, baseline positive case — was previously untested at this call site since
org roots were never threaded at all); (ii) two-pack chain, cross-pack `requires` edge (FR-001 AC2
/ User Story 1 AC2). Both fail on this WP's starting commit, pass after T008-T010.
T012 [P] Revert-test: temporarily revert ONLY T008 (keep T009/T010's threading) and confirm the
T011 test still fails — proves the ID-mapping widening, not just the org-roots threading, is what
T011 exercises.
T013 [P] Regression test: `charter list --all-layers` over the same two-pack chain does not crash
or type-error post-T008 — `roots["org"]` still resolves to a single `Path` (User Story 3 AC4,
FR-001 AC7). Required even though `list_cmd.py` itself is not edited.
T014 [P] No-org-pack regression test (FR-001 AC4): both commands' cascade behavior byte-for-byte
unchanged from pre-fix behavior.
T015 [P] `referenced_but_not_cascaded` report test (FR-001 AC5): confirms org-pack artifacts that
were referenced-but-excluded now correctly appear in the warning (proving the DRG it warns from
contains org-pack nodes at all).
T016 Malformed-pack test (FR-001 AC3, explicitly scoped as NOT requiring graceful degrade — see
spec.md "Out of Scope" / C-006): assert the malformed case does not silently succeed with wrong
data; a raised `DRGLoadError` is an acceptable outcome for this WP.

### Implementation Notes

- Do NOT modify `charter/_drg_helpers.py::_resolve_org_root` (stays inert, C-001,
  `test_layer_rules.py`-enforced).
- `mypy --strict` baseline for these three files: NOT yet checked live by plan.md (plan.md checked
  `activate.py`/`deactivate.py` and found no NEW errors reported against them specifically —
  confirm `_layer_roots.py`'s baseline the same way, via `uvx --with-requirements pyproject.toml
  mypy --strict src/specify_cli/cli/commands/charter/_layer_roots.py`, before this WP's first
  commit).

### Parallel Opportunities

- T011-T016 (test-writing) can be drafted in parallel once T008's shape is fixed; T009 and T010 can
  proceed in parallel with each other (disjoint files: `activate.py` vs `deactivate.py`) once T008
  lands.

### Dependencies

- None on WP01/WP03 (disjoint files). Internally: T009/T010 depend on T008.

### Risks & Mitigations

- Risk: picking the additive-field shape (T008) inconsistently between `activate.py`'s two call
  sites and `deactivate.py`'s one. Mitigation: T008 is one commit, one shape, consumed identically
  by T009 and T010 — do not let the two threading subtasks invent divergent access patterns.

---

## Work Package WP03: Context bundle — stop CLI truncation + route JSON path through the self-resolving wrapper (Priority: P2)

**Goal**: Both `spec-kitty charter context` (plain-text) and `--json` reflect the full org-pack
chain — closing the gap the spec's own adversarial review caught the first drafted fix as inert
against.
**Independent Test**: Two-pack chain, doctrine content relevant to `--action specify` lives only in
pack 2 — present in BOTH `build_charter_context`'s and `build_charter_context_json`'s output after
this WP, absent before.
**Prompt**: `tasks/WP03-context-bundle-org-chain.md`
**Requirement Refs**: FR-002 (all 4 ACs + Design Notes), User Story 4 (all 5 scenarios).

### Included Subtasks

T017 In `src/specify_cli/cli/commands/charter/context.py`'s `context()` CLI command (lines
~84-134): stop precomputing `org_root = org_roots[0] if org_roots else None` for the value passed
to `build_charter_context`/`build_charter_context_json`; pass `org_root=None` through instead. Keep
the separately-computed full `org_roots` list unchanged for `load_org_charter_json_block(org_roots)`
(a different, already-correct consumer — do not touch that call).
T018 In `src/charter/context.py::build_charter_context_json`: swap the internal call from the
private `_load_action_doctrine_bundle` to `charter.action_doctrine_bundle._resolve_action_bundle`
(mirroring what `build_charter_context`, the plain-text path, already does at line ~270).
T019 [depends on T017, T018] **Empirical proof subtask, not optional**: write the red-first test
for FR-002 AC2 such that it is run THREE times during development — (i) with neither T017 nor T018
applied (red, expected — this is today's behavior), (ii) with ONLY T017 applied (must still be
red — proves T017 alone is insufficient), (iii) with ONLY T018 applied (must still be red — proves
T018 alone is insufficient) — before finally applying both together and confirming green. Record
all three intermediate results in this WP's own notes; this is the concrete implementation of
spec.md's "prove the new fix is not also inert" instruction and plan.md's IC-02 Risks note.
T020 [P] Regression tests: (i) single healthy org pack, both call paths already include pack-1
doctrine today and must not regress (FR-002 AC1); (ii) no org pack configured, `org_root=None`
path unchanged for both call paths (FR-002 AC4).
T021 [P] Malformed-pack test (FR-002 AC3, explicitly scoped as NOT requiring graceful degrade — see
"Out of Scope"/C-006): `_load_action_doctrine_bundle`'s existing whole-bundle-collapse behavior is
unaffected by T017/T018; assert it stays exactly as it is today (a regression check on the
UNCHANGED behavior, not a new requirement).

### Implementation Notes

- `mypy --strict` baseline: ALREADY CHECKED LIVE by plan.md — `src/charter/context.py` carries 6
  pre-existing `no-any-return` errors (lines 250/336/342/351/365/376) and
  `cli/commands/charter/context.py:19` carries 1 pre-existing `untyped-decorator` error, both
  unrelated to T017/T018's edit sites. Run `uvx --with-requirements pyproject.toml mypy --strict
  src/charter/context.py src/specify_cli/cli/commands/charter/context.py` before AND after this
  WP's changes and confirm the count does not grow.

### Parallel Opportunities

- T020, T021 can be drafted in parallel with T017-T019's implementation, but T019's three-phase
  empirical proof must run sequentially against the actual code state at each of its three points
  — it cannot be parallelized with T017/T018 themselves.

### Dependencies

- None on WP01/WP02 (disjoint files).

### Risks & Mitigations

- Risk: repeating Round 1's mistake — stopping after T018 alone because it "looks like the fix."
  Mitigation: T019's three-phase empirical proof is specifically designed to make this mistake
  impossible to miss (phase (ii) would visibly still be red).

---

## Dependency & Execution Summary

- **Sequence**: WP01 (risk-first) → WP02 → WP03, OR any order — all three are structurally
  independent (no shared files), so the sequence above is a risk-management recommendation
  (front-load the one unresolved unknown), not a hard gate. `lanes.json` (generated by
  `finalize-tasks`) will record `dependencies: []` for all three.
- **Parallelization**: Since topology is `single_branch` (no per-WP worktrees), WPs are implemented
  one after another on the same working tree regardless of their structural independence — the
  "Parallel Opportunities" notes above describe SUBTASK-level parallelism within a WP's own
  implementation session, not cross-WP parallel execution.
- **MVP Scope**: All three WPs together are this mission's whole, single-PR scope — there is no
  smaller MVP subset; each WP fixes a distinct, independently-real defect the issue and its comment
  thread both named.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 (all 7 ACs) | WP02 |
| FR-002 (all 4 ACs) | WP03 |
| FR-003 (all 5 ACs) | WP01 |
| NFR-001 | WP02 |
| NFR-002 | WP01, WP02, WP03 (per-WP, per plan.md's Charter Check) |
| C-001 | WP02 |
| C-002 | WP02 |
| C-003 | spec.md itself (no numeric claims in any WP's own artifacts either) |
| C-004 | N/A to implementation — D2 stays closed, no WP touches `kind_vocabulary.py` |
| C-006 | WP02, WP03 (both explicitly do NOT implement malformed-pack degrade logic) |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Worktree investigation | WP01 | P2 | No |
| T002 | Derivation (B) implementation (if outcome a) | WP01 | P2 | No |
| T003 | Worktree-aware correction (if outcome b) | WP01 | P2 | No |
| T004 | Red-first Indexer repo_root test | WP01 | P2 | Yes |
| T005 | No-org-pack regression test | WP01 | P2 | Yes |
| T006 | Malformed-pack no-crash test | WP01 | P2 | No |
| T007 | Multi-pack inheritance check | WP01 | P2 | Yes |
| T008 | resolve_layer_roots additive widening | WP02 | P1 | No |
| T009 | activate.py threading | WP02 | P1 | No |
| T010 | deactivate.py threading | WP02 | P1 | No |
| T011 | Red-first two-pack cascade test | WP02 | P1 | Yes |
| T012 | Revert-test for ID-mapping widening | WP02 | P1 | Yes |
| T013 | list_cmd.py back-compat regression test | WP02 | P1 | Yes |
| T014 | No-org-pack cascade regression test | WP02 | P1 | Yes |
| T015 | referenced_but_not_cascaded test | WP02 | P1 | Yes |
| T016 | Malformed-pack loud-failure test | WP02 | P1 | No |
| T017 | Stop CLI-level org_root truncation | WP03 | P2 | No |
| T018 | Swap to _resolve_action_bundle | WP03 | P2 | No |
| T019 | Three-phase empirical inertness proof | WP03 | P2 | No |
| T020 | Single-pack + no-org-pack context regression tests | WP03 | P2 | Yes |
| T021 | Malformed-pack context regression test | WP03 | P2 | Yes |
