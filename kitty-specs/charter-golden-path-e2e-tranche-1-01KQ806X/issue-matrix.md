# Issue Matrix — charter-golden-path-e2e-tranche-1-01KQ806X

**Mission**: `charter-golden-path-e2e-tranche-1-01KQ806X` (Charter Golden-Path E2E, Tranche 1)
**Created**: 2026-04-27 (during mission review's "address findings directly" pass)
**Authoring context**: The issue-matrix doctrine was added by mission `stability-and-hygiene-hardening-2026-04-01KQ4ARB` on 2026-04-26, one day before this mission was authored. The `/spec-kitty.tasks` command surface in this version did not auto-generate a matrix. The mission review surfaced the gap and this matrix was authored as part of "address findings directly".

This matrix records every product finding the mission surfaced during implementation and review, every workflow papercut encountered during the run, and every pre-existing failure observed but not addressed, with a verdict cell drawn from the FR-037 allow-list (`fixed` / `verified-already-fixed` / `deferred-with-followup`).

## Verdict legend

- **fixed** — the finding was addressed inside this mission's diff.
- **verified-already-fixed** — the finding was investigated and confirmed fixed by an earlier change (i.e., not present at HEAD).
- **deferred-with-followup** — the finding was NOT addressed in this mission and a concrete follow-up handle (issue link or precise narrower title) is recorded.

A bare "deferred" with no follow-up handle is a Gate 4 hard fail per the doctrine; every `deferred-with-followup` row in this matrix names a specific follow-up.

---

## Product findings (FR-021 — Charter epic operator-path regressions surfaced by the test)

| ID | Title | Surface | Where surfaced in code | Verdict | Evidence ref |
|---|---|---|---|---|---|
| F1 | `charter synthesize --adapter fixture` requires hand-curated corpus; fresh-project input hashes don't match | `spec-kitty charter synthesize` | `tests/e2e/test_charter_epic_golden_path.py:454-516` (with FR-021 inline comments) | deferred-with-followup | Follow-up: file Priivacy-ai/spec-kitty issue titled "charter synthesize --adapter fixture: fresh-project input hashes (e.g. `8d56b9a6827d`, `3bc56581c663`) miss the curated corpus, raising FixtureAdapterMissingError; need a public synthesize path that works unattended without an LLM harness". Workaround in test: use `--dry-run-evidence` for FR-011 and hand-seed `.kittify/doctrine/` for FR-012. |
| F2 | `spec-kitty init` does not stamp `.kittify/metadata.yaml.spec_kitty.{schema_version,schema_capabilities}` | `spec-kitty init` | `tests/e2e/test_charter_epic_golden_path.py:364-407` (`_bootstrap_schema_version` helper docstring) | deferred-with-followup | Follow-up: file Priivacy-ai/spec-kitty issue titled "spec-kitty init: `.kittify/metadata.yaml` lacks `spec_kitty.schema_version` + `schema_capabilities`; downstream charter/mission/next commands then exit 4 with 'needs migrations'; `spec-kitty upgrade --project --yes` is a no-op against this state". Workaround: test bootstraps the fields by hand (mirrors existing `e2e_project` fixture). |
| F3 | `charter generate` writes `charter.md` but does NOT `git add` it; `bundle validate` requires it tracked | `spec-kitty charter generate`, `spec-kitty charter bundle validate` | `tests/e2e/test_charter_epic_golden_path.py:431-443` (inline comment naming `tracked_files.expected` invariant) | deferred-with-followup | Follow-up: file Priivacy-ai/spec-kitty issue titled "charter generate writes charter.md but does not stage it; charter bundle validate then fails because charter.md is untracked; the two commands have a contradictory implicit invariant". Workaround: test commits `charter.md` between `generate` and `bundle validate`. |
| F4 | Agent commands append non-JSON SaaS error line to stdout, breaking `--json` parse | `spec-kitty agent mission create --json` and other `agent` subcommands when SaaS sync is not authenticated | `tests/e2e/test_charter_epic_golden_path.py:102-116` (`_parse_first_json_object` using `JSONDecoder.raw_decode`) | deferred-with-followup | Follow-up: file Priivacy-ai/spec-kitty issue titled "SaaS sync errors leak into --json envelopes: `❌ Connection failed: Forbidden: Direct sync ingress must target Private Teamspace.` is appended to stdout AFTER the JSON object, breaking strict parsers". **Same root cause** as the 3 pre-existing `tests/e2e/test_cli_smoke.py::TestFullCLIWorkflow::*` failures (`json.decoder.JSONDecodeError: Extra data`). Workaround: parse with `JSONDecoder.raw_decode`. |
| F5 | `next --result success` for `step_id=discovery → action=research` does NOT create `.kittify/events/profile-invocations/` | `spec-kitty next` | `tests/e2e/test_charter_epic_golden_path.py:761-908` (FR-016 paired-records assertion is gated on `pi_dir.is_dir()`; tight `action == issued_step_id` comparison applies only when records ARE present; the expected xfail is deferred until after `retrospect summary` runs) | deferred-with-followup | Follow-up: file Priivacy-ai/spec-kitty issue titled "next --result success on the first composed action (`step_id=discovery`, `action=research`) does not write profile-invocation lifecycle records; the `step_id != action` mismatch + missing `pi_dir` together suggest the legacy single-dispatch path is taken instead of the composition path that writes profile-invocation records". When fixed, remove the F5 xfail gate in `_run_next_and_assert_lifecycle` / `_run_golden_path`. |

---

## Workflow papercuts (the mission orchestration itself)

| ID | Title | Surface | Verdict | Evidence ref |
|---|---|---|---|---|
| W1 | Dossier-snapshot file blocks `move-task` pre-flight | `spec-kitty agent tasks move-task` | deferred-with-followup | Follow-up: file Priivacy-ai/spec-kitty issue titled "agent tasks mark-status updates `kitty-specs/<slug>/.kittify/dossiers/.../snapshot-latest.json` (gitignored), but `agent tasks move-task` pre-flight requires a clean working tree; the orchestrator must `git add -f` and commit between every state transition". Recurred 3 times during the run (WP01 move-to-for-review, WP02 move-to-approved, pre-merge). |
| W2 | `/spec-kitty.specify` and `/spec-kitty.plan` auto-commits don't pick up post-create edits | `/spec-kitty.specify`, `/spec-kitty.plan` | deferred-with-followup | Follow-up: file Priivacy-ai/spec-kitty issue titled "specify/plan auto-commits land the empty scaffold but not the populated content; the orchestrator must run a follow-up `git add` + `git commit` to land the actual spec/plan/research/etc. content". Resolved in this mission via commit `dbfae30a` (manual catch-up). |
| W3 | Decision events collide with WP-state schema in `status.events.jsonl` | `spec-kitty agent decision open/resolve` (writes events to `kitty-specs/<slug>/status.events.jsonl`) vs the WP-state reducer (expects every line to carry top-level `wp_id`) | deferred-with-followup | Follow-up: file Priivacy-ai/spec-kitty issue titled "DecisionPointOpened / DecisionPointResolved events are written to status.events.jsonl with `event_type` + nested `payload` schema; the WP-state reducer expects top-level `wp_id` and rejects every line with 'Invalid event structure on line 1: wp_id'; effectively decision events block all subsequent finalize-tasks runs". Workaround in this mission: archived the conflicting events to `_archive/decisions-prefix.events.jsonl` (canonical record preserved in `decisions/DM-*.md`); finalize-tasks then succeeded and recreated `status.events.jsonl` with the correct schema. |

---

## Pre-existing failures observed

| ID | Title | Surface | Verdict | Evidence ref |
|---|---|---|---|---|
| P1 | `tests/contract/test_cross_repo_consumers.py::test_spec_kitty_events_module_version_matches_resolved_pin` fails (4.0.0 installed vs 4.1.0 in uv.lock) | uv environment / package pin drift | deferred-with-followup | Environmental drift; failure persists at HEAD. Verified pre-existing by checking out `cdcbf5df^` and running the same test — fails with identical assertion. Resolution: per the test's own error message, run `uv sync` to align the installed package with `uv.lock`, OR regenerate the envelope snapshot via `python scripts/snapshot_events_envelope.py --force` if the bump is intentional. Follow-up: file Priivacy-ai/spec-kitty issue titled "CI/dev environment hygiene: uv.lock pins `spec_kitty_events==4.1.0` but installed venv has 4.0.0; tests/contract/test_cross_repo_consumers.py::test_spec_kitty_events_module_version_matches_resolved_pin fails on every clean review run; add a pre-PR `uv sync && pytest tests/contract/` step to catch this class of drift." Owner: dev-environment / CI. (Earlier draft of this matrix marked the row `verified-already-fixed`; that was misleading because the failure is live — corrected to `deferred-with-followup` per post-review feedback.) |
| P2 | `tests/e2e/test_cli_smoke.py::TestFullCLIWorkflow::{test_create_feature, test_setup_plan, test_full_workflow_sequence}` fail with `json.decoder.JSONDecodeError: Extra data` | Same root cause as F4 | deferred-with-followup | Follow-up handle: same as F4 (Priivacy-ai/spec-kitty SaaS-sync stdout pollution issue). Confirmed pre-existing by both WP01 reviewer and WP02 implementer via `git stash` + re-run on lane base. Fixing F4 is expected to fix these. |

---

## Verdict-cell summary (Gate 4 compliance)

- Total rows: 10 (5 product findings F1-F5 + 3 workflow papercuts W1-W3 + 2 pre-existing P1-P2)
- Empty `verdict` cells: 0
- `unknown` verdicts: 0
- `deferred-with-followup` rows missing follow-up handles: 0 (every deferred row names either a specific issue title to file or, for F4 and P2, a shared follow-up)
- `fixed`: 0 (this mission did not fix the underlying product regressions — by design; the test surfaces them, the follow-ups fix them)
- `verified-already-fixed`: 0
- `deferred-with-followup`: 10

Per FR-037 of the issue-matrix doctrine, every cell is in the allow-list. Gate 4 passes.

---

## Operator follow-up checklist

The orchestrator did not file the GitHub issues directly because no GitHub remote was configured for this workspace. The user (or a downstream automation step) should:

1. File one issue per F1, F2, F3 with the proposed titles above.
2. File one combined issue covering F4 + P2 (same root cause).
3. File one issue for F5; note the deferred xfail gate that needs removing when it lands.
4. File three "workflow papercut" issues (W1, W2, W3) with the proposed titles above. Tag with `papercut` or similar.
5. Decide whether P1 (uv.lock vs installed pin drift) deserves a CI hardening change to prevent recurrence (recommend: yes — a `uv sync && uv run pytest tests/contract/` pre-PR step would catch it).

After filing, link each issue's URL into this matrix's `Evidence ref` cells (replacing the proposed title text with the issue URL) and commit the update. That edit closes the loop on the matrix as a forward-tracking artifact rather than a one-shot review snapshot.
