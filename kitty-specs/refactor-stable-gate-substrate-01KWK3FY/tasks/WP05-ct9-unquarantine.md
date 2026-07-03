---
work_package_id: WP05
title: CT9 un-quarantine
dependencies: []
requirement_refs:
- FR-007
- FR-008
tracker_refs: []
planning_base_branch: tidy/gate-substrate
merge_target_branch: tidy/gate-substrate
branch_strategy: Planning artifacts for this mission were generated on tidy/gate-substrate. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/gate-substrate unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
phase: Phase 1 - Parallel substrate work
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1783280"
history:
- at: '2026-07-03T06:37:42Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/cli/commands/test_retrospect.py
- tests/readiness/test_upgrade_ux.py
- tests/specify_cli/cli/commands/test_decision_widen_subcommand.py
- tests/specify_cli/cli/test_decision_command_shape_consistency.py
- tests/specify_cli/invocation/cli/test_doctor_ops_cli.py
- tests/specify_cli/invocation/test_doctor_ops.py
- tests/specify_cli/test_mid8_contract_sensitive_routing.py
- tests/specify_cli/test_mid8_direct_routing.py
- tests/specify_cli/test_no_checklist_surface.py
- tests/sync/test_daemon_singleton_reaper_consolidation.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – CT9 un-quarantine

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

CT9 (#2311, spec FR-007/FR-008/**FR-010** — RESCOPED by the operator's CI-green fold,
2026-07-03): make the `quarantine visibility (non-blocking)` CI job GREEN. Ground
truth (spec Context + research D9/D10): ALL 31 quarantined tests FAIL on CI
(run 28643092421) while 16 pass locally — total local≠CI skew. Every one of the 31
gets a per-test adjudication on CI EVIDENCE:
(a) **REMEDIATE** — fix the test's CI-env fragility (Rich-rendered help assertions,
    fresh-venv version skew, HOME/env assumptions) so it passes on CI, then
    UN-quarantine it into its normal shard;
