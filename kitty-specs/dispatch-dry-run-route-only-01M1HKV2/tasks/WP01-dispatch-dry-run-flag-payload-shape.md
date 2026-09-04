---
work_package_id: WP01
title: dispatch --dry-run flag + payload shape
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-008
- FR-009
- FR-010
- FR-011
- NFR-001
- NFR-002
- NFR-003
- C-001
- C-006
planning_base_branch: feat/dispatch-dry-run-route-only-3840
merge_target_branch: feat/dispatch-dry-run-route-only-3840
branch_strategy: Planning artifacts for this mission were generated on feat/dispatch-dry-run-route-only-3840. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/dispatch-dry-run-route-only-3840 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/invocation/
create_intent: []
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/cli/commands/dispatch.py
- src/specify_cli/invocation/executor.py
- src/specify_cli/invocation/router.py
- docs/api/cli-commands.md
- tests/specify_cli/invocation/cli/test_dispatch.py
- tests/invocation/test_dispatch_recommendation.py
- tests/glossary/test_chokepoint.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP01 – `dispatch --dry-run` flag + payload shape

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Add a `--dry-run` flag to `spec-kitty dispatch` that returns a `"status": "dry_run"` JSON
payload carrying the routing signal (`profile_id`, `action`, `router_confidence`) while
writing **nothing** — no `kitty-ops/` file, no `kitty-ops/ops-index.jsonl` line, no
`.kittify/events/glossary/*.jsonl` file, no SaaS propagator submit — closing issue #3840's
core ask (spec.md FR-001–FR-004, FR-008–FR-011).

## Context

Today every `spec-kitty dispatch --json` call mints a truthy `invocation_id`, opens a
governance Op (`kitty-ops/<id>.jsonl` + an `ops-index.jsonl` append), and — when a request
token is unrecognized — persists a `TermCandidateObserved` glossary event. A UI or
automation consumer that wants a routing signal as the operator types has no side-effect-free
way to get one; it either litters governance history or does not probe at all.

The plan's chosen approach (plan.md "Summary" / "Seam") is a **new sibling method**
`ProfileInvocationExecutor.dry_run()`, not a `dry_run: bool` flag threaded through
`invoke()`. `invoke()` unconditionally mints a truthy `invocation_id = _new_ulid()` as its
first statement, and that value is load-bearing for every write that follows (the Op record
filename, the glossary chokepoint's event-context gate, the SaaS propagator payload).
`dry_run()` mirrors only the **read** half of `invoke()` — routing resolution, the advisory
model-routing recommendation, governance-context assembly, the glossary scan — and never
reaches the write half at all. This is also how FR-003's non-obvious requirement (never
mint or pass a truthy `invocation_id` into `GlossaryChokepoint.run()`) is satisfied
**structurally**, not by an `if` branch that could regress silently: `dry_run()` calls
`chokepoint.run(request_text, invocation_id="", actor_id=actor)`, and
`GlossaryChokepoint._build_event_context`'s existing `if not invocation_id: return None`
gate (chokepoint.py:221) already suppresses the event write — **no code change is needed
in `chokepoint.py`**, only a test that pins this existing gate behavior explicitly.

Downstream of this WP: WP02 adds the `alternatives` field to both dry-run and real
dispatch payloads (depends on this WP's `dry_run()`/`to_dry_run_dict()` existing first);
WP03 lands the SK-08 selection-logic fix after WP02. Do not anticipate either — this WP's
scope is the flag, the payload shape, and the write-suppression guarantee only.

**Two JSON shapes on the dry-run path** (plan.md, read in full before starting): the
**success** branch reuses `InvocationPayload`'s field set (`to_dry_run_dict()`, minus
`invocation_id`/`close_contract`, `status="dry_run"`). The **`ROUTER_AMBIGUOUS`** branch is
a deliberate, narrow exception — a small dedicated dict (`profile_id: null, action: null,
router_confidence: "ambiguous", alternatives: [...]`) built by a new module-level helper
`build_ambiguous_dry_run_payload(request_text, err) -> dict[str, object]`, colocated in
`executor.py` beside `to_dry_run_dict()` — **not** a `dispatch.py`-local helper, and **not**
a second competing `InvocationPayload`-shaped type. `InvocationPayload`'s `profile_id`/
`action` slots stay non-Optional (`mypy --strict`) for every other caller.

