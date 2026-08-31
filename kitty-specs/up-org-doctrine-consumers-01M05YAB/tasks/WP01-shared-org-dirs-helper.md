---
work_package_id: WP01
title: Shared org_dirs resolution helper
dependencies: []
requirement_refs:
- FR-003
- NFR-002
- NFR-003
- NFR-006
planning_base_branch: pr/up-org-doctrine-consumers-01M05YAB
merge_target_branch: pr/up-org-doctrine-consumers-01M05YAB
branch_strategy: Planning artifacts for this mission were generated on pr/up-org-doctrine-consumers-01M05YAB. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/up-org-doctrine-consumers-01M05YAB unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
history:
- at: '2026-08-16T19:20:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/
create_intent:
- tests/doctrine/drg/test_org_pack_config_resolve_org_dirs.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/doctrine/drg/org_pack_config.py
- tests/doctrine/drg/test_org_pack_config_resolve_org_dirs.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Shared org_dirs resolution helper

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

## Objective

Implement one shared function, `resolve_org_dirs(repo_root, subdir)`, that returns the
existing-path-filtered, declaration-ordered list of per-pack org directories for a given
artifact subdirectory name. This is the foundation four other requirements in this mission
(FR-001, FR-004, FR-005, FR-006, FR-006a — done in WP02/WP03/WP04) build on. Writing it once
here, and having every downstream WP import it rather than re-implement it, is the entire
point of FR-003: two of the five in-scope call sites (`gate_bindings.py` and `executor.py`)
had already independently drifted from each other before this mission existed — this helper
is what stops a third drift.

**This WP is a pure foundation package.** Nothing in this codebase calls `resolve_org_dirs`
yet (WP02/WP03/WP04 add the callers). Your job is only to make the helper correct, tested,
and exported — not to wire any caller.

## Context

### The reference implementation you are extracting from

`src/doctrine/service.py:118` (`DoctrineService.mission_step_contracts` property) is **already
correct** — treat it as the reference pattern, not something to reinvent:

```python
@property
def mission_step_contracts(self) -> MissionStepContractRepository:
    if "mission_step_contracts" not in self._cache:
        self._cache["mission_step_contracts"] = MissionStepContractRepository(
            org_dirs=self._org_dirs("mission_step_contracts"),
            project_dir=self._project_dir("mission_step_contracts"),
        )
    return cast(MissionStepContractRepository, self._cache["mission_step_contracts"])
```

`DoctrineService._org_dirs` (`src/doctrine/service.py:47-52`) is the exact logic to lift out
into a standalone function:

```python
def _org_dirs(self, artifact: str) -> list[Path]:
    """Return per-pack org-layer directories for *artifact* in declaration order.
    ...
    """
    return [root / artifact for root in self._org_roots]
```

`self._org_roots` there is itself sourced from `resolve_org_roots(repo_root)` — the existing
function in the same module you are editing, `src/doctrine/drg/org_pack_config.py:404-412`:

```python
def resolve_org_roots(repo_root: Path) -> list[Path]:
    """Return configured org doctrine local roots in declaration order."""
    return [pack.effective_root(repo_root) for pack in load_pack_registry(repo_root).packs]
```

Your new function is the missing piece between these two: `resolve_org_roots` gives you org
**roots**; `_org_dirs` (currently private to `DoctrineService`) joins a subdirectory onto each
and is what you are promoting to a standalone, reusable function.

### The resolver-shape distinction — read this before you touch anything

This mission has **two structurally different** org-tier resolution shapes, and conflating
them is a mistake the mission's own spec had to explicitly correct once (see spec.md D-000(2)):

- **List shape** (`org_dirs: list[Path]`) — what **you** are building here. Consumed by every
  `BaseDoctrineRepository` subclass constructor (`doctrine/base.py`), including
  `MissionStepContractRepository` and `MissionTypeProfileRepository`. Declaration order
  matters: later-configured packs override earlier ones for the same artifact id (NFR-003) —
  this is an existing, unchanged merge semantic your helper must preserve, not something you
  implement yourself (the merge happens inside `BaseDoctrineRepository`, not in your function).
