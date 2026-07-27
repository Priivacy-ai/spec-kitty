# Research: ScopeSource gate follow-up — locked design decisions

**Mission**: `scopesource-gate-followup-01KY6S9P` · closes #2873 · follows #2871 half A (epic #2535)
**Base**: merged main `eb06ca176` (PRs #2874 coord-commit-integrity + #2820 dossier-parity landed).
Working tree HEAD `774143246` carries #2874's `_binding_role_for_lane` (compat golden = 157, verified
`tests/specify_cli/cli/commands/agent/test_tasks_compat_surface.py:479`).

**Status**: this is a **build map, not open research.** Every decision below was resolved by the
post-spec + fold/boyscout squads (`reviews/post-spec-squad.md`, `reviews/fold-boyscout-squad.md`) and
re-verified against the merged code cited by `file:line`. No decision is left open.

---

## D-1 (FR-008, B1 blocker) — Baseline artifact lifecycle: read/relocate BEFORE worktree teardown

**Decision.** In `_capture_baseline_via_scope_source`
(`src/specify_cli/review/baseline.py:491-536`) the baseline artifact MUST be **parsed (or relocated to
a stable out-of-worktree path) INSIDE the `_baseline_worktree` `with` block**, before teardown — not
after it.

**Evidence of the bug.** Today the run happens inside the block but the parse happens after it:

- `baseline.py:517-520` — `with _baseline_worktree(...) as tmp_worktree:` then
  `raw = _run_command_for_baseline(command, cwd=tmp_worktree)` (inside).
- `baseline.py:522` — `failures = tuple(scope_source.parse_results(raw))` runs **dedented, after the
  `with` exits** → after `git worktree remove --force` + `TemporaryDirectory` cleanup
  (`_baseline_worktree`, `baseline.py:230-260`).
- `raw.output_artifact_path` is recovered from a `--junitxml=<path>` arg by
  `_extract_junit_output_path` (`baseline.py:441-451`).

For `GateCoverageScopeSource` this is *accidentally* safe: its JUnit path is an **absolute
out-of-worktree tempfile** (`_junit_output_path` → `tempfile.mkdtemp(...)`,
`scope_source.py:429-433`), so the artifact survives teardown. For `DeclaredCommandScopeSource` whose
declared command writes a **worktree-relative** `--junitxml`, the artifact is deleted with the
worktree → `parse_results` (`scope_source.py:518-540`) falls through to the `FAIL`-text /
`_whole_run_failure` synthetic branch → baseline failure identities land in a **disjoint namespace**
from the head run's JUnit identities → `diff_baseline` (`baseline.py:544-580`) reports **every** head
failure as new → false `NEW_FAILURES` on every review. This is the exact bug the naive
"just activate `_capture_baseline_via_scope_source`" fix would ship.

**Rationale.** Baseline↔head symmetry is only real if both sides parse the artifact under the same
lifetime guarantees. The head path parses `raw` while its own tempdir is still live
(`run_scoped_tests_at_head`, `pre_review_gate.py:660-740`; `_run_raw_command`,
`pre_review_gate.py:808-845`). The baseline path must match: parse before teardown, or relocate the
artifact out of the worktree before teardown and parse the relocated copy.

**Alternatives rejected.**
- *Force every source to an absolute JUnit path.* Rejected: `DeclaredCommandScopeSource.test_command`
  (`scope_source.py:495-506`) is `shlex.split(review.test_command)` — the gate does not own the
  consumer's argv and cannot rewrite an embedded `--junitxml` without parsing arbitrary shell.
- *Leave the parse after teardown and special-case the text fallback.* Rejected: it silently accepts
  the disjoint-namespace path B1 identifies; FR-010 requires the worktree-relative-artifact case land
  in the SAME namespace as head, not a "best-effort text" one.

---

## D-2 (FR-009) — Source/parse-mode identity on `BaselineTestResult`; `from_dict` "unknown → unverified warn"

