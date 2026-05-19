# Investigation Outcome — Issue #1142

**Schema**: data-model.md "Investigation Outcome"
**Investigator**: claude:opus-4-7:researcher-robbie:implementer (orchestrated by HiC)
**Investigation date**: 2026-05-19

| Field | Value |
|---|---|
| `issue_number` | 1142 |
| `mission_window_days` | 7 |
| `window_deadline` | 2026-05-26 |
| `hypothesis_order` | 1 → 2 → 3 (issue body numbering; spec.md mirrored as H1→H2→H3) |
| `hypothesis_tested` | Hypothesis 1 (RULED OUT) + Hypothesis 2 (CONFIRMED) |
| `commands` | See sections below |
| `evidence` | `research/h1-pip-canary-1142.log`, `research/h1-pip-spec-kitty-1142.log`, `research/h1-run-1142.log`, `research/h2-emitter-walk-1142.md` |
| `conclusion` | RULED_OUT (H1); CONFIRMED (H2) |
| `recommendation` | A — open a 1-WP follow-up mission to broaden the WP01 lifecycle-row predicate to `{Project, Mission, WorkPackage, MissionDossier}` |
| `closing_action` | LEAVE_OPEN_WITH_NEXT_STEP (issue stays open; follow-up mission to be linked) |
| `comment_url` | https://github.com/Priivacy-ai/spec-kitty/issues/1142#issuecomment-4488095110 |
| `posted_at` | 2026-05-19T13:08Z (within 7-day window; window deadline 2026-05-26) |
| `linked_pr` | n/a |
| `follow_up_mission_slug` | TBD — to be filed as a separate mission after this one merges |

## Pre-flight notes (FR-008, FR-009)

