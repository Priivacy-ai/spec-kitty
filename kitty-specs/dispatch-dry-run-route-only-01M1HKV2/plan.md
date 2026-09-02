# Implementation Plan: `dispatch --dry-run` — side-effect-free routing query mode

**Branch**: `feat/dispatch-dry-run-route-only-3840` | **Date**: 2026-09-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/dispatch-dry-run-route-only-01M1HKV2/spec.md`

**Note**: This template is filled in by the `/spec-kitty.plan` command. See `src/doctrine/missions/software-dev/command-templates/plan.md` for the execution workflow.

## Summary

Issue #3840: `spec-kitty dispatch --json` has no side-effect-free routing-query mode — every
call mints an `invocation_id`, opens a governance Op (`kitty-ops/<id>.jsonl` +
`ops-index.jsonl`), and (when a token is unrecognized) persists a `TermCandidateObserved`
glossary event. This mission adds three work packages, gated in this order:

- **WP1** — a `--dry-run` flag on `dispatch` that returns a `"status": "dry_run"` JSON payload
  with a routing signal and writes **nothing** (FR-001–FR-004, FR-008–FR-011).
- **WP2** — a new `alternatives` field on `RouterDecision` / the payload shape, exposing the
  router's already-computed losing candidates, threaded onto **both** the dry-run and real
  dispatch paths (FR-005).
- **WP3** — the SK-08 selection-logic fix: `ActionRouter.route()` today lets a lone/weak
  `domain_keyword` candidate outrank the request's own `canonical_verb` match via
  `routing_priority`, and lets a lone domain-keyword candidate auto-select instead of failing
  closed (FR-006/FR-007). Lands last, as its own commit, because it changes selection behavior
  on every real (Op-opening) dispatch call — the additive work must not stall on it (operator
  decision, spec.md Clarifications #1).

The technical approach is a **new sibling method** on `ProfileInvocationExecutor`
(`dry_run()`) rather than threading a `dry_run: bool` flag through `invoke()`. `invoke()`
unconditionally mints a truthy `invocation_id = _new_ulid()` as its first statement and that
value is *load-bearing* for every write that follows (the Op record filename, the glossary
chokepoint's event-context gate, the SaaS propagator payload). A boolean flag threaded through
`invoke()` would have to special-case every one of those call sites from inside a single, long,
branchy method (`invoke()` spans executor.py:284-430 — 147 total lines, 103 non-blank/
non-comment lines) already at meaningful branching complexity; a sibling method mirrors only the
**read** half of `invoke()` (routing resolution, advisory recommendation, governance-context
assembly, glossary scan) and never reaches the write half at all, which is also how FR-003's
non-obvious requirement — *never mint or pass a truthy `invocation_id` into
`GlossaryChokepoint.run()`* — is satisfied structurally rather than by an `if` branch that could
regress silently.

## Technical Context

**Language/Version**: Python 3.11+ (existing repo standard, no change)
**Primary Dependencies**: none added or changed. Touches only first-party modules:
`specify_cli.cli.commands.dispatch`, `specify_cli.invocation.{executor,router,errors}`,
`glossary.chokepoint` (verification only, no edit expected — see Seam below).
**Storage**: `kitty-ops/*.jsonl` (Op records), `.kittify/events/glossary/*.jsonl` (glossary
trail) — this mission's entire functional point is that WP1's new path writes to **neither**.
**Testing**: `pytest` (existing repo suite; no new test framework). Targeted paths:
`tests/specify_cli/invocation/test_router.py`, `tests/specify_cli/invocation/cli/test_dispatch.py`,
`tests/invocation/test_dispatch_recommendation.py`.
**Target Platform**: CLI, same as all `spec-kitty` commands — no platform-specific concern.
**Project Type**: Single project (this is the spec-kitty CLI repository itself).
**Performance Goals**: NFR-001 — dry-run must not add latency over real dispatch. Since dry-run
omits the Op write, the glossary-observation write, and the propagator submit that real
dispatch performs, and reuses the same read-only `build_charter_context(...)` call, dry-run is
structurally *at most* as expensive as real dispatch, never more. No caching layer is
introduced.
**Constraints**: NFR-002 (no lock/flock semantics — invoke path uses only atomic appends, so
dry-run has no lock-release edge case), NFR-003 (no production-deploy / HITL approval step —
every path here is local filesystem read/compute, or for real dispatch, local writes plus a
best-effort background SaaS submit).
**Scale/Scope**: 5 implementation files touched (one, `chokepoint.py`, verification-only), 1
generated doc (`docs/api/cli-commands.md`, regenerated, not hand-edited), 1 hand-maintained
contract doc (`cli-do-output.md`), 1 `CHANGELOG.md` entry (WP3, per "Downstream/external
consumer impact" below), 3 test files extended. No new files.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against `.kittify/charter/charter.md` (binding; wins over `CLAUDE.md`/`AGENTS.md` on
any drift — none found for this mission):

- **Single canonical authority** — `RouterDecision`/`InvocationPayload`/`RouterAmbiguityError`
  remain the one owning shape for routing/invocation results; this mission extends them
  in-place rather than introducing a second competing payload type for the dry-run case (see
  "Two JSON shapes on the dry-run path" below for the one narrow, justified exception, an
  ambiguous-branch-only minimal dict that is *not* a competing canonical type).
- **Architectural alignment** — confined to `specify_cli.invocation` / `specify_cli.cli.commands`
  / `glossary` (verification-only). No kernel/doctrine seam touched (spec.md C-006, confirmed
  below).
- **ATDD-first (C-011)** — satisfied per-WP; see "ATDD-First obligations" below.
- **`__all__` (C-007)** — does not bind (spec.md C-006); confirmed below, not silently dropped.
- **External Contract Packages** — `spec-kitty-events`/`spec-kitty-tracker` are not touched;
  confirmed below.
- **Terminology Canon** — no `--feature`/`feature` surface introduced; the new flag is
  `--dry-run`, not `--mission`-adjacent, so the mission-vs-feature rename rule does not apply
  here, but no code in the touched files introduces a `feature` alias either.

No violations found. Nothing in Complexity Tracking below.

## Seam: exactly where each symbol lands

No kernel/doctrine seam is touched (spec.md C-006). Everything below is CLI-command-layer or
`specify_cli.invocation` / `glossary` package code — no CLI command reaches past a service
into kernel internals; this plan introduces no such reach.

| File | Change | New vs. existing branch |
|---|---|---|
| `src/specify_cli/cli/commands/dispatch.py` | new `--dry-run: bool = typer.Option(False, "--dry-run", ...)` param on `dispatch()`; `_dispatch_impl` grows a dry-run branch that calls `executor.dry_run(...)` inside its OWN `try`/`except`, scoped only to that call and kept separate from the existing `try`/`except` around `executor.invoke(...)`; its `except RouterAmbiguityError as e:` clause branches explicitly on `e.error_code` — `"ROUTER_AMBIGUOUS"` builds and emits the exit-0 dry-run ambiguous payload (via the executor.py-colocated builder, see below); anything else reuses the existing exit-1 error-JSON behavior via a small shared helper (WP1). Full mechanism stated in "Two JSON shapes on the dry-run path" below | new branch + new scoped `try`/`except` in `_dispatch_impl`, new CLI option on `dispatch` |
| `src/specify_cli/invocation/executor.py` | new public method `ProfileInvocationExecutor.dry_run(request_text, profile_hint=None, actor="unknown") -> InvocationPayload` (WP1, propagates `RouterAmbiguityError`/`ProfileNotFoundError` unchanged like `invoke()` does — no internal catch); `InvocationPayload` grows a `alternatives: list[dict[str,str]]` slot (WP2) and a new `to_dry_run_dict(alternatives)` method that omits `invocation_id`/`close_contract` and sets `status="dry_run"` (WP1); a new module-level `build_ambiguous_dry_run_payload(request_text, err: RouterAmbiguityError) -> dict[str, object]` helper is colocated here beside `to_dry_run_dict()` (WP1), not in `dispatch.py` — see "Two JSON shapes on the dry-run path" below for why; this relocation requires adding `RouterAmbiguityError` to `executor.py`'s existing `from specify_cli.invocation.errors import (...)` block (currently `InvalidModeForEvidenceError`, `InvocationError`, `UndeterminedModeForEvidenceError` only — `RouterAmbiguityError` is not yet imported here, unlike in `dispatch.py`, which already has it via its own `except RouterAmbiguityError` handler) | new method (`dry_run`), new method (`to_dry_run_dict`), new function (`build_ambiguous_dry_run_payload`), new slot (`alternatives`), new import (`RouterAmbiguityError`, needed to type-annotate `build_ambiguous_dry_run_payload`'s `err` parameter) — `invoke()`'s body is unchanged except adding `alternatives=result.alternatives` (or `[]` on the explicit-hint branch) to its final `InvocationPayload(...)` construction (WP2) |
| `src/glossary/chokepoint.py` | **no code change** — `_build_event_context`'s `if not invocation_id: return None` (line 221) already exists and already does the job; WP1 only needs to call `chokepoint.run(request_text, invocation_id="", actor_id=actor)` from the new `dry_run()` method, i.e. never pass the (nonexistent, in this path) minted ULID in. A new test pins this existing gate behavior explicitly (see ATDD section) | none — verification-only |
| `src/specify_cli/invocation/router.py` | `RouterDecision` gains `alternatives: list[dict[str, str]]` (WP2, no default — see "4 call sites" below); `route()`'s three `RouterDecision(...)` construction sites (explicit-hint L262, single-candidate L343, tiebreaker-unique-winner L363) each populate it; `ROUTER_AMBIGUOUS` raise at L373 gets a `confidence` key added to every candidate dict (FR-009, WP1); WP3 restructures the `if len(candidates) == 1:` block (L343) and the `routing_priority` tiebreaker block (L352-370) to separate the verb tier from the keyword tier, and adds ≥1 new `RouterAmbiguityError(..., "ROUTER_AMBIGUOUS", ...)` raise site(s) for the lone/weak-keyword and 2+-keyword-tier cases (AC-2, AC-4) — each new raise site must also carry the `confidence` key per FR-009's extended obligation | new field (`alternatives`), new/restructured branches inside `route()` (WP3) |
| `src/specify_cli/invocation/empty_charter.py` | `resolve_generic_fallback()`'s single `RouterDecision(...)` construction (L123) gets `alternatives=[]` (WP2 — this path never computes candidates, so the empty list is definitionally correct, not a placeholder) | existing construction site, one new kwarg |
| `src/specify_cli/invocation/errors.py` | `RouterAmbiguityError` itself is unchanged (WP1/WP3 only change what `route()` puts *into* its `candidates` list, not the exception's own shape) | none |
| `kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/contracts/cli-do-output.md` | add the `"status": "dry_run"` JSON branch (both success and `ROUTER_AMBIGUOUS` shapes) and the `alternatives` field on the existing `"status": "open"` example (FR-011) | new section, hand-edited (see "Generated artifacts" below — this file is NOT generated) |
| `docs/api/cli-commands.md` | regenerated (not hand-edited) once WP1's `--dry-run` flag/help text exists, via `scripts/docs/build_cli_reference.py` (see "Generated artifacts" below) | mechanical regeneration |
| `CHANGELOG.md` | new entry documenting the auto-route behavior change, per "Downstream/external consumer impact (WP3)" below (WP3) | new entry, hand-edited |

### "4 call sites" needing `alternatives=` (WP2 — do not miss one)

`RouterDecision` is a frozen dataclass with no default for the new field, so adding it without
a default makes every existing constructor call a compile-time-missing-argument error until
updated. There are exactly **four** construction sites in the current codebase:

1. `router.py` `route()` Level 1, explicit `profile_hint` branch (L262-267) → `alternatives=[]`
   (the router never computes candidates on this path — Edge Case / Acceptance Scenario 2).
2. `router.py` `route()` single-candidate return (L343-350) → `alternatives=[]` (only one
   candidate existed).
3. `router.py` `route()` tiebreaker-unique-winner return (L363-370) → `alternatives=` every
   entry of `candidates` other than the selected one, each rendered as
   `{"profile_id", "action", "confidence": c["_confidence"], "match_reason"}` (SC-003 requires
   *every* non-winning candidate, not only those that tied for top `routing_priority`).
4. `empty_charter.py` `resolve_generic_fallback()` (L123) → `alternatives=[]` (this path never
   calls `route()` at all — it short-circuits before the router runs).

WP3 (landing after WP2) adds new/restructured `RouterDecision` success returns inside its
verb-tier-first restructuring of `route()`; those inherit the same `alternatives=` population
rule.

## Two JSON shapes on the dry-run path (a deliberate, scoped exception to "reuse `InvocationPayload`")

FR-004/Key-Entities describe the dry-run envelope as reusing `InvocationPayload`'s field set.
That is true for the **success** case (a winning profile exists). It is **not** true for the
FR-009 `ROUTER_AMBIGUOUS`-on-dry-run case (User Story 2, Acceptance Scenario 3 / Edge Cases):
that branch reports `profile_id: null, action: null, router_confidence: "ambiguous",
alternatives: [...]` and nothing else meaningful — no governance context was ever assembled
(routing never resolved to a profile, so `build_charter_context` was never called), no
recommendation, no glossary scan tied to a winning profile.

`InvocationPayload`'s slots are typed non-Optional (`profile_id: str`, `action: str`) for
`mypy --strict`, and that typing is correct for every other caller (`invoke()`, and dry-run's
own success branch). Forcing `str | None` through those slots to accommodate one narrow branch
would ripple an `Optional` into the real-dispatch success contract for no benefit. The plan
therefore keeps `InvocationPayload` untouched in shape for this case and builds the
ambiguous-case dict directly via a small dedicated helper (mechanism below) rather than
constructing a real `InvocationPayload` with fabricated non-null placeholders. This is not a
second competing canonical payload type — it is the one place the contract legitimately has no
winner to describe, and Key Entities already documents this branch as a distinct shape ("On the
`ROUTER_AMBIGUOUS` dry-run branch, `profile_id`/`action` are `null` and `router_confidence` is
`"ambiguous"`").

### The mechanism, stated explicitly

`ProfileInvocationExecutor.dry_run()` does **not** catch `RouterAmbiguityError` internally — it
lets both `"ROUTER_AMBIGUOUS"` and `"ROUTER_NO_MATCH"` (and the explicit-hint branch's
`ProfileNotFoundError`) propagate unchanged out of `route()`, exactly as `invoke()` does today.
All of the distinguishing logic lives in `_dispatch_impl` (`dispatch.py`), which gains a
**second, separate** `try`/`except` scoped only to the `executor.dry_run(...)` call — kept
distinct from, never merged with, the existing `try`/`except` around `executor.invoke(...)`:

```
if dry_run:
    try:
        payload = executor.dry_run(request, profile_hint=profile_hint, actor=_detect_actor())
    except RouterAmbiguityError as e:
        if e.error_code == "ROUTER_AMBIGUOUS":
            # FR-009: exit 0 with the ambiguous dry-run payload, alternatives populated.
            typer.echo(json.dumps(build_ambiguous_dry_run_payload(request, e)))
            return
        # ROUTER_NO_MATCH: "no partial signal worth reporting" — same exit-1 shape real
        # dispatch already produces. Reuse the existing handler's JSON, do not hand-duplicate it.
        _emit_routing_error_and_exit(e)
    except ProfileNotFoundError as e:
        profile_not_found_routing(e)
        return
    typer.echo(json.dumps(payload.to_dry_run_dict(payload.alternatives)))
    return
```

This replaces an earlier, unworkable draft of this plan that tried to have the *same*
`except RouterAmbiguityError` clause both special-case `"ROUTER_AMBIGUOUS"` (exit 0, dry-run
payload) and "reuse the existing handler unchanged" for every `RouterAmbiguityError`
(exit 1, error JSON) — impossible as stated, because Python `except` clauses select by exception
**type**, and `ROUTER_AMBIGUOUS`/`ROUTER_NO_MATCH` are the *same* exception type
(`errors.py`), distinguished only by `e.error_code`. The explicit `if e.error_code ==
"ROUTER_AMBIGUOUS": ... else: ...` branch inside that one `except` clause is therefore required,
not optional, and is now the plan's stated mechanism rather than something an implementer must
independently discover.

To avoid duplicating the existing invoke()-path error-JSON construction (the `error_obj = {...}`
literal built inside the current `except RouterAmbiguityError` handler around
`executor.invoke(...)`), extract it into a small shared helper — e.g.
`_emit_routing_error_and_exit(e: RouterAmbiguityError) -> NoReturn` — called from both the
invoke()-path handler and the dry-run-path `else` branch above: one exit-1 JSON shape, built in
one place, with two call sites.

The ambiguous-payload builder itself, `build_ambiguous_dry_run_payload(request_text, err:
RouterAmbiguityError) -> dict[str, object]`, is **colocated in `executor.py` beside
`InvocationPayload.to_dry_run_dict()`** rather than living as a `dispatch.py`-local helper. This
keeps both dry-run shape sources authored next to each other for the next maintainer touching
this surface, rather than splitting them across the CLI-command layer and the invocation
package — a purely-prose "not a competing shape" claim (as the Constitution Check above states)
is honest only when the two builders are visibly adjacent, not merely conventionally similar by
field-name coincidence.

## Generated artifacts

- **`docs/api/cli-commands.md`** — **generated**, by `scripts/docs/build_cli_reference.py`
  (confirmed: this script's docstring states it builds the file "from the live Typer surface"
  via `subprocess.run(["uv", "run", "spec-kitty", *path, "--help"])`; there is no CLI flag to
  override that internal `cmd_runner` default). WP1's new `--dry-run` help text on `dispatch`
  changes this file's `## spec-kitty dispatch` section (confirmed present at line ~1096 in the
  current file). **Do not hand-patch this file.** Regenerate it with the exact command already
  documented in `docs/development/how-to/pr-landing.md` (verified present, not invented for this
  plan):
  ```
  PYTHONPATH=. uv run python scripts/docs/build_cli_reference.py \
    --output docs/api/cli-commands.md \
    --agent-output docs/api/agent-subcommands.md
  ```
  This is `uv run python <script>`, **not** the forbidden bare `uv run spec-kitty <command>`
  pattern this session was told to avoid — the session-level rule is about *this agent's own*
  CLI invocations (to protect a hand-built `.venv` from `uv run`'s auto-resync, per AGENTS.md
  "Other Notes"); the doc-build script's own internal subprocess call to `uv run spec-kitty
  --help` is pre-existing, sanctioned repo tooling that this mission does not change. **Overlap
  note**: PR #3842 (open) also regenerates `docs/api/cli-commands.md`, in the unrelated
  `charter list --json` section (~line 540, confirmed via `gh pr diff 3842`). Since the
  regeneration rewrites the whole file, WP1's implementer should rebase onto the latest
  `main`/`planning_base_branch` tip (picking up PR #3842's regenerated content if it has merged
  by then) *before* running the regeneration command, so this mission's diff to the generated
  file is scoped to the `dispatch` section only, not a stale full-file rewrite that clobbers
  PR #3842's already-landed section.
- **`kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/contracts/cli-do-output.md`** — **NOT
  generated**. Confirmed by inspection: no build-script header, no `<!-- BEGIN GENERATED -->`
  envelope marker (unlike `cli-commands.md`'s hybrid-mode envelope), plain hand-authored prose
  with a "Behavior" / "JSON output" / "Close surface" structure. Edited directly, by hand, in
  WP1 (FR-011) — no regeneration step exists or is needed for this file.
- Everything else touched (`dispatch.py`, `executor.py`, `router.py`, `empty_charter.py`, the
  three test files) is hand-authored source, not generated.

## Contracts: does `dispatch --json`'s output shape move?

**Yes — additively.** Concretely:

- New top-level `alternatives: list[dict[str, str]]` field on every successful `dispatch --json`
  response (real or dry-run) — never absent, never `null`, always a list (possibly `[]`). This
  is the "always a list" contract SC-003/Key-Entities require; the implementation enforces it
  via the type annotation (`alternatives: list[dict[str, str]]`, no `Optional`) plus a direct
  test asserting `[]` (not `None`, not the key being absent) on the single-candidate case (see
  ATDD section, WP2).
- New `"status": "dry_run"` terminal value, only reachable via `--dry-run`; the existing
  `"status": "open"` branch on real dispatch is unchanged — no existing field is removed,
  renamed, or repurposed on the real-dispatch success path.
- New minimal ambiguous-branch shape (`profile_id: null, action: null, router_confidence:
  "ambiguous", alternatives: [...]`), reachable only via `--dry-run` on a request that would
  otherwise raise `ROUTER_AMBIGUOUS` under real dispatch — real dispatch's own
  `ROUTER_AMBIGUOUS` behavior (exit 1, structured error JSON, no Op) is unchanged.
- **No `contract_version`/semver envelope is introduced** (C-003, binding — orchestrator-api's
  separate, larger contract-versioning effort owns that; this plan does not propose one).
- **`RouterDecision`, `InvocationPayload`, `RouterAmbiguityError.candidates` remain internal
  CLI-owned dataclasses/types** — none of them are part of, nor become part of, the
  `spec-kitty-events` / `spec-kitty-tracker` external contract packages. Per charter's
  "External Contract Packages" section, those two packages are true external, non-vendored
  PyPI dependencies owning event envelopes/schemas and tracker abstractions respectively; this
  mission touches neither package's source, dependency pin, or lockfile entry, and nothing in
  this plan implies they are vendored or editable in this repo (C-007/spec.md numbering).

## The gate set

Chosen from the candidate list, grounded in what actually exists in this checkout (not assumed):

| Gate | Applies? | Why / why not |
|---|---|---|
| `ruff check .` (repo-wide lint; also `make lint` → `uv run ruff check src/`, confirmed present in `Makefile`) | **Yes** | Standard for all new/changed Python in this repo (AGENTS.md "Code Style" — zero issues, zero warnings, no blanket suppressions). |
| `mypy --strict src/specify_cli/invocation/ src/specify_cli/cli/commands/dispatch.py src/glossary/chokepoint.py` (targeted; the repo's own `Makefile typecheck` target is scoped to one unrelated file, so this mission scopes its own targeted mypy run to the touched packages) | **Yes** | Charter Code Review Checklist requires "Type annotations present (mypy --strict passes)"; this mission's new `alternatives`/`dry_run()`/`to_dry_run_dict()` surfaces must type-check strictly, including the non-Optional `profile_id`/`action` slots discussed above. |
| `pytest tests/specify_cli/invocation/` | **Yes** | Direct home of `test_router.py`, `test_dispatch.py` (under `cli/`), and the executor/dispatch code under test. |
| `pytest tests/invocation/test_dispatch_recommendation.py` | **Yes** | Named in spec.md Blast Radius as a file this mission extends (verifies the advisory recommendation still populates under `--dry-run`). |
| `pytest tests/glossary/` (or wherever chokepoint tests live — confirmed: `tests/glossary/` exists in this checkout) | **Yes, narrowly** | WP1's FR-003 pins the *existing* `_build_event_context` gate with a new test; run the existing chokepoint suite to confirm no regression, even though `chokepoint.py` itself is not edited. |
| `pytest tests/architectural/test_no_legacy_terminology.py` | **Yes, cheap (~0.1s)** | AGENTS.md: some repo-wide gates (this one) run only in CI's `integration-tests-core-misc` job, not `fast-tests-*`; run it pre-push whenever prose/doc files change — WP1 edits `cli-do-output.md` prose. |
| kernel coverage ≥90% (`--cov=src/kernel`, `module-kernel.yml`) | **No** | This mission touches zero files under `src/kernel/` — confirmed by the file list above; the gate's own workflow only fires on `src/kernel/**` path changes. |
| mission-loader coverage ≥90% (`--cov=src/specify_cli/mission_loader`, `ci-quality.yml` `mission-loader-coverage` job) | **No** | Zero files under `src/specify_cli/mission_loader/` touched — confirmed. |
| commitlint | **Yes** | Applies to every commit message in this repo unconditionally (`commitlint.config.cjs` present at repo root); each of WP1/WP2/WP3's ATDD + implementation commits must pass it. |
| markdown lint (`.markdownlint-cli2.jsonc`) | **Yes, for `cli-do-output.md`** | That file is committed Markdown under the repo's lint scope; `plan.md`/the tracer files are also Markdown under the same scope. `docs/api/cli-commands.md` is regenerated, not hand-formatted, so lint conformance is the generator's responsibility, not this mission's. **The new WP3 `CHANGELOG.md` entry is also in scope**: `CHANGELOG.md` is a repo-root symlink to `docs/changelog/CHANGELOG.md`, hand-edited Markdown, and `.markdownlint-cli2.jsonc`'s `ignores` list carries no exclusion for `docs/changelog/` or `CHANGELOG.md`. |
| architecture/docs consistency (`scripts/docs/check_docs_freshness.py`) | **Yes** | `cli-commands.md` changes; run `PYTHONPATH=. uv run python scripts/docs/check_docs_freshness.py --ci` per the documented pattern before declaring the branch green. **The new WP3 `CHANGELOG.md` entry is also in scope**: `CHANGELOG.md` symlinks to `docs/changelog/CHANGELOG.md`, a page tracked in `docs/development/3-2-page-inventory.yaml` (line 1859) that this same freshness check's page-inventory-completeness and inventory-lockfile-drift sub-checks validate. |
| doctrine schema freshness | **No** | This mission touches no `src/doctrine/` schema or doctrine-pack YAML; nothing to refresh. |
| Contextive glossary | **No** | No new canonical term is introduced — `--dry-run`, `alternatives`, `dry_run` (status value) are code/API surface, not new glossary-tracked domain terminology; C-005 (spec.md) already rules out bulk-edit/occurrence-classification for the same reason. |
| TID251 banned-API (flake8-tidy-imports) | **Yes, respect existing exemption** | `executor.py` already carries a `# noqa: TID251` on its SHA-256 line (L363); WP1's new `dry_run()` method calls `build_charter_context(...)` (same as `invoke()`) but does **not** need its own hash computation, so no new noqa is expected — if one becomes necessary, it must carry an inline rationale per AGENTS.md's no-blanket-suppression rule. |
| Typer JSON error surface | **Yes** | `dispatch.py`'s existing `except RouterAmbiguityError` / `except ProfileNotFoundError` / `except InvocationWriteError` handlers are exactly this gate's subject; WP1's dry-run branch must emit conforming structured JSON on its own error paths (`ROUTER_NO_MATCH`, unknown `--profile`) by reusing the *existing* handlers unchanged (see "Two JSON shapes" section — no new error handler needed for those two cases). |
| `patch()` target validation | **Yes, if new tests use it** | New ATDD tests for WP1-3 may use `unittest.mock.patch`; any such usage must patch at the *call site* (import location), matching the repo's existing test-suite convention — verified against the existing patterns already in `test_router.py`/`test_dispatch.py` rather than introduced fresh. |
| Bandit | **Yes (CI default)**, no new finding expected | No new subprocess/eval/pickle/credential-handling code is introduced; the touched methods are pure read/compute + (on the real path only, unchanged) existing writes. |
| pip-audit | **Yes (CI default)**, no-op for this mission | No dependency added or changed. |
| `uv.lock` freshness | **No** | No dependency added, removed, or version-bumped by this mission — `uv.lock` is untouched. |
| **SonarCloud** | **No, does NOT run on PRs** | Verified in `.github/workflows/ci-quality.yml` (~L3470-3556): the `sonarcloud` job description states "PRs skip Sonar entirely" and gates on `secrets.SONAR_TOKEN` + a nightly/default-branch schedule, not `pull_request`. Do not list it as a PR gate; AGENTS.md's "Sonar Expectations" (complexity ceiling 15, no dup literals ≥3, no empty except blocks) are still followed as code-shaping discipline during implementation, just not CI-enforced on this PR. |

**Actual invocable commands** (not "we'll run the tests"):
```
ruff check .
mypy --strict src/specify_cli/invocation/ src/specify_cli/cli/commands/dispatch.py src/glossary/chokepoint.py
pytest tests/specify_cli/invocation/ tests/invocation/test_dispatch_recommendation.py tests/glossary/ -v
pytest tests/architectural/test_no_legacy_terminology.py
PYTHONPATH=. uv run python scripts/docs/check_docs_freshness.py --ci
```
Parallel/full-suite forms (`PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider`)
are available per AGENTS.md but not required for this scoped mission; targeted paths above are
sufficient and avoid the shared test-venv contention noted below.

## The baseline: pre-existing red, and the shared-venv lock

- `main` carries known-red tests, tracked as **issue #3284** ("main full suite has 23 untracked
  failures and 2 errors after bootstrap prewarm", confirmed OPEN) — cite this issue; do not open
  a new one for pre-existing failures encountered while running the targeted suites above.
- The shared test-venv lock that can time out under concurrent missions is tracked as **issue
  #3283** ("pytest shared test-venv lock times out before editable install completes", confirmed
  OPEN).
- **Per-WP baseline-red protocol** (AGENTS.md's "Test-run baseline-red gotcha", applied
  concretely to this mission): before WP1's first implementation change, each WP's implementer
  runs the WP's targeted test file(s) **on the WP's `planning_base_branch`** (i.e. before that
  WP's own changes land — for WP1 this is `feat/dispatch-dry-run-route-only-3840` at mission
  start; for WP2 it is WP1's final commit; for WP3 it is WP2's final commit) and records the red
  count. After the WP's implementation commit, the same targeted run must show: every
  previously-red test still red or newly green (never a new red outside the WP's own new ATDD
  test, which is expected red-then-green by design), and the new ATDD test transitioning
  RED→GREEN. Only a failure that is red on the WP's branch **and** green on that WP's own
  `planning_base_branch` is attributable to the WP's own change.
- Run targeted paths only when grounding this plan or implementing — never the full suite
  concurrently with another mission's checkout, per the test-contention warning (issue #3283).

## Campsite-clean scope (charter Standing Order #2)

Checked all five touched implementation files (`dispatch.py`, `executor.py`, `router.py`,
`errors.py`, `chokepoint.py`) for `TODO`/`FIXME`/`XXX` markers and obvious duplication in the
functions this mission edits: **none found** (`grep -n "TODO\|FIXME\|XXX"` over all five files
returns nothing). No obvious over-long function or duplicated block sits directly in the
functions WP1-3 touch (`route()` at ~166 lines is the largest, already within the repo's
complexity-15 ceiling per its existing structure, and WP3's restructuring is itself the
functional change to that function, not a preceding cleanup of it).

**Campsite-clean is a no-op for this mission.** This is a stated, honest finding, not an omission
— no debt was invented to fold in where none exists in the touched surfaces.

## ATDD-First obligations (charter C-011 / spec.md C-001)

Each WP's failing-first test is committed as its own commit, BEFORE that WP's implementation
commit. The reviewer verifies RED on the WP's `planning_base_branch` and GREEN on the WP's
final commit — stated explicitly per WP below.

### WP1 (dry-run + payload shape)

Failing-first tests (new, in `tests/specify_cli/invocation/cli/test_dispatch.py` and
`tests/glossary/` or `tests/specify_cli/invocation/`):

1. `test_dry_run_writes_nothing_to_kitty_ops` — snapshot `kitty-ops/` file count and
   `kitty-ops/ops-index.jsonl` line count before and after N (e.g. 3) `spec-kitty dispatch
   "<request>" --dry-run --json` calls against a clean checkout; assert byte-identical state
   (directory listing equal, line count equal) — this is SC-001's exact assertion shape.
2. `test_dry_run_suppresses_glossary_event_write` — with a request whose tokens are
   unrecognized by the glossary index, snapshot the set of files under
   `.kittify/events/glossary/` (by name, treating "directory absent" and "directory present but
   empty" as the same unchanged state — SC-002's explicit requirement) before/after N dry-run
   calls; assert unchanged, while separately asserting the returned JSON's
   `glossary_observations` field is still populated (the in-memory scan still ran).
3. `test_dry_run_payload_shape` — assert the JSON payload has `"status": "dry_run"`, no
   `invocation_id` key, no `close_contract` key, and does have `profile_id`, `action`,
   `router_confidence`.
4. `test_dry_run_ambiguous_returns_dry_run_payload_not_exit_1` — construct a request that would
   raise `ROUTER_AMBIGUOUS` under real dispatch; assert `--dry-run` exits 0 with
   `profile_id: null, action: null, router_confidence: "ambiguous"` and `alternatives`
   populated with every tied candidate.
5. `test_dry_run_no_match_still_raises` / `test_dry_run_unknown_profile_still_raises` — assert
   `ROUTER_NO_MATCH` and an unknown `--profile` both still exit 1 with the same structured error
   JSON as real dispatch, unchanged by `--dry-run`.
6. `test_dry_run_does_not_submit_to_saas_propagator` — construct the executor with a mock/spy
   `InvocationSaaSPropagator` (patched at the call site — `dispatch.py`'s `_build_executor`
   constructs it — per the plan's own `patch()`-target-validation gate) and assert `submit` is
   never called across N (e.g. 3) `--dry-run` invocations, mirroring tests 1-2's
   kitty-ops/glossary-directory assertions for the third named suppressed-write surface (see
   Silent-success framing's `dry_run()` "no write happened" claim below).

**RED on `planning_base_branch`** (no `--dry-run` flag exists at all — Typer rejects the
unrecognized option) → **GREEN on WP1's final commit**.

### WP2 (`alternatives`)

Failing-first tests (new, in `test_router.py` and `test_dispatch.py`):

1. `test_alternatives_empty_on_single_candidate` — a request matching exactly one profile;
   assert `alternatives == []` (an explicit empty list, not `None`, not an absent key) on both
   dry-run and real dispatch.
2. `test_alternatives_empty_on_explicit_profile_hint` — `--profile <id>` bypasses the router
   entirely; assert `router_confidence == "exact"` and `alternatives == []`.
3. `test_alternatives_nonempty_on_two_candidate_tiebreak` — a request matching two profiles
   (one canonical-verb, one domain-keyword, so `routing_priority` decides today); assert
   `alternatives` is non-empty and its one entry carries the losing candidate's `profile_id`,
   `action`, `confidence`, and `match_reason` — matching User Story 2's own Independent Test.
4. `test_router_ambiguous_candidates_carry_confidence_key` — trigger the existing
   post-tiebreaker `ROUTER_AMBIGUOUS` raise (two candidates tied at the same top priority);
   assert every dict in `err.candidates` (and the resulting dry-run `alternatives`) carries a
   `confidence` key (FR-009).

**RED on WP1's final commit** (the `alternatives` field/key does not exist yet — `KeyError` or
`AttributeError` on the assertion) → **GREEN on WP2's final commit**. Also re-run (unmodified)
`test_router_priority_tiebreaker_selects_higher_priority` and confirm it still passes — spec.md
explicitly requires this test to keep passing unmodified through WP2.

### WP3 (SK-08 rerank)

Failing-first tests (new, in `test_router.py`), built from the ledger's documented probe
requests (SPEC-KITTY-LEDGER.md:2727, SK-08):

1. `test_canonical_verb_beats_domain_keyword_regardless_of_priority` (SC-004 / AC-1) — a request
   whose tokens match a canonical verb for profile A and a domain keyword for a
   higher-`routing_priority` profile B; assert the winner is A with
   `confidence: "canonical_verb"`, and B appears in `alternatives` with
   `confidence: "domain_keyword"`.
2. `test_lone_domain_keyword_candidate_is_ambiguous` (SC-005 / AC-2) — a request matching no
   canonical verb for any profile but exactly one profile's domain keyword; assert
   `RouterAmbiguityError("ROUTER_AMBIGUOUS")` is raised (not an auto-select), and (via a
   dispatch-level test) that no new `kitty-ops/` file appears.
3. `test_lone_domain_keyword_with_explicit_profile_still_works` (AC-3) — same request as above,
   but with `--profile <id>` supplied; assert routing succeeds exactly as before (explicit-hint
   path is untouched by WP3).
4. `test_two_plus_domain_keyword_candidates_still_ambiguous_regardless_of_priority_spread`
   (SC-006 / AC-4) — zero verb-tier candidates, two keyword-tier candidates at different
   `routing_priority` values (e.g. 80 and 10); assert `ROUTER_AMBIGUOUS` is still raised
   (today's code would auto-select the priority-80 candidate — this is the exact regression
   this test pins).
5. `test_new_ambiguous_raise_sites_carry_confidence_key` — for both new raise sites (AC-2's
   lone-candidate case and AC-4's 2+-keyword-candidates case), assert `err.candidates` entries
   carry the `confidence` key — WP3 must not reintroduce the pre-FR-009 shape on its own new
   raise sites (FR-009's explicit extended obligation).

**RED on WP2's final commit** (today's code auto-selects the domain-keyword candidate in case 1,
auto-selects the lone candidate in case 2, and lets `routing_priority` decide in case 4 — all
three assertions fail against current behavior) → **GREEN on WP3's final commit**. Also re-run
(unmodified) `test_router_priority_tiebreaker_selects_higher_priority` (canonical-verb-vs-
canonical-verb intra-tier) and confirm it still passes unmodified — FR-006 requires this
explicitly.

**Accepted mid-mission routing-consistency risk (spec.md Clarifications #5, restated here since
it becomes operationally relevant at this WP):** `route()` is pure and stateless, re-evaluated on
every call; a spec-kitty mission whose WP subagents dispatch across the span of time during which
WP3 merges to `main` could see two auto-routed (no `--profile`) `dispatch` calls for similar
request text resolve to different profiles before and after the rerank lands. This is accepted as
inherent to any bug fix to `router.py`'s selection logic — not novel to this mission — and is not
mitigated further here (no mid-mission routing-version pin is introduced); this was already
adjudicated by the operator, not an open question for WP3's implementer to raise. A caller
wanting a stable profile across a mission's lifetime should pass an explicit `--profile` hint,
which this fix does not affect.

## `__all__` (charter C-007)

**Does not bind this mission**, matching spec.md's own C-006 constraint explicitly (not silently
dropped): C-007 is binding on `src/charter/` and `src/kernel/` only. Every file this mission
touches (`specify_cli.cli.commands.dispatch`, `specify_cli.invocation.*`, `glossary.chokepoint`
verification-only) sits outside that seam. No `__all__` addition or update is expected in this
mission's diff.

## Write scopes: are WP1/WP2/WP3 disjoint?

**No — WP2 and WP3 deliberately, spec-acknowledged overlap** (spec.md C-002). Both edit the
same two statements inside `router.py`'s `route()`:

- the `if len(candidates) == 1:` single-candidate return (currently L343-350), and
- the `routing_priority` tiebreaker block (currently L352-370).

This is **not an oversight** — it is why spec.md's operator decision explicitly frames WP3 as
"own commit, auditable and cherry-pickable," but **not** guaranteed to be a conflict-free
independent `git revert <wp3-sha>` target: reverting WP3 alone may require reverting or
hand-resolving WP2's `alternatives=` edits to those same lines first. The sequencing mitigation
is ordering, not disjointness: **WP3 lands strictly after WP2's commit**, so WP3's diff is
computed against the post-WP2 state of those lines (which already carries `alternatives=`
population), not a parallel/concurrent edit to the pre-WP2 state. WP1 and WP2 are themselves
close but distinguishable: WP1 adds the `dry_run()` method and payload shape (executor.py,
dispatch.py) without touching `route()`'s selection logic at all; WP2 is the first to touch
`route()`'s three success-return sites (adding `alternatives=`, not changing selection).

**Cross-mission overlap — PR #3842** (open, confirmed via `gh pr view 3842 --json files`):
touches `src/charter/activation/evidence/orchestrator.py`,
`src/specify_cli/cli/commands/_command_surface_doctor.py`,
`src/specify_cli/cli/commands/charter/{list_cmd,resynthesize,status,synthesize}.py`,
`src/specify_cli/core/agent_config.py`, `src/specify_cli/git/protection_policy.py`, and their
test files. **None of these source files overlap this mission's touched files** — confirmed.
**One narrow, mechanical exception**: PR #3842 also regenerates `docs/api/cli-commands.md`
(confirmed via `gh pr diff 3842`), in the `charter list --json` section (~line 540) — a
different region of the same generated file this mission's WP1 also regenerates (`spec-kitty
dispatch` section, ~line 1096). This is a generated-file regeneration overlap, not a source-code
write-scope overlap; the mitigation is the rebase-before-regenerate step already stated under
"Generated artifacts" above, not a change to WP sequencing.

## Silent-success framing (dominant failure mode per SPEC-KITTY-LEDGER.md)

For each new/changed code path, what happens when it cannot do its job:

- **`dry_run()`'s "no write happened" claim** — this is not a runtime check that could
  silently fail; it is structural. `dry_run()` never calls `self._writer.write_started(...)`,
  never calls `self._writer.write_glossary_observation(...)`, never calls
  `self._propagator.submit(...)`, and never mints a truthy `invocation_id`. There is no
  "what if `write_started` would have failed" question on the dry-run path, because dry-run
  never reaches that call at all — it is moot by construction, not by a runtime guard that
  could be bypassed or could silently no-op. This is the explicit design rationale for the
  sibling-method approach over a boolean flag threaded through `invoke()` (see Summary).
- **`alternatives` empty list vs. `None`** — never `None`. Enforced by: (a) the type annotation
  `alternatives: list[dict[str, str]]` (no `Optional`, no default of `None`) on the frozen
  `RouterDecision` dataclass — a caller passing `None` fails at construction under
  `mypy --strict`, not silently at serialization; (b) all four `RouterDecision(...)` /
  `InvocationPayload(...)` construction sites listed above pass a list literal, never a
  conditional that could resolve to `None`; (c) a direct test
  (`test_alternatives_empty_on_single_candidate`, WP2 ATDD) asserts `== []`, not
  `is None or == []` — a regression to `None` or an absent key fails this test, not just a type
  checker that could be suppressed; (d) `alternatives` is added only to the ephemeral
  `RouterDecision`/`InvocationPayload` types — `OpStartedEvent` (`record.py`), the type actually
  persisted to `kitty-ops/*.jsonl`, is untouched by this mission and has no `alternatives` slot;
  `alternatives` is not, and must not become, part of the persisted Op-record schema.
- **`RouterDecision.alternatives` population when `route()` cannot determine confidence tiers
  cleanly (WP3's restructuring)** — WP3's new raise sites (lone-candidate, 2+-keyword-candidates)
  are `RouterAmbiguityError` raises, not silent auto-selects; per FR-009's extended obligation,
  every candidate dict on these new raise sites carries the `confidence` key so a downstream
  `alternatives` built from `err.candidates` never silently drops that field. The ATDD test
  `test_new_ambiguous_raise_sites_carry_confidence_key` pins this directly, not via a docstring
  claim.
- **Dry-run's glossary scan when `_load_index()` or the classifier raises** — unchanged from
  today: `GlossaryChokepoint.run()` already wraps `_run_inner()` in a try/except that returns an
  error-bundle (`error_msg` populated, all collection fields empty) rather than propagating; this
  applies identically whether `dry_run()` or `invoke()` calls `chokepoint.run()`, so dry-run
  inherits the existing non-silent-but-non-fatal behavior without needing a new guard.
- **The empty-charter fallback under dry-run (FR-010)** — `resolve_generic_fallback()` is
  already read-only and unconditionally returns either a `RouterDecision` or `None`; `dry_run()`
  calls it exactly as `invoke()` does, so `empty_charter_fallback: true` and the generic-agent
  routing signal surface identically. The one console-only side-channel
  (`_render_empty_charter_warning`) stays a rich-console concern outside the JSON payload and is
  unaffected either way — not a silent-success gap, since it was never part of the JSON contract.

### Downstream/external consumer impact (WP3)

WP3 changes what auto-routed (no `--profile`) `dispatch` calls select or reject. Every downstream
project that has run `spec-kitty init` / `spec-kitty upgrade` and picks up a release containing
this mission's changes relies on unhinted `dispatch` calls as its default pattern — every
spec-kitty-managed project's own `CLAUDE.md` "Skill Routing" section instructs agents to run
`spec-kitty dispatch "<request verbatim>"` for ad-hoc requests with no `--profile` — including
`team-kitty-missions`, `muster-missions`, and any other spec-kitty consumer repo. After WP3 lands,
some previously-succeeding auto-routed calls that today auto-select a lone/weak domain-keyword
candidate will instead raise `ROUTER_AMBIGUOUS` (exit 1) rather than silently opening an Op under
a possibly-wrong profile. This is an **intentional, user-visible behavior change** on the CLI's
most commonly invoked ad-hoc entry point, not an incidental side effect of the selection-logic
fix. **WP3's implementation commit must include a `CHANGELOG.md` entry** stating explicitly that
some previously-successful no-`--profile` `dispatch` calls will now exit 1 with
`ROUTER_AMBIGUOUS` instead of auto-selecting, so downstream consumers upgrading their
`spec-kitty` CLI pin are not surprised by the change.

## PR shape

**One PR for the whole mission.** Blast Radius names 5 implementation files (one,
`chokepoint.py`, verification-only — no diff expected there), 1 generated doc regeneration, 1
hand-edited contract doc, 1 `CHANGELOG.md` entry (WP3, per "Downstream/external consumer impact"
above), and 3 test files — small enough to review in a single sitting, and the
WP1→WP2→WP3 commit sequence (each with its own ATDD-then-implementation commit pair) keeps the
diff legible per-commit even though it lands as one PR. This also matches the charter's default
("one PR for the whole mission by default" per `sk-implement` doctrine) and spec.md's own framing
of WP3 as "its own commit" rather than "its own PR." No per-WP PR split is recommended.

## Project Structure

### Documentation (this mission)

```
kitty-specs/dispatch-dry-run-route-only-01M1HKV2/
├── spec.md                      # already committed (input to this plan)
├── plan.md                      # this file
├── tracer-tooling-friction.md   # seeded this phase, appended during implementation
├── tracer-approach.md           # seeded this phase
├── tracer-design-decisions.md   # seeded this phase
└── tasks.md                     # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

No `research.md`/`data-model.md`/`quickstart.md`/`contracts/` subdirectory is warranted: this is
a small, well-bounded CLI-surface mission with no new data model, no new external contract, and
no setup quickstart distinct from "run `spec-kitty dispatch --dry-run`" (already fully specified
in spec.md's User Scenarios).

### Source Code (repository root)

```
src/
├── specify_cli/
│   ├── cli/commands/dispatch.py          # WP1: --dry-run flag, dry-run branch
│   └── invocation/
│       ├── executor.py                    # WP1: dry_run() method, to_dry_run_dict(), build_ambiguous_dry_run_payload() helper; WP2: alternatives slot
│       ├── router.py                       # WP2: RouterDecision.alternatives, 3 construction sites; WP3: rerank
│       ├── empty_charter.py                # WP2: 4th alternatives=[] construction site
│       └── errors.py                       # unchanged (RouterAmbiguityError shape itself doesn't change)
└── glossary/
    └── chokepoint.py                       # unchanged — verification-only (existing gate already correct)

tests/
├── specify_cli/invocation/
│   ├── test_router.py                      # WP2 + WP3 ATDD
│   └── cli/test_dispatch.py                # WP1 ATDD
├── invocation/test_dispatch_recommendation.py  # WP1: dry-run recommendation-populates check
└── glossary/                               # WP1: SC-002 glossary-event-suppression pin

kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/contracts/cli-do-output.md  # WP1: FR-011
docs/api/cli-commands.md                    # regenerated after WP1 (mechanical, not hand-edited)
CHANGELOG.md                                # WP3: new entry documenting the auto-route behavior change
```

**Structure Decision**: Single project (this repository's existing `src/specify_cli/` +
`src/glossary/` layout). No new top-level directory, no new package. This mirrors the existing
`invocation/` package structure exactly — `dry_run()` sits beside `invoke()` and
`complete_invocation()` on the same `ProfileInvocationExecutor` class, following the repo's
existing pattern of one execution-primitive class per concern rather than introducing a parallel
"dry-run executor" type.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

No violations found — table intentionally left empty.

## Parallel Work Analysis

*Include this section if multiple developers/agents will implement this mission*

This mission is **not** parallelizable across WPs — WP2 and WP3 share touch points inside
`route()` (see "Write scopes" above) and WP3 is defined, per operator decision, as landing after
WP1 and WP2. A single implementer (or a single lane) works WP1 → WP2 → WP3 sequentially, each
as its own ATDD-commit + implementation-commit pair.

### Dependency Graph

```
WP1 (dry-run + payload shape) → WP2 (alternatives, both paths) → WP3 (SK-08 rerank)
```

No wave-parallel structure — strictly sequential, by spec.md Clarifications #1 and the C-002
shared-touch-point overlap between WP2 and WP3.

### Work Distribution

- **Sequential work**: all three WPs, in order — see Dependency Graph above.
- **Parallel streams**: none. A single lane/implementer owns all three WPs to avoid the
  WP2/WP3 `route()` overlap turning into a merge conflict between concurrent lanes.
- **Agent assignments**: one implementer for the full WP1→WP2→WP3 chain; a separate reviewer
  role per charter Standing Order #8 (mission hygiene — reviewer and implementer are distinct
  roles) reviews each WP's diff before the next WP starts, or reviews the whole chain once at
  the end, at the operator's discretion — either satisfies the charter, since this is a single
  PR, not per-WP PRs.

### Coordination Points

- **Sync schedule**: N/A — sequential single-lane work, no concurrent streams to sync.
- **Integration tests**: WP1's ATDD tests must still pass after WP2/WP3 land (WP2/WP3 do not
  remove or narrow WP1's dry-run-writes-nothing guarantee); WP2's `alternatives` tests must
  still pass after WP3 lands (WP3 changes *which* candidates end up in `alternatives`'
  contents on the SK-08 reproduction cases, but not the field's presence/shape contract). The
  three test files named in Blast Radius are the integration surface — no separate
  integration-test file is introduced.
