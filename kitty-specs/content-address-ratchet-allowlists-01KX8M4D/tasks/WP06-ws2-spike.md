---
work_package_id: WP06
title: IC-WS2-SPIKE — relocation-proof key + carve checkpoint
dependencies: []
requirement_refs:
- FR-007
- FR-008
- FR-009
tracker_refs: []
planning_base_branch: analysis/test-change-coupling
merge_target_branch: analysis/test-change-coupling
branch_strategy: Planning artifacts for this mission were generated on analysis/test-change-coupling. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into analysis/test-change-coupling unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1712622"
history:
- created at planning (tasks) — WS2 design spike + carve checkpoint
agent_profile: python-pedro
authoritative_surface: tests/
create_intent:
- tests/architectural/_symbol_identity.py
- tests/unit/test_symbol_identity_spike.py
execution_mode: code_change
model: sonnet
owned_files:
- tests/architectural/_symbol_identity.py
- tests/unit/test_symbol_identity_spike.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load python-pedro` (role: implementer). Read [spec.md](../spec.md)
§WS2 + C-004/C-005, [research.md](../research.md) D-4/D-5/D-6, and the plan's WS2
tripwire ruling. **This is a design SPIKE, gated LAST — it MUST NOT gate WS1/WS3
merge, and it MUST NOT bulk-migrate the 343-entry allow-list.** It ends with a
carve/continue decision.

## Objective
Prototype a relocation-proof symbol identity for the dead-symbol allow-list that
forbids bare-name-alone (preserving T004 no-false-negative), prove it against the
real same-name fixtures, run a body-hash stability probe, and produce an explicit
carve/continue recommendation — WITHOUT touching `test_no_dead_symbols.py`'s 343
entries yet.

## Why a spike (C-004 / C-005)
`composite_key` is relocation-*tolerant* but the dead-symbol gate keys on
`module::Name` (net-new key needed). vulture is disqualified (treats `__all__` as
used). Bare-name-alone re-blinds T004 (`ArtifactKind`×3 etc. exist across modules).
This is the mission's design-risk concentration — de-risk it before committing to
the 343-entry migration.

## Subtasks

### T025 — Prototype the key (NEW `tests/architectural/_symbol_identity.py`)
**LOCATION (post-tasks squad — avoids two CI-red traps):** the spike helper lives at
`tests/architectural/_symbol_identity.py` — a `_`-prefixed, **non-collected**,
**non-`src/`** module (exactly like `_ratchet_keys.py`). Do NOT put it under `src/`:
a `src/` module imported only by a test would RED `test_no_dead_modules` (zero
non-test callers, not allowlisted), and WP06 owns none of the gate files to wire
out. This is a throwaway design spike (may carve to #2546) — it must not ship in
`src/`. Its spike test lives at `tests/unit/test_symbol_identity_spike.py` (outside
the arch pole roots → **no `_arch_shard_map.py` entry, no WP05 dependency**);
`pytestmark = [pytest.mark.unit]`.
Design a relocation-tolerant key that FORBIDS bare-name-alone: bare name PLUS a
module/body disambiguator. A pure move (same name + body, new module) → same key;
two distinct same-named symbols → distinct keys. **S3776 (squad):** isolate the
body-hash normalization into its own helper — reuse `anchoring.code_tokens_by_line`'s
interpreter-independence (3.11↔3.12) rather than fork a second normalizer.

### T026 — T004 no-false-negative fixtures
Wire the real same-name fixtures: `ArtifactKind` in `doctrine.directives` /
`doctrine.procedures` / `doctrine.tactics`; `GateDecision`×2; `ResolutionResult` /
`ResolutionTier`×2. Prove: marking one dead while its sibling is sanctioned →
the dead one is STILL caught (no re-blinding). This is the load-bearing proof.

### T027 — Body-hash stability probe
"Unstable body-hash" = any drift under (a) the NFR-001 motion battery (blank/comment
insertion, whitespace) or (b) the 3.11↔3.12 `code_tokens_by_line` normalization
(the same interpreter-independence the substrate already guards). Measure it.

### T028 — Carve/continue checkpoint (decision gate)
Write an explicit recommendation: **continue in-mission** OR **carve to standalone
#2546**. Carve if: the key needs >2 implementation WPs (design + 343-migration +
categories/modules is already 3), OR the body-hash is unstable per T027. The
implementer proposes; the **operator confirms** before any bulk migration. Do NOT
migrate `test_no_dead_symbols.py` in this WP. If continue, the bulk migration
(FR-008 auto-derived categories: registered symbol only, ~96 `m_*.py`; FR-009
`test_no_dead_modules` preservation) is authored as a follow-on; if carve, it seeds
#2546 (pre-wired in issue-matrix).

## Branch Strategy
Planning/merge branch `analysis/test-change-coupling`; worktree per `lanes.json`
via `spec-kitty agent action implement WP06 --agent <you>`. No hard dependency on
other WPs; sequenced last so a carve leaves WS1/WS3/WP05 fully shippable.

## Definition of Done
- `contracts/symbol_identity.py` prototype: relocation-proof, no bare-name-alone.
- T004 fixtures prove no re-blinding; body-hash stability measured.
- A written carve/continue recommendation (operator confirms). `test_no_dead_symbols.py`
  is UNTOUCHED. Full `tests/architectural/` 869/0.

## Reviewer guidance
Confirm the key is NOT bare-name-alone and the T004 fixtures still catch a dead
same-name symbol. Confirm the WP did NOT bulk-migrate (spike only). Sanity-check the
carve/continue reasoning against the C-004 tripwire.

## Activity Log

- 2026-07-11T16:37:03Z – claude:sonnet:python-pedro:implementer – shell_pid=1623588 – Assigned agent via action command
- 2026-07-11T16:58:57Z – claude:sonnet:python-pedro:implementer – shell_pid=1623588 – Ready (SPIKE): relocation-proof key prototype + T004 no-false-negative proof; carve/continue recommendation = CARVE (key needs >2 impl WPs: two-tier candidate A/B + facade-dict detector before the 343-entry migration + FR-008 categories; body-hash itself STABLE under motion battery + 3.11/3.12 f-string probe); test_no_dead_symbols.py untouched.
- 2026-07-11T17:02:33Z – claude:opus:reviewer-renata:reviewer – shell_pid=1712622 – Started review via action command
