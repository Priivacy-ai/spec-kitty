---
work_package_id: WP10
title: Documentation Cutover and PR
dependencies:
- WP02
- WP05
- WP07
- WP08
- WP09
requirement_refs:
- FR-014
- FR-015
- FR-020
- NFR-007
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T038
- T039
- T040
- T041
- T042
- T043
- T044
- T045
agent: "claude:opus-4.7:python-reviewer:reviewer"
shell_pid: "73685"
history:
- at: '2026-04-25T10:31:00+00:00'
  actor: planner
  event: created
authoritative_surface: docs/migration/shared-package-boundary-cutover.md
execution_mode: code_change
owned_files:
- CHANGELOG.md
- README.md
- CLAUDE.md
- docs/development/mission-next-compatibility.md
- docs/development/mutation-testing-findings.md
- docs/development/local-overrides.md
- docs/migration/shared-package-boundary-cutover.md
- docs/host-surface-parity.md
- architecture/2.x/adr/2026-04-25-1-shared-package-boundary.md
tags: []
---

# WP10 — Documentation Cutover and PR #779 Supersession

## Objective

Update operator-facing documentation to describe the new boundary, create
the migration runbook, document developer workflows for cross-package work,
record the cross-cutting decision in an ADR, and have the closing PR formally
supersede PR #779.

## Context

This is the final WP. By the time it lands, all production code (lanes A and
B) has cutover, the architectural / packaging / consumer / clean-install
gates are green, and the metadata (`pyproject.toml`, `uv.lock`) reflects the
new boundary. Operators encountering CLI from this point forward must read
docs that match the new reality.

NFR-007 verifies via `grep -rn "install spec-kitty-runtime" docs/ README.md`
that no stale references remain.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: convergence (depends on WP02, WP05, WP07, WP08, WP09).

## Implementation

### Subtask T038 — Update `CHANGELOG.md` [P]

**Purpose**: Operator-facing changelog entry for the cutover.

**Steps**:

1. Add an entry under the next unreleased version (version bump itself
   happens at release time; this WP doesn't bump the version):

   ```markdown
   ## Unreleased

   ### Changed

   - **Shared package boundary cutover**: `spec-kitty-runtime` is no longer
     a dependency of `spec-kitty-cli`. The CLI now owns its own runtime
     internally; `spec-kitty next` works from a clean install of
     `spec-kitty-cli` alone. `spec-kitty-events` and `spec-kitty-tracker`
     are external PyPI dependencies consumed via their public import surfaces
     (`spec_kitty_events`, `spec_kitty_tracker`). The vendored events tree
     under `src/specify_cli/spec_kitty_events/` has been removed. Developers
     who relied on editable cross-package overrides should consult
     [`docs/development/local-overrides.md`](docs/development/local-overrides.md);
     operators upgrading from a pre-cutover release should consult
     [`docs/migration/shared-package-boundary-cutover.md`](docs/migration/shared-package-boundary-cutover.md).

   ### Removed

   - `constraints.txt` is removed; it existed solely to paper over a
     transitive pin conflict with the retired `spec-kitty-runtime` package.
   ```

2. Verify the entry's wording matches the actual code state (e.g. the
   version range pins, the migration doc paths).

**Files**: `CHANGELOG.md`.

**Validation**: Markdown lints clean.

### Subtask T039 — Update `README.md` install instructions [P]

**Purpose**: First-time users see the correct install command.

**Steps**:

1. Audit the existing README's "Install" section. Look for any text that
   says "also install spec-kitty-runtime" or similar.

2. Replace with the canonical post-cutover install:
   ```bash
   pip install spec-kitty-cli
   ```
   (One step.)

3. Add a short note: "spec-kitty-cli ships its own runtime; no separate
   `spec-kitty-runtime` install is required."

4. Run the NFR-007 grep gate:
   ```bash
   grep -rn "install spec-kitty-runtime\|pip install spec-kitty-runtime" README.md
   ```
   Expected: zero matches.

**Files**: `README.md`.

**Validation**: Grep gate is clean.

### Subtask T040 — Update `CLAUDE.md` [P]

