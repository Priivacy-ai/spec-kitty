---
affected_files: []
cycle_number: 1
mission_slug: sonar-qa-config-remediation-01KWYCX7
reproduction_command:
reviewed_at: '2026-07-07T14:00:00Z'
reviewer_agent: reviewer-renata
verdict: rejected
wp_id: WP01
---

# WP01 review — cycle 1 — reviewer-renata

## Verdict: REQUEST CHANGES (one blocking gate; code itself is sound)

The code, tests, workflow wiring, and gates all PASS. The ONLY blocker is an
unfilled required gate artifact. Fixing it is a ~2-minute transcription; re-review
is a rubber-stamp.

## What is APPROVED (all proven, adversarially)

- **Single-sourced version (FR-001/FR-002):** `scripts/ci/sonar_project_version.py`
  reads `[project].version` from `pyproject.toml` via `tomllib` (resolved 3.2.5).
  No hardcoded/duplicated version; the materialize step strips any existing
  `sonar.projectVersion=` before re-adding, and consumes
  `${{ steps.sonar_version.outputs.version }}`. Survives a bump with zero edits.
- **Raises-not-empty (green-but-broken guard):** module RAISES `ProjectVersionError`
  and emits NOTHING to stdout on missing/blank/non-string/unreadable/malformed
  version. Proven by mutation: a silent-`""` mutant reds exactly 7 tests
  (6 raise-path + `test_main_errors_and_prints_no_version_when_absent`). Workflow
  step has a belt-and-suspenders `if [ -z "$version" ]; then exit 1` so an empty
  capture fails the job rather than stamping an empty projectVersion.
- **Red-first, not tautological:** new tests run against the PRE-FIX tree
  (base branch's unwired `ci-quality.yml` + no script):
    - unit test file: 11 errors (script absent) — genuinely red.
    - static wiring test: 2 core wiring assertions fail ("found 0" script steps).
  The static test is a genuine `yaml.safe_load` parse of the real workflow (not a
  tautology): a hardcoded-literal mutant (`sonar.projectVersion=3.2.5`) reds both
  `test_projectversion_wired_via_extraction_step_output` and
  `test_projectversion_is_not_hardcoded`. Green on the fixed tree: 14/14 pass.
- **Workflow wiring correct:** the `sonarcloud` job is left `schedule` /
  `workflow_dispatch`-gated (unchanged) — no attempt to make it run on PR/push.
  New derive-step gated on `sonar_token.outputs.enabled` consistent with the
  sibling materialize step.
- **Gates:** `ruff` clean; `mypy --strict` clean (3 files); no suppressions
  (`# noqa` / `# type: ignore` / NOSONAR); NFR-001 (no new SONAR_TOKEN) and
  NFR-002 (no ratchet/allowlist) held. Locality (DIR-024) clean: the feat commit
  319cc5c6f touches exactly the 4 owned files + empty `tests/ci/__init__.py`.

## BLOCKER (must fix before approval)

`kitty-specs/sonar-qa-config-remediation-01KWYCX7/issue-matrix.md` is entirely
placeholders — all five rows still `unknown` with `<fill at WP-implementation
time>`. The approval path hard-blocks (FR-037 / mission-review Gate-4:
"issue-matrix.md has unresolved entries. Fill in verdicts before approving.
Unknown: #1928, #2416, #2421, #2422, #825"). Per the file header this is filled
at implementation time — it is the implementer's artifact, so I (read-only) am
not editing it; transcribe the adjudicated verdicts below and re-submit.

### Adjudicated verdicts to transcribe (Title + Verdict + Evidence)

| Issue | Verdict | Rationale / Evidence |
|-------|---------|----------------------|
| #2421 | `fixed` | projectVersion wired from pyproject.toml — commit 319cc5c6f + tests/ci/*. (SC-001b observable post-merge on next nightly; code fix complete in WP01.) |
| #2422 | `in-mission` | coverage-scope interpretability (FR-003/FR-004) is a later WP in this mission. |
| #2416 | `verified-already-fixed` | spec.md provenance: census-gate #2416 (and #2419/#2420) already landed; out of scope here. |
| #825  | `deferred-with-followup` | parent epic umbrella; this mission is the 3-part sonar-config slice only (C-001). |
| #1928 | `deferred-with-followup` | epic (~900-issue backlog slicing) explicitly EXCLUDED by C-001. |

Fill Title cells from the actual issue titles; the Verdict + Evidence columns are
the reviewer determinations above. After filling, move WP01 back to review — the
code needs no further change.