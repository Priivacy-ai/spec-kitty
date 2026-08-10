---
work_package_id: WP01
title: Acceptance & verification harness (red-first)
dependencies: []
requirement_refs:
- C-001
- C-003
- C-004
- NFR-001
- NFR-002
- NFR-003
- NFR-004
planning_base_branch: feat/egress-single-authority
merge_target_branch: feat/egress-single-authority
branch_strategy: Planning artifacts for this mission were generated on feat/egress-single-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/egress-single-authority unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
history:
- at: '2026-08-10T08:22:23Z'
  actor: claude
  note: authored by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/sync/tracker/
create_intent:
- tests/sync/tracker/test_egress_single_authority.py
execution_mode: code_change
owned_files:
- tests/sync/tracker/test_egress_single_authority.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile: `/ad-hoc-profile-load python-pedro`. It sets your implementer identity, boundaries, and governance scope for this work package.

## Objective

Land the mission's **acceptance harness** — the tests that define "done" — in a new file `tests/sync/tracker/test_egress_single_authority.py`, and capture the **pre-change golden references** those tests compare against. This is ATDD: the suite must be **red** on the current tree and go green only after WP03. Do **not** change any product code.

## Context (read these first)

- `kitty-specs/egress-single-authority-01KZN7CB/spec.md` — FR/NFR/C + SC-001..SC-005.
- `.../quickstart.md` — the exact checks this WP encodes (SC-001..SC-005, NFR-003, C-003/C-004).
- `.../data-model.md` — the `EgressConsent` split, the `channel1_state` total mapping, and `EgressDecision`.
- Current code: `src/specify_cli/tracker/egress_verdict.py`, `src/specify_cli/invocation/adapters.py`, `src/specify_cli/egress.py`, `src/specify_cli/sync/__init__.py`, `tests/sync/tracker/test_tracker_egress_verdict_3108.py` (the existing `#3108` harness this complements).

**Marker convention**: this new file MUST declare a module `pytestmark` consistent with the sibling suites (it spawns subprocesses / touches sqlite → `pytest.mark.integration`, not `unit`/`fast`). Verify against the marker-correctness gate before finishing.

## Subtasks

### T001 — Enforcement-equivalence matrix (SC-001 / NFR-001)
Parametrize over **`granted` + each consent precedence level (project-local / machine-index / env) + the three refusal states (`no_record`/`recorded_refusal`/`not_consentable`)** × the Channel-2 value set × `LOCAL_SUBPROCESS`/`HOSTED_SERVICE`. For each cell assert the verdict's `refused` and `refusing_channels` equal a **captured golden** from the current tree, and that **no previously-refused cell permits**. Capture the golden now (it is the pre-change behaviour). This is the C-001 safety net — the permit row is mandatory.

### T002 — Hosted byte-identity + saas_client (SC-002 / NFR-002 / FR-004) `[P]`
Assert the `HOSTED_SERVICE` Channel-1 refusal message is byte-identical across the three refusal states and to the shipped string (0-byte diff). Separately assert `saas_client/client.py`'s `SaasConsentError(project_egress_refusal(...))` string is byte-identical — it is **not** covered by the `HOSTED_SERVICE` pin.

### T003 — One-resolution count (SC-003 / NFR-004) `[P]`
Spy/patch `resolve_checkout_sync_routing_readonly` and `resolve_project_consent`; drive one gated verdict; assert **exactly one** call to each. (Red now — the current tree calls each twice.)

### T004 — NFR-003 fail-closed enumeration `[P]`
Enumerate each degraded resolver return — bare `bool`, `None`, an unrecognized value, and a resolver-import-failure — driven through the `OUTCOME_DEFER` branch. Assert each: **refuses**, renders **generic** wording, and raises **nothing** at any `permits_egress` sink (incl. `propagator`). Inject degraded returns via `register_egress_consent_resolver` / the `sys.modules` blocker. (Red now not because of a `KeyError` — the composer already checks `generic` first — but because today the degraded *enforcing* return does not drive `channel1_state`; the independent classifier does. Goes green when WP03 sources the state from the single authority.)

### T005 — C-004 no-local-import + C-001 members + root-is-None `[P]`
- Assert `egress.py` contains **no** `import sync.consent`/`sync.routing` (parse imports, not substring). (Green now; guards against relocation in WP02.)
- Assert every `EgressConsent` member except `GRANTED` answers `permits_egress is False` (iterate all members). (Red now — the split members don't exist yet.)
- Assert `undetermined` is produced for `root is None`.

### T006 — sync doctor parity + degraded golden + symbol-absence (SC-005 / SC-004) `[P]`
Capture the pre-change `sync doctor` per-destination Channel-1 state/remedy as the golden for `granted` + the three refusal states, and separately capture the pre-change degraded reported-state (today import-failure masquerades as `no_record`) as an **intended-change** golden. **Capture surface (U1):** snapshot the `sync doctor` **renderer** over a per-destination row (the same surface `tests/cli/commands/test_sync_doctor_tracker_egress_3108.py` drives — the verdict-reading renderer, not a full `spec-kitty` subprocess), so the golden is the rendered state/remedy string per destination. Assert `_classify_channel1` is absent from `src/` (red now — it still exists).

## Branch Strategy

Planning/base branch: `feat/egress-single-authority`. Final merge target: `feat/egress-single-authority`. Execution worktrees are allocated per computed lane from `lanes.json` after finalize-tasks; enter the workspace `spec-kitty implement WP01` resolves.

## Definition of Done

- New file `tests/sync/tracker/test_egress_single_authority.py` with a correct `pytestmark`, joined to any completeness/marker baselines.
- All six subtasks encoded; suite collects cleanly. Distinguish the two kinds of check:
  - **Invariance guards — green throughout** (before AND after): T001 (enforcement unchanged vs golden), T002 (byte-identity), T005 no-local-import, T005 root-is-None. These certify nothing regressed; do not write them red-first.
  - **Behavior-change cells — red now, green only after WP03**: T003 (one resolution — currently two), T004 (degraded state drives `channel1_state` from the single authority — currently the independent classifier does), T005 iterate-members (the split members don't exist yet), T006 (`_classify_channel1` absent; degraded reported-state improvement).
- Golden references captured in-test (not hand-typed) so they reflect the true pre-change behaviour.
- `ruff` clean; no product-code edits.

## Reviewer guidance

Confirm the matrix includes the **permit** row and precedence levels; confirm goldens are captured from the live pre-change path (not asserted as literals a green-before-and-after test would pass); confirm the file's marker is `integration` and it joins the marker baseline.
