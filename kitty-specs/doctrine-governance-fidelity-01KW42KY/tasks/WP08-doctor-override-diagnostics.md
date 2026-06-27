---
work_package_id: WP08
title: Wire doctor doctrine override diagnostics
dependencies:
- WP07
requirement_refs:
- FR-010
- FR-012
tracker_refs: []
planning_base_branch: mission/doctrine-governance-fidelity
merge_target_branch: mission/doctrine-governance-fidelity
branch_strategy: Planning artifacts for this mission were generated on mission/doctrine-governance-fidelity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/doctrine-governance-fidelity unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
phase: Lane C — override-governance runtime wiring
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1035277"
history:
- at: '2026-06-27T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- tests/specify_cli/cli/commands/test_doctor_override_diagnostics.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/doctor.py
- src/specify_cli/cli/commands/_doctrine_collect.py
- tests/specify_cli/cli/commands/test_doctor_override_diagnostics.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP08 – Wire doctor doctrine override diagnostics

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` via the `/ad-hoc-profile-load` skill (read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml`) and adopt its directives before implementing.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent**: `claude`

---

## Objectives & Success Criteria

- `spec-kitty doctor doctrine` reports **unsanctioned built-in overrides** in a deployed repo: an org pack that overrides a built-in DRG node without a sanctioning `.kittify/doctrine/replaceable-builtins.yaml` entry is flagged, and the report becomes `healthy=false` (RC=1) (FR-010).
- A sanctioning allowlist entry (with a reason for directive overrides) clears the finding — not flagged, `healthy` unchanged.
- The diagnostics live in the **org-packs-present branch only**, guarded by the existing `if not registry.packs:` no-packs short-circuit — a built-in-only / no-org-packs repo is byte-identical to today (NFR-001).
- **Project-tier overrides stay intentionally ungoverned (FR-012)** — documented in the doctor output/help and a short doc note; only `org:`-provenance overrides are adjudicated.

**Done when**: a scratch repo with an unsanctioned org override → `doctor doctrine --json` flags it and `healthy=false`; with a sanctioning entry → not flagged; no org packs → unchanged; the project-tier boundary is documented; ruff + mypy clean; complexity ≤ 15.

## Context & Constraints

- **Depends on WP07** — import `find_overridden_builtin_urns`, `find_unsanctioned_overrides`, `UnsanctionedOverride` from `doctrine.drg.override_policy` (promoted there in WP07). Do NOT re-implement them.
- **The doctor seam is already half-built — reuse it, add NO new DRG plumbing (C-006):**
  - `doctor.py::doctrine_check` (≈ line 969) builds `report = _collect_profile_health(repo_root)` once, computes `exit_code = 0 if report.healthy else 1`, short-circuits on `if not registry.packs:` via `_emit_doctrine_no_packs`, then renders the org-packs-present branch through `_emit_doctrine_json` / `_emit_doctrine_human`.
  - `_doctrine_collect.py::_collect_profile_health` (≈ line 136) already loads the merged 3-layer DRG and has `repo_root`. `_collect_org_layer_data(repo_root)` (≈ line 312) ALREADY calls `merge_three_layers(built_in=..., org_fragments=fragments, project=None)` (line 363) but **discards the merged graph**. That call site is the canonical slot: capture the merged graph and adjudicate it.
  - `DoctrineHealthReport.healthy` (`_doctrine_health.py` ≈ line 110) is `bool(self.packs) and all(pack.healthy) and not self.org_drg.get("errors")`. The honest path to flip `healthy` is to surface findings through `org_drg` (e.g. an `unsanctioned_overrides` key) and extend the `healthy` predicate to treat a non-empty findings list as unhealthy — mirroring how `org_drg["errors"]` already forces unhealthy. Decide the exact key/shape in T023; keep it one load, no parallel assembly.
- **Fail-closed + no-packs guard:** the adjudication is only meaningful when `fragments` (org packs) are present — `_collect_org_layer_data` already returns early when `not fragments`. Do NOT flip a healthy built-in-only repo (NFR-001): the finding path must be unreachable without org packs.
- **The allowlist load:** `load_replaceable_builtins(repo_root)` already reads `.kittify/doctrine/replaceable-builtins.yaml` fail-closed (absent → forbids all). Reuse it; pass the resulting `ReplaceableBuiltinsPolicy` to `find_unsanctioned_overrides`.
- **C-005 red-first** through the public `doctor doctrine --json` surface (NOT the promoted predicate's API — that is WP07's surface). **C-007** realistic org-pack fixtures (real `OrgDRGFragment`/pack layout, real built-in URNs). **NFR-001** no-org-packs regression test. **NFR-003** ruff/mypy clean, complexity ≤ 15.

