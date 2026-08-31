---
work_package_id: WP05
title: Org-tier expected-artifacts.yaml override
dependencies:
- WP04
requirement_refs:
- C-003
- FR-008
- NFR-001
- NFR-002
- NFR-003
planning_base_branch: pr/up-org-doctrine-consumers-01M05YAB
merge_target_branch: pr/up-org-doctrine-consumers-01M05YAB
branch_strategy: Planning artifacts for this mission were generated on pr/up-org-doctrine-consumers-01M05YAB. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/up-org-doctrine-consumers-01M05YAB unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
- T026
- T027
history:
- at: '2026-08-16T19:20:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- src/charter/org_expected_artifacts.py
- tests/charter/test_org_expected_artifacts.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/charter/org_expected_artifacts.py
- src/charter/mission_type_profiles.py
- src/specify_cli/dossier/manifest.py
- tests/charter/test_mission_type_profiles.py
- tests/charter/test_org_expected_artifacts.py
- tests/dossier/test_manifest.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP05 – Org-tier expected-artifacts.yaml override

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

## ⚠️ File-collision note (why this WP depends on WP04)

**This WP depends on WP04 purely because both edit `src/charter/mission_type_profiles.py` (and
its test module) — a file collision, not a functional dependency.** FR-008 (this WP) does not
need anything FR-004 (WP04) implements; it only needs `resolve_org_dirs` from WP01, which WP04
does not gate. The dependency exists so `owned_files` stays non-overlapping between two
otherwise-concurrent packages — the finalizer exempts dependency-ordered pairs from its overlap
check. **Do not "optimise" this into parallel execution with WP04.** If your worktree's merge
base does not yet include WP04's `_mission_type_profile_repository` change, that is expected —
your edits are in a different function (`_resolve_expected_artifacts_slot`) in the same file.

> **Tooling note**: this WP's frontmatter `requirement_refs` cannot list `SC-005` —
> `spec-kitty agent tasks map-requirements` only accepts `FR-`/`NFR-`/`C-` prefixed refs
> (confirmed live during this mission's task generation), not `SC-`. SC-005 fully applies to
> this WP (see T026/T027 below) despite being absent from the structured field.

## Objective

`MissionTemplateRepository` and `ManifestRegistry` have **no org-tier or project-tier mechanism
of any kind** today — unlike every other consumer in this mission, this is genuinely new
surface, not caller-side parameter threading (see spec.md D-000(3)). This WP:

1. Adds a new shared helper, `resolve_org_expected_artifacts`, that checks each configured org
   root for `<org_root>/<mission_type>/expected-artifacts.yaml`.
2. Wires it into `_resolve_expected_artifacts_slot` (`mission_type_profiles.py`).
3. Wires it into `ManifestRegistry.load_manifest` (`specify_cli/dossier/manifest.py`) —
   **and fixes a real, self-identified cache-key defect while doing so** (see the dedicated
   section below; this is explicit, budgeted scope for this WP, not optional cleanup).

**This is the largest package in the mission** (~90-130 production LOC, ~90-120 test LOC per
plan.md's own estimate — the plan's overall sizing assessment (`plan.md` "Sizing Assessment")
puts this mission at the **upper end** of its L-size range specifically because of this WP's
cache-key fix). Budget your time accordingly; do not compress T023/T024 to "just make the
happy path work" — the cache-key correctness is the part most likely to hide a real bug if
rushed.

## Context

### Dependency: WP01's `resolve_org_dirs` — NOT what this WP's new helper takes as input

Unlike WP02/WP03/WP04, this WP's new helper does **not** call `resolve_org_dirs` directly.
Per contract C-4, `resolve_org_expected_artifacts` takes `org_roots: list[Path]` — **raw org
roots**, not the `resolve_org_dirs`-style subdir-joined output — because `mission_type` varies
per call and cannot be baked into a fixed `subdir` string the way `"mission_step_contracts"` or
`"mission_types"` can. Both of this WP's two callers are responsible for passing their own
existence-filtered org roots (e.g. via `resolve_org_roots(repo_root)` directly, filtered to
`.exists()`) — **not** `resolve_org_dirs(repo_root, "expected_artifacts")`, which would produce
the wrong shape entirely (a fixed-subdir join, when what's needed is a per-mission-type join
your new helper does itself).

### Constraint C-003 — what you must NOT do to `MissionTemplateRepository`

`MissionTemplateRepository` (`doctrine/missions/repository.py:122-135`) is **not** a
`BaseDoctrineRepository` subclass — it is a bespoke single-root reader
(`__init__(self, missions_root: Path)`, `.default()` always points at the built-in tree). C-003
is explicit: do not restructure it into a `BaseDoctrineRepository` subclass, do not add a new
`ArtifactKind` for mission-scoped assets, and — read literally — do not add **any** new method
to the class either (not just "don't restructure existing methods"). Your org-file check must
live **beside** the class in a new module, calling
`MissionTemplateRepository.default().get_expected_artifacts(mission_type)` only as the
built-in-tier fallback when your new helper returns `None`.

### Contract C-4 — the shared helper's binding shape

```python
def resolve_org_expected_artifacts(
    org_roots: list[Path], mission_type: str
) -> Mapping[str, object] | None:
    """<org_root>/<mission_type>/expected-artifacts.yaml, later org_roots override earlier."""
```

- **Location**: new module `src/charter/org_expected_artifacts.py`.
- **Precedence within `org_roots`**: **last-existing-match wins** — the more common
  `org_dirs`-style later-wins convention (NFR-003), **not** first-match. This is deliberately
  different from FR-002's DRG `org_root` resolution (which is first-match, an inherited C-004
  limitation) — FR-008 is new surface with no pre-existing first-match precedent to inherit, so
  it follows the more common convention instead. Do not copy FR-002's first-match pattern here.
