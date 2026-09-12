---
description: "Work package task list template for mission implementation"
---

# Work Packages: Custom Mission Guard Failure Blocking Inert

**Inputs**: `kitty-specs/custom-mission-guard-failure-blocking-inert-01M0STY0/spec.md` (544 lines,
PASSED), `kitty-specs/custom-mission-guard-failure-blocking-inert-01M0STY0/plan.md` (604 lines,
PASSED, both with full adversarial review trails in `reviews/`)
**Prerequisites**: spec.md (PASSED), plan.md (PASSED). No research.md/data-model.md/contracts/
were produced — plan.md's own "Design decisions left to this plan" and "Seam and module
placement" sections carry that detail inline; this mission introduces no new entity, contract, or
external interface, so those artifacts were not generated (confirmed by plan.md's own Project
Structure section: "no new top-level directory is created").

**Tests**: Explicit ATDD test authoring is required for every WP (charter C-011, binding — not
optional; see "ATDD-first discipline" below).

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). WP00
(campsite-clean, resolver.py stale-comment + `__all__` restoration) is **folded into WP02** per
plan.md's binding sequencing — it has no standalone prompt file (see "WP00 disposition" below).

**Prompt Files**: Each work package references a matching prompt file in `tasks/`. This file is
the high-level checklist; deep implementation detail (exact commands, exact branch/set-comparison
logic, exact stub-vs-real staging) lives in the prompt files.

## Subtask Format: `[Txxx] [P?] Description`

- **[P]** would indicate the subtask can proceed in parallel — **none of the subtasks below carry
  `[P]`**, because this mission has a genuinely sequential dependency chain end to end (see "Write
  scopes / lanes / chokepoints" below); no subtask in this mission is safe to run concurrently
  with another WP's subtasks.
- Subtasks are **reference rows**, not checkboxes: record completion with
  `spec-kitty agent tasks mark-status <Txxx> --status done`. The reduced event-log snapshot is the
  sole subtask-completion authority.

## Path Conventions

Single project (this repo IS the tooling; no web/mobile split). All paths below are relative to
the repository root: `src/runtime/next/`, `src/specify_cli/runtime/`, `tests/runtime/`,
`tests/specify_cli/`, `tests/architectural/` (matches plan.md's Project Structure section
exactly — no new file or directory is added by this mission).

---

## Note — WP00 disposition (folded into WP02, no standalone prompt file)

Per plan.md's "Campsite-clean scope" and "Phasing / work-package shape" sections (binding, not
re-litigated here): the campsite-clean item (`src/specify_cli/runtime/resolver.py`'s stale
WP04b-deferral comment at lines 58-66, and restoring `required_artifacts_for` to `__all__` at
lines 46-57) is **folded into WP02**, landing as a commit that immediately follows (or is
combined with) WP02's functional commit that gives `required_artifacts_for` its first real
cross-module caller — never before it. Landing it any earlier would add
`required_artifacts_for` to `__all__` with zero callers and red
`tests/architectural/test_no_dead_symbols.py` — the exact failure the stale comment itself warns
about (this was PLAN-GOV-001, already found and fixed at the plan phase — see
`reviews/plan.confirmed.yaml`). WP00 therefore has **no standalone `tasks/WP00-*.md` file**; its
subtask (T014) lives inside `tasks/WP02-*.md`, sequenced explicitly as the second commit of that
WP.

---

## Baseline (binding — copy from plan.md's Baseline section)

This mission's branch (`fix/custom-mission-guard-3704`) is checked out at the exact merge-base of
`fix/org-tier-expected-artifacts-3703` (PR #3708) — verified live:
`git merge-base fix/org-tier-expected-artifacts-3703 fix/custom-mission-guard-3704` ==
`git rev-parse fix/org-tier-expected-artifacts-3703` (`ae3e5ad7a`) at authoring time. No
functional commit has landed on this branch yet — only spec/plan-phase documentation commits sit
on top. **Every WP's red-first ATDD verification and every diff computed while implementing this
mission MUST anchor on `fix/org-tier-expected-artifacts-3703`, never `main`** — diffing against
`main` would spuriously attribute PR #3708's ~47 commits (the org-tier path anchor) to this
mission. This anchor instruction is unaffected by, and does NOT change as a result of, the
PR-state correction immediately below — `planning_base_branch` stays
`fix/org-tier-expected-artifacts-3703` in every WP's frontmatter regardless of that branch's
upstream PR state.

**PR #3708 state correction (post-authoring, live-verified — TASKS-SEQ-001 fix).** PR #3708
merged into `origin/main` at `2026-08-24T14:01:27Z` (merge commit `3f8716fac`), roughly 3 minutes
after this tasks.md's authoring session's final commit — it was still open/"unmerged" at
authoring time (hence the phrasing above described it that way), but is **no longer open**.
Re-verified live for this fix round:
`gh pr view 3708 --repo Priivacy-ai/spec-kitty --json state,mergedAt` → `{"state":"MERGED","mergedAt":"2026-08-24T14:01:27Z"}`.
`git merge-base --is-ancestor ae3e5ad7a origin/main` succeeds — `ae3e5ad7a`
(`fix/org-tier-expected-artifacts-3703`'s tip, this mission's merge-base) is an ancestor of
`origin/main`, whose tip is literally PR #3708's own merge commit. **Pre-implementation
rebase decision (recorded, not executed — do not run `git rebase` to enact this until an
implementing WP actually starts):** `git merge-base HEAD origin/main` returns `ae3e5ad7a` itself
— every commit on `fix/custom-mission-guard-3704` since the merge-base is a spec/plan/tasks
documentation commit (no `src/` changes), and a trial `git merge-tree` of this branch's HEAD
against `origin/main` produces zero conflict markers. A rebase onto current `origin/main` before
WP01's first functional commit is therefore **mechanically a no-op today** (no functional code to
replay, no conflicts) — but it is still the operator's call whether to actually perform it before
WP01 starts, since it would shrink the eventual PR's diff against `main` down to just this
mission's own changes instead of carrying `ae3e5ad7a..origin/main`'s history implicitly via the
merge-base. This tasks-authoring pass records that conclusion; it does not execute the rebase.

