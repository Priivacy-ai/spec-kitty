---
work_package_id: WP05
title: Inventory Promotion + Tranche A Closeout
dependencies:
- WP02
- WP03
- WP04
requirement_refs:
- FR-001
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T024
- T025
agent: "claude:sonnet-4-6:implementer:implementer"
shell_pid: "18311"
history:
- event: created
  at: '2026-04-23T05:10:00Z'
  note: Initial generation from /spec-kitty.tasks
authoritative_surface: docs/host-surface-parity.md
execution_mode: code_change
owned_files:
- docs/host-surface-parity.md
- tests/specify_cli/docs/test_host_surface_inventory.py
tags: []
---

# WP05 — Inventory Promotion + Tranche A Closeout

## Objective

Promote the mission-local host-surface inventory matrix to a durable operator-facing doc at `docs/host-surface-parity.md`, ensure the doc is discoverable (linked from `docs/trail-model.md` and from the README Governance layer subsection), add the coverage test that enforces FR-001 / NFR-003, and mark Tranche A ready for merge.

This is the Tranche A closeout WP. Tranche B cannot start until WP05 merges.

## Context

WP01 authored the inventory in `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/artifacts/host-surface-inventory.md`. WP04 brought the non-canonical surfaces to parity and updated the matrix accordingly. WP05 takes that living matrix and:
1. Promotes it to a permanent docs location.
2. Adds a coverage test that enforces every `AGENT_DIRS` surface is represented.
3. Wires discoverability from the two operator doc anchors.
4. Signals that Tranche A is ready to merge.

## Branch Strategy

- **Planning base**: `main`.
- **Final merge target**: `main`.
- **Execution worktree**: allocated from `lanes.json` at implement time. WP05 depends on WP02, WP03, and WP04 all landing. The lane scheduler will not start WP05 until its dependencies are done.

## Subtask Guidance

### T020 — Promote inventory to `docs/host-surface-parity.md`

**Purpose**: Copy the mission-local matrix to the durable docs location, prefixed with an operator-facing preamble.

**Steps**:
1. Read `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/artifacts/host-surface-inventory.md`.
2. Create `docs/host-surface-parity.md`.
3. Write a preamble before the matrix:

   ```markdown
   # Host-Surface Parity Matrix

   This is Spec Kitty's authoritative record of how each supported host surface teaches hosts about the governance-injection contract for `spec-kitty advise`, `spec-kitty ask <profile>`, `spec-kitty do <request>`, and `spec-kitty profile-invocation complete`.

   **Keeping this matrix fresh**: any new host integration MUST add a row here; any change to how a host surface teaches the advise/ask/do loop MUST update the corresponding row. The coverage test at `tests/specify_cli/docs/test_host_surface_inventory.py` enforces that every surface from `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py::AGENT_DIRS` has exactly one row.

   **Schema and parity rubric**: see [kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/contracts/host-surface-inventory.md](../kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/contracts/host-surface-inventory.md).

   **Canonical skill packs referenced by `guidance_style=pointer` rows**:
   - [`.agents/skills/spec-kitty.advise/SKILL.md`](../.agents/skills/spec-kitty.advise/SKILL.md) — Codex CLI, Vibe.
   - [`src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`](../src/doctrine/skills/spec-kitty-runtime-next/SKILL.md) — Claude Code.

   ---
   ```

4. Append the matrix table (the full 9-column table from the mission-local inventory).
5. Confirm the file is valid markdown and renders cleanly.

**Note on dual location**: after WP05 merges, `docs/host-surface-parity.md` is the canonical reference. The `kitty-specs/.../artifacts/host-surface-inventory.md` is the mission-local record kept for the mission's audit trail and may diverge from the promoted doc over time (future changes update the promoted doc, not the mission artifact).

### T021 — Add link from `docs/trail-model.md`

**Purpose**: Make the promoted matrix discoverable from the shipped trail-model doc.

**Steps**:
1. Open `docs/trail-model.md`.
2. Locate a logical spot — typically at the end, or under a new "Host surfaces that teach the trail" subsection if none exists.
3. Add a short subsection:

   ```markdown
   ## Host surfaces that teach the trail

   The advise/ask/do surface is taught to host LLMs through per-host skill packs. See [`docs/host-surface-parity.md`](host-surface-parity.md) for the authoritative matrix of supported hosts and each host's parity status.
   ```

