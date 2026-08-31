---
work_package_id: WP02
title: 'Wave 1: status freshness + synthesize post-condition (FR-005, FR-009)'
dependencies:
- WP01
requirement_refs:
- FR-005
- FR-009
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-ux-and-org-pack-vocabulary-01KSAF14
base_commit: febef640b762b91dc27b4dbcbfb0f3a9b12b28c2
created_at: '2026-05-24T08:59:30.360888+00:00'
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
- T014
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "1076547"
history:
- by: claude
  at: '2026-05-23T13:30:00+00:00'
  action: generated
agent_profile: python-pedro
authoritative_surface: src/charter/synthesizer/
execution_mode: code_change
mission_id: 01KSAF14K8FZ56MHYT45EGWHHC
mission_slug: charter-ux-and-org-pack-vocabulary-01KSAF14
owned_files:
- src/specify_cli/cli/commands/charter.py
- src/specify_cli/charter_freshness/**
- src/charter/synthesizer/manifest.py
- src/charter/synthesizer/project_drg.py
- src/charter/synthesizer/orchestrator.py
- tests/integration/test_charter_status_freshness.py
- tests/integration/test_charter_synthesize_built_in_only.py
- tests/specify_cli/charter_freshness/**
priority: P0
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Invoke `/ad-hoc-profile-load` with argument `python-pedro` before reading further. Pedro's Pydantic + pytest + pathlib focus covers freshness computation, manifest schema updates, and atomic file operations.

## Objective

Extend `charter status --json` with a `freshness` sub-payload computed by hash/timestamp comparison (FR-005), and codify the `charter synthesize` post-condition on fresh checkouts: either `.kittify/doctrine/graph.yaml` exists OR `synthesis-manifest.yaml` records `built_in_only: true` (FR-009). Resolve the conflict case per `data-model.md §6` deterministically.

## Branch strategy

- Planning base branch: `main`
- Merge target branch: `main`
- Execution worktree: allocated by `finalize-tasks`.

## Context

- `kitty-specs/.../spec.md` — FR-005, FR-009
- `kitty-specs/.../contracts/charter-status-json.md` — JSON shape and staleness rules
- `kitty-specs/.../data-model.md` — §5 (freshness sub-object), §6 (conflict resolution)
- Existing source: `src/specify_cli/cli/commands/charter.py::status` (line ~1708), `src/charter/synthesizer/manifest.py`, `src/charter/synthesizer/project_drg.py`
- WP01's `GraphState` enum — `synthesized_drg.state = "built_in_only"` aligns with this enum value

## Subtask details

### T008 — DIR-012 assign #1101 and #1104 to HiC

```bash
unset GITHUB_TOKEN
gh issue edit 1101 --add-assignee @stijn-dejongh --repo Priivacy-ai/spec-kitty
gh issue edit 1104 --add-assignee @stijn-dejongh --repo Priivacy-ai/spec-kitty
```

### T009 — Freshness computation

**Files**: NEW `src/specify_cli/charter_freshness/__init__.py`, `src/specify_cli/charter_freshness/computer.py`

Create a small helper module (separate from `charter_lint` to keep responsibility clear). Public functions:

```python
def compute_freshness(repo_root: Path) -> CharterFreshness:
    """Return a CharterFreshness with three sub-states."""
```

Where `CharterFreshness` is:
```python
@dataclass(frozen=True)
class FreshnessSubState:
    state: Literal["fresh", "stale", "missing", "built_in_only", "invalid"]
    last_change: str | None  # ISO 8601
    remediation: str | None

@dataclass(frozen=True)
class CharterFreshness:
    charter_source: FreshnessSubState
    synced_bundle: FreshnessSubState
    synthesized_drg: FreshnessSubState
```

Detection rules per `contracts/charter-status-json.md`:
- `charter_source.state = "stale"` when `.kittify/charter/charter.md` SHA-256 differs from `metadata.yaml` stored hash.
- `synced_bundle.state = "stale"` when any bundle file mtime is older than `charter_source.last_change`.
- `synthesized_drg.state = "stale"` when manifest's input mtimes are older than `synced_bundle.last_change`.
- `synthesized_drg.state = "missing"` when `.kittify/doctrine/graph.yaml` is absent AND manifest does not declare `built_in_only: true`.
- `synthesized_drg.state = "built_in_only"` when manifest declares `built_in_only: true`.
- `synthesized_drg.state = "invalid"` when manifest declares `built_in_only: true` AND `graph.yaml` also exists (conflict case — see T013).

### T010 — Wire freshness sub-payload into `charter status --json`

**Files**: `src/specify_cli/cli/commands/charter.py::status`

After the existing payload construction (around line 1730), add:
```python
from specify_cli.charter_freshness import compute_freshness
payload["freshness"] = compute_freshness(repo_root).to_dict()
```

Define `to_dict()` on `CharterFreshness` (one-line via `asdict`). The human-readable branch of `status` also surfaces a `[bold]Freshness[/bold]` section under "Synthesis"; render three rows with state-colour coding.

### T011 — Add `built_in_only` field to synthesis-manifest schema

**Files**: `src/charter/synthesizer/manifest.py`

Extend the manifest Pydantic model with `built_in_only: bool = False`. Update any model_dump/YAML serialisation to include the field. Backward compatibility: an old manifest without the field continues to load (Optional default).

### T012 — Synthesizer atomic post-condition

**Files**: `src/charter/synthesizer/project_drg.py`, `src/charter/synthesizer/orchestrator.py`

In the project-DRG generation path:
1. If synthesis produced project artifacts → write `.kittify/doctrine/graph.yaml`, set manifest `built_in_only=False`.
2. If synthesis legitimately had nothing to write → DELETE any existing `.kittify/doctrine/graph.yaml`, set manifest `built_in_only=True`.

The delete + manifest-write MUST be atomic from the caller's perspective. Implement using a temp-file + rename for the manifest, and a `Path.unlink(missing_ok=True)` for the graph file in the same try/except. Document the atomicity guarantee in a docstring.

### T013 — Conflict resolution

**Files**: `src/specify_cli/charter_freshness/computer.py`, `src/specify_cli/cli/commands/charter.py::status` human-readable rendering

When `compute_freshness` detects the conflict state (manifest `built_in_only=True` + `graph.yaml` exists), the sub-state is `"invalid"` with:
- `detail`: `"synthesis manifest declares built_in_only=true but graph.yaml exists; this is a stale artifact"`
- `remediation`: `"spec-kitty charter synthesize --force-overwrite"` (or `rm .kittify/doctrine/graph.yaml`, but the synthesize path is preferred per data-model §6).

Status human banner renders this as `[red]INVALID[/red]` with the detail and remediation visible.

### T014 — Tests for FR-005, FR-009 + conflict case

**Files**: NEW `tests/integration/test_charter_status_freshness.py`, NEW `tests/integration/test_charter_synthesize_built_in_only.py`, NEW `tests/specify_cli/charter_freshness/test_computer.py`

Cases:
1. Fresh repo (charter only) → `synthesized_drg.state = "missing"`.
2. Fresh repo after synthesize → `synthesized_drg.state = "fresh"` OR `"built_in_only"`.
3. Repo with conflict (manifest `built_in_only=true` + `graph.yaml` present) → `state = "invalid"` with conflict detail.
4. Repo with stale synthesis input → `synthesized_drg.state = "stale"`.
5. `charter status --json` payload contains all three sub-objects with required fields.
6. Synthesizer atomic delete + manifest write under simulated failure: verify no half-written state remains.

## Definition of Done

- [ ] Issues #1101 and #1104 assigned to HiC.
- [ ] `CharterFreshness` module exists with `compute_freshness(repo_root)` and `__all__` exports.
- [ ] `charter status --json` includes `freshness` top-level key with three sub-objects.
- [ ] Synthesizer guarantees the post-condition: either `graph.yaml` OR `built_in_only: true`, never both.
- [ ] Conflict case surfaces as `state="invalid"` with the documented remediation.
- [ ] Tests pass and cover all four detection states + conflict.
- [ ] `mypy --strict` and `ruff check` pass.

## Risks

- **Manifest schema migration**: pre-existing manifests in dogfood repos lack `built_in_only`. The Optional default solves loading but the orchestrator must write the field on the next run. Document in docstring.
- **Status command perf**: hash computation on every `charter status` invocation adds latency. Mitigation: SHA-256 of a charter.md is ~1 ms even at 20 KB; acceptable for NFR-001.

## Reviewer guidance

1. Verify atomic guarantee: write a test that injects an exception between the delete and the manifest write — the manifest must end up consistent.
2. Verify FR-009 acceptance: a fresh checkout + `charter synthesize` produces a deterministic, asserted post-condition (no flaky behaviour).
3. Verify the conflict case is impossible to produce via the new synthesizer — only legacy state should trigger `"invalid"`.

## Activity Log

- 2026-05-24T08:59:31Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1036861 – Assigned agent via action command
- 2026-05-24T09:12:54Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1036861 – Ready for review: freshness payload + atomic synthesize post-condition + conflict resolution
- 2026-05-24T09:13:25Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1076547 – Started review via action command
- 2026-05-24T09:15:55Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1076547 – Review passed: freshness payload + atomic synthesize post-condition + invalid-conflict state per data-model §6, 27 new tests pass, #1101/#1104 assigned
- 2026-05-24T11:46:50Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1076547 – Done override: Feature merged to main as squash commit 37407a3b2; status carried through from mission branch
