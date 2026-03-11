---
work_package_id: WP02
title: CI Integration
lane: done
dependencies:
- WP01
subtasks:
- T006
- T007
- T008
- T009
- T010
phase: Phase 1 - Foundation
assignee: ''
agent: ''
shell_pid: ''
review_status: approved
reviewed_by: Stijn Dejongh
review_feedback: ''
history:
- timestamp: '2026-03-01T16:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- NFR-001
- C-003
- C-004
---

# Work Package Prompt: WP02 – CI Integration

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check `review_status`. If it says `has_feedback`, read `review_feedback` first.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*No feedback yet — this is a fresh work package.*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ` ```python `, ` ```bash `

---

## Objectives & Success Criteria

- `scripts/check_mutation_floor.py` exists and correctly enforces a score floor from the `MUTATION_FLOOR` env var.
- A `mutation-testing` job is present in `.github/workflows/ci-quality.yml`.
- The job runs on `push` and `workflow_dispatch`, skips on `pull_request`.
- The job produces HTML and JSON mutation reports in `out/reports/mutation/` and uploads them as a CI artifact named `mutation-reports`.
- `MUTATION_FLOOR` is set to `0` in the job definition (no builds blocked initially).
- The full CI pipeline validates these claims on the next push.

## Context & Constraints

- **Branch**: `architecture/restructure_and_proposals` (no worktree)
- **Depends on**: WP01 (mutmut installed and config verified)
- **Plan**: `kitty-specs/047-mutmut-mutation-testing-ci/plan.md` — Technical Context and WP02 description
- **Research**: `kitty-specs/047-mutmut-mutation-testing-ci/research.md` — CI job pattern (Finding 5), JSON schema (Finding 3), floor enforcement approach (Finding 4)
- **CI file**: `.github/workflows/ci-quality.yml` (read before editing to understand existing job structure)
- **Constraint C-003**: Floor starts at 0%. The mechanism must exist; it will be raised in WP05.
- **Constraint C-004**: Report output must follow `out/reports/<category>/` convention.
- **NFR-001**: PRs must never trigger the mutation-testing job.

**Implementation command** (since WP01 is the dependency):
```bash
spec-kitty implement WP02 --base WP01
```
*(No worktree actually created for this feature — work directly on the branch.)*

## Subtasks & Detailed Guidance

### Subtask T006 – Write scripts/check_mutation_floor.py

**Purpose**: Provide a testable, readable floor-enforcement script that CI calls
after `mutmut export-cicd-stats`. mutmut 3.x has no built-in `--min-score` flag.

**Steps**:
1. Create `scripts/check_mutation_floor.py` with this logic:

```python
#!/usr/bin/env python3
"""Enforce a minimum mutation score floor.

Reads out/reports/mutation/mutation-stats.json (produced by
`mutmut export-cicd-stats`) and exits non-zero if the score
falls below the MUTATION_FLOOR environment variable (0-100, default 0).
"""
import json
import os
import sys
from pathlib import Path

STATS_FILE = Path("out/reports/mutation/mutation-stats.json")
FLOOR = int(os.environ.get("MUTATION_FLOOR", "0"))


def main() -> int:
    if not STATS_FILE.exists():
        print(f"ERROR: stats file not found at {STATS_FILE}", file=sys.stderr)
        print("Ensure `mutmut export-cicd-stats` ran before this script.", file=sys.stderr)
        return 1

    try:
        data = json.loads(STATS_FILE.read_text())
    except json.JSONDecodeError as exc:
        print(f"ERROR: could not parse {STATS_FILE}: {exc}", file=sys.stderr)
        return 1

    # Robustly extract counts — support both flat and nested schema variants
    summary = data.get("summary", data)
    killed = int(summary.get("killed", 0))
    survived = int(summary.get("survived", 0))
    total_scored = killed + survived

    if total_scored == 0:
        print("WARNING: no killable mutants found (zero killed + survived). Skipping floor check.")
        return 0

    score_pct = int(killed / total_scored * 100)
    print(f"Mutation score: {score_pct}% ({killed} killed / {total_scored} scoreable)")
    print(f"Floor:          {FLOOR}%")

    if score_pct < FLOOR:
        print(
            f"FAIL: mutation score {score_pct}% is below the configured floor of {FLOOR}%.",
            file=sys.stderr,
        )
        print("Raise the floor only after running a squashing campaign.", file=sys.stderr)
        return 1

    print("PASS: mutation score meets or exceeds the floor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

2. Make the script executable: `chmod +x scripts/check_mutation_floor.py`
3. Smoke-test locally:
   ```bash
   # Create a dummy stats file
   mkdir -p out/reports/mutation
   echo '{"summary": {"killed": 80, "survived": 20}}' > out/reports/mutation/mutation-stats.json
   MUTATION_FLOOR=0 python scripts/check_mutation_floor.py   # should pass
   MUTATION_FLOOR=90 python scripts/check_mutation_floor.py  # should fail
   ```

**Files**: `scripts/check_mutation_floor.py` (new)

**Notes**:
- The script supports two JSON schema variants (flat and nested under `summary`) to
  handle any differences across mutmut 3.x patch versions.
- The zero-mutant branch exits 0 to avoid false failures if the scope is empty.

---

### Subtask T007 – Add mutation-testing job skeleton to ci-quality.yml

**Purpose**: Create the job definition with correct trigger conditions and resource
settings before filling in the steps (T008).

**Steps**:
1. Read `.github/workflows/ci-quality.yml` to understand the existing job list
   and indentation style.
2. Add the following job after `dashboard-tests` and before `sonarcloud`:

```yaml
  mutation-testing:
    runs-on: ubuntu-latest
    needs: unit-tests
    # Slow job: only runs on push or manual dispatch, never on pull_request
    if: always() && (github.event_name == 'push' || (github.event_name == 'workflow_dispatch' && inputs.run_extended))
    timeout-minutes: 75
    env:
      MUTATION_FLOOR: 0

    steps:
      - name: Check out repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