## Subtasks & Detailed Guidance

### Subtask T022 — RED test through `doctor doctrine --json`

- **Purpose**: Witness that an unsanctioned override is invisible to the operator today.
- **Steps**: In `tests/specify_cli/cli/commands/test_doctor_override_diagnostics.py`, build a scratch repo fixture with a configured org pack that overrides a built-in DRG node (same-kind override at a built-in URN), and NO sanctioning `replaceable-builtins.yaml` entry. Drive `doctor doctrine --json` via `CliRunner`. Assert the JSON flags the override (e.g. an `unsanctioned_overrides` list naming the URN) and `healthy=false` / exit code 1. Add a second case: add the sanctioning allowlist entry (with a reason, since it is a directive) → assert NOT flagged. Add a third case: no org packs → output byte-identical to today (NFR-001). Confirm cases 1–2 are RED today (no diagnostic emitted).
- **Files**: `tests/specify_cli/cli/commands/test_doctor_override_diagnostics.py`.
- **Notes**: Use real org-pack fixtures and a real built-in URN drawn from the shipped graph (C-007) — not a handcrafted placeholder pack.

### Subtask T023 — Wire the promoted predicates into the org-packs-present branch

- **Purpose**: Make the operator-facing command honour the governance gate.
- **Steps**:
  1. In `_doctrine_collect.py::_collect_org_layer_data`, capture the merged graph from the existing `merge_three_layers(...)` call (line ≈ 363), compute `built_in_urns = frozenset(n.urn for n in built_in.nodes)`, call `find_overridden_builtin_urns(merged, built_in_urns)`, load the policy via `load_replaceable_builtins(repo_root)`, and call `find_unsanctioned_overrides(targets, policy)`. Store the findings (serialised: `urn`/`kind`/`why`) under a new `org_drg` key (e.g. `"unsanctioned_overrides"`). Keep the early-return-when-no-fragments guard intact so the finding path is unreachable without org packs.
  2. Flip `healthy`: extend `DoctrineHealthReport.healthy` (in `_doctrine_health.py` — note: NOT in your owned set, so prefer surfacing findings via the existing `errors` channel OR coordinate the predicate change; if `_doctrine_health.py` must change, FLAG it as an ownership gap rather than editing outside owned_files). Simplest in-ownership path: append a structured entry to `org_drg["errors"]` when findings exist (the `healthy` predicate already treats non-empty `errors` as unhealthy), while ALSO exposing the findings under a dedicated key for precise rendering.
  3. Thread the findings into both emitters: `_emit_doctrine_json` (machine-readable list) and `_emit_doctrine_human` (a clear, loud "unsanctioned built-in override" block). The exit code already derives from `report.healthy` in `doctrine_check` — no separate exit wiring needed once `healthy` reflects the findings.
- **Files**: `src/specify_cli/cli/commands/_doctrine_collect.py`, `src/specify_cli/cli/commands/doctor.py`.
- **Notes**: Single org-DRG load — do not add a second merge. If the cleanest `healthy` flip genuinely requires touching `_doctrine_health.py` (outside owned_files), STOP and flag it for the planner rather than silently editing or hand-rolling a parallel health computation.

### Subtask T024 — Document the project-tier ungoverned boundary (FR-012)

- **Purpose**: Make explicit that project doctrine is the trusted operator tier and is deliberately NOT gated.
- **Steps**: Add a concise note in the `doctor doctrine` command docstring/help and a short doc note (e.g. alongside the existing doctrine-health docs) stating: only `org:`-provenance built-in overrides are adjudicated against `replaceable-builtins.yaml`; project-tier (`.kittify/doctrine/`) overrides are intentionally ungoverned (FR-012). Keep wording terminology-canon clean (run the terminology guard if prose touches doctrine/user-facing text).
- **Files**: `src/specify_cli/cli/commands/doctor.py` (docstring/help). If a standalone doc note is warranted, place it under `docs/` per repo convention — but do NOT create sprawling docs; a short note suffices.
- **Notes**: This boundary mirrors the scope docstring already on `find_overridden_builtin_urns` (WP07).

