# Implementation Plan: Org Pack DRG Root Graph Guard

**Branch**: `kitty/mission-org-pack-drg-root-graph-guard-01KZY0QT` | **Date**: 2026-08-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/org-pack-drg-root-graph-guard-01KZY0QT/spec.md` — GitHub issue [#3384](https://github.com/Priivacy-ai/spec-kitty/issues/3384)

**Branch contract (stated explicitly, per Location Check discipline)**: current branch is
`kitty/mission-org-pack-drg-root-graph-guard-01KZY0QT`; `meta.json`'s own `target_branch` is
`main`; this plan lands on the mission branch and the mission's eventual merge target is
`main`. Note: `spec-kitty agent mission branch-context --json` reports `target_branch` /
`planning_base_branch` / `merge_target_branch` all as the *current* branch name rather than
reading `meta.json.target_branch` — a live-verified tool defect (SK-10, seeded in
`tracer-tooling-friction.md`) — so this plan states the contract by reading `meta.json`
directly rather than trusting that command's branch fields.

## Summary

Issue #3384: an org pack whose only DRG content lives at `<org_root>/drg/*.graph.yaml` — the
**only** layout the shipped authoring guide documents — silently zeroes every action-scoped
directive/tactic/styleguide/toolguide/procedure count the moment the pack is declared,
because `_drg_helpers.py:87` calls `load_graph_or_dir(org_root)` unconditionally on
`org_root.exists()` with no check for whether `org_root` itself contains a loadable graph;
`load_graph_or_dir` raises `DRGLoadError` on a directory with no root-level graph file, and
`_load_action_doctrine_bundle`'s wide `except DRGLoadError` catches it and collapses the
*entire* action bundle to empty, logging only a WARNING.

The fix (both halves of the operator's binding decision, not either): (1) guard the org-root
load with a `has_graph_files`-style existence check across **both** `org_root` itself and
`org_root/drg/` before deciding there is "nothing to load" (FR-001), and (2) actually load
`<org_root>/drg/*.graph.yaml` fragments when present (FR-002) — composing the two into one new
module-private helper, `_load_org_layer`, in `src/charter/_drg_helpers.py`. When both a
root-level graph and `drg/` fragments are present, they are merged with `drg/` authoritative on
node-label conflicts and identical edge triples deduplicated via the existing canonical
`doctrine.drg.validator.duplicate_edge_triples` primitive, never independently reimplemented
(FR-003/C-001). Org-layer content that is genuinely malformed (bad YAML or schema-invalid) —
whether the **root-level** `graph.yaml`/`*.graph.yaml` or a `drg/*.graph.yaml` fragment — raises
a new, narrowly-scoped exception (`OrgDRGFragmentError`) that does **not** subclass
`DRGLoadError`, so it sails past the existing wide catch and surfaces as a real, structurally
distinguishable CLI failure via the existing Typer JSON error surface, rather than being
silently swallowed the way "nothing to load" now correctly is (FR-004). `_load_org_layer` wraps
**both** the root-level load and the `drg/`-level load independently in this exception, so a
malformed root graph can no longer take a valid, sibling `drg/` fragment down with it (closing
PLAN-ARCH-001's confirmed gap by construction — see IC-01/IC-03). The project-layer
`DRGLoadError` catch and the built-in `merge_layers()` implementation are untouched.

Entire change is confined to `src/charter/_drg_helpers.py`, a docstring/comment update in
`src/charter/action_doctrine_bundle.py`, and new regression tests/fixtures under
`tests/charter/` (C-001). #3385 (the `kind_vocabulary.py` activation-filter drop) is
explicitly out of scope — see Non-Goals in spec.md; this mission's PR description must state
that plainly so nobody closes #3385 believing this fix covers it.

**Mid-flight rollout note — a third outcome beyond spec.md's binary.** spec.md's mid-flight
Edge Case names two outcomes for a project mid-mission when this fix lands: unaffected (no org
pack declared) or counts increase (pack declared, previously-unloaded `drg/` content now loads
correctly). That binary omits a third, more disruptive outcome, stated here explicitly: an
*existing* root+`drg/` org pack whose `drg/` content was previously dormant — never even
inspected, because `load_graph_or_dir` on a directory prefers a root-level `graph.yaml` and never
looks at `drg/` when one is present — and happens to be malformed (invalid YAML or schema-invalid,
never validated before because never loaded) will, once this fix lands, have that dormant content
loaded for the first time; IC-03 then makes that failure surface as an uncaught
`OrgDRGFragmentError` instead of silently swallowing it. A `charter context` call that worked
(root-only, `drg/` never consulted) before this fix will **hard-fail** after it, for exactly this
pack shape, until an operator repairs or removes the malformed `drg/` fragment. This is intended
(IC-03 doing exactly what FR-004 requires) but is a genuine rollout risk for any downstream
spec-kitty-driven workspace (e.g. team-kitty-missions, muster-missions) that may carry this
root+`drg/` shape today with a never-validated `drg/` fragment. This mission's PR description
must state this plainly as a pre-upgrade audit note, mirroring the #3385 disclosure above.
The same shift applies, symmetrically, to a pre-existing pack whose **root-level** graph is
malformed: previously that raised plain `DRGLoadError`, swallowed by the wide catch into a
silently-zeroed-but-reported "success" (today's pre-fix behavior, and the deeper defect
PLAN-FRESH-002 flagged when only the `drg/` half of this design was wrapped); after this fix it
raises `OrgDRGFragmentError` and hard-fails instead. This is the same category of rollout risk
as the `drg/` case above, now also covered by IC-01/IC-03's broadened design and worth the same
pre-upgrade audit-note treatment.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `pydantic` (`DRGGraph`/`DRGNode`/`DRGEdge` models, `model_copy`), `ruamel.yaml` (graph YAML parsing, unchanged), `typer`/`rich` (existing CLI error surface consumed, not modified) — all pre-existing; no new runtime dependency added, no `uv.lock` change.
**Storage**: N/A — filesystem-based YAML graph fragments only (`<org_root>/graph.yaml` / `<org_root>/*.graph.yaml`, `<org_root>/drg/*.graph.yaml`).
**Testing**: pytest, scoped per NFR-002 to `tests/charter/` and `tests/architectural/` (not the full ~17,000-test suite); `mypy --strict` on the two changed source files; `ruff check` on the two changed source files. See Gate Set below for literal invocations.
**Target Platform**: Cross-platform CLI (Linux/macOS/Windows) — no platform-specific code; unaffected.
**Project Type**: Single project (CLI library) — the change is entirely inside the `charter` package (below `specify_cli`, above `doctrine`/`kernel` in the dependency hierarchy stated in `_drg_helpers.py`'s own module docstring).
**Performance Goals**: No regression to the CLI's <2s budget (charter.md, Technical Standards). The new dedup step is a single linear scan over the org-internal sub-merge's edges (`duplicate_edge_triples`, already O(E)); negligible for realistic pack sizes.
**Constraints**: charter→doctrine layering preserved — no `specify_cli` import added under `src/charter/` (unaffected; `_drg_helpers.py` already imports only from `doctrine.drg.*`); `merge_layers()` (`src/doctrine/drg/loader.py`) is **not modified**, byte-for-byte (C-001); blast radius confined to `src/charter/_drg_helpers.py`, `src/charter/action_doctrine_bundle.py`, and new fixtures/tests under `tests/charter/` — explicitly **not** `src/charter/kind_vocabulary.py` (C-001, Non-Goals); no version-number prescription in scope.
**Scale/Scope**: One new module-private helper (`_load_org_layer`) + one new module-private dedup helper (`_dedup_org_layer_edges`) + one new exception type (`OrgDRGFragmentError`) in `_drg_helpers.py`; a docstring/comment update (no behavior change) in `action_doctrine_bundle.py`; new regression tests under `tests/charter/` covering all four User Stories. No new files outside `tests/charter/`.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Charter rule | Status | Note |
|---|---|---|
| Single canonical authority (DIR-044) | ✅ | Dedup reuses the existing canonical `doctrine.drg.validator.duplicate_edge_triples` — no second, independently written `(source, target, relation)` comparison (C-001). |
| Architectural alignment / layering (DIR-001) | ✅ | No new import crosses the `kernel <- doctrine <- charter <- specify_cli` boundary; the fix stays inside `charter`, composing existing `doctrine.drg.loader`/`validator` primitives. No CLI command reaches past a service into kernel internals — this fix doesn't touch the CLI layer at all, only the charter-layer resolver it already calls into. |
| DDD + tiered rigour | ✅ | This is core domain logic (doctrine-graph composition) — full ATDD coverage per User Story, not glue/IO tiered-down. |
| ATDD-first (C-011) | ✅ | Each of FR-001+FR-002, FR-003, FR-004 lands a red-first test (against `planning_base_branch`) as a separate commit before its implementation commit — see Test Strategy below. |
| Terminology canon | ✅ | No `feature`/`--feature` surface touched; new prose uses "org pack", "org DRG layer", "drg/ fragment" — all already-canonical terms from the org-doctrine-pack guide. `tests/architectural/test_no_legacy_terminology.py` only guards two unrelated legacy terms from the completed 01KSPN6C rename and explicitly excludes `kitty-specs/`, so it does **not** cover the Feature/Features prohibition; the "no feature/--feature surface touched" claim above is verified by manual review only, consistent with how SK-11 (`tracer-tooling-friction.md`) already treats this mission's own pre-existing "Feature specification" instance at `plan.md:4`. |
| `__all__` convention (C-007/C-002) | ✅ | See dedicated `__all__` Export Discipline section below — all three new symbols are deliberately kept out of `_drg_helpers.py`'s `__all__` (no real `src/` caller outside the defining module). |
| Campsite-first (DIR-025) | ✅ (no debt found) | See Campsite-Clean Scope below — both touched files were inspected for domain-matched debt (complexity, repeated literals, empty handlers); none found worth folding. Stated plainly rather than inventing busywork. |
| No version prescription | ✅ | No patch/version numbers assigned anywhere in this plan. |
| Reviewer ≠ implementer | ✅ | Enforced at review (separate role, per mission hygiene standing order). |
| Red-main / pre-existing exclusion (C-005) | ✅ | Issue #3284's ~23 known-red tests / 2 errors on `main`, and #3283's shared pytest test-venv lock timeout, are pre-existing and out of scope — see Baseline section below for how this mission distinguishes pre-existing red from introduced red. |

**Post-design re-check**: no new violations. The design introduces no new cross-layer import, no schema change, and no new external dependency.

## Project Structure

### Documentation (this mission)

```
kitty-specs/org-pack-drg-root-graph-guard-01KZY0QT/
├── plan.md                      # This file
├── spec.md                      # Passed, 4 review rounds + operator ruling
├── reviews/spec.ruling.md       # Binding: --json 4-count split, procedures via plain-text
├── tracer-tooling-friction.md   # Seeded this phase (SK-09, SK-09b, SK-10); SK-11 added during
│                                 #   the R4 fix round (PLAN-GOV-002)
├── tracer-approach.md           # Seeded this phase
├── tracer-design-decisions.md   # Seeded this phase
└── tasks.md                     # Phase 2 (/spec-kitty.tasks — NOT created here)
```

No `research.md` / `data-model.md` / `contracts/` / `quickstart.md` are generated for this
mission: there is no NEEDS CLARIFICATION left unresolved (the operator's pre-specify
clarifications already pinned the fix shape and scope), no new data entities (the three Key
Entities in spec.md — org DRG root, doctrine bundle, DRG graph — are pre-existing types this
mission composes, not new ones), and no external contract surface changes (see Contract
Movement below). Generating empty Phase 0/1 placeholder files for a change this bounded would
itself be busywork; the plan/spec/ruling trio already carries the full research record (the
operator's clarification Q&A did the Phase-0 unknown-resolution work before `/spec-kitty.plan`
ran).

### Source Code (repository root)

```
src/charter/
├── _drg_helpers.py              # THE FIX — load_validated_graph's org-layer branch (~line 83-97)
│                                 #   + NEW: _load_org_layer() (module-private)
│                                 #   + NEW: _dedup_org_layer_edges() (module-private)
│                                 #   + NEW: OrgDRGFragmentError (module-private-by-convention;
│                                 #     not added to __all__ — see __all__ Export Discipline)
└── action_doctrine_bundle.py    # DOCSTRING/COMMENT ONLY — _load_action_doctrine_bundle's
                                  #   existing DRGLoadError-catch comment (~line 152-156)
                                  #   updated to state which exception types now propagate vs.
                                  #   are caught. No functional/behavioral change in this file.

tests/charter/
└── test_org_root_graph_guard.py      # NEW — all four User Stories' regression tests,
                                        following the existing inline tmp_path fixture
                                        convention (test_merged_graph_on_live_path.py,
                                        test_context_org_governance.py), not committed
                                        fixture files under tests/charter/fixtures/.
```

**Structure Decision**: single-project CLI library; the entire functional change is two
functions' worth of logic inside one existing module (`_drg_helpers.py`), a documentation-only
touch in its sibling caller module, and one new test module. No new package, no new top-level
directory, no new external dependency.

## Complexity Tracking

*Fill ONLY if Charter Check has violations that must be justified*

No Charter Check violations — table intentionally empty.

## Implementation Concern Map

> Concerns, not work packages. `/spec-kitty.tasks` translates these into executable WPs — one
> concern may become multiple WPs; multiple small concerns may merge into one WP.

### IC-01 — Combined root+`drg/` graph-files guard closes the P0 zeroing (FR-001 + FR-002; User Stories 1 & 2)

- **Purpose**: Replace the unconditional `load_graph_or_dir(org_root) if org_root and org_root.exists() else None` at `_drg_helpers.py:87` with a combined existence check across **both** `org_root` itself and `org_root/drg/` (`has_graph_files`-style, reusing the existing `doctrine.drg.loader.has_graph_files` primitive unchanged — C-001 forbids touching its public contract, so this concern only *calls* it, twice, at a new call site). A pack with graph content in **neither** location degrades to `None` ("no org DRG layer") cleanly, with no exception. A pack with content in `drg/` only (the guide-compliant, only-documented shape) now actually loads it — closing the reported defect, not just guarding it (per the operator's own rejected-alternative note: guard-alone would leave every correctly-authored pack's edges permanently unloaded, a smaller but still-silent residual drop).
- **Relevant requirements**: FR-001, FR-002; NFR-001 (byte-parity when `org_root` is `None`); Edge Case "org_root itself does not exist" (unchanged `.exists()` outer guard preserved).
- **Affected surfaces**: `src/charter/_drg_helpers.py` — new `_load_org_layer(org_root: Path) -> DRGGraph | None` module-private function; `load_validated_graph`'s org-layer line changes from a `load_graph_or_dir(...)` call to `_load_org_layer(org_root) if org_root and org_root.exists() else None`.
- **Sequencing/depends-on**: none — lands first; IC-02 and IC-03 both extend this same function's body.
- **Risks**: `has_graph_files` only checks for the *presence* of a recognisably-named graph file, not its validity — a root-level `graph.yaml` that exists but is malformed still causes `has_root_graph=True`, and the subsequent load of that root content can raise plain `DRGLoadError`. This concern's `_load_org_layer` wraps that root-level load in the same `try/except DRGLoadError as exc: raise OrgDRGFragmentError(...) from exc` shape IC-03 already uses for the `drg/` load (see IC-03), so a malformed root graph now surfaces as a real, distinguishable failure instead of propagating a plain `DRGLoadError` that the existing wide `except DRGLoadError` in `_load_action_doctrine_bundle` silently swallows. This closes the gap for the case where a valid, loadable `drg/` fragment sits alongside the malformed root graph in the same org pack: previously the *entire* org layer — including that perfectly valid `drg/` content — collapsed to an empty-but-reported-success bundle (a variant of #3384's own defect shape one directory over, and PLAN-ARCH-001's confirmed finding); now the malformed root raises `OrgDRGFragmentError` on its own, and a valid sibling `drg/` fragment is no longer taken down with it by construction (root and `drg/` loads are attempted and wrapped independently, per PLAN-ARCH-001 remediation option (b)). This broadens `OrgDRGFragmentError`'s coverage beyond FR-004's literal `drg/`-fragment wording to org-layer content generally (root or `drg/`); see the design-choice note below Contract Movement for why this stays inside this fix round's plan-authoring authority and does not require a spec.md edit or a fresh operator ruling. See the paired Test Strategy row below
  (`test_malformed_root_graph_with_valid_drg_sibling_raises_distinguishable_failure`) that pins
  this as the new, closed behavior.

### IC-02 — Root+`drg/` merge, `drg/`-authoritative precedence, identical-edge-triple dedup (FR-003; User Story 4)

- **Purpose**: When IC-01's guard finds content in **both** locations, merge them via `merge_layers(root_graph, drg_graph)` — root as the first (`built_in`) positional argument, `drg/` as the second (`project`) positional argument, so `drg/`'s node labels win on same-URN conflicts (mirroring `merge_layers`' own existing override-wins convention for its second argument — FR-003's own text flags this as a confusing but pre-existing overload of the `project` parameter name, not something this mission invents). Then collapse any edge triple duplicated identically across the two sources to exactly one retained copy, via the canonical `doctrine.drg.validator.duplicate_edge_triples` primitive (C-001 — no independently-written triple comparison), **before** the result is fed into the existing, unmodified `merge_layers(built_in, org)` call and the final `assert_valid`.
- **Relevant requirements**: FR-003; C-001 (mandates reuse of `duplicate_edge_triples`).
- **Affected surfaces**: `src/charter/_drg_helpers.py` — `_load_org_layer` extended to call `merge_layers` when both sources are present; new `_dedup_org_layer_edges(graph: DRGGraph) -> DRGGraph` module-private helper.
- **Sequencing/depends-on**: IC-01 (needs `_load_org_layer` and its root_graph/drg_graph locals to exist first).
- **Risks**: scope precision — this dedup step only collapses duplicates **strictly within** the org-internal root+`drg/` sub-merge. A duplicate between the org layer and the built-in or project layer is a *different* scope (unrelated to FR-003) and continues to raise `DRGValidationError` at the final `assert_valid` exactly as today; this concern must not accidentally widen the dedup to cover that case.

### IC-03 — Malformed org-layer content (root graph or `drg/` fragment) surfaces as a real, distinguishable failure (FR-004; User Story 3; PLAN-ARCH-001/PLAN-FRESH-002 remediation option (b))

- **Purpose**: Org-layer content that fails to parse (invalid YAML) or fails `DRGGraph` schema validation is a genuine authoring mistake, not "nothing to load" — whether the malformed content is the **root-level** `graph.yaml`/`*.graph.yaml` or a `drg/*.graph.yaml` fragment. `_load_org_layer` wraps **both** the root-level load and the `drg/`-level load, each independently in its own `try/except DRGLoadError as exc: raise OrgDRGFragmentError(...) from exc`, so either source's malformed content re-raises as the same new exception (module-private-by-convention name; deliberately **not** a `DRGLoadError` subclass) with the original exception chained (`from exc`) — and, critically, a malformed root graph no longer takes a valid, loadable `drg/` fragment down with it (each load is attempted and wrapped on its own, not as one combined try block). Because `_load_action_doctrine_bundle`'s existing `except DRGLoadError as exc:` clause does not match a non-subclass type, `OrgDRGFragmentError` propagates uncaught, past `load_validated_graph`, past `_load_action_doctrine_bundle`, up to the `charter context` CLI command's existing catch-all (`except Exception as e: _emit_error(..., unexpected=True)`), which already turns any uncaught exception into `{"result": "error", "success": False, "error": "<message>"}` in `--json` mode (or a red `Unexpected error: ...` line + exit code 1 in plain-text mode) — **zero code change needed in the CLI layer**, this concern only needs the exception type to deliberately not match the existing narrow catch. This is a considered broadening of FR-004's literal `drg/`-fragment wording — FR-004's text names "a malformed or invalid `drg/` fragment" as the case that must surface as a real, non-swallowed failure, which is a floor, not a ceiling — closing PLAN-ARCH-001's confirmed gap by construction (remediation option (b): `_load_org_layer` attempts the root and `drg/` loads independently of each other's outcome) instead of leaving it as a plan-only carve-out with a self-authorized escape hatch.
- **Relevant requirements**: FR-004; Non-Goals ("No change to project-layer `DRGLoadError` handling" — the narrowing must be scoped to the org branch only, achieved here by construction: the new type is raised only inside `_load_org_layer`'s root-level and `drg_dir` branches, never for the project-layer `.kittify/doctrine` load elsewhere in `load_validated_graph`).
- **Affected surfaces**: `src/charter/_drg_helpers.py` — new `OrgDRGFragmentError(Exception)`; `_load_org_layer`'s root-level `load_graph_or_dir(org_root)` call **and** its `drg_graph = load_graph_or_dir(drg_dir)` call each wrapped independently in `try/except DRGLoadError as exc: raise OrgDRGFragmentError(...) from exc`. `src/charter/action_doctrine_bundle.py` — the comment near `_load_action_doctrine_bundle`'s existing `except DRGLoadError` block (~line 152-156) updated to document that this catch now only fires for project-layer malformed content (unchanged) — **not** for malformed org-layer content of either shape (root or `drg/`), both of which are now IC-03's new, deliberately-uncaught `OrgDRGFragmentError`. No functional code change in this file.
- **Sequencing/depends-on**: IC-01 (needs the `has_root_graph`/`has_drg_layer`/`drg_dir` locals `_load_org_layer` establishes).
- **Risks**: must not accidentally widen `OrgDRGFragmentError` to the *project-layer* malformed-content case — that stays swallowed by the pre-existing wide catch, per Non-Goals (which is scoped to project-vs-org-pack-branch, not root-vs-`drg/` within the org branch — broadening within the org branch does not touch that boundary). The regression tests (FR-004) must assert against **both** the root-level-malformed and `drg/`-fragment-malformed cases (including the combined root-malformed+valid-`drg/`-sibling shape — see the Test Strategy row below), and any existing project-layer malformed-content test must continue to assert the pre-existing swallow-to-empty-success behavior, unchanged.

---

## Seam, Generated Artifacts, Contract Movement

### Seam

This change lands entirely on the **charter/doctrine seam**, inside the `charter` package's
DRG-composition layer — **not** the kernel, and **not** any CLI command surface directly.
Concretely:

- `src/charter/_drg_helpers.py` — the resolver-facing composition function
  (`load_validated_graph`) and its new private helpers. This module already sits below
  `specify_cli` and above `doctrine`/`kernel` (its own module docstring states the dependency
  chain: `kernel (root) <- doctrine <- charter <- specify_cli`); the fix stays inside `charter`
  and only calls existing `doctrine.drg.loader`/`doctrine.drg.validator` primitives it (or its
  sibling `_drg_helpers.py` code) already imports or is adding an import of — no new
  cross-layer edge.
- `src/charter/action_doctrine_bundle.py` — the doctrine-bundle assembly layer that calls
  `load_validated_graph` and decides what to do when it raises. Only a comment/docstring
  changes here; the actual except-clause code is untouched (its narrowing is achieved by the
  new exception type simply not matching the existing `except DRGLoadError`, not by editing
  the clause).
- **No CLI command is touched.** `src/specify_cli/cli/commands/charter/context.py`'s existing
  catch-all exception handler already does the right thing for an uncaught exception type; this
  fix relies on that existing behavior rather than adding new CLI-layer code. This satisfies
  "no CLI command may reach past a service into kernel internals" vacuously — the CLI layer
  isn't touched at all, so there's no new reach to audit.
- **No kernel (`src/kernel/`) file is touched.**

### Generated Artifacts

**This change does not touch any generated artifact.** Explicitly, for each candidate:

- **Doctrine schemas** — `DRGGraph`/`DRGNode`/`DRGEdge` (in `src/doctrine/drg/models.py`) are
  **not modified**; no field, kind, or relation is added, so there is no generated JSON schema
  or fixture to regenerate.
- **Contextive glossary** — no new domain terminology is introduced. "Org pack", "org DRG
  layer", "`drg/` fragment" are all pre-existing terms already documented in
  `docs/guides/how-to/governance/create-an-org-doctrine-pack.md`; no glossary entry needs
  adding or regenerating.
- **Agent command copies** (`.claude/`, `.codex/`, etc., generated via `spec-kitty upgrade`
  from `src/doctrine/missions/mission-steps/`) — not touched; this mission does not change any
  mission-step prompt template.
- **`.kittify/command-skills-manifest.json`** and any other install-time manifest — not
  touched; no new command or skill is added.

If a future WP discovers a generated artifact this analysis missed, that is a plan defect to
flag at review time, not something to hand-patch silently.

### Contract Movement

Stated explicitly for each surface named in the task brief:

- **Doctrine schemas** (`DRGGraph`/`DRGNode`/`DRGEdge`, `NodeKind`, `Relation`) — **do not
  move.** No field added, removed, or retyped.
- **Mission step contracts** — **do not move.** This mission changes no
  `mission_step_contract` artifact or its executor.
- **Action indices** — **do not move.** The `action:<mission_type>/<action>` URN resolution
  path (`resolve_context`, `_classify_artifact_urns`) is unchanged; this fix only changes what
  graph content is available for that resolution to walk, not the resolution logic itself.
- **The orchestrator-api surface** — **does not move.** No orchestrator-api endpoint,
  request/response shape, or CLI command signature changes. The CLI's `--json` payload shape
  for `charter context` is unchanged (see below).
- **The `spec-kitty-events` dependency** — **does not move.** Not imported, not touched; this
  fix has no event-sourcing surface.
- **`merge_layers()`** (`src/doctrine/drg/loader.py`) — **is explicitly NOT modified.** Its
  additive-only, no-removal semantics stay byte-for-byte unchanged (C-001). The new dedup logic
  lives entirely in `_drg_helpers.py`, operating on `merge_layers`' *output* before that output
  is fed into the existing, unmodified `merge_layers(built_in, org)` call used elsewhere in
  `load_validated_graph`.
- **`charter.context_contract`'s versioned key ledger and `context_schema_version`** — **do
  not move.** Per the spec ruling's binding decision (SPEC-FRESH4-001), this mission does
  **not** add a `procedures[]` array to the `--json` payload — that is issue #3389, explicitly
  out of scope here. The `--json` payload's shape, field set, and `context_schema_version` are
  unchanged by this mission; the fix changes what *counts* the existing typed arrays report
  (higher, correctly, once an org pack's `drg/` content loads), not the payload's *shape*.

### Design-choice note: `OrgDRGFragmentError` broadened to root-level org content (PLAN-ARCH-001 / PLAN-FRESH-002)

Broadening `OrgDRGFragmentError` to cover a malformed **root-level** org graph in addition to a
malformed `drg/` fragment (IC-01/IC-03) is a considered plan-level design choice, not a scope
change: FR-004 states a floor, not a ceiling, so this broadening still fully satisfies FR-004
while closing PLAN-ARCH-001's confirmed remediation option (b); it stays within C-001's stated
blast radius (`_drg_helpers.py`, `action_doctrine_bundle.py`, `tests/charter/`) and strictly
narrows silent-swallowing further rather than widening scope elsewhere, so it does not require a
spec.md edit or a fresh operator ruling.

## Gate Set

Chosen from the candidate list; every skip carries a concrete reason, not "we'll run the
tests." This set is consumed verbatim by `sk-implement`.

**Enforced gates (real, literal invocations):**

1. `pytest tests/charter/` — the direct blast-radius test package (NFR-002, C-001). ~1,500
   tests; run the whole directory, not a hand-picked subset, so a regression in a sibling
   charter test (e.g. `test_context_org_governance.py`, `test_merged_graph_on_live_path.py`)
   is caught.
2. `pytest tests/architectural/` — required by SC-004 explicitly, and by NFR-002's own framing.
   Includes, by name, per SC-004:
   - `tests/architectural/test_no_dead_symbols.py` — the C-002/C-007 `__all__` convention gate
     (verifies the three new symbols staying out of `__all__` is consistent — no orphaned
     public name).
   - `tests/architectural/test_no_legacy_terminology.py` — run per AGENTS.md's own pre-push
     instruction since this touches `src/charter/` prose (repo-wide gate that runs in CI's
     `integration-tests-core-misc` job but not always in fast-tests locally). **Not** cited as
     coverage for the Feature/Features prohibition: this test only guards two unrelated legacy
     terms from the completed 01KSPN6C rename and explicitly excludes `kitty-specs/` from its
     scan, so it cannot and does not catch "Feature". The "no feature/--feature surface touched"
     self-certification (Charter Check, Terminology canon row) is verified by manual review
     only, consistent with SK-11's treatment of this mission's own pre-existing instance.
   - `tests/architectural/test_layer_rules.py` (run as part of the directory) — confirms no new
     `specify_cli` import leaked into `src/charter/` (none is added, but the gate proves it
     rather than asserting it).
3. `mypy --strict src/charter/_drg_helpers.py src/charter/action_doctrine_bundle.py` — CLAUDE.md's
   binding Code Style rule ("New code MUST pass ruff and mypy with zero issues... do NOT
   suppress"). Both new helper functions and the new exception type need full type annotations
   (`DRGGraph | None` return types, `Path` params) — mypy strict mode will catch a missed
   Optional or an untyped `except` binding.
4. `ruff check src/charter/_drg_helpers.py src/charter/action_doctrine_bundle.py` (and the new
   test file) — enforces TID251 banned-API, complexity ceiling (C901/S3776 = 15), and the
   repo's lint rule set as a real per-file invocation, not the advisory aggregate.
5. **CLI JSON error-surface exercise** — not a separate CI step; this is the concrete mechanism
   the FR-004 regression test itself exercises end-to-end (invoking the `charter context
   --action <a> --json` Typer command, e.g. via `CliRunner` or subprocess, not by calling
   `_load_org_layer` directly), proving `OrgDRGFragmentError` actually reaches the existing
   `_emit_error(..., unexpected=True)` catch-all and produces `{"result": "error", "success":
   false, "error": "..."}`. Named explicitly here because it is the load-bearing verification
   for FR-004/SC-007, not because it needs its own CI job.

**Explicitly NOT enforced, with reasons:**

- **Markdown lint (`markdownlint-cli2`)** — checked, and it does not apply: `.markdownlint-cli2.jsonc`'s
  `ignores` list explicitly excludes `kitty-specs/**`, which is where `plan.md` and all three
  tracer files live. Verified by reading the config directly rather than assumed; this is
  genuinely inapplicable to this phase's own doc output, not skipped for convenience.
- **`make lint`** — advisory-only per the charter's own candidate-list annotation ("local
  discipline, not a hard gate"); the *individual* `ruff check` / `mypy --strict` invocations
  above are the real, binding gates per CLAUDE.md's Code Style section.
- **Kernel coverage ≥90%** — not applicable. No file under `src/kernel/` is touched (C-001
  confines the blast radius to `src/charter/` + `tests/charter/`).
- **Mission-loader coverage ≥90%** — not applicable. No mission-loader package file is touched.
- **commitlint** — applies to commit messages, not source files; followed by construction when
  authoring commits (`plan: ...`, `test: ...`, `fix: ...` types per `commitlint.config.cjs`'s
  `type-enum`), not a separate pre-merge invocation against this diff.
- **Doctrine schema freshness** — not applicable. No generated schema artifact exists for
  `DRGGraph`/`DRGNode`/`DRGEdge` in this checkout that this change would leave stale (verified:
  no `*.schema.json` under `src/doctrine/` derived from these models); see Generated Artifacts
  above.
- **Contextive glossary** — not applicable. No new domain term introduced; see Generated
  Artifacts above.
- **`patch()` target validation** — no distinctly-named standalone architectural test for this
  was found in this checkout (a `patch_seam_control` fixture directory exists under
  `tests/architectural/_fixtures/` but no current test references it by that name, as far as
  this plan's investigation could establish). The applicable discipline — patch only real,
  importable seams, e.g. `charter._drg_helpers.load_built_in_graph`, matching the established
  convention in `test_merged_graph_on_live_path.py` — is followed by construction in the new
  tests; not treated as a separately-invoked CI gate for this diff.
- **Bandit** — no subprocess call, `eval`/`exec`, deserialization, or credential handling is
  added; this is a pure in-memory graph-composition change. Runs automatically at the
  repo-wide CI level regardless; no targeted local invocation needed for this specific diff.
- **pip-audit / `uv.lock` freshness** — not applicable. No new third-party dependency is added
  (only existing internal imports: `doctrine.drg.loader.DRGLoadError`,
  `doctrine.drg.validator.duplicate_edge_triples`); `uv.lock` is untouched.
- **SonarCloud Quality Gate** — runs automatically at the CI/PR level; no targeted local
  invocation exists for it. The design pre-empts its usual findings by construction: no
  repeated (≥3×) literal was found in either touched file (checked via an AST scan during
  planning), no empty/effect-free exception handler is introduced (the new `except
  DRGLoadError` in IC-03 always re-raises with content), and every new branch/helper gets a
  focused unit test in the same PR (see Test Strategy below) — the Sonar new-code-coverage
  gate is expected to pass without special local reproduction.

## Baseline: distinguishing pre-existing red from introduced red

Per C-005 and the charter's Test Remediation standing order: `main` carries ~23 known-red
tests and 2 errors (issue #3284) plus a shared pytest test-venv lock that can time out (issue
#3283) — neither is this mission's to fix, and this mission must not file a duplicate for
either.

**Procedure, to run BEFORE the first functional-change commit lands:**

1. On the mission's `planning_base_branch` (before any of this mission's commits), run the
   exact two targeted shards this mission will use throughout:
   `pytest tests/charter/ tests/architectural/ -q` (or `-n auto --dist loadfile` per the
   parallel-run convention in AGENTS.md, if the environment supports it).
2. Record the resulting red set (test IDs + failure summaries) verbatim — this is the
   pre-existing baseline for *this specific mission's targeted surface*, not a hand-wave
   reference to #3284's whole-suite count. It may be a subset of #3284's ~23, since
   `tests/charter/`/`tests/architectural/` is a fraction of the full suite.
3. After each WP's change lands, re-run the same two shards and diff the red set against step
   2's baseline. Only NEWLY red tests (red on this mission's branch, green on the recorded
   baseline) are this mission's to fix — matching AGENTS.md's own "Test-run baseline-red
   gotcha" classification discipline (category 1: pre-existing known-P0 reds; do not "fix"
   them, do not green-wash them).
4. If a #3283-style test-venv lock timeout occurs, that is a CI-environment failure (category 2
   per AGENTS.md), not attributable to this mission's diff — report it as such, do not retry
   into a stale-install false green.
5. This baseline-capture step happens once, is committed to the mission's tracer notes (not
   re-run from scratch per WP), and is distinct from — and precedes — the ATDD red-first
   test-per-FR discipline described in Test Strategy below (that discipline is per-behavior;
   this one is per-mission, whole-shard).

## Campsite-Clean Scope

Per `RECONCILE_CHANGE_SCOPE_TENSIONS`'s resolution order: smallest-viable-diff picks the file
set (`_drg_helpers.py`, `action_doctrine_bundle.py`) first; Boy Scout then governs cleanup
*strictly inside* that file set, without adding files; Locality of Change is the brake against
growing the file set further.

**Domain-matched debt search, performed during this planning phase:**

- Both files were read in full and scanned (via an AST pass over string constants, and a
  manual complexity read of `load_validated_graph` and `_load_action_doctrine_bundle`) for:
  repeated (≥3×) non-trivial literals (Sonar S1192) — **none found** in either file; functions
  near or over the complexity ceiling of 15 — **none found** (`load_validated_graph` is ~15
  lines of straight-line logic; `_load_action_doctrine_bundle` has one linear try/except
  sequence, no deep nesting); empty or effect-free exception handlers — **none present** (the
  one existing `except DRGLoadError` in `action_doctrine_bundle.py` already logs a structured
  WARNING, not a silent pass).
- **Conclusion: no real domain-matched debt worth folding was found in either file.** Per the
  charter's own instruction ("If there is no real domain-matched debt worth folding, say so
  plainly rather than inventing busywork"), this mission does **not** open with a separate
  behavior-preserving campsite-clean commit. The first commit of the mission is the first
  ATDD red test (IC-01's User Story 2 test), per the ATDD-first discipline below — there is no
  distinct preceding cleanup step because there is nothing to clean.

## Test Strategy per Acceptance Criterion

Every AC below is pinned to a concrete test in the new `tests/charter/test_org_root_graph_guard.py`
module (function-level naming is illustrative; exact names are a tasks/implementation-time
decision). Per C-003/ATDD-first, each test is committed RED against `planning_base_branch`
*before* its corresponding implementation commit, and confirmed GREEN on the WP's final commit
— the reviewer verifies this red→green transition, not merely that the test passes today.

| User Story / AC | FR / SC | Test (illustrative name) | Fixture shape | Assertion (concrete, non-vacuous) | Reverted-code check |
|---|---|---|---|---|---|
| US1 AC1 — `drg/`-only pack keeps counts ≥ baseline | FR-001, FR-002, FR-005; SC-001 | `test_drg_only_pack_preserves_or_grows_typed_counts` | tmp repo; `.kittify/config.yaml` declares a pack whose root has **only** `drg/fixture.graph.yaml` (no root `graph.yaml`) | Compute the **no-pack baseline** in the same test (same action, no org pack declared) via `--json`, then assert the with-pack run's `directives`/`tactics`/`styleguides`/`toolguides` counts are each `>=` that dynamically-computed baseline — never a hardcoded magic number, so the test doesn't rot as built-in doctrine grows — **and**, via the plain-text render of the same action, the Procedures section's count is likewise `>=` the plain-text baseline (per the spec ruling's binding split). | Revert IC-01: `load_validated_graph` raises `DRGLoadError` on the drg/-only pack (today's bug) → the `--json` call's typed counts collapse to the swallowed-empty-bundle shape (all four `<` baseline, in fact `== 0`) → test goes RED. |
| US1 AC2 — pack's `drg/`-declared node is actually loaded | FR-002; SC-002 | `test_drg_fragment_node_reaches_resolved_bundle` | same fixture; `drg/fixture.graph.yaml` declares a **`tactic`-kind** node reachable from the resolved action (an edge from the action URN) — pinned to `tactic` specifically, one of the four kinds `--json`'s typed arrays actually expose (directive/tactic/styleguide/toolguide), never `procedure` (per the spec ruling's binding split, `--json` never surfaces a typed `procedures` array to check membership against) | Assert the fixture's specific tactic-kind artifact ID is a **member of** the `--json` payload's `tactics` typed ID list (positive membership, not "no error") | Revert IC-01: org load raises, node never loads → membership assertion fails (ID absent from `tactics`) → RED. |
| US2 AC1+AC2 — genuinely empty pack degrades to exact baseline, indistinguishable from no-pack | FR-001; SC-003 | `test_empty_org_pack_degrades_to_no_pack_baseline` | tmp repo; declared pack directory exists but has no `graph.yaml`/`*.graph.yaml` anywhere (root or `drg/`, and an **empty** `drg/` variant too) | Assert the with-pack run's counts are `==` (not merely `>=`) the no-pack baseline, across all five kinds (four via `--json`, procedures via plain-text) — proves "degrade-to-empty-org-layer, not degrade-to-empty-everything" **and** that empty-drg/-directory and no-drg/-directory-at-all behave identically. No exception raised. | Revert IC-01: `org_root.exists()` alone (today's guard) makes `load_graph_or_dir(org_root)` raise `DRGLoadError` on an empty dir → today's bug (zeroed bundle) → equality-to-baseline assertion fails (counts drop to 0, not equal to baseline) → RED. |
| US3 AC1 — invalid-YAML `drg/` fragment surfaces distinguishably | FR-004; SC-007 | `test_malformed_yaml_drg_fragment_raises_distinguishable_failure` | tmp repo; `drg/broken.graph.yaml` contains invalid YAML syntax | Invoke the `charter context --action <a> --json` CLI entry point (not the internal function) and assert the JSON output has `result != "success"` **and** a non-empty `error` field — a shape User Story 2's genuinely-empty case never produces (that case reports `"result": "success"`) | Revert IC-03: the malformed fragment's `DRGLoadError` is caught by the existing wide catch and silently collapses the bundle → CLI reports `"result": "success"` with zeroed counts, indistinguishable from US2 → assertion (`result != "success"`) fails → RED. |
| US3 AC2 — schema-invalid-but-valid-YAML `drg/` fragment: same distinguishable shape | FR-004; SC-007 | `test_schema_invalid_drg_fragment_raises_same_distinguishable_shape` | tmp repo; `drg/broken.graph.yaml` is valid YAML but violates `DRGGraph`'s schema (e.g. a stray top-level key, or a node missing a required field) | Same assertion shape as AC1 — proves the failure signal is identical regardless of whether the cause was a parse error or a schema violation | Same revert argument as AC1. |
| US4 AC1 — root+`drg/` both present, no conflict: both nodes present | FR-003; FR-006(a); SC-005 | `test_root_and_drg_both_present_neither_node_dropped` | tmp repo; root `graph.yaml` declares node A (kind: **`tactic`**), `drg/fixture.graph.yaml` declares node B (kind: **`directive`**) — distinct URNs, no overlap; both kinds pinned to ones `--json`'s typed arrays actually expose (directive/tactic/styleguide/toolguide), never `procedure` (per the spec ruling's binding split) | Assert A's artifact ID is a **member of** the `--json` payload's `tactics` typed ID list **and** B's artifact ID is a **member of** the `--json` payload's `directives` typed ID list — two independent positive-membership assertions against named typed arrays, not "no exception while iterating a possibly-empty discovered set" (guards against the named vacuity-by-empty-set risk) | Revert IC-02 (imagine a naive "prefer one source" implementation instead of merging): one of A/B is absent → its typed-array membership assertion fails → RED. |
| US4 AC2 — identical edge triple across root+`drg/`: deduped to exactly one, not dropped, no raise | FR-003; FR-006(b); SC-006 | `test_identical_edge_triple_deduped_to_one_not_dropped` | tmp repo; root `graph.yaml` and `drg/fixture.graph.yaml` both declare the exact same `(source, target, relation)` edge triple | Call `_load_org_layer`/`load_validated_graph` directly (not `--json` — the payload doesn't expose raw edges, per the spec's own methodology note) and assert: (a) no `DRGValidationError` raised, **and** (b) the resolved `DRGGraph.edges` filtered to that exact triple has **length exactly 1** — not "no exception" alone (vacuity guard) | Revert IC-02: without dedup, the org-internal merge carries both copies through to the final `assert_valid` → either `DRGValidationError` raises (test's "no raise" assertion fails) or, if the caller special-cased tolerance, the length-1 assertion fails (finds 2) → RED either way. |
| Malformed root-level `graph.yaml` + valid `drg/` sibling: distinguishable failure, not silent zeroing | FR-001, FR-004; closes PLAN-ARCH-001/PLAN-FRESH-002's confirmed gap (remediation option (b)) | `test_malformed_root_graph_with_valid_drg_sibling_raises_distinguishable_failure` | tmp repo; root `graph.yaml` is malformed (invalid YAML or schema-invalid) **and** `drg/fixture.graph.yaml` alongside it is valid and declares a loadable, reachable node | Invoke the `charter context --action <a> --json` CLI entry point (not the internal function) and assert the JSON output has `result != "success"` **and** a non-empty `error` field — the same assertion shape as US3's malformed-`drg/`-fragment rows (`test_malformed_yaml_drg_fragment_raises_distinguishable_failure`), never a baseline-count assertion; a valid `drg/` fragment sitting next to a malformed root graph must not be silently taken down with it. | Revert IC-03's root-level wrap only (leave the `drg/`-level wrap in place): the malformed root graph's plain `DRGLoadError` is caught by the existing wide catch in `_load_action_doctrine_bundle` and silently collapses the *entire* org layer — including the valid `drg/` content — to a zeroed-but-reported-success bundle (today's pre-fix shape) → CLI reports `"result": "success"` → assertion (`result != "success"`) fails → RED. |

**Vacuity-by-empty-set guard, stated explicitly (Standing Order #5 / C-004):** every assertion
above is a **positive membership or exact-count check against a concrete, non-zero or
dynamically-computed floor** — never "the loop found no violations" over a set that could
trivially be empty. The US4 AC1 test in particular asserts membership of two *specific* IDs
individually, not "for every discovered node, no conflict was found" (which would pass
vacuously if node discovery itself silently returned nothing).

## Non-Vacuous Gate for the Defect Class (Standing Order #5 / C-004)

The reported bug's shape: a code path composes an optional graph-content source without first
checking whether that source has anything loadable, so "nothing to load" and "content exists"
both hit the same unconditional loader call — the loader raises on the former, and the
call site's `except DRGLoadError` silently collapses that into an empty-but-reported-success
bundle.

**What a NEXT instance of this defect class would look like**, and why FR-005's test catches
it: imagine a future mission adds a *third* optional org-pack content location (say,
`<org_root>/overlays/`) and forgets to gate its "nothing found" case the same way — it calls
`load_graph_or_dir(overlays_dir)` unconditionally whenever `overlays_dir.exists()`, exactly
reproducing #3384's shape one directory over. FR-005's regression test (`test_drg_only_pack_...`
and its US2 sibling) does not merely check "no exception was raised" — it asserts a **concrete
numeric floor**: the four typed counts must be `>=` a dynamically-computed real baseline (not
`>= 0`, which would be vacuously true always). If the new overlay path's bug reintroduces
silent zeroing for *any* pack shape the existing fixtures exercise, the floor assertion goes
RED because the with-pack counts drop below the baseline — the same signal that would have
caught #3384 itself had this test existed beforehand. The gate is non-vacuous specifically
*because* the floor is a real, non-zero, freshly-computed number every run, not a placeholder
like "count > -1" or "no traceback printed."

## Silent Success Discipline (User Story 3 / FR-004)

Stated explicitly: when the changed code **cannot** do its job — org-layer content, whether the
root-level graph or a `drg/` fragment, that is invalid YAML or fails `DRGGraph` schema
validation — it does **not** return `None`, `0`, or an empty bundle and call it success. It
raises `OrgDRGFragmentError` (chained from the original
`DRGLoadError` via `from exc`, preserving the underlying diagnostic), which is a distinguishable
exception type by construction (not a `DRGLoadError` subclass), and that exception is left
**uncaught** all the way to the CLI's existing Typer error boundary, which reports
`{"result": "error", "success": false, "error": "<message>"}` in `--json` mode or a red
`Unexpected error: ...` line with exit code 1 otherwise. This is a hard, structural
distinguishing signal — not a log-level bump, not a warning that still reports success (the
exact vacuous "fix" C-004 warns against).

## `__all__` Export Discipline (C-007 / C-002)

Three new module-level names are introduced in `src/charter/_drg_helpers.py`:

| Symbol | Kind | Added to `__all__`? | Rationale |
|---|---|---|---|
| `_load_org_layer` | function | No | Leading-underscore name; only called from `load_validated_graph` in the same module. No external `src/` caller. |
| `_dedup_org_layer_edges` | function | No | Leading-underscore name; only called from `_load_org_layer` in the same module. No external `src/` caller. |
| `OrgDRGFragmentError` | exception class | **No** | Not underscore-prefixed by name, but deliberately kept **out** of `__all__`: it is raised inside `_load_org_layer` and is designed to propagate **uncaught** through every intermediate `src/` caller (`load_validated_graph`, `_load_action_doctrine_bundle`) all the way to the CLI's generic `except Exception` boundary — by design, **no other `src/` module ever needs to import and catch it by name**. Per C-002's own rule ("kept module-private... no leading-underscore-free name added to `__all__` without a caller in `src/`"), the correct choice is to leave it off `__all__`, not to force it in for symmetry. Regression tests import it directly via `from charter._drg_helpers import OrgDRGFragmentError` (or assert on its `type(exc).__name__` at the CLI-output boundary) — test-only imports don't require `__all__` membership and are explicitly not counted by `tests/architectural/test_no_dead_symbols.py`'s own caller search (which only scans `src/`, by design). This is a considered decision, verified against the actual gate's mechanics (`tests/architectural/test_no_dead_symbols.py`'s module docstring), not an afterthought. |

`_drg_helpers.py`'s existing `__all__ = ["load_validated_graph"]` is **unchanged** by this
mission.

## PR Shape

**One PR, not one-PR-per-work-package** (binding decision #5). This mission is right-sized for
a single PR: the entire functional change is one function's evolution
(`load_validated_graph`'s org-layer branch, factored into `_load_org_layer` +
`_dedup_org_layer_edges` + `OrgDRGFragmentError`, all in one existing ~100-line file), a
documentation-only touch in one sibling file, and one new test module covering four User
Stories. This is not remotely close to the scale that would warrant recommending a split to
the operator — no such recommendation is being made. IC-01 → IC-02 → IC-03 sequencing (each
building on the same function's growing body) means `/spec-kitty.tasks` will likely produce a
small number of WPs (plausibly even a single WP, given how tightly coupled the three concerns
are structurally) rather than three independent ones; that WP-count decision belongs to the
tasks phase, not this plan.
