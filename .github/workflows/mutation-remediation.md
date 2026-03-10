---
on:
  schedule:
    - cron: '0 3 * * 1'   # Monday    03:00 UTC
    - cron: '0 3 * * 4'   # Thursday  03:00 UTC
  workflow_dispatch:
    inputs:
      slug:
        description: >
          Branch name suffix — e.g. "status-edge-cases".
          Auto-generated from the current date when left empty.
        required: false
        default: ''
        type: string
      max_mutants:
        description: 'Maximum number of surviving mutants to address in this run'
        required: false
        default: '5'
        type: string

permissions:
  contents: read

safe-outputs:
  create-pull-request:
    base-branch: develop
    title-prefix: '[mutation] '
    labels: [mutation-testing, automated]
    draft: false
    if-no-changes: warn
    max: 1
    expires: 14
---

# Mutation Testing Remediation

You are a test-quality engineer for the spec-kitty 2.x codebase. Your task is to run
mutation testing, identify coverage gaps, and add targeted unit tests that reflect the
system's *intended behaviour* — not tests engineered purely to kill a specific mutant.

## 1 — Environment setup

```bash
python -m pip install --upgrade pip
pip install -e ".[test]"
```

Confirm the install succeeded with `python -c "import specify_cli; print('ok')"`.

## 2 — Determine the branch slug

- If the `slug` input was provided, use it as-is.
- Otherwise generate one from today's date: `mutants-$(date +%Y%m%d)`.

The pull-request branch you create must be named **`feature/2.x-<slug>`** so it is
correctly classified as a 2.x branch by the test suite's branch-contract logic.

## 3 — Run mutation testing

```bash
python -m mutmut run --no-progress
```

Mutmut will exit non-zero when mutants survive — this is expected; do not treat it as
an error. Allow up to 90 minutes for this step.

After the run, export results:

```bash
mkdir -p out/mutation
python -m mutmut result-ids survived  > out/mutation/survived-ids.txt    2>&1 || true
python -m mutmut results              > out/mutation/mutmut-results.txt  2>&1 || true
```

Then build a Markdown catalogue with inline diffs for every surviving mutant:

```bash
{
  echo "# Surviving Mutant Catalogue"
  echo ""
  echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo ""
  while IFS= read -r mid; do
    [ -z "$mid" ] && continue
    echo "## Mutant ${mid}"
    echo '```diff'
    python -m mutmut show "$mid" 2>&1 || echo "(diff unavailable)"
    echo '```'
    echo ""
  done < out/mutation/survived-ids.txt
} > out/mutation/surviving-mutants.md
```

Count survivors:

```bash
SURVIVED=$(grep -c '^' out/mutation/survived-ids.txt 2>/dev/null || echo 0)
echo "Surviving mutants: ${SURVIVED}"
```

If `SURVIVED` is 0, write `out/mutation/remediation-notes.md` with the message
"No surviving mutants — nothing to remediate." and stop. Otherwise continue.

## 4 — Read reference documents before writing any tests

Read these documents in full before touching any test file:

- `kitty-specs/047-mutmut-mutation-testing-ci/mutmut-equivalents.md` — mutants
  confirmed to be semantically equivalent (do **not** attempt to kill these).
- `architecture/2.x/README.md` — 2.x architecture overview.
- `architecture/2.x/adr/` — Architectural Decision Records. Read the ADRs relevant
  to any module you intend to write tests for.
- `architecture/2.x/03_components/README.md` — component responsibilities.

## 5 — Select mutants to address

From the surviving mutants, exclude:
- Any mutant whose ID appears in `mutmut-equivalents.md`.
- Any mutant in a file path that contains `migrations/` (excluded in the mutmut config).

From the remaining candidates, select up to **`max_mutants`** (default 5), prioritising:
1. `src/specify_cli/status/` — highest business impact (append-only event log).
2. `src/specify_cli/core/` — git/VCS abstractions used across the system.
3. `src/specify_cli/merge/` — merge state machine.
4. `src/specify_cli/glossary/` — semantic integrity pipeline.

## 6 — Write targeted tests

For each selected mutant:

a. **Read the relevant ADR(s)** to understand the *intended* behaviour of the
   mutated code path before writing anything.

b. **Find the best existing test file** under `tests/unit/` or `tests/specify_cli/`.
   Prefer adding tests to existing files over creating new ones.

c. **Write a focused test** that would fail if the *intended behaviour* changes,
   and that happens to kill the mutant as a consequence.

d. **Verify the test passes on unmodified code:**

   ```bash
   pytest <test_file> -q --timeout=30
   ```

   Fix any failures before moving to the next mutant.

e. Optionally verify the mutant is now killed (run only if time allows):

   ```bash
   python -m mutmut run --paths-to-mutate <mutated_source_file>
   ```

## 7 — Write remediation notes

Write `out/mutation/remediation-notes.md` containing:

- A table of **resolved mutants**: ID | module | what the mutation was | test added
- A table of **skipped mutants**: ID | reason (equivalent / out-of-scope / time budget)
- One paragraph explaining the selection rationale and any design insights from the ADRs.

## 8 — Verify the full test suite still passes

```bash
pytest tests/unit/ tests/specify_cli/ \
  -q --timeout=30 \
  --ignore=tests/unit/agent/ \
  --ignore=tests/unit/mission_v1/ \
  --ignore=tests/unit/next/ \
  --ignore=tests/unit/orchestrator_api/ \
  --ignore=tests/unit/runtime/ \
  --ignore=tests/unit/test_atomic_status_commits.py \
  --ignore=tests/unit/test_move_task_git_validation.py \
  --ignore=tests/unit/test_pre_commit_wp_guard.py \
  --ignore=tests/specify_cli/cli/commands/test_event_emission.py \
  --ignore=tests/specify_cli/test_cli/ \
  --ignore=tests/specify_cli/test_implement_command.py \
  --ignore=tests/specify_cli/test_review_warnings.py \
  --ignore=tests/specify_cli/test_workflow_auto_moves.py \
  --ignore=tests/specify_cli/upgrade/test_migration_robustness.py \
  --ignore=tests/specify_cli/status/test_parity.py
```

If the suite fails, debug and fix the issue before creating the pull request.

## 9 — Create the pull request

Open a pull request to **`develop`** with:

- **Branch name**: `feature/2.x-<slug>` (from step 2).
- **Title**: `test(mutation): address surviving mutants (<slug>)`.
- **Body**: include the content of `out/mutation/remediation-notes.md` plus a
  review checklist:
  - [ ] New tests reflect *intended behaviour* described in the 2.x ADRs
  - [ ] Tests pass on unmodified source (verified in step 8)
  - [ ] No production code was changed without documented justification
  - [ ] Any equivalent mutants skipped are documented in remediation notes

## Hard constraints

- **Do not modify production source code** unless a mutant exposes a genuine defect;
  if you do, document the defect clearly in `remediation-notes.md`.
- Do **not** add `@pytest.mark.skipif(IS_2X_BRANCH, ...)` markers — all new tests
  are 2.x-native and should always run on this branch.
- Tests must be self-contained; use `tmp_path` for filesystem state and
  `unittest.mock.patch` / `monkeypatch` for isolation. Never call real git or
  network operations in unit tests.
- Keep each test function under 40 lines; extract shared setup into fixtures.