**Decision.** `BaselineTestResult` (`baseline.py:62-124`) gains ONE identity field capturing **source
class + parse-mode/artifact-presence** (not just class/command-shape). Identity is computed by a
single shared helper `scope_source_identity(scope_source, raw)` (new, home = `scope_source.py`) called
**at both** baseline capture (record) and head diff (compare), so the two sides can never draw the
token from different logic. `BaselineTestResult.from_dict` (`baseline.py:91-105`) defaults a missing
field to `"unknown"`, which the head path treats as **UNVERIFIED_BASELINE**, never a `KeyError` and
never a spurious `SOURCE_MISMATCH` (US1 AS4).

**Why class/command-shape alone is insufficient (squad B2).** B1's failure mode is *same class, same
command, different parse-mode* (JUnit artifact present vs. deleted → text). A class-only identity
cannot catch it. The token therefore folds in the parse-mode the artifact actually resolved to
(`junit_xml` when `raw.output_artifact_path` exists, else `text`/`none`), mirroring the exact branch
`parse_results` takes (`scope_source.py:527` — `if raw.output_artifact_path is not None and
raw.output_artifact_path.exists()`).

**Where the assertion runs.** The injected-`ScopeSource` head path ONLY — `_evaluate_via_scope_source`
(`pre_review_gate.py:851-909`), after the head run produces `raw` and before `parse_results` +
`_classify_current_failures`. It MUST NOT fire on the FR-004 shared-override tier
(`_mt_pre_review_gate_with_override_scope` → `evaluate_with_scope(scope_source=None)`,
`tasks_move_task.py:994-1027`; `pre_review_gate.py:952-985`), which has no injected source and no
recorded identity.

**Rationale.** One recorded token + one compare site keeps the mismatch check falsifiable and fail-open
(a mismatch or an unknown never blocks). `from_dict`'s default makes straddling-upgrade artifacts
degrade quietly.

**Alternatives rejected.**
- *Structured (class, mode) tuple field.* Rejected: `BaselineTestResult` round-trips through JSON
  (`to_dict`/`from_dict`, `baseline.py:77-105`); a flat string token keeps the `"unknown"` default and
  content hash trivially stable and diffable.
- *Compare against a re-derived head identity computed independently on each side.* Rejected: that is
  the two-namespace drift this mission kills — one helper, two call sites, or the split re-opens.

---

## D-3 (FR-011) — `GateOutcome.SOURCE_MISMATCH` as a NEW warn-shaped member; fail-open by construction

**Decision.** Add `SOURCE_MISMATCH = "source_mismatch"` as a **new** member of `GateOutcome`
(`pre_review_gate.py:748-756`). Do **NOT** overload `NO_COVERAGE` (its meaning is empty-scope /
no-config, `pre_review_gate.py:751`) and do **NOT** route the mismatch through `NEW_FAILURES`. The
verdict is warn-shaped: fails open, distinct `reason` string, `transition_applied=True`.

**Fail-open is by construction — assert, do not edit.** Both hard-stop paths are member-explicit
allowlists:
- Terminal: `_TERMINAL_OUTCOMES = frozenset({TIMED_OUT, CANCELLED})`
  (`verdict_aggregation.py:58-60`), consumed by `_first_terminal` (`:99-104`).
- Block: `blocking = tuple(v for v in ordered if v.outcome is GateOutcome.NEW_FAILURES)`
  (`verdict_aggregation.py:138`), consumed by `_should_block` (`:107-111`).

A new member appears in NEITHER allowlist, so it falls to `WARN_PROCEED`
(`verdict_aggregation.py:148-154`) automatically. **Do not add `SOURCE_MISMATCH` to those filters** —
prove fail-open with a test instead (FR-011, SC-004).

