# Data Model — Modular per-package CI + regen

Phase-0 entity sketch. Full data model is refined in the plan phase; this fixes the vocabulary the spec uses.

## Entities

- **Module** — an independently-owned CI unit. Instances this mission: `kernel`, `doctrine`, `packs`.
  (`spec-internal` is a future module, not in-tree — out of scope.) Attributes: id, source roots
  (`src/kernel` | `src/doctrine`+`src/charter` | `packs/built-in`), test roots, coverage roots, coverage
  artifact name(s).

- **Module Workflow** — a `.github/workflows/module-<id>.yml` file with `on: workflow_call`, holding the
  module's test steps + coverage upload. Independently runnable; invoked as an ordered `uses:` job inside
  `ci-quality.yml`. Attributes: inputs (none required initially), gate condition (path-filter output),
  emitted artifact name (`<slug>-reports`), coverage file (`coverage-<slug>.xml`).

- **Coverage Artifact** — per-run uploaded `<slug>-reports` containing `coverage-*.xml`. Consumed by
  `diff-coverage` (PR gate) and `sonarcloud` (nightly scan) via glob discovery. Invariant: filename stability
  across the refactor (aggregators discover by glob, never by producing job name).

- **Fixture Set** — the committed generated assets that drift: `_twelve_agent_baseline` (144 command files)
  and skill `__snapshots__` (24 SKILL.md files), rendered from source `prompt.md` templates.

- **Regen Tool** — `spec-kitty regen [--check] [--json]`. Modes: **write** (mutate fixtures) and **check**
  (render to memory/tempdir, byte-diff, exit 1 + remediation message on drift).

- **Render Version Pin** — shared constant(s) giving the version stamp both the fixtures and `regen` use.
  Single source of truth replacing the two divergent hard-coded pins (`3.1.2a3`, `3.0.0`).

- **Regen Workflow** — CI automation. Trust tiers: same-repo/`workflow_dispatch` → auto-commit; fork PR →
  check-only failure; labeled (`regen`) fork PR → privileged PAT-push (security-review-gated).

## Key relationships

- `ci-quality.yml` **invokes** each Module Workflow as an ordered job (`uses:`), **aggregates** their Coverage
  Artifacts in one run.
- Regen Tool **produces** the Fixture Set from source templates using the Render Version Pin.
- Gate tests **verify** the Fixture Set (post-narrowing: structural invariants + one canonical snapshot).
- Regen Workflow **runs** the Regen Tool in the mode selected by the trust tier of the triggering event.
