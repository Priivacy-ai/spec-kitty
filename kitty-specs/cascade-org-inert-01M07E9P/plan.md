# Implementation Plan: Cascade Org Inert

**Branch**: `pr/up-cascade-org-inert` | **Date**: 2026-08-17 | **Spec**: `kitty-specs/cascade-org-inert-01M07E9P/spec.md`
**Input**: Feature specification from `kitty-specs/cascade-org-inert-01M07E9P/spec.md`

**Branch contract (repeated per the mandatory confirmation, stated once here and again in the
final report)**: `current_branch` = `target_branch` = `base_branch` = `planning_base_branch` =
`merge_target_branch` = **`pr/up-cascade-org-inert`** (per `setup-plan --json`'s
`branch_matches_target: true`). This branch is itself based on
`origin/pr/up-org-doctrine-consumers-01M05YAB` (PR #3520), not `main` — see spec.md's
Base-Branch Drift section; this plan does not repeat that section's content, only its consequence
for sequencing (below).

## Summary

Three functional requirements, all in `spec.md`, all real bugs confirmed live and (for FR-002's
first-draft fix) re-derived after an adversarial review caught the original fix as inert:

- **FR-001**: thread `resolve_existing_org_roots(repo_root)` into the three cascade
  `load_validated_graph` call sites (`activate.py:226,317`, `deactivate.py:139`) that currently
  carry no org roots at all, and widen `resolve_layer_roots`'s ID-mapping past its first-match
  `break` — back-compat-preserving for its third consumer, `charter list --all-layers`.
- **FR-002**: stop `context.py`'s CLI command from truncating the resolved org-pack chain to
  `org_roots[0]` before it ever reaches either `build_charter_context` (plain-text) or
  `build_charter_context_json`, AND swap `build_charter_context_json`'s internal call from the
  private `_load_action_doctrine_bundle` to the self-resolving `_resolve_action_bundle` — both
  changes required together, neither alone closes the gap.
- **FR-003**: make `dossier/rebaseline.py` org-aware by deriving `repo_root` per-snapshot from
  `feature_dir.parent.parent` inside `rebaseline_snapshot_file`, rather than leaving
  `Indexer(ManifestRegistry())` permanently `repo_root=None`.

Scope item 4 (the `load_validated_graph` project/org guard asymmetry and its whole-bundle-collapse
consequence) was investigated, live-reproduced, and then **retired from this mission's scope**
once the orchestrator confirmed it is already fixed in open PR #3401 — see spec.md's "Out of
Scope" section and Constraint C-006. This plan does not design, and no work package below
implements, anything for that defect class.

**Technical approach**: every fix is a **caller-side parameter-threading change** — no new
abstractions, no schema changes, no new modules. The shared primitives
(`resolve_existing_org_roots`, `_resolve_action_bundle`, `Indexer.__init__`'s `repo_root` param)
already exist on this branch (introduced by #3520/#3525); this mission's job is exclusively to
call them from the sites that currently don't. FR-001's ID-mapping widening
(`resolve_layer_roots`) is the only place introducing new *shape* (an additive field on an
existing `dict[str, Path]` return value), and it is deliberately additive/back-compat-preserving
per spec.md's third-consumer analysis.

## Technical Context

**Language/Version**: Python 3.11+ (repo `pyproject.toml` `requires-python = ">=3.11"`; this
checkout runs 3.14.6 locally, `.venv` pinned with pytest 9.0.3)
**Primary Dependencies**: `typer` (CLI), `rich` (console), `ruamel.yaml` (frontmatter/YAML),
`pydantic` (DRG node/graph models) — all already in use by the touched modules; this mission adds
no new dependency.
**Storage**: N/A — no database. Touched persistence is filesystem-only: `.kittify/config.yaml`
(org-pack registration, read-only for this mission), DRG YAML fragments (read-only), and
`.kittify/dossiers/<slug>/snapshot-latest.json` (read + rewrite, FR-003, unchanged serialization
format).
**Testing**: `pytest` via `.venv/bin/python -m pytest` (never bare `pytest` — CLAUDE.md's
`spec-kitty` shell-out gotcha; a stale install reports false reds until `pip install -e .` reruns
after any packaging-relevant change, which this mission does not make). Charter's own "targeted
packages" rule (Testing Requirements) applies: this mission's changes are scoped to
`src/specify_cli/cli/commands/charter/`, `src/charter/`, and `src/specify_cli/dossier/`, so the
targeted surface is `tests/charter/`, `tests/specify_cli/cli/commands/charter/`, and
`tests/dossier/` — all three verified live to exist on this branch (see Project Structure's test
tree below for the specific files within each). Not the full `tests/` suite. The full suite is
reserved for
release-candidate verification, not this mission.
**Target Platform**: spec-kitty CLI, cross-platform (Linux/macOS/Windows), no platform-specific
code touched by this mission.
**Project Type**: single project (the spec-kitty CLI repository itself) — no web/mobile split.
**Performance Goals**: NFR-001 — no measurable regression in `<2s typical-project` CLI performance
from threading org roots through; the DRG-merge work already happens for other callers
(`gate_bindings.py`) at comparable cost, so this is an "extend an existing cost to new call sites,"
not a new cost class.
**Constraints**: C-001 (`_resolve_org_root` stays inert — architectural boundary,
`test_layer_rules.py`-enforced), C-002 (existing shared-reference-safety "C-005" contract, an
external reference — not renumbered by this mission), C-003 (no unverifiable numbers), C-004 (D2
stays closed, do not resurrect), C-006 (item 4 not duplicated, PR #3401 owns it).
**Scale/Scope**: 3 FRs, 3 call-site families (cascade ×3, context ×2 internal functions behind 1
CLI command, rebaseline ×1), all within `src/charter/`, `src/specify_cli/cli/commands/charter/`,
and `src/specify_cli/dossier/`. No cross-repo, no cross-package contract change.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design (below).*

Governance context loaded per `spec-kitty charter context --action plan --json` bootstrap
requirement (this plan session ran that step before drafting; see the mission's own investigation
trail for the resolved directives — `DIRECTIVE_001` architectural-integrity, `DIRECTIVE_024`
locality-of-change, `DIRECTIVE_025` boy-scout/campsite, `DIRECTIVE_044` canonical-source-unification
all apply directly, per the Governance-by-Workflow-Action table's "Specify / Plan" row).

Charter-relevant checks, each answered explicitly (no silent pass):

- **Single canonical authority (reconcile, don't duplicate)**: FR-002's Design Notes require
  routing through the EXISTING `_resolve_action_bundle` wrapper rather than re-implementing
  self-resolution inline in `context.py` — reconcile-don't-duplicate applied directly. Item 4's
  retirement (C-006) is the same principle applied at mission-scope granularity: an existing
  in-flight fix (#3401) is reconciled with (deferred to), not duplicated. **PASS.**
- **Architectural alignment**: no boundary crossed. `_resolve_org_root` in `charter/_drg_helpers.py`
  stays inert (C-001); all fixes are `specify_cli`-layer caller changes, exactly where the
  architecture (per `_drg_helpers.py`'s own docstring) says they belong. **PASS.**
- **Domain-driven splits + tiered rigour**: the touched code is all "glue" (CLI command → shared
  service function), not core domain logic (the DRG merge/validate logic itself is untouched) — a
  lighter rigour tier applies appropriately; the plan does not over-engineer new abstractions for
  what is, in every case, a missing-argument bug. **PASS.**
- **ATDD-first (C-011, binding)**: every WP below is red-first — a failing test pinning the
  user-observable defect (multi-pack content invisible, org root never threaded) committed BEFORE
  the fix commit, on this WP's own branch state, red on the WP's `planning_base_branch`
  (`pr/up-cascade-org-inert`) and green on the WP's final commit. Stated per-WP below (Phase 1).
- **Campsite cleaning (Standing Order #2)**: assessed and explicitly scoped OUT as a distinct
  step — see "Campsite-Clean Scope" below.
- **Terminology canon**: no `feature*` aliases introduced (grepped spec.md, confirmed clean in the
  spec-fix round); this plan and the resulting tasks must carry the same discipline — `Mission` not
  `Feature`, verified again at tasks-authoring time.
- **Silent-success is this repo's dominant failure mode (NFR-002)**: every fix path either raises
  or is threaded through a primitive that already warns (`resolve_existing_org_roots`,
  `resolve_org_dirs`'s WARNING-per-dropped-root sibling). No new silent-`None`/silent-`0` path is
  introduced by any of the three FRs. **PASS**, verified per-WP in Phase 1's test strategy below.
- **Ledger** (`SPEC-KITTY-LEDGER.md`): spec.md's Reflexivity section already states no prior entry
  was found for this defect class; unchanged at plan time. If tooling friction surfaces during
  implementation, the ledger gets an entry then, per the mission's own operating discipline (not
  this plan's job to pre-empt).

**No Charter Check violations** — the Complexity Tracking table below is therefore empty (no
justification needed).

## Project Structure

### Documentation (this mission)

```
kitty-specs/cascade-org-inert-01M07E9P/
├── spec.md                     # committed (2 fix rounds: 6 review findings + item-4 retirement)
├── plan.md                     # this file
├── tasks.md                    # Phase 2 output (a later /spec-kitty.tasks step, not this plan)
├── tasks/README.md             # scaffold placeholder, present since specify
├── reviews/                    # spec-phase R1-R6 trail (committed); plan-phase trail lands here too
├── tracer-tooling-friction.md  # seeded this plan phase (Standing Order #3)
├── tracer-approach.md          # seeded this plan phase
└── tracer-design-decisions.md  # seeded this plan phase
```

No `research.md` / `data-model.md` / `contracts/` / `quickstart.md` are produced by this plan:
there is no new data model (no new persisted schema — FR-003 rewrites the SAME
`snapshot-latest.json` shape it already writes today), no new external contract (no OpenAPI/CLI
JSON-surface change — `charter context --json`'s payload shape is unchanged, only its *content*
gains pack-2+ entries it was always supposed to have), and no genuinely open research question
(every technical question the spec raised was resolved with an explicit recommendation and
rationale during the spec phase, not deferred as `[NEEDS CLARIFICATION]`). Producing empty
placeholder files for these would be padding, not signal — Locality of Change (`DIRECTIVE_024`)
favours the smaller, real deliverable set.

### Source Code (repository root) — Option 1: Single project

```
src/
├── charter/
│   ├── _drg_helpers.py                 # load_validated_graph, _resolve_org_root — UNCHANGED (C-001)
│   ├── context.py                      # build_charter_context, build_charter_context_json — FR-002
│   └── action_doctrine_bundle.py       # _resolve_action_bundle, _load_action_doctrine_bundle — FR-002
├── specify_cli/
│   ├── cli/commands/charter/
│   │   ├── activate.py                 # _render_cascade_activation, _render_no_cascade_warning — FR-001
│   │   ├── deactivate.py               # _render_cascade_deactivation — FR-001
│   │   ├── _layer_roots.py             # resolve_layer_roots — FR-001 (ID-mapping widening)
│   │   ├── context.py                  # context() CLI command — FR-002 (stop pre-truncating)
│   │   └── list_cmd.py                 # UNCHANGED — third resolve_layer_roots consumer, back-compat only
│   └── dossier/
│       ├── rebaseline.py               # rebaseline_snapshot_file, _resolve_feature_dir — FR-003
│       └── indexer.py                  # Indexer.__init__(repo_root=...) — UNCHANGED, already supports it (#3520)

tests/
├── charter/                             # test_context*.py (18 files, incl. test_context_org_governance.py, test_org_activations_reach_context.py) — verified live to exist
├── specify_cli/cli/commands/charter/    # test_charter_activate_commands_{core,cascade_flags,cascade_output}.py, test_charter_deactivate_commands.py, test_charter_list_commands.py, test_activate_preserve.py — verified live to exist
└── dossier/                             # test_rebaseline.py — verified live to exist at tests/dossier/test_rebaseline.py
```

**Structure Decision**: single project, no new directories or modules. This mission edits 6
existing files (3 for FR-001, 2 shared for FR-002 [`charter/context.py` +
`cli/commands/charter/context.py`], 1 for FR-003) and adds test coverage to the existing test
files/directories that already cover them — no new top-level package.

## Complexity Tracking

*Empty — Charter Check found no violations to justify.*

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into
> executable WPs.

### IC-01 — Cascade org-roots threading + layer-roots ID-mapping widening (FR-001)

- **Purpose**: make `charter activate/deactivate --cascade` see and correctly ID-map
  `requires`/`suggests` edges that live in or target any configured org pack, including pack 2+ of
  a chain, without breaking `charter list --all-layers`'s existing pack-1-only consumption.
- **Relevant requirements**: FR-001 (all 7 ACs), User Stories 1-3, NFR-001, NFR-002, C-001, C-002.
- **Affected surfaces**: `src/specify_cli/cli/commands/charter/activate.py` (two call sites,
  `_render_cascade_activation` and `_render_no_cascade_warning`),
  `src/specify_cli/cli/commands/charter/deactivate.py` (`_render_cascade_deactivation`),
  `src/specify_cli/cli/commands/charter/_layer_roots.py` (`resolve_layer_roots`'s return shape).
  `list_cmd.py` is READ (to confirm the back-compat contract) but not edited.
- **Sequencing/depends-on**: none structurally (disjoint files from IC-02/IC-03) — but see the
  mission-level sequencing recommendation under IC-03's entry: front-load IC-03's investigation
  before committing to a WP order, per the charter's "risky/unknown work front-loaded" phasing
  principle.
- **Risks**: the additive-field shape for `resolve_layer_roots` (keep `roots["org"]` as a single
  `Path`, add a new key for the chain) must be picked BEFORE the three call sites are edited, since
  both `activate.py`'s two functions and `deactivate.py`'s one function consume the same new field
  — implement `_layer_roots.py`'s shape change first, in its own commit, before threading the
  cascade call sites, so the cascade-site commits have a stable target to code against. A
  regression test for `list_cmd.py`'s continued pack-1-only behavior over a 2-pack chain is
  required (User Story 3 AC4) even though `list_cmd.py` itself is not edited — this is the
  "prove the back-compat claim, don't just assert it" discipline C-related findings in the spec
  review demanded.

### IC-02 — Context bundle: stop CLI-level truncation + route JSON path through the self-resolving wrapper (FR-002)

- **Purpose**: make BOTH `spec-kitty charter context` (plain-text) and `--json` reflect the full
  org-pack chain, not just pack 1 — closing the gap the spec's own adversarial review caught the
  first drafted fix as inert against.
- **Relevant requirements**: FR-002 (all 4 ACs + Design Notes), User Story 4 (all 5 scenarios).
- **Affected surfaces**: `src/specify_cli/cli/commands/charter/context.py` (the `context()` CLI
  command, lines ~84-134 — stop precomputing `org_root = org_roots[0]`, pass `org_root=None`
  through to both downstream calls, keep `org_roots` unchanged for
  `load_org_charter_json_block`), `src/charter/activation/context.py` (`build_charter_context_json` — swap
  its internal `_load_action_doctrine_bundle` call for `_resolve_action_bundle`).
- **Sequencing/depends-on**: none — self-contained. Independent of IC-01 and IC-03 (disjoint files).
- **Risks**: THIS IS THE CONCERN WHERE THE SPEC'S OWN REVIEW CAUGHT AN INERT FIX (SPEC-ARCH-002).
  The implementer must NOT stop at swapping the internal function call — both changes (CLI-level
  truncation removal AND the internal swap) are required together, and the WP's own red-first test
  must assert pack-2 content present in BOTH plain-text and JSON output, run against the change
  with EACH half applied alone first (to prove neither half alone is sufficient — an empirical,
  not asserted, proof) before both are applied together and the test goes green. This is the
  concrete implementation of spec.md's "prove the new fix is not also inert" instruction.

### IC-03 — Dossier rebaseline org-awareness via per-snapshot `repo_root` derivation (FR-003)

- **Purpose**: make `migrate rebaseline` consult a configured org pack's `expected-artifacts.yaml`
  override (via `ManifestRegistry.load_manifest`), consistent with `reconcile` and
  `sync/dossier_pipeline`, instead of the current permanent `repo_root=None`.
- **Relevant requirements**: FR-003 (all 5 ACs + Design Notes + the worktree open question), User
  Story 5.
- **Affected surfaces**: `src/specify_cli/dossier/rebaseline.py`
  (`rebaseline_snapshot_file` — derive `repo_root = feature_dir.parent.parent` and pass it to
  `Indexer(ManifestRegistry(), repo_root=repo_root)`).
- **Sequencing/depends-on**: **BLOCKED on resolving the worktree open question FIRST** (spec.md
  FR-003 Design Notes) — this is not optional sequencing, it changes the correctness of the fix.
  Concretely: before writing the `feature_dir.parent.parent` derivation, the assigned WP must
  determine (by reading `src/specify_cli/workspace/context.py`'s `resolve_workspace_for_wp` and
  the worktree layout it creates, per CLAUDE.md's "Execution Workspace Strategy" section) whether
  a spec-kitty execution worktree (`.worktrees/<slug>-<mid8>-lane-<id>/`) ever contains its own
  `kitty-specs/<slug>/.kittify/dossiers/...` tree distinct from the primary checkout's. **Two
  outcomes, both acceptable, neither silent**: (a) if worktrees never carry dossier snapshots
  (dossier/rebaseline only ever runs against the primary/coord checkout — plausible, since
  `migrate rebaseline`'s sole caller resolves `repo_root` via `locate_project_root()` from wherever
  the operator invoked `spec-kitty migrate`, and `migrate` is a primary-checkout-only command
  family per the Merge & Preflight Patterns section of CLAUDE.md), derivation (B) as specced is
  correct as-is and the WP documents the finding with the file:line evidence it found; (b) if
  worktrees CAN carry dossier snapshots, the WP must design a worktree-aware correction (e.g. via
  `git rev-parse --path-format=absolute --git-common-dir` or an equivalent superproject-root
  resolution) before implementing FR-003, and document why.
- **Risks**: this is the mission's only IC where the "correct implementation" is not fully
  determined by the spec — the worktree investigation genuinely gates what code gets written.
  Do not let time pressure collapse this into "just derive it and hope" — the spec is explicit
  that assuming single-checkout-only without checking is not acceptable.
- **Mission-level sequencing recommendation (seq-lens finding, applied at authoring time rather
  than left for a review round)**: IC-03 carries the mission's only unresolved unknown (the
  worktree question) — per the charter's phasing principle ("risky/unknown work front-loaded"),
  the tasks phase should schedule IC-03's investigation FIRST among the three WPs, even though
  IC-01/IC-02 have no structural dependency on it. Rationale: if the investigation finds outcome
  (b) — worktrees CAN carry dossier snapshots — FR-003's design changes materially (a
  worktree-aware correction is needed instead of the two-fixed-parent-hops derivation), which is
  useful to know before tasks.md locks in a specific WP description for FR-003, not after.

## Test Strategy (per FR, red-first, revert-fails)

- **FR-001**: two-pack chain fixture with a cross-pack `requires` edge (User Story 1 AC2 / FR-001
  AC2) is the primary red-first test — it fails on `pr/up-cascade-org-inert`'s current HEAD (org
  roots never threaded) and must pass after the fix. A SEPARATE revert-test: temporarily revert
  only the `resolve_layer_roots` widening (keep the three call-site threading) and confirm the
  pack-2 ID-mapping test still fails — proves the widening, not just the threading, is what the
  test exercises (guards against a vacuous pass where the cascade-graph-visibility fix alone
  happens to satisfy a loosely-written assertion). `list_cmd.py`'s regression test (User Story 3
  AC4) is a required companion, not optional.
- **FR-002**: per IC-02's Risks note above — the red-first test must independently prove BOTH
  halves are necessary (apply (a) alone → still red; apply (b) alone → still red; apply both →
  green) before the WP is considered done. This is stricter than the charter's default
  revert-discipline (one test that fails when the WHOLE change is reverted) because the mission's
  own review history shows a whole-change-only test would NOT have caught the first inert fix
  (SPEC-ARCH-002's finding was that a plausible fix passed inspection but not code-tracing).
- **FR-003**: red-first test asserting `Indexer` receives a non-`None` `repo_root` matching the
  project root after rebaseline runs (SC-005) — must fail on current HEAD (`Indexer(ManifestRegistry())`
  with no `repo_root`) and pass after the fix. A separate test for the "no org pack configured"
  regression case (FR-003 AC2) must stay green throughout — this is the WP's own revert-discipline
  companion (a test that would fail if the derivation accidentally broke the org-agnostic path).

**Baseline discipline for every WP** (SC-004, CLAUDE.md's baseline-red gotcha): before any WP's
first commit, run the WP's targeted test files (per Technical Context's "Testing" note) on the
WP's `planning_base_branch` HEAD (`pr/up-cascade-org-inert` at commit `63e9da4c9`, this plan's own
commit-to-be, or whatever the branch tip is when the WP actually starts — re-check, don't assume
staleness) and record which tests are already red. #3284's 23 failures / 2 errors are a repo-wide
number; this mission's targeted-file baseline is almost certainly a small subset of that (or
zero) — the WP must state the actual number it found, not cite #3284's repo-wide figure as its own
targeted baseline.

## Gate Set (from the hub's gate table, per sk-design's plan-phase rule)

| Gate | Included? | Rationale |
|---|---|---|
| `ruff check .` | **Yes** | Advisory in CI but mandatory local discipline (charter, CLAUDE.md). Run via `uvx ruff check` per workspace prep note — never bare `uv run`, which re-syncs and destroys the hand-built `.venv`. |
| Targeted pytest shards (`tests/charter/`, `tests/specify_cli/cli/commands/charter/`, `tests/dossier/`) | **Yes** | Per Testing Requirements' "targeted packages for scoped changes" rule — this mission is exactly that scoped case. |
| Full `pytest tests/` | **No** | Reserved for post-merge mission-level validation, cross-cutting changes touching shared infra, or release-candidate verification — none of which this mission is. If the plan or a later phase discovers this mission's blast radius is wider than believed, this decision is revisited explicitly, not silently expanded. |
| `mypy --strict` | **Yes, with a verified pre-existing baseline to not misattribute** | Charter's binding Testing Requirements ("mypy --strict must pass"); this mission's changes are all typed function signatures gaining/threading `Path`/`list[Path]` arguments — a natural mypy surface. **Checked live** (`.venv` lacks mypy; ran via `uvx --with-requirements pyproject.toml mypy --strict <files>`, which works and should be the invocation WPs reuse): `src/charter/activation/context.py` (FR-002 target) already carries 6 PRE-EXISTING `no-any-return` errors (lines 250/336/342/351/365/376, unrelated to this mission's edit sites) on this branch's current HEAD; `src/specify_cli/cli/commands/charter/context.py:19` already carries 1 PRE-EXISTING `untyped-decorator` error (the Typer `@app.command()` decorator, a repo-wide pattern, not specific to this file). Neither FR-002 WP is required to fix these (baseline-red-gotcha, applied to mypy the same as pytest) but must run this exact mypy invocation before AND after its change and confirm it introduces no NEW error beyond this baseline — a WP that reports "mypy clean" without having run it, or that silently inherits a NEW error into this pre-existing count, fails this gate. |
| kernel coverage ≥90% / mission-loader coverage ≥90% | **No** | This mission touches neither `src/kernel/` nor the mission-loader surface — the coverage floors do not apply to the files this mission changes. |
| commitlint | **Yes (inherited)** | Every commit already follows `<type>(scope): summary` per this branch's own commit history; no special action needed, just discipline maintained per WP commit. |
| markdown lint | **Yes (inherited)** | `spec.md`/`plan.md`/`tasks.md` are markdown; no code-block or heading-structure violations introduced — verified informally by this plan's own structure matching the canonical template. |
| architecture/docs consistency, doctrine schema freshness, Contextive glossary | **No** | This mission adds no new doctrine schema, no new glossary term, no new architecture doc — these gates have nothing new to check. |
| TID251 banned-API, Typer JSON error surface, `patch()` target validation | **No** | No new banned-API usage, no new Typer command/flag, no new test `patch()` target introduced by threading existing function parameters. |
| Bandit, pip-audit, `uv.lock` freshness | **No** | No new dependency, no new subprocess/eval/credential-handling code path. |
| SonarCloud Quality Gate | **Yes (passive)** | Applies to every PR by default; this mission's diff is small parameter-threading changes unlikely to trip complexity/duplication thresholds, but the gate still runs — no special mission action required beyond keeping functions under the complexity ceiling (15) while editing them, per CLAUDE.md's Sonar Expectations. |

**"We'll run the tests" is not a gate statement** (per sk-overlay's own instruction) — the above
table is the gate statement; each WP's own task description (Phase 2) restates its OWN slice of
this table with the exact test files it targets.

## Campsite-Clean Scope (Standing Order #2)

Assessed and explicitly scoped OUT as a distinct opening step for this mission, checked live
rather than assumed: `uvx ruff check --select C901` (the complexity gate, ceiling 15 per
`pyproject.toml`'s `[tool.ruff.lint.mccabe]`) against all seven touched files (`activate.py`,
`deactivate.py`, `_layer_roots.py`, `charter/context.py`, `cli/commands/charter/context.py`,
`rebaseline.py`, `action_doctrine_bundle.py`) returned **zero violations** — "All checks passed!".
Two of the three cascade-renderer functions this mission touches are moderately sized
(`_render_cascade_activation` 58 lines, `_render_cascade_deactivation` 54 lines — not "a handful,"
correcting an earlier overstatement in this section's first draft) but neither trips the
complexity ceiling; the size is sequential rendering logic (loop + try/except + console.print
calls), not branching complexity, so it is not the kind of debt Standing Order #2 targets. A
dedicated campsite-clean commit would therefore have nothing domain-matched to fold, and forcing
one would itself be a violation of Locality of Change (`DIRECTIVE_024`) — manufacturing scope
where none exists. If a WP implementer finds debt in these files while working (a `ruff C901` pass
is not a substitute for reading the code with intent to change it), the Boy Scout Rule still
applies opportunistically within the touched file set, per the charter's
standing reconciliation order — proportional, in-file, one-line-rationale — not as a separate
mission phase.

## Tracer Files (Standing Order #3, seeded this phase)

Seeded now (see the three files listed under "Documentation (this mission)" above); each carries
this plan's own friction/approach/decisions, and is appended-to (not overwritten) during
implementation:

- **`tracer-tooling-friction.md`**: records the `event journal capture failed: project sync store
  is locked` / `Explicit-context event capture failed: machine layout cutover did not publish
  within the bounded wait` warnings seen on every `spec-kitty specify`/`plan` invocation this
  mission ran (non-blocking, but recurring — worth tracking in case it compounds for other
  concurrent missions on this machine, per this programme's ledger-of-friction discipline).
- **`tracer-approach.md`**: records the two-round spec-fix history (6 adversarial-review findings,
  then item-4 retirement after the orchestrator's PR #3401 discovery) as the approach rationale for
  why this plan's scope is exactly 3 FRs, not 4.
- **`tracer-design-decisions.md`**: records the additive-field decision for `resolve_layer_roots`
  (IC-01), the two-changes-required-together decision for FR-002 (IC-02), and the
  worktree-investigation-gates-the-fix decision for FR-003 (IC-03) — the three genuinely
  non-obvious design calls this plan makes.

## Reflexivity Check (Charter Check re-run after Phase 1 design)

Re-confirmed after drafting the Implementation Concern Map: no new charter violation introduced by
the concrete design above. `_resolve_org_root` remains untouched (IC-01/02/03 all thread roots at
the `specify_cli` layer, never inside `charter/_drg_helpers.py`). No new silent-failure path
introduced (IC-02's explicit two-half test design is itself an anti-silent-inertness gate). The
`resolve_layer_roots` additive-field shape is the only structural change, and it is
back-compat-preserving by design (IC-01's Risks note). **PASS, unchanged from the pre-design gate
above.**