`dry_run()` does **not** catch `RouterAmbiguityError` internally — it lets `RouterAmbiguityError`
propagate unchanged out of `route()`, exactly as `invoke()` does today, covering all three of
its error codes: `"ROUTER_AMBIGUOUS"`, `"ROUTER_NO_MATCH"`, and — on the Level-1 explicit-
`profile_hint` branch — `"PROFILE_NOT_FOUND"`. A literal `ProfileNotFoundError` does **not**
propagate out of `route()`: the explicit-hint branch already catches it internally
(`router.py`'s `except ProfileNotFoundError as exc: raise RouterAmbiguityError(..., "PROFILE_NOT_FOUND", ...)`)
and re-raises it as `RouterAmbiguityError(error_code="PROFILE_NOT_FOUND")` before it would ever
reach `dry_run()`'s caller. All distinguishing logic lives in
`_dispatch_impl` (`dispatch.py`), which gains a **second, separate** `try`/`except` scoped
only to the `executor.dry_run(...)` call — kept distinct from, never merged with, the
existing `try`/`except` around `executor.invoke(...)`. Its `except RouterAmbiguityError as
e:` clause branches explicitly on `e.error_code`:

```python
if dry_run:
    try:
        payload = executor.dry_run(request, profile_hint=profile_hint, actor=_detect_actor())
    except RouterAmbiguityError as e:
        if e.error_code == "ROUTER_AMBIGUOUS":
            # FR-009: exit 0 with the ambiguous dry-run payload, alternatives populated.
            typer.echo(json.dumps(build_ambiguous_dry_run_payload(request, e)))
            return
        # ROUTER_NO_MATCH: "no partial signal worth reporting" — same exit-1 shape real
        # dispatch already produces. Reuse the existing handler's JSON, do not duplicate it.
        _emit_routing_error_and_exit(e)
    except ProfileNotFoundError as e:
        # Dead/defensive branch: route()'s Level-1 explicit-hint branch already catches
        # ProfileNotFoundError internally and re-raises RouterAmbiguityError(error_code=
        # "PROFILE_NOT_FOUND") before it reaches this call site, so this clause is never
        # live-hit — mirrors the existing pragma-no-cover dead branch on the real
        # invoke()-path handler above. Kept for defense-in-depth, not because it fires.
        profile_not_found_routing(e)
        return
    typer.echo(json.dumps(payload.to_dry_run_dict([])))
    return
```

**Note on the `to_dry_run_dict([])` call above**: at this WP's final commit, `InvocationPayload`
has no `alternatives` field yet (T002 step 2 explicitly forbids adding one here) —
`to_dry_run_dict()` takes `alternatives` as a parameter for exactly this reason, and this WP
always passes `[]` (WP01 never has real alternatives to populate; that only becomes possible
once WP02 exists). **WP02's T009 subtask is what changes this call site**: once
`InvocationPayload` gains a real `alternatives` field (T009 step 1) and `to_dry_run_dict()` is
updated to read it directly off `self` (T009 step 4), this line becomes
`payload.to_dry_run_dict(payload.alternatives)` or simplifies to the no-arg
`payload.to_dry_run_dict()`. Do not write either of those forms in this WP — both raise
`AttributeError` before WP02 lands, because `payload.alternatives` does not exist yet.

Extract the existing `error_obj = {...}` construction inside the current
`except RouterAmbiguityError` handler around `executor.invoke(...)` into a small shared
helper (e.g. `_emit_routing_error_and_exit(e: RouterAmbiguityError) -> NoReturn`) called
from **both** the invoke()-path handler and the dry-run-path `else` branch above — one
exit-1 JSON shape, built in one place, two call sites. Do not hand-duplicate it.

`route()`'s `ROUTER_AMBIGUOUS` raise (currently L373, `errors.py`'s
`RouterAmbiguityError`) must also carry a `confidence` key on every candidate dict —
sourced the same way the winning-candidate dicts already are elsewhere in `route()` — so
`build_ambiguous_dry_run_payload` can populate `alternatives` from `err.candidates` without
a schema mismatch. **This WP only fixes the ONE raise site that exists in `route()` today**
(the post-tiebreaker "still ambiguous" raise). WP03 inherits the same obligation for the
new raise site(s) its SK-08 restructuring introduces — do not attempt to anticipate those
here; this WP's router.py touch is narrowly the `confidence` key on the one existing raise
site, nothing else in `route()`'s selection logic.

