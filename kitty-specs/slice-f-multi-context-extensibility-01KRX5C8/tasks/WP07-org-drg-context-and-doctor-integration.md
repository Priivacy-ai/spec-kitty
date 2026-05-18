---
work_package_id: WP07
title: Org-DRG integration — `build_charter_context` wiring + `doctor doctrine` + provenance render
dependencies:
- WP06
requirement_refs:
- C-001
- FR-001
- FR-002
- FR-007
- NFR-001
- NFR-003
- NFR-005
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T034
- T035
- T036
- T037
- T038
agent: claude:opus-4-7:python-pedro:implementer
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/context.py
execution_mode: code_change
owned_files:
- src/charter/context.py
- src/specify_cli/cli/commands/doctor.py
- tests/integration/test_charter_status_reports_three_layers.py
- tests/charter/test_context_provenance.py
- tests/specify_cli/cli/commands/test_doctor_doctrine_org_layer.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Scope governance context to Python implementation before reading anything else.

---

## Objective

Wire WP06's `load_org_drg` + `merge_three_layers` into the existing `build_charter_context` rendering pipeline so the resolved prompt body carries per-layer `source:` provenance (`built-in | org:<pack> | project`); extend `spec-kitty doctor doctrine` to surface org-layer state (configured packs, fetched/missing, collision warnings) in its Selections section.

NFR-001 binds: when no `organisation_packs:` is configured in `.kittify/config.yaml`, `build_charter_context` behaviour is byte-identical to today — the 23 `test_wp_prompt_governance_contract.py` fixtures pass unchanged.

---

## Context

After WP06, the org-DRG schema, loader, merge, and validator extension are in place. WP07 surfaces them through the operator's everyday touchpoints:

