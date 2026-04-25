# Phase 0 Research: Shared Package Boundary Cutover

**Mission**: `shared-package-boundary-cutover-01KQ22DS`
**Date**: 2026-04-25
**Branch contract**: planning/base `main` → merge target `main`

This research log resolves the three open architectural questions identified in
`plan.md` before implementation begins.

---

## R0-1: Where exactly should the internalized runtime live, and what is its import surface?

### Decision

The internalized runtime lives at `src/specify_cli/next/_internal_runtime/`,
colocated with the existing `runtime_bridge.py`, `decision.py`, and
`prompt_builder.py` modules.

The public surface (what `runtime_bridge.py` and `next_cmd.py` import) mirrors
exactly what they import from `spec_kitty_runtime` today:

| Symbol | From `spec_kitty_runtime` (pre-cutover) | New location (post-cutover) |
|--------|------------------------------------------|------------------------------|
| `DiscoveryContext` | `spec_kitty_runtime` | `specify_cli.next._internal_runtime` |
| `MissionPolicySnapshot` | `spec_kitty_runtime` | `specify_cli.next._internal_runtime` |
| `MissionRunRef` | `spec_kitty_runtime` | `specify_cli.next._internal_runtime` |
| `NextDecision` | `spec_kitty_runtime` | `specify_cli.next._internal_runtime` |
| `NullEmitter` | `spec_kitty_runtime` | `specify_cli.next._internal_runtime` |
| `next_step` (aliased `runtime_next_step`) | `spec_kitty_runtime` | `specify_cli.next._internal_runtime` |
| `provide_decision_answer` | `spec_kitty_runtime` | `specify_cli.next._internal_runtime` |
| `start_mission_run` | `spec_kitty_runtime` | `specify_cli.next._internal_runtime` |
| `ActorIdentity` | `spec_kitty_runtime.schema` | `specify_cli.next._internal_runtime.schema` |
| `load_mission_template_file` | `spec_kitty_runtime.schema` | `specify_cli.next._internal_runtime.schema` |
| `MissionRuntimeError` | `spec_kitty_runtime.schema` | `specify_cli.next._internal_runtime.schema` |
| `_read_snapshot` | `spec_kitty_runtime.engine` | `specify_cli.next._internal_runtime.engine` |
| `engine` (module reference) | `spec_kitty_runtime.engine` | `specify_cli.next._internal_runtime.engine` |
| `plan_next` | `spec_kitty_runtime.planner` | `specify_cli.next._internal_runtime.planner` |

Internal sub-module layout:

```
specify_cli/next/_internal_runtime/
├── __init__.py        # re-exports the public surface above
├── models.py          # DiscoveryContext, MissionPolicySnapshot, MissionRunRef, NextDecision
├── emitter.py         # NullEmitter + emitter Protocol
├── lifecycle.py       # next_step, provide_decision_answer, start_mission_run
├── engine.py          # _read_snapshot, snapshot persistence
├── planner.py         # plan_next, DAG planner
└── schema.py          # ActorIdentity, load_mission_template_file, MissionRuntimeError
```

### Rationale

- **Colocation** with `runtime_bridge.py` keeps the import paths short and the
  diff surface auditable. `runtime_bridge.py` is the only module that consumes
  the full surface; its re-import lines change from
  `from spec_kitty_runtime import (...)` to
  `from specify_cli.next._internal_runtime import (...)` — every other file in
  the call graph imports from `runtime_bridge` (which already abstracts the
  runtime), not from `spec_kitty_runtime` directly.
- **Underscore prefix** marks `_internal_runtime` as not part of the public CLI
  Python import surface, even though it is shipped in the wheel. External
  Python importers must continue to use `specify_cli.next.*` public symbols, not
  reach into `_internal_runtime`.
- **Existing layer rules** in `tests/architectural/test_layer_rules.py` already
  scope `specify_cli.*` as the top layer; placing the new module under
  `specify_cli` leaves those rules undisturbed and adds only one new
  package-boundary rule (the C-001 enforcement) on top.
- **No top-level package**: spec C-009 explicitly forbids introducing a new
  top-level package. The repo already has 4 (`kernel`, `doctrine`, `charter`,
  `specify_cli`); a fifth top-level for runtime would explode review surface and
  conflict with the in-flight `runtime-mission-execution-extraction-01KPDYGW`
  mission's own canonical-runtime location decision.

### Alternatives considered

- **`src/runtime/` as a new top-level package**: rejected. The
  `runtime-mission-execution-extraction-01KPDYGW` mission already proposes
  `src/runtime/` for a *different* extraction (the CLI's internal "next-step
  decisioning + agent dispatch" layer, not the standalone PyPI runtime
  package). Stomping on that namespace creates a merge conflict and confuses
  reviewers about which runtime is which.
