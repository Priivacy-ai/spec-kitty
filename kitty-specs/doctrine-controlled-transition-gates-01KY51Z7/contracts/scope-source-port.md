# Contract: `ScopeSource` port

**Traces**: FR-001, FR-002, FR-003, FR-009, FR-010, FR-011, FR-012, NFR-004
**Home**: `src/specify_cli/review/scope_source.py` (new) · **Pattern**: `doctrine/sources/protocol.py:53`

## Interface

`ScopeSource` is a `@runtime_checkable typing.Protocol` covering **only** the concerns that vary
by repo shape. "Which files changed" is NOT on the port — it is the shared canonical
merge-base+diff input, passed to the gate.

```python
@runtime_checkable
class ScopeSource(Protocol):
    def test_command(self) -> list[str] | None: ...
    def file_to_scope(self, path: str) -> tuple[str, ...]: ...
    def parse_results(self, raw: RawRunResult) -> tuple[BaselineFailure, ...]: ...
```

`RawRunResult` (new, `scope_source.py`) is the **unparsed** run the engine produces by executing
`test_command()` without interpreting it:

```python
@dataclass(frozen=True)
class RawRunResult:
    returncode: int
    stdout: str
    stderr: str
    output_artifact_path: Path | None
```

### `test_command() -> list[str] | None`
The runnable argv the gate executes at head. `None` ⇒ the repo declares no command → the gate is
a visible `NO_COVERAGE` warn (FR-012), never a crash and never a silent green.

### `file_to_scope(path) -> tuple[str, ...]`
Map ONE changed file to zero-or-more test targets. `()` = "contributes no scope" (NOT an error).
Called once per element of the shared `changed_files` input.

### `parse_results(raw: RawRunResult) -> tuple[BaselineFailure, ...]`
Turn a completed head run into **per-failure identities** (not a bare pass/fail bit). **Load-
bearing** (squad F1): without it the portable path is decorative — a failing non-pytest suite
collapses to `NO_COVERAGE` instead of a blocking `NEW_FAILURES`. Exit code alone is insufficient
identity: the diff (`diff_baseline`) needs stable per-failure identities to classify pre-existing
vs new. A non-zero exit with unparseable output ⇒ the whole run counts as failing (surfaced,
never swallowed).

**Baseline-relative, NOT absolute.** `NEW_FAILURES` means *new vs baseline*, preserving the
incumbent meaning. The portable path captures its baseline by running the **same declared command
through the same port** and persisting the parsed identities, then the gate diffs head vs that
baseline. A `parse_results = returncode != 0` (ANY_FAILURES) is **forbidden** — it would block a
consumer with a pre-existing red suite on every transition. Both impls therefore feed baseline
capture AND the head run from one authority (FR-011): baseline↔head symmetry is structural, not
per-side.

## Port-wide obligations

1. **Never raise for environmental problems.** Surface them via return values (the
   `OrgDoctrineSource` discipline, `protocol.py:16-17`). `test_command() -> None` is the no-config
   signal, not an exception.
2. **`changed_files` is shared, not per-impl.** The gate passes the merge-base+diff SSOT
   (`core.vcs.git.merge_base_changed_files`, via `tasks_move_task.py:927`) into the evaluation;
   neither impl re-derives it. This forbids the two impls diverging on the changed-file SSOT
   (FR-001).
3. **Sole test-command authority** (FR-011). The port is consumed by BOTH baseline capture
   (today `review/baseline.py:124` `_get_test_command`) and the head run (today the hardcoded
   `review/_interpreter.py:32` `resolve_pytest_command`). The third key
   `review.pre_review_test_command` (`tasks_move_task.py:785`) is re-pointed at the port or
   deprecated.

## Implementation obligations

### `GateCoverageScopeSource` (internal, behaviour-preserving) — FR-002, FR-009
- Reproduces today's exact scope derivation, pytest invocation, and JUnit parsing on the
  Spec-Kitty tree — **zero behaviour change** (NFR-001).
- Injects `--junitxml`/`-q` **inside this impl** (moved off the shared runner,
  `pre_review_gate.py:656`).
- `parse_results(raw)` parses JUnit XML from `raw.output_artifact_path` via `_parse_junit_xml`
  (`baseline.py:151`, imported into `pre_review_gate.py` at `:63`).
- **Owns the internal import.** `_load_gate_coverage_module` / `import_module(
  "tests.architectural._gate_coverage")` (`pre_review_gate.py:167,185`) and the demoted
  `_is_spec_kitty_source_repo` (`:153`) are **private internals of this class only**. The import
  is unreachable unless this impl is selected by activation (FR-009).

### `DeclaredCommandScopeSource` (portable default) — FR-003, FR-010
- `test_command()` = `shlex.split(review.test_command)` or `None`.
- `file_to_scope(path)` = `()` always — no narrowing; the declared command runs the **whole
  suite** (layout-agnostic; does not relocate #2330).
- `parse_results(raw)` parses the declared command's real pass/fail so a failing suite yields
  blocking-capable `NEW_FAILURES` (NFR-004).
- **Never** imports `_gate_coverage`; **never** assumes pytest or a `src/specify_cli/` layout.

## No-config behaviour (FR-012)

`test_command() -> None` → the gate does not run and does not crash → `GateOutcome.NO_COVERAGE`
**visible** warn (mirrors `baseline.capture_baseline` "No review.test_command configured;
skipping", `baseline.py:244`). A block only ever fires on `NEW_FAILURES` (layered above by the
hook), so absent config can never hard-fail a consumer. "Empty is never clean"
(`evaluate_with_scope` L797-798).

## Selection contract

The impl is chosen by **charter activation**, never by `_is_spec_kitty_source_repo` (FR-009).
`GateCoverageScopeSource` is reachable only when the Spec-Kitty pre-review handler is the
activated handler; otherwise `DeclaredCommandScopeSource` (or no gate at all) applies.