**Purpose**: Agent-facing dev-docs reflect the new boundary.

**Steps**:

1. Audit `CLAUDE.md` for references to `spec-kitty-runtime`. The file is
   long; key sections to inspect:
   - "Active Technologies" — remove any line that pins
     `spec-kitty-runtime`.
   - "PyPI Release (Quick Reference)" — verify the release process doesn't
     mention pre-installing runtime.
   - The whole section about "Recent Changes" is auto-generated from feature
     plans; the cutover's plan adds a fresh entry.

2. Add a new section titled "Shared Package Boundary (post-cutover)":

   ```markdown
   ## Shared Package Boundary

   As of mission `shared-package-boundary-cutover-01KQ22DS` (2026-04-25):

   - **Runtime**: CLI-internal under `src/specify_cli/next/_internal_runtime/`.
     The standalone `spec-kitty-runtime` PyPI package is retired; the CLI
     does not depend on it.
   - **Events**: external PyPI dependency. Consumed only via
     `spec_kitty_events.*` public imports. The vendored copy under
     `src/specify_cli/spec_kitty_events/` was removed.
   - **Tracker**: external PyPI dependency. Consumed only via
     `spec_kitty_tracker.*` public imports.
   - **Compatibility ranges** live in `pyproject.toml`; **exact pins** live
     in `uv.lock`.
   - **Editable / path overrides** for events / tracker are dev-only; never
     committed in `pyproject.toml`'s `[tool.uv.sources]`. Consult
     `docs/development/local-overrides.md` for the dev workflow.

   Architectural enforcement of these invariants lives in
   `tests/architectural/test_shared_package_boundary.py` and
   `tests/architectural/test_pyproject_shape.py`.
   ```

**Files**: `CLAUDE.md`.

**Validation**: Grep `CLAUDE.md` for `spec-kitty-runtime` — only references
that survive are historical (e.g. inside a "Recent Changes" entry that
documents the cutover itself).

### Subtask T041 — Update mission-next-compatibility, mutation-testing-findings, host-surface-parity [P]

**Purpose**: Existing dev docs reference the standalone runtime; bring them
up to date.

**Steps**:

1. `docs/development/mission-next-compatibility.md`: mark the doc historical
   with a header note: "*HISTORICAL — describes the pre-cutover compatibility
   matrix between `spec-kitty-cli` and the (retired) `spec-kitty-runtime`
   PyPI package. Superseded by mission
   `shared-package-boundary-cutover-01KQ22DS`. Retained for historical
   reference; do not consult for current behavior.*"

2. `docs/development/mutation-testing-findings.md`: lines 146 and 159 mention
   `spec-kitty-runtime` as a prerequisite for certain test imports. Update
   these references — after the cutover, `tests/unit/next/` no longer needs a
   transitive runtime install. Replace with: "imports `_internal_runtime`."