- **`src/specify_cli/runtime/`**: rejected. That directory already exists and
  owns CLI asset / home-directory bootstrap (different concern). Reusing the
  name would collide.
- **Inlining the runtime code into `runtime_bridge.py`**: rejected. The
  pre-cutover code is ~3 sub-modules (engine, planner, schema) plus public
  models. Inlining ~3kLoC into a single file destroys reviewability and breaks
  the existing function-decomposition style.

### Behavior-equivalence strategy

WP01 captures behavior parity by:
1. Running `spec-kitty next` against a checked-in fixture mission with the
   currently-installed `spec-kitty-runtime` 0.4.3 and recording golden JSON
   snapshots in `tests/fixtures/runtime_parity/`.
2. Running the same fixture against the new internalized runtime and asserting
   byte-equal snapshots (modulo timestamp / path normalization, identical to
   how mission `runtime-mission-execution-extraction-01KPDYGW` does it).
3. Any delta forces an iteration on `_internal_runtime` *before* WP02 begins.

---

## R0-2: What is the compatibility range strategy for events and tracker, and what
happens to `[tool.uv.sources]` and `constraints.txt`?

### Decision

| Item | Pre-cutover state | Post-cutover state |
|------|-------------------|---------------------|
| `pyproject.toml` events dep | `spec-kitty-events==4.0.0` (exact pin) | `spec-kitty-events>=4.0.0,<5.0.0` |
| `pyproject.toml` tracker dep | `spec-kitty-tracker==0.4.2` (exact pin) | `spec-kitty-tracker>=0.4,<0.5` |
| `pyproject.toml` runtime dep | Absent (intentionally) | Absent (locked in by FR-006 + arch test) |
| `[tool.uv.sources]` for events | `spec-kitty-events = { path = "../spec-kitty-events", editable = true }` | Empty / absent |
| `[tool.uv.sources]` for tracker | Absent | Absent |
| `constraints.txt` | Pin `spec-kitty-events==4.0.0` to paper over runtime's transitive `<4.0` pin | Removed (no longer needed) |
| `uv.lock` | Pinned to dev path | Regenerated; pins to PyPI versions |

### Rationale

- The events public-surface contract from `events-pypi-contract-hardening-01KQ1ZK7`
  documents a SemVer policy: minor / patch within `4.x` are non-breaking; major
  bumps (`5.x`) are breaking. The compatibility range
  `>=4.0.0,<5.0.0` exactly matches that policy.
- The tracker mission `tracker-pypi-sdk-independence-hardening-01KQ1ZKK` is still
  in implement-review at the time of this plan. The conservative range `>=0.4,<0.5`
  matches the currently-published `0.4.2` line and reserves a tightening pass for
  when the upstream mission lands. The consumer test contract (FR-009) is the
  real safety belt; a too-loose range can only break CI explicitly via that
  contract, never silently in production.
- Editable / path overrides in `[tool.uv.sources]` were the **direct cause** of
  PR #779's CI failure: they masked the missing `spec-kitty-runtime` dependency
  during local dev because the editable events install pulled the runtime
  transitively, while CI installed from PyPI and exploded. Removing them is
  non-negotiable.
- Developer overrides for cross-package work (events / tracker) are documented
  separately in `docs/development/local-overrides.md` (created by WP10), using
  `uv` workspace patterns or explicit `--with-editable` flags that do **not**
  touch the committed `pyproject.toml`.
- `constraints.txt` exists today exclusively to paper over the
  `spec-kitty-runtime`-transitive `spec-kitty-events<4.0` pin conflict (see
  DRIFT-1 in mission review `01KPWT8P`). With `spec-kitty-runtime` no longer a
  dependency, the constraint has no purpose and is removed in WP08.

### Alternatives considered

- **Keep exact pins** (`==4.0.0`, `==0.4.2`): rejected. Exact pins recreate the
  cross-package release lockstep the cutover exists to dissolve. Spec
  acceptance criterion A7 forbids this.
- **Open-ended ranges** (`>=4`): rejected. SemVer minor windows are the right
  contract; a `5.x` major bump is breaking and must require an explicit CLI
  version bump.
- **Keep `[tool.uv.sources]` for dev convenience**: rejected. The dev workflow
  is fully servable by a separate developer-only override file. Committing
  editable overrides re-introduces the failure mode that rejected PR #779.
