---
cycle_number: 2
verdict: approved
wp_id: WP04
mission_slug: docs-ia-onboarding-overhaul-01KY02JB
reviewer_agent: "claude:sonnet-5:curator-carla:reviewer"
reviewed_at: "2026-07-20T18:50:00+00:00"
---

# WP04 Review — Cycle 2

## Verdict: Approved

Cycle 1 rejected `docs/context/ops-vs-missions.md` for the overbroad claim "a mission action
never opens a `kitty-ops/*.jsonl` Op record" (contradicted by `spec-kitty next` writing to
`kitty-ops/lifecycle.jsonl`). Cycle 2 replaced that sentence with a precise distinction. This
review independently re-verified the corrected claim against source, not against the prior
review's wording.

**Independent verification performed:**

- `src/specify_cli/invocation/writer.py`: `InvocationWriter.invocation_path()` confirms
  `dispatch`'s per-invocation Op record path is `kitty-ops/<invocation_id>.jsonl`
  (`self._dir / f"{invocation_id}.jsonl"`, `_dir = repo_root / "kitty-ops"`). `write_started`
  uses exclusive-create (`"x"` mode); `write_completed` appends the `completed` event to the
  same file.
- `src/specify_cli/invocation/executor.py`: `ProfileInvocationExecutor.invoke()` calls
  `self._writer.write_started(record)`; `complete_invocation()` calls
  `self._writer.write_completed(completed)` — confirms the doc's "opens... explicitly closed via
  `profile-invocation complete`" claim.
- `src/specify_cli/invocation/lifecycle.py`: `LIFECYCLE_LOG_RELATIVE_PATH = Path("kitty-ops") /
  "lifecycle.jsonl"`; `write_started`/`write_paired_completion` append `ProfileInvocationRecord`
  entries (a distinct schema from `OpStartedEvent`/`OpCompletedEvent`) to one shared file — no
  per-invocation file, no explicit close command.
- `src/specify_cli/cli/commands/next_cmd.py`: confirmed `_write_issuance_lifecycle_record` and
  `_pair_previous_lifecycle_record` are the actual call sites invoking
  `specify_cli.invocation.lifecycle.write_started` / `write_paired_completion` — so the doc's
  "`spec-kitty next` appends paired started/completed lifecycle records...to one shared
  `kitty-ops/lifecycle.jsonl` log" claim is grounded in the real call graph, not just the
  lifecycle module's own docstring.
- `docs/context/mission-types.md`: confirmed genuinely untouched this cycle — `git log --oneline
  -- docs/context/mission-types.md` shows only the original cycle-1 commit (`0345455d7`). Its
  4-mission-type list was re-spot-checked against
  `src/specify_cli/missions/{software-dev,research,documentation,plan}/mission.yaml` (name,
  phases, purpose) — accurate.
- Remaining claims on the page (dispatch is synchronous / never spawns an LLM call per
  `executor.py`'s docstring, `doctor ops` sweep existing at `src/specify_cli/doctor/ops.py` with
  `outcome="abandoned"` / `closed_by="doctor_sweep"`, the `toc.yml` "Core Concepts > Context &
  Terminology" slot reservation at `context/index.md` cited in the Activity Log) were spot-checked
  and are accurate. No further unverified absolute claims found.

Issue 1 from cycle 1 is resolved. No new issues found.
