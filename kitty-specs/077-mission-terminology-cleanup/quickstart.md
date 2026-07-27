# Quickstart: Mission Terminology Cleanup

**Mission**: `077-mission-terminology-cleanup`
**Audience**: The agent or engineer implementing Scope A (`#241`)
**Estimated path**: helper → one command end-to-end → batch the rest → grep guards → docs → orchestrator-api verification

This quickstart walks through the implementation in the order that minimizes rework. Read the spec, plan, research, data-model, and contracts first. Then start here.

## Prerequisites

- Python 3.11+ installed
- `uv` installed (per `CONTRIBUTING.md`; `pipx install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Repo checked out at HEAD (validated baseline `54269f7c131a5efc40b729d412de26f6b05c65fb` or later)
- You are on `main` (planning/base branch)
- The repo uses **PEP 621 + Hatch** (`pyproject.toml`) and **`uv`** for dependency management. **Do not use `poetry`** — there is no `poetry.lock` and `poetry install` will fail.
- You have read:
  - `kitty-specs/077-mission-terminology-cleanup/spec.md`
  - `kitty-specs/077-mission-terminology-cleanup/plan.md` (especially the Charter Reconciliation note)
  - `kitty-specs/077-mission-terminology-cleanup/research.md`
  - `kitty-specs/077-mission-terminology-cleanup/data-model.md`
  - `kitty-specs/077-mission-terminology-cleanup/contracts/selector_resolver.md`
  - `kitty-specs/077-mission-terminology-cleanup/contracts/deprecation_warning.md`
  - `kitty-specs/077-mission-terminology-cleanup/contracts/grep_guards.md`
- You understand that **`--feature` becomes a hidden alias**, not a deleted flag (charter requirement)
- You understand that the **orchestrator-api stays canonical-only and is not modified** (C-010)
- You understand that **historical artifacts under `kitty-specs/**` and `architecture/**` are not modified** (C-011)

## Step 0: Reproduce the Verified Bug

Before writing any fix, reproduce the bug in spec §8.2 to confirm the baseline:

```bash
cd /private/tmp/241/spec-kitty
uv sync
```

Then run the current `mission current` command directly against the source tree:

```bash
uv run spec-kitty mission current --mission 077-mission-terminology-cleanup --feature 047-namespace-aware-artifact-body-sync
```

Observe that this command does **not** raise a conflict error. It silently resolves to the second value (typer's last-alias-wins). This is the verified bug. Once your fix lands, this exact command must exit non-zero with the conflict error from `contracts/selector_resolver.md` §"Conflict Error Format".

## Step 1: Write the Failing Tests First

Create `tests/specify_cli/cli/commands/test_selector_resolution.py` with the 18 test cases enumerated in `contracts/selector_resolver.md` §"Required Test Coverage". All tests should fail at this point (the helper does not exist yet).

```bash
uv run pytest tests/specify_cli/cli/commands/test_selector_resolution.py -x
```

You should see 18 failures, all of the form `ModuleNotFoundError: No module named 'specify_cli.cli.selector_resolution'`.

## Step 2: Implement the Helper

Create `src/specify_cli/cli/selector_resolution.py` following `data-model.md` and `contracts/selector_resolver.md`. The whole module should be ~80 lines:

- `SelectorResolution` dataclass (frozen, slots)
- `_warned: set[tuple[str, str]] = set()` module-level state
- `_err_console = Console(stderr=True)` module-level rich console
- `_doc_path_for(alias_flag)` helper
- `_emit_deprecation_warning(canonical_flag, alias_flag, suppress_env_var)` private sub-helper
- `resolve_selector(...)` public function

Run the helper unit tests until they pass:

```bash
uv run pytest tests/specify_cli/cli/commands/test_selector_resolution.py -x -k "not integration"
```

## Step 3: Wire One Command End-to-End

Pick `mission current` (because it has the smallest blast radius and is the verified-bug site). Modify `src/specify_cli/cli/commands/mission.py` lines 172-194:

**Before** (current buggy state):
```python
@app.command("current")
def current_cmd(
    feature: str | None = typer.Option(
        None,
        "--mission",
        "--feature",
        "-f",
        help="Mission slug",
    ),
) -> None:
    ...
```

**After**:
```python
from typing import Annotated

import typer
from specify_cli.cli.selector_resolution import resolve_selector

@app.command("current")
def current_cmd(
    mission: Annotated[str | None, typer.Option(
        "--mission",
        "-f",
        help="Mission slug",
    )] = None,
    feature: Annotated[str | None, typer.Option(
        "--feature",
        hidden=True,
        help="(deprecated) Use --mission",
    )] = None,
) -> None:
    """Show the active mission type for a mission."""
    resolved = resolve_selector(
        canonical_value=mission,
        canonical_flag="--mission",
        alias_value=feature,
        alias_flag="--feature",
        suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
        command_hint="--mission <slug>",
    )
    mission_slug = resolved.canonical_value
    # ... rest of function unchanged ...
```

**Important**: do **not** keep the old `feature` parameter name on the canonical flag. Use `mission` for the canonical parameter and `feature` for the hidden alias parameter. They must be two separate parameters; that's the entire point of the fix.

Now run:

```bash
uv run pytest tests/specify_cli/cli/commands/test_selector_resolution.py -x
```

The integration tests for `mission current` should now pass. Run the manual repro from Step 0:

```bash
uv run spec-kitty mission current --mission 077-mission-terminology-cleanup --feature 047-namespace-aware-artifact-body-sync
```

You should now see a non-zero exit and the conflict error message. The verified bug is fixed.

## Step 4: Batch the Rest of the Tracked-Mission Sites (WPA2a)

Use the WPA1 audit output to identify every tracked-mission selector site. The verified-known sites are:

- `src/specify_cli/cli/commands/next_cmd.py:33` (1 site, plus the example in line 48 which becomes documentation cleanup)
- `src/specify_cli/cli/commands/agent/tasks.py` (9 sites at lines 842, 1389, 1572, 1655, 1726, 1945, 2205, 2295, 2659)

For each site, apply the same pattern as Step 3:
1. Split the multi-alias `Option` into two separate parameters: canonical `--mission` (visible) and `--feature` (hidden, if it was previously aliased).
2. **Drop `--mission-run` entirely from tracked-mission selector aliases.** The WPA1 audit must confirm that no caller in the runtime/session code depends on `--mission-run` being a tracked-mission alias on these specific commands. If any caller does, that's a runtime bug to fix separately.
3. Update the help string from "Mission run slug" to "Mission slug".
4. Call `resolve_selector(...)` in the function body and use the returned canonical value.

After each file, run the full selector-resolution test suite:

```bash
uv run pytest tests/specify_cli/cli/commands/test_selector_resolution.py
```

## Step 5: Inverse Drift (WPA2b)

Three known sites in `contracts/selector_resolver.md` §"Inverse-Drift Command":

- `src/specify_cli/cli/commands/agent/mission.py:488`
- `src/specify_cli/cli/commands/charter.py:67`
- `src/specify_cli/cli/commands/lifecycle.py:27`

For each, apply the inverse-direction pattern:
1. Rename the canonical parameter to use `--mission-type` as its primary flag.
2. Add a hidden `--mission` alias parameter with `hidden=True`.
3. Call `resolve_selector` with `canonical_flag="--mission-type"`, `alias_flag="--mission"`, `suppress_env_var="SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION"`.
4. Update tests for these commands to use `--mission-type` as canonical.

## Step 6: Doctrine Skills (WPA6)

Open `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` and replace every `--mission-run <slug>` instruction with `--mission <slug>` (only when the slug means a tracked mission). Leave any genuine `--mission-run` references for runtime/session contexts alone.

Search for other doctrine skills that might mention tracked-mission selection:

```bash
grep -rn "mission-run" src/doctrine/skills/ | grep -v "runtime\|session"
```

Update each match.

## Step 7: Agent-Facing Docs and Top-Level Project Docs (WPA7)

Spec FR-022 puts both `docs/**` and the top-level project docs in scope.

### Step 7a: Live `docs/**` files

Open `docs/explanation/runtime-loop.md` and replace legacy selector teaching. Search for other live docs:

```bash
grep -rn "mission-run\|--feature" docs/explanation/ docs/reference/ docs/tutorials/ 2>/dev/null
```

Update each match. **Do not scan `kitty-specs/**` or `architecture/**` or `docs/migration/**`** (the migration docs are required to mention `--feature` and `--mission-run` by name; that's where the deprecation warnings link to).

### Step 7b: Top-level project docs

Per FR-022, the top-level files `README.md`, `CONTRIBUTING.md`, and the **Unreleased section** of `CHANGELOG.md` are also in scope. Verified drift sites at HEAD `35d43a25`:

- `README.md:883` — example block teaches `# Accept mission (legacy --feature flag name)` followed by a `spec-kitty agent mission accept --json` example. Remove the "(legacy --feature flag name)" comment and any `--feature`-using example block; keep the canonical `--mission`-using example.
- `README.md:910` — `--feature <slug>` is documented in the `spec-kitty accept` Options table. **This is the most visible drift in the repo** because it teaches a new user that `--feature` is a valid option for an active command. Replace the row with `--mission <slug>` and remove the "Legacy flag name retained as a software-dev compatibility alias" prose.

Search for any other top-level drift:

```bash
grep -n "mission-run\|--feature" README.md CONTRIBUTING.md
```

For `CHANGELOG.md`, only the Unreleased section is in scope. Historical version entries (e.g., the line at `CHANGELOG.md:172` describing what changed in a past release) are explicitly excluded by the "CHANGELOG-style historical entries" carve-out in FR-022. **Do not rewrite history.** If the Unreleased section has any active mention of `--feature` or `--mission-run` for tracked-mission selection, update it; otherwise leave CHANGELOG.md alone.

```bash
# Check the Unreleased section only — everything above the first ## [<version>] heading
awk '/^## \[[0-9]+\.[0-9]+\.[0-9]+/{exit} {print}' CHANGELOG.md | grep -n "mission-run\|--feature"
```

**Do not scan `kitty-specs/**` or `architecture/**`** under any circumstances (C-011).

## Step 8: Migration Docs (WPA9)

Create the two migration doc pages referenced from the deprecation warnings:

- `docs/migration/feature-flag-deprecation.md`
- `docs/migration/mission-type-flag-deprecation.md`

Each should include:
- Why the change (links to ADR + initiative + this mission's spec)
- What changed (the canonical flag names)
- How to migrate scripts (find/replace examples)
- How to suppress the warning during cutover (the env var name)
- Removal criteria (named conditions only, no date — per spec §15 Q1)

## Step 9: Grep Guards (WPA6 + WPA7 finalization)

Create `tests/contract/test_terminology_guards.py` following `contracts/grep_guards.md`. Implement all 8 guard test functions. Run them:

```bash
uv run pytest tests/contract/test_terminology_guards.py
```

If any guard fails, the failure message names the file and the fix. Fix the source of the failure (not the guard) and re-run. The guards should be green when all of WPA1..WPA8 are complete.

**Critical**: do not silence a failing guard. The guards exist precisely to fail noisily.

## Step 10: Cross-Surface Verification (WPA8)

This work package is mostly **reading** code, not writing it. Verify:

1. `src/specify_cli/orchestrator_api/commands.py` is unchanged.
2. `src/specify_cli/orchestrator_api/envelope.py` is unchanged.
3. `src/specify_cli/core/upstream_contract.json` is unchanged in the `orchestrator_api` section.
4. `tests/contract/test_orchestrator_api.py` is unchanged.
5. The new `tests/contract/test_terminology_guards.py::test_orchestrator_api_envelope_width_unchanged` passes.

The intentional asymmetry from spec §11.1 means there is no orchestrator-api code change in this mission. Resist the temptation to "tidy up" the orchestrator-api side; that would violate C-010.

## Step 11: Spec Edit (Charter Reconciliation)

Per the plan's Charter Reconciliation note, edit spec §11.1 to use the language "hidden deprecated compatibility alias" instead of "deprecated compatibility alias". This is a one-line clarification that aligns the spec with the charter without changing behavior. Make this edit in the same PR as the implementation.

**Do not** edit any other spec section. The spec is the authoritative artifact for this mission and should not drift from its post-review state except for this one clarification.

## Step 12: Full Test Suite + Coverage

```bash
PWHEADLESS=1 uv run pytest tests/
uv run pytest --cov=specify_cli.cli.selector_resolution --cov-report=term-missing tests/specify_cli/cli/commands/test_selector_resolution.py
```

Verify:
- All tests pass.
- Coverage on `selector_resolution.py` is ≥ 90% (NFR-005). It should be 100%.
- mypy --strict passes:

```bash
uv run mypy --strict src/specify_cli/cli/selector_resolution.py
```

## Step 13: Manual End-to-End Smoke Test

Run each of the following and verify the behavior matches the contract:

```bash
# Canonical works
uv run spec-kitty mission current --mission 077-mission-terminology-cleanup
# expected: succeeds, no warning

# Hidden alias works with warning
uv run spec-kitty mission current --feature 077-mission-terminology-cleanup
# expected: succeeds, one yellow "Warning: --feature is deprecated; use --mission..." on stderr

# Same value with both flags works with warning
uv run spec-kitty mission current --mission 077-mission-terminology-cleanup --feature 077-mission-terminology-cleanup
# expected: succeeds, one warning

# Conflict fails deterministically
uv run spec-kitty mission current --mission 077-mission-terminology-cleanup --feature 047-namespace-aware-artifact-body-sync
# expected: non-zero exit, conflict error message naming both flags and both values

# Suppression env var works
SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION=1 uv run spec-kitty mission current --feature 077-mission-terminology-cleanup
# expected: succeeds, NO warning

# --feature is hidden in help
uv run spec-kitty mission current --help | grep -- "--feature"
# expected: empty (no match) — --feature must not appear in help

# Inverse direction: canonical works
uv run spec-kitty agent mission create new-quickstart-test --mission-type software-dev --json
# expected: succeeds, no warning, creates a new mission directory

# Inverse direction: hidden alias with warning
uv run spec-kitty agent mission create another-quickstart-test --mission software-dev --json
# expected: succeeds, one yellow "Warning: --mission is deprecated; use --mission-type..." on stderr

# Clean up the test missions
rm -rf kitty-specs/*new-quickstart-test*
rm -rf kitty-specs/*another-quickstart-test*
```

## Step 14: Pre-PR Checklist

Before opening the PR for Scope A acceptance review:

- [ ] All 15 acceptance gates in spec §10.1 pass
- [ ] CI is green
- [ ] Coverage on `src/specify_cli/cli/selector_resolution.py` is ≥ 90%
- [ ] mypy --strict is clean on all touched files
- [ ] No file under `kitty-specs/**` (other than `077-mission-terminology-cleanup/`) is modified
- [ ] No file under `architecture/**` is modified
- [ ] `src/specify_cli/orchestrator_api/envelope.py` is unchanged
- [ ] `src/specify_cli/core/upstream_contract.json` orchestrator-api section is unchanged
- [ ] `tests/contract/test_orchestrator_api.py` continues to assert `--feature` is rejected (regression check)
- [ ] All 9 guards in `tests/contract/test_terminology_guards.py` pass (8 original + Guard 5b for top-level docs)
- [ ] `README.md` no longer documents `--feature <slug>` as a live option for any command (verified drift sites at lines 883 and 910 cleaned up)
- [ ] `CONTRIBUTING.md` does not teach `--feature` or `--mission-run` for tracked-mission selection
- [ ] `CHANGELOG.md` historical version entries are unchanged; only the Unreleased section was edited (if at all)
- [ ] Migration docs at `docs/migration/feature-flag-deprecation.md` and `docs/migration/mission-type-flag-deprecation.md` exist and link to the spec, ADR, and initiative
- [ ] spec §11.1 clarification edit is included
- [ ] PR description references `Priivacy-ai/spec-kitty#241` and includes the spec gates checklist

## Out of Scope for Scope A

Do **not** do any of the following in the same PR:

- Touching the orchestrator-api (C-010, §10.1 item 10)
- Renaming `MissionCreated` / `MissionClosed` (locked non-goal §3.3)
- Adding `mission_run_slug` anywhere (C-009)
- Renaming `aggregate_type="Mission"` (locked non-goal §3.3)
- Renaming any directory under `kitty-specs/` (locked non-goal §3.3, C-002)
- Modifying historical mission specs under `kitty-specs/**` (C-011)
- Modifying ADRs or initiatives under `architecture/**` (C-011)
- Removing `--feature` (out of scope per spec §11.2 — removal is gated on telemetry)
- Any Scope B work (gated on Scope A acceptance per spec §2 + C-004)

## When Scope A Is Accepted

Open a follow-on issue or work package set for Scope B (`#543`). Reference spec §13.2 for the work package outline. Do not start Scope B until Scope A is merged and the gates in §10.1 are confirmed green on `main`.