**ATDD-First is charter-binding (C-011, spec.md C-001).** This WP's failing-first tests
(subtask T001) must be committed as their **own commit**, before the implementation commit
(subtasks T002–T005), with **RED verified on `feat/dispatch-dry-run-route-only-3840` at
mission start** (`--dry-run` does not exist — Typer rejects the unrecognized option) and
**GREEN on this WP's final commit**.

## Marker + CI job for every new test (verified against `.github/workflows/*.yml` — do not
assume, do not invent a marker)

- **`tests/specify_cli/invocation/cli/test_dispatch.py`** — existing module marker
  `pytestmark = [pytest.mark.non_sandbox, pytest.mark.fast]`. New tests in this WP MUST
  carry the same markers (do not invent a new one). Collected by: the `doctrine-charter-tests`
  job (`.github/workflows/doctrine-charter-tests.yml`, path-triggered on
  `tests/specify_cli/invocation/**`, runs `-m "fast and not windows_ci and not timing"`) and
  by `fast-tests-core-misc`'s `specify-cli-rest-2` shard (`.github/workflows/ci-quality.yml`,
  positional path `tests/specify_cli/invocation`, runs `-m "fast and not windows_ci and not
  regression"`).
- **`tests/invocation/test_dispatch_recommendation.py`** — existing module marker
  `pytestmark = [pytest.mark.unit]` **only** (no `fast`). New tests here MUST carry the same
  `unit` marker (do not add `fast` — that would silently double-collect the test in two
  disjoint job tiers). `tests/invocation/` (top-level, distinct from
  `tests/specify_cli/invocation/`) is walked ONLY by `doctrine-charter-tests.yml`'s
  path-trigger, but that job's own pytest run filters `-m "fast and not windows_ci and not
  timing"` — since this file's tests are `unit`, not `fast`, they are **deselected there**.
  The job that actually executes them is `unit-contract-residual`
  (`.github/workflows/ci-quality.yml`), a whole-tree, always-on (no path gate) job running
  `-m "(unit or contract) and not (fast or integration or ... )"` over `tests/` — confirmed
  by reading the workflow directly. State this explicitly in your PR notes if asked: this
  file's coverage comes from `unit-contract-residual`, not from the invocation-specific
  `doctrine-charter-tests` job whose name would otherwise suggest it.
