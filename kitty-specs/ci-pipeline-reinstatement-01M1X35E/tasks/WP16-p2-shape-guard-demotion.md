---
work_package_id: WP16
title: P2 shape-guard demotion + committed membership
dependencies:
- WP09
requirement_refs:
- C-007
- FR-014
- NFR-007
planning_base_branch: feat/ci-pipeline-reinstatement
merge_target_branch: feat/ci-pipeline-reinstatement
branch_strategy: Planning artifacts for this mission were generated on feat/ci-pipeline-reinstatement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-pipeline-reinstatement unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-ci-pipeline-reinstatement-01M1X35E
base_commit: 28a49aa2aaa50bf94534e258accb9d3bfed231b1
created_at: '2026-09-07T15:15:28.628443+00:00'
subtasks:
- T082
- T083
- T084
- T085
- T086
- T087
history:
- at: '2026-09-07T00:00:00Z'
  actor: planner-priti
  action: created
agent_profile: python-pedro
authoritative_surface: tests/architectural/shape_guard_membership.yaml
create_intent:
- tests/architectural/shape_guard_membership.yaml
- tests/architectural/test_shape_guard_membership.py
execution_mode: code_change
owned_files:
- tests/architectural/test_golden_count_ban.py
- tests/specify_cli/regression/test_twelve_agent_parity.py
- tests/architectural/shape_guard_membership.yaml
- tests/architectural/test_shape_guard_membership.py
role: implementer
tags: []
tracker_refs:
- '#3458'
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load <profile>` (role:
implementer) before anything else. Then read `plan.md` (LEAN-SUITE L2),
`work/ci-reinstatement/PARAMOUNT-constraints.md` §P2 (the CRITICAL distinction),
`spec.md` FR-014 + C-007 + NFR-007 + US7 scenario 3, `data-model.md` E4, and the
charter §"ATDD-First".

**Cluster gate:** claim after WP09 (live pipeline) is approved/done.

## Objective

Demote the **low-ROI shape guards** (golden-count `len==N`, export-count, twelve-agent
byte-parity) **off the blocking gate** — convert to a behavior/content check or derive
the expectation from the `src` SSOT — and commit a **machine-checkable
allowlist-vs-shape-guard membership** (E4) so relabeling cannot game the partition in
either direction. Evidence: #3458 (golden-count = 0 catches, 2 forced annotations).

**CRITICAL boundary (C-007):** the **enforcement allowlists**
(`test_no_dead_symbols`/`test_no_retired_subsystems`/`test_no_dead_modules`/
`test_integration_boundary`) are NOT shape guards — they catch real defects and stay
**always-on**. Never demote them. The membership list makes this partition explicit.

## Subtask guidance

### T082 — Red-first: `test_shape_guard_membership.py` (SEPARATE first commit)

As your **first commit**, author `tests/architectural/test_shape_guard_membership.py`
asserting: every test in the committed membership has exactly one class
(`enforcement-allowlist` | `shape-guard` | `behavioral`); `enforcement-allowlist`
members are on the blocking gate; `shape-guard` members are **off** it; and a test
cannot be silently **relabeled** to move on/off the gate (assert against a canonical
source, not free text). Run against base: red for the right reason (membership file
absent).

### T083 — Commit the membership

Create `tests/architectural/shape_guard_membership.yaml` (E4): `test_id → class`. Seed
it with the enforcement allowlists (always-on), the demotion targets (shape-guards),
and the behavioral tests. This is the committed, machine-checkable partition.

### T084 — Demote `test_golden_count_ban.py`

Demote the golden-count `len==N` cardinality bans off the blocking gate: convert to a
content/behavior check or derive the count from the `src` SSOT, or mark advisory. The
existing 313 annotated asserts should no longer force per-PR churn on a benign symbol
add. Keep the file (it may still carry advisory value), but off the gate.

### T085 — Derive twelve-agent parity from source

Rework `tests/specify_cli/regression/test_twelve_agent_parity.py` to **derive** the
twelve-agent expectation from source (the test's own docstring TODO proposes exactly
this) + one canonical snapshot + structural invariants — instead of a byte-for-byte
frozen grid + `AGENT_DIRS` re-enumeration. This removes the ~20-file re-enumeration toll
while keeping a real structural check.

### T086 — Assert enforcement allowlists out of demotion scope

Assert (in the membership test) that the enforcement allowlists are classed
`enforcement-allowlist` and remain on the blocking gate — the C-007 partition. This is
the guard against gutting P1's enforcement while demoting shape guards.

### T087 — Prove benign-symbol-add doesn't red on shape (NFR-007)

Add a proof: a benign symbol addition (the classic golden-count trigger) does not red
CI on shape alone (NFR-007). This closes #3458 — record the resolution for the issue
matrix.

## Branch Strategy

- Base/target: `feat/ci-pipeline-reinstatement`; worktree via `spec-kitty implement WP16`.
- Depends on WP09 — claim after approved/done.
- Commit order: **T082 red-first FIRST**, then T083–T087.

## Definition of Done

- T082 red on base (evidence captured), green on final.
- `shape_guard_membership.yaml` is committed and machine-checkable; relabeling cannot
  move a test on/off the gate.
- `test_golden_count_ban.py` cardinality bans + twelve-agent parity are off the
  blocking gate (converted/derived); enforcement allowlists proven always-on.
- A benign symbol-add does not red on shape (NFR-007); #3458 recorded.
- **Targeted test surface**: `pytest tests/architectural/test_shape_guard_membership.py tests/architectural/test_golden_count_ban.py tests/specify_cli/regression/test_twelve_agent_parity.py -q`.

## Risks

- **Gutting P1 (the P2 footgun)**: a naïve "delete all whitelists" would gut the
  enforcement allowlists P1 depends on. The membership + T086 are the defense — never
  demote an `enforcement-allowlist` member.
- **Ticket assignment (DIR-012)**: assign #3458 to the HiC before/as you begin.
- **Marker/golden-count self-trip**: editing these guards can itself trip golden-count
  or marker baselines — annotate `# golden-count: cardinality-is-contract` where a count
  is genuinely a contract, or convert (memory `golden-count arch ratchets`).
- **Twelve-agent regen**: deriving from source may interact with `spec-kitty regen`
  fixtures — run regen and commit derived fixtures if a source-derived path touches
  generated agent copies.

## Reviewer guidance

- Confirm T082 red-on-base for the right reason.
- Confirm NO enforcement allowlist was demoted (open the membership; verify every
  `test_no_dead_*`/`test_no_retired_subsystems` is `enforcement-allowlist` + on-gate).
- Confirm the twelve-agent test now derives from source (not a re-frozen grid).
- Confirm the benign-symbol-add proof actually passes where it previously reds.
