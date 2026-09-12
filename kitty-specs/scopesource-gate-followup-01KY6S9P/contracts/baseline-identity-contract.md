# Contract: baseline source/parse-mode identity + lifecycle + #2874 read seam

**Traces**: FR-008, FR-009, FR-010, FR-012, NFR-005, C-005
**Homes**: `baseline.py` (`BaselineTestResult`, capture), `pre_review_gate.py:851-909` (head compare),
`tasks_move_task.py:1282-1303` (#2874 kind-aware read)

## The identity field

```python
# round-trip: skip: illustrative field add — executable round-trip in tests/review/test_baseline.py
@dataclass(frozen=True)
class BaselineTestResult:
    ...                                   # existing fields, baseline.py:66-75
    source_identity: str = "unknown"      # NEW: "<SourceClass>/<parse_mode>"
```

| Aspect | Value |
|--------|-------|
| Format | `"<SourceClassName>/<parse_mode>"` |
| `parse_mode` ∈ | `junit_xml`, `text`, `none`, `unknown` |
| Producer | `scope_source_identity(scope_source, raw)` (new, `scope_source.py`) — ONE helper, BOTH sides |
| `to_dict` | add `"source_identity": self.source_identity` (`baseline.py:77-89`) |
| `from_dict` | `source_identity=data.get("source_identity", "unknown")` (`baseline.py:91-105`) |

**Parse-mode derivation (mirrors `parse_results`, `scope_source.py:518-540`):**

| Condition on `raw` | `parse_mode` |
|--------------------|--------------|
| `raw.output_artifact_path` exists | `junit_xml` |
| no artifact, `FAIL`-lines present in stdout/stderr | `text` |
| no artifact, non-zero exit, nothing parseable | `none` |

## Backward-compat obligation (US1 AS4 / FR-009)

```yaml
# round-trip: skip: illustrative degradation table, not a fixture
legacy_artifact_without_field:
  from_dict: source_identity -> "unknown"        # no KeyError
  head_diff_behaviour: UNVERIFIED_BASELINE        # never SOURCE_MISMATCH, never a crash
sentinel_baseline (failed == -1):
  unchanged: diff_baseline returns everything-new  # baseline.py:561-562, untouched
```

## Parse-mode matching at diff time (FR-009)

Runs in the **injected-`ScopeSource` head path ONLY** (`_evaluate_via_scope_source`,
`pre_review_gate.py:851-909`) — NEVER the FR-004 shared-override tier
(`evaluate_with_scope(scope_source=None)`, `pre_review_gate.py:952-985`; no injected source, no
recorded identity).

```python
# round-trip: skip: illustrative diff-time gate — executable coverage in tests/review/test_pre_review_gate_engine.py
head_identity = scope_source_identity(scope_source, raw)          # after the head run
if baseline is not None and baseline.source_identity != "unknown" and head_identity != baseline.source_identity:
    return GateVerdict(outcome=GateOutcome.SOURCE_MISMATCH, scope=scope,
                       reason=f"baseline captured under {baseline.source_identity}; "
                              f"head ran under {head_identity} — failure identities are not comparable")
failures = scope_source.parse_results(raw)
return _classify_current_failures(failures, scope=scope, baseline=baseline)
```

| baseline state | head identity | verdict |
|----------------|---------------|---------|
| `None` | any | `UNVERIFIED_BASELINE` (existing, `_classify_current_failures` `:785-791`) |
| `source_identity == "unknown"` | any | `UNVERIFIED_BASELINE` (legacy degrade) |
| known, equal | equal | normal `NO_NEW_FAILURES` / `NEW_FAILURES` diff |
| known, differs | differs | `SOURCE_MISMATCH` (warn, fail-open) |

## Artifact lifecycle (FR-008 / B1) — read/relocate BEFORE teardown

```python
# round-trip: skip: illustrative before/after — executable coverage in tests/review/test_baseline.py (FR-010 parity)
# _capture_baseline_via_scope_source, baseline.py:491-536
with _baseline_worktree(repo_root, base_branch) as tmp_worktree:
    if tmp_worktree is None:
        return _make_sentinel(...)
    raw = _run_command_for_baseline(command, cwd=tmp_worktree)
    failures = tuple(scope_source.parse_results(raw))                 # MOVED INSIDE the with (was :522, post-teardown)
    identity = scope_source_identity(scope_source, raw)              # recorded at the same point
# ... build BaselineTestResult(..., source_identity=identity, failures=failures)
```

**Invariant.** For `DeclaredCommandScopeSource` writing a **worktree-relative** `--junitxml`, the
artifact is parsed while the worktree still exists → baseline identities share the head run's namespace.
For `GateCoverageScopeSource` (absolute tempfile JUnit, `scope_source.py:429-433`) behaviour is
unchanged.

## FR-010 parity test matrix

Baseline and head MUST land in the same failure-identity namespace across all three:

| Source | Artifact | Zero-new-failure change → must NOT be `NEW_FAILURES` |
|--------|----------|------------------------------------------------------|
| `GateCoverageScopeSource` | absolute JUnit tempfile | ✓ |
| `DeclaredCommandScopeSource` | **worktree-relative** JUnit (`--junitxml`) | ✓ (the B1 case) |
| `DeclaredCommandScopeSource` | `FAIL`-text convention | ✓ |

Plus a parity assertion: baseline `source_identity` == head identity in each case (NFR-005).

## #2874 kind-aware read seam (FR-009 / D-6)

The diff-time load MUST consume the already-merged seam, not reconstruct `feature_dir`:

```python
# round-trip: skip: illustrative — merged code at tasks_move_task.py:1296-1303
baseline_read_dir = _resolve_workflow_read_dir(              # workflow.py:573-587
    repo_root=st.main_repo_root, mission_slug=st.mission_slug,
    kind=MissionArtifactKind.WORK_PACKAGE_TASK,             # C-008, coord-topology safe
)
return BaselineTestResult.load(baseline_read_dir / "tasks" / wp_slug / "baseline-tests.json")
```

The new `source_identity` rides on the loaded object — the read site needs **no change**. Reconstructing
a `feature_dir` here is a regression (reopens the coord-husk bug #2874 closed).

## Anti-narrowing guard (FR-012 / C-005)

A focused test asserts the baseline command is run WITHOUT head's per-file `scope.test_targets`
appended. Command **authority** is unified; **scope** legitimately differs (baseline broad, head
narrowed). The head path appends targets (`pre_review_gate.py:889` — `[*command, *scope.test_targets]`)
but the baseline path (`_run_command_for_baseline`, `baseline.py:454-488`) runs the bare command — the
guard pins that a future refactor cannot silently narrow the baseline.
</content>