**Note**: WP08 also edits `docs/trail-model.md` to add new subsections (Mode of Work, Correlation Links, SaaS Read-Model Policy, Tier 2 deferral). WP05 and WP08 do NOT share ownership of `docs/trail-model.md` — WP08 owns that file per its owned_files. WP05's T021 needs a workaround:

**Resolution**: Do NOT edit `docs/trail-model.md` from WP05 directly. Instead, include the "Host surfaces that teach the trail" subsection in WP08's T044 as an additional doc-presence assertion. Delete this T021 step and move its intent into WP08's scope by updating the WP08 prompt if needed. Alternatively, WP05's owned_files must add `docs/trail-model.md` and WP08 removes it — the cleanest outcome.

**Chosen resolution**: update `tasks.md` and WP05/WP08 owned_files so WP05 owns `docs/trail-model.md` until Tranche A merges, and WP08 adds its subsections after. Since that creates lifecycle complexity, the simpler and final resolution is:

- **T021 is deferred**: WP05 does NOT link from `docs/trail-model.md`. Instead, **WP08's T044** includes adding a link to `docs/host-surface-parity.md` as part of its trail-model.md edits. This keeps ownership clean: only WP08 touches `docs/trail-model.md`.

Implementer: mark T021 as "deferred to WP08/T044" in the WP05 final report. Do not edit `docs/trail-model.md` from this WP.

### T022 — Verify README link to promoted matrix

**Purpose**: Confirm the forward link authored in WP03 now resolves.

**Steps**:
1. Read `README.md`.
2. Confirm the Governance layer subsection links to `docs/host-surface-parity.md`.
3. Confirm that file now exists (T020 created it).
4. No edits required if both are true; if the link is missing, re-add it.

### T023 — Parity-coverage test

**Purpose**: Enforce FR-001 / NFR-003 automatically.

**File**: `tests/specify_cli/docs/test_host_surface_inventory.py` (new).

**Test structure**:

```python
"""WP05 / FR-001 / NFR-003 — Host-surface parity matrix coverage test.

Asserts that every supported host surface from AGENT_DIRS has exactly one row
in docs/host-surface-parity.md, and that every row has a valid parity_status.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PARITY_DOC = REPO_ROOT / "docs/host-surface-parity.md"

# Pulled from src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py::AGENT_DIRS
# plus the 2 Agent Skills surfaces (codex, vibe).
EXPECTED_SURFACES = frozenset({
    "claude", "copilot", "gemini", "cursor", "qwen",
    "opencode", "windsurf", "kilocode", "auggie", "roo",
    "q", "kiro", "agent", "codex", "vibe",
})

VALID_PARITY_STATUS = {"at_parity", "partial", "missing"}


def _parse_rows() -> list[dict[str, str]]:
    """Parse the parity matrix table from docs/host-surface-parity.md."""
    content = PARITY_DOC.read_text()
    # Find the first markdown table in the doc
    lines = content.splitlines()
    in_table = False
    header: list[str] | None = None
    rows: list[dict[str, str]] = []
    for line in lines:
        if line.startswith("| surface_key"):
            header = [c.strip() for c in line.strip("|").split("|")]
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) != len(header or []):
                continue
            rows.append(dict(zip(header or [], cells)))
        elif in_table and not line.startswith("|"):
            in_table = False
    return rows


def test_parity_doc_exists() -> None:
    assert PARITY_DOC.exists(), "docs/host-surface-parity.md must exist after WP05"


def test_every_surface_has_a_row() -> None:
    rows = _parse_rows()
    present_surfaces = {row["surface_key"] for row in rows}
    missing = EXPECTED_SURFACES - present_surfaces
    assert not missing, f"Missing rows for surfaces: {sorted(missing)}"


def test_no_duplicate_surface_rows() -> None:
    rows = _parse_rows()
    keys = [row["surface_key"] for row in rows]
    dupes = {k for k in keys if keys.count(k) > 1}
    assert not dupes, f"Duplicate rows for surfaces: {sorted(dupes)}"


def test_every_row_has_valid_parity_status() -> None:
    rows = _parse_rows()
    for row in rows:
        assert row["parity_status"] in VALID_PARITY_STATUS, (
            f"Invalid parity_status for {row['surface_key']}: {row['parity_status']}"
        )


def test_every_non_parity_row_has_notes() -> None:
    """FR-006 — pointer/partial/missing rows must explain the gap in notes."""
    rows = _parse_rows()
    for row in rows:
        if row["parity_status"] != "at_parity" or row.get("guidance_style") == "pointer":
            assert row.get("notes"), (
                f"Row {row['surface_key']} (parity_status={row['parity_status']}, "
                f"guidance_style={row.get('guidance_style')}) must have a non-empty notes column."
            )
```