- **`tests/glossary/test_chokepoint.py`** — existing module marker `pytestmark =
  pytest.mark.fast`. The new pin test for `_build_event_context`'s falsy-`invocation_id`
  gate MUST carry the same `fast` marker. `tests/glossary/` is not excluded by
  `fast-tests-core-misc`'s `core-misc` shard `--ignore=` list (whole-tree `paths: ''` minus
  ignores), so it is collected there, running `-m "fast and not windows_ci and not
  regression"`. It is NOT collected by the `module-packs.yml` corpus job (`-m "corpus and
  not windows_ci"` only — this test is `fast`, not `corpus`), nor by
  `doctrine-charter-tests.yml` (that workflow's path list does not include `tests/glossary/`).

### Subtask T001: Write the failing-first ATDD tests (own commit, before implementation)

**Purpose**: Pin every WP1 user-observable behavior as a RED test before any implementation
code exists, per charter C-011 / spec.md C-001.

**Steps**:
1. In `tests/specify_cli/invocation/cli/test_dispatch.py`, add (matching the file's existing
   `pytestmark = [pytest.mark.non_sandbox, pytest.mark.fast]`):
   - `test_dry_run_writes_nothing_to_kitty_ops` — snapshot `kitty-ops/` file count and
     `kitty-ops/ops-index.jsonl` line count before and after **3** `spec-kitty dispatch
     "<request>" --dry-run --json` calls against a clean checkout; assert byte-identical
     state (directory listing equal, line count equal). This is SC-001's exact assertion
     shape.
   - `test_dry_run_suppresses_glossary_event_write` — with a request whose tokens are
     unrecognized by the glossary index, snapshot the **set of files** under
     `.kittify/events/glossary/` (by name) before/after 3 dry-run calls; assert unchanged,
     treating "directory absent" and "directory present but empty" as the same unchanged
     state (SC-002's explicit requirement — do not require a `FileNotFoundError` special
     case). Separately assert the returned JSON's `glossary_observations` field is still
     populated (the in-memory scan still ran; only the persisted write is suppressed).
   - `test_dry_run_payload_shape` — assert the JSON payload has `"status": "dry_run"`, no
     `invocation_id` key, no `close_contract` key, and does have `profile_id`, `action`,
     `router_confidence`.
   - `test_dry_run_profile_hint_returns_exact_confidence` — `spec-kitty dispatch "<request>"
     --dry-run --profile <id> --json`; assert `router_confidence == "exact"` and
     `alternatives == []` (FR-008's explicit-hint dry-run combo — not covered by any other
     test in this list, which all omit `--profile`).
   - `test_dry_run_under_empty_charter_fallback` — mirror the fixture/assertion shape of the
     existing (non-dry-run) `test_dispatch_empty_charter_auto_routes_to_generic_agent` in this
     same file, but with `--dry-run` added; assert `envelope["empty_charter_fallback"] is
     True` and the generic-agent routing signal (`profile_id == "generic-agent"`,
     `router_confidence == "generic_fallback"`) surfaces identically under `--dry-run`
     (FR-010's dry-run case — not covered by any other test in this list).
   - `test_dry_run_ambiguous_returns_dry_run_payload_not_exit_1` — construct a request that
     would raise `ROUTER_AMBIGUOUS` under real dispatch; assert `--dry-run` exits 0 with
     `profile_id: null, action: null, router_confidence: "ambiguous"` and `alternatives`
     populated with every tied candidate.
   - `test_dry_run_no_match_still_raises` / `test_dry_run_unknown_profile_still_raises` —
     assert `ROUTER_NO_MATCH` and an unknown `--profile` both still exit 1 with the same
     structured error JSON as real dispatch, unchanged by `--dry-run`.
   - `test_dry_run_does_not_submit_to_saas_propagator` — construct the executor with a
     mock/spy `InvocationSaaSPropagator`, patched at the call site (`dispatch.py`'s
     `_build_executor` constructs it — patch there, matching this file's existing
     `patch()`-target convention), and assert `submit` is never called across 3 `--dry-run`
     invocations. This is the third named suppressed-write surface (alongside `kitty-ops/`
     and the glossary event log) — do not skip it.
2. In `tests/invocation/test_dispatch_recommendation.py` (matching the file's existing
   `pytestmark = [pytest.mark.unit]` — do not add `fast`, see marker note above), add a test
   asserting the advisory model-routing recommendation still populates under `--dry-run`
   (it is already read-only — `build_charter_context(..., mark_loaded=False)` — so this is a
   pin, not new plumbing).
3. In `tests/glossary/test_chokepoint.py` (matching the file's existing `pytestmark =
   pytest.mark.fast`), add a direct unit-level test calling `GlossaryChokepoint._build_event_context`
   (or the public `run()` entry point) with a falsy `invocation_id=""` and asserting it
   returns `None` / short-circuits before any file write — pinning the existing gate at
   chokepoint.py:221 explicitly, since this WP relies on that gate without changing it.
4. Run the new tests and confirm every one fails for the expected reason: `--dry-run` is an
   unrecognized Typer option (the CLI-level tests fail with a Typer usage error, not an
   assertion error) — this is RED on `feat/dispatch-dry-run-route-only-3840` at mission
   start.
5. Commit this test-only diff as its own commit (e.g. `test(dispatch): add failing-first
   ATDD for --dry-run flag (WP1)`), before touching any implementation file.

**Files**: `tests/specify_cli/invocation/cli/test_dispatch.py` (+~150 lines),
`tests/invocation/test_dispatch_recommendation.py` (+~30 lines),
`tests/glossary/test_chokepoint.py` (+~20 lines).

**Validation**: `pytest tests/specify_cli/invocation/cli/test_dispatch.py
tests/invocation/test_dispatch_recommendation.py tests/glossary/test_chokepoint.py -v`
shows every new test RED, and the reason is "no `--dry-run` flag exists" / "gate already
passes" as expected — not an unrelated collection error.

### Subtask T002: `InvocationPayload.to_dry_run_dict()` + `build_ambiguous_dry_run_payload()` (executor.py)

**Purpose**: Give `dispatch.py` the two payload-shape builders it needs, colocated in
`executor.py` per plan.md's "Two JSON shapes" mechanism.

**Steps**:
1. In `src/specify_cli/invocation/executor.py`, add `RouterAmbiguityError` to the existing
   `from specify_cli.invocation.errors import (...)` block (currently
   `InvalidModeForEvidenceError`, `InvocationError`, `UndeterminedModeForEvidenceError`
   only) — needed to type-annotate `build_ambiguous_dry_run_payload`'s `err` parameter.
2. Add `InvocationPayload.to_dry_run_dict(self, alternatives: list[dict[str, str]]) ->
   dict[str, object]`: returns the existing `InvocationPayload` field set minus
   `invocation_id` and `close_contract`, plus `"status": "dry_run"` and `"alternatives":
   alternatives`. (WP02 will later populate `alternatives` from a real field on
   `InvocationPayload` itself — for this WP, thread it through as a parameter so
   `to_dry_run_dict` doesn't need to know about a field that doesn't exist yet. If WP02's
   sequencing makes it cleaner to add the empty-list `alternatives` slot now, that is
   WP02's call, not this WP's — do not add the slot here.)
3. Add module-level `build_ambiguous_dry_run_payload(request_text: str, err:
   RouterAmbiguityError) -> dict[str, object]`, colocated beside `to_dry_run_dict()`:
   returns `{"status": "dry_run", "profile_id": None, "action": None, "router_confidence":
   "ambiguous", "alternatives": [...built from err.candidates...]}`.
4. Type-check: `mypy --strict src/specify_cli/invocation/executor.py` — the non-Optional
   `profile_id`/`action` slots on `InvocationPayload` itself are untouched; only the
   ambiguous-branch dict (a plain `dict[str, object]`, not an `InvocationPayload`) carries
   `None`.

**Files**: `src/specify_cli/invocation/executor.py` (+~40 lines: 1 import edit, 2 new
functions/methods).

**Validation**: `mypy --strict src/specify_cli/invocation/executor.py` passes; no existing
`invoke()` behavior changes (diff review: `invoke()`'s body itself is untouched by this
subtask).

### Subtask T003: `ProfileInvocationExecutor.dry_run()` (executor.py)

**Purpose**: The core new read-only execution path — mirrors `invoke()`'s read half,
never reaches its write half.

**Steps**:
1. Add `ProfileInvocationExecutor.dry_run(self, request_text: str, profile_hint: str | None
   = None, actor: str = "unknown") -> InvocationPayload`.
2. Mirror `invoke()`'s routing resolution, advisory recommendation, and governance-context
   assembly (`build_charter_context(..., mark_loaded=False)`, already read-only).
3. Call `chokepoint.run(request_text, invocation_id="", actor_id=actor)` — an explicit
   falsy (empty-string) `invocation_id`, **never** a minted ULID. Do not compute or pass any
   value that could be truthy on this path. This is FR-003's structural guarantee.
4. Do **not** call `self._writer.write_started(...)`, `self._writer.write_glossary_observation(...)`,
   or `self._propagator.submit(...)` anywhere in `dry_run()`. Do not mint a truthy
   `invocation_id` anywhere in the method body.
5. Let `RouterAmbiguityError` propagate unchanged out of `route()` — no internal catch,
   exactly as `invoke()` does today. This covers all three of `route()`'s error codes
   (`ROUTER_AMBIGUOUS`, `ROUTER_NO_MATCH`, and — on the explicit-`profile_hint` branch —
   `PROFILE_NOT_FOUND`); a literal `ProfileNotFoundError` never reaches `dry_run()`'s caller,
   since `route()`'s explicit-hint branch already catches and re-raises it as
   `RouterAmbiguityError(error_code="PROFILE_NOT_FOUND")` internally.
6. `invoke()`'s own body is otherwise unchanged by this subtask (WP02 later adds
   `alternatives=result.alternatives` to its final `InvocationPayload(...)` construction —
   not this WP's concern).

**Files**: `src/specify_cli/invocation/executor.py` (+~50 lines: 1 new method).

**Validation**: A scratch/manual call to `dry_run()` against a request matching a canonical
verb returns an `InvocationPayload` with the routing signal populated; grepping the method
body confirms zero references to `write_started`, `write_glossary_observation`, or
`propagator.submit`.

### Subtask T004: `RouterAmbiguityError` candidate dicts carry `confidence` (router.py, FR-009)

**Purpose**: Close the schema gap FR-009 names — the existing `ROUTER_AMBIGUOUS` raise's
candidate dicts (currently `profile_id`/`action`/`match_reason` only) must also carry a
`confidence` key so `build_ambiguous_dry_run_payload` can build `alternatives` from
`err.candidates` without omitting a Key-Entities-required field.

**Steps**:
1. In `src/specify_cli/invocation/router.py`, locate the `ROUTER_AMBIGUOUS` raise inside
   `route()` (currently ~L373 — the post-tiebreaker "still ambiguous" raise; this is the
   ONE raise site that exists in `route()` at this WP's time — WP03 introduces new raise
   sites later and inherits the same obligation there, not here).
2. Add a `confidence` key to every candidate dict this raise site builds, sourced the same
   way the winning-candidate dicts already are elsewhere in `route()` (i.e. from the same
   `_confidence` value already computed for each candidate during the verb/keyword match
   passes — do not invent a new confidence-computation path).
3. Do **not** touch the `if len(candidates) == 1:` single-candidate return or the
   `routing_priority` tiebreaker block's selection logic in this subtask — those are WP02's
   (`alternatives=` population) and WP03's (SK-08 rerank) concerns respectively. This
   subtask's router.py diff is narrowly the `confidence` key on the one existing
   `ROUTER_AMBIGUOUS` raise's candidate dicts.

**Files**: `src/specify_cli/invocation/router.py` (+~5 lines: one raise-site edit).

**Validation**: `test_dry_run_ambiguous_returns_dry_run_payload_not_exit_1` (T001) and
`test_router_ambiguous_candidates_carry_confidence_key`-style assertion pass; the
pre-existing `test_router_priority_tiebreaker_selects_higher_priority` test continues to
pass unmodified (this subtask does not touch the tiebreaker's selection logic).

### Subtask T005: `--dry-run` CLI flag + dispatch branch (dispatch.py)

**Purpose**: Wire the flag and the dry-run branch into `_dispatch_impl`, per the mechanism
stated in Context above.

**Steps**:
1. Add `--dry-run: bool = typer.Option(False, "--dry-run", help="...")` to `dispatch()`.
2. In `_dispatch_impl`, add the dry-run branch exactly as shown in Context above: a
   **second, separate** `try`/`except` scoped only to `executor.dry_run(...)`, kept distinct
   from the existing `try`/`except` around `executor.invoke(...)`.
3. Extract the existing invoke()-path `error_obj = {...}` construction into
   `_emit_routing_error_and_exit(e: RouterAmbiguityError) -> NoReturn`; call it from both
   the invoke()-path handler and the dry-run-path `else` branch. Do not duplicate the JSON
   construction.
4. Handle the empty-charter fallback identically to real dispatch (FR-010):
   `resolve_generic_fallback()` is already read-only; `dry_run()` (T003) already calls it
   exactly as `invoke()` does, so `empty_charter_fallback: true` and the generic-agent
   routing signal surface identically with no extra branching needed in `dispatch.py`. The
   one console-only side-channel (`_render_empty_charter_warning`) stays unaffected either
   way — it is outside the JSON payload contract.

**Files**: `src/specify_cli/cli/commands/dispatch.py` (+~40 lines: new option, new branch,
new shared helper).

**Validation**: All of T001's ATDD tests transition RED → GREEN. `spec-kitty dispatch "fix
the failing test" --dry-run --json` against a clean checkout exits 0, prints `"status":
"dry_run"`, and creates no `kitty-ops/` directory.

### Subtask T006: Contract doc + generated CLI reference + gates

**Purpose**: Close FR-011 and keep the generated CLI reference in sync; run the mission's
gate set before declaring this WP done.

**Note on `owned_files`**: `kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/contracts/cli-do-output.md`
is edited by this subtask but is **not** listed in this WP's `owned_files` frontmatter —
`spec-kitty agent mission finalize-tasks` hard-rejects any `owned_files` entry under
`kitty-specs/` (`INVALID_WP_OWNED_FILES_KITTY_SPECS`), since `kitty-specs/` is planning-
artifact territory outside the WP-ownership model. Edit this file anyway per FR-011 — the
ownership declaration constraint does not narrow this subtask's actual scope, only what can
be recorded in `wps.yaml`/frontmatter.

**Steps**:
1. Hand-edit `kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/contracts/cli-do-output.md`
   (NOT generated — confirmed by inspection, no `<!-- BEGIN GENERATED -->` envelope): add
   the `"status": "dry_run"` JSON branch (both the success shape and the `ROUTER_AMBIGUOUS`
   shape) and note the new `alternatives` field placeholder on the existing `"status":
   "open"` example (WP02 populates its actual values; this WP documents the branch and the
   field's existence).
2. Before regenerating `docs/api/cli-commands.md`, rebase onto the latest
   `feat/dispatch-dry-run-route-only-3840`/base tip to pick up any concurrent regeneration
   of the same file (plan.md notes PR #3842 also regenerates a different section of this
   file — check its merge status; if merged, rebase first so this WP's diff to the generated
   file is scoped to the `dispatch` section only).
3. Regenerate:
   ```
   PYTHONPATH=. uv run python scripts/docs/build_cli_reference.py \
     --output docs/api/cli-commands.md \
     --agent-output docs/api/agent-subcommands.md
   ```
   Do not hand-patch `docs/api/cli-commands.md`.
4. Run the gate set scoped to this mission:
   ```
   ruff check .
   mypy --strict src/specify_cli/invocation/ src/specify_cli/cli/commands/dispatch.py src/glossary/chokepoint.py
   pytest tests/specify_cli/invocation/ tests/invocation/test_dispatch_recommendation.py tests/glossary/ -v
   pytest tests/architectural/test_no_legacy_terminology.py
   PYTHONPATH=. uv run python scripts/docs/check_docs_freshness.py --ci
   ```
5. Per AGENTS.md's baseline-red gotcha: before attributing any red to this WP, confirm it is
   red on this WP's own change and green on `planning_base_branch`
   (`feat/dispatch-dry-run-route-only-3840` at mission start) — cite issue #3284 for known
   pre-existing red, do not "fix" it.
6. Commit the implementation (T002–T006) as its own commit, distinct from T001's ATDD
   commit.

**Files**: `kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/contracts/cli-do-output.md`
(+~30 lines), `docs/api/cli-commands.md` (regenerated, mechanical diff only).

**Validation**: All gates above pass (or show only pre-existing #3284/#3283-tracked red);
`check_docs_freshness.py --ci` passes; `markdownlint` conformance on `cli-do-output.md`.

## Definition of Done

- [ ] T001's ATDD tests are committed as their own commit, verified RED on
      `feat/dispatch-dry-run-route-only-3840` at mission start (Typer rejects the
      unrecognized `--dry-run` option).
- [ ] `spec-kitty dispatch "<request>" --dry-run --json` exits 0 and returns `"status":
      "dry_run"` with `profile_id`, `action`, `router_confidence` populated, no
      `invocation_id` key, no `close_contract` key.
- [ ] **Absence-of-writes, three explicit checks** (per SC-001/SC-002, made concrete, not
      just "verify no writes happen"):
  1. `kitty-ops/` file-count and `kitty-ops/ops-index.jsonl` line-count snapshot before/after
     N (≥3) `--dry-run` calls are byte-identical.
  2. The **set of files** under `.kittify/events/glossary/` (by name) is unchanged
     before/after N `--dry-run` calls on a request with unrecognized tokens — "directory
     absent" and "directory present but empty" both count as the same unchanged state; the
     returned JSON's `glossary_observations` field is still populated (scan ran, write did
     not).
  3. A mocked/spied `InvocationSaaSPropagator.submit` is asserted **never called** across N
     `--dry-run` invocations, patched at the call site (`dispatch.py`'s `_build_executor`).
- [ ] `--dry-run --profile <id>` returns `router_confidence: "exact"`, `alternatives: []`
      (FR-008).
- [ ] `--dry-run` on a request that would raise `ROUTER_AMBIGUOUS` under real dispatch exits
      0 with `profile_id: null, action: null, router_confidence: "ambiguous"`, `alternatives`
      populated with every tied candidate (FR-009).
- [ ] `--dry-run` on `ROUTER_NO_MATCH` and an unknown `--profile` both still exit 1 with the
      same structured error JSON as real dispatch (FR-009).
- [ ] `--dry-run` under the empty-charter fallback surfaces `empty_charter_fallback: true`
      and the generic-agent routing signal (FR-010).
- [ ] `err.candidates` on the one existing `ROUTER_AMBIGUOUS` raise site in `route()` (this
      WP's scope only) carries a `confidence` key on every entry (FR-009).
- [ ] `kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/contracts/cli-do-output.md`
      documents the `dry_run` branch (FR-011); `docs/api/cli-commands.md` is regenerated,
      not hand-edited.
- [ ] New tests carry the exact markers named above (`non_sandbox`+`fast` in
      `test_dispatch.py`, `unit`-only in `test_dispatch_recommendation.py`, `fast` in
      `test_chokepoint.py`) — no invented markers.
- [ ] `test_router_priority_tiebreaker_selects_higher_priority` still passes unmodified.
- [ ] `ruff check .`, `mypy --strict` (scoped paths above), and the targeted pytest paths
      pass, modulo pre-existing #3284/#3283-tracked red (attributed per AGENTS.md's
      baseline-red gotcha, not silently green-washed).
- [ ] Implementation is committed as its own commit, distinct from T001's ATDD commit.

Implement with: `spec-kitty agent action implement WP01 --agent claude`

## Risks

- **`invocation_id=""` regressing to a truthy value.** Mitigated structurally (T003 never
  computes or passes a minted ULID on the dry-run path) and pinned by
  `test_dry_run_suppresses_glossary_event_write` (T001) and the direct chokepoint gate pin
  in `test_chokepoint.py`.
- **Duplicating the invoke()-path error-JSON construction instead of extracting the shared
  helper** — would drift the two error shapes apart silently over time. Mitigated by T005's
  explicit instruction to extract `_emit_routing_error_and_exit` and call it from both
  paths.
- **Marker mismatch causing a test to be collected by no job** (the SK-144/#3241-shaped
  failure mode this repo has hit before) — mitigated by the explicit per-file marker table
  above, verified against the live workflow YAML, not assumed.
- **Regenerating `docs/api/cli-commands.md` without rebasing first**, clobbering PR #3842's
  already-landed section of the same generated file if it has merged — mitigated by T006's
  explicit rebase-before-regenerate step.

## Reviewer Guidance

- Confirm T001's ATDD commit precedes the implementation commit in git history, and that
  the ATDD tests were actually RED on `feat/dispatch-dry-run-route-only-3840` before this
  WP's implementation landed (not merely "written first" — verify the RED claim).
- Confirm `dry_run()` never calls `write_started`/`write_glossary_observation`/
  `propagator.submit` and never mints a truthy `invocation_id` — this is a structural
  property, not a runtime guard; read the method body directly.
- Confirm the dry-run `try`/`except` in `dispatch.py` is genuinely a **second, separate**
  block from the existing `invoke()` handler, not a merged/shared `except` clause branching
  on `dry_run` internally (plan.md explicitly rules out the merged-clause approach as
  unworkable — Python `except` selects by type, not a boolean).
- Confirm the new tests' markers match their file's existing sibling tests exactly, and spot
  -check that `tests/invocation/test_dispatch_recommendation.py`'s new test is actually
  collected (by `unit-contract-residual`, not `doctrine-charter-tests`) rather than silently
  orphaned.
- Confirm `router.py`'s diff in this WP is narrowly the `confidence`-key addition to the one
  existing `ROUTER_AMBIGUOUS` raise site — no selection-logic change (that is WP03's scope).
- Confirm every genuinely pytest-testable entry in this WP's `requirement_refs`
  frontmatter — FR-001, FR-002, FR-003, FR-004, FR-008, FR-009, FR-010, C-001 —
  traces to a named, committed T001 test, not only to a Definition-of-Done checkbox.
  FR-008 and FR-010 specifically must trace to
  `test_dry_run_profile_hint_returns_exact_confidence` and
  `test_dry_run_under_empty_charter_fallback` respectively. **FR-011 is verified via
  T006's markdownlint/`check_docs_freshness.py` gates, not a T001 pytest** — do not
  demand a pytest trace for it. **NFR-001, NFR-002, NFR-003, and C-006 are
  scope/non-behavior notes** (spec.md states NFR-002/NFR-003 as "considered and
  absent," NFR-001 is a structural/analytical claim — dry-run strictly omits work real
  dispatch performs, so no dedicated latency test is expected — and C-006 is a
  reviewer-scope clarification, not a pinnable behavior) — no test is expected for
  these four.