- **`build_charter_context`** (the prompt builder's entry to charter resolution) consumes `load_org_drg` + `merge_three_layers` and threads per-layer provenance into the `_render_*` helpers so rendered artifact stanzas carry the `source:` marker. This satisfies FR-001's "preserves per-artefact provenance" surface (the renderer side).
- **`spec-kitty doctor doctrine`** gains an "Organisation Layer" subsection listing each configured pack, its fetched/missing status (per FR-004 policy), and any collision warnings surfaced by `merge_three_layers`. This satisfies FR-007.
- **`spec-kitty charter status`** reports the presence/absence and freshness of each of the three DRG layers (shipped, organisation, project). This satisfies FR-002.

Per **NFR-001** (binding): the 23 `test_wp_prompt_governance_contract.py` fixtures pass unchanged. The way to guarantee this is to make org-DRG wiring a NO-OP when `load_org_drg(repo_root)` returns `[]` — and an empty `.kittify/config.yaml::organisation_packs:` is the default state.

References:
- [spec.md §"Scenario 1 — Organisation-tier doctrine"](../spec.md)
- [spec.md FR-001, FR-002, FR-007](../spec.md)
- [plan.md §1.1, §2.3, §2.13](../plan.md)
- [data-model.md §2 OrgDRGFragment provenance threading](../data-model.md)
- [atdd-coverage.md AC-1 (provenance side), AC-2 (doctor)](../atdd-coverage.md)

**Ownership boundary note (`src/charter/context.py`):** WP09 also touches `build_charter_context` to thread a `scope=` parameter. Resolution: WP07 owns `src/charter/context.py` for the org-DRG wiring. WP09 implements its scope wiring as a thin wrapper module `src/charter/scope_router.py` that calls into `build_charter_context` rather than changing its signature. This avoids cross-WP file ownership conflict.

---

## ATDD Discipline

Per **C-011** WP07 lands its lane-incremental ATDD test as its FIRST commit:

1. **Commit A (RED, T034):** `tests/integration/test_charter_status_reports_three_layers.py` — `spec-kitty charter status` MUST report shipped + org + project layers when org packs are configured. RED on planning base because `charter status` does not yet know about org layers. Commit message: `covers: FR-002 — expected GREEN at: WP07 final commit`.
2. **Commits B..E (GREEN progression, T035-T038):** wire `build_charter_context`, thread provenance, extend `doctor doctrine`, confirm regression suite.

ATDD anchors per [atdd-coverage.md](../atdd-coverage.md):
- FR-002 / partial AC-1: `tests/integration/test_charter_status_reports_three_layers.py`
- AC-1 (full): completion of `tests/integration/test_three_layer_drg_end_to_end.py::test_charter_lint_lints_all_three_layers_with_provenance` (mostly WP06; WP07's provenance render is the final brick)
- AC-2 (partial — doctor side): `tests/specify_cli/cli/commands/test_doctor_doctrine_org_layer.py`

---

## Subtasks

### T034 — Land failing-first `tests/integration/test_charter_status_reports_three_layers.py`

**File:** `tests/integration/test_charter_status_reports_three_layers.py` (new)

```python
"""FR-002: charter status reports all three DRG layers."""
from __future__ import annotations

from pathlib import Path

import pytest


def test_charter_status_reports_shipped_org_and_project(
    tmp_repo_with_org_pack: Path,
) -> None:
    """When an org pack is configured, charter status lists all three layers."""
    # Invoke `spec-kitty charter status` in-process (typer.testing.CliRunner)
    # OR via subprocess; assert output contains:
    #  - "[shipped]" / "[built-in]"
    #  - "[org:example-org]"
    #  - "[project]"
    ...


def test_charter_status_reports_only_two_layers_without_org_pack(
    tmp_repo_without_org_pack: Path,
) -> None:
    """NFR-001: when no org pack configured, behaviour is byte-identical to today."""
    # Assert output does NOT introduce an empty "[org]" section
    ...
```

**Validation:** `pytest tests/integration/test_charter_status_reports_three_layers.py -v` MUST FAIL on planning base. Commit RED.

### T035 — Wire `load_org_drg` + `merge_three_layers` into `build_charter_context`

**File:** `src/charter/context.py`

Locate the existing `build_charter_context` function. Add the org-DRG wiring:

```python
from charter.drg import load_org_drg, merge_three_layers

def build_charter_context(repo_root, feature_dir, **kwargs):
    shipped = _load_shipped_drg()
    org_fragments = load_org_drg(repo_root)
    project = _load_project_drg(repo_root)
    merged_drg = merge_three_layers(shipped, org_fragments, project)
    # thread merged_drg into the existing rendering pipeline
    return _render(merged_drg, feature_dir, **kwargs)
```

**NFR-001 byte-stability:** when `load_org_drg` returns `[]` and `project` is `None`, `merge_three_layers` must produce a graph byte-identical to the shipped-only graph the previous code path produced. Verify by running `pytest tests/specify_cli/next/test_wp_prompt_governance_contract.py -v` AFTER this change — 23/23 MUST still pass.

Do NOT change the function signature in this WP (WP09 owns signature extension via the scope_router wrapper). If `build_charter_context` currently accepts no kwargs, leave it; just internally consult `load_org_drg(repo_root)`.

### T036 — Thread per-layer `source:` provenance into `_render_*` helpers

**File:** `src/charter/context.py`

For each `_render_<kind>` helper that emits artifact stanzas, thread the `source:` field from the merged graph into the rendered output. Example transformation:

```yaml
# BEFORE
directives:
  - id: caveman-comments
    body: ...

# AFTER
directives:
  - id: caveman-comments
    source: built-in
    body: ...
  - id: sox-controls
    source: org:acme-compliance
    body: ...
```

The `source:` field is purely additive — existing fixtures without an org pack continue to emit only `source: built-in` (or are unchanged if the `source:` field is omitted when there's only one layer). Decide:

- **Option A (additive always):** every stanza carries `source:` even when only built-in. Breaks NFR-001 (23 fixtures would diff).
- **Option B (additive when org present):** stanzas carry `source:` only when an org pack contributes. Preserves NFR-001.

**Choose Option B** to preserve NFR-001 byte-stability. Verify by running the 23-fixture suite.

### T037 — Extend `spec-kitty doctor doctrine` to surface org-layer state

**File:** `src/specify_cli/cli/commands/doctor.py`

Locate the `doctor doctrine` command implementation. Find the Selections section. Append an "Organisation Layer" subsection:

```
Organisation Layer:
  - acme-compliance       [local_path: ../acme-org-doctrine]         ✓ loaded (12 nodes, 4 edges)
  - acme-engineering      [local_path: ../acme-engineering-doctrine] ✗ MISSING — path does not exist
  collisions: 1 shipped-invariant override silently ignored from acme-compliance
```

Implementation:

```python
def _render_org_layer_section(repo_root: Path, console) -> None:
    try:
        fragments = load_org_drg(repo_root)
    except OrgPackMissingError as e:
        console.print(f"[red]Org pack missing: {e}[/red]")
        return
    if not fragments:
        console.print("Organisation Layer: (no packs configured)")
        return
    console.print("Organisation Layer:")
    for f in fragments:
        node_count = len(f.nodes)
        edge_count = len(f.edges)
        console.print(f"  - {f.pack_name}   [{f.source_kind}: {f.source_ref}]   ✓ loaded ({node_count} nodes, {edge_count} edges)")
    # collisions: load shipped, merge, surface any silent shipped_wins
    ...
```

### T038 — Confirm Lane C tests GREEN; regression sweep clean

```bash
pytest tests/integration/test_charter_status_reports_three_layers.py -v
# EXPECTED: GREEN

pytest tests/integration/test_three_layer_drg_end_to_end.py -v
# EXPECTED: GREEN (provenance render completes AC-1)

pytest tests/specify_cli/cli/commands/test_doctor_doctrine_org_layer.py -v
# EXPECTED: GREEN (partial AC-2; rest in WP08)

pytest tests/specify_cli/next/test_wp_prompt_governance_contract.py -v
# EXPECTED: 23/23 pass unchanged (NFR-001)

PWHEADLESS=1 pytest tests/architectural/ -v
# EXPECTED: exit 0 (NFR-005)
```

---

## Definition of Done

The following tests turn GREEN with this WP:

- ✅ `tests/integration/test_charter_status_reports_three_layers.py::test_charter_status_reports_shipped_org_and_project` (was RED on planning base)
- ✅ `tests/integration/test_charter_status_reports_three_layers.py::test_charter_status_reports_only_two_layers_without_org_pack` (NFR-001)
- ✅ `tests/integration/test_three_layer_drg_end_to_end.py::test_charter_lint_lints_all_three_layers_with_provenance` (now fully GREEN with provenance render)
- ✅ `tests/charter/test_context_provenance.py` (new unit suite — every `_render_*` helper threads `source:` when present)
- ✅ `tests/specify_cli/cli/commands/test_doctor_doctrine_org_layer.py` (new)
- ✅ 23 governance-contract fixtures pass unchanged (NFR-001)
- ✅ Full architectural sweep exit 0 (NFR-005)
- ✅ Layer-rule sweep unchanged (NFR-003)

FR coverage:

- ✅ FR-001 — per-artifact provenance now fully threaded through the renderer
- ✅ FR-002 — `charter status` reports all three layers
- ✅ FR-007 — `doctor doctrine` surfaces org-layer state

AC coverage:

- ✅ AC-1 — three-layer DRG operational end-to-end (org-configured DRG merges with shipped + project; `charter lint` lints all three; `build_charter_context` resolves through all three with provenance — completed here)
- ✅ Partial AC-2 — `doctor doctrine` surfaces org state (the `doctrine org init` + `org validate` operator commands ship in WP08)

---

## Risks

1. **NFR-001 regression** — adding `source:` to render output diffs the 23 fixtures. Mitigation: T036 chooses Option B (additive when org present); the 23 fixtures don't configure org packs, so their output stays byte-identical. Verify after T036 by re-running the suite.
2. **`build_charter_context` signature change** — WP09 also wants to touch this signature. Mitigation: WP07 does NOT change signature; WP09 implements scope plumbing via a wrapper module (`scope_router.py`). No cross-WP file ownership collision.
3. **`merge_three_layers` raises `OrgDRGConflictError` during normal `doctor doctrine` invocation** — hard-fail in a diagnostic command is hostile. Mitigation: T037's `_render_org_layer_section` catches `OrgDRGConflictError` and renders the conflict as a finding instead of propagating. Doctor commands are READ-ONLY and should never crash on operator misconfiguration.
4. **`doctor doctrine` becomes too verbose** for large org packs. Mitigation: truncate node/edge counts to 3 lines per pack; full detail goes to `charter lint`.
5. **Provenance threading silently changes the layer rule check** — `test_runtime_charter_doctrine_boundary._BASELINE_ALLOWLIST` may grow. Mitigation: WP01's baseline is 0; if it grows, edit `_baselines.yaml` in the same PR with a justification comment so reviewer sees the diff.

---

## Reviewer Guidance

**ATDD red→green verification (mandatory per C-011):**

```bash
# 1. RED on planning base:
git checkout feat/org-doctrine-layer
pytest tests/integration/test_charter_status_reports_three_layers.py -v
# EXPECTED: failure (charter status doesn't know about org layers)

# 2. GREEN on WP final commit:
git checkout <wp_branch>
pytest tests/integration/test_charter_status_reports_three_layers.py \
       tests/integration/test_three_layer_drg_end_to_end.py \
       tests/specify_cli/cli/commands/test_doctor_doctrine_org_layer.py -v
# EXPECTED: GREEN
```

**Substantive review checks:**

- Confirm `build_charter_context` signature is UNCHANGED (WP09 owns signature extension).
- Confirm `load_org_drg(repo_root)` is called from `build_charter_context`; org-DRG nodes thread `source:` into the rendered output.
- Confirm Option B is implemented: stanzas carry `source:` only when an org pack contributes. Verify by running 23-fixture suite: `pytest tests/specify_cli/next/test_wp_prompt_governance_contract.py -v` — MUST stay 23/23 (NFR-001 binding).
- Confirm `doctor doctrine` catches `OrgDRGConflictError` and renders gracefully (diagnostic commands never crash on operator misconfiguration).
- Confirm layer-rule unchanged: `src/charter/context.py` imports nothing from `src/specify_cli/` (NFR-003).
- Confirm `_baselines.yaml::test_runtime_charter_doctrine_boundary` is still 0 (or edited with justification if it grew).
- Confirm full architectural sweep exit 0 (NFR-005).

**FR-304 commit-message check:** T034 RED commit cites `covers: FR-002 — expected GREEN at: WP07 final commit`.