`main` (and therefore this stacked branch, since it descends from `main` via
`fix/org-tier-expected-artifacts-3703`) carries ~23 known-red tests + 2 errors (issue #3284) and a
shared test-venv lock that can time out (issue #3283) — **accepted baseline, not this mission's to
fix.** Before each WP's first ATDD-red commit, it re-runs its own narrow test-file scope against
`fix/org-tier-expected-artifacts-3703` HEAD first, per plan.md's exact mechanism:

```bash
git fetch origin fix/org-tier-expected-artifacts-3703
uv run pytest tests/runtime/next/test_pertype_presence_gate.py tests/runtime/next/test_cli_guard_family.py \
    tests/runtime/test_bridge_parity.py tests/runtime/test_bridge_cores.py \
    tests/specify_cli/runtime/test_configured_artifact_name.py \
    tests/specify_cli/next/test_runtime_bridge_composition.py -v
# run against fix/org-tier-expected-artifacts-3703 HEAD, not main, not this branch
```

Any red found outside the accepted #3284 set (~23 failures + 2 errors) is a **fresh finding** —
the implementing WP stops and flags it in its own commit/report; only the operator authorizes
filing a new ledger/GitHub issue for it. No new red was authored or introduced during this
tasks-authoring session (no implementation code was touched); this section documents the
mechanism every implementing WP must follow, it does not itself constitute a run against that
baseline.

---

## ATDD-first discipline (charter C-011, binding — restated per WP below, not just once)

Every WP below requires a failing-first ATDD test as a **separate commit BEFORE** its
implementation commit(s). Red is verified on `planning_base_branch =
fix/org-tier-expected-artifacts-3703` (the stacked parent — see Baseline above and Mission
identity below); green is verified on the WP's final commit. This is mechanically checkable by a
later reviewer: each WP's prompt file names the exact test file(s) extended and the exact command
to run them, matching plan.md's "ATDD-first per WP" table verbatim (not re-derived).

**`planning_base_branch` frontmatter value — explicit resolution of a real tension in this
mission's authoring brief.** The mission brief's "Mission identity and branch" section (marked
"do not deviate") states: *"All WP frontmatter's `planning_base_branch` / red-first anchor must be
`fix/org-tier-expected-artifacts-3703`, NOT `main`."* This matches spec.md's own Clarifications
section verbatim (*"every WP's red-first ATDD verification MUST use `planning_base_branch =
fix/org-tier-expected-artifacts-3703`, not `main`"*) and plan.md's ATDD-first-per-WP table
(anchor column = `fix/org-tier-expected-artifacts-3703` for every WP). The brief's separate
"Tooling reality" section, by contrast, shows `planning_base_branch: "fix/custom-mission-guard-3704"`
as part of a **generic frontmatter-shape illustration** copied from `tasks/README.md`'s own
generic template (which naturally uses "the current mission branch" as its placeholder value,
since the README is not mission-specific). Given spec.md and plan.md both explicitly bind this
field's *value* to the stacked parent for this stacked mission, and the Mission-identity section
is marked "do not deviate," every WP file below sets
`planning_base_branch: "fix/org-tier-expected-artifacts-3703"` and
`merge_target_branch: "fix/custom-mission-guard-3704"` — the two fields answer different
questions (which branch is red-verified against vs. which branch the WP's changes land on), and
only the first one is affected by the stacking decision.

---

## Gate set for this mission (binding — copied from plan.md's "Gate set for this mission" section,
not re-derived)

**ENFORCED:** commitlint (every commit, conventional-commit format via `spec-kitty safe-commit`);
markdown lint (this mission's own markdown files); doctrine schema freshness (always-on, expected
to pass trivially — zero schema drift, `ArtifactPresenceSnapshot` is a plain
`@dataclass(frozen=True)`, not a generated Pydantic model); Contextive glossary (always-on,
expected to pass trivially — no new domain term, `blocking_artifact_names` is a field name);
TID251 banned-API lint; Typer JSON error surface (expected to pass trivially — no CLI surface
touched); `patch()` target validation (this mission's new/edited tests patch
`resolve_org_expected_artifacts`/`required_artifacts_for`, every target must resolve to a real
importable path); Bandit; pip-audit; `uv.lock` freshness (no new dependency) — **and, the one that
actually bites this mission: the `diff-coverage` job's 90% DIFF-coverage floor on
`critical_paths`** (`.github/workflows/ci-quality.yml:3283`, step at `:3333`, `critical_paths`
array at `:3345-3367` literally includes `'src/runtime/next/*'` at `:3366`,
`--fail-under=90 --include "${critical_paths[@]}"` at `:3391-3394`, no `|| true` escape). This
gates 4 of this mission's 5 blast-radius files — `runtime_bridge_cores.py`, `runtime_bridge_io.py`,
`runtime_bridge.py`, `runtime_bridge_composition.py` (all under `src/runtime/next/`) — at a 90%
floor on every new/changed line, on every PR. Only `src/specify_cli/runtime/resolver.py` escapes
this specific job (not in `critical_paths`), falling to the "diff-coverage (full-diff, advisory)"
step (`ci-quality.yml:3396`, non-blocking `|| true`) instead. **Every WP below that touches
`src/runtime/next/*` states explicitly, in its own file, that it budgets test coverage for its
own new/changed lines toward this 90% diff-coverage floor — this is not optional narrative, it
changes what "done" means for that WP.**

**The kernel-90% (`module-kernel.yml:58`, `--cov=src/kernel`) and mission-loader-90%
(`ci-quality.yml:1437-1456`, `--cov=src/specify_cli/mission_loader`) TOTAL-coverage floors do NOT
apply** — both measure packages entirely outside this mission's blast radius. (This is the plan's
own already-corrected classification — see `reviews/plan.confirmed.yaml` finding PLAN-VERIFY-001
for the paper trail on why the diff-coverage floor was initially missed and then added.)

**ADVISORY-ONLY in CI** (never treated as "CI will catch it"): `ruff`, `mypy` — `make lint` is
local discipline only. Every WP runs `make lint` locally before its commits regardless.

**NOT a PR gate on this repo:** SonarCloud Quality Gate does not run on pull requests here.

**Shared regression command block** (every WP re-runs this after its own narrow scope; copied
verbatim from plan.md's Gate set section):

```bash
uv run pytest <WP's specific test file(s)> -v
uv run pytest tests/architectural/test_bridge_cores_import_boundary.py -v   # only for WPs touching cores.py
uv run pytest tests/runtime/test_bridge_parity.py -v                        # every WP touching bridge*.py
uv run pytest tests/runtime/next/test_pertype_presence_gate.py tests/runtime/next/test_cli_guard_family.py -v
uv run pytest tests/specify_cli/runtime/test_configured_artifact_name.py -v # NFR-001 byte-compat
uv run pytest tests/specify_cli/next/test_runtime_bridge_composition.py -v
```

Always `uv run pytest ...` — never a bare `pytest` invocation for anything beyond a solo-file
sanity check, per plan.md's explicit instruction.

---

## Write scopes / lanes / chokepoints (binding — verified, not assumed)

**No genuine parallelism within this mission.** WP01 → WP02 → WP03 → WP04 form one sequential
dependency chain (WP01's snapshot field must exist before WP02 replaces its stub with real
resolution; WP02's org-tier reach must exist before WP03's call-site threading makes it live
end-to-end; WP03's convergence must be complete before WP04's full regression sweep is
meaningful). WP00's campsite-clean folds into WP02 for the same reason (its `__all__` restoration
is only valid once WP02's functional commit gives `required_artifacts_for` a real caller). There
is therefore no disjoint-write-scope check to perform *within* this mission — every WP after WP01
touches files a prior WP already touched, by design, and this is declared as a sequential
same-lane chain (via each WP's `Depends on WP0N` declaration below) specifically so
`validate_no_overlap`'s dependency-reachability exemption applies rather than flagging these as
colliding parallel WPs.

**Cross-mission check (already performed by the orchestrator before this authoring session; result
stated here):** 19 open PRs existed on `Priivacy-ai/spec-kitty` as of the authoring session's own
cutoff (2026-08-24, before ~14:01Z); **none** touched any of this mission's 5 blast-radius files
(`src/runtime/next/runtime_bridge_cores.py`, `runtime_bridge_io.py`, `runtime_bridge.py`,
`runtime_bridge_composition.py`, `src/specify_cli/runtime/resolver.py`). PR #3708
(`fix/org-tier-expected-artifacts-3703`, this mission's own stacked parent) was among those 19 at
that time, but its files were already in this mission's base — not a conflict source, an ancestor.

**Re-run for this fix round (TASKS-SEQ-001), current as of this correction:** PR #3708 has since
**merged** into `origin/main` (`2026-08-24T14:01:27Z`, merge commit `3f8716fac`) and PR #3707 also
merged around the same time — both are no longer part of the open-PR set. Live re-run —
`gh pr list --repo Priivacy-ai/spec-kitty --state open --json number` → **17 open PRs** (19 − the
2 that merged), and `gh pr list --repo Priivacy-ai/spec-kitty --state open --json number,files`
filtered against this mission's 5 blast-radius files returns **zero matches**. The substantive
"write scopes disjoint from every currently-open PR" conclusion is **reconfirmed, not just
carried forward** — none of the 17 currently-open PRs touch any of the 5 files above. See the
Baseline section above for the live PR #3708 merge-state verification and the pre-implementation
rebase-need conclusion (recorded, not executed).

**Chokepoint.** Every WP touching `src/runtime/next/*` (WP01, WP02's functional half, WP03, WP04)
shares the same enforced `diff-coverage` 90% CI gate — that shared gate, plus the sequential
dependency chain itself, means this mission is effectively serialized end-to-end regardless of
what a lanes/parallelism file might otherwise suggest. **Contract-moves check (per plan.md's own
section, restated here, not re-derived):** this mission does **not** touch the migration chain,
any doctrine schema, any mission step contract, the orchestrator-api surface, or the vendored
`spec-kitty-events` package. `ArtifactPresenceSnapshot.blocking_artifact_names` is additive
(default `None`, no existing construction call site breaks) and internal (referenced only inside
`runtime_bridge_io.py`/`runtime_bridge_cores.py` and their own test files — never by
`orchestrator_api/commands.py` or any `spec_kitty_events`-adjacent code). The one externally-visible
consequence — `Decision.guard_failures`'s *content* changes for custom families with a declared
manifest, since that field is already part of `spec-kitty next --json`'s serialized output — is
NFR-002's own concern, not a contract move, and is WP04's explicit documentation deliverable
(T028). So: **the only chokepoint here is the shared CI gate + the dependency chain, not a
contract-stability one.**

---

<!-- WORK PACKAGES BELOW -->

---

## Work Package WP01: Snapshot field + `evaluate_guards_strict` dispatch branch (FR-001/FR-002/FR-006 core, Priority: P1)

**Goal**: Give `evaluate_guards_strict` a real, data-driven branch for a family outside
`_GUARD_TABLES` — `snapshot.blocking_artifact_names is None` (raise, unchanged) vs. a real
`frozenset` (evaluate genuinely) — built and ATDD-tested in isolation against a **minimal
test-only stub** population of the new field, so the import-boundary-sensitive change lands as
its own small, easily-reviewed diff before WP02's larger org-tier plumbing.
**Independent Test**: Construct an `ArtifactPresenceSnapshot`-shaped test double with
`blocking_artifact_names` set to `None`, then to `frozenset()`, then to a non-empty `frozenset`
missing from `present_artifacts`; assert `evaluate_guards_strict` raises
`UnregisteredMissionFamilyError` only in the `None` case, and otherwise returns `[]` /
non-empty accordingly — reachable without any org-tier manifest resolution existing yet (that is
WP02's job).
**Prompt**: `tasks/WP01-snapshot-field-and-dispatch-branch.md`
**Requirement Refs**: FR-001, FR-002, FR-006 (Protocol/dataclass field + cores.py branch only —
real population is WP02), AC-3, AC-9

### Included Subtasks

T001 [ATDD-RED] Extend `tests/runtime/test_bridge_cores.py` with failing test case(s) for
`evaluate_guards_strict`'s new `snapshot.blocking_artifact_names is None` branch
T002 [ATDD-RED] Extend `TestCustomFamilyPresenceGateFailsClosedBothDirections` in
`tests/runtime/next/test_pertype_presence_gate.py` with AC-9's two-family distinguishability case
T003 Add `blocking_artifact_names -> frozenset[str] | None` read-only `@property` to
`_ArtifactPresenceSnapshotLike` Protocol in `src/runtime/next/runtime_bridge_cores.py:354`
T004 Add the `is None` branch to `evaluate_guards_strict` in
`src/runtime/next/runtime_bridge_cores.py:684` (dispatch-miss point at line 693-695)
T005 Add `blocking_artifact_names: frozenset[str] | None = None` field to `ArtifactPresenceSnapshot`
dataclass in `src/runtime/next/runtime_bridge_io.py:900`
T006 Populate `blocking_artifact_names` inside `gather_artifact_presence`
(`src/runtime/next/runtime_bridge_io.py:931`) with a minimal test-only stub (not full org-tier
resolution — WP02 replaces this)
T007 Run WP01's regression command block; verify T001/T002 green; verify
`tests/architectural/test_bridge_cores_import_boundary.py` stays green; budget coverage for new
lines toward the 90% diff-coverage floor on `src/runtime/next/*`

### Implementation Notes

- `evaluate_guards_strict` MUST test `is None` explicitly, never bare falsiness
  (`frozenset()` is falsy in Python — `if not snapshot.blocking_artifact_names:` would silently
  reintroduce SPEC-FRESH-001's exact collapse). See plan.md's "SPEC-FRESH-001 preservation"
  section.
- The stub in T006 exists ONLY to let T001/T002 exercise the cores.py branch in isolation; it must
  not attempt org-tier lookup — that would pull `charter.missions`-shaped complexity into WP01's
  small diff and duplicate WP02's work.
- This WP touches `src/runtime/next/*` — budget test coverage for T003-T006's new/changed lines
  toward the enforced 90% diff-coverage floor (`ci-quality.yml:3333`, `critical_paths` includes
  `'src/runtime/next/*'`).

### Dependencies

- None (first work package in this mission's implementation chain).

### Risks & Mitigations

- Risk: a reviewer conflates the stub's temporary population logic with WP02's real resolution and
  approves the wrong invariant. Mitigation: T006's stub is explicitly labeled test-only in its own
  commit message and in the WP prompt file; WP02's task (T013) explicitly states it *replaces* T006.

---

## Work Package WP02: Org-tier manifest resolution + campsite-clean (FR-004/FR-005/FR-007/FR-008, Priority: P1)

**Goal**: Make `_presence_filenames_for`, `required_artifacts_for`, and
`_load_expected_artifact_manifest` org-tier-aware (built-in tier as before, org tier via
`resolve_org_expected_artifacts`, whole-file-replacement, never merged); replace WP01's test-only
stub inside `gather_artifact_presence` with the real resolution. **Folds WP00's campsite-clean
commit** (restoring `required_artifacts_for` to `resolver.py`'s `__all__`, fixing the stale
WP04b-deferral comment) as the commit immediately following this WP's functional commit.
**Independent Test**: Stand up an org pack at `<org_root>/missions/<type>/expected-artifacts.yaml`
with a mix of `blocking: true`/`blocking: false` entries across two steps, and a built-in manifest
for the same family (or none) as a control. Assert the org file wins whole-file (never merged),
that only `blocking: true` absences populate `blocking_artifact_names`, and that a `blocking:
false` absence never does — at each step independently.
**Prompt**: `tasks/WP02-org-tier-manifest-resolution-and-campsite-clean.md`
**Requirement Refs**: FR-004, FR-005, FR-006 (real population), FR-007, FR-008, FR-010, AC-4,
AC-5, AC-6, C-002

### Included Subtasks

T008 [ATDD-RED] Add org-tier test cases to `tests/specify_cli/runtime/test_configured_artifact_name.py`
(mirroring `ManifestRegistry.load_manifest`'s FR-008/WP05 test shape); includes a named
`repo_root`-supplied-but-no-org-pack fallback case (TASKS-VERIFY-003 fix)
T009 [ATDD-RED] Add AC-4/AC-5/AC-6 org-tier + whole-file-replacement scenarios to
`tests/runtime/next/test_pertype_presence_gate.py`; includes a named
`repo_root`-supplied-but-no-org-pack fallback case (TASKS-VERIFY-003 fix)
T009b [ATDD-RED, FR-010 fix round] Add schema-invalid-manifest test cases to
`tests/specify_cli/runtime/test_configured_artifact_name.py`: a built-in manifest and an org-tier
manifest that each parse as YAML but fail `ExpectedArtifactManifest`'s Pydantic schema
(`extra="forbid"`), asserting `_load_expected_artifact_manifest`/`required_artifacts_for` raise
`ManifestSchemaError` (not a bare `pydantic.ValidationError`) for both tiers. For the org-tier
case, also assert `ManifestSchemaError.origin` is a non-empty descriptive string naming the org
tier + mission type (mirrors `manifest.py`'s synthesized org-tier origin, `manifest.py:283-291`
— never the built-in branch's `config.origin`, which is unreachable and `AttributeError`-prone
in the org-tier branch — ANALYZE-FRESH-001). Verify RED against
`fix/org-tier-expected-artifacts-3703` before writing implementation code.
T010 `_load_expected_artifact_manifest` (`src/specify_cli/runtime/resolver.py:555`) gains
`repo_root: Path | None = None`, becomes org-aware via `resolve_org_expected_artifacts` (FR-008),
mirroring `ManifestRegistry.load_manifest`'s parameter shape (`src/specify_cli/dossier/manifest.py:193-233`)
T010b [FR-010 fix round; org-tier origin corrected per ANALYZE-FRESH-001]
`_load_expected_artifact_manifest` wraps each tier's `ExpectedArtifactManifest.model_validate(...)`
call in its own `try/except pydantic.ValidationError`, re-raising `ManifestSchemaError` (imported
from `specify_cli.dossier.manifest`) with a **branch-specific origin** — mirroring
`ManifestRegistry.load_manifest`'s own two DIFFERENT origin expressions per branch
(`src/specify_cli/dossier/manifest.py:274-340`), NOT a single shared `config.origin`: the built-in
branch uses `ManifestSchemaError(mission_type, config.origin)` (`config` is a real `ConfigResult`
there, `manifest.py:326-340`); the org-tier branch synthesizes a descriptive origin string (mission
type + org roots checked, mirroring `manifest.py:283-291`'s org-tier except-block) because
`resolve_org_expected_artifacts` returns a bare `Mapping` with no `.origin` attribute — using
`config.origin` there would raise `AttributeError`, not `ManifestSchemaError`. Do not mask that
risk with a broad `except Exception` either. Closes ANALYZE-ARCH-001/FR-010's crash risk; lands
in the same commit as T010 (or immediately after it, before T011) — makes T009b GREEN.
T011 `required_artifacts_for` (`src/specify_cli/runtime/resolver.py:634`) gains
`repo_root: Path | None = None`, forwards to `_load_expected_artifact_manifest`
T012 `_presence_filenames_for` (`src/runtime/next/runtime_bridge_io.py:841`) gains
`repo_root: Path | None = None`; also consults org tier (FR-004), stays family-scoped not
step-scoped (FR-005/C-002 — do not re-attempt step-scoping)
T013 [functional commit] `gather_artifact_presence` (`src/runtime/next/runtime_bridge_io.py:931`)
gains `repo_root: Path | None = None`, forwards it; replaces WP01's stub with real resolution —
reuses the same tier-checking `config is None`/org-tier-equivalent logic already run for
`_presence_filenames_for` (lines ~891-892) to decide `None` vs. real `frozenset`; wraps
`required_artifacts_for(...)`'s `list[str]` in `frozenset(...)`. **This is the commit that gives
`required_artifacts_for` its first real cross-module caller.**
T014 [campsite-clean commit, folds WP00 — lands immediately AFTER T013, never before] Restore
`required_artifacts_for` to `resolver.py`'s `__all__` (lines 46-57); remove/update the stale
WP04b-deferral comment (lines 58-66) to reflect the real wiring T013 just landed
T015 Run WP02's regression command block; verify T008/T009/T009b green; verify
`tests/architectural/test_no_dead_symbols.py` stays green (would RED if T014 landed before T013);
budget coverage for new/changed lines toward the 90% diff-coverage floor (resolver.py changes fall
to the advisory full-diff step only, per Gate set above)

### Implementation Notes

- Commit order inside this WP is load-bearing: (1) T008/T009/T009b RED tests, (2)
  T010/T010b-T013 functional implementation (GREEN), (3) T014 campsite-clean — never T014 before
  T013 (PLAN-GOV-001, `reviews/plan.confirmed.yaml`).
- `required_artifacts_for` itself keeps returning `list[str]` — the `frozenset(...)` wrap happens
  at the `gather_artifact_presence` call site (T013), not inside `required_artifacts_for`, so its
  own existing unit-tested contract (`tests/specify_cli/runtime/test_configured_artifact_name.py`)
  stays intact.
- C-002 (binding, not reopened here): do NOT re-attempt step-scoping `_presence_filenames_for` —
  a prior attempt reverted after redding `test_coverage_floor_is_met` by spuriously blocking
  software-dev's composed `tasks` guard and `plan`'s `specify`/`plan` guards. `blocking:`-awareness
  is solved at the evaluation layer (WP01), not by gathering-layer step-scoping.
- FR-010 (malformed manifest handling) — **corrected (ANALYZE-ARCH-001 fix round; a prior draft
  of this note falsely claimed both halves were "already implemented" — they were not):**
  built-in YAML-syntax failures already raise `MalformedManifestError` loudly
  (`MissionTemplateRepository.get_expected_artifacts`, #3412 already fixed there); org-tier
  YAML-syntax failures still degrade silently (`resolve_org_expected_artifacts`) — a pre-existing,
  out-of-scope built-in/org asymmetry this WP does not reconcile. Neither tier raises
  `ManifestSchemaError` on this WP's call path today — that type is defined/raised only in
  `specify_cli.dossier.manifest.ManifestRegistry.load_manifest`, a sibling module none of this
  WP's functions call. Because T010 edits `_load_expected_artifact_manifest` to add org-tier
  awareness (FR-008) — the first change that makes the org tier reach
  `ExpectedArtifactManifest.model_validate(...)` — this WP also closes the resulting
  uncaught-`pydantic.ValidationError` crash risk in that same function, for both tiers, via T009b
  (RED) and T010b (GREEN): wrap `model_validate(...)` in `try/except pydantic.ValidationError`,
  re-raise `ManifestSchemaError` (imported from `specify_cli.dossier.manifest`, precedented by
  `specify_cli.sync.namespace`/`specify_cli.sync.dossier_pipeline`'s existing imports of that
  type — no architectural boundary gate forbids `specify_cli.runtime` importing
  `specify_cli.dossier`). This is a small, in-file addition to a function this WP already edits;
  it does not expand WP02's `owned_files` beyond what it already lists, nor plan.md's Seam table
  beyond the row it already commits to.
- This WP touches `src/runtime/next/*` (T012, T013) — budget coverage for those new/changed lines
  toward the enforced 90% diff-coverage floor.

### Dependencies

- Depends on WP01.

### Risks & Mitigations

- Risk: landing T014 before T013 (or in a separate, earlier commit) reds
  `test_no_dead_symbols.py`. Mitigation: T014 is explicitly sequenced last in this WP's subtask
  list and its own subtask text says "lands immediately AFTER T013, never before."

---

## Work Package WP03: `repo_root` call-site convergence (FR-003, Priority: P1)

**Goal**: Thread the already-live `repo_root` local through all 3 real call sites so WP02's
org-tier reach is genuinely live end-to-end (AC-8), not merely reachable from a unit test that
calls the leaf function directly. The WP-iteration pre-check and the composed-action guard must
reach the same evaluation result for the same `(mission_family, step_id)` input (FR-003's
convergence requirement).
**Independent Test**: With an org-tier manifest reachable and no built-in manifest for a custom
family, drive both the CLI/WP-iteration pre-check and the composed-action guard for the same step
and on-disk artifact state; assert both report the same `guard_failures` (neither disagrees with
the other), and assert `resolve_org_roots` is invoked with the real, non-`None` `repo_root` the
enclosing function already holds (AC-8).
**Prompt**: `tasks/WP03-repo-root-call-site-convergence.md`
**Requirement Refs**: FR-003, AC-1, AC-2, AC-8, NFR-004

### Included Subtasks

T016 [ATDD-RED] Add AC-1/AC-2 test cases to `tests/runtime/next/test_cli_guard_family.py`
T017 [ATDD-RED] Add AC-8 test case asserting `resolve_org_roots` is invoked with the real
`repo_root` for a custom mission family, exercising the WP-iteration pre-check call site
(`runtime_bridge.py` ~line 1608) — structurally cannot reach the CLI pre-check call site (see
T017b)
T017b [ATDD-RED, TASKS-VERIFY-001 fix] Add a second AC-8 test case, scoped to the `software-dev`
family at a non-WP-iteration step (e.g. `specify`) with an org-tier manifest override, asserting
`resolve_org_roots`/the org-tier manifest is consulted with the real `repo_root` specifically
through the CLI pre-check call site (`runtime_bridge.py` ~line 1643, gated by
`get_mission_type(feature_dir) == MISSION_TYPE_SOFTWARE_DEV` at ~line 1642) — the call site T017's
custom-family scenario cannot reach
T018 `_check_cli_guards` (`src/runtime/next/runtime_bridge.py:751`) gains
`repo_root: Path | None = None`, forwards to `gather_artifact_presence`
T019 `_dn_dependency_gate` (`src/runtime/next/runtime_bridge.py:1538`, `repo_root = ctx.repo_root`
local at line 1549) forwards the already-live local at both `_check_cli_guards` call sites
(WP-iteration pre-check ~line 1607-1610, CLI pre-check ~line 1631-1643) — currently dropped at both
T020 `_check_composed_action_guard` (`src/runtime/next/runtime_bridge_composition.py:429`) gains
`repo_root: Path | None = None`, forwards to `gather_artifact_presence`
T021 `_dispatch_via_composition` (`src/runtime/next/runtime_bridge_composition.py:502`, already
requires `repo_root` as a required kw) stops dropping it at its call site (line ~626,
`_rb._check_composed_action_guard(action, feature_dir, mission=mission, legacy_step_id=legacy_step_id)`)
— forward `repo_root=repo_root`
T022 Run WP03's regression command block; verify T016/T017 green; verify
`test_non_software_dev_missing_artifact_owned_by_composed_guard`
(`tests/runtime/test_bridge_parity.py:1242`) stays green (NFR-004); budget coverage for
new/changed lines toward the 90% diff-coverage floor

### Implementation Notes

- `_check_cli_guards`'s two live call sites inside `_dn_dependency_gate` (~1607-1610 for
  WP-iteration, ~1631-1643 for the CLI pre-check) both already have `repo_root` in local scope —
  this WP forwards the already-live value, it does not compute a new one.
- The CLI pre-check at `runtime_bridge.py` ~line 1642 stays scoped to the `software-dev` mission
  family (#3407 M3) — do not widen that scoping; `test_non_software_dev_missing_artifact_owned_by_composed_guard`
  is the regression guard pinning this, and it is the exact mechanism keeping
  `_GUARD_BRANCH_FLOOR` (18) met (NFR-004) — not FR-005's family-scoping, which is a separate,
  unrelated mechanism.
- This WP touches `src/runtime/next/*` (all 4 files: cores.py is read-only here but bridge.py,
  bridge_composition.py, and the io.py call boundary are touched) — budget coverage accordingly.

### Dependencies

- Depends on WP02.

### Risks & Mitigations

- Risk: widening the CLI pre-check's family scoping while threading `repo_root` accidentally
  changes which families it fires for, redding the coverage floor. Mitigation: T022 explicitly
  re-runs `test_coverage_floor_is_met`'s sibling regression test as part of this WP's own gate,
  not deferred to WP04 alone.

---

## Work Package WP04: Full regression/NFR sweep + NFR-002 documentation deliverable (Priority: P1)

**Goal**: Confirm byte-identical behavior for the 4 built-in families (NFR-001/AC-7), confirm
AC-3/AC-9's three-outcome distinguishability end to end, confirm the coverage floor and the
frozen-template e2e walk both stay green, demonstrate AC-10 at the conventional
`<org_root>/missions/<type>/` layout, and land NFR-002's mandatory operator-visible-behavior-change
documentation (PLAN-ARCH-001, binding — this WP owns it, it has no other WP owner).
**Independent Test**: Run the full named regression suite below against this WP's final commit;
every listed test file is green; the CHANGELOG.md entry and/or tracer-design-decisions.md note
exists and states plainly that `spec-kitty next --json`'s `guard_failures`/`Decision.kind` output
for a custom mission family with a declared manifest changes content after this mission (a family
that previously always emitted `guard_failures == []` can now emit real failure strings and a
`blocked` decision).
**Prompt**: `tasks/WP04-regression-sweep-and-nfr002-docs.md`
**Requirement Refs**: NFR-001, NFR-002, NFR-004 (final confirm), FR-009, FR-011, FR-012, AC-3,
AC-7, AC-9, AC-10, C-001

### Included Subtasks

T023 Run full NFR-001 byte-compat suite: `tests/specify_cli/runtime/test_configured_artifact_name.py`
and the `TestAC14SoftwareDevUnchanged` class in `test_cli_guard_family.py` — confirm byte-identical
`guard_failures` for `research`/`documentation`/`software-dev`/`plan` (FR-009/NFR-001/AC-7)
T024 Run AC-3/AC-9 confirmation: `TestTypelessMissionFamily` and
`TestIssue3627WpIterationUnregisteredFamilyDegrades` in `test_cli_guard_family.py` stay green
(C-001 — unregistered/typeless family behavior unchanged)
T025 Run `tests/runtime/test_bridge_parity.py::test_coverage_floor_is_met` — confirm the
`_GUARD_BRANCH_FLOOR` (18, `test_bridge_parity.py:1196`) stays met (NFR-004)
T026 Run `tests/specify_cli/next/test_runtime_bridge_composition.py::TestCustomMissionComposition`
— confirm the frozen-template e2e walk for an unregistered custom mission type still runs to
completion (C-001)
T027 AC-10 end-to-end demonstration: stand up a custom family (e.g. `qa`) with
`<org_root>/missions/qa/expected-artifacts.yaml` at the conventional layout (reachable now that
this branch is stacked on #3708's path fix) and walk a `next` decision showing the family gates
on its own filenames; record the walk as this WP's Independent Test evidence
T028 NFR-002 documentation deliverable: add a CHANGELOG.md entry and/or an operator-facing note in
`tracer-design-decisions.md` documenting that `spec-kitty next --json`'s
`guard_failures`/`Decision.kind` output for custom mission families with a declared manifest
changes content (PLAN-ARCH-001)
T029 Run the full shared regression command block (all 6 commands, Gate set section above) one
final time against this WP's final commit; confirm every blast-radius file is green end to end

### Implementation Notes

- T023-T026 run (not necessarily extend) existing test files/classes — this WP's own new test
  authoring, if any, is limited to whatever AC-10's demonstration (T027) needs to be reproducible;
  it is not expected to add new assertions to the byte-compat/coverage-floor/frozen-template
  suites, only to keep them green.
- T028 is a **required non-test deliverable**, not optional narrative — see plan.md's "Blast
  radius to downstream workspaces" section: `Decision.guard_failures` is already part of
  `spec-kitty next --json`'s serialized stdout contract (`next_cmd.py:899-905` under `--json`,
  `next_cmd.py:1056-1057` human-readable); this mission changes that field's *content* for custom
  families, not its schema — a downstream consumer treating `guard_failures == []` as "always
  passes" will start seeing real blocks after this mission ships. NFR-002 requires this be
  documented, "not silently absorbed."
- This WP's own diff should be small (mostly test-running + one CHANGELOG/tracer edit) — the bulk
  of `src/runtime/next/*` coverage risk was already retired by WP01-WP03; T029's full sweep is the
  final confirmation, not a place where new uncovered lines are expected to appear.

### Dependencies

- Depends on WP03.

### Risks & Mitigations

- Risk: NFR-002's documentation deliverable gets treated as optional polish and dropped under time
  pressure. Mitigation: it is a named subtask (T028) with its own line in the Requirements
  Coverage Summary below, not folded into a vague "wrap up" bullet.

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP02 (folds WP00) → WP03 → WP04. Strictly linear — see "Write scopes /
  lanes / chokepoints" above for why no `[P]` parallel marker appears anywhere in this mission.
- **Parallelization**: None within this mission. All 4 WPs share the same `diff-coverage` 90%
  enforced CI gate on `src/runtime/next/*`, which is the mission's one real chokepoint (alongside
  the dependency chain itself).
- **MVP Scope**: All 4 WPs are required to close the issue — Part 1 (dispatch, WP01/WP03) has
  nothing to evaluate without Part 2 (manifest reach, WP02), and Part 2 has no consumer without
  Part 1, per spec.md's own framing. There is no smaller MVP cut within this mission.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) | Note |
|---|---|---|
| FR-001 | WP01 | Data-driven evaluation for a declared-but-untabled family |
| FR-002 | WP01 | Three distinguishable dispatch outcomes |
| FR-003 | WP03 | All three call sites converge on one evaluation |
| FR-004 | WP02 | Org-tier-aware manifest lookup, threaded to real call sites |
| FR-005 | WP02 | Presence gathering stays family-scoped, not step-scoped |
| FR-006 | WP01 (field/branch), WP02 (real population) | `blocking:` honored at evaluation layer |
| FR-007 | WP02 | `required_artifacts_for` wired in + restored to `__all__` (WP00 fold) |
| FR-008 | WP02 | `required_artifacts_for`'s own manifest lookup becomes org-aware |
| FR-009 | WP04 | Byte-identical behavior for the 4 built-in families (verification) |
| FR-010 | WP02 (T009b/T010b) | Malformed-manifest handling: correct the precedent claim; close org-tier schema-validation crash risk |
| FR-011 | Not touched (non-goal) | `accept` step's built-in `[]` stays untouched; confirmed unchanged by WP04's regression sweep |
| FR-012 | Not touched (non-goal) | `mission_v1.guards`/`GUARD_REGISTRY` not revived; no WP touches this surface |
| NFR-001 | WP04 | Byte-compat for built-in families (verification) |
| NFR-002 | WP04 | Reflexivity + mandatory documentation deliverable (T028) |
| NFR-003 | All WPs | ATDD-first/red-first discipline — see "ATDD-first discipline" above |
| NFR-004 | WP03 (mechanism), WP04 (final confirm) | Coverage floor stays met |
| C-001 | WP01 (preserved by branch design), WP04 (verification) | No hard-block for unknown/typeless families |
| C-002 | WP02 | No naive step-scoping of `_presence_filenames_for` |
| C-003 | N/A | Not this mission's scope — org-tier path anchor is #3703/PR #3708, already merged into this branch's history; WP02 consumes it, does not re-implement it |
| C-004 | Not touched (non-goal) | `accept` step's built-in `[]` is deliberate; see FR-011 |
| C-005 | Not touched (non-goal) | `mission_v1.guards`/`GUARD_REGISTRY` not revived; see FR-012 |
| AC-1 | WP03 | Composed-action guard blocks on missing blocking artifact |
| AC-2 | WP03 | Composed-action guard passes on genuine evaluation |
| AC-3 | WP01 (built), WP04 (confirmed) | No-manifest family behavior unchanged |
| AC-4 | WP02 | Org-tier manifest consulted, blocks correctly |
| AC-5 | WP02 | `blocking: false` never contributes to `guard_failures` |
| AC-6 | WP02 | Org file wins whole-file, never field-merged |
| AC-7 | WP04 | 4 built-in families byte-identical (verification) |
| AC-8 | WP03 | `resolve_org_roots` invoked with real `repo_root` |
| AC-9 | WP01 (built), WP04 (confirmed) | Two-family distinguishability despite both empty `required_artifacts_for` |
| AC-10 | WP04 | End-to-end demo at conventional `<org_root>/missions/<type>/` layout (pre-existing AC-ID, external to this spec's own numbering — see spec.md Clarifications) |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|---|---|---|---|---|
| T001 | ATDD-RED: `evaluate_guards_strict` `is None` branch cases | WP01 | P1 | No |
| T002 | ATDD-RED: AC-9 two-family distinguishability case | WP01 | P1 | No |
| T003 | Add `blocking_artifact_names` Protocol property | WP01 | P1 | No |
| T004 | Add `is None` branch to `evaluate_guards_strict` | WP01 | P1 | No |
| T005 | Add `blocking_artifact_names` dataclass field | WP01 | P1 | No |
| T006 | Populate field with test-only stub | WP01 | P1 | No |
| T007 | WP01 regression run + coverage budget | WP01 | P1 | No |
| T008 | ATDD-RED: org-tier `test_configured_artifact_name.py` cases + no-org-pack fallback (TASKS-VERIFY-003) | WP02 | P1 | No |
| T009 | ATDD-RED: AC-4/AC-5/AC-6 org-tier scenarios + no-org-pack fallback (TASKS-VERIFY-003) | WP02 | P1 | No |
| T009b | ATDD-RED: schema-invalid-manifest cases, both tiers (FR-010, ANALYZE-ARCH-001 fix) | WP02 | P1 | No |
| T010 | `_load_expected_artifact_manifest` org-aware | WP02 | P1 | No |
| T010b | `_load_expected_artifact_manifest` re-raises `ManifestSchemaError` on schema-invalid manifests, both tiers (FR-010, ANALYZE-ARCH-001 fix) | WP02 | P1 | No |
| T011 | `required_artifacts_for` gains `repo_root` | WP02 | P1 | No |
| T012 | `_presence_filenames_for` org-tier consult | WP02 | P1 | No |
| T013 | `gather_artifact_presence` real resolution (functional commit) | WP02 | P1 | No |
| T014 | Campsite-clean: `__all__` + stale comment (folds WP00) | WP02 | P1 | No |
| T015 | WP02 regression run + coverage budget | WP02 | P1 | No |
| T016 | ATDD-RED: AC-1/AC-2 `test_cli_guard_family.py` cases | WP03 | P1 | No |
| T017 | ATDD-RED: AC-8 `resolve_org_roots repo_root` case (custom family, WP-iteration call site) | WP03 | P1 | No |
| T017b | ATDD-RED: AC-8 `resolve_org_roots repo_root` case (software-dev family, CLI pre-check call site — TASKS-VERIFY-001) | WP03 | P1 | No |
| T018 | `_check_cli_guards` gains `repo_root` | WP03 | P1 | No |
| T019 | `_dn_dependency_gate` forwards `repo_root` at both call sites | WP03 | P1 | No |
| T020 | `_check_composed_action_guard` gains `repo_root` | WP03 | P1 | No |
| T021 | `_dispatch_via_composition` stops dropping `repo_root` | WP03 | P1 | No |
| T022 | WP03 regression run + coverage budget | WP03 | P1 | No |
| T023 | Run NFR-001 byte-compat suite | WP04 | P1 | No |
| T024 | Run AC-3/AC-9 unregistered-family confirmation | WP04 | P1 | No |
| T025 | Run coverage-floor test | WP04 | P1 | No |
| T026 | Run frozen-template e2e walk | WP04 | P1 | No |
| T027 | AC-10 end-to-end demonstration | WP04 | P1 | No |
| T028 | NFR-002 documentation deliverable | WP04 | P1 | No |
| T029 | Final full shared regression sweep | WP04 | P1 | No |

---

## PR Shape

**Verdict: ONE PR for the whole mission** (the repo default per charter/AGENTS.md — `accept` →
`merge` machinery assumes one mission branch; `tk`'s per-WP-PR convention is a different repo's
rule and does not apply here).

**Reasoning**: plan.md's own Technical Context describes this mission's scope as "4 source files
touched in `src/`... + 2 in `src/specify_cli/runtime/resolver.py`" (5 files total, no new file
added — Locality of Change holds throughout) plus 6 existing test files extended (no new test
file). The WP shape is a genuinely sequential chain (WP01's snapshot field → WP02's real
population replacing WP01's stub → WP03's call-site threading → WP04's regression sweep) with no
parallel-lane fan-out to reason about, and no new project/module boundary, contract move, or
migration is introduced (Contract-moves check, Upgrade/migration chain, both plan.md sections
concluded "No"). The functional diff per file is narrow and mechanical (a new `Path | None`
parameter threaded through 6-7 call sites, one new dataclass field + Protocol property, one new
`if ... is None` branch) — this is the shape plan.md itself describes as "tightly bounded," and a
reviewer reading WP01→WP02→WP03→WP04 in commit order sees a single coherent story (stub → real →
wired end-to-end → verified), which is easier to review as one linear diff than as 4 separate PRs
each needing its own context-setting.

**Caveat, surfaced explicitly per the authoring brief's instruction, not decided unilaterally**: 6
test files are extended across the 4 WPs (`test_bridge_cores.py`, `test_pertype_presence_gate.py`,
`test_configured_artifact_name.py`, `test_cli_guard_family.py`, `test_bridge_parity.py` (regression
only, not extended), `test_runtime_bridge_composition.py` (regression only, not extended)) plus a
CHANGELOG/tracer doc edit in WP04 — if the aggregate diff (source + new test assertions) turns out
to exceed what one reviewer can hold in a single sitting once actually written, the operator may
prefer a per-WP PR split instead, given the dependency chain already makes the WPs individually
reviewable as ordered, self-contained diffs (WP01's diff is genuinely small and isolable per its
own Independent Test framing). That decision belongs to the orchestrator/operator, not to this
tasks-authoring pass — this section surfaces the trade-off, it does not resolve it.

---

> Mission-specific content above replaces the template's sample WP01-WP03 shape. Template
> structure preserved so downstream automation (`finalize-tasks`, `mark-status`, ownership
> inference) parses these work packages reliably.
