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

**Full run against the configured scope** (`src/specify_cli/`):

```bash
mutmut run
```

This takes ~30–60 minutes for the full codebase. For quick feedback, target
a single module:

```bash
# Scope to one module
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

**Browse the HTML report** (after running):

```bash
mutmut html --output out/reports/mutation/
open out/reports/mutation/index.html  # macOS
xdg-open out/reports/mutation/index.html  # Linux
```

**Export machine-readable JSON stats**:

```bash
mutmut export-cicd-stats --output out/reports/mutation/mutation-stats.json
cat out/reports/mutation/mutation-stats.json
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

## Check mutation score floor

The floor check is the same script used by CI:

```bash
# Check against default 0% floor (always passes during setup)
MUTATION_FLOOR=0 python scripts/check_mutation_floor.py

# Check against a specific floor (e.g., 50%)
MUTATION_FLOOR=50 python scripts/check_mutation_floor.py
```

---

## CI behaviour

| Event | mutation-testing job |
|-------|---------------------|
| `push` | Runs |
| `workflow_dispatch` | Runs |
| Pull request | **Skipped** |

Artifacts are uploaded to `out/reports/mutation/` and available as a
downloadable CI artifact named `mutation-reports`.

---

## Files modified by this feature

| File | Change |
|------|--------|
| `pyproject.toml` | `mutmut>=3.5.0` added to `[project.optional-dependencies].test`; `[tool.mutmut]` config section added |
| `.github/workflows/ci-quality.yml` | `mutation-testing` job added |
| `scripts/check_mutation_floor.py` | New floor-check helper |
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

Ensure `mutmut export-cicd-stats` ran before the floor check. The CI job
steps are ordered to guarantee this.