### T024 — Mark `#496` delivered in tracker-hygiene checklist

**Purpose**: Record the Tranche A closeout event for WP09 to execute at merge time.

**Steps**:
1. Create or open `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/artifacts/tracker-hygiene.md` (WP09 owns this file; WP05 writes into it as a dependency producer).

**Ownership note**: WP09 owns `tracker-hygiene.md`. WP05 appending to it creates a cross-WP write. Resolution: WP05 does NOT write to the WP09-owned file directly. Instead, WP05 records "Tranche A closed — close `#496` on merge" in its PR description / commit message. WP09 reads the Tranche A state from git history and from the inventory matrix when it runs.

**Revised T024 action**: include a note in WP05's commit message: "Closes #496 on merge (Tranche A scope delivered per mission plan)." GitHub's `Closes #N` semantics auto-close on merge to main. WP09 verifies the auto-close actually happened.

### T025 — Merge-ready signal

**Purpose**: Confirm all Tranche A tests are green before declaring Tranche A ready.

**Steps**:
1. Run the full Tranche A test suite:
   ```bash
   pytest tests/specify_cli/dashboard/test_dashboard_wording.py \
          tests/specify_cli/docs/test_readme_governance.py \
          tests/specify_cli/docs/test_host_surface_inventory.py -v
   ```
2. Confirm all tests pass.
3. Record the test run outcome in the WP's completion commit message.
4. If any test fails, do not mark WP05 done — return to the failing WP and resolve.

## Definition of Done

- [ ] `docs/host-surface-parity.md` exists with preamble + full matrix.
- [ ] `tests/specify_cli/docs/test_host_surface_inventory.py` exists and all 5 test cases pass.
- [ ] README's forward link to `docs/host-surface-parity.md` resolves.
- [ ] T021 deferral to WP08 is recorded in the PR description.
- [ ] Commit message includes `Closes #496` on the merge commit.
- [ ] Full Tranche A test suite (WP02 + WP03 + WP05 tests) runs green.

## Risks

- **Ownership scuffle on `docs/trail-model.md`**: documented above — T021 is deferred to WP08. If the implementer forgets and edits `docs/trail-model.md` from WP05, `finalize-tasks --validate-only` will flag an ownership collision.
- **`AGENT_DIRS` drift**: if the `AGENT_DIRS` constant is updated in some future WP before WP05 runs, `EXPECTED_SURFACES` in T023's test may go stale. Mitigation: add a comment in the test file pointing to the source-of-truth module; update the test in sync with any future `AGENT_DIRS` change.
- **Parser brittleness**: `_parse_rows()` in T023 is a simple markdown-table parser that assumes the table format. If the preamble accidentally contains a leading `|` line, the parser may mis-identify the start of the table. Mitigation: anchor on the specific header `| surface_key |`.

## Reviewer Guidance

Reviewer should:
- Diff `docs/host-surface-parity.md` against `kitty-specs/.../artifacts/host-surface-inventory.md` — the matrix body should match post-promotion; the preamble is new.
- Run the 5 tests in `test_host_surface_inventory.py` manually and confirm pass.
- Confirm the commit message has `Closes #496`.
- Confirm WP05 did NOT touch `docs/trail-model.md`.
- Confirm Tranche A is fully closed: every Tranche A WP (WP01–WP05) is in `done` / `approved` state and all tests pass.

## Activity Log

- 2026-04-23T05:49:10Z – claude:sonnet-4-6:implementer:implementer – shell_pid=18311 – Started implementation via action command
- 2026-04-23T05:52:57Z – claude:sonnet-4-6:implementer:implementer – shell_pid=18311 – Tranche A closeout: parity matrix promoted to docs/host-surface-parity.md; coverage test green; Tranche A test suite green (17+6+5=28 total, 27 passed + 1 xpassed). T021 deferred to WP08. kitty-specs inventory left unchanged (validator constraint).
