# Contract: Selector Resolution Helper

**Mission**: `077-mission-terminology-cleanup`
**Surface**: `src/specify_cli/cli/selector_resolution.py` (new module)
**Owner**: Scope A (`#241`)
**Test file**: `tests/specify_cli/cli/commands/test_selector_resolution.py` (new file)

## Module Structure

```
src/specify_cli/cli/selector_resolution.py
├── SelectorResolution             (frozen dataclass; see data-model.md)
├── resolve_selector(...)          (public helper)
├── _emit_deprecation_warning(...) (private sub-helper)
└── _warned: set[tuple[str, str]]  (module-level state for NFR-002)
```

## Public API

### `resolve_selector`

```python
def resolve_selector(
    *,
    canonical_value: str | None,
    canonical_flag: str,
    alias_value: str | None,
    alias_flag: str,
    suppress_env_var: str,
    command_hint: str | None = None,
) -> SelectorResolution:
    ...
```

**Behavioral contract**:

| Input case | Returns | Side effects | Raises |
|---|---|---|---|
| Both `None` or empty | — | — | `typer.BadParameter` via `require_explicit_feature(None, command_hint=command_hint)` |
| Only `canonical_value` set | `SelectorResolution(canonical_value, canonical_flag, alias_used=False, alias_flag=None, warning_emitted=False)` | None | — |
| Only `alias_value` set | `SelectorResolution(canonical_value=alias_value.strip(), canonical_flag, alias_used=True, alias_flag, warning_emitted=<actual>)` | At most one yellow stderr deprecation warning per process per `(canonical_flag, alias_flag)` pair, suppressible via `os.environ.get(suppress_env_var) == "1"` | — |
| Both set, equal (after `.strip()`) | `SelectorResolution(canonical_value=canonical_value.strip(), canonical_flag, alias_used=True, alias_flag, warning_emitted=<actual>)` | One deprecation warning (same suppression rule) | — |
| Both set, not equal (after `.strip()`) | — | None | `typer.BadParameter` with the conflict message format defined below |

## Conflict Error Format

```
Conflicting selectors: <canonical_flag>=<canonical_value!r> and <alias_flag>=<alias_value!r> were both provided with different values. <alias_flag> is a hidden deprecated alias for <canonical_flag>; pass only <canonical_flag>.
```

**Example for `mission current --mission A --feature B`**:
```
Conflicting selectors: --mission='A' and --feature='B' were both provided with different values. --feature is a hidden deprecated alias for --mission; pass only --mission.
```

**Example for `agent mission create new-thing --mission-type software-dev --mission research`** (inverse direction):
```
Conflicting selectors: --mission-type='software-dev' and --mission='research' were both provided with different values. --mission is a hidden deprecated alias for --mission-type; pass only --mission-type.
```

The format is verified by `tests/specify_cli/cli/commands/test_selector_resolution.py::test_conflict_error_format`.

## Call-Site Pattern

Every tracked-mission command in the main CLI follows this pattern. Two separate typer parameters; one helper call in the function body.

### Tracked-Mission Command (Scope A — direction: `--feature` is the alias)

```python
import typer
from specify_cli.cli.selector_resolution import resolve_selector

@app.command("current")
def current_cmd(
    mission: Annotated[str | None, typer.Option(
        "--mission",
        help="Mission slug",
    )] = None,
    feature: Annotated[str | None, typer.Option(
        "--feature",
        hidden=True,  # ← KEY: charter compliance
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
    # ... rest of command logic uses mission_slug ...
```

### Inverse-Drift Command (Scope A — direction: `--mission` is the alias)

```python
import typer
from specify_cli.cli.selector_resolution import resolve_selector

@app.command(name="create")
def create_mission(
    mission_slug: Annotated[str, typer.Argument(help="Mission slug (e.g., 'user-auth')")],
    mission_type: Annotated[str | None, typer.Option(
        "--mission-type",
        help="Mission type (e.g., 'documentation', 'software-dev')",
    )] = None,
    mission: Annotated[str | None, typer.Option(
        "--mission",
        hidden=True,
        help="(deprecated) Use --mission-type",
    )] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
    target_branch: Annotated[str | None, typer.Option("--target-branch", help="Target branch (defaults to current branch)")] = None,
) -> None:
    """Create new mission directory structure in the project root checkout."""
    resolved = resolve_selector(
        canonical_value=mission_type,
        canonical_flag="--mission-type",
        alias_value=mission,
        alias_flag="--mission",
        suppress_env_var="SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION",
        command_hint="--mission-type <name>",
    )
    mission_type_value = resolved.canonical_value
    # ... rest of command logic uses mission_type_value ...
```

