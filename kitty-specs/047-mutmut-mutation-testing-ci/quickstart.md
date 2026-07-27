# Quickstart: Mutation Testing with mutmut

*Phase 1 output for feature 047 — local developer guide*

## Prerequisites

Install the test dependencies (includes mutmut):

```bash
pip install -e ".[test]"
```

Verify mutmut is available:

```bash
mutmut --version
# mutmut 3.x.x
```

---

## Run mutation testing locally

**Full run against the configured scope** (status, glossary, merge, core):

```bash
mutmut run
```

This takes ~30–60 minutes for the full scope. For quick feedback, target
a single module:

```bash
mutmut run --paths-to-mutate src/specify_cli/status/
```

---

## Inspect results

**Summary of all mutants**:

```bash
mutmut results
```

**Show the source diff for a specific mutant** (replace `42` with the ID):

```bash
mutmut show 42
```

**Export machine-readable JSON stats**:

```bash
# mutmut 3.5.0 writes to mutants/mutmut-cicd-stats.json (no --output flag)
mutmut export-cicd-stats
cat mutants/mutmut-cicd-stats.json
```

---

## Fix a surviving mutant

1. Find surviving mutants:
   ```bash
   mutmut results | grep -i surviving
   ```

2. Inspect the mutant diff:
   ```bash
   mutmut show <id>
   ```

3. Write a test that exercises the code path the mutant changed.

4. Re-run mutmut on the affected file:
   ```bash
   mutmut run --paths-to-mutate src/specify_cli/<module>/
   ```

5. Confirm the mutant is now killed:
   ```bash
   mutmut results | grep <id>
   # Should show: killed
   ```

---

## Check mutation score locally

The floor check is the same script used by CI. It is advisory — it
reports the score but never exits non-zero:

```bash
MUTATION_FLOOR=70 python scripts/check_mutation_floor.py
```

When the score is below the floor, the script prints a markdown summary
listing surviving mutants. In CI this is written to `GITHUB_STEP_SUMMARY`.

---

## CI behaviour

| Event | mutation-testing job |
|-------|---------------------|
| `push` | Runs (scoped to changed files in mutation directories) |
| `workflow_dispatch` | Runs (scoped to changed files in mutation directories) |
| Pull request | **Skipped** |

The job is **advisory** — it never blocks the pipeline. When the score
is below the floor, a summary with surviving mutants appears in the
GitHub Actions step summary.

If no Python files in the mutation scope (`status/`, `glossary/`,
`merge/`, `core/`) were changed, the job skips entirely.

Artifacts are uploaded to `out/reports/mutation/` and available as a
downloadable CI artifact named `mutation-reports`.

---

## Files modified by this feature

| File | Change |
|------|--------|
| `pyproject.toml` | `mutmut>=3.5.0` added to `[project.optional-dependencies].test`; `[tool.mutmut]` config section added |
| `.github/workflows/ci-quality.yml` | `mutation-testing` job added (advisory, scoped to changed files) |
| `scripts/check_mutation_floor.py` | Advisory floor-check helper (writes markdown to `GITHUB_STEP_SUMMARY`) |
| `.gitignore` | `mutmut.db`, `mutmut-cache/` added |

---

## Troubleshooting

**`mutmut run` hangs on a slow test**

mutmut 3.x respects `--timeout` in the runner command. The default config
sets `--timeout=30` per-test. Timed-out mutants are counted separately and
do not fail the run.

**`export-cicd-stats` produces empty JSON**

Run `mutmut run` first — the stats command reads from `mutmut.db` which is
populated by the run step.

**Floor check script can't find the JSON file**

Ensure `mutmut export-cicd-stats` ran before the floor check. In CI the
steps are ordered to guarantee this. Locally, the stats file is at
`mutants/mutmut-cicd-stats.json` (not `out/reports/mutation/`).
