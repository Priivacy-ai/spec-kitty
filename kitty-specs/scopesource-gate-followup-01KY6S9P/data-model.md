# Data Model: ScopeSource gate follow-up

**Mission**: `scopesource-gate-followup-01KY6S9P` · base merged main `eb06ca176` (HEAD `774143246`).
Every entity below is named against the merged code by `file:line`. This is the explicit register the
post-spec squad required be carried into plan (`reviews/post-spec-squad.md` "Carried into plan").

---

## 1. `BaselineTestResult.source_identity` — new identity field (FR-009)

**Home**: `src/specify_cli/review/baseline.py:62-124` (the `@dataclass(frozen=True)`).

| Aspect | Value |
|--------|-------|
| Field name | `source_identity` |
| Type | `str` |
| Default | `"unknown"` |
| Captures | producing-**source class** + **parse-mode / artifact-presence** — e.g. `"GateCoverageScopeSource/junit_xml"`, `"DeclaredCommandScopeSource/junit_xml"`, `"DeclaredCommandScopeSource/text"`, `"DeclaredCommandScopeSource/none"` |
| Parse-mode vocabulary | `junit_xml` (artifact resolved + parsed), `text` (`FAIL`-line convention), `none` (unparseable non-zero → whole-run synthetic), `unknown` (legacy artifact, no field) |

**Why parse-mode, not just class (squad B2).** B1's failure mode is *same class, same command,
different parse-mode* (JUnit present vs. deleted → text). A class-only token cannot catch it; the mode
mirrors exactly the branch `parse_results` takes (`scope_source.py:527` — artifact exists → JUnit;
else text; else whole-run synthetic).

**Producer.** Computed by the shared helper `scope_source_identity(scope_source, raw)` (new; home
`scope_source.py`) so baseline capture and head diff draw the token from ONE function (NFR-005). Set
into the result in `_capture_baseline_via_scope_source` (`baseline.py:491-536`).

**`to_dict` / `from_dict` (`baseline.py:77-105`).**
- `to_dict`: add `"source_identity": self.source_identity`.
- `from_dict`: `source_identity=data.get("source_identity", "unknown")` — a straddling-upgrade artifact
  lacking the key degrades to `"unknown"`, never a `KeyError` (US1 AS4). `"unknown"` at diff time ⇒
  the head path emits `UNVERIFIED_BASELINE`, never a spurious `SOURCE_MISMATCH`.

**Watch-item (fold-squad, benign).** Adding the field changes `baseline-tests.json`'s content hash →
shifts a mission's #2820 dossier parity hash. This is per-mission runtime data, not a shared
fixture/symbol collision — no action, documented only.

---

## 2. `GateOutcome.SOURCE_MISMATCH` — new warn-shaped member (FR-011)

**Home**: `src/specify_cli/review/pre_review_gate.py:748-756` (the `GateOutcome(StrEnum)`).

| Aspect | Value |
|--------|-------|
| Member | `SOURCE_MISMATCH = "source_mismatch"` |
| Shape | warn (fail-open): `transition_applied=True`, distinct `reason`, `run_state=COMPLETED` |
| Distinct from | `NO_COVERAGE` (empty-scope / no-config) and `NEW_FAILURES` (hard block) — never overload either |

**Verdict construction.** Built in `_evaluate_via_scope_source` (`pre_review_gate.py:851-909`) when the
head-side identity (`scope_source_identity(scope_source, raw)`) differs from a **known** (non-`unknown`)
`baseline.source_identity`. Returns
`GateVerdict(outcome=SOURCE_MISMATCH, scope=scope, reason="baseline captured under <a>; head ran under
<b> — failure identities are not comparable")`. If `baseline` is `None` or its `source_identity` is
`"unknown"`, the path degrades to the existing `UNVERIFIED_BASELINE` classification
(`_classify_current_failures`, `pre_review_gate.py:771-805`), NOT a mismatch.

**Aggregation handling (fail-open by construction — assert, do not edit).**
- `verdict_aggregation._TERMINAL_OUTCOMES = frozenset({TIMED_OUT, CANCELLED})` (`:58-60`) — member
  allowlist; `SOURCE_MISMATCH` is absent → never terminal.
- Block predicate `blocking = (… v.outcome is GateOutcome.NEW_FAILURES)` (`:138`) — member allowlist;
  `SOURCE_MISMATCH` is absent → never blocks.
- Net: `aggregate_verdicts` (`:114-154`) routes it to `WARN_PROCEED` automatically. FR-011 forbids
  editing those filters; prove fail-open with a test (SC-004).

**Console handling (the ONE live edit).** `_mt_pre_review_gate_console_warning`
(`tasks_move_task.py:1156-1184`):
- add an explicit `SOURCE_MISMATCH` branch (warn-styled line naming the two identities),
- convert the trailing unconditional `return "[dim]…no new failures[/dim]"` (`:1184`) into an explicit
  `NO_NEW_FAILURES` branch,
- add a **defensive `else`** rendering the raw `outcome.value`, so no future member ever renders as a
  clean pass again.