**The ONE live edit is the console ladder.** `_mt_pre_review_gate_console_warning`
(`tasks_move_task.py:1156-1184`) is the latent gap: its trailing
`return "[dim]…no new failures[/dim]"` (`:1184`) is an **unconditional fall-through** — any
`GateOutcome` member that isn't `NEW_FAILURES` / `NO_COVERAGE` / `UNVERIFIED_BASELINE` / `TIMED_OUT` /
`CANCELLED` renders as a clean "no new failures" pass. Fix: add an explicit `SOURCE_MISMATCH` branch,
convert the fall-through into an explicit `NO_NEW_FAILURES` branch, and add a **defensive `else`**
rendering the raw `outcome.value` so no future member can ever masquerade as a green pass again.

**Rationale.** `NO_COVERAGE` already means two things operators must distinguish (empty scope vs.
no-config); a mismatch is a third, orthogonal condition that half-B code (#2599) must branch on. A
dedicated member keeps the block/terminal exhaustiveness a pure structural property.

**Alternatives rejected.**
- *Reuse `NO_COVERAGE`.* Rejected (squad M1): conflates the empty-scope and mismatch conditions;
  operators and half B can't disambiguate.
- *Add an exhaustive `list(GateOutcome)` golden.* Rejected: none exists today; the console defensive
  `else` + the allowlist-is-explicit assertion is a smaller, sufficient blast radius (fold-squad
  Lens 3).

---

## D-4 (FR-003) — Shared `ScopeSource` factory hoist + seam placement (no import cycle)

**Decision.** Hoist the factory core out of `_mt_resolve_scope_source`
(`tasks_move_task.py:1250-1264`) into **`src/specify_cli/review/scope_source.py`** as
`resolve_scope_source(repo_root, *, filter_groups_override=None, composite_routing_override=None)`.
`_mt_resolve_scope_source` stays in `tasks_move_task.py` as a thin wrapper that threads the two
test seams `_pre_review_gate_filter_groups()` / `_pre_review_gate_composite_routing()`
(`tasks_move_task.py:828-847`) into the hoisted factory. The implement-time baseline path calls the
hoisted factory directly (production → both overrides `None`).

**Why `scope_source.py` and why no cycle.** `scope_source.py` already defines
`GateCoverageScopeSource` (`:288-433`) and is already imported by BOTH consumers —
`baseline.py:30` (`from specify_cli.review.scope_source import RawRunResult, ScopeSource`) and
`pre_review_gate.py:65-71`. Adding the factory there introduces **no new edge**. The seams stay in
`tasks_move_task.py` (they are monkeypatched by integration tests) and are passed as parameters, so
the factory never imports back into `tasks_move_task` — satisfying FR-003's "moved with it or passed
as parameters" clause and keeping `GateCoverageScopeSource`'s `*_override` fields
(`scope_source.py:303-304`) as the injection points.

**Baseline consumer wiring (FR-008).** `implement_capture_baseline`
(`workflow_executor.py:1135-1160`) currently calls `capture_baseline(...)` WITHOUT `scope_source`
(`:1153-1160`) — this is why `_capture_baseline_via_scope_source` is dormant. FR-008 injects
`scope_source=resolve_scope_source(main_repo_root)` at that call, activating the port path (with D-1's
lifecycle fix in place). `capture_baseline` already dispatches on a non-`None` `scope_source`
(`baseline.py:317-324`).

**Rationale.** One factory = one authority for "which source, resolved how". NFR-005 pins equivalence
= equal `test_command()` output AND equal parse-mode/identity at both call sites.

**Alternatives rejected.**
- *Leave the factory in `tasks_move_task.py` and import it from `baseline.py`.* Rejected: creates a
  `baseline.py → tasks_move_task.py` import cycle (`tasks_move_task` already imports `baseline`).
- *A brand-new `review/scope_factory.py` module.* Rejected: adds a module for one function both
  existing consumers already reach `scope_source.py` for; more surface, no payoff.

---

## D-5 (FR-005/FR-006) — Two independent predicates + `file_to_scope` ABC/mixin

**Decision.** Replace the single `isinstance(scope_source, ScopeBreakdownSource)` check — which today
decides BOTH concerns at TWO sites — with two independently-evaluable predicates backed by **separate
signals**:

- Welded site 1 (policy): `pre_review_gate.py:881` — `if isinstance(scope_source,
  ScopeBreakdownSource) and scope.is_empty:` → "empty derived scope ⇒ `NO_COVERAGE`".
- Welded site 2 (capability): `pre_review_gate.py:1013` (`_scope_result_from_source`) —
  `if isinstance(scope_source, ScopeBreakdownSource):` → "this source exposes breakdown metadata".

New predicates (home = `scope_source.py`, consumed in `pre_review_gate.py`):
- `exposes_scope_breakdown(source) -> bool` — capability signal: `isinstance(source,
  ScopeBreakdownSource)` (structural presence of `scope_breakdown`, `scope_source.py:148-165`).
- `empty_scope_is_coverage_gap(source) -> bool` — policy signal: reads a **distinct** class-level
  marker (`ClassVar` `treats_empty_scope_as_coverage_gap`, default `False`) that the mixin sets `True`.

Because the two predicates read two differently-named signals, a synthetic source can satisfy one
without the other (US3 AS3 proof) — the weld is *gone*, not renamed.

**`file_to_scope` as a default projection (FR-006, ABC/mixin — NOT a Protocol default).** Introduce an
ABC/mixin (proposed name `ScopeBreakdownMixin`) providing:
- concrete `file_to_scope(self, path) -> tuple[str,...]: return self.scope_breakdown(path).test_targets`
  (today hand-written on the class, `scope_source.py:355-362`),
- abstract `scope_breakdown(self, path) -> FileScopeBreakdown`,
- `ClassVar treats_empty_scope_as_coverage_gap = True`.

`GateCoverageScopeSource` (`scope_source.py:288`) inherits it and implements ONLY `scope_breakdown`.
`DeclaredCommandScopeSource` (`scope_source.py:481`) stays a **structural** `ScopeSource` implementer
— no `scope_breakdown`, no marker → `empty_scope_is_coverage_gap` returns `False` (its empty per-file
scope is not a gap; it runs its whole declared suite).

**Why ABC/mixin, not a `Protocol` default.** A `Protocol` with a default `file_to_scope` body does not
inject that body into a *structural* implementer — `DeclaredCommandScopeSource` satisfies the port by
shape, not by inheritance, so a Protocol default would never reach it. An ABC/mixin only affects the
class that explicitly inherits it (`GateCoverageScopeSource`), which is exactly the intent.

**Rationale.** Removes the weld so a future source can express the empty-is-gap policy without also
exposing breakdown metadata (or vice versa), with zero verdict change for the two shipped sources.

**Alternatives rejected.**
- *One renamed helper both sites call.* Rejected (squad carla-2): that is the weld renamed, not
  removed; the two decisions would still move together.
- *`Protocol` with a default `file_to_scope`.* Rejected (FR-006 explicit): won't reach the structural
  implementer.

---

## D-6 (FR-009) — Diff-time baseline read consumes #2874's C-008 kind-aware seam

**Decision.** FR-009's diff-time identity read MUST consume the already-merged #2874 kind-aware seam,
NOT reconstruct `feature_dir`. `_mt_resolve_gate_baseline` (`tasks_move_task.py:1282-1303`) already
reads through it:

```
baseline_read_dir = _resolve_workflow_read_dir(
    repo_root=st.main_repo_root, mission_slug=st.mission_slug,
    kind=MissionArtifactKind.WORK_PACKAGE_TASK,          # tasks_move_task.py:1298-1302
)
return BaselineTestResult.load(baseline_read_dir / "tasks" / wp_slug / "baseline-tests.json")
```

`_resolve_workflow_read_dir` lives at `workflow.py:573-587` and routes the WORK_PACKAGE_TASK-kind read
through the placement seam's `.read_dir(kind)`. The new `source_identity` field simply rides on the
`BaselineTestResult` loaded there — the read site needs **no change**; FR-009 only adds the field to
the loaded object and the comparison in the head path (D-2).

**Rationale (fold-squad Lens 3).** Under coord topology `st.feature_dir` is the kind-blind coord husk
where the PRIMARY-authored baseline does not exist; reading it there silently loses pre-existing-failure
suppression. #2874 already fixed the READ; this mission must not regress it by reconstructing a
`feature_dir`. The corresponding WRITE (`implement_capture_baseline`) already uses the sibling
`_resolve_workflow_placement(kind=WORK_PACKAGE_TASK)` seam (`workflow_executor.py:1176-1180`).

**Alternatives rejected.**
- *Reconstruct `feature_dir` for the identity read.* Rejected: reintroduces the coord-husk latent bug
  #2874 closed.

---

## Cross-cutting: what stays live vs. what is retired (C-002 / FR-001 / FR-002)

**Retired from `pre_review_gate.py` (FR-001 census tier):** `derive_test_scope` (`:324`),
`_glob_matches_file` (`:231`), `_glob_to_pytest_target` (`:249`), `_src_dir_segment` (`:257`),
`resolve_excluded_catchall_groups` (`:100`), `NAMED_CATCHALL_GROUPS` (`:96`), `_WHOLE_SRC_TREE_GLOB`
(`:97`), `_live_filter_groups` (`:204`), `_live_composite_routing` (`:220`), `_SRC_PACKAGE_PREFIX`
(`:110`), `_TESTS_PREFIX` (`:111`), `_EMPTY_COMPOSITE_ROUTE` (`:115`). Plus `_mt_pre_review_gate_verdict`
(`tasks_move_task.py:1061`, FR-002).

`evaluate_pre_review_gate` (`:1062`) loses its `scope_source is None` census branch (`:1104-1118`) and
the `filter_groups`/`composite_routing` params; the live registry path always injects a source
(`gate_registry.py:109-113`).

**Deletion is safe — the census branch has no live caller.** `_mt_pre_review_gate_verdict` is dead:
grep across `src/` finds only the compat re-export (`tasks.py:448`), two docstring mentions, and the
compat-surface entry (`test_tasks_compat_surface.py:249`) — no production call. The live for_review
path is `_mt_dispatch_one_gate` → `gate_registry.get_gate_handler` →
`evaluate_pre_review_gate(scope_source=ctx.scope_source)`.

**Kept live (C-002 — do NOT delete):** `_CompositeRoute` (`pre_review_gate.py:114`, referenced by the
kept seam signature `pre_review_gate._CompositeRoute` at `tasks_move_task.py:845`),
`_pre_review_gate_filter_groups` / `_pre_review_gate_composite_routing`
(`tasks_move_task.py:828-847`), `evaluate_with_scope` (`:912`), `run_scoped_tests_at_head` (`:630`,
live via the override tier's `scope_source=None` path), `ScopeResult` + `from_override` /
`describe_empty_reason` / `is_empty` (`:278-321`), `_mt_pre_review_gate_with_override_scope`
(`tasks_move_task.py:994`), `_mt_empty_scope_verdict` (`tasks_move_task.py:1030`),
`evaluate_pre_review_gate` (retained, census branch removed). The `scope_source.py` PRIVATE census copy
(`_resolve_excluded_catchall_groups` etc., `:195-411`) is untouched — it is the LIVE derivation
`GateCoverageScopeSource` runs.

**Compat golden delta:** 157 → **156** (remove `_mt_pre_review_gate_verdict`). Update in ONE atomic
change (C-004): drop the `tasks.py:448` re-export, the `test_tasks_compat_surface.py:249` tuple entry,
decrement the `tasks_move_task` seam count 76 → 75, and set the assertion
(`test_tasks_compat_surface.py:479`) 157 → 156. Confirm #2825's pre-existing `test_no_dead_symbols` /
`test_golden_count_ban` reds on the base BEFORE attributing any dead-symbol/golden failure to this diff
(baseline-red-gotcha).
</content>
</invoke>