- **Single-path shape** (`org_root: Path | None`) — consumed by
  `charter._drg_helpers.load_validated_graph(repo_root, org_root=...)`. This is **not** your
  concern in this WP. WP02 resolves it inline (first-match pattern, mirroring
  `charter/action_doctrine_bundle.py:_resolve_action_bundle` lines ~90-97) — it is deliberately
  **not** a shared helper, because the spec's FR-003 only mandates one for the list shape. Do
  not build a single-path variant here "for completeness" — it is out of this WP's scope and
  would just be unused code.

### Contract C-1 (binding shape — write exactly this signature)

From `contracts/org-tier-resolution-contract.md`:

```python
def resolve_org_dirs(repo_root: Path, subdir: str) -> list[Path]:
    """Existing-path-filtered, declaration-ordered org directories for *subdir*."""
```

- **Guarantee**: Returns `[]` when no org packs are configured, or when configured packs'
  roots do not exist on disk. **Never raises** for a missing/stale config entry (NFR-002 —
  a stale `local_path` config entry must degrade to "no org contribution," not an exception).
- **Guarantee**: Declaration order preserved — later-configured packs appear later in the
  returned list (downstream `BaseDoctrineRepository` subclasses interpret "later overrides
  earlier" for a same-id collision; NFR-003).
- **Non-guarantee**: Does **not** check whether `<root>/<subdir>` itself exists — only the org
  **root** is existence-filtered before joining. This mirrors
  `charter.doctrine_service_builder._self_resolve_existing_org_roots` (lines 142-152):
  existence filtering happens at the org-root level, not the joined-subdirectory level. A
  caller passing the result into a `BaseDoctrineRepository` subclass relies on that
  repository's own load-time missing-directory tolerance (existing, unchanged behavior).
- **Invariant** (data-model.md): `resolve_org_dirs(repo_root, subdir) == [root / subdir for
  root in resolve_org_roots(repo_root) if root.exists()]`. Your implementation should make this
  invariant trivially true, not merely coincidentally true — implement it in terms of
  `resolve_org_roots`, don't reimplement pack-registry loading.

### Consumers and their `subdir` values (for context only — not this WP's job to wire)

- FR-001 (`executor.py`), FR-005 (`gate_bindings.py`), FR-006
  (`runtime_bridge_composition.py`), FR-006a (`mission_loader/command.py`):
  `subdir="mission_step_contracts"`.
- FR-004 (`mission_type_profiles.py`): `subdir="mission_types"` — note this is **not** an
  `ArtifactKind` enum member (verified: `ArtifactKind` in `src/doctrine/artifact_kinds.py` has
  no mission-type member). Your function signature must accept an arbitrary caller-supplied
  string, not restrict to `ArtifactKind.plural` values.

## Subtasks

### T001 — Implement `resolve_org_dirs(repo_root, subdir)` [P]

In `src/doctrine/drg/org_pack_config.py`, add:

```python
def resolve_org_dirs(repo_root: Path, subdir: str) -> list[Path]:
    """Existing-path-filtered, declaration-ordered org directories for *subdir*.

    Filters non-existent org-pack roots before joining *subdir* (mirrors
    charter.doctrine_service_builder._self_resolve_existing_org_roots), so a
    stale local_path config entry degrades to "no org contribution" cleanly
    rather than raising.
    """
    return [root / subdir for root in resolve_org_roots(repo_root) if root.exists()]
```

Place it immediately after `resolve_org_roots` (currently ~line 404-412) so the two functions
read as a pair. Add `"resolve_org_dirs"` to the module's `__all__` list (currently lines 21-29)
in alphabetical position, matching the existing convention.

Do not touch `DoctrineService._org_dirs` in `src/doctrine/service.py` — it is out of scope for
this WP (it already works correctly; a later WP could refactor it to delegate to your new
function, but that is not required by any FR in this mission and is not part of this WP's
Definition of Done).

### T002 — Unit tests: empty config and single pack [P]

In new file `tests/doctrine/drg/test_org_pack_config_resolve_org_dirs.py`, using the same
`tmp_path` + `.kittify/config.yaml`-writing fixture pattern already used by
`tests/doctrine/test_org_pack_subdir.py` (see `_write_config_with_subdir` there for the YAML
shape), write:

- `test_no_org_packs_returns_empty_list` — no `.kittify/config.yaml` (or one with no
  `doctrine.org.packs` entries) → `resolve_org_dirs(repo_root, "mission_step_contracts") == []`.
- `test_single_pack_returns_one_joined_path` — one configured, existing org pack root →
  `resolve_org_dirs(...) == [org_root / "mission_step_contracts"]`.
- `test_invariant_matches_resolve_org_roots_composition` — asserts the C-1 invariant directly:
  `resolve_org_dirs(repo_root, subdir) == [r / subdir for r in resolve_org_roots(repo_root) if
  r.exists()]` for a fixture with at least one existing and one non-existent configured pack.

### T003 — Unit tests: multi-pack precedence and stale-path filtering [P]

Same test file as T002:

- `test_two_packs_preserve_declaration_order` (NFR-003) — configure two org packs in a known
  declared order; assert the returned list's order matches declaration order (not sorted,
  not reversed). This is the property downstream `BaseDoctrineRepository` subclasses rely on
  for "later overrides earlier."