---

## 3. Shared `ScopeSource` factory (FR-003) + kind-aware seam homes

| Symbol | Proposed home | Shape | Notes |
|--------|---------------|-------|-------|
| `resolve_scope_source` | `review/scope_source.py` (new) | `resolve_scope_source(repo_root: Path, *, filter_groups_override=None, composite_routing_override=None) -> ScopeSource` | Hoisted core of `_mt_resolve_scope_source` (`tasks_move_task.py:1250-1264`); constructs `GateCoverageScopeSource(repo_root, filter_groups_override=…, composite_routing_override=…)`. Both consumers already import `scope_source.py` → no new import edge. |
| `_mt_resolve_scope_source` | stays `tasks_move_task.py:1250` | `(gate_repo_root) -> ScopeSource` | Thin wrapper: calls `resolve_scope_source(...)` threading `_pre_review_gate_filter_groups()` / `_pre_review_gate_composite_routing()` (`:828-847`). Keeps the two seams monkeypatchable; factory never imports back into `tasks_move_task`. |
| `_pre_review_gate_filter_groups` / `_pre_review_gate_composite_routing` | stay `tasks_move_task.py:828-847` | `() -> Mapping \| None` | Production returns `None`; integration tests monkeypatch. FR-003 "seams move-with or are parameterized" is satisfied by parameterization. |
| Baseline write-side placement | `workflow_executor.py:1176-1180` (`_resolve_workflow_placement(kind=WORK_PACKAGE_TASK)`) | existing | Unchanged; FR-008 only adds `scope_source=resolve_scope_source(main_repo_root)` to the `capture_baseline(...)` call (`:1153-1160`). |
| Diff-time baseline read seam | `tasks_move_task.py:1282-1303` (`_resolve_workflow_read_dir(kind=WORK_PACKAGE_TASK)`, def at `workflow.py:573-587`) | existing (#2874 C-008) | Unchanged; the new `source_identity` rides on the loaded `BaselineTestResult` (FR-009 / D-6). |

---

## 4. Two independent predicates + the `file_to_scope` ABC/mixin (FR-005/FR-006)

**Predicates** (home `scope_source.py`; consumed in `pre_review_gate.py`):

| Predicate | Signature | Backing signal | Replaces |
|-----------|-----------|----------------|----------|
| `exposes_scope_breakdown` | `(source: ScopeSource) -> bool` | `isinstance(source, ScopeBreakdownSource)` — structural presence of `scope_breakdown` (`scope_source.py:148-165`) | the `isinstance` at `pre_review_gate.py:1013` (`_scope_result_from_source`) |
| `empty_scope_is_coverage_gap` | `(source: ScopeSource) -> bool` | `getattr(source, "treats_empty_scope_as_coverage_gap", False)` — a **distinct** `ClassVar` marker | the `isinstance` at `pre_review_gate.py:881` (empty ⇒ `NO_COVERAGE`) |

The two read **different** signals → a synthetic source may set the `ClassVar` `True` without
implementing `scope_breakdown` (policy without capability), or implement `scope_breakdown` with the
`ClassVar` `False` (capability without policy) — the US3 AS3 weld-is-gone proof.

**ABC/mixin `ScopeBreakdownMixin`** (proposed name; home `scope_source.py`):

```python
# round-trip: skip: illustrative mixin shape — the executable behaviour lives in tests/review/test_scope_source.py
class ScopeBreakdownMixin(abc.ABC):
    treats_empty_scope_as_coverage_gap: ClassVar[bool] = True

    @abc.abstractmethod
    def scope_breakdown(self, path: str) -> FileScopeBreakdown: ...

    def file_to_scope(self, path: str) -> tuple[str, ...]:
        return self.scope_breakdown(path).test_targets   # default projection (FR-006)
```

- `GateCoverageScopeSource` (`scope_source.py:288-433`) **inherits** it: implements only
  `scope_breakdown` (already at `:364-411`), drops the now-inherited hand-written `file_to_scope`
  (`:355-362`), and gains the `treats_empty_scope_as_coverage_gap = True` marker.
- `DeclaredCommandScopeSource` (`scope_source.py:481-540`) stays a **structural** `ScopeSource`
  implementer — no `scope_breakdown`, no marker → `empty_scope_is_coverage_gap` → `False`.
- Not a `Protocol` default (FR-006): a Protocol default body never reaches a structural implementer;
  an ABC/mixin affects only the class that inherits it.

---

## 5. Artifact-lifecycle change in `_capture_baseline_via_scope_source` (FR-008 / B1)

**Home**: `baseline.py:491-536`.

| Before (buggy) | After (fixed) |
|----------------|---------------|
| `raw = _run_command_for_baseline(...)` inside `with _baseline_worktree(...)` (`:517-520`); `failures = scope_source.parse_results(raw)` **after** the `with` (`:522`, post-teardown) | parse (or relocate the artifact to a stable out-of-worktree path, then parse the relocated copy) **inside** the `with`, before teardown; record `source_identity = scope_source_identity(scope_source, raw)` at the same point |

Effect: `DeclaredCommandScopeSource` with a worktree-relative `--junitxml` parses its JUnit artifact
while it still exists → baseline identities share the head run's namespace → `diff_baseline`
(`baseline.py:544-580`) reports only genuinely-new failures. `GateCoverageScopeSource` (absolute
tempfile JUnit, `scope_source.py:429-433`) is unaffected either way.

**Campsite fold (FR-013, WP-C rewrites this file anyway).** Delete the unused `timezone` import
(`baseline.py:25` — `from datetime import datetime, timezone, UTC`; only `datetime`/`UTC` are used) and
tighten the `ruff.toml` legacy-debt entry for `baseline.py` from `["ARG001","F401","S314","S602"]` to
`["ARG001","S314"]` (F401 clears once the import is gone; S602 is already stale — no `shell=True` in the
file; ARG001 stays for the dead `mission_slug` param `baseline.py:267`, explicitly OUT of scope).

---

## 6. Retire / keep inventory (C-002 / FR-001 / FR-002)

**Delete — `pre_review_gate.py` dead census tier (FR-001):**

| Symbol | Line |
|--------|------|
| `derive_test_scope` | `:324` |
| `_glob_matches_file` | `:231` |
| `_glob_to_pytest_target` | `:249` |
| `_src_dir_segment` | `:257` |
| `resolve_excluded_catchall_groups` | `:100` |
| `NAMED_CATCHALL_GROUPS` | `:96` |
| `_WHOLE_SRC_TREE_GLOB` | `:97` |
| `_live_filter_groups` | `:204` |
| `_live_composite_routing` | `:220` |
| `_SRC_PACKAGE_PREFIX` | `:110` |
| `_TESTS_PREFIX` | `:111` |
| `_EMPTY_COMPOSITE_ROUTE` | `:115` |

Plus the `scope_source is None` census branch of `evaluate_pre_review_gate` (`:1104-1118`) and its
`filter_groups`/`composite_routing` params. Plus `_mt_pre_review_gate_verdict`
(`tasks_move_task.py:1061`, FR-002).

**Keep live (C-002 — do NOT delete):** `_CompositeRoute` (`pre_review_gate.py:114`, referenced by the
kept seam `pre_review_gate._CompositeRoute` at `tasks_move_task.py:845`), `_pre_review_gate_filter_groups`
/ `_pre_review_gate_composite_routing` (`tasks_move_task.py:828-847`), `evaluate_with_scope` (`:912`),
`run_scoped_tests_at_head` (`:630`, live via the override tier's `scope_source=None` path), `ScopeResult`
+ `from_override`/`describe_empty_reason`/`is_empty` (`:278-321`),
`_mt_pre_review_gate_with_override_scope` (`tasks_move_task.py:994`), `_mt_empty_scope_verdict`
(`tasks_move_task.py:1030`), `evaluate_pre_review_gate` (census branch removed). The **private** census
copy inside `scope_source.py` (`_resolve_excluded_catchall_groups`, `_glob_matches_file`, … `:195-411`)
is untouched — it is the LIVE derivation `GateCoverageScopeSource` runs.

**Sole-live-caller audit (FR-002 precondition).** The live for_review path is `_mt_dispatch_one_gate` →
`gate_registry.get_gate_handler("spec-kitty-pre-review").run(ctx)` → `_spec_kitty_pre_review_handler`
(`gate_registry.py:99-114`) → `evaluate_pre_review_gate(scope_source=ctx.scope_source)` — always a
non-`None` source. `_mt_pre_review_gate_verdict` (the only census-branch caller) has NO production call
site: grep finds only the compat re-export (`tasks.py:448`), docstrings, and the compat-surface entry
(`test_tasks_compat_surface.py:249`). The audit is a documented + test-asserted precondition, red-first
(C-006).

---

## 7. Compat golden delta (C-004 / NFR-004)

**Exact delta on the merged base: 157 → 156** (verified against
`tests/specify_cli/cli/commands/agent/test_tasks_compat_surface.py`):

| Site | Change |
|------|--------|
| `test_tasks_compat_surface.py:479` | `assert len(SYMBOL_TO_MODULE) == 157` → `== 156` |
| `test_tasks_compat_surface.py:249` | remove `"_mt_pre_review_gate_verdict"` from `_TASKS_MOVE_TASK` |
| `test_tasks_compat_surface.py:153` docstring | `tasks_move_task … = 76` → `= 75` |
| `tasks.py:448` | remove the `_mt_pre_review_gate_verdict as _mt_pre_review_gate_verdict` re-export |

One atomic change (C-004) — never an accidental import break. Base is post-#2874 (which added
`_binding_role_for_lane` → 156→157, `test_tasks_compat_surface.py:475-479`); this mission's single
removal takes it to 156. Confirm #2825's pre-existing `test_no_dead_symbols` / `test_golden_count_ban`
reds on the base BEFORE attributing any such failure to this diff (baseline-red-gotcha).
</content>
