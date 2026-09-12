# Mission Specification: Org-Pack Authoring Diagnostics

**Mission Branch**: `feat/org-pack-authoring-diagnostics-3387`
**Created**: 2026-08-13
**Status**: Draft
**Input**: Upstream issue [`Priivacy-ai/spec-kitty#3387`](https://github.com/Priivacy-ai/spec-kitty/issues/3387) — *"Org-pack authoring fails silently: guide-named step contracts never load but are counted, misfielded profiles skipped, validation skips what the runtime reads"* — plus binding operator decisions delivered against a readiness probe's findings (Researcher Robbie). The issue states it verified its claims on `main @ 4a2367539`; this spec re-verified every cited code path directly against the checkout's current `main @ ab0a0b9b5` (`4a2367539` is an ancestor — `git merge-base --is-ancestor 4a2367539 ab0a0b9b5` succeeds, no drift affects the cited files). One issue claim is corrected below (Clarification 2) and one issue citation is corrected in-place (see "Verified Code Surfaces," snapshot.py).

---

## Clarifications

### Session 2026-08-13

- **Q1 (Defect #1 — step-contract glob/suffix mismatch, and whether to fix it on the legacy `MissionStepContract` surface given the accepted-but-not-yet-implemented retirement ADR):** Should this mission fix the `*.contract.yaml` vs `*.step-contract.yaml` mismatch on the legacy `step_contracts.py` surface now, or defer to PR #3378's `MissionStep` unification?
  **A1 — Decision: fix it now, on the current legacy `MissionStepContract` / `step_contracts.py` surface.** Scope: a shared suffix constant consumed by `step_contracts.py`, `pack_validator.py`, and the snapshot bucket table (see correction below); the guide correction at `docs/guides/how-to/governance/create-an-org-doctrine-pack.md:65` and `:140` (currently document `*.contract.yaml`, must match the loader's actual `*.step-contract.yaml`); and a regression test proving that a contract file authored with the guide's old, incorrect suffix now produces a named diagnostic instead of silent non-loading.
  **Rationale:** this closes a live, guide-matching authoring trap that every pack author following the *currently published* guide hits today. Open PR #3378 carries ADR `docs/adr/3.x/2026-08-13-1-built-in-mission-subtree-stays-nested-retire-legacy-step-contracts.md`, which decides to retire the entire `MissionStepContract` / `step_contracts.py` surface in favor of a unified `MissionStep` model. Re-verified directly against PR #3378's current head commit (`37a38274…`; `gh pr view 3378` confirms `state: OPEN`, unmerged) rather than trusting an earlier read: this specific ADR's frontmatter and body both read `status: Accepted`, `**Status:** Accepted`, `**Date:** 2026-08-13`, `**Deciders:** Operator (ATDD)` — **the retirement decision is ratified**, unlike the other five ADRs bundled into the same PR (`2026-08-13-2` through `-6`, the gate ADRs), which genuinely remain `Proposed`. What has **not** happened is the *implementation*: PR #3378 is a docs-only design-review PR (no code changes) and is unmerged, so `step_contracts.py` / `MissionStepContract` still exist on `main`, unchanged, today; the ADR's own "Confirmation" section names a large, not-yet-started cross-cutting migration (~45 src files + ~40 test files) as the precondition for actually deleting the surface. **This mission deliberately proceeds on the legacy surface because the retirement, while decided, has not been executed.** When that migration lands and `step_contracts.py` is deleted, this fix (a handful of lines plus one test file) is deleted with it at negligible sunk cost — named here so a reviewer does not discover the tension unaided and file it as scope drift.
  **Superseded by binding operator ruling (2026-08-13, `reviews/spec.ruling.md`):** the code-change scope described in this A1 (shared suffix constant, validator mismatch diagnostic, `_ARTIFACT_BUCKETS` removal) is dropped. FR-001 below is narrowed to the guide correction only, documentation-only, per that ruling and ADR `2026-08-13-1`. This A1 is preserved verbatim as the historical record of the 2026-08-13 clarification session; it no longer states FR-001's current scope — see the ruling and FR-001's requirement text for the binding scope.

- **Q2 (Defect #2 — misfielded agent profiles silently skipped; is the issue's "`pack validate` passes" claim still true?):** Is it still true, on this checkout, that `pack validate` passes silently for a misfielded (extra-key) agent-profile YAML, as the issue claims?
  **A2 — Decision: the claim is FALSE on this checkout; corrected scope below.** `src/doctrine/agent_profiles/profile.py:258` (`AgentProfile.model_config = ConfigDict(extra="forbid", populate_by_name=True)`) was added by commit `f732e10d6` ("feat(WP04): GREEN — forbid undeclared fields, derive the writers from the model"), dated 2026-07-27 — an ANCESTOR of `4a2367539` (`git merge-base --is-ancestor f732e10d6 4a2367539` succeeds; re-verified directly on this checkout, not merely asserted). `pack validate` today correctly emits a `schema_invalid` error for a misfielded profile YAML (Pydantic's `extra inputs are not permitted`) via `pack_validator.py`'s generic per-file schema scan (`_scan_artifact_directory`, using the `AgentProfile` model directly). **That acute half of the issue's claim was already closed before the issue was filed and this spec does NOT re-specify it as broken.**
  The **actual residual gap**: `pack_validator.py`'s generic schema scan validates each profile YAML file *in isolation* against the bare `AgentProfile` schema. It does not run the load path `AgentProfileRepository` actually uses at runtime (`src/doctrine/agent_profiles/repository.py`), which additionally (a) field-merges an org/project profile onto a same-ID built-in profile and can fail post-merge in ways a single-file schema check cannot see, and (b) records every such failure via `_record_skip` (`:293-309`) into `skipped_profiles()` (`:311-320`) — a diagnostic that exists today but surfaces *only* through `spec-kitty doctor doctrine --json`, a command nothing in the authoring guide or the `pack validate` / `pack assemble` / `doctrine fetch` loop tells an author to run. An author who fixes every `pack validate` schema error can still ship a pack where a profile silently fails to merge and never learns it without a separate, undocumented `doctor doctrine --json` invocation. **Scope is corrected to this residual gap only** — FR-002 below wires the existing `AgentProfileRepository.skipped_profiles()` machinery into `pack validate`'s own output; it does not add a new validation engine.

- **Q3 (Defect #4 — the DRG carrier three-way mismatch, and whether the runtime carrier itself is in scope):** Should this mission fix `_drg_helpers.py` / `load_validated_graph` so the runtime reads `drg/` fragments as the guide documents?
  **A3 — Decision (resolved by the readiness probe, not escalated): the runtime-carrier fix is OUT OF SCOPE.** Sibling mission `org-pack-drg-root-graph-guard-01KZY0QT` (issue #3384) is in spec phase concurrently, on the identical `src/charter/_drg_helpers.py:87` `load_validated_graph` function. Its docstring (verified directly, `_drg_helpers.py:1-100`) confirms `_resolve_org_root()` is charter-layer-inert by architectural necessity — it always returns `None` because the `kernel <- doctrine <- charter <- specify_cli` layering forbids `charter` importing `specify_cli` (enforced by `tests/architectural/test_layer_rules.py`) — and that `load_validated_graph` reads `org_root` directly (the pack root), never `org_root/drg/`. **This mission scopes only an ADDITIVE `pack validate` advisory/error** for a pack whose DRG content lives exclusively under `drg/` with no root-level `*.graph.yaml`; today `pack_validator.py`'s `_validate_drg` check (`:480-609`) produces zero signal for this shape — it only inspects fragments *inside* `drg/` (`drg_dir.glob("*.graph.yaml")`, `:506`) and never looks at the pack root. This lives entirely in `pack_validator.py`, a different file from `_drg_helpers.py`, so it is independently fixable without colliding with #3384's file. **A design that changes `_drg_helpers.py` or `load_graph_or_dir` is a scope collision with in-flight work and is explicitly rejected here.**

---

## Problem

Several org-pack authoring mistakes today produce **no error anywhere** — the pack loads,
`pack validate` reports clean, and parts of the pack are silently inert at runtime. Silent
success is this repository's dominant tooling-defect class (see #3133, #3212, #3282, #3336
and the ledger note below) and this mission's literal subject. FR-002, FR-003 and FR-004 below
each state not just what the new check detects, but what it does when it detects nothing
wrong (passes silently, by design) and what it does when it detects the defect (a named,
per-file diagnostic — never a bare `0` count or a swallowed exception). FR-001 is the
exception: per the binding operator ruling (`reviews/spec.ruling.md`), it is
documentation-only and adds no check of its own, so it leaves a residual gap rather than
closing one — an author who follows the corrected guide still gets no runtime signal for a
mis-suffixed contract, because ADR `2026-08-13-1` retires that surface wholesale rather than
hardening it.

Four authoring-time gaps are in scope, each independently verified against this checkout
(see "Verified Code Surfaces"):

1. **Step contracts named per the guide never load, and `pack validate` has no opinion.**
   The guide documents `mission_step_contracts/*.contract.yaml`; the loader
   (`step_contracts.py`) and `pack_validator.py`'s own registry both already require
   `*.step-contract.yaml`. A `*.contract.yaml` file therefore matches **zero** files in
   either the loader's glob or the validator's glob — the loader silently loads nothing and
   `pack validate` silently reports nothing, because an empty glob match produces no error
   in either surface today. The author sees a clean `pack validate` and a doctrine snapshot
   that (per the corrected finding below) *does* count the file, and gets zero working
   contracts.
2. **Misfielded agent profiles field-merge-fail with no signal in the authoring loop.**
   Corrected scope per Clarification 2: the acute schema-rejection case is already fixed;
   the residual gap is that `AgentProfileRepository`'s post-merge skip diagnostics
   (`skipped_profiles()`) never reach `pack validate`.
3. **`pack validate` and the runtime disagree about directory recursion for assets.**
   `AssetRepository._project_scan` deliberately `rglob`s (its own docstring, `:18-22`,
   names the reason: an org-pack manifest at `assets/<pack>/x.asset.yaml` would never be
   found otherwise). `pack_validator.py`'s `_scan_files` (`:202-206`) recurses only when
   `directory.name == "styleguides"` — every other kind, `"assets"` included, gets a
   non-recursive `glob`. A nested asset sidecar loads at runtime and is invisible to
   validation.
4. **The DRG carrier the guide documents is not the one the runtime reads, and `pack
   validate` has no signal for the mismatch shape.** Scoped per Clarification 3 to an
   additive `pack validate` check only.

---

## Verified Code Surfaces

Every path below was read directly on this checkout (not trusted from the issue's line
numbers) before being cited in a requirement.

| Surface | File:line | What was verified |
|---|---|---|
| Step-contract loader glob | `src/doctrine/missions/step_contracts.py:174` | `GLOB = "*.step-contract.yaml"`, consumed by `MissionStepContractRepository` (built-in `rglob`, org/project `glob` via the shared `BaseDoctrineRepository`). |
| Step-contract validator glob | `src/specify_cli/doctrine/pack_validator.py:181` | `_artifact_schema_registry()` already maps `"mission_step_contracts": ("*.step-contract.yaml", MissionStepContract)` — the validator's glob is **already correct** and therefore silently matches nothing against a `*.contract.yaml` file, exactly like the loader. |
| Guide's documented suffix | `docs/guides/how-to/governance/create-an-org-doctrine-pack.md:65` and `:140` | Both instances document `*.contract.yaml` (layout tree + namespace table), unchanged from the issue's citation — no drift. |
| **Corrected: snapshot bucket-counting mechanism** | `src/specify_cli/doctrine/snapshot.py:53-65` vs `:195-212` | The issue cites `snapshot.py:53-65` with `endswith("contract.yaml")` semantics as the counter that "counts" a mis-suffixed contract. On this checkout, `_ARTIFACT_BUCKETS` (`:53-65`) is defined but **never referenced by any other code in the file or the repo** (`grep -rn "_ARTIFACT_BUCKETS" src/ tests/` returns only its own definition) — it is dead code. The function that actually populates `pack-manifest.yaml`'s `artifact_counts` is `_count_artifacts` (`:195-212`), which counts by **directory membership**, not filename suffix: for the `mission_step_contracts/` directory it runs `entry.rglob("*.yaml")` and counts *every* `.yaml` file inside, regardless of suffix. The net effect the issue describes (a mis-suffixed contract is counted by the snapshot but never loaded) **still holds**, but through `_count_artifacts`'s directory-glob, not the dead `_ARTIFACT_BUCKETS`/`endswith` path the issue names. Per the binding operator ruling narrowing FR-001 to a documentation-only guide correction (`reviews/spec.ruling.md`), this mission does **not** remove `_ARTIFACT_BUCKETS` — its removal is deferred to ADR `2026-08-13-1`'s retirement of the legacy step-contract surface, since it is domain-matched debt on the surface being deleted wholesale, not on this mission's org-pack-authoring-diagnostics domain. `_count_artifacts`'s directory-based counting behavior is unchanged by this mission (it is not suffix-discriminating by design and is not the defect FR-001 now addresses). |
| Asset repository recursion + rationale | `src/doctrine/assets/repository.py:18-22` (docstring), `:130-132` (`_project_scan`) | Docstring point 2 ("Recursive overlay discovery (A-3)") states the rationale verbatim: a non-recursive `glob` would never find `assets/<pack>/x.asset.yaml`. `_project_scan` overrides the base with `project_dir.rglob(self._glob)`. |
| Validator's non-recursive asset scan | `src/specify_cli/doctrine/pack_validator.py:202-206` | `_scan_files` recurses (`rglob`) only for `directory.name == "styleguides"`; all other kinds, `"assets"` included, get `directory.glob(glob)`. |
| Agent-profile skip machinery | `src/doctrine/agent_profiles/repository.py:293-309` (`_record_skip`), `:311-320` (`skipped_profiles`) | Both exist and are populated today at load time; nothing in `pack_validator.py` calls either. |
| Agent-profile closed schema | `src/doctrine/agent_profiles/profile.py:258` | `model_config = ConfigDict(extra="forbid", populate_by_name=True)`, added by `f732e10d6` (2026-07-27), an ancestor of the issue's cited verification commit `4a2367539`. |
| DRG fragment-only validator scope | `src/specify_cli/doctrine/pack_validator.py:480-609` (`_validate_drg`) | Only inspects `drg_dir.glob("*.graph.yaml")` (`:506`) — no pack-root scan exists anywhere in the function or the file. |
| Runtime DRG carrier | `src/charter/_drg_helpers.py:36-92` (`_resolve_org_root`, `load_validated_graph`) | `_resolve_org_root` always returns `None` (charter-layer-inert, by the `kernel <- doctrine <- charter <- specify_cli` layering); `load_validated_graph` calls `load_graph_or_dir(org_root)` — reads the pack root directly, never `org_root / "drg"`. |
| `pack validate` CLI entry point | `src/specify_cli/cli/commands/doctrine.py:348-372` (`pack_validate`) | Thin wrapper: calls `validate_pack(pack_path)` then `render_validation_result(result, json_output=...)`; exit code `0`/`1` on `result.ok`. FR-002's, FR-003's, and FR-004's new diagnostics flow through this same `ValidationResult`/`ValidationIssue` surface — no new CLI command or flag is introduced. FR-001 is documentation-only per the binding operator ruling (`reviews/spec.ruling.md`) and adds no diagnostic to this surface. |
| **Reflexivity: `validate_pack`'s other callers** | `src/specify_cli/doctrine/pack_assembler.py:335` (`assemble_pack`'s internal `validate_pack(output_dir)` call, rollback on `!ok`), `:475-539` (`_copy_drg_fragments`, writes DRG content only to `output_dir/drg/*.graph.yaml`, never a pack-root graph); `src/specify_cli/cli/commands/doctrine.py:966` (`org_validate`'s `validate_pack(pack_path)` call, reached via the CLI's `doctrine org init` → `doctrine org validate` onboarding flow) and `:899-940` (`org_init`'s scaffold: `org-charter.yaml` + `drg/fragment.yaml` + `README.md` — no pack-root graph) | `validate_pack` is called not only by the author-facing `pack validate` CLI above but also internally by the assembler as a round-trip check on its own freshly-built output, and by the narrower `doctrine org validate` command against a pack scaffolded by `doctrine org init`. These two callers are reasoned about **separately, not as one shared architectural guarantee** — see FR-004's "Reflexivity fix." `pack_assembler.py`'s carve-out is structural: `_copy_drg_fragments` never writes a pack-root graph, so an assembled pack carrying DRG fragments is, by construction, always exactly the shape this check targets; that carve-out stays unconditional. `org_init`'s scaffold writes `drg/fragment.yaml` — a filename that never matches the check's `*.graph.yaml` glob — so the check never fired for the scaffold's own output *with or without* a carve-out; `org_validate`'s carve-out was never load-bearing for the shape its own justification cited, so it is dropped, and the call site passes `check_drg_root=True` explicitly instead. `tests/specify_cli/doctrine/test_pack_assembler.py:169` `test_force_dedup_prunes_duplicate_edges_via_canonical_serializer` (the only currently-passing test that actually reaches `validate_pack` on this shape — `:151`'s `test_drg_conflict` returns via an earlier conflict-detection guard and never reaches `validate_pack` at all, so it is not cited as reflexivity evidence) and `tests/cli/test_doctrine_org_commands.py:108` `test_doctrine_org_validate_accepts_valid_pack` both continue to pass — the assembler's because of its carve-out, `org_validate`'s because its scaffold never trips the check in the first place. |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Author reads the corrected guide and never hits the suffix trap (Priority: P1)

An org-pack author opens the published guide
(`docs/guides/how-to/governance/create-an-org-doctrine-pack.md`) before authoring a step
contract, reads the layout tree (`:65`) and the namespace table (`:140`), and names their
file per the guide's documented suffix.

**Why this priority**: per the binding operator ruling narrowing FR-001 to a
documentation-only requirement (`reviews/spec.ruling.md`), the guide text itself was the
trap — every pack author following the *previously published* guide named their file
`*.contract.yaml`, a suffix neither the loader nor the validator has ever matched, and got
silence. Correcting the guide is the highest-leverage, lowest-risk fix available given that
the surface the guide describes is itself slated for retirement under ADR `2026-08-13-1`
(Accepted) — this mission does not invest further implementation effort in a surface an
Accepted ADR retires wholesale.

**Independent Test**: read
`docs/guides/how-to/governance/create-an-org-doctrine-pack.md` at `:65` and `:140`; assert
both cite `*.step-contract.yaml`, not `*.contract.yaml`; assert the same guide section
cites ADR `2026-08-13-1` and states the surface's retirement trajectory.

**Acceptance Scenarios**:

1. **Given** the corrected guide, **When** an author reads the layout tree at `:65` and the
   namespace table at `:140`, **Then** both instruct `*.step-contract.yaml` — the suffix
   the loader (`step_contracts.py`) and `pack_validator.py`'s own registry already require
   — not the guide's previous, incorrect `*.contract.yaml`.
2. **Given** the corrected guide, **When** an author reads the same section, **Then** it
   names ADR `2026-08-13-1` and states that this step-contract surface is slated for
   retirement in its entirety, so the author does not treat the corrected suffix as a
   durable authoring target.

---

### User Story 2 - Author learns a profile silently failed to merge, without a second command (Priority: P1)

An org-pack author authors an `agent_profiles/acme-implementer.agent.yaml` that passes
schema validation as an individual file, but fails to field-merge onto a same-ID built-in
profile at `AgentProfileRepository` load time (the residual gap in Clarification 2). They
run `pack validate` and expect to learn about it there, not by separately knowing to run
`spec-kitty doctor doctrine --json`.

**Why this priority**: the corrected residual gap — the acute schema case is already
closed, but this merge-time class is not, and nothing in the authoring guide mentions
`doctor doctrine --json`.

**Independent Test**: construct a synthetic pack + built-in-profile fixture that reproduces
a load-time skip not otherwise caught by the generic per-file schema scan (e.g. a
post-merge validation failure); run `pack validate --json`; assert the skip is present in
the output keyed by file and reason, without a separate `doctor doctrine` invocation.

**Acceptance Scenarios**:

1. **Given** a profile file that individually passes `AgentProfile.model_validate` but is
   recorded by `AgentProfileRepository._record_skip` during merge, **When** `pack validate
   --json` runs against the pack, **Then** the JSON payload's existing `errors` or
   `advisories` array (per its severity) includes a `ValidationIssue` with `category:
   profile_skipped` naming the file, the profile id (when known), and the recorded
   `error_summary` in its `message` — sourced from the same
   `AgentProfileRepository.skipped_profiles()` call `doctor doctrine --json` already uses,
   not a re-implementation. This is a new category value inside the existing
   `{ok, errors, advisories}` shape (`ValidationResult.to_dict()`); it is **not** a new
   top-level JSON key such as a standalone `skipped_profiles` array.
2. **Given** a profile file with an undeclared key (the already-fixed acute case), **When**
   `pack validate` runs, **Then** it still reports exactly one diagnostic for that file (the
   existing `schema_invalid` error) — the new skip-surfacing does not double-report the same
   root cause as two unrelated-looking issues for one file.
3. **Given** a pack with no profile problems, **When** `pack validate` runs, **Then** no
   `profile_skipped` issue appears in `errors` or `advisories` and `ok` is unaffected — no
   false positive.

---

### User Story 3 - A nested asset sidecar is caught by validation, matching what the runtime loads (Priority: P2)

An org-pack author places `assets/acme-pack/logo.asset.yaml` (nested one directory deep,
the ADR-mandated org-pack manifest layout) and runs `pack validate`.

**Why this priority**: lower blast radius than P1s (assets are typically supplementary
content, not governance-critical), but still a validate/runtime disagreement that lets
unreviewed content ship silently.

**Independent Test**: author a pack with an asset manifest one directory below
`assets/`; run `pack validate --json`; assert the manifest is scanned and any schema
violation is reported, matching what `AssetRepository` would load at runtime.

**Acceptance Scenarios**:

1. **Given** `assets/acme-pack/logo.asset.yaml` with a schema violation (e.g. an invalid
   `mime` value), **When** `pack validate` runs, **Then** it reports the violation against
   that nested file — today it is invisible to validation and only surfaces (or silently
   loads) at runtime.
2. **Given** the same nested file with no violation, **When** `pack validate` runs,
   **Then** it passes with no false positive, and the asset participates in the existing
   `_validate_asset_manifests` containment/mime checks exactly as a top-level asset would.

---

### User Story 4 - Author is warned when DRG content lives only under `drg/` with no pack-root graph (Priority: P2)

An org-pack author follows the guide's `drg/010-security.graph.yaml` layout exclusively
(no pack-root `*.graph.yaml`) and runs `pack validate`.

**Why this priority**: per sibling mission #3384, adopting such a pack *zeroes the action
grain* at runtime — a destructive silent failure — but the runtime-carrier fix is out of
scope here (Clarification 3); this mission's job is only to make `pack validate` say
something instead of nothing.

**Independent Test**: author a pack with `drg/010-security.graph.yaml` present and no
`*.graph.yaml` at the pack root; run `pack validate --json`; assert a diagnostic names the
mismatch and points at the pack-root carrier the runtime actually reads.

**Acceptance Scenarios**:

1. **Given** a pack with one or more fragments under `drg/*.graph.yaml` and no
   `*.graph.yaml` at the pack root, **When** `pack validate` runs, **Then** it reports a
   diagnostic (category name TBD at plan time, e.g. `drg_root_graph_missing`) stating that
   the action-grain runtime reads a pack-root `*.graph.yaml`, not `drg/` fragments, and that
   this pack's DRG content will not be read by that runtime path as authored today.
2. **Given** a pack with a pack-root `*.graph.yaml` (with or without additional `drg/`
   fragments), **When** `pack validate` runs, **Then** no such diagnostic is reported.
3. **Given** a pack with neither a pack-root graph nor a `drg/` directory, **When** `pack
   validate` runs, **Then** no such diagnostic is reported (nothing to warn about — a pack
   with no DRG content is not this check's concern).

### Edge Cases

- An org-pack whose `agent_profiles/` directory is entirely absent: FR-002's new check must
  not attempt to instantiate `AgentProfileRepository` in a way that raises for a missing
  directory — absent directory means zero skips, not an error.
- A pack whose `assets/` directory does not exist at all: FR-003 must not change behavior —
  today's `if not type_dir.is_dir(): continue` guard already skips absent directories; the
  fix only changes the glob used *when* the directory is present.
- A pack with a pack-root file named e.g. `notes.graph.yaml.bak` or similar near-miss: must
  not be mistaken for a satisfying pack-root `*.graph.yaml` — FR-004 uses the same exact
  glob (`*.graph.yaml`) the runtime and the existing `_validate_drg` fragment scan already
  use, so this is consistent by construction rather than a new pattern to get subtly wrong.

---

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Guide correction for the step-contract suffix (documentation-only) | User Story 1 | High | Open |
| FR-002 | `pack validate` surfaces `skipped_profiles` inline (residual gap only) | User Story 2 | High | Open |
| FR-003 | `pack validate` recurses into `assets/` matching `AssetRepository` | User Story 3 | Medium | Open |
| FR-004 | `pack validate` advisory/error for DRG-only-under-`drg/` with no pack-root graph | User Story 4 | Medium | Open |

#### FR-001 — Guide correction for the step-contract suffix (documentation-only)

**Requirement**: Documentation-only, per the binding operator ruling
(`reviews/spec.ruling.md`) that replaces the acceptance bar for FR-001 and C-001. Correct
`docs/guides/how-to/governance/create-an-org-doctrine-pack.md` at `:65` (the layout tree)
and `:140` (the namespace table) from `*.contract.yaml` to `*.step-contract.yaml`, so the
guide stops instructing authors to create files the loader can never read. In the same
guide, point authors at ADR `2026-08-13-1`
(`docs/adr/3.x/2026-08-13-1-built-in-mission-subtree-stays-nested-retire-legacy-step-contracts.md`,
status `Accepted`) so a reader learns that this entire step-contract surface —
`step_contracts.py`, the `MissionStepContract` model, and this suffix — is slated for
retirement in its entirety, and does not treat the corrected suffix as a durable authoring
target. FR-001 changes **no code**: it does not introduce a shared suffix constant, does
not add a `pack_validator.py` near-miss mismatch diagnostic for `*.contract.yaml` files,
and does not remove `snapshot.py`'s `_ARTIFACT_BUCKETS` table — all three were dropped from
this mission's scope by the ruling, which found each to be work that would land on a
surface an Accepted ADR retires wholesale (see C-001).

**Fails how**: before this fix, the guide instructs authors to name step-contract files
`*.contract.yaml`, a suffix neither the loader (`step_contracts.py`) nor
`pack_validator.py`'s own registry has ever matched — every author following the
currently published guide produces files that silently never load, and `pack validate`
silently reports nothing. After this fix, the guide documents the suffix the loader and
validator actually use, and directs the author to ADR `2026-08-13-1` for the surface's
retirement trajectory. This requirement corrects the guide's instruction only; it does not
add any new runtime or validator behavior. A pack authored with the stale
`*.contract.yaml` suffix still passes `pack validate` silently after this mission — that
residual gap is an accepted consequence of deferring the whole surface to ADR
`2026-08-13-1`'s retirement, not a defect this mission closes.

**Acceptance Criteria**:
- AC-1: `docs/guides/how-to/governance/create-an-org-doctrine-pack.md` documents
  `*.step-contract.yaml` at both `:65` (layout tree) and `:140` (namespace table); no
  remaining reference to `*.contract.yaml` as the mission-step-contract suffix exists in
  that guide.
- AC-2: The same guide section cites ADR `2026-08-13-1` and states that the step-contract
  surface it documents is slated for retirement in its entirety, so a reader does not treat
  the corrected suffix as a durable authoring target.
- **Targeted test surface**: None. This FR is documentation-only per the binding operator
  ruling (`reviews/spec.ruling.md`); it touches no code, adds no validator diagnostic, and
  contributes no entry to C-004's targeted test list.

#### FR-002 — `pack validate` surfaces `skipped_profiles` inline (residual gap only)

**Requirement**: `pack validate` additionally runs the same load path
`AgentProfileRepository` uses against the pack's `agent_profiles/` directory (org-layer
construction, i.e. treating the pack under validation as the sole org source) and includes
any `skipped_profiles()` entries in its `ValidationResult` — as `ValidationIssue`s with a
distinct category, `profile_skipped` — deduplicated against files that already
produced a `schema_invalid` error from the existing generic per-file scan so one root cause
is not reported twice under two unrelated-looking categories. **JSON shape (resolved):** each
skip becomes one `ValidationIssue` (`category: profile_skipped`, `file`, `artifact_id` set to
the profile id when resolvable, `message` carrying the recorded `error_summary`) placed in
the existing `errors` or `advisories` array per its severity — the shared `ValidationIssue`
model already used by every other check in this file. `ValidationResult.to_dict()`
(`src/specify_cli/doctrine/pack_validator.py:144-149`) keeps its current top-level shape,
exactly `{ok, errors, advisories}` — **no new top-level JSON key** (e.g. no standalone
`skipped_profiles` array) is introduced. This is additive wiring, not
a new validation engine: `AgentProfileRepository.skipped_profiles()`
(`src/doctrine/agent_profiles/repository.py:311-320`) already exists and is already
populated at load time by `_record_skip` (`:293-309`); `pack_validator.py` already loads
built-in IDs per kind via `_load_built_in_ids_per_kind()` for the existing collision checks,
so the seam for resolving a comparable built-in profile set already exists in this file.

**Fails how**: before this fix, a profile that individually passes schema validation but
fails to field-merge (or otherwise fails post-schema load-time checks) produces **no**
diagnostic anywhere `pack validate`, `pack assemble`, or `doctrine fetch` touch — the only
surface is `spec-kitty doctor doctrine --json`'s `skipped_profiles` key, which nothing in
the authoring guide tells an author to run. After this fix, the same information appears
directly in `pack validate`'s own output (human and `--json`), in the authoring loop the
guide actually documents.

**Acceptance Criteria**:
- AC-1: A synthetic fixture where a profile passes `AgentProfile.model_validate` in
  isolation but is recorded via `_record_skip` during `AgentProfileRepository` load (e.g. a
  post-merge failure mode) causes `pack validate --json` to include, within the existing
  `errors`/`advisories` array (per severity), a `ValidationIssue` with `category:
  profile_skipped` naming the file, the profile id (when resolvable), and the error summary —
  not a new top-level JSON key.
- AC-2: A profile file with an undeclared key (the already-fixed acute case) still produces
  exactly one diagnostic for that file from `pack validate`, not two.
- AC-3: A pack with no profile issues produces no `profile_skipped` issue in `errors` or
  `advisories` and an unaffected `ok` result — no false positive, no regression to today's
  passing packs.
- AC-4: The new check reuses `AgentProfileRepository`/`skipped_profiles()` directly (verified
  by test asserting the same function is called or the same dataclass shape is surfaced) —
  it does not hand-roll a second skip-detection heuristic that could drift from the
  authoritative one `doctor doctrine --json` already uses.
- AC-5: A pack whose `agent_profiles/` directory is entirely absent: `pack validate` does not
  raise (the new check must not attempt to instantiate `AgentProfileRepository` in a way that
  requires the directory to exist), `profile_skipped` issues are absent, and a regression
  test asserts the check path actually executed against the absent-directory case (not
  merely that nothing crashed) — proving "directory missing" produces zero skips rather than
  an unraised exception silently swallowing the check (Edge Cases bullet 2).
- **Targeted test surface**: `tests/specify_cli/doctrine/test_pack_validator.py`,
  `tests/doctrine/test_agent_profile_model_field.py` (model-layer fixtures only, no new
  runtime code there).

#### FR-003 — `pack validate` recurses into `assets/` matching `AssetRepository`

**Requirement**: `pack_validator.py`'s `_scan_files` (`:202-206`) recurses (`rglob`) for
`"assets"` in addition to `"styleguides"`, matching `AssetRepository._project_scan`'s
existing `rglob(self._glob)` behavior (`src/doctrine/assets/repository.py:130-132`,
rationale documented in the class's own docstring at `:18-22`). This is a pure widening of
the validator's scan, not a runtime change — `AssetRepository` itself is untouched.

**Fails how**: before this fix, an asset manifest nested under `assets/<pack>/x.asset.yaml`
(the ADR-mandated org-pack manifest layout, per the docstring) is invisible to `pack
validate` — it is never scanned, never schema-checked, never subjected to the existing
`asset_path_escape` / `asset_mime_invalid` checks — while `AssetRepository` loads and uses
it at runtime. Validation reports clean for content it never examined. After this fix, the
nested manifest is scanned identically to a top-level one.

**Acceptance Criteria**:
- AC-1: A pack with `assets/acme-pack/logo.asset.yaml` containing a schema violation (e.g.
  malformed `mime`) is caught by `pack validate` with the existing `asset_mime_invalid` /
  `schema_invalid` categories — today it produces zero diagnostics.
  - **Given/When/Then**: Given a pack with a nested, schema-violating asset manifest, When
    `pack validate` runs, Then the violation is reported against the nested file path.
- AC-2: A pack with a valid nested asset manifest passes `pack validate` with no false
  positive, and the manifest participates in the existing containment/mime checks.
- AC-3: Existing top-level `assets/*.asset.yaml` behavior is unchanged (regression-free) —
  a top-level asset test already in `tests/specify_cli/doctrine/test_pack_validator.py`
  (e.g. `test_multiple_assets_independent`, `:715`) continues to pass unmodified.
- AC-4: A pack whose `assets/` directory does not exist at all produces no error and no
  behavior change — the existing `if not type_dir.is_dir(): continue` guard is exercised
  (present before this fix and left alone), and a regression test proves this path actually
  runs for an absent `assets/` directory, not merely that nothing crashes (Edge Cases
  bullet 3).
- **Targeted test surface**: `tests/specify_cli/doctrine/test_pack_validator.py`.

#### FR-004 — `pack validate` advisory/error for DRG-only-under-`drg/` with no pack-root graph

**Requirement**: `pack_validator.py` gains an additive check, independent of and alongside
the existing `_validate_drg` fragment-content checks (`:480-609`): when a pack's `drg/`
directory contains one or more `*.graph.yaml` fragments and the **pack root** contains no
top-level `*.graph.yaml` file, emit a diagnostic stating that the action-grain runtime
(`src/charter/_drg_helpers.py:load_validated_graph`) reads a pack-root `*.graph.yaml`, not
`drg/` fragments, so this pack's DRG content is not consumed by that runtime path as
authored. **Explicitly out of scope**: any change to `_drg_helpers.py`, `load_graph_or_dir`,
or any other runtime DRG-carrier code — this check only makes `pack validate` say something
where it currently says nothing about this specific mismatch shape (see Clarification 3).

**Reflexivity fix — two other callers, reasoned about separately (Reflexivity finding;
per binding operator ruling #2, `reviews/plan.ruling.md`):**
`validate_pack()` is not only the author-facing entry point behind the CLI's
`pack_validate` command (`src/specify_cli/cli/commands/doctrine.py:348-372`) — it has (at
least) two other callers. **The two are not one shared architectural guarantee; each is
carved out, or not, for its own reason:**

1. `pack_assembler.py:assemble_pack()` calls it *internally* at its own
   `validate_pack(output_dir, check_drg_root=False)` call (`pack_assembler.py:335`) as a
   round-trip check on output the assembler just produced, rolling the assembly back on
   failure. `_copy_drg_fragments` (`pack_assembler.py:475-539`) writes DRG content **only**
   to `output_dir/drg/*.graph.yaml`; the assembler has no code path that ever writes a
   pack-root `*.graph.yaml`. This is a structural guarantee about the assembler's own write
   paths, not an assumption about any caller or about `org_init`'s output shape. **This
   carve-out stands, unconditional, unchanged.**
2. `doctrine.py:org_validate` (`:966`) calls `validate_pack(pack_path)` against an arbitrary
   `pack_path: Path` — a general-purpose CLI command, not scoped to freshly-`org_init`'d
   directories. Nothing stops an author from running `org init`, then adding real
   `agent_profiles/`, `directives/`, and a `drg/010-security.graph.yaml` fragment with no
   pack-root graph, then running `org validate` on the now-substantial pack — precisely the
   destructive shape this FR exists to catch. The check itself is already content-conditional
   (it fires only when `drg/*.graph.yaml` fragments exist and the pack root has none), and
   `org_init` (`:899-940`) scaffolds `drg/fragment.yaml` — a filename that never matches
   `*.graph.yaml` — so the carve-out has never protected anything for the shape its own
   justification cited (the three-file onboarding stub). **`org_validate`'s carve-out is
   therefore dropped.** The call site passes `check_drg_root=True` **explicitly** rather than
   relying on `validate_pack`'s own default, with a short inline comment recording why: if a
   future refactor changes that default, an implicit reliance on it would silently change
   `org_validate`'s behaviour and nothing would fail to flag it. Writing it explicitly makes
   the dependency visible and lets AC-7 assert it directly.

**Corrected: what a uniformly-applied default-error severity would actually do.** A
default-error severity applied uniformly would fail `assemble_pack()`'s internal
`validate_pack` call on every DRG-carrying assembly, including the currently-passing
`test_force_dedup_prunes_duplicate_edges_via_canonical_serializer`
(`tests/specify_cli/doctrine/test_pack_assembler.py:169`), which asserts `result.ok is True`
against exactly this drg/-fragments-only, no-pack-root-graph shape — this is why the
assembler's carve-out is needed and kept. It would **not** fail `org_validate`'s call on a
freshly-scaffolded org pack: `org_init`'s scaffold writes `drg/fragment.yaml`, a filename
that never matches the check's `*.graph.yaml` glob, so `test_doctrine_org_validate_accepts_valid_pack`
(`tests/cli/test_doctrine_org_commands.py:108-119`) would keep passing with or without a
carve-out. (This passage previously asserted the default would fail "both call sites on
every invocation... including... `test_doctrine_org_validate_accepts_valid_pack`" — checked
directly against this checkout and found factually false; corrected here, not merely
reworded, per operator ruling #2.)

Accordingly: `validate_pack()` gains a keyword-only parameter, `check_drg_root: bool = True`.
The CLI's `pack_validate` command (and any other full-pack-authoring caller) uses the
default `True`. `pack_assembler.py`'s internal `validate_pack(output_dir,
check_drg_root=False)` call at `:335` keeps its unconditional carve-out, for the structural
reason in point 1 above. `doctrine.py`'s `org_validate` call at `:966` passes
`check_drg_root=True` explicitly (see point 2 above) — it carries no carve-out.

For the assembler: extending the assembler to also emit a pack-root graph, or defaulting the
whole check to advisory, were both considered and rejected: the former is an unrelated, larger
change to the assembler's architecture that this mission does not otherwise need, and the
latter would blunt the diagnostic for the author-facing case that is this mission's actual
target, given the destructive "zeroes the action grain" consequence documented by sibling
mission #3384.

**Fails how**: before this fix, a pack authored exactly per the guide's `drg/` section
passes `pack validate` cleanly and, per sibling mission #3384's finding, **zeroes the action
grain** on adoption — a destructive silent failure with no validation-time signal at all.
After this fix, `pack validate` names the mismatch at authoring time, before the pack is
ever published or fetched by a consumer. `assemble_pack()`'s internal round-trip check
continues to pass for its own known drg/-fragments-only output — because of its unconditional
carve-out, unaffected by this new author-facing diagnostic. `org_validate`'s
onboarding-scaffold check continues to pass too, but for a different reason: not because it
is carved out, but because `org_init`'s scaffold never produces the shape the diagnostic
fires on. Should a pack that started as an `org_init` stub later accumulate real
`drg/*.graph.yaml` content with no pack-root graph, `doctrine org validate` now correctly
fires the diagnostic — this is the positive-fire case AC-7 tests.

**Acceptance Criteria**:
- AC-1: A pack with `drg/010-security.graph.yaml` and no pack-root `*.graph.yaml` produces
  the new diagnostic from `pack validate` (default `check_drg_root=True`), naming the runtime
  carrier it reads instead.
- AC-2: A pack with a pack-root `*.graph.yaml` (with or without `drg/` fragments) produces
  no such diagnostic.
- AC-3: A pack with neither a pack-root graph nor a `drg/` directory produces no such
  diagnostic (this check is about a *mismatch*, not about requiring DRG content to exist).
- AC-4: The diagnostic's severity for the author-facing (`check_drg_root=True`) case is
  **error** (fails `pack validate`'s exit code), not advisory-only — given the destructive
  consequence documented in #3384 and this mission's "silent success is the dominant defect
  class" mandate. This is falsifiable in a test asserting `ok is False` and exit code `1` for
  AC-1's fixture.
- AC-5: A pack with a pack-root file named e.g. `notes.graph.yaml.bak` or another near-miss
  that does not match `*.graph.yaml`, with `drg/` fragments present, still produces the AC-1
  diagnostic — the near-miss file is not mistaken for a satisfying pack-root `*.graph.yaml`
  (Edge Cases bullet 4); the check uses the same exact `*.graph.yaml` glob the runtime and
  the existing `_validate_drg` fragment scan already use.
- AC-6: `assemble_pack()` assembling input packs whose only DRG content is `drg/` fragments
  (the shape `test_force_dedup_prunes_duplicate_edges_via_canonical_serializer` already
  exercises — `test_drg_conflict` is not cited here: it returns via an earlier
  conflict-detection guard and never reaches `validate_pack` at all, so it is not evidence
  either way for this AC) continues to succeed unmodified — its internal
  `validate_pack(output_dir, check_drg_root=False)` call does not newly fail on its own
  drg/-fragments-only, no-pack-root-graph output. The cited existing test in
  `tests/specify_cli/doctrine/test_pack_assembler.py` passes unchanged, and a new test asserts
  `check_drg_root=False` is actually the parameter value used by that internal call (not
  merely that the test happens to still pass).
- AC-7: `doctrine org validate`'s internal `validate_pack(pack_path, check_drg_root=True)`
  call carries **no carve-out** — this inverts the previous version of this AC. Two cases:
  - *(a) Negative, unmodified scaffold*: an org pack scaffolded via `doctrine org init`
    (`org-charter.yaml` + `drg/fragment.yaml` + `README.md`, no pack-root graph) still
    passes — `tests/cli/test_doctrine_org_commands.py::test_doctrine_org_validate_accepts_valid_pack`
    continues to exit `0` unmodified, because `drg/fragment.yaml` never matches the
    `*.graph.yaml` glob this check keys off, not because of any carve-out. A new/updated
    test in that file asserts `check_drg_root=True` is actually the parameter value used at
    `org_validate`'s call site, written explicitly rather than left to `validate_pack`'s own
    default — mirroring AC-6's parameter-value assertion for the assembler's call, but
    asserting the opposite value.
  - *(b) Positive-fire, no fixture exists today*: a new test fixture — a pack scaffolded via
    `doctrine org init`, then given a real `drg/*.graph.yaml` fragment (in addition to or
    replacing the scaffolded `drg/fragment.yaml`) with still no pack-root graph — asserts
    `doctrine org validate` now produces the `drg_root_graph_missing` diagnostic and exits
    non-zero. No such fixture exists in `tests/cli/test_doctrine_org_commands.py` today; this
    is the exact shape the dropped carve-out was suppressing, and proving it fires is the
    whole point of dropping the carve-out.
- **Targeted test surface**: `tests/specify_cli/doctrine/test_pack_validator.py`,
  `tests/specify_cli/doctrine/test_pack_assembler.py`, `tests/cli/test_doctrine_org_commands.py`.

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Documentation-only; no code touched | Per the binding operator ruling (`reviews/spec.ruling.md`), FR-001 changes **no code at all**: it corrects `docs/guides/how-to/governance/create-an-org-doctrine-pack.md`'s documented step-contract suffix and points authors at ADR `2026-08-13-1`. It must not touch, extend, or de-duplicate `step_contracts.py`, `pack_validator.py`'s `_artifact_schema_registry()`, `snapshot.py`'s `_ARTIFACT_BUCKETS`, or any other code on the legacy `MissionStepContract` surface — ADR `2026-08-13-1` is `Accepted` and retires that entire legacy step-contract surface (PR #3378 unmerged, docs-only) in favor of the unified `MissionStep` model; investing implementation effort in a surface an Accepted ADR retires wholesale is work that lands and is then deleted. | Technical | High | Open |
| C-002 | No runtime DRG-carrier change | FR-004 must not modify `src/charter/_drg_helpers.py`, `load_graph_or_dir`, or `load_validated_graph` — that surface belongs to sibling mission #3384 (`org-pack-drg-root-graph-guard-01KZY0QT`), in spec phase concurrently. | Technical | High | Open |
| C-003 | No fifth surface | This mission's scope is bounded to exactly the four FRs above. No additional pack-authoring defect surfaced during implementation should be folded in without a scope amendment. | Process | Medium | Open |
| C-004 | Targeted test packages, not full suite | Per the charter's binding Testing Requirements section, validation runs only the test packages named per FR (`tests/specify_cli/doctrine/test_pack_validator.py`, `tests/doctrine/test_agent_profile_model_field.py`, `tests/specify_cli/doctrine/test_pack_assembler.py`, `tests/cli/test_doctrine_org_commands.py`), not a full `pytest tests/` gate. FR-001 is documentation-only per the binding operator ruling (`reviews/spec.ruling.md`) and contributes no test surface of its own. | Process | High | Open |

---

## Reflexivity: what happens to missions and packs mid-flight

This change alters `pack validate`, a surface other running missions and CI jobs invoke.
Per the charter's reflexivity expectation, the following consequences are explicit and
intended:

- **A pack that validated clean yesterday can start failing today for FR-002/003/004's
  shapes.** Three of the four FRs — FR-002, FR-003, and FR-004 — are new *diagnostics for
  pre-existing defects*, not new restrictions on previously-correct content. A profile with
  a merge-time skip, a nested asset manifest, or `drg/`-only content was **already broken at
  runtime** before this mission — `pack validate`'s silence was itself the defect. This
  mission does not regress any pack that was genuinely working; it removes false-positive
  "healthy" reports from packs that were already delivering nothing for the affected
  artifact. **FR-001 is the exception**: per the binding operator ruling narrowing it to a
  documentation-only guide correction (`reviews/spec.ruling.md`), it adds no new `pack
  validate` diagnostic — a pack with a stray `*.contract.yaml` file continues to pass `pack
  validate` silently after this mission, exactly as before. That residual gap is accepted
  as a consequence of deferring the whole surface to ADR `2026-08-13-1`'s retirement, not
  closed by this mission.
- **CI jobs that gate on `pack validate`'s exit code** (e.g. an org's own pack-repo CI
  calling `spec-kitty doctrine pack validate --json` per the guide's Step 5) will newly fail
  for packs exhibiting FR-002/003/004's three shapes (a profile merge-time skip, a nested
  asset manifest, or `drg/`-only content). This is the intended effect — it is the entire
  point of the mission for those three FRs — but it is a real, visible behavior change for
  any pack in the wild today and should be called out in the mission's changelog entry /
  release note at merge time, not just in this spec. FR-001's shape (a stray
  `*.contract.yaml` step-contract file) is unaffected: no new diagnostic is added for it, so
  `pack validate`'s exit code does not change for that shape — only the guide's documented
  suffix changes.
- **`spec-kitty doctor doctrine --json`'s existing `skipped_profiles` reporting is
  unaffected** — FR-002 adds a second surface for the same underlying data; it does not
  remove or change the `doctor doctrine` command.
- **No mid-flight mission in this workspace currently depends on any of the four exact
  broken shapes** (verified: no in-progress mission here authors an org pack under
  `kitty-specs/*/`), so there is no known active consumer this change breaks out from under
  mid-mission. This claim is scoped to *this* workspace, not every consumer of the public
  `spec-kitty` package.

---

## Campsite / Standing-Order Notes (for the plan phase, not actioned here)

Per Charter Standing Order #2 (campsite cleaning) and #3 (mission tracer files):

- The three touched files (`pack_validator.py`, `pack_assembler.py`, `doctrine.py`) carry
  pre-existing Sonar/complexity debt worth a look before or alongside the functional change
  — in particular `pack_validator.py`'s `validate_pack()` is already a long orchestration
  function and `_scan_artifact_directory`'s docstring already notes it was extracted to stay
  under ruff's C901 limit; adding FR-002/004's new checks should follow the same
  extract-a-helper discipline rather than growing `validate_pack()` in place.
  `pack_assembler.py` and `doctrine.py` are touched only for FR-004's Reflexivity fix — the
  unconditional `check_drg_root=False` carve-out at `assemble_pack()`'s call site, and the
  explicit `check_drg_root=True` (no carve-out) written out at `org_validate`'s call site —
  a narrow, single-call-site edit each, not a rewrite. Per the binding
  operator ruling narrowing FR-001 to a documentation-only guide correction
  (`reviews/spec.ruling.md`), `snapshot.py` and `step_contracts.py` are **not** touched by
  this mission's code — the guide fix only. This is a planning-phase call, not specified
  further here — campsite-cleaning is scoped to domain-matched debt in files this mission
  touches, not a grab-bag.
- Mission tracer files (tooling-friction, approach, design-decisions) are seeded at planning
  and are not created by this spec.
- This spec itself found and corrected one citation drift in the issue (the `snapshot.py`
  `_ARTIFACT_BUCKETS`/`endswith` vs. `_count_artifacts` distinction) — worth naming in the
  approach tracer as an example of "verify, don't trust, the reported line numbers."

---

## Ledger Note

The readiness probe found zero existing `SPEC-KITTY-LEDGER.md` entries for `org.pack` /
`org-doctrine-pack` / `step.contract` / `pack validate` / `snapshot.py` / `AssetRepository`.
This mission's corrected finding (Clarification 2's correction — the issue's "`pack
validate` passes" claim for misfielded profiles is false; the real residual gap is narrower)
is new ledger material. A ledger entry is **not** written by this spec — per the ledger's
own instructions, entries are added during the reviewing/implementing phase's retrospective
— but the retrospective owes one, and this note flags that obligation now so it is not lost
by the time the mission closes.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `docs/guides/how-to/governance/create-an-org-doctrine-pack.md` documents
  `*.step-contract.yaml` (not `*.contract.yaml`) at both `:65` and `:140`, and cites ADR
  `2026-08-13-1` so an author learns the surface is slated for retirement. Per the binding
  operator ruling (`reviews/spec.ruling.md`), FR-001 is documentation-only: it does not add
  a `pack validate` diagnostic, so a pack authored with the stale `*.contract.yaml` suffix
  still passes `pack validate` silently — that residual gap is accepted as a consequence of
  deferring the whole surface to ADR `2026-08-13-1`'s retirement, not left for this mission
  to close.
- **SC-002**: A profile that individually passes schema validation but is recorded as
  skipped by `AgentProfileRepository` at load time appears in `pack validate --json`'s
  output without any separate `doctor doctrine --json` invocation.
- **SC-003**: A nested `assets/<pack>/x.asset.yaml` manifest is scanned and validated by
  `pack validate`, matching what `AssetRepository` loads at runtime.
- **SC-004**: A pack with DRG content only under `drg/` and no pack-root `*.graph.yaml`
  produces a `pack validate` diagnostic naming the actual runtime carrier — zero such
  diagnostic exists today for this exact shape.
- **SC-005**: All four targeted test surfaces
  (`tests/specify_cli/doctrine/test_pack_validator.py`,
  `tests/doctrine/test_agent_profile_model_field.py`,
  `tests/specify_cli/doctrine/test_pack_assembler.py`,
  `tests/cli/test_doctrine_org_commands.py`) pass for the new/changed tests
  specifically — this criterion does not assume or require a green full-suite baseline
  (`main` carries ~23 known-red tests and 2 errors per issue #3284). FR-001 is
  documentation-only per the binding operator ruling (`reviews/spec.ruling.md`) and
  contributes no test surface here.