## Test Strategy

- Run: `PWHEADLESS=1 pytest tests/specify_cli/cli/commands/test_doctor_override_diagnostics.py -q`.
- Prove T022 RED against pre-T023 code (no diagnostic), then GREEN after wiring.
- Regression: a no-org-packs scratch repo → `doctor doctrine --json` output unchanged (NFR-001) — include this as an explicit assertion, not an afterthought.
- `ruff check` + `mypy` clean on `doctor.py` and `_doctrine_collect.py`.

## Risks & Mitigations

- New DRG plumbing creeping in → reuse the existing `_collect_org_layer_data` merge and `load_replaceable_builtins`; assert "one merge" in review (C-006).
- Healthy repos flipping to RC=1 → the no-packs short-circuit + the `not fragments` early return keep the finding path unreachable without org packs; the regression test pins NFR-001.
- Ownership overspill into `_doctrine_health.py` → prefer the `org_drg["errors"]` channel (already drives `healthy`); flag if a predicate change is truly required.

## Review Guidance

- Verify red-first ordering on the unsanctioned/sanctioned cases.
- Verify the merge is reused (single org-DRG load) — no second `merge_three_layers`.
- Verify the no-org-packs path is byte-identical to today (NFR-001 regression assertion present).
- Verify FR-012 boundary is documented and that ONLY `org:`-provenance overrides are adjudicated.
- Verify no edits leaked outside the three owned files (especially `_doctrine_health.py`).

## Post-Tasks Squad Remediations (BINDING)

- **Health flip stays IN-OWNERSHIP — no `_doctrine_health.py` edit (the earlier flag was a false alarm).** Append the structured unsanctioned-override finding to `org_drg["errors"]` (assembled in owned `_doctrine_collect.py::_collect_profile_health`); `DoctrineHealthReport.healthy` already returns unhealthy on non-empty `org_drg["errors"]`, flipping RC=1.
- ALSO expose a dedicated `unsanctioned_overrides` key and render THAT in the human/JSON emitter (so the operator sees "unsanctioned built-in override", not a merged errors blob).
- **Extract a pure `_adjudicate_org_overrides(merged, built_in_urns, repo_root)` helper** (keep `_collect_org_layer_data` ≤ complexity 15) and unit-test it directly. Narrow `org_drg["unsanctioned_overrides"]` reads with `isinstance` — no `# type: ignore`.

---

## Activity Log

- 2026-06-27T00:00:00Z – system – Prompt created.
- 2026-06-27T10:05:37Z – claude:opus:python-pedro:implementer – shell_pid=964928 – Assigned agent via action command
- 2026-06-27T10:16:55Z – claude:opus:python-pedro:implementer – shell_pid=964928 – doctor flags unsanctioned org overrides of built-in DRG nodes; healthy flips via org_drg errors (RC=1); dedicated unsanctioned_overrides key rendered in human+JSON; FR-012 project-tier boundary documented; ruff/C901/mypy exit 0; 5/5 new tests green, 57 existing doctrine-doctor tests pass
- 2026-06-27T10:17:41Z – claude:opus:reviewer-renata:reviewer – shell_pid=1005716 – Started review via action command
- 2026-06-27T10:25:20Z – user – shell_pid=1005716 – Moved to planned
- 2026-06-27T10:25:40Z – claude:opus:python-pedro:implementer – shell_pid=1025281 – Started implementation via action command
- 2026-06-27T10:29:56Z – claude:opus:python-pedro:implementer – shell_pid=1025281 – cycle 1: re-pinned doctrine help golden snapshot; 0 net-new failures; override diagnostics 5/5 green
- 2026-06-27T10:30:24Z – claude:opus:reviewer-renata:reviewer – shell_pid=1035277 – Started review via action command
- 2026-06-27T10:36:07Z – user – shell_pid=1035277 – Cycle-1 re-review by reviewer-renata APPROVED (golden re-pin content-anchored, zero net-new failures, 5/5 override green); supersedes the cycle-0 rejection artifact review-cycle-1.md
