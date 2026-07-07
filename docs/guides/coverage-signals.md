---
title: Coverage signals — reconciling the three "coverage" numbers
description: 'Why SonarCloud coverage, new_coverage, and the internal diff-coverage CI gate disagree — and how to tell an expected scope difference from a real coverage regression.'
doc_status: active
updated: '2026-07-08'
related:
- docs/guides/testing-flakiness.md
- docs/guides/testing-parallel.md
- docs/guides/review-gates.md
- .github/workflows/ci-quality.yml
- sonar-project.properties
- scripts/ci/sonarcloud_branch_review.sh
---
# Coverage signals — reconciling the three "coverage" numbers

Three different measurements are all colloquially called "coverage" on a Spec
Kitty pull request, and they routinely disagree by tens of percentage points.
That disagreement is **expected and by design** — it is not, on its own, a bug
or a regression. This guide explains what each number measures, why they differ,
and gives you a decision aid for the moment they seem to contradict each other:
*is this a real regression, or an expected scope difference?*

If you only remember one thing: **the internal `diff-coverage` gate and the
SonarCloud numbers measure different files, different lines, and against
different baselines. A passing internal gate next to a low SonarCloud number is
the normal, healthy state — not a contradiction.**

## The three signals at a glance

| Signal | Where it runs | Which files it scores | Which lines it counts | Threshold |
|---|---|---|---|---|
| **Internal `diff-coverage` gate** | CI `diff-coverage` job, **on `pull_request` only** (`.github/workflows/ci-quality.yml`) | A deliberate **critical-path subset** of `src/` (see list below) | **Only the lines your PR changed** vs the base branch (`diff-cover --compare-branch=origin/<base>`) | **90%**, blocking |
| **SonarCloud `coverage`** | Nightly Sonar analysis (cron `17 2 * * *`) / manual dispatch — **never per PR** | The **whole `src/` tree** (`sonar.sources=src`) | **Every** executable line in the tree, cumulative | No blocking floor on the overall number (the gate uses the `new_*` metrics) |
| **SonarCloud `new_coverage`** | Same nightly analysis | The whole `src/` tree | Lines in the **New Code Period** (since the `projectVersion` baseline) | **80%**, blocking Sonar's own gate |

There is also a **second, advisory** `diff-cover` step in the same CI job that
scores the *full* PR diff (all changed files, not just critical-path) with no
`--fail-under`; it prints a number but never blocks a merge.

### The internal gate's critical-path allowlist

The enforced internal gate restricts itself (`diff-cover ... --include`) to these
paths — the kernel, doctrine, charter, status, merge, and mission-runtime
surfaces where a coverage miss is highest-risk:

```
src/kernel/*
src/doctrine/*
src/charter/*
src/specify_cli/status/*
src/specify_cli/lanes/branch_naming.py
src/specify_cli/dashboard/handlers/*
src/specify_cli/dashboard/scanner.py
src/specify_cli/merge/*
src/runtime/next/*
src/mission_runtime/*
```

That is roughly **247 Python files** — a strict subset of the **~969 tracked
`.py` files** SonarCloud scores across the whole `src/` tree (SonarCloud indexes
**1305 files** in total under `src/`, spanning all seven top-level packages:
`specify_cli`, `doctrine`, `charter`, `runtime`, `glossary`, `kernel`,
`mission_runtime`).

## Why the numbers differ (the evidence)

The reconciliation below was produced against SonarCloud's **public read API**
(no token) using the read-only tool `scripts/ci/sonarcloud_branch_review.sh`.
You can reproduce every figure yourself:

```bash
scripts/ci/sonarcloud_branch_review.sh coverage       # overall + new_coverage
scripts/ci/sonarcloud_branch_review.sh quality-gate   # gate conditions + thresholds
scripts/ci/sonarcloud_branch_review.sh version        # projectVersion / baseline history
```

Three independent axes make the numbers diverge:

1. **File set (scope of files).** SonarCloud scores *all* of `src/`; the enforced
   internal gate scores only the critical-path subset above. So SonarCloud will
   surface uncovered lines in packages (for example `src/specify_cli/cli/`,
   `.../missions/`, `.../doctor/`) that the *enforced* internal gate never looks
   at. This is intentional — coverage effort is kept proportional to risk — and
   the full-diff advisory step exists precisely so the wider diff is still
   visible without blocking.

2. **Line basis (which lines, over what history).** This is the dominant driver.
   - SonarCloud `coverage` (**47.3%**) is a **cumulative average over the entire
     codebase**: `lines_to_cover = 95,111`, `uncovered_lines = 50,090`. It counts
     every executable line ever written, covered or not.
   - The internal gate (**90%**) counts **only the handful of lines the current
     PR changed**. A ten-line PR is judged on ten lines.

   These two can never be close: one is a whole-history denominator of ~95k
   lines, the other is your diff.

