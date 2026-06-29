---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: event-sync-retention-delivery-01KVYWRG
mission_id: 01KVYWRGF148VXAXDJ90MECYRR
generated_at: '2026-06-29T07:12:30.199915+00:00'
analyzer_agent: unknown
input_artifacts:
  spec.md:
    path: /Users/robert/spec-kitty-dev/spec-kitty-20260629-075047-zE1EDZ/spec-kitty/kitty-specs/event-sync-retention-delivery-01KVYWRG/spec.md
    sha256: 9483fc09f8b4c44df8872e966cea0dadf0b7af9b8445fcb2be53de66e928e989
  plan.md:
    path: /Users/robert/spec-kitty-dev/spec-kitty-20260629-075047-zE1EDZ/spec-kitty/kitty-specs/event-sync-retention-delivery-01KVYWRG/plan.md
    sha256: 81b4a84382953afde49bf4ee3477980c7aa8236642a4eab07171a209d7efd902
  tasks.md:
    path: /Users/robert/spec-kitty-dev/spec-kitty-20260629-075047-zE1EDZ/spec-kitty/kitty-specs/event-sync-retention-delivery-01KVYWRG/tasks.md
    sha256: c43cc06b534c618b2a8da3baa12bcb83a17eb599236ef550e7524368c6419d99
  charter:
    path: /Users/robert/spec-kitty-dev/spec-kitty-20260629-075047-zE1EDZ/spec-kitty/.kittify/charter/charter.md
    sha256: d393b068f20eab1bb918c2f53e669d01048f049e8b0f948ff6001fc280517c08
verdict: blocked
issue_counts:
  low: 2
  critical: 1
  high: 1
  medium: 3
  info: 0
findings:
- id: A1
  severity: critical
  category: charter
  summary: ATDD-First Discipline (binding C-011) is not encoded in any of the 12 WP prompts; every implementation WP must commit a failing-first ATDD test before implementation and the reviewer must verify red→green.
- id: A2
  severity: high
  category: charter
  summary: Identifier Safety Rules not mandated in WP01/WP04/WP10, which generate storage slugs (derived_queue_scope, url_hash, target_id) from URL/user/team input that must be ASCII-only deterministic with non-ASCII regression coverage.
- id: A3
  severity: medium
  category: charter
  summary: No WP references the authoritative CLI↔SaaS contract (../spec-kitty-saas/contracts/cli-saas-current-api.yaml); the charter requires updating it in the same change if batch/sync wire semantics change. Contract §4 claims wire-compat but no WP confirms/guards it.
- id: A4
  severity: medium
  category: coverage
  summary: NFR-001..NFR-006 are addressed in WP subtask prose but not registered as requirement_refs (the mapper is FR-only), so non-functional coverage is not machine-verifiable.
- id: A5
  severity: medium
  category: coverage
  summary: FR-012 (target-reset detection) and the deployment-identity clause of SC-004 are only partially satisfiable in MVP; full detection depends on SaaS /health metadata that C-004/plan IC-09 defer out of scope. WP04 ships advisory scaffolding only and the completion boundary is implicit.
- id: A6
  severity: low
  category: inconsistency
  summary: tasks.md introduces module files not named in plan.md Project Structure (delivery/status_report.py, delivery/retention.py, delivery/interfaces.py) — harmless decomposition refinement, undocumented in the plan.
- id: A7
  severity: low
  category: ambiguity
  summary: The operator-facing CLI surface for EventSyncConfig mode selection (command/flag name) is not pinned in spec or plan; WP09/WP12 leave it to implementation.
---

## Specification Analysis Report

