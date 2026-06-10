# Issue matrix — do-dispatch-open-op-lifecycle-01KTSJ2H

One row per issue referenced in spec.md. Filled at WP01 review (schema v2 split);
verdicts upgraded post-merge (squash merge 447754669) after the owning WPs landed
and the post-merge mission review verified the implementations.

| Issue | Verdict | Evidence ref |
|-------|---------|--------------|
| #1810 | deferred-with-followup | WP01 (commit b1f8634cf, in merge 447754669) fixes the "unreadable record" portion: OpCompletedEvent requires outcome/closed_by, blank-default records unrepresentable (tests/specify_cli/invocation/test_record.py). The do→dispatch rename is explicitly out of scope per spec.md C-002 and is NOT done — follow-up remains #1810 (rename). |
| #1229 | fixed | Open→work→close loop landed in merge 447754669: WP02 `do` is an honest open dispatch (do_cmd.py writes started event only; tests/specify_cli/invocation/cli/test_do.py::test_creates_jsonl_record_on_successful_routing) and WP03 close surface requires `--outcome` with `closed_by="agent"` (advise.py; tests/specify_cli/invocation/cli/test_complete.py). |
| #1688 | fixed | Record durability schema v2 landed in merge 447754669: WP01 frozen OpStartedEvent/OpCompletedEvent split with required outcome/closed_by Literals (record.py), WP04 doctor stale sweep closes via the executor with `closed_by="doctor_sweep"` (doctor/ops.py; tests/specify_cli/invocation/test_doctor_ops.py). Sweep SaaS propagation gap fixed post-merge (commit d5e3eb762). |
| #1781 | fixed | Orphan hygiene landed in merge 447754669: WP04 `doctor ops --close-stale` sweep (doctor/ops.py, tests/specify_cli/invocation/test_doctor_ops_cli.py) plus WP05 legacy record migration m_3_3_0_op_record_schema_v2 via `spec-kitty upgrade` (tests/upgrade/test_op_record_schema_v2_migration.py) and WP06 session-presence open-Ops surfacing in the SessionStart/Stop hooks (session_start.py/session_stop.py, tests/specify_cli/session_presence/test_open_ops.py). |
| #701 | fixed | Session presence contract prose rewritten to the open→work→close lifecycle in merge 447754669 (WP06: session_presence/content.py, src/doctrine/skills/spec-kitty.advise/SKILL.md; tests/specify_cli/session_presence/test_content.py asserts the close-contract prose; grep for retired "outcome done"/"single-shot" prose = 0 hits per mission-review-report.md FR-010). |