- Repo state at start: 7 local commits ahead of `origin/main` (this mission's planning artifacts); `origin/main` was 5 commits ahead of `main` at start (PR #1143 merged, rc14 bump, charter PR #1154, CI fixes). Resolved by `git rebase origin/main` before investigation — clean rebase, no conflicts (this mission only touches a new `kitty-specs/` subdirectory).
- `NEXT-AGENT-HANDOFF.md` confirmed absent at repo root (already deleted during /specify phase).
- PR #1143 (focused-PR carrying parent mission) **MERGED** as commit `fdca93e14`. Therefore the FR-007 cross-branch follow-up update uses the fallback path (edit `mission-exception.md` on `main`, which is where the file now lives).

## State-drift findings worth recording for the comment

1. **Canary scenario paths in the issue body are stale**. The issue body and parent-mission `mission-exception.md` cite `tests/identity_boundary/test_scenario_1_*.py` — that path doesn't exist on `Priivacy-ai/spec-kitty-end-to-end-testing/main`. The scenarios live on PR branch `kitty/pr/sync-identity-boundary-deployed-dev-canary-01KRXVW4-to-main` (PR e2e#42), still open. They have not yet merged into the canary repo's main.
2. **Canary scenarios are deployed-dev tests, not local**. They require `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, `SPEC_KITTY_E2E_TRUSTED_RUNNER=1`, `flyctl auth whoami`, and live SaaS at `https://spec-kitty-dev.fly.dev`. The "10 minute clean-venv repro" framing in the issue body's recommendation underestimated this; the repro is still feasible from an authenticated trusted-runner workstation but it is not a one-line `pytest` call against a fresh venv on any machine.

## Hypothesis 1 — RULED OUT

**Commands run** (cheapest-first, ~5 minutes total):

```bash
# Fresh canary venv against the merged-mission CLI (rc14)
cd /tmp && rm -rf sk-canary-1142 && mkdir sk-canary-1142 && cd sk-canary-1142
git clone https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing.git canary-repo
cd canary-repo
git checkout origin/kitty/pr/sync-identity-boundary-deployed-dev-canary-01KRXVW4-to-main  # PR #42 branch — scenarios live here
python3 -m venv .venv && source .venv/bin/activate
pip install -e .                                                                # canary harness
pip install /Users/robert/spec-kitty-dev/1122-1123-1124-43/spec-kitty            # spec-kitty (non-editable)
spec-kitty --version                                                            # confirmed 3.2.0rc14
SPEC_KITTY_ENABLE_SAAS_SYNC=1 SPEC_KITTY_E2E_TRUSTED_RUNNER=1 \
  pytest tests/identity_boundary/test_scenario_1_*.py tests/identity_boundary/test_scenario_2_*.py \
    -v --capture=no -m sync_identity_boundary_deployed_dev --timeout=60
```

**Result**: Both scenarios FAIL with the same `TeamSpace mission-state migration required... Finding codes: FORBIDDEN_KEY` error described in the issue body. The CLI is `3.2.0rc14` (the merged-mission CLI carrying the WP01 fix from PR #1143). The venv is brand-new — there is no possibility of stale CLI artifacts.

**Verdict**: H1 (stale canary venv) is **ruled out**. The failure reproduces on a verifiably fresh install of the merged-mission CLI.

## Hypothesis 2 — CONFIRMED

Full static audit in `research/h2-emitter-walk-1142.md`. Summary:

- WP01 predicate (`is_mission_lifecycle_row`) restricts lifecycle classification to `aggregate_type == "Mission"`.
- Static walk across the emitter surfaces named in the parent mission finds **3 non-`Mission` aggregate_types** in active lifecycle envelopes:
  - `"Project"` — emitted by `spec-kitty init` (`lifecycle_events.py:410`)
  - `"WorkPackage"` — emitted by WP-lifecycle helper (`lifecycle_events.py:562`)
  - `"MissionDossier"` — emitted in 4 places by `dossier/events.py`
- All lifecycle envelopes structurally carry `event_type` as a top-level key (`_build_envelope`, `lifecycle_events.py:156–169`).
- `detect_forbidden_keys` (`detectors.py:113–148`) only skips envelopes for which `is_mission_lifecycle_row()` returns True. Therefore every non-`Mission` envelope's structural `event_type` key is mis-classified as `FORBIDDEN_KEY`.

**Concrete row** captured in local repro (`spec-kitty init` produced this row in `.kittify/canonical-events.jsonl` on a brand-new project):

```json
{
  "aggregate_id": "23860ff5-ad42-484d-bde7-8c327edf9cba",
  "aggregate_type": "Project",
  "event_id": "01KS05J4W9RCFD9J9D03K4DG71",
  "event_type": "ProjectInitialized",
  ...
}
```

This row, when scanned by the audit, returns one `FORBIDDEN_KEY` finding (key = `"event_type"`).

**Verdict**: H2 (WP01 predicate doesn't cover all lifecycle emitters) is **confirmed by construction**. The fix is to broaden the lifecycle-row classifier from `aggregate_type == "Mission"` to `aggregate_type in {"Project", "Mission", "WorkPackage", "MissionDossier"}` (or rename the function to `is_lifecycle_row` and use a `LIFECYCLE_AGGREGATE_TYPES` constant).

## Hypothesis 3 — not tested

H3 (race between `agent mission create` and `spec-kitty sync now`) was not pursued because H2 already explains the observed failure on its own. H3 may still hold as a separate concern but is not the root cause of the `FORBIDDEN_KEY` blocker reported in #1142.

## Next steps (post-mission)

1. After this mission merges, file a 1-WP follow-up mission titled "Broaden lifecycle-row classifier to all aggregate types" with the predicate-extension scope above. Link it from #1142 and update the `mission-exception.md ## Follow-up` row accordingly. (Per C-003, this mission does NOT include the patch.)
2. Update the issue body's "10 minute clean-venv repro" guidance to acknowledge the deployed-dev environment requirements (`SPEC_KITTY_ENABLE_SAAS_SYNC`, `SPEC_KITTY_E2E_TRUSTED_RUNNER`, live SaaS reachable). This avoids future operators getting stuck on the same "the scenarios don't run locally" friction.
