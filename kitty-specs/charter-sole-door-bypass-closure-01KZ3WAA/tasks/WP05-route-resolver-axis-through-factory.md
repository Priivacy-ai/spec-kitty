---
work_package_id: WP05
title: Consolidate the template/command resolver axis onto the factory
dependencies:
- WP01
requirement_refs:
- FR-003
planning_base_branch: feat/charter-sole-door-bypass-closure
merge_target_branch: feat/charter-sole-door-bypass-closure
branch_strategy: Planning artifacts for this mission were generated on feat/charter-sole-door-bypass-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/charter-sole-door-bypass-closure unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
phase: Phase 2 - Bypass closure
history:
- at: '2026-08-03T14:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
- at: '2026-08-03T15:00:00Z'
  actor: system
  action: Post-tasks squad correction - the original framing ("stops importing doctrine.resolver directly") was factually wrong; specify_cli/runtime/resolver.py never imported doctrine.resolver — it imports the charter.resolution facade and charter.activation.template_resolver, both already legitimately inside src/charter/** (debugger-debbie finding). Reframed as an entry-point consolidation. Fixed a method-naming collision risk (debugger-debbie finding).
agent_profile: architect-alphonso
authoritative_surface: src/charter/activation/template_resolver.py
create_intent:
- tests/charter/test_resolver_tier_axis_via_factory.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/activation/template_resolver.py
- src/specify_cli/runtime/resolver.py
- tests/charter/test_resolver_tier_axis_via_factory.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP05 – Consolidate the template/command resolver axis onto the factory

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `architect-alphonso` (implementer role, claude agent) before
parsing the rest of this prompt — this WP is a structural seam change, not a mechanical swap.

---

## ⚠️ IMPORTANT: Review Feedback

Check `review_ref` in the event log before starting. Address all feedback; log changes in the Activity Log.

---

## Objectives & Success Criteria

**Reframed by the post-tasks squad — the original premise was wrong.** This is NOT about removing a
`doctrine.resolver` import from outside `src/charter/**` — there isn't one. Every current importer of
`doctrine.resolver` (`charter/template_resolver.py`, `charter/resolution.py`,
`charter/context_renderers/template_include.py`, `doctrine/template_catalog.py`) is already legitimately
inside `src/charter/**` or `src/doctrine/**`, where `charter → doctrine` is the sanctioned direction. The
real problem is a **two-doors-within-charter** seam: `charter.activation.template_resolver.CharterTemplateResolver`
is a *second* charter-layer object separate from `charter.activation.resolver.DoctrineService` (the factory), each
reaching `doctrine/resolver.py` independently. FR-003 closes this by consolidating the 5-tier
template/command resolution entry point onto the factory — one charter-layer door, not two.

**This WP's scope was corrected by the post-plan squad (still true, unaffected by the reframe above):**
- `src/charter/resolution.py` and `src/charter/activation/context_renderers/template_include.py` are **NOT** in scope —
  both import only the `ResolutionResult`/`ResolutionTier` *types*, sanctioned by an existing facade
  contract, not resolution calls. Do not touch them.
- `doctrine.template_catalog.resolve_template_by_id` (5 importers) and `specify_cli/runtime/resolver.py`'s
  own tier-1-4 reimplementation are explicitly **deferred debt**, named but out of this WP's blast radius.
- `doctrine/resolver.py`'s tier functions (`_resolve_asset`, `resolve_mission`) **stay where they are**.

## Context & Constraints

- Read `research.md`'s R6 finding in full — it names the exact precedent
  (`specify_cli/runtime/resolver.py`'s existing tier-5 routing pattern) to extend, and the exact things to
  leave alone.
- **Real design work required**: `CharterTemplateResolver`'s one real caller currently uses a cached
  (`lru_cache`), `missions_root`-keyed construction (`from_missions_root(...)`); the factory is built from
  `repo_root` via the unified builder (WP01). T019 resolves this mismatch explicitly.
- **Naming collision to avoid** (post-tasks squad finding): `CharterTemplateResolver` already has methods
  named `resolve_command_template` (`template_resolver.py:52`) and `resolve_content_template` (`:90`) with
  DIFFERENT signatures than what T018 will add to the factory. Do NOT reuse these exact names for the new
  factory methods while both objects coexist (even transiently, before T020 retires/shims the old class) —
  pick distinct names (e.g. `resolve_command_asset`, `resolve_content_asset`, `resolve_mission_definition`)
  so a reader is never unsure which signature applies where.
- **Depends on WP01** (declared in frontmatter) — not just for the unified builder, but because T018 adds
  methods to `src/charter/activation/resolver.py`, which WP01 exclusively owns and edits first. `src/charter/activation/resolver.py`
  is **not** in this WP's `owned_files` — T018's edit there is a small, explicitly sequenced out-of-map
  addition, safe because the dependency on WP01 guarantees this WP never runs in parallel with it.

## Branch Strategy

- **Strategy**: lane-per-WP (normalized by `finalize-tasks`)
- **Planning base branch**: feat/charter-sole-door-bypass-closure
- **Merge target branch**: feat/charter-sole-door-bypass-closure

## Subtasks & Detailed Guidance

### Subtask T018 – Add resolution methods to `charter.activation.resolver.DoctrineService`

- **Purpose**: Give the factory a public surface for the 5-tier axis, under NEW names distinct from
  `CharterTemplateResolver`'s existing methods (see the naming-collision note above).
- **Steps**:
  1. Read `doctrine/resolver.py::_resolve_asset` (5 tiers) and `resolve_mission` (4 duplicated tiers) and
     `CharterTemplateResolver`'s current method signatures — understand the shape, but do NOT reuse its
     exact method names.
  2. Add methods with distinct names (e.g. `resolve_command_asset`, `resolve_content_asset`,
     `resolve_mission_definition`) to `charter.activation.resolver.DoctrineService` that call into `doctrine.resolver`'s
     functions internally.
  3. These new methods are explicitly **ungated** by design (the 5-tier axis has no activation concept
     today) — do not add activation filtering here; that would conflate FR-003 with FR-005's separate scope.
     Note this explicitly in a docstring/comment on the new methods.
- **Files**: `src/charter/activation/resolver.py` (out-of-map edit, sequenced after WP01 via the declared dependency).
- **Parallel?**: No — T020 depends on this.

### Subtask T019 – Resolve the construction-contract mismatch

- **Purpose**: `_charter_template_resolver_for()` in `runtime/resolver.py` is `lru_cache`d and keyed on a
  `missions_root` string; `charter.activation.resolver.DoctrineService` needs a `repo_root`. Design the mapping now.
- **Steps**: Either (a) resolve `repo_root` at the same call site `missions_root` is currently resolved from
  (check what upstream context is available there), or (b) add a `repo_root`-equivalent construction path.
  Document the chosen mapping in a comment at the call site.
- **Files**: `src/specify_cli/runtime/resolver.py`.
- **Parallel?**: No — depends on T018's method shapes being settled.

### Subtask T020 – Retarget `CharterTemplateResolver`

- **Purpose**: Consolidate onto one charter-layer door.
- **Steps**: Either turn `CharterTemplateResolver` into a thin delegating shim to T018's new factory methods
  (translating its old method names/signatures to the new ones), or retire it entirely and have
  `_charter_template_resolver_for()` construct `charter.activation.resolver.DoctrineService` directly (per T019's
  resolved mapping) and call the new methods. Pick whichever is the smaller diff given T019's actual design;
  state which you picked and why in the Activity Log.
- **Files**: `src/charter/activation/template_resolver.py`, `src/specify_cli/runtime/resolver.py`.
- **Parallel?**: No — depends on T018, T019.

### Subtask T021 – Regression test: tier resolution unchanged

- **Purpose**: Prove the consolidation didn't change resolution behaviour.
- **Steps**: For each of the 5 tiers (OVERRIDE, LEGACY, GLOBAL_MISSION, GLOBAL, PACKAGE_DEFAULT), assert the
  factory-routed resolution returns the identical result the old `CharterTemplateResolver` call would have,
  on the same fixture project.
- **Files**: `tests/charter/test_resolver_tier_axis_via_factory.py` (new).
- **Parallel?**: No — depends on T020.

## Test Strategy

- `pytest tests/charter/ tests/specify_cli/runtime/ -v`.
- `mypy --strict src/charter/activation/resolver.py src/charter/activation/template_resolver.py src/specify_cli/runtime/resolver.py`.

## Risks & Mitigations

- **Moving `doctrine/resolver.py`'s tier functions instead of adding an entry point.** Explicitly forbidden —
  the tier functions stay put.
- **Reusing `CharterTemplateResolver`'s exact method names for the new factory methods.** This is the
  naming-collision risk named above — pick distinct names.
- **Silently pulling in `template_catalog` or `runtime/resolver.py`'s tier-1-4 reimplementation.** Stop and
  report if T019/T020 seem to require touching either — that's scope creep beyond this WP's boundary.

## Review Guidance

- Confirm the new factory methods use names distinct from `CharterTemplateResolver`'s existing ones.
- Confirm `doctrine/resolver.py` itself is untouched (diff should show zero changes to that file).
- Confirm T019's chosen mapping is documented, not silently invented.
- Confirm the PR description does NOT claim this WP removed a `doctrine.resolver` import bypass from
  outside `src/charter/**` — there wasn't one; the claim is entry-point consolidation.

## Activity Log

- 2026-08-03T14:10:00Z – system – Prompt created.
- 2026-08-03T15:00:00Z – system – Post-tasks squad: corrected premise and naming-collision risk.
- 2026-08-03T18:59:50Z – claude – shell_pid=4174443 – T020 architectural decision — THIN DELEGATE, not retire-and-repoint. Rationale: (1) CharterTemplateResolver is public charter API (charter/__init__.py:90 exports it), so retiring it is an unauthorised breaking change plus an out-of-map edit to charter/__init__.py and the deletion of tests/charter/test_template_resolver.py; (2) this mission's OWN precedent for the identical C-001 situation is delegation, not deletion — WP01 turned specify_cli.doctrine_service_factory.build_activation_aware_doctrine_service into a thin re-export rather than removing it; (3) 'one canonical authority' is satisfied because the delegate now has NO independent path to doctrine.resolver (that import is gone from template_resolver.py entirely) and its one production caller, specify_cli/runtime/resolver.py, no longer touches it at all — it calls the factory directly, so the production path has exactly one door. T019 decision — the missions_root->repo_root mismatch is DISSOLVED, not mapped: the new factory methods are @staticmethods taking missions_root/project_dir as arguments, because the 5-tier axis is ungated by design and reads zero instance state. Rejected T019 option (a) (build the activation-aware factory from the project_dir already threaded through _resolve_asset) because it would couple pure-filesystem tier-5 lookup to charter governance-config loading (PackContext.from_config + resolve_org_roots + infer_repo_languages) whose result the methods provably never read, and would newly make template resolution fail-closed on a malformed .kittify/config.yaml. Documented at the call site (_package_default_path docstring) as required. Scope note: CharterTemplateResolver.resolve_*_path stay on MissionTemplateRepository deliberately — they are package-default repository lookups, not doctrine.resolver tier-chain calls, so they are not the FR-003 seam and add no second authority.
