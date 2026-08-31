---
work_package_id: WP07
title: 'Wave A LD-3: route charter_freshness/computer.py through ensure_charter_bundle_fresh (FR-013)'
dependencies:
- WP06
requirement_refs:
- FR-013
planning_base_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
merge_target_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
base_commit: 8459756e0ecc57ce7f78d435bf33bcad52f59385
created_at: '2026-05-25T15:48:30.486298+00:00'
subtasks:
- T023
- T024
- T025
- T026
- T027
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "2228711"
history:
- by: claude
  at: '2026-05-25T14:00:00+00:00'
  action: generated
agent_profile: python-pedro
authoritative_surface: src/specify_cli/charter_freshness/
execution_mode: code_change
mission_id: 01KSF9HJBFKRBC617JVHKZXNE2
mission_slug: test-stabilization-and-debt-pass-01KSF9HJ
owned_files:
- src/specify_cli/charter_freshness/computer.py
- tests/specify_cli/charter_freshness/test_computer.py
priority: P1
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Invoke `/ad-hoc-profile-load` with argument `python-pedro` before reading further. Behaviour-preserving routing change; preserves the public `compute_freshness` API.

## Objective

Route the manifest and graph reads inside `src/specify_cli/charter_freshness/computer.py` through the canonical `charter.compiler.ensure_charter_bundle_fresh` chokepoint. This closes LD-3 from the architectural review (which was RISK-2 in the post-merge mission review of #122).

The current code reads `.kittify/charter/synthesis-manifest.yaml` and `.kittify/doctrine/graph.yaml` directly via `_safe_load_yaml(...)` and `Path.exists()` at `computer.py:280-281`. This bypasses the chokepoint's refresh semantics and creates a potential staleness window under concurrent invocation.

**Behaviour-preserving** (spec C-007): `compute_freshness(repo_root) -> CharterFreshness` public API and its three sub-state semantics unchanged. The data-model §6 conflict-resolution case (`built_in_only=true` AND `graph.yaml` present ⇒ `state="invalid"`) MUST still fire correctly.

## Branch strategy

- Planning base branch: mission lane branch (post-WP06)
- Merge target branch: `main`
- Execution: lane workspace allocated by `finalize-tasks`.

## Context

- [`spec.md`](../spec.md) FR-013 + C-007.
- [`plan.md`](../plan.md) Wave A § WP07 (behaviour-preservation test anchors).
- [`docs/engineering_notes/architectural-review/2026-05-25-deep-dive-architectural-review.md`](../../../docs/engineering_notes/architectural-review/2026-05-25-deep-dive-architectural-review.md) §2 LD-3.
- [`architecture/3.x/adr/2026-05-24-1-charter-freshness-ux-contract.md`](../../../architecture/3.x/adr/2026-05-24-1-charter-freshness-ux-contract.md) — the public contract.
- Existing source: `src/specify_cli/charter_freshness/computer.py` (lines 100, 103, 280, 281).
- Chokepoint API: `src/charter/compiler.py::ensure_charter_bundle_fresh` (or its read-only sibling — verify name).

## Subtask details

### T023 — Identify the canonical chokepoint API

```bash
grep -n "def ensure_charter_bundle_fresh\|def .*fresh.*bundle\|@.*fresh" src/charter/compiler.py 2>&1 | head
```

Read the function signature + docstring. Determine whether `ensure_charter_bundle_fresh` is the right entry point or whether there's a `read_charter_bundle` (read-only sibling) that better fits the freshness module's needs. If only the refresh-side exists, request from charter.compiler a `load_charter_bundle_snapshot(repo_root) -> CharterBundleSnapshot` read-only helper as a small in-WP addition.

### T024 — Route manifest read through chokepoint

In `src/specify_cli/charter_freshness/computer.py`, replace the direct manifest read at line 281:

```python
# BEFORE
from .computer import _safe_load_yaml  # or wherever
manifest_data = _safe_load_yaml(manifest_path)

# AFTER
from charter.compiler import load_charter_bundle_snapshot  # or whatever T023 settles on
snapshot = load_charter_bundle_snapshot(repo_root)
manifest_data = snapshot.synthesis_manifest  # or whatever the snapshot exposes
```

If the chokepoint API only provides "force-refresh" semantics, gate the refresh on a freshness-aware flag so `compute_freshness` itself doesn't recursively trigger a refresh (that would change semantics and break NFR-001 perf budget).

### T025 — Route graph read through chokepoint

Same pattern for the `.kittify/doctrine/graph.yaml` direct read at line 280. Replace with the chokepoint-returned graph reference.

### T026 — Verify public API unchanged

```bash
python3 -c "
from specify_cli.charter_freshness import compute_freshness, CharterFreshness, FreshnessSubState
import inspect
print(inspect.signature(compute_freshness))
print(CharterFreshness.__dataclass_fields__.keys())
"
```

Expected signature: `(repo_root: Path) -> CharterFreshness`. The `CharterFreshness` dataclass fields must remain `charter_source`, `synced_bundle`, `synthesized_drg` (each a `FreshnessSubState`).

### T027 — Verify data-model §6 conflict-resolution test

The conflict case (`built_in_only=true` AND `graph.yaml` present ⇒ `state="invalid"` with remediation `spec-kitty charter synthesize --force-overwrite`) is asserted in `tests/specify_cli/charter_freshness/test_computer.py`. If that exact test isn't there (it should be from mission #122 WP02), ADD it before the routing change so the refactor is locked behind it.

```bash
PWHEADLESS=1 .venv/bin/pytest tests/specify_cli/charter_freshness/test_computer.py -q
PWHEADLESS=1 .venv/bin/pytest tests/integration/test_charter_status_freshness.py -q
```

## Definition of Done

- [ ] No direct `.kittify/charter/synthesis-manifest.yaml` or `.kittify/doctrine/graph.yaml` reads remain in `src/specify_cli/charter_freshness/computer.py`.
- [ ] Reads go through the chokepoint API identified in T023.
- [ ] `compute_freshness()` public API unchanged (signature + return-shape).
- [ ] Data-model §6 conflict-resolution test green.
- [ ] All `tests/specify_cli/charter_freshness/` tests green.
- [ ] NFR-001 perf (preflight warm <300 ms) still passes if exercised.
- [ ] Success criterion 5 of the spec verified: `git grep -n "_safe_load_yaml\|.kittify/charter/synthesis-manifest\|.kittify/doctrine/graph.yaml" src/specify_cli/charter_freshness/` returns no direct reads outside the chokepoint adapter.

## Risks

- **Chokepoint refresh-recursion**: if the chokepoint API only has refresh semantics, calling it from `compute_freshness` could trigger a refresh inside what should be a read. Guard with a freshness-only flag or use a read-only sibling.
- **Perf regression**: the chokepoint may do extra validation work that `_safe_load_yaml` skipped. Verify the preflight `<300 ms` NFR-001 budget still holds.

## Reviewer guidance

1. Verify zero direct manifest/graph reads remain — `git grep` is the contract.
2. Verify the data-model §6 conflict case fires under the new routing (the test name from the plan is `test_invalid_state_when_built_in_only_and_graph_yaml_both_exist` — if that's not the exact test, identify the one that does this and quote it).
3. Verify NFR-001 perf if applicable.

## Activity Log

- 2026-05-25T15:48:31Z – claude:opus-4-7:python-pedro:implementer – shell_pid=2192695 – Assigned agent via action command
- 2026-05-25T15:55:44Z – claude:opus-4-7:python-pedro:implementer – shell_pid=2192695 – LD-3 closed: manifest+graph reads routed through chokepoint; public API unchanged; §6 conflict rule still fires
- 2026-05-25T15:56:20Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=2228711 – Started review via action command
- 2026-05-25T15:58:44Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=2228711 – Review passed: LD-3 closed via typed chokepoint API; public API unchanged; §6 conflict test passes
