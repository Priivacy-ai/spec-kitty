# Quickstart — Charter Golden-Path E2E (Tranche 1)

A reviewer or maintainer can validate this mission's deliverable in three commands.

## 1. Run the new test in isolation

From the source checkout root:

```bash
uv run pytest tests/e2e/test_charter_epic_golden_path.py -q -s
```

Expected: exit 0, one passing test (the golden path), wall-clock under ~180 s on a current CI runner (NFR-001).

## 2. Run the regression slices the spec calls out

```bash
uv run pytest \
  tests/e2e/ \
  tests/next/ \
  tests/integration/test_documentation_runtime_walk.py \
  tests/integration/test_research_runtime_walk.py \
  -q
```

Expected: no previously-green test newly fails (NFR-006, SC-004).

## 3. Run the test-asset quality gates the spec demands

```bash
uv run ruff check tests/e2e/test_charter_epic_golden_path.py tests/e2e/conftest.py
uv run mypy --strict tests/e2e/test_charter_epic_golden_path.py
```

Expected: both exit 0 (NFR-003).

## 4. Verify the source-checkout pollution guard works end-to-end

After step 1 completes:

```bash
git status --short
```

Expected: empty output. If anything appears here, the test passed but the guard failed, which is itself a regression worth investigating.

## What the test proves (Charter epic surfaces under coverage)

- `spec-kitty init` produces a usable fresh project for downstream Charter work.
- `spec-kitty charter interview / generate / bundle validate / synthesize / status / lint` all succeed end-to-end on a fresh project (with `synthesize --adapter fixture` per R-002).
- `spec-kitty agent mission create / setup-plan / finalize-tasks` scaffold a minimal `software-dev` mission via the public CLI.
- `spec-kitty next --json` issues exactly one composed action for the scaffolded mission.
- `spec-kitty next --result success --json` advances the action AND writes paired pre/post lifecycle records under `.kittify/events/profile-invocations/`.
- The recorded `action` matches the issued step (no role-default verb leaks).
- `spec-kitty retrospect summary --json` runs against the project without mutation.
- The whole flow runs from a temp project outside the source checkout and writes nothing to the source checkout.

## What the test does NOT prove (deferred to follow-up tranches)

- External canaries in `spec-kitty-end-to-end-testing`.
- Plain-English scenarios.
- Full CLI walks for every built-in mission type (only `software-dev` is exercised here).
- Browser / dashboard surfaces.
- Retrospective synthesize via `agent retrospect synthesize`.
- Multi-mission or multi-action runtime walks.

These are explicitly enumerated in spec "Out of Scope (this tranche)" and are tracked as #827 follow-up work.

## Documented deviation from `start-here.md`

`start-here.md` recommends `spec-kitty charter synthesize --json` (no `--adapter`). This tranche uses `spec-kitty charter synthesize --adapter fixture --json`. Reason: the default `generated` adapter requires LLM-authored YAML under `.kittify/charter/generated/`, which is unavailable in an unattended automated test. The `fixture` adapter is the documented offline/testing path. See `research.md` R-002 for the full rationale; the PR description repeats this finding.
