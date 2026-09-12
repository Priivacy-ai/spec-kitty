---
work_package_id: WP02
title: Org-tier manifest resolution + campsite-clean (folds WP00)
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-010
planning_base_branch: fix/custom-mission-guard-3704
merge_target_branch: fix/custom-mission-guard-3704
branch_strategy: Planning artifacts for this mission were generated on fix/custom-mission-guard-3704. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/custom-mission-guard-3704 unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T009b
- T010
- T010b
- T011
- T012
- T013
- T014
- T015
phase: Phase 2 - Org-tier manifest reach (FR-004/FR-005/FR-007/FR-008) + campsite-clean (WP00 fold)
history:
- timestamp: '2026-08-24T15:45:00Z'
  agent: tasks-author
  action: Prompt authored directly during tasks-phase authoring (spec-kitty agent tasks tasks-outline/tasks-packages do not exist as CLI subcommands in this checkout's v3.2.6rc3 build; authored per tasks.md decomposition of plan.md's WP02, folding plan.md's WP00 per its own binding sequencing).
authoritative_surface: src/specify_cli/runtime/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/runtime/resolver.py
- src/runtime/next/runtime_bridge_io.py
- tests/specify_cli/runtime/test_configured_artifact_name.py
- tests/runtime/next/test_pertype_presence_gate.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP02 – Org-tier manifest resolution + campsite-clean (folds WP00)

## Mission context

Issue #3704 Part 2 (manifest reach). STACKED on `fix/org-tier-expected-artifacts-3703` (PR
#3708) — the org-tier path anchor (`<org_root>/missions/<type>/expected-artifacts.yaml`) this WP
consumes is already merged into this branch's history from that PR; this WP does not
re-implement or re-verify the anchor itself (C-003). Full spec: `../spec.md`. Full plan:
`../plan.md`. This WP implements plan.md's WP02 exactly as scoped there, **and folds plan.md's
WP00** (campsite-clean) per its own binding sequencing — see "Campsite-clean fold" below.

## Goal

Two things, in this order, within this one WP:

1. **Org-tier awareness.** `_presence_filenames_for` (`src/runtime/next/runtime_bridge_io.py:841`)
   currently calls only `MissionTemplateRepository.default()` — built-in tier only. It MUST also
   consult the org tier via `charter.org_expected_artifacts.resolve_org_expected_artifacts`
   (already in this branch's history from #3703/PR #3708) against
   `<org_root>/missions/<mission_type>/expected-artifacts.yaml`, with the same
   last-existing-match-wins / whole-file-replacement precedence that function already implements
   — never field-merged with a built-in manifest. `required_artifacts_for`'s own manifest lookup
   (`_load_expected_artifact_manifest`, `src/specify_cli/runtime/resolver.py:555`) needs the
   identical org-tier awareness (FR-008), otherwise an org-tier custom family would silently fall
   back to "no manifest" one layer below where the presence-gathering fix just landed —
   reintroducing Part 2's exact defect underneath the fix.
2. **Replace WP01's stub with real resolution.** `gather_artifact_presence`
   (`src/runtime/next/runtime_bridge_io.py:931`) currently populates `blocking_artifact_names`
   with WP01's minimal test-only stub. This WP replaces that stub with the real determination:
   reuse the exact same tier-checking `config is None` / org-tier-equivalent logic FR-004 already
   has to run for `_presence_filenames_for` (lines ~891-892) to decide `None` (no manifest at
   either tier) vs. a real `frozenset` (manifest resolved — wrap `required_artifacts_for(step,
   mission_type, repo_root=...)`'s `list[str]` result in `frozenset(...)`).
3. **Close FR-010's org-tier schema-crash risk (ANALYZE-ARCH-001 fix round).** Item 1 above is the
   first change that makes `_load_expected_artifact_manifest`'s
   `ExpectedArtifactManifest.model_validate(...)` call reachable for an org-authored manifest
   (today `resolver.py` has zero org-tier lookup, so this path does not yet exist for org
   manifests). That call has zero exception handling today, for either tier — a schema-invalid
   manifest raises a bare, uncaught `pydantic.ValidationError`. T009b/T010b close this: wrap the
   call and re-raise the existing `ManifestSchemaError` (from `specify_cli.dossier.manifest`) for
   both tiers. Out of scope: the separate, pre-existing built-in/org asymmetry on YAML-*syntax*
   failures (built-in raises `MalformedManifestError`; org degrades silently) — this WP does not
   reconcile that; see spec.md's FR-010 for the corrected record and rationale.

The parameter shape to follow throughout: an optional `repo_root: Path | None = None` parameter,
mirroring `specify_cli.dossier.manifest.ManifestRegistry.load_manifest`'s existing FR-008/WP05
fix (`src/specify_cli/dossier/manifest.py:193-233`) — defaulting to today's built-in-only
behavior for any caller with no root in scope yet (WP03 threads the real value in).

## Campsite-clean fold (charter Standing Order #2, folds plan.md's WP00)

`src/specify_cli/runtime/resolver.py:58-66`'s stale comment currently reads (in substance):
*"Neither has a runtime caller under src/ outside this module until WP04b wires
`required_artifacts_for` into the live per-type presence gate... adding either to `__all__`
before that caller exists reds `tests/architectural/test_no_dead_symbols.py`."* Once T013 below
wires `required_artifacts_for` into `gather_artifact_presence` — its first real cross-module
caller — this comment becomes false. **This WP's own T013 commit is that caller.** T014 restores
`required_artifacts_for` to `resolver.py`'s `__all__` (lines 46-57) and fixes the stale comment,
**landing as the commit immediately AFTER T013's functional commit (or combined into the same
commit) — never before it.** Landing T014 any earlier would add `required_artifacts_for` to
`__all__` with zero callers still existing at that commit and red
`tests/architectural/test_no_dead_symbols.py` — the exact failure the stale comment itself warns
about (this exact ordering mistake was found and fixed at the plan phase: PLAN-GOV-001,
`../reviews/plan.confirmed.yaml`; do not reintroduce it).

## Independent Test

Stand up an org pack at `<org_root>/missions/<type>/expected-artifacts.yaml` (the conventional
layout, reachable now that this branch is stacked on #3708's path fix) with a mix of
`blocking: true` / `blocking: false` entries across two steps, and a built-in manifest for the
same family (or none) as a control. Assert:
- The org file wins whole-file (never merged) — AC-6.
- Only `blocking: true` absences produce guard failures (via `blocking_artifact_names`) — AC-4.
- A `blocking: false` absence never does, at every step it's declared for — AC-5.

## Requirement Refs

FR-004, FR-005, FR-006 (real population — the field/Protocol/branch itself is WP01's), FR-007,
FR-008, FR-010, AC-4, AC-5, AC-6, C-002

## Subtasks

**T008 [ATDD-RED — separate commit BEFORE any implementation commit]** Add org-tier test cases to
`tests/specify_cli/runtime/test_configured_artifact_name.py`, mirroring
`ManifestRegistry.load_manifest`'s existing FR-008/WP05 test shape
(`src/specify_cli/dossier/manifest.py:193-233` and its own test file for the pattern to mirror):
exercise `_load_expected_artifact_manifest`/`required_artifacts_for` with `repo_root` pointing at
a directory containing an org pack, asserting the org manifest is the one resolved. **Also add a
named fallback case (TASKS-VERIFY-003 fix, this fix round):** `repo_root` set to a real temp
directory with NO `missions/<type>/expected-artifacts.yaml` under it, and a built-in manifest
present for the family — assert `required_artifacts_for`/`_load_expected_artifact_manifest`
resolve to the built-in manifest's artifacts, unchanged from the `repo_root=None` case (proves the
org-tier consult's "no match" path falls through cleanly at the resolver.py layer rather than
masking or erroring past the built-in result). Verify RED against
`fix/org-tier-expected-artifacts-3703` before writing implementation code:

```bash
git fetch origin fix/org-tier-expected-artifacts-3703
uv run pytest tests/specify_cli/runtime/test_configured_artifact_name.py -v   # baseline first
```

**T009 [ATDD-RED — same commit family as T008, before implementation]** Add AC-4/AC-5/AC-6
org-tier + whole-file-replacement scenarios to `tests/runtime/next/test_pertype_presence_gate.py`:
org manifest with mixed `blocking: true`/`blocking: false` entries across two steps, a built-in
manifest for the same family present as a control, asserting the org file wins whole-file and
only `blocking: true` absences surface. **Also add a named fallback case (TASKS-VERIFY-003 fix,
this fix round):** `repo_root` set to a real temp directory with NO
`missions/<type>/expected-artifacts.yaml` under it, and a built-in manifest present for the
family — assert `_presence_filenames_for`/`gather_artifact_presence`'s resulting
`blocking_artifact_names` still reflect the built-in manifest's blocking artifacts, unchanged from
the `repo_root=None` case. This is the specific new branch introduced by T012/T013
(`runtime_bridge_io.py:841-891` and `:931`): `repo_root` supplied but no org pack found at it,
proving the org-tier consult's "no match" path falls through cleanly to the built-in-tier manifest
rather than raising or silently dropping the built-in result — distinct from the
`repo_root=None`-never-invokes-org-tier-at-all case already covered by regression. Verify RED
against `fix/org-tier-expected-artifacts-3703`.

**T009b [ATDD-RED — same commit family as T008/T009, before implementation; ANALYZE-ARCH-001 fix
round]** Add schema-invalid-manifest test cases to
`tests/specify_cli/runtime/test_configured_artifact_name.py`: a built-in manifest that parses as
YAML but fails `ExpectedArtifactManifest`'s Pydantic schema (`extra="forbid"`), and an org-tier
manifest with the same defect, each asserting `_load_expected_artifact_manifest`/
`required_artifacts_for` raise `ManifestSchemaError` — not a bare `pydantic.ValidationError` —
for both tiers. This is FR-010's actual contract: today `_load_expected_artifact_manifest` calls
`ExpectedArtifactManifest.model_validate(...)` with zero exception handling (verified against live
source), so this test is genuinely RED before T010b lands. **For the org-tier case specifically
(ANALYZE-FRESH-001 fix), also assert on the raised `ManifestSchemaError.origin` value: it must be
a non-empty descriptive string naming the org tier and the mission type (mirroring
`ManifestRegistry.load_manifest`'s synthesized org-tier origin, `manifest.py:283-291`) — never the
built-in branch's `config.origin` expression, which is unreachable in the org-tier branch and
would raise `AttributeError` there if used by mistake.** This origin assertion is what actually
pins T010b's corrected per-branch origin derivation, not just the exception type. Verify RED
against `fix/org-tier-expected-artifacts-3703` before writing implementation code.

**T010** `_load_expected_artifact_manifest` (`src/specify_cli/runtime/resolver.py:555`) gains
`repo_root: Path | None = None`, becomes org-aware via `resolve_org_expected_artifacts` (FR-008),
mirroring `ManifestRegistry.load_manifest`'s parameter shape exactly
(`src/specify_cli/dossier/manifest.py:193-233`). **Correction (ANALYZE-ARCH-001 fix round):** this
subtask's prior text claimed the docstring's "schema-invalid manifests raise `ManifestSchemaError`
loudly per #3542's precedent" contract already held here — that was false: this function calls
`ExpectedArtifactManifest.model_validate(...)` with zero exception handling, so a schema-invalid
manifest raises a bare `pydantic.ValidationError`, uncaught. T010b (below) is the subtask that
actually makes the docstring's claim true; do not assume it is already satisfied when landing
T010's org-tier-awareness change.

**T010b [ANALYZE-ARCH-001 fix round; org-tier origin corrected per ANALYZE-FRESH-001]**
`_load_expected_artifact_manifest` wraps EACH tier's `ExpectedArtifactManifest.model_validate(...)`
call in its own `try/except pydantic.ValidationError`, re-raising the existing `ManifestSchemaError`
— imported from `specify_cli.dossier.manifest` — with a **branch-specific `origin` argument**,
mirroring `ManifestRegistry.load_manifest`'s own TWO DIFFERENT origin expressions per branch
(`src/specify_cli/dossier/manifest.py:274-340`), not one shared expression used for both:

- **Built-in branch** (`config = MissionTemplateRepository.default().get_expected_artifacts(mission_type)`,
  a `ConfigResult`): `raise ManifestSchemaError(mission_type, config.origin) from exc` —
  `config.origin` is a real attribute here, exactly mirroring `manifest.py:326-340`'s built-in
  except-block.
- **Org-tier branch** (`org_parsed = resolve_org_expected_artifacts(org_roots, mission_type)`, a
  bare `Mapping[str, Any] | None` with **no `.origin` attribute**): synthesize a descriptive origin
  string naming the mission type and the org roots checked, exactly as `ManifestRegistry
  .load_manifest`'s org-tier except-block does (`manifest.py:283-291`), e.g.:
  ```python
  origin = (
      f"org-tier expected-artifacts.yaml for mission type {mission_type!r} "
      f"(no single source file path available; checked org roots: "
      f"{', '.join(str(root) for root in org_roots)})"
  )
  raise ManifestSchemaError(mission_type, origin) from exc
  ```

**Do NOT reuse `config.origin` for the org-tier branch** — in that branch there is no `config`
variable of type `ConfigResult` in scope; reading `.origin` off the org-tier mapping/`org_parsed`
raises `AttributeError`, not `ManifestSchemaError`, defeating this fix on exactly the org-tier path
FR-010 exists to cover (ANALYZE-FRESH-001). **Do NOT paper over that `AttributeError` risk with a
broad `except Exception` wrapped around the org-tier branch either** — that would silently swallow
genuine schema errors instead of surfacing `ManifestSchemaError`, reintroducing the exact
silent-failure hazard this fix round exists to close. This import crosses `specify_cli.runtime` →
`specify_cli.dossier`, the same sibling-package seam `specify_cli.sync.namespace` and
`specify_cli.sync.dossier_pipeline` already cross for this exact type; no architectural boundary
gate forbids it (checked against `tests/architectural/test_runtime_charter_doctrine_boundary.py`
and `tests/architectural/test_dossier_sync_boundary.py` — neither covers `runtime`→`dossier`).
Lands in the same commit as T010 (or immediately after it, before T011). Makes T009b GREEN
(including its org-tier `.origin` assertion). Closes the crash risk FR-010 exists to address:
today `resolver.py` has zero org-tier lookup, so this exact uncaught-`ValidationError` path does
not yet exist for org manifests — T010 is what makes it reachable, so T010b must land no later
than T010 for FR-010 to genuinely hold once WP02 is done.

**T011** `required_artifacts_for` (`src/specify_cli/runtime/resolver.py:634`) gains
`repo_root: Path | None = None`, forwards it to `_load_expected_artifact_manifest`. Its own return
contract stays `list[str]` — the `frozenset(...)` wrap happens at the `gather_artifact_presence`
call site (T013), not here, so `tests/specify_cli/runtime/test_configured_artifact_name.py`'s
existing unit-tested contract for this function stays intact.

**T012** `_presence_filenames_for` (`src/runtime/next/runtime_bridge_io.py:841`) gains
`repo_root: Path | None = None`; also consults org tier via `resolve_org_expected_artifacts`
against `<org_root>/missions/<mission_type>/expected-artifacts.yaml`, same
last-existing-match-wins / whole-file-replacement precedence that function already implements.
**Stays family-scoped, NOT step-scoped** (FR-005/C-002 — a prior attempt at step-scoping was
reverted after it red `test_coverage_floor_is_met` by spuriously blocking software-dev's composed
`tasks` guard and `plan`'s `specify`/`plan` guards; do not re-attempt it here). Continue unioning
`required_always` + every `required_by_step` list + `optional_always` across the whole family,
exactly as today, just now from whichever tier (org or built-in) actually resolves.

**T013 [functional commit]** `gather_artifact_presence` (`src/runtime/next/runtime_bridge_io.py:931`)
gains `repo_root: Path | None = None`, forwards it to `_presence_filenames_for` and
`required_artifacts_for`. Replace WP01's test-only stub with the real resolution: reuse the exact
same tier-checking `config is None` / org-tier-equivalent logic already run for
`_presence_filenames_for` (lines ~891-892) to determine reachability ONCE per call — set
`blocking_artifact_names` to `None` only when that check finds no manifest at either tier;
otherwise wrap `required_artifacts_for(step, mission_type, repo_root=repo_root)`'s `list[str]`
result in `frozenset(...)`, including the degenerate `frozenset()` case (manifest resolved,
nothing blocking at this step — a genuine pass, never a stand-in for "no manifest"). **This
determination happens ONCE per `gather_artifact_presence` call and is the single source for the
field's `None` state — never re-derived or inferred elsewhere** (never inferred from an empty
list, which would silently reopen the exact collapse this mission fixes — see plan.md's
"SPEC-FRESH-001 preservation" section). **This commit gives `required_artifacts_for` its first
real cross-module caller under `src/`** — T014 depends on this being true.

**T014 [campsite-clean commit, folds WP00 — lands immediately AFTER T013's functional commit, or
combined with it; NEVER before it]** Restore `required_artifacts_for` to `resolver.py`'s
`__all__` (currently excluded, lines 46-57) alongside the caller T013 just added. Update or
remove the stale comment at lines 58-66 so it reflects the real wiring that now exists (it
currently claims "no runtime caller under src/ outside this module until WP04b" — that claim is
now false). Do not land this commit, or any part of it, before T013's commit exists — see
"Campsite-clean fold" above for why.

**T015** Run this WP's full regression scope; confirm T008/T009/T009b go GREEN; confirm
`tests/architectural/test_no_dead_symbols.py` stays GREEN (this is the mechanical proof that T014
landed in the correct order relative to T013 — it would RED if `required_artifacts_for` were in
`__all__` with no caller); budget test coverage for T012/T013's new/changed lines in
`src/runtime/next/runtime_bridge_io.py` toward the enforced 90% diff-coverage floor. T010/T010b/T011's
`resolver.py` changes are NOT in `critical_paths` (they fall to the advisory full-diff step
only, per Gate set in `../tasks.md`) — write thorough tests for them per ATDD-first discipline
regardless, just note this file is not enforcement-gated the same way:

```bash
uv run pytest tests/specify_cli/runtime/test_configured_artifact_name.py -v
uv run pytest tests/runtime/next/test_pertype_presence_gate.py -v
uv run pytest tests/architectural/test_no_dead_symbols.py -v
uv run pytest tests/architectural/test_bridge_cores_import_boundary.py -v
uv run pytest tests/runtime/test_bridge_parity.py -v
uv run pytest tests/runtime/next/test_cli_guard_family.py -v
uv run pytest tests/specify_cli/next/test_runtime_bridge_composition.py -v
```

## Gates that apply to this WP's files

**ENFORCED**: commitlint; doctrine schema freshness (trivial pass); Contextive glossary (trivial
pass); TID251; `patch()` target validation (T008/T009/T009b's new tests will patch
`resolve_org_expected_artifacts`/`required_artifacts_for` — every patch target must resolve to a
real importable path); Bandit; pip-audit; `uv.lock` freshness; **`diff-coverage` 90% floor on
`src/runtime/next/*`** — applies to T012/T013 (`runtime_bridge_io.py`). `src/specify_cli/runtime/resolver.py`
(T010/T010b/T011) is exempt from this specific enforced job, falling to the advisory full-diff step.

**ADVISORY-ONLY**: `ruff`, `mypy` — run `make lint` locally; this WP adds several
`repo_root: Path | None = None` parameters worth type-checking.

## Dependencies

- Depends on WP01. (WP01's `blocking_artifact_names is None` branch and Protocol property must
  exist before this WP's real population has anything to feed.)

## Risks

- Landing T014 before T013 → reds `test_no_dead_symbols.py`. Mitigated by T015's explicit
  verification step and this file's repeated ordering warning.
- Reintroducing step-scoped gathering while adding org-tier awareness. Mitigated by T012's
  explicit "stays family-scoped, NOT step-scoped" instruction and C-002's citation.
- Landing T010 (org-tier awareness) without T010b (schema-error handling) would make T010's own
  change the origin of a new, silent org-tier crash risk (ANALYZE-ARCH-001). Mitigated by T009b's
  RED test failing until T010b lands, and by this file's explicit "T010b must land no later than
  T010" note in T010b's own text.
