# Data Model: Write-Side Seam: Matrix & Tracer Writers

Phase 1 output. Entities, schemas, invariants, and state for the structured matrices, the tracer finding, and the write-routing surfaces.

## Entity: Acceptance-matrix (`acceptance-matrix.json`) — existing, formalized

- **Partition**: COORD (`_PLACEMENT_ARTIFACT_KINDS`).
- **Shape**: a set of criteria rows, each `{criterion_id, requirement_ref, verification_method, result, evidence?}`, plus negative-invariant provenance.
- **Computed**: `overall_verdict` is a computed `@property` (`pass` | `pending` | `fail` | `pass_pending_consolidation`). Serialized via `to_dict`; **excluded from `from_dict` round-trip** — never hand-stored.
- **Invariants**:
  - I-A1: `overall_verdict` is always derived from criteria + invariants, never authored.
  - I-A2: Canonical acceptance of an all-`pass`/no-negative-invariant matrix MUST persist `overall_verdict: "pass"` (FR-001; today `_evaluate_acceptance_matrix` only writes on negative-invariants → stale `pending`).
  - I-A3: A verdict write preserves existing negative-invariant provenance (#2743).
- **Write path**: `write_target(ACCEPTANCE_MATRIX)` → `commit_for_mission`.

## Entity: Issue-matrix (`issue-matrix.json`) — NEW structured artifact

- **Partition**: COORD.
- **Migration**: replaces `issue-matrix.md` (markdown). **No markdown render** is emitted (D-2). Back-compat via failover-read + migrate-on-write (D-3, FR-013).
- **Schema** (as-built WP05 — reconciled from the earlier `status` sketch to the canonical `IssueMatrixVerdict` vocabulary; see note below):
  ```json
  {
    "schema_version": 1,
    "mission_id": "01K…",
    "rows": {
      "#1726": {
        "issue_ref": "#1726",
        "sources": ["tasks/WP01.md", "tasks/WP02.md"],
        "verdict": "fixed|verified-already-fixed|deferred-with-followup|in-mission",
        "wp_refs": ["WP01"],
        "evidence_ref": null
      }
    }
  }
  ```
- **Vocabulary decision (WP05, reviewer-confirmed):** rows carry **`verdict`/`evidence_ref`** reusing the existing closed-set `IssueMatrixVerdict` (`fixed` | `verified-already-fixed` | `deferred-with-followup` | `in-mission`), **not** a parallel `status: open|addressed|not_applicable|verified` set. Load-bearing reason: the approval-gate consumer `tasks_parsing_validation.py:116` does an **`is` identity check** against `IssueMatrixVerdict.IN_MISSION` — a free-form string would silently never match, defeating the "unresolved in-mission blocks at done" gate; and it keeps ONE vocabulary for the concept the coord matrix + approve gate already use (unification-not-parity). The scaffold placeholder `unknown` is a non-member sentinel (excluded from `.rows`, surfaced as `ISSUE_MATRIX_VERDICT_UNKNOWN`). **`rows` is object-keyed by `issue_ref`** (not an array). **WP07 (`issue-verdict`) MUST use `--verdict`/`evidence_ref`.**
- **Row identity**: `issue_ref` (canonical, deduped) — the stable key the row-aware merge driver unions on.
- **Invariants**:
  - I-I1: rows are keyed by `issue_ref`; discovery scans `spec.md`+`tasks/`+`plan.md`+`research.md`+`analysis-report.md`+`contracts/` (FR-004).
  - I-I2: a mission whose canonical spec declares **zero** issue references records Gate 4 `not_applicable`; no matrix is fabricated (FR-005/#3035).
  - I-I3: the canonical-reference definition is shared across finalization, approval, merge, and review (one definition, not four).
- **Write path**: `write_target(ISSUE_MATRIX)` → `commit_for_mission`.

## Entity: Tracer finding entry (`traces/*.md`) — writer is the one genuine build

- **Partition**: COORD (`TRACER_FILE`).
- **Shape**: dated, actor-attributed entry appended to a category file (`tooling-friction.md` / `approach.md` / `design-decisions.md`).
- **Invariants**:
  - I-T1: a lane-origin append routes to the coord surface via `commit_for_mission` — **zero** `kitty-specs/` commits on the lane branch (FR-006).
  - I-T2: attribution (`actor`) is non-empty and preserved (guard #2960).
  - I-T3: identical content re-append is a no-op (FR-012 idempotency).
  - I-T4: the writer must NOT use the `read_dir(RETROSPECTIVE)` short-circuit — it calls the leaf/`write_target` directly (Ledger-M16 recursion guard).

## Entity: Write-routing result (structured command output)

- **Shape**: `{ok, kind, destination_surface: "coord"|"primary", row_or_entry_ref, migrated?: bool, refusal?: {reason, deferred_to: "#3033"}}`.
- **Invariants**:
  - I-W1: idempotent — re-run with identical inputs = no-op (FR-012).
  - I-W2: unroutable (deleted `target_branch`/missing coord/unknown target) → structured **zero-write refusal** disclosing #3033 (FR-011); never a fallback write, never a consolidation abort.

## Entity: Execution lane base (FR-009)

- **State**: lane branch base ref = the **recorded** planning-artifact commit (finalize-tasks tip in `lanes.json`/`meta.json`), not the coord tip nor a moving `target_branch` tip.
- **Invariants**:
  - I-L1: a lane shares a common ancestor containing planning artifacts with the consolidation base (SC-003; #2993).
  - I-L2: dependent-lane visibility (#1684) is preserved (achieved by merging dep tips, not by a shared root).
  - I-L3: no consolidation-time abort path is added (ADR `2026-07-23-2`).

## Merge-driver model (FR-008)

- **Row-aware union**: for `acceptance-matrix.json` / `issue-matrix.json`, merge unions rows by stable key (criterion_id / issue_ref); per-row conflicts resolve by the richer/newer side; disjoint rows both survive (no clobber). Replaces `_write_more_filled_side`.
- **`traces` / `event-log`** drivers remain line/entry unions (unchanged).