3. **Baseline (what "new" means).** SonarCloud `new_coverage` (**50.06%**)
   *sounds* like it should match the internal per-PR gate — both mention "new"
   code — but it does not, for a concrete reason: `new_lines_to_cover = 80,038`.
   About **84% of the whole tree** is currently counted as "new code," because
   every recent nightly analysis reports `projectVersion = "not provided"` and
   the New Code Period baseline is therefore frozen. So today `new_coverage`
   (~50%) is effectively *another whole-repo number*, not a per-PR one — which is
   why it sits right next to the overall `coverage`, nowhere near 90%. (See
   [Known caveats](#known-caveats-and-follow-ups) — a separate change wires
   `projectVersion` from `pyproject.toml` so this baseline resets per release
   cycle. Even after that fix, `new_coverage` becomes a *per-release-cycle*
   number, still not a *per-PR* one.)

## The verdict: file-set **and** philosophy differ — but nothing is misconfigured

Investigation finding, stated plainly:

- **The file sets do differ.** SonarCloud scores the entire `src/` tree; the
  enforced internal gate scores only a critical-path subset of the PR diff.
- **The measurement philosophy also differs**, and more decisively: whole-repo
  cumulative average (and a baseline-anchored "new code" number) versus per-PR
  changed-lines-only.
- **Neither difference is a `sources`/`exclusions` misconfiguration.**
  `sonar.sources=src` with `sonar.exclusions=**/__pycache__/**,**/*.pyc,**/migrations/**`
  is correct and standard: tests are registered separately as `sonar.tests`
  (so they are not counted as production lines to cover), and no generated or
  vendored code is wrongly swept in (the agent directories live at the repo
  root, outside `src/`). The internal allowlist is a deliberate,
  risk-proportional choice, not an accident.

Because the divergence is a philosophy-and-baseline difference rather than a
genuine file-set misconfiguration, it is **discharged by this document, not by a
config change** (research-first, per the mission constraint C-002). In
particular, this guide deliberately does **not** recommend narrowing Sonar's
scope to flatter the number — doing so would mask genuinely untested code, which
the project's no-ratchet standing order forbids.

## Decision aid: real regression, or expected scope difference?

When a SonarCloud number looks alarming next to the internal gate, walk these
questions in order:

1. **Did the internal `diff-coverage` (critical-path, enforced) gate pass on
   your PR?**
   - **Yes** → the lines you changed in critical-path modules are ≥90% covered.
     A low SonarCloud *overall* `coverage` or *current* `new_coverage` is **not a
     regression you introduced** — it is the whole-repo / frozen-baseline scope.
     Stop here for those two numbers.
   - **No** → you have a real gap in changed critical-path lines. Add tests
     before merge. This is a real signal, not a scope artifact.

2. **Is the number you are worried about SonarCloud's whole-repo `coverage`
   (~47%)?** Judge it against the **previous nightly analysis's `coverage`**, not
   against the 90% per-PR gate. A *drop* versus the previous analysis is worth
   investigating; a low *absolute* value is expected and structural.

3. **Is it SonarCloud `new_coverage`?** Until the `projectVersion` baseline is
   wired (see caveats), "new code" ≈ the whole repo, so read it like the overall
   number. After that fix it becomes a per-release-cycle figure — still not the
   per-PR diff the internal gate reports.

4. **Did your PR change files *outside* the critical-path allowlist?** The
   *enforced* internal gate does not measure them (only the advisory full-diff
   step does); SonarCloud does. So SonarCloud can legitimately show uncovered
   new lines that the enforced gate stayed silent on — an **expected scope
   difference, not a gate bug**. If those lines carry real logic, add focused
   tests anyway (the charter's rule: every new branch/helper ships with tests).

If after these steps a real coverage gap remains in code you changed, treat it
as a regression and add tests. If every "gap" resolves to whole-repo scope or a
frozen baseline, it is an expected scope difference — record that reasoning in
the PR so the next reader does not re-litigate it.

## Where each signal is configured

- **Internal `diff-coverage` gate** — the `diff-coverage` job in
  [`.github/workflows/ci-quality.yml`](../../.github/workflows/ci-quality.yml)
  (`--fail-under=90`, `--include <critical-paths>`, `--compare-branch`).
- **SonarCloud scope and exclusions** —
  [`sonar-project.properties`](../../sonar-project.properties)
  (`sonar.sources=src`, `sonar.tests=tests`, `sonar.exclusions=...`).
- **Read-only query tool** —
  [`scripts/ci/sonarcloud_branch_review.sh`](../../scripts/ci/sonarcloud_branch_review.sh),
  which reproduces every number above against the public API with no
  `SONAR_TOKEN`.
- **Related testing guides** — [Test-flakiness handling policy](testing-flakiness.md),
  [Running the test suite in parallel](testing-parallel.md),
  [Review gates](review-gates.md).

## Known caveats and follow-ups

- **`projectVersion` baseline is frozen.** Every recent nightly reports
  `projectVersion = "not provided"`, so SonarCloud's New Code Period never resets
  and `new_coverage` currently behaves like a whole-repo metric. A companion
  change in this same mission wires `sonar.projectVersion` from `pyproject.toml`
  so the baseline resets per release cycle; the effect lands on the **next
  nightly run after that change merges**, not on merge itself.
- **Internal allowlist entry repointed.** The critical-path `--include` list
  references `src/specify_cli/lanes/branch_naming.py`
  (`parse_mission_slug_from_branch`) — the real defining home of the
  branch-based mission-slug detection. An earlier draft pointed this entry at a
  path that had since been removed/superseded; #2443 repointed it to this
  defining home in **both** authorities (the workflow `--include` array and
  `tests/release/test_diff_coverage_policy.py`). This was always an incidental
  staleness nit in the internal gate's config, **not** a SonarCloud
  misconfiguration.
