# SonarQube Static Analysis and Quality Gate

Operator reference for running SonarQube (SonarCloud or a self-hosted SonarQube
server) as a static-analysis and quality-gate tool. Use alongside the
[Testing Principles](../../styleguides/built-in/testing-principles.styleguide.yaml)
and [Quadruple-A Test Format](../../styleguides/built-in/quadruple-a-test-format.styleguide.yaml)
styleguides; Sonar tracks the size/complexity/duplication metrics that do **not**
belong in a per-file test gate.

## What Sonar Measures

Sonar analyses source without running it and reports four families of measure:

| Family | What it flags | Typical response |
|--------|---------------|------------------|
| **Coverage** | Lines/branches not exercised by tests, reported per file and as a project trend | Add tests for the uncovered new lines, not the whole file |
| **Maintainability (code smells)** | Cognitive complexity, long methods, duplicated blocks, dead code, confusing constructs | Extract helpers, flatten conditionals, keep complexity within the ceiling |
| **Reliability (bugs)** | Patterns likely to misbehave at runtime (null dereferences, unclosed resources) | Fix the flagged path; add a regression test |
| **Security (hotspots + vulnerabilities)** | Code that touches a security-sensitive API and needs human review (a *hotspot*), or a confirmed weakness (a *vulnerability*) | Review each hotspot; either fix or mark reviewed-safe with a recorded rationale |
| **Duplication** | Copy-pasted blocks above a token threshold | Hoist the shared literal/logic to one home |

## Gate on NEW Code, Not the Whole Project

The single most important configuration choice: evaluate the quality gate on
**new code** (the "Clean as You Code" model), not on the whole-project totals.

- A project-total gate punishes the contributor who touched a legacy file and
  lets a genuinely bad new change through as long as the aggregate stays above a
  threshold.
- A new-code gate asks a bounded, fair question: *is the code this change
  introduced clean?* — new-code coverage, new code smells, new duplication, new
  security hotspots. It is the metric a reviewer can act on for the diff in front
  of them.

Configure the "new code" period (previous version, number of days, or reference
branch) so the gate compares against the right baseline, and require the
**new-code coverage** and **zero new blocker/critical issues** conditions.

```properties
# sonar-project.properties (illustrative)
sonar.projectKey=my-project
sonar.sources=src
sonar.tests=tests
sonar.newCode.referenceBranch=main
```

```bash
# Run the scanner (CI or local)
sonar-scanner -Dsonar.host.url="$SONAR_HOST_URL"
```

## Loopback-Safe URLs — Do NOT Force HTTPS on 127.0.0.1

A local SonarQube server or a local control-plane endpoint is commonly reachable
at `http://127.0.0.1:9000` (or `http://localhost:9000`). This is an intentional
loopback transport: traffic never leaves the machine.

- **Do not "fix" a loopback `http://127.0.0.1` / `http://localhost` URL by
  forcing it to `https://`.** There is no man-in-the-middle to protect against on
  the loopback interface, and a forced-HTTPS local URL simply fails to connect.
- If Sonar raises a hotspot on an `http://` control-plane or Sonar URL that is
  loopback-only, keep the safe loopback semantics, keep or add a regression test
  that pins the loopback host, and record the rationale in the hotspot review /
  PR body. The code change and the hotspot review are **separate actions**: a
  loopback URL is correct code, and the hotspot is discharged by review, not by a
  transport change.

## Working the Findings

- **New-code coverage below target** — add tests for the specific new lines Sonar
  lists, exercising the new branches directly; do not chase the whole-file
  number.
- **Repeated literal (S1192) / duplication** — hoist a string/path/message that
  recurs three or more times in a module to a named constant.
- **Cognitive complexity (S3776) / ruff `C901`** — the two are aligned; keep a
  touched function at or below the configured ceiling by extracting deterministic
  helpers, then test those helpers directly.
- **Security hotspot** — review each one. Fix, or mark it reviewed-safe with a
  concrete reason (loopback-only transport, validated input, etc.). Never blanket-
  suppress to clear the list.
- **Remaining UI-side work** — if the code is correct but Sonar still needs a
  hotspot review or a UI-side rationale, say so explicitly in the PR body so a
  later reviewer does not try to "fix" correct code.

## Red Flags

- A gate configured on project totals rather than new code — it hides new debt
  behind a large clean legacy base.
- Suppression comments added purely to clear findings, with no rationale — this
  moves the debt, it does not resolve it.
- A forced-HTTPS rewrite of a loopback URL — a transport change masquerading as a
  security fix, which breaks the local connection.
