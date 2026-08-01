---
work_package_id: WP04
title: 'The tests/sync/ process-global and thread-seam inventory'
dependencies:
- WP01
requirement_refs:
- FR-006
planning_base_branch: feat/verification-trust-3115
merge_target_branch: feat/verification-trust-3115
branch_strategy: Planning artifacts for this mission were generated on feat/verification-trust-3115. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verification-trust-3115 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-verification-trust-3115-01KYVYWM
base_commit: d8d0ad7eff9ddeb14e154afd82450cf2dfd5472d
created_at: '2026-07-31T12:00:00+00:00'
subtasks:
- T013
- T014
- T015
history: []
authoritative_surface: docs/development/
execution_mode: code_change
owned_files:
- docs/development/process-global-inventory-3115.md
- docs/development/toc.yml
- docs/development/3-2-page-inventory.yaml
- docs/development/3-2-docs-retrieval-index.yaml
create_intent:
- docs/development/process-global-inventory-3115.md
tags: []
tracker_refs: []
---

# WP04 — The `tests/sync/` process-global inventory

**This is the map, not the answer.** It needs no culprit and **survives a failed hunt**: WP05's leak
guard is scoped to it, and WP14's outcome-B deferral inherits it.

**Blocked by WP01 — and the reason is a docs artefact, not the inventory.** WP01 appends a section
(a `##` heading) to `docs/development/testing-parallel.md`, and
`docs/development/3-2-docs-retrieval-index.yaml` is regenerated from **body headings**
(`scripts/docs/docs_index.py:93` `scan_headings`, level-2/3 ATX). WP01's heading therefore *drifts the
retrieval index*, and so does WP04's new page. Both must be regenerated, and there is one owner. The
dependency edge exists so **WP01's heading lands before WP04 regenerates — one regeneration, after
both changes.** Without it, WP04 regenerates in `parallel_group` 0 and WP01's heading arrives
afterwards, leaving `DOCS-INDEX-DRIFT` on the branch with nobody left who may fix it.

## Why it lands outside `kitty-specs/`

`src/specify_cli/policy/commit_guard.py:84-89` **refuses any staged path under `kitty-specs/` from an
implementation branch** (C-010). The artefact therefore lives at
`docs/development/process-global-inventory-3115.md`. Narrative evidence is folded into `notes/` **by
the orchestrator on the mission branch**, never by a lane.

## Why the docs plumbing is owned here — all **four** files

`docs/development/3-2-page-inventory.yaml` is a **generated lockfile**
(`scripts/docs/inventory_lockfile.py`, ADR 2026-06-27-1 D1) guarded by
`tests/docs/test_inventory_path_stable.py`, and `docs/development/toc.yml` is the nav. A new page needs
frontmatter (`title` / `description` / `doc_status` / `updated` / `type` / `related`, per
`docs/development/testing-parallel.md:1-13`), a `toc.yml` entry and a **lockfile regeneration**.

**`docs/development/3-2-docs-retrieval-index.yaml` is the third generated artefact, added post-tasks.**
Nothing in the dossier named it before, and its drift is an **error**, not a warning:
`_check_docs_index_drift` (`scripts/docs/check_docs_freshness.py:767-812`) regenerates the index from
`docs/**/*.md` frontmatter **and body headings** and emits `DOCS-INDEX-DRIFT` at `severity="error"` on
any added / removed / changed row. Its sibling `_check_page_inventory_completeness` (`:669-697`) emits
`INVENTORY-INCOMPLETE`, also `severity="error"`. **Both run on every PR** as blocking steps of
`.github/workflows/docs-freshness.yml`.

**Two changes in this mission drift the retrieval index**: WP04's new page (a new row), and **WP01's
appended `##` section** in `docs/development/testing-parallel.md` (a changed `anchors` row — the index
is built from `scan_headings`, `scripts/docs/docs_index.py:93`, over level-2/3 ATX headings). That is
why WP04 is **blocked by WP01**: one owner, one regeneration, taken **after both changes have landed**.

**WP04 is the only WP adding a page, so it owns all four.** **WP01 appends a section to an existing
page and owns none of the four** — it does not touch the nav or either generated artefact; its heading
is simply picked up by WP04's regeneration (R7, extended).

## Definition of done — measurable evidence

### T013 — scope and the four mandatory values

Scope is the **`tests/sync/` cone only**. The CLI cone is **excluded** — its failure has a measured
non-global cause (render width), and re-opening it here would re-derive a settled answer.