- **Convert `constraints.txt` into a generic dev constraint file**: rejected.
  It would become a magnet for similar paper-over hacks. Better to delete it
  cleanly and document developer override patterns in
  `docs/development/local-overrides.md`.

### Cross-repo handshake

- Events mission `events-pypi-contract-hardening-01KQ1ZK7` is merged at sha
  `81d5ccd4`. The compatibility range chosen here is committed against that sha.
- Tracker mission `tracker-pypi-sdk-independence-hardening-01KQ1ZKK` is in
  implement-review. WP07 (consumer-test contract) and WP08 (`pyproject.toml`
  range) explicitly note that the tracker range may need to be tightened on
  rebase if the upstream mission lands a contract change before this mission's
  closing PR is merged. The orchestrator picks up that delta automatically when
  the WP07 work resumes.

---

## R0-3: How does the clean-install CI job structurally guarantee absence of
`spec-kitty-runtime`?

### Decision

WP09 adds a new job named `clean-install-verification` to
`.github/workflows/ci-quality.yml`. The job:

1. Checks out the repo at the PR head.
2. Builds the CLI wheel with `python -m build --wheel`.
3. Spins up a fresh container (e.g. `python:3.12-slim`) with no
   pre-installed packages.
4. Inside the container, runs:
   ```bash
   pip install dist/spec_kitty_cli-*.whl
   pip list | grep -i spec-kitty-runtime && exit 1 || true   # must NOT be installed
   spec-kitty --version
   ```
5. Checks out a known fixture mission committed at
   `tests/fixtures/clean_install_fixture_mission/` and runs:
   ```bash
   spec-kitty agent mission setup-plan --mission <fixture-handle> --json
   spec-kitty next --agent claude --mission <fixture-handle> --json
   ```
6. Asserts the JSON output contains `"result": "success"` and that the loop
   advanced at least one step (event log gained at least one `StatusEvent` row).
7. Asserts wall-clock runtime ≤ 5 minutes (NFR-004).

The local-runnable counterpart is `tests/integration/test_clean_install_next.py`,
which uses `subprocess` and a `tmp_path` venv to perform the same flow on a dev
machine. It is gated behind a marker (`@pytest.mark.distribution`) so the main
test suite stays fast.

### Rationale

- **Container isolation** is the strongest available guarantee: a fresh
  `python:3.12-slim` image has no leftover state from the workspace's editable
  installs, no cached `spec-kitty-runtime`, and no `[tool.uv.sources]`
  precedence. If the CLI works there, it works for end users.
- **Wheel install** (not `pip install -e .`) mirrors the user experience.
- **Explicit `pip list | grep` assertion** turns "spec-kitty-runtime is not a
  dep" into a CI-enforced observation.
- **JSON-asserted advancement** is the same contract the existing
  `tests/next/test_next_command_integration.py` uses; reusing the assertion
  pattern keeps reviewer cognitive load low.

### Alternatives considered

- **Run the existing test suite in a clean venv**: rejected. The existing
  suite has hundreds of unit tests that don't need an isolated environment;
  running all of them in a clean venv would blow the 5-minute budget.
- **Mock the absence of `spec-kitty-runtime`**: rejected. Mocking does not
  prove what users experience.
- **Use `tox`**: rejected. The repo standardized on `uv`/`pytest`; introducing
  `tox` for one job is an unnecessary new tool.

### CI surface details

- The job key in `ci-quality.yml` is `clean-install-verification`.
- It is added to the `protect-main.yml` required-check set so a green run is
  required to merge.
- Fixture mission lives under `tests/fixtures/clean_install_fixture_mission/`;
  it is the smallest possible mission scaffold that exercises one
  `spec-kitty next` step (a single planned WP, no dependencies).

### Documentation handoff

- WP10 updates `docs/development/local-overrides.md` (new) and
  `CHANGELOG.md` to point at this job for operators who want to verify the
  cutover locally.

---

## Resolved clarifications

No `[NEEDS CLARIFICATION]` markers existed in `spec.md`. None added by this
research log.

## Inputs for Phase 1

The following Phase 1 artifacts use this research as ground truth:

- `data-model.md` — uses R0-1's import-surface table to model the structural
  before / after.
- `contracts/internal_runtime_surface.md` — copies the symbol table from R0-1.
- `contracts/events_consumer_surface.md` — derives from the public-surface doc
  in `spec-kitty-events` at sha `81d5ccd4`, scoped to the subset CLI uses.
- `contracts/tracker_consumer_surface.md` — derives from the published
  `spec-kitty-tracker` 0.4.2 SDK, scoped to the subset CLI uses.
- `quickstart.md` — uses R0-3's clean-install recipe.