(b) **DISABLE** — `pytest.mark.skip(reason=...)` with an accurate diagnosis + issue
    ref (daemon-reaper → #2309; uv-tool → the upstream issue you file);
(c) **DELETE** — valueless/stub tests, with a recorded surviving-coverage judgment.
FORBIDDEN (operator): masking/deleting the lane, env-var games, retry-to-green,
softening an assertion that carries a real product signal. Success = the lane is
green on the mission PR; remediated tests also pass in their normal shard selection.

## Context & Constraints

Read FIRST:
- `research.md` D5 + **D9/D10** (the CI-vs-local truth table, per-file marker
  distribution, and the FR-010 adjudication framework).
- The CI failure log capture: the scratchpad `qlane.log` referenced in D10 — or
  re-pull it: `unset GITHUB_TOKEN; gh api repos/Priivacy-ai/spec-kitty/actions/jobs/84944784070/logs`.
  Diagnose CI failure signatures BEFORE touching anything; group by root cause
  (e.g. the 13 upgrade-ux CI failures likely share 1-2 env-skew roots — fix the
  root, not 13 assertions).
- CLAUDE.md parallel-run rules; note `tests/sync/test_daemon_singleton_reaper_consolidation.py`
  is the real-port serial class (`-n0` for local runs).
- C-003: uv-tool product drift is NOT fixed here (upgrade domain) — those two are
  disablement candidates with the issue ref. Same judgment for daemon-reaper (#2309
  exists — likely skip with ref, unless the CI failure is trivially a test bug).
- DIRECTIVE_041 judge-the-test: remediation means making the test honestly measure
  reality on CI; if a failure is a REAL product signal, do not soften — skip with an
  issue ref and record the escalation.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: tidy/gate-substrate
- **Merge target branch**: tidy/gate-substrate

## Subtasks & Detailed Guidance

### Subtask T019 – CI-evidence adjudication census

- **Steps**: Build the 31-row adjudication table: node id | local result | CI failure
  signature (from the lane log) | root-cause hypothesis | verdict
  (remediate/disable/delete) | evidence. Diagnose the CI-only failures for real
  (read the assertion + the CI output — e.g. the retrospect help failure shows the
  flag missing from Rich-rendered output: is it version skew in help rendering, or
  is the flag genuinely absent in a fresh install?). Group shared roots. Record the
  table in the Activity Log BEFORE editing. Any test whose CI failure is a real
  product signal → verdict is disable+issue (escalate in the log), never soften.

### Subtask T020 – Execute the adjudications

- **Steps**:
  1. REMEDIATE verdicts: fix the CI-env fragility at the root (robust help-output
     assertions that survive Rich rendering differences; env/HOME isolation fixes;
     version-skew-tolerant expectations) — then remove `@pytest.mark.quarantine`
     so the test returns to its normal shard. NO assertion softening that loses the
     test's actual contract.
  2. DISABLE verdicts: replace `@pytest.mark.quarantine` with
     `@pytest.mark.skip(reason="<honest diagnosis> — <issue ref>")` (a skip is green
     in the lane AND in normal shards; the quarantine marker's job is done for these).
  3. DELETE verdicts: remove the test with the surviving-coverage judgment recorded.
  4. Per remediated file, verify normal-shard CI selection (`file → markers → gate`
     in the Activity Log).
- **Files**: the 10 owned test files (edit only those with verdicts).

### Subtask T021 – Differential determinism ×2 (bypass UNSET)

- **Steps** (squad hardening — an exported bypass var masks whether markers were
  really handled): in a shell with `SPEC_KITTY_RUN_QUARANTINE` explicitly UNSET, run
  the owned files twice in CI form: `PWHEADLESS=1 pytest <files> -n auto --dist
  loadfile -q -p no:cacheprovider` (daemon file separately with `-n0`). Both runs:
  remediated nodes PASS (executed, not skipped) AND every disable-verdict node shows
  as SKIPPED in the same output — paste both tails showing the differential. Then
  the lane simulation: `SPEC_KITTY_RUN_QUARANTINE=1 pytest -m quarantine -q` (the
  remaining quarantine-marked set, if any survive) must be green. A flake in any
  run: revert that node to quarantine/skip with an honest reason and record the
  judgment (DIRECTIVE_041 — no retry-to-green).

### Subtask T022 – Honest stay-behind reasons + upstream issue

- **Steps**:
  1. Rewrite the 2 uv-tool quarantine reasons in `tests/readiness/test_upgrade_ux.py`:
     `test_uv_tool_auto_upgrade_preserves_custom_uv_tool_dir` → "behavioral drift:
     UV_TOOL_DIR env no longer passed to the subprocess — see <issue>"; 
     `test_uv_tool_auto_upgrade_preserves_receipt_python` → "behavioral drift:
     receipt --python no longer threaded into uv tool install argv — see <issue>".
  2. File the upstream issue (gh CLI with `unset GITHUB_TOKEN;`): upgrade-domain
     behavioral drift, judge-the-test framework applies (stale-test vs product-bug is
     the upgrade owner's call), the two failure signatures verbatim, quarantine
     reasons now reference it. Label tech-debt; assign nobody; reference #2311.
  3. The A16 perf case (`test_sweep_enumeration_perf_1k_files`,
     tests/specify_cli/invocation/test_doctor_ops.py) — it FAILS on CI (timing), so
     it gets a verdict like everything else: likely remediate per the flakiness
     policy (tune the budget gate per docs/guides/testing-flakiness.md — budget
     tuning is the sanctioned remediation for perf gates, not a workaround) or
     disable with an accurate reason. Adjudicate on the CI signature.
  4. FR-010 closure evidence: the authoritative gate is the lane run on the mission
     PR — record in the Activity Log that the orchestrator verifies it there; your
     local differential evidence is the precondition.

## Test Strategy

```bash
export PATH="$PWD/.venv/bin:$PATH"; PYTHONPATH="$PWD/src"
SPEC_KITTY_RUN_QUARANTINE=1 PWHEADLESS=1 pytest -m quarantine -q   # T019 baseline (31 nodes)
env -u SPEC_KITTY_RUN_QUARANTINE PWHEADLESS=1 pytest <owned files minus daemon> -n auto --dist loadfile -q -p no:cacheprovider  # ×2 (T021)
env -u SPEC_KITTY_RUN_QUARANTINE PWHEADLESS=1 pytest tests/sync/test_daemon_singleton_reaper_consolidation.py -n0 -q  # serial class
ruff check <owned files>
```

## Risks & Mitigations

- **local≠CI skew is THE problem, not a risk** — never claim a remediation done on
  local green alone; the lane run on the mission PR is the gate (FR-010).
- **Assertion softening disguised as remediation**: the review checks each remediated
  assertion still pins the test's original contract (e.g. the help test must still
  prove the flag is exposed — via a render-robust check, not a weaker one).
- **Marker-file conflicts with WP01-04**: none — the 10 files are disjoint from every
  other WP's surface.

## Review Guidance

- The 31-row adjudication table exists, is CI-evidence-grounded, and every verdict
  traces to a signature (spot-check 5).
- Verify T021 ran with the bypass UNSET and shows the differential (remediated PASS
  executed + disabled SKIPPED in the same output).
- REJECT any remediation that softens the test's contract; REJECT any lane-level
  masking or env-var workaround (FR-010's forbidden list).
- Verify the upstream uv-tool issue exists and skip reasons reference their issues.
- Post-state census: every remaining quarantine/skip marker has an honest reason;
  the lane simulation run is green.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-03T06:37:42Z – system – Prompt created.
- 2026-07-03T07:12:19Z – claude:opus:python-pedro:implementer – shell_pid=1660876 – Assigned agent via action command
- 2026-07-03T09:30:00Z – claude:opus:python-pedro:implementer – T019 CI-evidence adjudication census. Pulled CI job 84944784070 log (run 28643092421): 31 failed / 0 passed. Local baseline (`-m quarantine -n0`): 16 failed / 15 passed. Built a CI-pinned reproduction venv (typer==0.26.8, click==8.4.2, rich==15.0.0, py3.11 + full `.[test]` deps) and reproduced the exact CI form `pytest tests/ -m quarantine`. KEY DIAGNOSIS: the 15 local-pass/CI-fail delta is NOT typer/click version skew directly — it reproduces only when **`CI=true`** (always set by GitHub Actions) and/or **`FORCE_COLOR=1`** are present. Two distinct env roots + several hermetic roots. Root-cause groups:
  - ROOT-1 (CI-env nag suppression, 11 upgrade-ux tests): `run_upgrade_ux` calls `Invocation.from_argv()` → `is_ci_env()` which reads `os.environ["CI"]` DIRECTLY (bypassing the injected `env=` param). Under `CI=true`, `suppresses_nag()` returns True → early `_inactive_outcome()` → `choice=None` / `ran=False` / empty `calls`. **Product is correct** (nag IS suppressed in CI); the tests fail to neutralise ambient CI detection → test-isolation bug. Verdict REMEDIATE (clear `CI`/`GITHUB_ACTIONS`/`CONTINUOUS_INTEGRATION` in a module autouse fixture; assertions unchanged).
  - ROOT-2 (Rich forced-terminal help render, 3 help/usage tests): under CI/`FORCE_COLOR`, Rich force-enables terminal styling; the Typer CliRunner help/usage output carries ANSI codes and wraps so raw-substring `in result.output` misses the flag literal. Verdict REMEDIATE (strip ANSI via shared `tests/_support/ansi.strip_ansi` before the substring assert; still proves the flag/usage token is exposed — no softening).
  - ROOT-3 (typer/click version-skew stale isinstance, 1 test): in typer 0.26.8/click 8.4.2 `TyperGroup` MRO is `TyperGroup→Command→ABC` — it NO LONGER subclasses `click.Group`, so `isinstance(agent_grp, click.Group)` is False on CI. Verdict REMEDIATE (duck-type the group via `.commands` / `typer.main.get_command`; the visible-subcommands contract stays; sibling `test_help_output_lists_canonical_subcommands` provides surviving coverage).
  - ROOT-4 (stale test API drift, 1 test mid8_direct): `_read_mission_mid8(meta_path)` was refactored to `load_meta(meta_path.parent)` (reads `meta.json` from the dir, ignoring the passed filename); the test writes `full.json`/`explicit.json`/`bare.json` in one shared tmp dir with no `meta.json` → `''`. Fails local+CI. Verdict REMEDIATE (write `meta.json` in per-case dirs; assertions GOLDEN_MID8/EXPLICIT8/'' unchanged).
  - ROOT-5 (shape-coupled positive-literal scan, 1 test mid8_contract): the 4 NEGATIVE invariants (`mission_id[:8]` absent in aggregate/scanner/implement/allocator) all PASS; only the positive `assert "resolve_mid8" in doctor.py` fails because doctor.py is now a 1118-line orchestration shell (mid8 logic delegated out). Verdict REMEDIATE-by-CONVERT (drop the stale positive-literal-presence assert per convert-or-delete-never-re-pin; keep the load-bearing negative scan incl. the `import mid8 as _mid8` reintroduction guard).
  - ROOT-6 (historical changelog trips live-surface scan, 1 test no_checklist): sole offender is `docs/changelog/CHANGELOG.md` — an immutable historical entry documenting the REMOVED `/spec-kitty.checklist` command. Verdict REMEDIATE (allowlist the changelog; it is not a live command surface — same spirit as the Terminology Canon's legacy-snapshot exemption).
  - ROOT-7 (perf budget gate, 1 test): 1k-file sweep proxy asserts `<0.5s`; CI observed 1.67s (marker cites 2.96s). Tier-1 budget gate per docs/guides/testing-flakiness.md → tune, never retry. Authoritative NFR-002 check is the separate `@pytest.mark.slow` 10k/<5s test. Verdict REMEDIATE (widen to `<5.0s` with inline rationale — still catches any O(n²)/order-of-magnitude regression).
  - ROOT-8 (uv-tool product drift, 2 tests): hermetic behavioral drift — `UV_TOOL_DIR` env dict no longer passed to `subprocess.run` (`calls[0][1] is None`); receipt `--python 3.13` no longer threaded into the `uv tool install` argv. REAL product signal, upgrade domain (out of this mission's scope). Verdict DISABLE — `@pytest.mark.skip` referencing filed upstream issue **#2316** (judge-the-test is the upgrade owner's call).
  - ROOT-9 (daemon-reaper, 10 tests): #2309 (OPEN) documents these are HERMETIC (reaper kill gate contradicts its documented contract), NOT environmental as the current marker claims — a REAL product/contract signal out of scope. They also fail local+CI+CI-venv. Verdict DISABLE — `@pytest.mark.skip` referencing #2309 + escalation note (marker reason was inaccurate).
  Tally: REMEDIATE 19 (un-quarantine) / DISABLE 12 (skip+issue: 2→#2316, 10→#2309) / DELETE 0. Filed upstream issue #2316 (label tech-debt, unassigned, references #2311). No lane masking, no env-var games, no assertion softening.
- 2026-07-03T07:51:35Z – claude:opus:python-pedro:implementer – shell_pid=1660876 – CT9 CI-green adjudication: 31 rows → 19 REMEDIATED (un-quarantined) / 12 DISABLED (skip+issue) / 0 DELETED. Roots: typer0.26 GITHUB_ACTIONS→FORCE_TERMINAL (help ANSI, fixed via strip_ansi), is_ci_env() ambient-CI nag suppression (autouse env-clear), TyperGroup no longer click.Group (duck-type), stale meta.json API drift, positive-literal scan convert, changelog allowlist, perf budget 0.5→5.0s. Disabled: 2 uv-tool→#2316 (filed), 10 daemon-reaper→#2309. Differential validated x2 under faithful CI env (GITHUB_ACTIONS=true CI=true, CI-pinned typer0.26.8 venv): 239 passed/2 skipped; daemon -n0 9 passed/10 skipped; cross-version green in local typer0.24 venv; lane -m quarantine collects 0. Authoritative FR-010 gate is the lane run on the mission PR. No masking/env-games/retry/softening.
- 2026-07-03T07:52:53Z – claude:opus:reviewer-renata:reviewer – shell_pid=1783280 – Started review via action command
- 2026-07-03T07:59:38Z – user – shell_pid=1783280 – Review passed: 19 REMEDIATE/12 DISABLE/0 DELETE all honest. Contracts preserved per class: strip_ansi SGR-only (content-safe, flag still proven exposed); env-clear autouse only delenv (assertions unchanged); duck-type still pins visible==EXPECTED 5 canonical subcommands; mid8 rewrite uses real load_meta(parent) API, truncate-then-decline intact; changelog allowlist narrowest docs/changelog/ prefix; perf 0.5->5.0s sanctioned (Tier-2 @slow 10k<5s exists, 10x stricter/file); mid8 scan convert dropped positive literal, negatives fire on reintroduction. CI-faithful verified: is_ci_env reads os.environ directly (R2), typer rich_utils FORCE_TERMINAL on GITHUB_ACTIONS (R1); remediated tests PASS under GITHUB_ACTIONS=true. Differential: 239 passed/2 skipped, daemon 9/10, -m quarantine collects 0. Issues #2316(OPEN,tech-debt)/#2309(OPEN) live; old 'environmental' lie corrected. Zero src changes, helper non-overlapping, ruff clean.
