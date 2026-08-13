# Mission Specification: Org-Pack Authoring Diagnostics

**Mission Branch**: `feat/org-pack-authoring-diagnostics-3387`
**Created**: 2026-08-13
**Status**: Draft
**Input**: Upstream issue [`Priivacy-ai/spec-kitty#3387`](https://github.com/Priivacy-ai/spec-kitty/issues/3387) — *"Org-pack authoring fails silently: guide-named step contracts never load but are counted, misfielded profiles skipped, validation skips what the runtime reads"* — plus binding operator decisions delivered against a readiness probe's findings (Researcher Robbie). The issue states it verified its claims on `main @ 4a2367539`; this spec re-verified every cited code path directly against the checkout's current `main @ ab0a0b9b5` (`4a2367539` is an ancestor — `git merge-base --is-ancestor 4a2367539 ab0a0b9b5` succeeds, no drift affects the cited files). One issue claim is corrected below (Clarification 2) and one issue citation is corrected in-place (see "Verified Code Surfaces," snapshot.py).

---

## Clarifications

### Session 2026-08-13

- **Q1 (Defect #1 — step-contract glob/suffix mismatch, and whether to fix it on the legacy `MissionStepContract` surface given the unratified retirement ADR in flight):** Should this mission fix the `*.contract.yaml` vs `*.step-contract.yaml` mismatch on the legacy `step_contracts.py` surface now, or defer to PR #3378's proposed `MissionStep` unification?
  **A1 — Decision: fix it now, on the current legacy `MissionStepContract` / `step_contracts.py` surface.** Scope: a shared suffix constant consumed by `step_contracts.py`, `pack_validator.py`, and the snapshot bucket table (see correction below); the guide correction at `docs/guides/how-to/governance/create-an-org-doctrine-pack.md:65` and `:140` (currently document `*.contract.yaml`, must match the loader's actual `*.step-contract.yaml`); and a regression test proving that a contract file authored with the guide's old, incorrect suffix now produces a named diagnostic instead of silent non-loading.
  **Rationale:** this closes a live, guide-matching authoring trap that every pack author following the *currently published* guide hits today. Open PR #3378 carries ADR `docs/adr/3.x/2026-08-13-1-built-in-mission-subtree-stays-nested-retire-legacy-step-contracts.md`, which proposes retiring the entire `MissionStepContract` / `step_contracts.py` surface in favor of a unified `MissionStep` model — but that ADR is status `Proposed`, unratified, carries no target mission and no date, and is one of six ADRs bundled into PR #3378 (a docs-only design-review PR, `state: OPEN`, not merged — confirmed via `gh pr view 3378`), several of which the PR's own description marks "Deferred by decision." Nothing binds until an ADR is ratified. **This mission deliberately proceeds on the legacy surface.** If ADR `2026-08-13-1` is later ratified and `step_contracts.py` is deleted, this fix (a handful of lines plus one test file) is deleted with it at negligible sunk cost — named here so a reviewer does not discover the tension unaided and file it as scope drift.

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
and the ledger note below) and this mission's literal subject. Each functional requirement
below states not just what the new check detects, but what it does when it detects nothing
wrong (passes silently, by design) and what it does when it detects the defect (a named,
per-file diagnostic — never a bare `0` count or a swallowed exception).

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
| **Corrected: snapshot bucket-counting mechanism** | `src/specify_cli/doctrine/snapshot.py:53-65` vs `:195-212` | The issue cites `snapshot.py:53-65` with `endswith("contract.yaml")` semantics as the counter that "counts" a mis-suffixed contract. On this checkout, `_ARTIFACT_BUCKETS` (`:53-65`) is defined but **never referenced by any other code in the file or the repo** (`grep -rn "_ARTIFACT_BUCKETS" src/ tests/` returns only its own definition) — it is dead code. The function that actually populates `pack-manifest.yaml`'s `artifact_counts` is `_count_artifacts` (`:195-212`), which counts by **directory membership**, not filename suffix: for the `mission_step_contracts/` directory it runs `entry.rglob("*.yaml")` and counts *every* `.yaml` file inside, regardless of suffix. The net effect the issue describes (a mis-suffixed contract is counted by the snapshot but never loaded) **still holds**, but through `_count_artifacts`'s directory-glob, not the dead `_ARTIFACT_BUCKETS`/`endswith` path the issue names. FR-001 unifies both: it wires `_ARTIFACT_BUCKETS` (or removes it if unification makes it redundant — an implementation-phase call) to the same shared suffix constant, and leaves `_count_artifacts`'s directory-based counting behavior alone (it is not suffix-discriminating by design and is not the defect). |
| Asset repository recursion + rationale | `src/doctrine/assets/repository.py:18-22` (docstring), `:130-132` (`_project_scan`) | Docstring point 2 ("Recursive overlay discovery (A-3)") states the rationale verbatim: a non-recursive `glob` would never find `assets/<pack>/x.asset.yaml`. `_project_scan` overrides the base with `project_dir.rglob(self._glob)`. |
| Validator's non-recursive asset scan | `src/specify_cli/doctrine/pack_validator.py:202-206` | `_scan_files` recurses (`rglob`) only for `directory.name == "styleguides"`; all other kinds, `"assets"` included, get `directory.glob(glob)`. |
| Agent-profile skip machinery | `src/doctrine/agent_profiles/repository.py:293-309` (`_record_skip`), `:311-320` (`skipped_profiles`) | Both exist and are populated today at load time; nothing in `pack_validator.py` calls either. |
| Agent-profile closed schema | `src/doctrine/agent_profiles/profile.py:258` | `model_config = ConfigDict(extra="forbid", populate_by_name=True)`, added by `f732e10d6` (2026-07-27), an ancestor of the issue's cited verification commit `4a2367539`. |
| DRG fragment-only validator scope | `src/specify_cli/doctrine/pack_validator.py:480-609` (`_validate_drg`) | Only inspects `drg_dir.glob("*.graph.yaml")` (`:506`) — no pack-root scan exists anywhere in the function or the file. |
| Runtime DRG carrier | `src/charter/_drg_helpers.py:36-92` (`_resolve_org_root`, `load_validated_graph`) | `_resolve_org_root` always returns `None` (charter-layer-inert, by the `kernel <- doctrine <- charter <- specify_cli` layering); `load_validated_graph` calls `load_graph_or_dir(org_root)` — reads the pack root directly, never `org_root / "drg"`. |
| `pack validate` CLI entry point | `src/specify_cli/cli/commands/doctrine.py:348-372` (`pack_validate`) | Thin wrapper: calls `validate_pack(pack_path)` then `render_validation_result(result, json_output=...)`; exit code `0`/`1` on `result.ok`. Both FR-001's and FR-002's new diagnostics flow through this same `ValidationResult`/`ValidationIssue` surface — no new CLI command or flag is introduced. |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Author gets caught immediately when a step contract uses the guide's documented suffix (Priority: P1)

An org-pack author follows the published guide, names a file
`mission_step_contracts/acme-msc-001.contract.yaml` (the guide's current, incorrect
suffix), and runs `spec-kitty doctrine pack validate ./my-pack`.

**Why this priority**: this is the exact trap every pack author following the *current*
guide hits on their first contract. It currently produces total silence — the highest-harm
defect in the issue.

**Independent Test**: author a pack with only a `mission_step_contracts/` directory
containing a single `*.contract.yaml` file (no `*.step-contract.yaml` sibling); run `pack
validate --json`; assert the JSON payload names the offending file and states the expected
suffix, and the process exits `1`.

**Acceptance Scenarios**:

1. **Given** a pack whose `mission_step_contracts/` directory contains only
   `foo.contract.yaml`, **When** `pack validate` runs, **Then** it reports one error whose
   `category` names the suffix mismatch, whose `file` is the offending path, and whose
   `message` states the expected suffix (`*.step-contract.yaml`) — not a silent `0
   mission_step_contracts` scan with no diagnostic.
2. **Given** the same pack, **When** an author instead names the file
   `foo.step-contract.yaml` (the corrected guide's suffix), **Then** `pack validate`
   reports no error for that file and the loader (`MissionStepContractRepository`) loads it.

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
   --json` runs against the pack, **Then** the JSON payload includes a `skipped_profiles`
   entry naming the file, the profile id (when known), and the recorded `error_summary` —
   sourced from the same `AgentProfileRepository.skipped_profiles()` call `doctor doctrine
   --json` already uses, not a re-implementation.
2. **Given** a profile file with an undeclared key (the already-fixed acute case), **When**
   `pack validate` runs, **Then** it still reports exactly one diagnostic for that file (the
   existing `schema_invalid` error) — the new skip-surfacing does not double-report the same
   root cause as two unrelated-looking issues for one file.
3. **Given** a pack with no profile problems, **When** `pack validate` runs, **Then**
   `skipped_profiles` is empty/absent and `ok` is unaffected — no false positive.

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

- A pack with **both** `foo.contract.yaml` and `foo.step-contract.yaml` for what is clearly
  the same intended contract (same stem before the suffix): FR-001's diagnostic still fires
  for the stray `*.contract.yaml` file; it is a distinct file from the validator's
  perspective and the author needs to know it is dead weight, not a working duplicate.
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
| FR-001 | Shared step-contract suffix constant + validator mismatch diagnostic + guide correction | User Story 1 | High | Open |
| FR-002 | `pack validate` surfaces `skipped_profiles` inline (residual gap only) | User Story 2 | High | Open |
| FR-003 | `pack validate` recurses into `assets/` matching `AssetRepository` | User Story 3 | Medium | Open |
| FR-004 | `pack validate` advisory/error for DRG-only-under-`drg/` with no pack-root graph | User Story 4 | Medium | Open |

#### FR-001 — Shared step-contract suffix constant + validator mismatch diagnostic + guide correction

**Requirement**: Introduce one shared suffix constant for the mission-step-contract glob,
consumed by `step_contracts.py`'s `MissionStepContractRepository.GLOB` and
`pack_validator.py`'s `_artifact_schema_registry()` entry for `"mission_step_contracts"`
(both already agree on `"*.step-contract.yaml"` today — this step is de-duplication, not a
behavior change, and closes the drift risk that let the two definitions diverge from the
guide in the first place). Extend `snapshot.py`'s dead `_ARTIFACT_BUCKETS` table (or fold
it away, an implementation-phase call — see "Verified Code Surfaces" correction) to consume
the same constant so no third hand-maintained suffix string exists anywhere in the pack
authoring pipeline. Add a new `pack_validator.py` diagnostic: when a recognized artifact
directory (starting with `mission_step_contracts/`) contains a file that does not match the
directory's expected glob but *looks like* a near-miss for that artifact kind (i.e., a
`*.contract.yaml` file with no matching `*.step-contract.yaml`), emit a named error instead
of the current silent zero-match. Correct the guide
(`docs/guides/how-to/governance/create-an-org-doctrine-pack.md:65` and `:140`) from
`*.contract.yaml` to `*.step-contract.yaml` in both the layout tree and the namespace table.

**Fails how**: before this fix, a mis-suffixed contract file produces **zero** diagnostics
from `pack validate` (empty glob match, no error path) and **zero** loaded contracts from
the runtime, while the doctrine snapshot's `artifact_counts` (via `_count_artifacts`'s
directory-based `*.yaml` glob) counts it as present — an author sees "1 contract" in the
snapshot and a clean `pack validate`, and gets zero working contracts. After this fix,
`pack validate` names the specific file and the expected suffix; it does not guess at
intent or attempt to auto-rename the file.

**Acceptance Criteria**:
- AC-1: A pack with only `mission_step_contracts/foo.contract.yaml` fails `pack validate`
  with a new, named diagnostic category identifying the file and stating the expected
  `*.step-contract.yaml` suffix. Exit code is `1`.
- AC-2: The same pack, with the file renamed to `foo.step-contract.yaml`, passes `pack
  validate` for that file and is loaded successfully by
  `MissionStepContractRepository.get_by_action` in a round-trip test.
- AC-3: `docs/guides/how-to/governance/create-an-org-doctrine-pack.md` documents
  `*.step-contract.yaml` at both cited locations; no remaining reference to
  `*.contract.yaml` as the mission-step-contract suffix exists in that guide.
- AC-4: A regression test in `tests/doctrine/mission_step_contracts/` or
  `tests/specify_cli/doctrine/test_pack_validator.py` authors a contract file using the
  guide's old, now-corrected-away-from suffix and asserts the new diagnostic fires — proving
  the exact authoring mistake the guide used to lead authors into is now caught, not silent.
- **Targeted test surface**: `tests/specify_cli/doctrine/test_pack_validator.py`,
  `tests/specify_cli/doctrine/test_snapshot.py`, `tests/doctrine/mission_step_contracts/`.

#### FR-002 — `pack validate` surfaces `skipped_profiles` inline (residual gap only)

**Requirement**: `pack validate` additionally runs the same load path
`AgentProfileRepository` uses against the pack's `agent_profiles/` directory (org-layer
construction, i.e. treating the pack under validation as the sole org source) and includes
any `skipped_profiles()` entries in its `ValidationResult` — as `ValidationIssue`s with a
distinct category (e.g. `profile_skipped`) — deduplicated against files that already
produced a `schema_invalid` error from the existing generic per-file scan so one root cause
is not reported twice under two unrelated-looking categories. This is additive wiring, not
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
  post-merge failure mode) causes `pack validate --json` to include a `skipped_profiles`
  (or equivalently-named) entry with file, profile id (when resolvable), and error summary.
- AC-2: A profile file with an undeclared key (the already-fixed acute case) still produces
  exactly one diagnostic for that file from `pack validate`, not two.
- AC-3: A pack with no profile issues produces an empty/absent skip list and an unaffected
  `ok` result — no false positive, no regression to today's passing packs.
- AC-4: The new check reuses `AgentProfileRepository`/`skipped_profiles()` directly (verified
  by test asserting the same function is called or the same dataclass shape is surfaced) —
  it does not hand-roll a second skip-detection heuristic that could drift from the
  authoritative one `doctor doctrine --json` already uses.
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

**Fails how**: before this fix, a pack authored exactly per the guide's `drg/` section
passes `pack validate` cleanly and, per sibling mission #3384's finding, **zeroes the action
grain** on adoption — a destructive silent failure with no validation-time signal at all.
After this fix, `pack validate` names the mismatch at authoring time, before the pack is
ever published or fetched by a consumer.

**Acceptance Criteria**:
- AC-1: A pack with `drg/010-security.graph.yaml` and no pack-root `*.graph.yaml` produces
  the new diagnostic from `pack validate`, naming the runtime carrier it reads instead.
- AC-2: A pack with a pack-root `*.graph.yaml` (with or without `drg/` fragments) produces
  no such diagnostic.
- AC-3: A pack with neither a pack-root graph nor a `drg/` directory produces no such
  diagnostic (this check is about a *mismatch*, not about requiring DRG content to exist).
- AC-4: The diagnostic's severity (advisory vs. error) is decided at plan time but must be
  falsifiable in a test either way; given the destructive consequence documented in #3384
  and this mission's "silent success is the dominant defect class" mandate, the default
  expectation is **error** (fails `pack validate`'s exit code) rather than advisory-only,
  unless the plan phase records a specific reason to soften it.
- **Targeted test surface**: `tests/specify_cli/doctrine/test_pack_validator.py`.

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Legacy surface only | FR-001 touches `step_contracts.py` / the legacy `MissionStepContract` model only; it must not touch, extend, or begin migrating toward the unified `MissionStep` model referenced by unratified ADR `2026-08-13-1` (PR #3378). | Technical | High | Open |
| C-002 | No runtime DRG-carrier change | FR-004 must not modify `src/charter/_drg_helpers.py`, `load_graph_or_dir`, or `load_validated_graph` — that surface belongs to sibling mission #3384 (`org-pack-drg-root-graph-guard-01KZY0QT`), in spec phase concurrently. | Technical | High | Open |
| C-003 | No fifth surface | This mission's scope is bounded to exactly the four FRs above. No additional pack-authoring defect surfaced during implementation should be folded in without a scope amendment. | Process | Medium | Open |
| C-004 | Targeted test packages, not full suite | Per the charter's binding Testing Requirements section, validation runs only the test packages named per FR (`tests/specify_cli/doctrine/test_pack_validator.py`, `tests/specify_cli/doctrine/test_snapshot.py`, `tests/doctrine/mission_step_contracts/`, `tests/doctrine/test_agent_profile_model_field.py`), not a full `pytest tests/` gate. | Process | High | Open |

---

## Reflexivity: what happens to missions and packs mid-flight

This change alters `pack validate`, a surface other running missions and CI jobs invoke.
Per the charter's reflexivity expectation, the following consequences are explicit and
intended:

- **A pack that validated clean yesterday can start failing today.** All four FRs are new
  *diagnostics for pre-existing defects*, not new restrictions on previously-correct
  content. A pack with a `*.contract.yaml` stray file, a profile with a merge-time skip, a
  nested asset manifest, or `drg/`-only content was **already broken at runtime** before
  this mission — `pack validate`'s silence was itself the defect. This mission does not
  regress any pack that was genuinely working; it removes false-positive "healthy" reports
  from packs that were already delivering nothing for the affected artifact.
- **CI jobs that gate on `pack validate`'s exit code** (e.g. an org's own pack-repo CI
  calling `spec-kitty doctrine pack validate --json` per the guide's Step 5) will newly fail
  for packs exhibiting any of these four shapes. This is the intended effect — it is the
  entire point of the mission — but it is a real, visible behavior change for any pack in
  the wild today and should be called out in the mission's changelog entry / release note
  at merge time, not just in this spec.
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

- The three touched files (`pack_validator.py`, `snapshot.py`, `step_contracts.py`) carry
  pre-existing Sonar/complexity debt worth a look before or alongside the functional change
  — in particular `pack_validator.py`'s `validate_pack()` is already a long orchestration
  function and `_scan_artifact_directory`'s docstring already notes it was extracted to stay
  under ruff's C901 limit; adding FR-001/002/004's new checks should follow the same
  extract-a-helper discipline rather than growing `validate_pack()` in place. This is a
  planning-phase call, not specified further here — campsite-cleaning is scoped to
  domain-matched debt in files this mission touches, not a grab-bag.
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

- **SC-001**: A pack authored with the guide's pre-fix step-contract suffix
  (`*.contract.yaml`) fails `pack validate` with a named, per-file diagnostic; the identical
  pack authored with the corrected suffix (`*.step-contract.yaml`) passes validation and the
  contract loads via `MissionStepContractRepository`.
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
  `tests/specify_cli/doctrine/test_snapshot.py`, `tests/doctrine/mission_step_contracts/`,
  `tests/doctrine/test_agent_profile_model_field.py`) pass for the new/changed tests
  specifically — this criterion does not assume or require a green full-suite baseline
  (`main` carries ~23 known-red tests and 2 errors per issue #3284).
