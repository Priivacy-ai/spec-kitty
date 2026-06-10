---
work_package_id: WP06
title: Session Presence and Contract Prose
dependencies:
- WP02
- WP04
requirement_refs:
- FR-009
- FR-010
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
- T027
agent: "claude:fable:reviewer-renata:reviewer"
shell_pid: "56228"
history:
- '2026-06-10T20:15:38Z: created by /spec-kitty.tasks'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/session_presence/
execution_mode: code_change
owned_files:
- src/specify_cli/session_presence/**
- src/doctrine/skills/spec-kitty.advise/**
- src/doctrine/missions/**/spec-kitty-standalone*
- CHANGELOG.md
- tests/specify_cli/session_presence/**
role: implementer
tags: []
---

# WP06 — Session Presence and Contract Prose

## ⚡ Do This First: Load Agent Profile

Before reading further, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, and boundaries for the remainder of this work package.

## Objective

Teach the ecosystem the open→work→close contract. Claude Code session-start output lists open Ops with close commands; a Stop hook prints a non-blocking reminder; the canonical doctrine skill pack and standalone command templates stop describing `do` as single-shot; the CHANGELOG records the breaking change. Hook work is Claude-Code-only (C-003); the other 18 harnesses get the contract via capsule text (WP02) and the skill-pack prose updated here.

## Context

- Spec: FR-009, FR-010, C-001, C-003, C-005. Research R5 (registrar generalization is the feasible path). Contract: session-presence section of `contracts/doctor-ops-close-stale.md`.
- Surfaces: `src/specify_cli/session_presence/content.py` (orientation text incl. the "Lightweight dispatch" block at ~lines 57-74), `manager.py` (install flow), `hooks/claude_code_hook.py` (`ClaudeCodeHookRegistrar`, currently `SessionStart`-only, idempotent, atomic settings writes), `writers/claude_code.py` (registers `"spec-kitty session-start"`).
- Doctrine prose (**source** files only — C-005, never generated agent copies): `src/doctrine/skills/spec-kitty.advise/SKILL.md` (canonical standalone-invocation skill) and the standalone command template that generates `.cursor/commands/spec-kitty-standalone.md` et al. — locate via `grep -rn "spec-kitty-standalone\|profile-invocation complete" src/doctrine`.
- **Pre-push gate**: terminology guard `pytest tests/architectural/test_no_legacy_terminology.py` runs only in CI's misc job — run it locally before pushing any doctrine/prose change.

## Subtasks

### T023 — Open-Ops section in session-start orientation

**Purpose**: orphans are surfaced where the operator/agent will see them (FR-009, Success Criterion 4).

**Steps**:
1. The `spec-kitty session-start` command emits orientation text to stdout. Locate its implementation (grep `"session-start"` under `src/specify_cli`). Append, only when open Ops exist, a section built from `list_orphan_ops()`:
   ```
   ⚠ Open Ops (3): work that was dispatched but never closed
     01KT… (implementer-iris, 26h old) — close: spec-kitty profile-invocation complete --invocation-id 01KT… --outcome <done|failed|abandoned>
     …
   Sweep stale ones: spec-kitty doctor ops --close-stale
   ```
2. Zero open Ops → zero extra output (don't add noise to every session).
3. Keep it fast: this runs on every session start — reuse the orphan scan, no git calls. Measurable bound: the open-Ops section must add <0.5 s at 1,000 Op files (same pro-rata budget as WP04's T018 guard, since it is the same `list_orphan_ops()` scan); cover it in the T018-style perf test or share that fixture.

**Validation**: unit test renders orientation with 0 and N open Ops fixtures.

### T024 — Stop hook via generalized registrar

**Purpose**: end-of-session reminder (FR-009; research R5 confirmed feasibility).

**Steps**:
1. Generalize `ClaudeCodeHookRegistrar` to take the hook event key as a parameter (`SessionStart` | `Stop`) instead of the hardcoded `_SESSION_START_KEY`; preserve idempotency (`is_registered`), preservation of foreign entries, and atomic temp-file + `os.replace` writes.
2. Add a `spec-kitty session-stop` (or `doctor ops --quiet-reminder` — pick the cleaner fit with existing CLI structure; prefer a dedicated thin `session-stop` command that calls the same orphan scan) that prints the open-Ops reminder when any exist and **always exits 0** — it must never block the host agent's stop flow.
3. Register both hooks in the install/migration path that currently registers SessionStart (`manager.py` install + the session-presence migration — extend the existing migration or add a sibling following its `detect()`/`apply()` idempotency pattern so existing projects get the Stop hook on upgrade).

**Validation**: registrar unit tests for the Stop key (register/idempotent/foreign-entry preservation); `session-stop` exits 0 with and without open Ops.

### T025 — Doctrine skill pack + standalone templates

**Purpose**: the written contract every harness reads (FR-010).

**Steps**:
1. `src/doctrine/skills/spec-kitty.advise/SKILL.md`: rewrite the `do` description to the open→work→close contract: `do` opens the Op and loads governance; the agent does the work under that context; the agent MUST close with `spec-kitty profile-invocation complete --invocation-id <id> --outcome <done|failed|abandoned> [--evidence …]`; failed work closes as `failed`, never left open deliberately; `doctor ops` reports and sweeps orphans.
2. Standalone command template (source of `.cursor/commands/spec-kitty-standalone.md` etc.): same contract summary; remove any "do is single-shot / record already closed / commit the record" phrasing.
3. Orientation text in `content.py` ("Lightweight dispatch" block): keep the ALWAYS-run-`do` instruction, add one line: "After finishing the work, close the Op with the command printed in the capsule."
4. Sweep for stragglers: `grep -rn "outcome done\|single-shot\|record written" src/doctrine src/specify_cli/session_presence` and reconcile every hit with the new contract.

**Validation**: grep-based assertions in tests where the repo already pins template content (check `tests/specify_cli/skills/__snapshots__/` — regenerate snapshots via the documented flow if they cover these files).

### T026 — CHANGELOG + terminology guard

**Purpose**: the breaking change is documented (C-001); prose passes the canon gate.

**Steps**:
1. `CHANGELOG.md` entry under the next unreleased version: **Breaking**: `spec-kitty do` no longer auto-closes its Op record as `done`; the working agent must close via `profile-invocation complete`; completed-event schema v2 (`outcome` required, new `closed_by`); new `doctor ops --close-stale`; legacy `kitty-ops` records migrated (rewrite-or-delete) by `spec-kitty upgrade`. Reference this mission slug.
2. Run `pytest tests/architectural/test_no_legacy_terminology.py` (≈0.1 s) and fix any hits in the prose you touched.

**Validation**: guard test green locally.

### T027 — Presence/prose tests

**Purpose**: pin the teaching surfaces.

**Steps**: extend `tests/specify_cli/session_presence/`: orientation contains the close-instruction line; open-Ops section rendering (0/1/N); Stop-hook registration in `.claude/settings.json` (registered once, idempotent, SessionStart entry preserved); migration applies on a fixture project lacking the Stop hook and no-ops on a current one.

**Validation**: `.venv/bin/pytest tests/specify_cli/session_presence tests/architectural/test_no_legacy_terminology.py -q` green; mypy --strict + ruff clean.

## Branch Strategy

Planning base branch: `main`. Final merge target: `main`. Execution worktrees are allocated per computed lane from `lanes.json`. Implement via `spec-kitty agent action implement WP06 --agent <name>` (depends on WP02 and WP04 — capsule wording and doctor flags must be final before prose references them).

## Definition of Done

- [ ] Session-start lists open Ops (silent when none); Stop hook reminds, always exit 0.
- [ ] Registrar generalized with idempotency + atomic writes preserved; migration backfills existing projects.
- [ ] Skill pack, standalone templates, and orientation text all state open→work→close; zero single-shot phrasing remains (grep-verified).
- [ ] CHANGELOG breaking-change entry present; terminology guard green; ≥90% coverage; mypy --strict + ruff clean.

## Risks & Reviewer Guidance

- **C-005 is the trap**: edits must land in `src/doctrine/` and `session_presence/` sources, never `.claude/`/`.cursor/` generated copies. Reviewer: check the diff paths first.
- **Stop hook must be unobtrusive**: non-zero exit or slow IO in `session-stop` degrades every Claude Code session. Keep it scan-only, no git, exit 0 unconditionally.
- **Snapshot churn**: command-template snapshots may need regeneration; reviewer should verify snapshot diffs show only the intended prose change.

## Activity Log

- 2026-06-10T21:46:31Z – claude:fable:python-pedro:implementer – shell_pid=51901 – Assigned agent via action command
- 2026-06-10T22:07:44Z – claude:fable:python-pedro:implementer – shell_pid=51901 – Ready for review: presence + Stop hook + contract prose + CHANGELOG
- 2026-06-10T22:08:23Z – claude:fable:reviewer-renata:reviewer – shell_pid=56228 – Started review via action command
- 2026-06-10T22:11:22Z – user – shell_pid=56228 – Review passed: session presence (open-Ops at start, exit-0 session-stop Stop hook), generalized registrar + migration backfill, open→work→close prose across skill pack/12 harness copies/content.py, CHANGELOG breaking entry; merge resolutions preserved both lanes (do_cmd no complete_invocation, executor kw-only closed_by, v2 model_dump envelopes); 532+14 tests, mypy --strict and ruff clean, straggler grep zero hits