**Mission**: `event-sync-retention-delivery-01KVYWRG` (#2124) · artifacts: spec.md, plan.md, tasks.md, contract, charter
**Scope**: cross-artifact consistency before implementation. Non-remediating.

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A1 | Charter | CRITICAL | charter.md:346-358 (C-011) vs tasks/WP01-WP12 | **ATDD-First** is binding for *every* implementation WP — a failing-first ATDD test must be committed as a separate commit *before* any implementation, and the reviewer verifies RED on `planning_base_branch` → GREEN on the final commit. 0/12 WP prompts mention this discipline. | Add an "ATDD-First (red→green)" requirement to each WP prompt (or the shared `task-prompt-template.md`): name the failing-first test, require it as the lane's first commit, and add the reviewer red→green checkpoint to Review Guidance. |
| A2 | Charter | HIGH | charter.md:181-185 vs WP01/WP04/WP10 | **Identifier Safety Rules**: `derived_queue_scope`, `url_hash`, `target_id`, and the migration digest derive from URL/user/team input and must be ASCII-only + deterministic (explicit `[A-Za-z0-9_]` allowlist or `re.ASCII`), with regression coverage for non-ASCII input (accented Latin + an `.isascii()` assertion). WP01/04/10 don't mandate it. | Add an identifier-safety subtask/acceptance line to WP01 (queue scope), WP04 (url_hash/target identity), WP10 (digest handling): ASCII allowlist + a non-ASCII regression test. |
| A3 | Charter | MEDIUM | charter.md:230-234 vs all WPs | The authoritative CLI↔SaaS contract `../spec-kitty-saas/contracts/cli-saas-current-api.yaml` must be updated in the same change if hosted routes/payloads/auth/websocket/sync semantics change. The TeamspaceReceiver posts to `/api/v1/events/batch/` and the batch-result semantics shift to ledger-on-success. No WP references the SaaS contract. | Confirm (per contract §4) the batch *wire* contract is unchanged; if so, add an explicit "no SaaS-contract change — wire-compatible" note to WP06. If any wire field changes, add a subtask to update `cli-saas-current-api.yaml` in the same WP. |
| A4 | Coverage | MEDIUM | spec.md NFR-001..006 vs tasks.md requirement_refs | All 6 NFRs are handled in subtask prose/tests (NFR-001 WP12; NFR-002 WP08+WP10; NFR-003 WP05; NFR-004 WP11; NFR-005 WP10; NFR-006 WP06/11/12) but none are registered as `requirement_refs` (the mapper is FR-only), so NFR coverage isn't machine-checkable. | Document an explicit NFR→WP map in tasks.md (a short table) so reviewers/acceptance can confirm NFR coverage without re-reading prose. |
| A5 | Coverage | MEDIUM | spec.md FR-012 / SC-004 / C-004; plan IC-09 | FR-012 (reset detection) and SC-004's deployment-identity clause can't be fully met in MVP — they need the SaaS `/health` metadata deferred by C-004/IC-09. WP04 ships advisory scaffolding only. The artifacts are internally consistent but the FR-012 completion boundary is implicit. | Mark FR-012 status as "Partial (advisory) — full reset-detection deferred to the IC-09 SaaS-metadata follow-on" so the in-MVP boundary is explicit. (Decision D-017 already records the scope cut.) |
| A6 | Inconsistency | LOW | plan.md Project Structure vs tasks.md WP04/WP11 | tasks introduces `delivery/status_report.py`, `delivery/retention.py`, `delivery/interfaces.py` not named in the plan's structure. Harmless refinement to keep the CLI thin and the domain seam explicit. | Either add a one-line note to plan.md's structure, or accept as a tasks-level detail. No action required to implement. |
| A7 | Ambiguity | LOW | spec.md US2 / plan IC-06 vs WP09/WP12 | The exact operator CLI surface for selecting an `EventSyncConfig` mode (e.g. `sync config <mode>` vs a flag) is unspecified. | Pin the command/flag name during WP12 wiring; ensure it honors the Terminology Canon (no `feature*`). |

### Coverage Summary (Functional Requirements)

| Requirement | Has Task? | WP(s) | Notes |
|---|---|---|---|
| FR-001 non-destructive success | ✅ | WP03, WP07 | |
| FR-002 per-target ledger | ✅ | WP04, WP05 | |
| FR-003 target-independent journal | ✅ | WP03 | |
| FR-004 dispatcher selects undelivered | ✅ | WP05, WP07 | |
| FR-005 re-drain to new target | ✅ | WP07, WP12 | |
| FR-006 EventSyncConfig modes | ✅ | WP09 | |
| FR-007 external receiver | ✅ | WP06, WP09 | |
| FR-008 stub receiver | ✅ | WP06 | |
| FR-009 status retention/delivery split | ✅ | WP11, WP12 | |
| FR-010 explicit gc/archive | ✅ | WP11, WP12 | |
| FR-011 coalescing honesty | ✅ | WP08 | |
| FR-012 target-reset detection | ⚠️ Partial | WP04 | Advisory only; full detection deferred (A5) |
| FR-013 migration of queues | ✅ | WP10 | |
| FR-014 DeliveryReceiver contract | ✅ | WP06 | |
| FR-015 terminal-failed handling | ✅ | WP05, WP07 | |
| FR-016 canonical target authority | ✅ | WP01, WP02 | |
| FR-017 capture-first durability | ✅ | WP03 | |
| FR-018 migration collision quarantine | ✅ | WP10 | |
| FR-019 machine-readable status | ✅ | WP11, WP12 | |
| NFR-001..006 | ⚠️ Prose-only | WP05/08/10/11/12 etc. | Not in requirement_refs (A4) |

### Charter Alignment Issues

- **CRITICAL — ATDD-First (C-011)**: not encoded in any WP (A1).
- **HIGH — Identifier Safety Rules**: not mandated for the new storage-slug generators (A2).
- **MEDIUM — CLI↔SaaS contract rule**: SaaS contract file not referenced by any WP (A3).
- **Satisfied**: Terminology Canon (WP12 T076 guards `feature*`); "declare targeted test surface" (all 12 WPs name a pytest path); Shared Package Boundary (`spec_kitty_events.*` consumed via public imports per plan); no-direct-push (planning on the mission branch); `__all__`/C-007 N/A (new modules are not under `src/charter/` or `src/kernel/`).

### Unmapped Tasks

None — every WP maps to ≥1 FR; no orphan tasks.

### Metrics

- **Functional requirements**: 19 · **mapped to ≥1 task**: 19 → **FR coverage 100%** (FR-012 partial-by-design)
- **Non-functional requirements**: 6 · machine-mapped via requirement_refs: 0 (prose coverage present)
- **Work packages**: 12 · **Subtasks**: 77
- **Edge cases (spec)**: 8 / 8 covered
- **Success criteria**: 11 (SC-004 partial — deployment-identity clause deferred)
- **Ambiguity findings**: 1 · **Duplication findings**: 0 · **Critical issues**: 1

### Next Actions

1. **Resolve A1 (CRITICAL) before `/spec-kitty.implement`** — add ATDD-First to the WP prompts (or the shared template). This is a binding charter gate; implementing without it produces WPs a reviewer must reject.
2. **Resolve A2 (HIGH)** — add the identifier-safety mandate + non-ASCII regression tests to WP01/WP04/WP10.
3. **Confirm A3 (MEDIUM)** — verify the batch wire contract is unchanged (contract §4) and note it in WP06, or add a `cli-saas-current-api.yaml` update subtask.
4. **A4/A5 (MEDIUM)** — add an NFR→WP map and mark FR-012 as partial/deferred in tasks.md.
5. **A6/A7 (LOW)** — optional polish; safe to implement as-is.
6. At implementation start, honor the **Tracker Ticket Assignment Rule** (assign #2124 to the HiC) and the **Pre-existing Failure Reporting Rule**.

**Verdict: blocked** (1 critical + 1 high). Recommended path: remediate A1+A2 in the WP prompts, then proceed to `/spec-kitty.implement` (or `/spec-kitty-implement-review`).