3. `docs/host-surface-parity.md`: line 11 references
   `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`. The skill itself
   stays; rename references from "spec-kitty-runtime-next" to neutral
   wording where they conflate the skill name with the retired PyPI package.
   Audit specifically:
   ```bash
   grep -n "spec-kitty-runtime" docs/host-surface-parity.md
   ```
   Each match either (a) refers to the skill (leave alone — it's a name) or
   (b) refers to the retired PyPI package (update).

**Files**: 3 files in `docs/development/` and `docs/`.

**Validation**: Each file's references are accurate post-cutover.

### Subtask T042 — Create migration runbook [P]

**Purpose**: Operators need a step-by-step upgrade story.

**Steps**:

1. Create `docs/migration/shared-package-boundary-cutover.md`:

   ```markdown
   # Migration: Shared Package Boundary Cutover

   **Mission**: `shared-package-boundary-cutover-01KQ22DS`
   **Released**: <release version when this lands>
   **Audience**: operators upgrading `spec-kitty-cli` from a pre-cutover
   version.

   ## What changed

   `spec-kitty-cli` no longer depends on the `spec-kitty-runtime` PyPI
   package. The runtime now lives inside `spec-kitty-cli`. Events and
   tracker remain external PyPI dependencies, but the vendored events copy
   was removed from the CLI tree.

   ## Action required

   For most operators: nothing. Re-run `pip install --upgrade spec-kitty-cli`
   and the new release works without `spec-kitty-runtime`. The retired
   package may remain installed in your environment; it is harmless and
   unused.

   ## Optional cleanup

   ```bash
   pip uninstall spec-kitty-runtime
   ```

   ## Verification

   ```bash
   # Confirm the CLI loads without spec-kitty-runtime in sys.modules:
   python -c "
   import sys, specify_cli
   assert 'spec_kitty_runtime' not in sys.modules
   print('OK')
   "

   # Confirm `spec-kitty next` runs against your project:
   spec-kitty next --agent <agent> --mission <mission>
   ```

   See [`kitty-specs/shared-package-boundary-cutover-01KQ22DS/quickstart.md`](
   ../../kitty-specs/shared-package-boundary-cutover-01KQ22DS/quickstart.md)
   for the full local-runnable verification recipe.

   ## Developer workflows

   If you work across `spec-kitty-cli` and `spec-kitty-events` /
   `spec-kitty-tracker` simultaneously, see
   [`docs/development/local-overrides.md`](../development/local-overrides.md)
   for editable-install patterns that don't pollute committed config.

   ## Why this happened

   See [ADR 2026-04-25-1: Shared Package Boundary](
   ../../architecture/2.x/adr/2026-04-25-1-shared-package-boundary.md).
   ```

**Files**: `docs/migration/shared-package-boundary-cutover.md`.

**Validation**: The doc renders cleanly; its links resolve.

### Subtask T043 — Create local-overrides developer doc [P]

**Purpose**: Replace the editable-source pattern that lived in
`pyproject.toml` (and was a contributing factor to PR #779's failure) with a
documented dev workflow that doesn't pollute committed config.

**Steps**:

1. Create `docs/development/local-overrides.md`:

   ```markdown
   # Local Overrides for Cross-Package Development

   When working across `spec-kitty-cli`, `spec-kitty-events`, and/or
   `spec-kitty-tracker`, you may need editable installs of the sibling
   packages. **Do NOT commit `[tool.uv.sources]` editable / path entries
   for these packages in `pyproject.toml`** — that committed override is
   exactly what got PR #779 rejected.

   Instead, use one of the following dev-only patterns.

   ## Pattern A: ad-hoc editable installs

   ```bash
   # In your local spec-kitty-cli checkout:
   pip install -e ../spec-kitty-events
   pip install -e ../spec-kitty-tracker
   ```

   The editable installs override the wheel-installed copies for the current
   venv only. Nothing is committed.

   ## Pattern B: a personal `pyproject.local.toml`

   `uv` and `hatch` honor a `pyproject.local.toml` file (gitignored). Add:

   ```toml
   [tool.uv.sources]
   spec-kitty-events = { path = "../spec-kitty-events", editable = true }
   spec-kitty-tracker = { path = "../spec-kitty-tracker", editable = true }
   ```

   Confirm `pyproject.local.toml` is in `.gitignore` (it is).

   ## CI guard

   `tests/architectural/test_pyproject_shape.py` fails CI when
   `pyproject.toml` (committed) contains an editable / path source for
   events / tracker / runtime. The guard exists specifically to prevent
   re-introducing the pattern that contributed to PR #779's failure.

   ## Verification before pushing

   ```bash
   # Confirm your changes don't add committed overrides:
   git diff pyproject.toml | grep -E "spec-kitty-(events|tracker|runtime).*path"
   # Expected: empty
   ```
   ```

2. Add `pyproject.local.toml` to `.gitignore` if not already present.

**Files**:
- `docs/development/local-overrides.md` (new).
- `.gitignore` (extended, if needed).

**Validation**: The doc renders cleanly.

### Subtask T044 — Create ADR [P]

**Purpose**: Capture the cross-cutting decision in the ADR record.

**Steps**:

1. Create `architecture/2.x/adr/2026-04-25-1-shared-package-boundary.md`:

   ```markdown
   # ADR: Shared Package Boundary Cutover

   **Date**: 2026-04-25
   **Status**: Accepted
   **Mission**: `shared-package-boundary-cutover-01KQ22DS`
   **Supersedes**: PR #779 (rejected for preserving the hybrid model)

   ## Context

   The Spec Kitty product surface includes three Python packages:
   `spec-kitty-cli`, `spec-kitty-events`, `spec-kitty-tracker`, plus the
   retiring `spec-kitty-runtime`. Pre-cutover, the CLI consumed a hybrid
   mix: vendored events code in CLI production paths; production imports
   of `spec_kitty_runtime` even though `pyproject.toml` did not list it as
   a dependency; an editable `[tool.uv.sources]` entry that masked the
   missing dependency in local dev.

   PR #779 attempted a partial cutover that moved runtime-shaped code into
   the CLI tree but kept `spec_kitty_runtime` production imports alive.
   That PR was rejected because the hybrid state failed CI in clean
   environments and re-imposed cross-package release lockstep.

   ## Decision

   1. The CLI internalizes the runtime surface it needs from
      `spec-kitty-runtime` into `src/specify_cli/next/_internal_runtime/`.
      Production code paths import only from the internalized module.
   2. The CLI consumes events through the public PyPI package
      (`spec_kitty_events`); the vendored copy at
      `src/specify_cli/spec_kitty_events/` is deleted.
   3. The CLI consumes tracker through the public PyPI package
      (`spec_kitty_tracker`); CLI-internal `specify_cli.tracker.*`
      adapters do not re-export tracker public surface.
   4. `pyproject.toml` lists events / tracker via compatibility ranges
      (e.g. `>=4.0,<5.0`); exact pins live only in `uv.lock`.
   5. `[tool.uv.sources]` does not contain editable / path entries for any
      shared package on the committed configuration path. Developer
      overrides live in dev-only configuration documented in
      `docs/development/local-overrides.md`.
   6. CI runs a clean-install verification job that proves
      `spec-kitty next` works in a fresh venv without
      `spec-kitty-runtime`.
   7. Architectural tests (using `pytestarch` per ADR 2026-03-27-1) fail
      when any production module re-introduces `spec_kitty_runtime` imports
      or vendored events imports.

   ## Consequences

   - Cross-package release lockstep is dissolved: events / tracker can ship
     within their compatibility windows without forcing a CLI release.
   - Operators install only `spec-kitty-cli` from PyPI; the retired
     `spec-kitty-runtime` package is unused.
   - The CLI codebase grows by ~3kLoC (the internalized runtime).
   - Cross-package contract changes (events / tracker public surface) break
     the CLI's consumer-test suite explicitly, forcing CLI to react.

   ## Alternatives considered

   - **Re-publish `spec-kitty-runtime` as a stable library**: rejected. The
     runtime API is CLI-specific; it has no other consumers. Maintaining a
     standalone PyPI package added cross-package release coordination cost
     without delivering external value.
   - **Keep events vendored**: rejected. Vendoring forks the contract;
     consumers see two events surfaces that may diverge.
   - **Land the cutover in two PRs (runtime first, events second)**:
     rejected. C-007 explicitly forbids partial cutovers; PR #779 was the
     cautionary example.

   ## References

   - Mission spec: [`kitty-specs/shared-package-boundary-cutover-01KQ22DS/spec.md`](
     ../../../kitty-specs/shared-package-boundary-cutover-01KQ22DS/spec.md)
   - Migration runbook:
     [`docs/migration/shared-package-boundary-cutover.md`](
     ../../../docs/migration/shared-package-boundary-cutover.md)
   - PR #779 (rejected, superseded):
     <https://github.com/Priivacy-ai/spec-kitty/pull/779>
   ```

**Files**:
`architecture/2.x/adr/2026-04-25-1-shared-package-boundary.md`.

**Validation**: The ADR renders cleanly; its links resolve.

### Subtask T045 — Closing PR description supersedes PR #779

**Purpose**: Make the supersession explicit in the closing PR.

**Steps**:

1. The closing PR description (the one that lands this mission) MUST include
   a "Supersedes" section:

   ```markdown
   ## Supersedes

   This PR formally supersedes [#779](https://github.com/Priivacy-ai/spec-kitty/pull/779),
   which was rejected for preserving the hybrid model (runtime-shaped code
   in the CLI tree alongside live `spec_kitty_runtime` production imports).

   This PR completes the actual cutover: the CLI owns its runtime
   internally; events and tracker are consumed only via public PyPI
   imports; CI proves `spec-kitty next` works in a clean install without
   `spec-kitty-runtime`.

   See [ADR 2026-04-25-1](architecture/2.x/adr/2026-04-25-1-shared-package-boundary.md)
   for the full decision rationale.
   ```

2. After the PR merges, post a comment on PR #779 cross-linking to the
   merged PR for traceability:

   ```bash
   gh pr comment 779 --repo Priivacy-ai/spec-kitty \
     --body "Superseded by #<merged-PR> (mission shared-package-boundary-cutover-01KQ22DS)."
   ```

**Files**: None directly; this is a process / PR-description task.

**Validation**:
- The closing PR description includes the Supersedes section.
- After merge, PR #779 has a cross-link comment.

## Definition of Done

- [ ] All 8 subtasks complete with checkboxes ticked above (`mark-status` updates the per-WP checkboxes here as the WP advances).
- [ ] CHANGELOG entry exists.
- [ ] README install instructions are correct; NFR-007 grep gate is clean.
- [ ] CLAUDE.md documents the new boundary.
- [ ] Stale dev docs are updated or marked historical.
- [ ] Migration runbook exists.
- [ ] Local-overrides dev doc exists.
- [ ] ADR 2026-04-25-1 exists.
- [ ] Closing PR description supersedes #779.
- [ ] Post-merge cross-link comment posted on PR #779.

## Risks

- **Stale doc references missed by grep.** Mitigation: NFR-007 requires the
  grep gate; reviewer runs it as part of approval.
- **The closing PR's description is forgotten in the rush to merge.**
  Mitigation: T045 is on the WP10 checklist; reviewer verifies it before
  approving.

## Reviewer guidance

- Run the NFR-007 grep gate:
  ```bash
  grep -rn "install spec-kitty-runtime" docs/ README.md
  ```
- Verify each new doc renders cleanly and links resolve.
- Verify the ADR captures the decision rationale (not just the FRs).
- Verify the closing PR description includes the supersession note.

## Implementation command

```bash
spec-kitty agent action implement WP10 --agent <name> --mission shared-package-boundary-cutover-01KQ22DS
```

## Activity Log

- 2026-04-25T12:11:09Z – claude:opus-4.7:python-implementer:implementer – shell_pid=72940 – Started implementation via action command
- 2026-04-25T12:15:46Z – claude:opus-4.7:python-implementer:implementer – shell_pid=72940 – All 8 subtasks done: CHANGELOG entry (T038), README install note (T039), CLAUDE.md boundary section (T040), historical/updated dev docs (T041), migration runbook (T042), local-overrides dev doc (T043), ADR 2026-04-25-1 (T044), supersession noted in migration doc + ADR (T045). NFR-007 grep clean. Refs FR-014, FR-015, FR-020, NFR-007.
- 2026-04-25T12:15:48Z – claude:opus-4.7:python-reviewer:reviewer – shell_pid=73685 – Started review via action command
- 2026-04-25T12:15:52Z – claude:opus-4.7:python-reviewer:reviewer – shell_pid=73685 – Approved: WP10 acceptance criteria met. (1) CHANGELOG entry exists. (2) README install instructions correct; NFR-007 grep clean. (3) CLAUDE.md documents the new boundary. (4) Stale dev docs marked historical / updated. (5) Migration runbook exists. (6) Local-overrides dev doc exists. (7) ADR 2026-04-25-1 exists. (8) Closing PR description supersession is documented in the migration doc + ADR header; the post-merge cross-link comment on PR #779 is a documented manual step. Refs FR-014, FR-015, FR-020, NFR-007, commit df04c58b.