- **Precedence vs. built-in**: whole-file replacement, not field-merge. When an org file
  resolves, the built-in file is not read at all for that mission type (SC-005 Given #3).
- **No built-in baseline required**: a wholly org-defined custom mission type (no built-in
  `expected-artifacts.yaml` at all) is valid — the org file is authoritative with no fallback
  needed.

### The `ManifestRegistry` cache-key defect — explicit, budgeted scope for this WP

This is a **real defect this mission's own plan.md investigation found**, not named by FR-008's
spec text, but explicitly called out as required scope (see plan.md's IC-05 Risks section and
Stated Assumption #1). **Do not skip this.**

`ManifestRegistry` (`specify_cli/dossier/manifest.py:164-214`) is a `@staticmethod`-only class
with a **process-global** cache:

```python
class ManifestRegistry:
    _cache: dict[str, ExpectedArtifactManifest | None] = {}

    @staticmethod
    def load_manifest(mission_type: str) -> ExpectedArtifactManifest | None:
        if mission_type in ManifestRegistry._cache:
            return ManifestRegistry._cache[mission_type]
        config = _doctrine_repository().get_expected_artifacts(mission_type)
        ...
        ManifestRegistry._cache[mission_type] = manifest
        ...
```

The cache is keyed **only** on `mission_type`. Its **sole production caller**,
`resolve_manifest_version(mission_type: str)` in `specify_cli/sync/namespace.py:90-98`, has
**no `repo_root` in scope at all**. If `load_manifest` gains org-tier resolution keyed only on
`mission_type`, the **first** call to resolve a given `mission_type` in a long-lived process
(a daemon, or a long test session touching two different projects with different org
overrides) permanently caches that project's result for every later call in that process —
project B's request for `"software-dev"` silently gets project A's org override (or lack
thereof). This is exactly the "silent success... reports success while measuring nothing"
failure class this repo's own charter names as its worst-severity class (SPEC-KITTY-LEDGER.md
SK-04), and NFR-002 forbids it explicitly for this mission's fix sites — this cache is a new
instance of the same shape, self-identified by this mission's plan.md, not a pre-existing issue
you get to leave alone.

**Required fix shape** (plan.md's recommendation, binding for this WP):

```python
@staticmethod
def load_manifest(
    mission_type: str, repo_root: Path | None = None
) -> ExpectedArtifactManifest | None:
    org_roots = tuple(sorted(str(p) for p in _resolve_existing_org_roots(repo_root))) if repo_root else ()
    cache_key = (mission_type, org_roots)
    if cache_key in ManifestRegistry._cache:
        return ManifestRegistry._cache[cache_key]
    ...
```

- `repo_root: Path | None = None` — **optional**, defaulting to today's behavior.
- Cache key becomes `(mission_type, tuple_of_resolved_existing_org_roots)` — an **empty tuple**
  when `repo_root is None` (today's call shape) or when no org pack is configured/exists for
  that `repo_root`.
- `_cache`'s type annotation changes from `dict[str, ExpectedArtifactManifest | None]` to
  `dict[tuple[str, tuple[str, ...]], ExpectedArtifactManifest | None]` — update it, and check
  `ManifestRegistry.clear_cache` (line ~305-310) still works unchanged (it just calls
  `._cache.clear()`, which is key-shape-agnostic — should need no change, but verify).
- `resolve_manifest_version` in `specify_cli/sync/namespace.py` is **not** changed by this
  mission (out of scope — it has no `repo_root` to pass, and retrofitting every existing caller
  is not required by FR-008; only "a caller that has `repo_root` can see the override").
  Confirm it still compiles and behaves identically by calling `load_manifest(mission_type)`
  with no second argument, which resolves to `repo_root=None` → empty-tuple cache key → today's
  exact behavior (this is what makes SC-005 Given #2's byte-identical requirement provable).

## Subtasks

### T021 — Implement `resolve_org_expected_artifacts` (new module)

Create `src/charter/org_expected_artifacts.py` implementing the C-4 contract exactly:
last-existing-match-wins precedence over `org_roots`, whole-file read (parse the YAML mapping,
no merging), returns `None` when no org root has a matching file for `mission_type`. Use
`ruamel.yaml` to parse, matching `MissionTemplateRepository`'s existing parsing approach (check
`doctrine/missions/repository.py` for the exact parser setup it uses and match it, for
consistency — do not introduce a second YAML-parsing convention).

### T022 — Wire the helper into `_resolve_expected_artifacts_slot`

Current code (`mission_type_profiles.py:971-996`):

```python
def _resolve_expected_artifacts_slot(
    mission_type: str,
    *,
    is_registered: bool,
) -> _ExpectedArtifactsManifest | None:
    if not is_registered:
        return None
    from doctrine.missions.repository import MissionTemplateRepository
    repo = MissionTemplateRepository.default()
    result = repo.get_expected_artifacts(mission_type)
    if result is None:
        return None
    parsed = result.parsed
    if not isinstance(parsed, Mapping):
        return None
    return parsed
```

This function currently has **no `repo_root` parameter at all** — check its caller (around
line 682, `_expected_artifacts_thunk=lambda: _resolve_expected_artifacts_slot(...)`) to see
whether `repo_root` is available in that closure's scope (it should be, since
`resolve_mission_type_context` itself requires `repo_root`) and thread it through as a new
parameter. Call `resolve_org_expected_artifacts(org_roots, mission_type)` first (with
`org_roots` = existence-filtered `resolve_org_roots(repo_root)`, per this WP's Context section
above on why it's raw roots, not `resolve_org_dirs`'s joined output); fall back to the existing
`MissionTemplateRepository.default()` read only when the org helper returns `None`. Update the
function's signature and every call site consistently — search for all callers of
`_resolve_expected_artifacts_slot` before assuming there is only the one at line 682.

### T023 — `ManifestRegistry.load_manifest` cache-key fix

Implement exactly the shape described in the Context section above:
`repo_root: Path | None = None` parameter, cache key becomes `(mission_type, tuple(sorted org
roots))`. Update the `_cache` type annotation. Do not change `resolve_manifest_version`'s call
site in `specify_cli/sync/namespace.py`.

### T024 — Wire the org-file check into `load_manifest`

When `repo_root` is provided and resolves to 1+ existing org roots, call
`resolve_org_expected_artifacts(org_roots, mission_type)` before falling back to the existing
`_doctrine_repository().get_expected_artifacts(mission_type)` built-in read. Preserve the
existing `ExpectedArtifactManifest.model_validate(...)` adaptation step and existing logging
(`logger.debug`/`logger.info`/`logger.error` calls) — only the source of the raw parsed mapping
changes, not the validation/caching/logging structure around it.

### T025 — Unit tests for `resolve_org_expected_artifacts`

New file `tests/charter/test_org_expected_artifacts.py`:

- No org roots (or none with a matching file) → `None`.
- One org root with `<root>/<mission_type>/expected-artifacts.yaml` → parsed mapping returned.
- Two org roots both with the file → **later** root's content wins (NFR-003-style
  declared-order precedence — confirm this is last-wins, the opposite of FR-002's first-match).
- A `mission_type` with no built-in baseline at all (a wholly org-defined custom type) — helper
  still returns the org file's content; no dependency on a built-in file existing.

### T026 — Integration tests: `_resolve_expected_artifacts_slot` org override (SC-005)

In `tests/charter/test_mission_type_profiles.py`:

- Configure an org pack with `<org_root>/<mission_type>/expected-artifacts.yaml` declaring one
  extra `required_always` artifact for a registered built-in type (e.g. `software-dev`).
  Assert the resolved manifest's `required_always` count/content changed relative to the
  built-in-only baseline — a delta, not merely "no exception."
- Whole-file-precedence test: configure both an org file **and** rely on the existing built-in
  file for the same mission type; assert the org file **fully replaces** the built-in one (its
  content is what's returned, not a merge of both) — SC-005 Given #3.

### T027 — Integration tests: `ManifestRegistry.load_manifest` (SC-005 + cache-key regression)

In `tests/dossier/test_manifest.py`:

- Org-override delta test mirroring T026's shape, but through `ManifestRegistry.load_manifest`
  with a `repo_root` argument.
- **Byte-identical no-override test (SC-005 Given #2)**: `load_manifest(mission_type)` called
  with no `repo_root` (or `repo_root=None`) produces output identical to pre-this-WP behavior —
  this is the test that proves the optional-parameter shape didn't silently change default
  behavior.
- **Cache-key regression test**: call `load_manifest("software-dev", repo_root=project_a)`
  where `project_a` has an org override, then `load_manifest("software-dev",
  repo_root=project_b)` where `project_b` has a **different** (or no) org override, in the same
  test process (mirroring `ManifestRegistry._cache` being process-global). Assert the second
  call does **not** silently return the first call's cached result — this is the exact defect
  this WP's cache-key fix exists to close; use `ManifestRegistry.clear_cache()` between
  unrelated test cases as needed, but this specific test must **not** clear the cache between
  the two calls, since proving no-shadowing-without-clearing is the point.

## Branch Strategy

Both planning and merge target are `pr/up-org-doctrine-consumers-01M05YAB`. Allocate via
`spec-kitty implement WP05` (depends on WP04 — file-collision ordering, not functional; do not
start until WP04 has merged). This mission's `meta.json` records `target_branch: main` while
the actual planning/merge branch is `pr/up-org-doctrine-consumers-01M05YAB` — a known mismatch;
do not improvise around it if a command refuses, flag it instead.

## Definition of Done

- `resolve_org_expected_artifacts` implemented per contract C-4 (last-wins precedence,
  whole-file replacement, no built-in-baseline-required).
- `_resolve_expected_artifacts_slot` and `ManifestRegistry.load_manifest` both wired to it,
  falling back to existing built-in-only behavior when the org helper returns `None`.
- `ManifestRegistry.load_manifest`'s cache-key fix implemented and proven not to shadow across
  different `repo_root`s in the same process (T027).
- SC-005's three Given scenarios (count/content delta, byte-identical no-override,
  whole-file-not-merge precedence) all have a passing regression test.
- `pytest tests/charter/test_mission_type_profiles.py tests/charter/test_org_expected_artifacts.py tests/dossier/test_manifest.py -v`
  green.

## Risks / Reviewer guidance

- **This is the mission's largest and riskiest package.** A reviewer should specifically not
  accept "the happy-path org override works" as sufficient — the cache-key fix (T023/T024/T027)
  is the part most likely to hide a real bug (stale results shadowing across projects) if
  under-tested, and it is easy to skip since FR-008's own spec text does not mention it at all.
- `src/charter/org_expected_artifacts.py` and `src/charter/mission_type_profiles.py` are in the
  enforced critical-path `diff-cover --fail-under=90` gate (`src/charter/*`).
  `src/specify_cli/dossier/manifest.py` is **not** critical-path and has no dedicated coverage
  job — same caveat as WP02/WP03's non-critical-path files: red-first tests (NFR-001) are the
  real backstop here, not a coverage gate.
- Confirm the file collision with WP04 resolved cleanly: your diff to
  `mission_type_profiles.py` should touch only `_resolve_expected_artifacts_slot` and its
  caller-threading, never `_resolve_governance_slot` or `_mission_type_profile_repository`
  (WP04's functions).
- Do not add a new method to `MissionTemplateRepository` (C-003) — the org-file check is a
  free function in the new module, called by both consumers, not a class method.
- Confirm `resolve_manifest_version` (`specify_cli/sync/namespace.py`) is untouched and still
  compiles — it is explicitly out of scope, not an oversight to "helpfully" fix.