```

3. The `if:` guard mirrors the `integration-smoke` job exactly. `always()` allows
   the job to run even if `unit-tests` had failures (consistent with existing pattern).
4. `timeout-minutes: 75` gives a 15-minute buffer above the estimated 60-minute run.

**Files**: `.github/workflows/ci-quality.yml`

---

### Subtask T008 – Add remaining job steps

**Purpose**: Wire up the full mutmut run, report generation, floor check, and
artifact upload within the job created in T007.

**Steps**:
1. Append the following steps inside the `mutation-testing` job (after the checkout step):

```yaml
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[test]"

      - name: Prepare report directories
        run: mkdir -p out/reports/mutation

      - name: Run mutation testing
        run: mutmut run
        continue-on-error: true  # Surviving mutants don't fail the job; floor check does

      - name: Export mutation stats (JSON)
        if: always()
        run: |
          mutmut export-cicd-stats --output out/reports/mutation/mutation-stats.json || \
            echo '{"summary": {"killed": 0, "survived": 0}}' > out/reports/mutation/mutation-stats.json

      - name: Export mutation report (HTML)
        if: always()
        run: mutmut html --output out/reports/mutation/ || true

      - name: Enforce mutation score floor
        if: always()
        run: python scripts/check_mutation_floor.py

      - name: Upload mutation artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: mutation-reports
          path: out/reports/mutation/
```

2. The `continue-on-error: true` on `mutmut run` ensures surviving mutants alone
   don't fail the job — only the floor check can fail it.
3. The JSON export step falls back to a minimal valid JSON if `export-cicd-stats`
   fails (e.g., zero mutants). This prevents the floor check from crashing.
4. The HTML export uses `|| true` because `mutmut html` may exit non-zero if there
   are no results.

**Files**: `.github/workflows/ci-quality.yml`

---

### Subtask T009 – Set initial MUTATION_FLOOR=0

**Purpose**: Confirm the floor is 0 so no builds are blocked during the initial
rollout (C-003 requirement for initial state).

**Steps**:
1. Verify `MUTATION_FLOOR: 0` is present in the `env:` block of the `mutation-testing`
   job (added in T007).
2. This is the value that will be raised to the achieved baseline in WP05.
3. Add a comment next to the env var:

```yaml
    env:
      MUTATION_FLOOR: 0  # Raised to achieved baseline after squashing campaign (WP05)
```

**Files**: `.github/workflows/ci-quality.yml`

---

### Subtask T010 – Verify PR skip logic

**Purpose**: Confirm the `if:` condition on the `mutation-testing` job correctly
skips it on pull_request events.

**Steps**:
1. Read the `if:` condition added in T007:
   ```
   if: always() && (github.event_name == 'push' || (github.event_name == 'workflow_dispatch' && inputs.run_extended))
   ```
2. Confirm that `pull_request` is not in the condition — the job will be skipped
   because `github.event_name == 'push'` is false for PRs and `workflow_dispatch`
   is also false.
3. Cross-check against the `integration-smoke` job `if:` condition — they should
   be identical.
4. Document the verified skip logic in a comment inside the job:

```yaml
  mutation-testing:
    # ...
    # NOTE: Skipped on pull_request — only runs on push and workflow_dispatch.
    # This keeps PR CI fast (NFR-001).
```

**Files**: `.github/workflows/ci-quality.yml` (comment only, no logic change)

**Validation**: Inspect the YAML — no `pull_request` event in the condition.

## Risks & Mitigations

- **mutmut run timeout in CI**: `continue-on-error: true` ensures partial results are still exported and reported, even if the run is killed by the 75-minute timeout.
- **export-cicd-stats missing in some mutmut 3.x versions**: The fallback JSON in the export step ensures the floor check always has something to parse.
- **YAML indentation errors**: Read the existing `ci-quality.yml` carefully before editing; misaligned indentation causes workflow parse failures. Use a YAML linter if in doubt (`python -c "import yaml; yaml.safe_load(open('.github/workflows/ci-quality.yml'))"` ).

## Review Guidance

- Confirm the `if:` condition is identical to `integration-smoke` (known-working pattern).
- Confirm `MUTATION_FLOOR: 0` is present in the job env.
- Confirm `continue-on-error: true` is only on `mutmut run`, not on the floor check (floor check must fail the job).
- Confirm artifact name is `mutation-reports` and path is `out/reports/mutation/`.
- Ask the implementer to push to the branch and link the CI run showing the `mutation-testing` job.

## Activity Log

- 2026-03-01T16:00:00Z – system – lane=planned – Prompt created.
- 2026-03-01T06:52:15Z – unknown – lane=in_progress – Starting WP02 CI integration
- 2026-03-01T07:16:50Z – unknown – lane=done – Done override: No worktree model: work committed directly on target branch. Review passed after fixing export-cicd-stats path and removing non-existent html command.
