---
work_package_id: WP04
title: Repoint runtime_bridge monkeypatch sites — batch B (runtime/specify_cli/integration/misc)
dependencies:
- WP03
requirement_refs:
- FR-003
- FR-016
- NFR-003
tracker_refs:
- '2561'
planning_base_branch: feat/test-suite-friction-remediation
merge_target_branch: feat/test-suite-friction-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-friction-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-friction-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: tests/runtime/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/runtime/**
- tests/specify_cli/**
- tests/integration/**
- tests/contract/test_next_no_implicit_success.py
- tests/contract/test_next_no_unknown_state.py
- tests/agent/test_implement_command.py
- tests/perf/test_loader_perf.py
- tests/unit/mission_loader/test_command.py
role: implementer
tags: []
shell_pid: "3628555"
shell_pid_created_at: "1783967824.84"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md) FR-003, and WP02's
classification note. This WP repoints **batch B** — everything outside `tests/next/**` (WP03's surface). The
two batches are file-disjoint; both are repoint-only and UPSTREAM of WP18's delegate deletion (repoint
first, so WP18 can delete the now-unreferenced façade delegates). **Do NOT edit
`tests/runtime/test_bridge_compat_surface.py`** — WP18 owns the frozen-baseline update; leave it green here.

## Objective

Repoint the remaining forwarding `monkeypatch.setattr(runtime_bridge, …)` sites at their owning seam
modules across `tests/runtime/**`, `tests/specify_cli/**`, `tests/integration/**`, and a small set of
explicitly-owned files. ~40 files, ~168 occurrences (mostly 1–3 each). Only the forwarding subset repoints.

## Context — batch B file map (owned files, disjoint from WP03)

Notable densities: `tests/specify_cli/next/test_runtime_bridge_composition.py` (31),
`tests/specify_cli/next/test_runtime_bridge.py` (16), `tests/specify_cli/events/test_decision_log_coord.py`
(13), `tests/runtime/test_runtime_bridge_identity.py` (13), `tests/runtime/test_bridge_engine.py` (10),
`tests/specify_cli/cli/commands/test_selector_resolution.py` (7),
`tests/specify_cli/cli/commands/test_next_fail_closed.py` (7),
`tests/integration/test_custom_mission_runtime_walk.py` (7),
`tests/integration/retrospective/test_wp04_coverage_branches.py` (11),
`tests/runtime/test_bridge_parity.py` (6) — the rest are 1–4 each.

`tests/architectural/test_no_dead_symbols.py` also matched the grep (5 hits) but it holds **allowlist
string rows**, not monkeypatch sites — it is **owned by WP05**, NOT this WP. Do not edit it here.

## Subtask guidance

- **T015 — runtime + specify_cli.** Repoint forwarding sites in `tests/runtime/**` and
  `tests/specify_cli/**`. `tests/runtime/test_bridge_*` and `tests/specify_cli/next/test_runtime_bridge*`
  are the bulk; group patches by target seam module.
- **T016 — integration + contract + misc.** Repoint `tests/integration/**` (incl. the
  `integration/retrospective/*` cluster), `tests/contract/test_next_no_implicit_success.py`,
  `tests/contract/test_next_no_unknown_state.py`, `tests/agent/test_implement_command.py`,
  `tests/perf/test_loader_perf.py`, `tests/unit/mission_loader/test_command.py`.
- **T017 — suites green.** Run the affected suites incl. the **behavioural-parity** guard
  `tests/runtime/test_bridge_parity.py`:
  `.venv/bin/python -m pytest tests/runtime tests/specify_cli tests/integration tests/contract/test_next_no_implicit_success.py tests/contract/test_next_no_unknown_state.py tests/agent/test_implement_command.py tests/perf/test_loader_perf.py tests/unit/mission_loader/test_command.py -q`.
  Verify zero forwarding-delegate patch survivors across the owned files.
- **T018 — gates + tracer.** `ruff`/`mypy` clean; append the parity-suite tracer row (WP04 observes
  `test_bridge_parity.py`).

## Branch Strategy

Branches from WP03's tip in the Lane-0 serial chain; merges into `feat/test-suite-friction-remediation`.

## Definition of Done (non-fakeable — NFR-002)

- [ ] Every forwarding patch site in the owned files repointed at its owning seam module.
- [ ] Affected suites green, **including `tests/runtime/test_bridge_parity.py`**.
- [ ] Zero forwarding-delegate patch survivors in the owned files (grep evidence).
- [ ] `tests/architectural/test_no_dead_symbols.py` was NOT edited here (it is WP05's).
- [ ] `ruff` + `mypy` clean; no production edits (test-only WP).
- [ ] **Tracer (FR-016):** append a row for the `test_bridge_parity` behavioural-parity suite (invariant-vs-
      shape discriminator) to `../tracer-design-decisions.md` + friction to `../tracer-tooling-friction.md`.

## Risks

- **Parity suite false-red** — `test_bridge_parity.py` asserts seam↔façade equivalence; a mis-repoint here
  is the most likely place to leave a stale pass. Verify it exercises the real seam post-repoint.
- **Wide file surface (40 files)** — most are 1–3 occurrences; work by directory to keep the diff coherent.

## Reviewer guidance

- Confirm the parity suite exercises the seam modules, not a re-added forwarder.
- Confirm `test_no_dead_symbols.py` is untouched (WP05 boundary).

## Activity Log

- 2026-07-13T19:41:41Z – claude – shell_pid=3628555 – 47 forwarding sites repointed (5 files); tests/runtime 604 passed, test_bridge_parity 10 passed, tests/specify_cli 10995 passed, integration+etc 665 passed; compat_surface+no_dead_symbols untouched; ruff clean; commit 6540d1dea. Scoping: left #2531 seam-family live-lookup wiring suites for WP18 co-evolution. Force: lane planning/status-behind only.
- 2026-07-13T19:41:48Z – claude:opus:reviewer-renata:reviewer – shell_pid=3628555 – Review claim
- 2026-07-13T19:49:42Z – claude:opus:reviewer-renata:reviewer – shell_pid=3628555 – APPROVE (reviewer-renata/opus): 47 repoints all target defining seam (grep-verified); repointed names are retained thin delegates (survive WP18 deletion); seam-family scoping CORRECT — those suites assert seam→façade live-lookup, repoint=vacuous; _composition_dispatch_inputs correctly left (plain re-export, WP18 co-refactors call-site+patch); compat_surface+no_dead_symbols untouched; 121 spot-check passed incl test_bridge_parity. Commit 6540d1dea.
