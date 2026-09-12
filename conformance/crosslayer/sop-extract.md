<!--
SOP policy extract (FR-007, OQ-6 option (b)).

This file is a bounded, verbatim subset of the repo-root AGENTS.md's
operating-policy sections — small enough to sit alongside a persona and a
skill in a composed context window without the small-model risk the full
file (35,933 bytes at this mission's base commit) would pose. AGENTS.md
itself is a shared, read-only input; neither this extract nor its drift
check ever modifies it.

Extraction rule (must match conformance/scripts/check-sop-extract-drift.sh
exactly, mechanical and re-run-able by that script, not a judgment call
re-made by hand): for each AGENTS.md heading listed below, in order, every
line from the heading (inclusive) through the line immediately before the
next line that is exactly "---" (AGENTS.md's own section-separator
convention) is extracted verbatim, excluding that "---" line itself.

Sections extracted (in AGENTS.md heading order):
  1. "## ⚠️ CRITICAL: Git Workflow — Branches, PRs, and Merges"

Regenerate with: bash conformance/scripts/check-sop-extract-drift.sh --write
-->

## ⚠️ CRITICAL: Git Workflow — Branches, PRs, and Merges

This repository uses **`main` as the integration branch**. Open a topic branch, target it with a pull request, and let repository review and branch-protection settings enforce the merge gate. GitHub Actions are live here: the reinstated lean, modular CI (`#3995`) runs on public `main` — a path router (`ci-router.yml`) feeding the single `gate_selection.py` authority, a per-module test matrix (`module-tests.yml` / `ci-modules.yml`), coverage/xunit aggregation with a diff-cover ≥90% gate (`ci-aggregate.yml`), a packs lane (`packs.yml`), a nightly full/performance/interpreter run (`ci-nightly.yml`), and a fork-safe SonarCloud workflow (`sonar.yml`). These replaced the archived EXPERIMENTAL Blacksmith producer.

- **Never push to `main`.** Create a topic branch from the current `main`, open a PR targeting `main`, and let the repository merge controls handle publication.
- `spec-kitty merge` consolidates lanes into your **local** `main` only; it never publishes to the remote. Qualify local vs origin when naming the branch (see the `primary`/`merge` footgun note under Terminology Canon).
- If your GitHub CLI installation cannot use issue or pull-request commands in a restricted environment, use the GitHub web interface or an authenticated GitHub API client.

### Convergence ports

- Port commits from the pre-fork line with `git cherry-pick -x` so authorship and provenance are preserved.
- Before applying a commit, classify it with `git show --stat <sha> -- <retired paths>`.
- If every touched path is retired, record the commit as `DROP` in the convergence map and do not port it.
- For a mixed commit, drop the retired hunks and cite the omitted hunks under `Dropped hunks:`.
- Every convergence PR carries `Retired-surface scan: 0 hits`, computed over added diff lines with the canonical regex in [planning `PROGRAM.md` §5](https://github.com/spec-kitty/EXPERIMENTAL-spec-kitty-planning/blob/main/PROGRAM.md#5-the-pr-protocol).
- Never add `# noqa: TID251` for a retired module.
- Never resolve a kept-file conflict with `theirs` without re-running `tests/architectural/test_no_retired_subsystems.py`.

**Test policy (§6):** run every test you write or change plus your blast radius, and record commands + counts in the PR. Baseline is `make test-fast`; add the test files of every module your diff touches, and the full test directory of each owning subsystem. Run `tests/architectural/` in full only for cross-cutting changes (pytest.ini, pyproject.toml, conftest, markers, packaging) — see "Test policy — what you must run for a change" below for the calibrated blast-radius rule. Do **not** run `make test-full` or any whole-repo suite — the CI agent owns that.

