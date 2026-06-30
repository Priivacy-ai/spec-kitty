# Tasks: Reliability Papercut Sweep

**Mission**: reliability-papercut-sweep-01KWD0V5 | **Branch**: `fix/reliability-papercut-sweep`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

7 work packages (one per Implementation Concern + 2 folded post-tasks), with disjoint file ownership. Every WP carries
a red-first regression test (NFR-001). Lane A = WP01/WP02/WP03 (WP03 depends on WP02); Lane B =
WP04/WP05 (independent). Binding: `classify_topology` AND `read_topology` stay pure (C-001).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Red-first: accept gate + merge preflight block on orphan kitty-ops debris | WP01 | | [D] |
| T002 | Add `kitty-ops/<ulid>.jsonl` arm to `is_self_bookkeeping_path` | WP01 | | [D] |
| T003 | Route accept gate (`_accept_dirty_gate`) through the shared authority | WP01 | | [D] |
| T004 | Route merge preflight through the shared authority | WP01 | | [D] |
| T005 | Extend allowlist test + assert genuine dirt still blocks | WP01 | | [D] |
| T006 | Red-first: declared-but-absent coord branch must not classify healthy `coord` | WP02 | [D] |
| T007 | Git-existence probe at backfill WRITE path (read_topology stays pure) | WP02 | | [D] |
| T008 | Reorder CoordinationBranchDeleted remediation to lead with flatten | WP02 | | [D] |
| T009 | Purity regression guard: `classify_topology` + `read_topology` unchanged | WP02 | | [D] |
| T010 | Red-first: #1890 dead-command standing regression (recommended cmd must exist) | WP03 | |
| T011 | Fix doctor coordination recovery hint (never-created → flatten; missing → real recovery) | WP03 | |
| T012 | Handle stale-behind-tip coordination worktree | WP03 | |
| T013 | Re-pin `test_doctor_coordination.py` + `test_doctor_cli_surface_golden.py` | WP03 | |
| T014 | Red-first: flat-path decision event persists ULID not slug; empty-mid8 fails closed | WP04 | [P] |
| T015 | INVERT `test_slug_fallback_when_no_mission_id` | WP04 | |
| T016 | `decision_log.py:98` — remove slug fallback, fail closed | WP04 | |
| T017 | `runtime_bridge` `_resolve_mission_ulid`/`:224`/mint — source real ULID or fail closed; empty-mid8 guard | WP04 | |
| T018 | `prompt_metadata.py:149` — remove slug-into-mission_id | WP04 | |
| T019 | Red-first: corrupt-meta read fails closed; field-absent still defaults | WP05 | [D] |
| T020 | Create shared `target_branch` read primitive (absent vs read-failure) | WP05 | | [D] |
| T021 | Convert `get_feature_target_branch` + `resolve_merge_target_branch` to thin adapters | WP05 | | [D] |
| T022 | Convert `resolve_target_branch` (git_ops) to thin adapter | WP05 | | [D] |
| T023 | Extend merge-target test + verify ~18–20 call sites behavior-stable | WP05 | | [D] |
| T024 | Red-first: byte-identical kitty-specs flagged after planning-branch rebase | WP06 | | [D] |
| T025 | Lane-hygiene guard re-checks content against the planning tip | WP06 | | [D] |
| T026 | Green + genuine-divergence still flagged (no force-count inflation) | WP06 | | [D] |
| T027 | Red-first: approve-over-coord-rejected → merge gate false-blocks | WP07 | |
| T028 | Persist approved/override artifact into the coord artifact dir | WP07 | |
| T029 | Merge gate honors coord-side approval + approval-handler wiring | WP07 | |
| T030 | Green: approve merges; genuine rejected-latest still blocks | WP07 | |
| T031 | lanes/compute.py — collapse duplicated slug-sentinel (FR-004) | WP04 | |
| T032 | merge/executor.py + status_transition.py — legacy slug sites under contract | WP04 | |

## Work Packages