- `test_nonexistent_org_root_is_filtered_not_raised` (NFR-002 / Edge Cases) — configure an org
  pack whose `local_path` does not exist on disk; assert `resolve_org_dirs(...)` returns `[]`
  (or omits that pack from a mixed list) **without raising**, and — this is the NFR-002 part
  that actually matters — assert this in a way that is distinguishable from "no org pack was
  ever configured" (e.g. assert on a captured log line or a mixed-fixture case with one valid
  and one stale pack, proving the stale one specifically was dropped, not that resolution
  silently no-opped for everything).

### T004 — Verify coverage and terminology gates locally

Run and confirm green, from the repo root:

```bash
pytest tests/doctrine/drg/test_org_pack_config_resolve_org_dirs.py -v
pytest tests/architectural/test_no_legacy_terminology.py -q
```

`src/doctrine/drg/org_pack_config.py` is in the enforced critical-path `diff-cover
--fail-under=90` gate (`.github/workflows/ci-quality.yml`'s critical-path job covers
`src/doctrine/*`) — your new function's lines must be exercised by T002/T003's tests, not just
present. `src/doctrine/` is also in scope for the terminology guard (NFR-006) since this WP
touches a file under that tree — confirm the guard passes locally before considering this WP
done; it runs in CI's `integration-tests-core-misc` job, not the fast-tests suites, so a
regression here would not surface until CI otherwise.

## Branch Strategy

Both planning and merge target are `pr/up-org-doctrine-consumers-01M05YAB`. Allocate via
`spec-kitty implement WP01` (no dependencies — this WP can start immediately after
finalize-tasks). Note: this mission's `meta.json` records `target_branch: main`, which does not
match the branch you are actually working on — this is a known, already-observed mismatch on
this branch (the mission's spec and plan commits were committed manually for the same reason).
If any `spec-kitty` command refuses an operation citing that mismatch, do not fight it silently —
flag it in your WP report rather than working around it with an improvised branch target.

## Definition of Done

- `resolve_org_dirs(repo_root, subdir) -> list[Path]` implemented in
  `src/doctrine/drg/org_pack_config.py`, exported via `__all__`.
- All T002/T003 tests pass and demonstrably exercise the function (not vacuously trivial).
- `pytest tests/architectural/test_no_legacy_terminology.py` passes.
- No caller anywhere in `src/` references `resolve_org_dirs` yet — that is WP02/WP03/WP04's
  job, not this WP's. Wiring a caller here would be scope creep and risks a merge collision
  with those WPs' `owned_files`.

## Risks / Reviewer guidance

- **Low risk overall** — this is an ~15-20 LOC pure function with no I/O beyond what
  `resolve_org_roots` already does.
- The one design decision a reviewer should specifically check: existence filtering happens at
  the **org-root** level (`root.exists()`), not by checking `(root / subdir).exists()`. This is
  intentional (matches `_self_resolve_existing_org_roots`'s precedent) — do not "fix" it to
  check the joined path; that would change behavior for every downstream caller in ways NFR-002
  does not ask for and the reference implementation (`doctrine/service.py:118`) does not do
  either.
- Do not add a `subdir: ArtifactKind` type restriction — FR-004's `"mission_types"` caller
  (landed in WP04) is not an `ArtifactKind` member, so the parameter must stay a plain `str`.
