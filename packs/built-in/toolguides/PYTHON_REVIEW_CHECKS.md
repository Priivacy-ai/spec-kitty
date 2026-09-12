# Python Review Checks

Automated checks a reviewer should run — or verify the implementer has run — before approving Python code changes. Each tool catches a different category of defect; no single tool replaces the others.

## Formatting

### ruff format (or black)

Enforces consistent code formatting so diffs stay clean and review focuses on logic, not whitespace.

```bash
ruff format --check src/ tests/
# or: black --check src/ tests/
```

**What it catches:** inconsistent indentation, trailing whitespace, quote style drift, line length violations.
**Review signal:** if formatting is not clean, the implementer skipped the quality gate.

## Linting

### ruff check

Fast, comprehensive linter replacing flake8, isort, pydocstyle, pyupgrade, and dozens of plugins in a single tool.

```bash
ruff check src/ tests/
```

**What it catches:** unused imports, undefined names, PEP 8 violations, import ordering, common anti-patterns, use of deprecated APIs.
**Key rule sets:** E (pycodestyle errors), W (warnings), F (pyflakes), I (isort), B (bugbear), C4 (comprehensions), UP (pyupgrade).

## Type Safety

### mypy

Static type checker that catches interface drift, wrong argument types, and missing return types before runtime.

```bash
mypy src/
# strict mode recommended:
mypy --strict src/
```

**What it catches:** type mismatches, missing annotations on public APIs, incompatible overrides, unreachable code branches, incorrect Optional handling.
**Review signal:** type errors in changed files indicate the implementation deviates from the declared interface contract.

## Architecture

### import-linter

Enforces module dependency rules — prevents coupling violations between architectural layers or bounded contexts.

```bash
lint-imports
```

**What it catches:** imports that violate declared layer boundaries (e.g., CLI importing directly from database layer, domain importing from infrastructure).
**Configuration:** `.importlinter` or `pyproject.toml [tool.importlinter]` with contract definitions.

### pytestarch / pyarchtest

Architecture testing — verifies structural rules as executable tests (similar to ArchUnit for Java).

```bash
pytest tests/architecture/ -v
```

**What it catches:** classes in wrong packages, forbidden dependencies between modules, naming convention violations, circular imports.
**Example rule:** "Modules in `src/specify_cli/status/` must not import from `src/specify_cli/cli/`."

## Security and Supply Chain

### bandit

Static security analysis for Python — finds common vulnerabilities in code.

```bash
bandit -r src/ -f json
```

**What it catches:** hardcoded passwords, use of `eval`/`exec`, insecure temporary files, weak cryptography, SQL injection patterns, shell injection via `subprocess`.

### pip-audit

Checks installed dependencies against known vulnerability databases.

```bash
pip-audit
```

**What it catches:** CVEs in direct and transitive dependencies, outdated packages with known security issues.

### cyclonedx-bom

Generates a Software Bill of Materials (SBOM) for license compliance and supply chain auditing.

```bash
cyclonedx-py environment -o sbom.json
```

**What it catches:** license violations, undeclared transitive dependencies, supply chain gaps.
**When to run:** before releases, during compliance reviews, when adding new dependencies.

## Test Quality

### pytest + pytest-cov

Test runner with coverage measurement.

```bash
pytest --cov=src --cov-report=term-missing tests/
```

**What it catches:** regressions, coverage gaps in new code, uncovered error paths.
**Review signal:** new code with no corresponding tests, or coverage drop, indicates the quality gate was not met.

### vulture

Dead code detector — finds unused functions, variables, imports, and classes.

```bash
vulture src/ --min-confidence 80
```

**What it catches:** functions that were refactored away but not removed, unused imports that linting missed, dead code branches.
**Review signal:** dead code in the diff suggests incomplete cleanup after refactoring.

### mutmut (optional, high-cost)

Mutation testing — modifies code and checks whether tests catch the mutations. Measures test suite effectiveness beyond line coverage.

```bash
mutmut run --paths-to-mutate=src/specify_cli/status/
mutmut results
```

**What it catches:** tests that achieve high coverage but don't actually assert meaningful behavior (weak assertions, tests that pass regardless of code changes).
**When to run:** for critical modules where correctness is paramount. Too slow for full-codebase runs on every PR.

## Review Checklist Order

Run checks in this order during review — cheapest and fastest first:

1. **ruff format --check** (seconds) — formatting clean?
2. **ruff check** (seconds) — linting clean?
3. **mypy** (seconds-minutes) — types correct?
4. **pytest** (seconds-minutes) — tests pass, coverage met?
5. **lint-imports** (seconds) — architecture rules respected?
6. **bandit** (seconds) — no security anti-patterns?
7. **pip-audit** (seconds) — no known CVEs in dependencies?
8. **vulture** (seconds) — no dead code introduced?
9. **cyclonedx-bom** (on release) — SBOM generated?
10. **mutmut** (minutes-hours, optional) — mutation score acceptable?

Stop at first failure and feed back to the implementer. Do not proceed to expensive checks while cheap checks are red.