### WP01 — Shared dirty-tree self-bookkeeping authority (kitty-ops) · [prompt](./tasks/WP01-dirty-tree-shared-authority.md)
- **Goal**: a `kitty-ops/<ulid>.jsonl` orphan never blocks any dirty-tree gate (record-analysis, accept, merge), while genuine mission dirt still blocks. (FR-001 / #2251)
- **Independent test**: run accept + merge preflight with only a kitty-ops orphan dirty → succeeds; add a genuine dirty file → blocks.
- **Dependencies**: none.
- **Subtasks**: T001–T005 (~5). **Est. ~220 lines.**
- **Risks**: keep match tight (segment + ULID-`.jsonl`); preserve disjoint-set G-5; converge 3 gates on one authority. Cite #2102; umbrella #1914.

### WP02 — Coord never-created classification & remediation logic · [prompt](./tasks/WP02-coord-never-created-classification.md)
- **Goal**: a declared-but-never-created `coordination_branch` is not classified healthy `coord`; remediation leads with flatten — without changing the pure SSOT. (FR-002 / #2250)
- **Independent test**: meta declaring an absent coord branch → not healthy coord + flatten-led remediation; `classify_topology`/`read_topology` unit behavior unchanged.
- **Dependencies**: none (but WP03 depends on this).
- **Subtasks**: T006–T009 (~4). **Est. ~230 lines.**
- **Risks**: C-001 binding — probe at backfill WRITE + surface_resolver, never in read/SSOT (would ripple to Lane B's runtime_bridge). Scope to lead-with-flatten, not reflog provenance. Cite #2219.

### WP03 — Doctor coordination recovery hint + #1890 guard · [prompt](./tasks/WP03-doctor-recovery-hint.md)
- **Goal**: every recommended recovery command exists and works; standing guard against the recurred #1890 dead-command; stale-behind-tip worktree handled. (FR-003 / #2240)
- **Independent test**: `doctor coordination` recommendations all resolve to real, working commands; #1890 regression stays green.
- **Dependencies**: **WP02** (shared `_coordination_doctor.py`, C-002 — sequenced).
- **Subtasks**: T010–T013 (~4). **Est. ~210 lines.**
- **Risks**: literal phantom already gone (#1890/`ecf45f52c`); residual is real recovery + the standing guard. Cite #1890; see-also #2017.

### WP04 — Canonical fail-closed mission-identity contract · [prompt](./tasks/WP04-identity-contract-fail-closed.md)
- **Goal**: `mission_id` persisted anywhere is always a ULID; absent ULID fails closed; coord-branch identity minted once (no empty-mid8). (FR-004 + FR-006 / #2138 + #2091)
- **Independent test**: flat-path decision event persists a ULID (never slug); composition with no resolvable mid8 fails closed; inverted slug test green.
- **Dependencies**: none.
- **Subtasks**: T014–T018 (~5). **Est. ~250 lines.**
- **Risks**: contract-coupled seam (do not split); flat path must SOURCE a ULID (meta/mint), not blind-delete the fallback; coord path already fail-closed. Cite #2136.

### WP05 — target_branch read primitive + thin adapters (fail-closed) · [prompt](./tasks/WP05-target-branch-primitive.md)
- **Goal**: one canonical primitive distinguishes field-absent (default) from read-failure (fail closed); the 3 readers become thin adapters with call sites unchanged. (FR-005 / #2139)
- **Independent test**: corrupt-meta read raises a structured error (no silent default); field-absent still defaults; all consumers behave unchanged.
- **Dependencies**: none.
- **Subtasks**: T019–T023 (~5). **Est. ~250 lines.**
- **Risks**: ~18–20 call sites must stay behavior-stable (C-005, not a bulk rename); 3 return types keep adapter shapes. Cite #2065.

### WP06 — Lane-hygiene guard: content-diff not commit-history · [prompt](./tasks/WP06-lane-hygiene-content-diff.md)
- **Goal**: the `kitty-specs`-on-lane guard compares by content vs the planning tip, so byte-identical files after a planning-branch rebase are not falsely flagged. (FR-007 / #2274) [folded post-tasks]
- **Independent test**: rebased lane with byte-identical `kitty-specs/` → not flagged; genuinely-divergent file → still flagged.
- **Dependencies**: none (but WP07 depends on it — shared `tasks.py`).
- **Subtasks**: T024–T026 (~3). **Est. ~150 lines.**
- **Risks**: directly affects this mission's own rebased branch; keep genuine-divergence signal. Occurrence class A3 of #2017.

### WP07 — Review-artifact coord authority (approve-over-rejected) · [prompt](./tasks/WP07-review-artifact-coord-authority.md)
- **Goal**: `move-task --to approved` over a coord-latest rejected artifact persists the approval in the coord worktree, so the merge gate no longer false-blocks with `REJECTED_REVIEW_ARTIFACT_CONFLICT`. (FR-008 / #2275) [folded post-tasks]
- **Independent test**: approve-over-rejected merges; genuine rejected-latest still blocks.
- **Dependencies**: **WP06** (shared `tasks.py`; small documented out-of-map edit to the approval handler).
- **Subtasks**: T027–T030 (~4). **Est. ~200 lines.**
- **Risks**: meatier review-artifact-authority surface (sibling #1817, epic #2160); honor #1924 override; write where the merge gate reads.

## Dependencies graph
```
WP01  (independent)
WP02 → WP03   (shared _coordination_doctor.py surface; sequenced, C-002)
WP04  (independent)
WP05  (independent)
WP06 → WP07   (shared tasks.py surface; sequenced — folded #2274/#2275)
```

## MVP / sequencing
Each WP is independently shippable behind its regression test. WP02 must merge before WP03.
Suggested first: WP01 (smallest, fully independent) or WP04/WP05 (Lane B, parallel).
