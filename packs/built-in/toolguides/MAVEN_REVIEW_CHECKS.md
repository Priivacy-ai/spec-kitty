# Maven Review Checks

Automated checks a reviewer should run — or verify the implementer has run — before approving Java code changes. Each tool catches a different category of defect; no single tool replaces the others.

## Compilation

```bash
mvn compile
```

**What it catches:** syntax errors, missing imports, type mismatches that the IDE may not have flagged.
**Review signal:** a failing compile means the change is not ready for review.

## Tests

```bash
mvn test
```

**What it catches:** regressions, broken contracts, missing edge-case coverage.
**Review signal:** any test failure in changed or downstream code blocks merge.

## Coverage

```bash
mvn verify -Pcoverage
# or with jacoco plugin directly:
mvn jacoco:report
```

**What it catches:** new production code with no corresponding tests, coverage regression below project threshold.
**Configuration:** `jacoco-maven-plugin` in `pom.xml`; project target is typically ≥80% line and branch coverage.

## Style

### Checkstyle

Enforces consistent naming, formatting, and code organisation rules defined in the project Checkstyle configuration.

```bash
mvn checkstyle:check
```

**What it catches:** naming convention violations, missing Javadoc on public APIs, import ordering, line length, whitespace inconsistencies.
**Configuration:** `checkstyle-maven-plugin` + `checkstyle.xml` (usually in `src/main/resources` or a shared parent POM).

## Static Analysis

### SpotBugs

Bytecode-level static analysis. Finds common defects that compilation and style checks miss.

```bash
mvn spotbugs:check
```

**What it catches:** null dereferences, resource leaks (unclosed streams), incorrect `equals`/`hashCode` implementations, synchronization errors, use of deprecated or dangerous APIs.
**Review signal:** any SpotBugs finding at the configured severity threshold (typically MEDIUM+) blocks merge.

## Architecture

### ArchUnit (via tests)

Architecture rules expressed as executable tests, analogous to pytestarch for Python.

```bash
mvn test -Dtest="*ArchTest,*ArchitectureTest"
# or run all tests (ArchUnit tests live alongside unit tests):
mvn test
```

**What it catches:** layer boundary violations (e.g., domain importing from infrastructure), forbidden dependencies between packages, naming convention violations at the type level, circular dependencies.
**Example rule:** `classes in package ..domain.. should not depend on ..infrastructure..`

## Security

### OWASP Dependency-Check

Scans project dependencies against the National Vulnerability Database for known CVEs.

```bash
mvn dependency-check:check
```

**What it catches:** CVEs in direct and transitive Maven dependencies.
**When to run:** before releases and when adding or upgrading dependencies. Can be slow on first run (downloads NVD data).

## Test Quality

### PIT Mutation Testing (optional, high-cost)

Modifies bytecode and reruns tests to verify that the test suite actually detects defects.

```bash
mvn org.pitest:pitest-maven:mutationCoverage
```

**What it catches:** tests that achieve high line coverage but do not assert meaningful behavior — mutations that survive indicate weak or missing assertions.
**When to run:** for critical domain modules where correctness is paramount. Too slow for full-codebase runs on every PR. Use `targetClasses` and `targetTests` to scope to the changed module.

## Review Checklist Order

Run checks in this order — cheapest and fastest first:

1. **mvn compile** (seconds) — compiles cleanly?
2. **mvn checkstyle:check** (seconds) — style rules met?
3. **mvn test** (seconds–minutes) — all tests pass?
4. **mvn verify -Pcoverage** (seconds–minutes) — coverage meets threshold?
5. **mvn spotbugs:check** (seconds–minutes) — no static analysis findings?
6. **ArchUnit tests** (part of mvn test) — architecture rules respected?
7. **mvn dependency-check:check** (minutes, on dep changes) — no known CVEs?
8. **mvn pitest:mutationCoverage** (minutes–hours, optional) — mutation score acceptable?

Stop at first failure and feed back to the implementer. Do not proceed to expensive checks while cheap checks are red.
