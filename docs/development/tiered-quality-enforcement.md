# Tiered Quality Enforcement

## Purpose

The codebase contains code at very different levels of criticality and testability.
A single global coverage threshold (previously 90%) fails in both directions: it is
too strict for glue/integration code that is inherently hard to unit-test, and too
lenient as a signal for the core domain logic that must be reliably covered.

This document describes the three-tier model that replaces the global threshold,
how it is enforced consistently between local development and CI, and how it
interacts with SonarCloud and dedicated security tooling.

---

## The Three Tiers

| Tier | Intent | Coverage enforcement | SonarCloud |
|---|---|---|---|
| **core** | Critical domain logic. Must be well-tested and well-understood. | Hard threshold (80%+) | Full analysis: quality + security + coverage |
| **supporting** | Important but I/O-heavy or CLI-bound code. Best-effort coverage. | Soft threshold (55%+) | Quality + security; reduced coverage expectation |
| **glue** | Orchestration, UI, scripts. Thin wiring, hard to unit-test. | Not enforced (0%) | Security only (Bandit); excluded from Sonar coverage metrics |

### Package classification

```
core
  src/specify_cli/status/          # canonical state machine
  src/specify_cli/core/            # core domain abstractions
  src/specify_cli/merge/           # merge orchestration
  src/specify_cli/constitution/    # quality model
  src/specify_cli/git/             # VCS operations
  src/specify_cli/events/          # event system
  src/specify_cli/next/            # next-generation runtime
  src/specify_cli/spec_kitty_events/  # vendored event model
  src/doctrine/                    # doctrine/knowledge-base Python modules

supporting
  src/specify_cli/cli/             # CLI commands (typer wrappers)
  src/specify_cli/glossary/        # glossary pipeline
  src/specify_cli/sync/            # sync protocol
  src/specify_cli/frontmatter.py   # YAML frontmatter parsing

glue
  src/specify_cli/orchestrator/    # orchestrator integration points
  src/specify_cli/orchestrator_api/
  src/specify_cli/dashboard/       # web UI (Playwright-tested separately)
  src/specify_cli/scripts/         # utility scripts
  src/specify_cli/missions/        # mission template runners
```

---

## Single Source of Truth: `pyproject.toml`

All tier membership and thresholds are declared in `pyproject.toml` under
`[tool.coverage_tiers]`. Every other config file (SonarCloud, CI steps) derives
from this, either by reading it directly or by keeping a documented mapping.

```toml
[tool.coverage_tiers]

[tool.coverage_tiers.core]
include = [
    "src/specify_cli/status/*",
    "src/specify_cli/core/*",
    "src/specify_cli/merge/*",
    "src/specify_cli/constitution/*",
    "src/specify_cli/git/*",
    "src/specify_cli/events/*",
    "src/specify_cli/next/*",
    "src/specify_cli/spec_kitty_events/*",
    "src/doctrine/*",
]
min_coverage = 80

[tool.coverage_tiers.supporting]
include = [
    "src/specify_cli/cli/*",
    "src/specify_cli/glossary/*",
    "src/specify_cli/sync/*",
    "src/specify_cli/frontmatter.py",
]
min_coverage = 55

[tool.coverage_tiers.glue]
include = [
    "src/specify_cli/orchestrator/*",
    "src/specify_cli/orchestrator_api/*",
    "src/specify_cli/dashboard/*",
    "src/specify_cli/scripts/*",
    "src/specify_cli/missions/*",
]
min_coverage = 0   # tracked but not enforced
```

---

## Coverage Checking Script

`scripts/check_coverage.py` reads the tier config and calls `coverage report`
once per non-glue tier. It uses the `.coverage` data file produced by the preceding
`pytest --cov` run -- no tests are re-executed.

```
pytest --cov=src/... --cov-report=xml   ->  .coverage (data file)
python scripts/check_coverage.py        ->  per-tier pass/fail
```

Both CI and local development call the same script. The global `--cov-fail-under`
flag is **removed** from the pytest invocation; all threshold logic lives in the
script.

### Running locally

```bash
# Generate coverage data (same flags as CI, minus --cov-fail-under)
python -m pytest \
    tests/unit/ tests/doctrine/ tests/contract/ \
    -m "not e2e and not slow and not distribution and not orchestrator_smoke" \
    --cov=src/specify_cli \
    --cov=src/doctrine \
    --cov-report=term-missing \
    --cov-report=xml:out/reports/coverage/coverage.xml

# Check tier thresholds
python scripts/check_coverage.py
```

### CI change (`ci-quality.yml`)

```yaml
# In the unit-tests job:

- name: Run unit tests with coverage
  run: |
    python -m pytest \
      -v \
      tests/unit/ tests/doctrine/ tests/contract/ \
      -m "not e2e and not slow and not distribution and not orchestrator_smoke" \
      --cov=src/specify_cli \
      --cov=src/doctrine \
      --cov-report=term-missing \
      --cov-report=xml:out/reports/coverage/coverage.xml \
      --junitxml=out/reports/xunit-reports/xunit-result-unit-${{ github.run_id }}.xml
      # NOTE: --cov-fail-under removed; tiered check below replaces it

- name: Check tiered coverage thresholds
  run: python scripts/check_coverage.py
```

---

## SonarCloud Configuration

SonarCloud has no first-class "exclude from quality but keep security" toggle.
The property `sonar.exclusions` removes files from all analysis including
security hotspots -- that is too broad for glue code. The correct combination is:

| Property | Effect | Applied to |
|---|---|---|
| `sonar.coverage.exclusions` | Drops coverage metric only; quality and security still run | glue paths |
| `sonar.issue.ignore.multicriteria` | Suppresses named rule keys for named file patterns | curated non-security Python rules on glue paths |

`sonar.coverage.exclusions` handles the coverage metric cleanly. For quality
issue suppression on glue paths, `sonar.issue.ignore.multicriteria` can target
specific rule categories (complexity, conventions, maintainability). Security-tagged
rules (OWASP, CWE, injection) are not included in the suppression list and will
continue to surface for glue code.

### `sonar-project.properties` additions

```properties
# Glue tier: exclude from coverage metrics.
# Quality issues are suppressed separately (see multicriteria below).
# Security rules are NOT suppressed -- Bandit (see below) covers these more thoroughly.
sonar.coverage.exclusions=\
    src/specify_cli/orchestrator/**,\
    src/specify_cli/orchestrator_api/**,\
    src/specify_cli/dashboard/**,\
    src/specify_cli/scripts/**,\
    src/specify_cli/missions/**

# Supporting tier: reduced coverage expectation; no issue suppression.
# (Coverage threshold is enforced by scripts/check_coverage.py, not Sonar.)

# Suppress Python quality rules (non-security) on glue paths.
# Security-tagged rules (python:S2076, python:S2083, etc.) are intentionally omitted.
sonar.issue.ignore.multicriteria=glue_complexity,glue_conventions,glue_design

sonar.issue.ignore.multicriteria.glue_complexity.ruleKey=python:S3776
sonar.issue.ignore.multicriteria.glue_complexity.resourceKey=src/specify_cli/orchestrator/**

sonar.issue.ignore.multicriteria.glue_conventions.ruleKey=python:S1192
sonar.issue.ignore.multicriteria.glue_conventions.resourceKey=src/specify_cli/dashboard/**

# Add additional (ruleKey, resourceKey) pairs as needed following the pattern above.
# Do NOT use ruleKey=* -- that would also suppress security rules.
```

> **Keeping in sync**: When tier membership changes in `pyproject.toml`, update
> `sonar.coverage.exclusions` in `sonar-project.properties` to match. Both files
> carry a comment pointing to the other. No automated sync script is used -- tier
> changes are infrequent and the two-file update is explicit and reviewable.

---

## Security Scanning (OWASP / CVE)

SonarCloud's Python security analysis covers some OWASP categories but is not
purpose-built for it. Glue code must still be scanned for security issues. Two
dedicated tools cover this:

### Bandit -- Python SAST (all tiers)

[Bandit](https://bandit.readthedocs.io/) is a Python-specific static analysis
tool focused entirely on security. It runs on **all source code** regardless of
tier, so glue code receives full OWASP coverage even when excluded from Sonar
quality analysis.

```yaml
# In ci-quality.yml, lint job or a dedicated security job:
- name: Run Bandit security scan
  run: |
    python -m bandit -r src/ \
      --severity-level medium \
      --confidence-level medium \
      -f json \
      -o out/reports/bandit/bandit-report.json
  continue-on-error: false
```

Add `bandit` to `[project.optional-dependencies] test` in `pyproject.toml`.

### pip-audit -- CVE / dependency scanning

[pip-audit](https://pypi.org/project/pip-audit/) scans installed packages against
known CVE databases. It operates at the dependency level and is not path-scoped,
so it inherently covers all tiers.

```yaml
- name: Run pip-audit CVE scan
  run: |
    python -m pip_audit \
      --output json \
      --output-file out/reports/pip-audit/pip-audit-report.json
  continue-on-error: false
```

Add `pip-audit` to `[project.optional-dependencies] test` in `pyproject.toml`.

---

## Summary: What enforces what

| Check | Tool | Scope | Blocks CI |
|---|---|---|---|
| Coverage - core (80%) | `check_coverage.py` | core tier | Yes |
| Coverage - supporting (55%) | `check_coverage.py` | supporting tier | Yes |
| Coverage - glue | not enforced | - | No |
| Quality issues | SonarCloud quality gate | core + supporting | Yes (gate) |
| Quality issues on glue | Suppressed per `sonar.issue.ignore.multicriteria` | glue | No |
| Security (Python SAST) | Bandit | all tiers | Yes |
| Security (CVE / deps) | pip-audit | all dependencies | Yes |
| Security (Sonar) | SonarCloud | core + supporting | Yes (gate) |
| Security (Sonar, glue) | SonarCloud | glue (not in `sonar.exclusions`) | Yes (gate) |

---

## Adjusting thresholds

Set thresholds to reflect current reality, then raise them incrementally as
coverage improves. Never set a threshold higher than the current measured value
without a plan to cover the gap in the same PR.

To find current per-tier coverage before setting initial thresholds:

```bash
# Run coverage, then inspect per-tier
python -m pytest tests/unit/ tests/doctrine/ tests/contract/ \
    -m "not e2e and not slow and not distribution and not orchestrator_smoke" \
    --cov=src/specify_cli --cov=src/doctrine --cov-report=term-missing -q

# Check a specific tier manually
python -m coverage report --include="src/specify_cli/status/*" | tail -1
python -m coverage report --include="src/specify_cli/core/*"   | tail -1
```
