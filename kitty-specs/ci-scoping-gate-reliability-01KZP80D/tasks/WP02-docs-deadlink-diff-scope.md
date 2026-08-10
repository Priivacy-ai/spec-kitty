---
work_package_id: WP02
title: Docs dead-link gate is scoped to the PR's own diff (#3147)
dependencies: []
requirement_refs:
- C-002
- FR-004
- FR-005
planning_base_branch: fix/ci-scoping-gate-reliability
merge_target_branch: fix/ci-scoping-gate-reliability
branch_strategy: Planning artifacts for this mission were generated on fix/ci-scoping-gate-reliability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/ci-scoping-gate-reliability unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
history:
- event: created
  at: '2026-08-10T16:54:20Z'
  actor: architect-alphonso
agent_profile: python-pedro
authoritative_surface: scripts/docs/
create_intent: []
execution_mode: code_change
owned_files:
- .github/workflows/docs-freshness.yml
- scripts/docs/relative_link_fixer.py
- scripts/docs/related_validator.py
- tests/docs/test_docs_freshness_invariant.py
- tests/docs/test_rulers_blocking.py
role: implementer
tags: []
tracker_refs:
- '#3147'
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This profile governs your implementation style, boundaries, and quality standards for this work package.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Scope the two **blocking** whole-tree dead-link checks to the PR's own changed files so a docs PR is
no longer failed for pre-existing broken links it never touched (#3147) — while keeping the unfiltered
`push:main` whole-tree run as the non-blocking rot backstop (FR-005). The scoping narrows WHICH files
are checked, never WHETHER the check bites.

**Done when**:
- SC-003: a docs PR whose changed files have no broken links PASSES the blocking gate even when an
  untouched file elsewhere has a broken link; introduce a broken link in a changed file → it FAILS;
  the `push:main` scan still reports the untouched link.
- The whole-tree `push:main` backstop (`docs-freshness.yml:48-49`) is retained (M3, C-002).
- `docs-freshness` is NOT wired into any required check / `quality-gate.needs` (N1).

## Context & Constraints

- **Authoritative squad remediation (READ BOTH FIRST)**:
  [tracer-squad-findings.md](../tracer-squad-findings.md) (M3, M5, N1) **and**
  [investigate-squad-findings.md](../investigate-squad-findings.md) — the pre-implement squad found a
  **BLOCKER (B-WP02)**: the fail-closed predicate must key on base **resolvability**, NOT changed-set
  emptiness. The corrections are folded into T008/T009/T010/T012 below and SUPERSEDE any conflicting
  wording. Read B-WP02 before writing a line.
- **N1 — docs-freshness is NOT a required check** (`test_docs_freshness_invariant.py` docstring +
  `docs-freshness.yml:20-24`: required contexts are `["drift-detector"]`). #3147's over-fire is
  red-X friction, not a merge block. Do NOT add `docs-freshness` to `quality-gate.needs` — a required
  docs-freshness that a path filter skips leaves every non-docs PR pending forever.
- **FR-005 / M3 / C-002**: FR-005's "retained whole-tree scan" IS the existing unfiltered `push:main`
  run (`:48-49`), which runs every step whole-tree on push. RETAIN it. A `schedule:` trigger is
  optional/additive, never a replacement — do not remove the push backstop.

### The two gates in scope (`docs-freshness.yml`)

- `:77-78` — `related_validator.py --strict --repo-root .` (related-edge / cross-tree link targets).
- `:81-82` — `relative_link_fixer.py --check --repo-root .` (relative body-link dead-link gate,
  whole-docs `rglob` at ~`relative_link_fixer.py:390`).
- The OTHER steps (`description_length_check`, structural lint, changelog/contributing sync,
  slash-command freshness, `check_docs_freshness.py`) are OUT of scope — #3147 is specifically the
  whole-tree dead-link/related-edge over-fire. Leave them unchanged.

## Subtasks & Detailed Guidance

### Subtask T008 — Diff-scope mode in `relative_link_fixer.py` (FR-004, M5, B-WP02)

- **Purpose**: let `--check` evaluate only the PR's changed docs files, fail-closed **on base
  resolvability**.
- **⚠️ B-WP02 — fail-closed keys on RESOLVABILITY, not emptiness.** docs-freshness triggers on many
  non-`.md` paths (`src/specify_cli/**`, `pyproject.toml`, `uv.lock`, `CHANGELOG.md`, `CONTRIBUTING.md`,
  `scripts/docs/**`), so a legit PR often changes ZERO `docs/**/*.md`. The existing `min_files=1` floor
  (`relative_link_fixer.py:530-544`, shared `scripts/docs/_guards.py:62-67`) raises on zero-examined —
  it **cannot** distinguish "base unresolvable" from "base resolved, zero docs changed". Do NOT reuse it
  as the diff-scope emptiness gate.
- **Steps**:
  1. Add a diff-scope option (e.g. `--changed-from <base-ref>`, or `--changed-paths-file <path>` for
     testability) that restricts the check to the changed files intersected with the docs scan set,
     instead of the whole-docs `rglob` (`:390`, `iter_doc_files` at `:508`).
  2. **Scope by FILE, not by hunk/line**: select the changed `docs/**/*.md` files and run the existing
     **whole-file** check (`path.read_text`, `_LINK.finditer(body)`, `:511-529`) on each. A line/hunk
     filter would miss a break on an unmodified line of a modified file. (The link-from-unchanged-file-
     to-deleted-target case is inherently invisible to diff-scope; it is delegated to the `push:main`
     backstop — do NOT weaken the empty-set semantics to try to cover it.)
  3. **Fail-closed trigger = git base resolution FAILS**: capture the `git` subprocess returncode; a
     non-zero return or an unresolvable/absent base ref (shallow clone with no `fetch-depth:0`, base sha
     unfetched, `merge-base` failure) → **exit non-zero (ERROR)**. This is the ONLY fail-closed trigger.
  4. **A successfully-computed diff yielding zero in-scope docs → clean exit 0 (PASS)** — do NOT route
     it through `min_files`. Keep `min_files=1` ONLY for the whole-tree/`push` mode (where zero docs
     genuinely means a broken scan).
  5. Keep the existing whole-tree `--check` mode intact (used by the `push:main` backstop).
- **Files**: `scripts/docs/relative_link_fixer.py`.

### Subtask T009 — Diff-scope mode in `related_validator.py --strict` (FR-004, M5, B-WP02)

- **Purpose**: same diff-scope + resolvability-keyed fail-closed for the related-edge validator.
- **Steps**: mirror T008 exactly — scope by changed file, whole-file check (rglob at
  `related_validator.py:108`, floor at `:118-124`); fail-closed ONLY on a non-zero git base resolution;
  a resolved-but-zero-docs diff PASSES (exit 0); retain the whole-tree `--strict` mode + its
  `min_files=1` for the backstop.
- **Files**: `scripts/docs/related_validator.py`.

### Subtask T010 — Wire `docs-freshness.yml` PR runs to diff-scope (FR-004, FR-005, M3, C-002, N1)

- **Purpose**: run the two gates diff-scoped on `pull_request`; keep the whole-tree `push:main`.
- **Steps**:
  1. Set `actions/checkout` to `fetch-depth: 0` so the base commit is available.
  2. On `pull_request`, invoke the two gates with the diff-scope flag deriving the base from
     `${{ github.event.pull_request.base.sha }}`.
  3. On `push` (event_name == 'push'), invoke them WHOLE-TREE exactly as today (the backstop). Use a
     step-level conditional or a small shell branch on `github.event_name` so one job body serves both.
  4. Do NOT add `docs-freshness` to any `needs`/required-check list (N1).
- **Notes**: the diff-scope flag must be passed ONLY when a base is available (PR context). On
  `push:main` there is no `pull_request.base.sha` → whole-tree mode (no diff flag), which by T008/T009
  design is the full scan with `min_files=1` intact, NOT the diff-scope path.
- **A non-docs-md PR that still triggers docs-freshness (e.g. `src/specify_cli/**`-only) MUST PASS**
  (exit 0) — its diff resolves fine and yields zero in-scope docs. Only a non-zero git base resolution
  errors. Do not let this class red (that is the B-WP02 trap).
- **Files**: `.github/workflows/docs-freshness.yml`.

### Subtask T011 — Co-evolve `test_docs_freshness_invariant.py` (NFR-003, M3)

- **Purpose**: keep the static invariant valid after the trigger/step change.
- **Steps**: the test statically pins the PR `paths:` allowlist (excludes `tests/**` + `kitty-specs/**`)
  and the unfiltered `push:main` backstop. Update it so it still passes AND additionally asserts the
  backstop survives and the PR-path shape is intact. Do not weaken the "not a required check" docstring.
- **Files**: `tests/docs/test_docs_freshness_invariant.py`.

### Subtask T012 — Co-evolve `test_rulers_blocking.py` (FR-004, M3)

- **Purpose**: prove the diff-scoped gate still BITES on a link the PR itself breaks.
- **Steps**: extend the CLI RED-proof for `relative_link_fixer`/`related_validator` to pass a
  base/changed-set and assert THREE cases (the third is load-bearing per B-WP02):
  - (a) a seeded violation IN the changed-set still reds (stays green as a RED-proof — the check BITES);
  - (b) a pre-existing violation OUTSIDE the changed-set does NOT red in diff-scope mode (exit 0);
  - (c) **base-unresolvable → non-zero exit** (e.g. an unfetched/garbage base ref) — distinct from both
    (a) and (b). Without (c) the fail-closed branch is untested and (a)/(b) collapse into it.
  Also assert the resolved-but-zero-in-scope-docs case exits 0 (a non-docs-md PR must not red).
- **Files**: `tests/docs/test_rulers_blocking.py`.

## Test Strategy

- `tests/docs/` is the acceptance surface. Run:
  `PWHEADLESS=1 python -m pytest tests/docs/test_docs_freshness_invariant.py tests/docs/test_rulers_blocking.py -p no:cacheprovider -q`.
- Add focused unit tests for the new diff-scope + fail-closed branches in both scripts (per B-WP02):
  **unresolvable base → non-zero**; violation in-scope → non-zero; violation out-of-scope → zero;
  **resolved diff with zero in-scope docs → zero** (the non-docs-md PR case). Sonar new-code coverage
  is dominated by these new branches — test them directly, not only via the invariant.

## Risks & Mitigations

- **⚠️ B-WP02 (BLOCKER)**: fail-closed keys on git base **resolvability** (non-zero return → ERROR),
  NOT on changed-set emptiness. A resolved diff with zero in-scope docs (common — non-`.md` PRs trigger
  docs-freshness) MUST pass. Do NOT reuse the `min_files=1` floor as the diff-scope emptiness gate; keep
  that floor for whole-tree/`push` mode only.
- **Missing the third test case**: T012 must test base-unresolvable → non-zero, or the M5 branch is
  unverified.
- **Scoping by line/hunk instead of file**: scope by changed FILE and run the whole-file check, or a
  break on an unmodified line of a modified file slips through.
- **Losing the backstop (M3/C-002)**: the `push:main` unfiltered whole-tree run must remain and run
  whole-tree (no diff flag).
- **Accidentally making it a required check (N1)**: do not add to `quality-gate.needs` or branch
  protection. ("Blocking" in this WP means job-step-failing, never gates-merge.)
- **Base commit not fetched**: `fetch-depth: 0` on checkout, or the base ref won't resolve (→ ERROR).

## Review Guidance

- Confirm fail-closed keys on **git base resolvability** (non-zero return → ERROR), and that a resolved
  diff with zero in-scope docs **passes** (the B-WP02 distinction). Reject any impl that errors on an
  empty resolved changed-set or reuses `min_files=1` for the diff path.
- Confirm the diff scopes by changed FILE and runs the whole-file check (not line/hunk filtering).
- Confirm the `push:main` whole-tree backstop is retained, runs whole-tree, keeps its `min_files=1`.
- Confirm `docs-freshness` is still NOT a required check / not in `quality-gate.needs`.
- Confirm `test_rulers_blocking` proves all three: in-scope BITE, out-of-scope pass, base-unresolvable error.

## Activity Log

- 2026-08-10T16:54:20Z – system – lane=planned – Prompt created.
