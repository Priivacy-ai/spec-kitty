# Operator ruling — tasks phase HALT

**Mission**: `mission-scaffold-tasks-lanes-defects-01M0NERD` (issue #3673)
**Phase**: tasks
**HALT trigger**: `TASKS-FRESH2-001` (severity 4) survived the R1–R6 loop; early stop fired
because the severity≥3 blocking count did not fall between rounds (2 → 2).
**Ruled by**: the operator, 2026-08-23, relayed by the orchestrator.
**Evidence**: `tasks-fresh-2.yaml` (findings), `tasks-verify-2.yaml`, and the committed trail at
`c02711fad`.

## Ruling: ONE targeted fix round, then a fresh verifier. Findings are NOT accepted unfixed.

All three surviving findings are to be fixed. This ruling **does not lower the acceptance bar** —
it authorises one more R4→R5 cycle beyond the early stop, and nothing else.

**This ruling REPLACES the acceptance bar for this round.** A verifier for this round judges the
three findings below against the remediations as written here, and **must not re-derive the HALT**
on the grounds that the early-stop threshold was previously crossed. The early stop is spent; the
bar is now "are these three specific findings resolved".

### The orchestrator independently confirmed the severity-4 claim against source

Not taken on the lens's word. Read directly from
`src/specify_cli/cli/commands/agent/mission_finalize.py` on this checkout:

- `state.work_packages.append({...})` — line ~1351, runs **unconditionally** for every WP file.
- `_apply_ownership_inference(...)` — line ~1365, called **after** it.

So an assertion of the form `wp_id in state.work_packages` passes identically whether the FR-002
contradiction logic is correct or broken. The finding stands.

## Binding remediations — apply exactly, do not improvise a third variant

**TASKS-FRESH2-001 (severity 4)** — in WP02's T009: assert
`wp_id in state.inmemory_frontmatter` (or that its `owned_files` / `execution_mode` are preserved)
**AND** `wp_id not in state.ownership_contradictions`. **Do not rely on `state.work_packages`.**

**TASKS-FRESH2-002 (severity 3)** — in T009 step 4 and T010 step 1: narrow to `_run_bootstrap_loop`
**only**. Drop the "(or `finalize_tasks`...)" alternative and cite the module docstring's ownership
split in `tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py`, mirroring how T011
already cites PLAN-VERIFY-002. That file contains zero `CliRunner`/`runner.invoke` usage, so there
is no convention to defer to.

**TASKS-FRESH2-003 (severity 2)** — re-estimate T009's Files line to reflect step 4's heavier
fixture, and re-sum `tasks.md`'s WP02 test-line and combined PR-size totals from the current text.

## Standing constraints — unchanged, and a fix that breaches one is itself a finding

- **No new CLI surface** (D1 / FR-005 / C-003): no `migrate rebuild-meta`, no
  `--reinfer-ownership`, no `--force`/recovery-mode substitute.
- **Pipeline ordering is frozen** (plan position (a), ledger SK-71): no reordering of
  `_flush_frontmatter_writes` / `_emit_local_canonical_events` relative to the FR-003/FR-004 checks.
- These are **documentation edits to WP prompt text**. No production code changes in this round.

## Why this round is bounded

The two previous fix rounds each introduced a *new* defective test instruction — round 1 wrapped
`pytest.raises` around a `CliRunner` call that could never go green; round 2 replaced it with an
assertion that can never go red. The remediations above name exact fields and exact call sites
precisely to stop a third variant being invented.

**If the fresh verifier does not return all three resolved, the phase stops again and returns to
the operator.** No further rounds are authorised by this ruling.