Each entry carries **four mandatory values**:

1. **module and symbol**;
2. `reset seam: <name>` / `no reset seam` / `not reachable`;
3. **who calls that seam**, or `nobody`;
4. whether `tests/sync/tracker/test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after`'s
   outcome **depends** on it — `depends` / `does not depend` / `undetermined`, **with the evidence**.

**Process-global**, for this inventory, means module-level mutable state whose lifetime is the worker
process: singletons, registries, caches, import-time-bound paths, memo sets, **live threads**,
`os.environ`, and the CWD.

### T014 — counts, or the deliverable is closable without doing the work

- The **count of modules scanned** is stated.
- A **per-bucket count** is given for each of the four values — e.g. *"31 modules scanned; 12 `no reset
  seam`; 4 `depends`; 9 `undetermined`"*.
- **A grep-shaped deliverable with no dependence column does not close this WP** (H7). The dependence
  column is the one that cannot be produced by pattern-matching, and it is the one WP05 and WP06
  consume.
- **NFR-008**: printing an input count beside any "all checks passed" is the whole point here — a gate
  that ran on zero inputs passes vacuously.

### T015 — docs plumbing

- Frontmatter on the new page, matching `docs/development/testing-parallel.md:1-13` — including
  `doc_status` and `updated` (`tests/docs/test_docs_structural_lint.py:144`,
  `frontmatter_required_fields=("doc_status", "updated")`), a `description:` within the length gate
  (`scripts/docs/description_length_check.py --strict`) and `related:` edges that resolve
  (`scripts/docs/related_validator.py --strict`).
- A `docs/development/toc.yml` nav entry.
- `docs/development/3-2-page-inventory.yaml` **regenerated by `scripts/docs/inventory_lockfile.py`** —
  it has 686 entries and is a **generated lockfile, never hand-edited**.
- **`docs/development/3-2-docs-retrieval-index.yaml` regenerated**, with:

  ```
  PYTHONPATH=. uv run python scripts/docs/docs_index.py --write
  ```

  the command `_docs_index_finding` itself names as the remedy. **Taken after WP01's section has
  landed in `docs/development/testing-parallel.md`**, so one regeneration covers both changes.
- **Both regenerations are verified, not assumed**, by re-running the ruler read-only:

  ```
  PYTHONPATH=. uv run python scripts/docs/check_docs_freshness.py --report freshness.json --link-check none
  ```

  and quoting that neither `INVENTORY-INCOMPLETE` nor `DOCS-INDEX-DRIFT` appears. **NFR-008**: quote
  the number of pages the run checked beside the "no findings" claim — a ruler that walked zero pages
  passes vacuously, which is this mission's entire subject.

### Cross-cutting

**NFR-009**: merge the mission branch into the worktree before the first measurement; state the commit
and merge-base. **NFR-004**: do not run `tests/sync` and `tests/cli` sessions concurrently on one
machine — 16 recorded false reds.

## Known candidate surfaces, so they are not re-derived

The leaked-thread hypothesis points at `src/specify_cli/sync/daemon.py` — threads started at `:587`,
`:767` and `:828`; sleep loops at `:584` and `:1382`. It does **not** point at
`SaaSTrackerClient._poll_operation`, which nothing in the tree threads. `src/specify_cli/sync/daemon.py`
and `src/specify_cli/tracker/saas_client.py` are **read-only** for this WP.

The mission's designated control case — `tests/specify_cli/invocation/test_propagator_consent_gate_3030.py`'s
`wiring` fixture, the known `reset_adapters()` leak — is outside the `tests/sync/` cone but is the
answer WP05's guard is validated against. Record it in the inventory as a **cross-cone reference**, not
as an in-scope entry.

## Files other agents hold

`tests/sync/conftest.py` and `tests/sync/test_leak_guard_probe_3115.py` are **WP05's**.
`tests/sync/tracker/test_saas_client.py` is **WP06's, then WP14's**.
`tests/sync/test_sync_consent_default_deny.py` is **WP09's**.
`docs/development/testing-parallel.md` is **WP01's** — this WP adds a *new* page and **does not edit
that file**, but it **does** pick up WP01's new heading when it regenerates the retrieval index, which
is why the dependency edge exists. `scripts/verify_shard_3115.sh` is **WP13's** — WP13 no longer adds a
page under `docs/`, so no other WP in this mission can drift the nav or either generated artefact.
`src/**` is nobody's.