## Required Test Coverage

The contract test file `tests/specify_cli/cli/commands/test_selector_resolution.py` must cover **all of the following cases** for `resolve_selector` directly, plus one integration test per direction via `typer.testing.CliRunner`:

### Unit Tests (helper, in isolation)

1. `test_canonical_only_returns_value` — only `canonical_value` set, returns it, `alias_used=False`, no warning.
2. `test_alias_only_returns_canonical_value` — only `alias_value` set, returns it, `alias_used=True`, warning emitted.
3. `test_both_equal_returns_value_with_warning` — both set, equal, returns value, `alias_used=True`, warning emitted.
4. `test_both_different_raises_bad_parameter` — both set, different, raises `typer.BadParameter` with the exact conflict message format.
5. `test_neither_raises_bad_parameter` — both `None`, raises via `require_explicit_feature`.
6. `test_both_empty_strings_raise_bad_parameter` — both `""`, raises via `require_explicit_feature` (after `.strip()`).
7. `test_canonical_whitespace_only_treated_as_none` — `canonical_value="   "`, `alias_value="x"`, returns `"x"` with warning.
8. `test_warning_emitted_only_once_per_pair` — call helper twice with the same `(canonical_flag, alias_flag)`, verify only one stderr line.
9. `test_warning_emitted_again_for_different_pair` — call with `--feature` then with `--mission` (different alias), verify two stderr lines.
10. `test_suppression_env_var_skips_warning` — set `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION=1`, call with alias, verify no stderr line, but `warning_emitted=False`.
11. `test_inverse_direction_works_identically` — call with `canonical_flag="--mission-type"`, `alias_flag="--mission"`, `suppress_env_var="SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION"`, verify all behaviors.
12. `test_conflict_error_format` — verify exact message text matches the format in this contract.

### Integration Tests (full typer command, via CliRunner)

13. `test_mission_current_canonical_succeeds` — `mission current --mission 077-x` resolves correctly.
14. `test_mission_current_alias_succeeds_with_warning` — `mission current --feature 077-x` resolves and emits warning.
15. `test_mission_current_dual_flag_conflict_fails` — `mission current --mission A --feature B` exits non-zero with conflict message. **This is the regression test for the verified bug from spec §8.2.**
16. `test_agent_mission_create_canonical_succeeds` — `agent mission create new --mission-type software-dev` resolves correctly.
17. `test_agent_mission_create_alias_succeeds_with_warning` — `agent mission create new --mission software-dev` resolves and emits warning.
18. `test_agent_mission_create_dual_flag_conflict_fails` — `agent mission create new --mission-type software-dev --mission research` exits non-zero with conflict message.

### Coverage Requirement

Per NFR-005, line coverage on `src/specify_cli/cli/selector_resolution.py` must be ≥ 90%. With the case list above, the helper should reach 100% line coverage.

## Module-Level State Reset

The `autouse` fixture from `data-model.md` (the `_reset_selector_resolution_state` fixture) must be installed in `tests/specify_cli/cli/commands/test_selector_resolution.py` and in any other test file that calls the helper directly. Without it, test order affects warning emission and CI is flaky.

## Constraints (from spec §7)

- **C-008**: The helper must not introduce any abstraction that would make a future `Mission → MissionRun` rename "easier". Specifically: no aggregate-type indirection, no parallel field shadows, no abstract base classes for selector resolution.
- **C-010**: The helper must live in `src/specify_cli/cli/`, not in `src/specify_cli/orchestrator_api/`. The orchestrator-api is not wired through this helper.
- **C-011**: The helper's tests must not scan `kitty-specs/**` or `architecture/**`.

## Backwards Compatibility for Existing Call Sites

The existing function `require_explicit_feature` at `src/specify_cli/core/paths.py:273` is **not modified**. It continues to be called by the new helper in the "missing value" path. All existing call sites of `require_explicit_feature` continue to work unchanged. WPA1 may identify call sites that should *additionally* be wired through `resolve_selector`, but the existing helper itself is unchanged.
