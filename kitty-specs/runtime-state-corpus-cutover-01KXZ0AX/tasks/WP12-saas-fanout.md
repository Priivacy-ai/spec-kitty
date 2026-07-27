---
work_package_id: WP12
title: SaaS fan-out of the resolved binding
dependencies:
- WP10
requirement_refs:
- FR-015
planning_base_branch: feat/runtime-state-corpus-cutover
merge_target_branch: feat/runtime-state-corpus-cutover
branch_strategy: Planning artifacts for this mission were generated on feat/runtime-state-corpus-cutover. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/runtime-state-corpus-cutover unless the human explicitly redirects the landing branch.
subtasks:
- T047
- T048
- T049
- T050
agent: "claude"
shell_pid: "703549"
shell_pid_created_at: "1784577989.12"
history:
- timestamp: '2026-07-20T08:39:02Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/status/
create_intent:
- tests/specify_cli/status/test_saas_resolved_binding_fanout.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- tests/specify_cli/status/test_saas_resolved_binding_fanout.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

**Before touching any file, load your governing profile:**

```bash
spec-kitty charter context --action implement --profile python-pedro
```

You are **python-pedro** — a Python-specialist implementer. Your standing orders for this WP:

- **mypy `--strict` is the crux.** This WP widens a load-bearing type surface (`actor: str → str | dict`)
  across three signatures and two `from_dict` decoders. Every touched signature, every consumer that
  reads `.actor`, and every `str(...)` coercion must type-check clean under strict mode. **No new
  `# type: ignore`, no `# noqa`, no per-file ignore.** If mypy complains, fix the type flow — do not
  silence it.
- **ATDD-first.** Write the round-trip and fan-out tests in the owned test file *before* (or alongside)
  the production widening. The dict-actor round-trip test must genuinely write and re-read JSONL.
- **Zero shared-package change on the preferred path.** `spec_kitty_events` 6.1.0
  `StatusTransitionPayload.actor` already accepts `Union[str, Dict]`. Do **not** edit, vendor, or bump
  `spec_kitty_events`. Consume it only via public imports.
- **Never block on the external release.** The version-gated event lands locally now.

## ⚠️ OPERATOR DECISION (Jeroen, 2026-07-20) — `WPResolvedBindingChanged` is FIRST-CLASS, not a fallback

This **overrides** the original "fallback only / zero shared-package change" framing below. The operator
wants the resolved-binding event **explicitly present in `spec_kitty_events`** as a genuine spec-kitty ↔
spec-kitty-saas **bridge**, not merely the actor-on-transition enrichment. So this WP delivers **BOTH**:

1. **Actor enrichment (keep):** enrich the structured `actor` (`{role, profile, tool, model}`) on the
   claim/review `StatusEvent` + `_saas_fan_out` (T047/T048) — the SaaS gets the binding on a transition it
   already consumes, even before the events package ships the new type.
2. **`WPResolvedBindingChanged` as a first-class emitted event (T049 — now REQUIRED, not optional):**
   emit a purpose-built `WPResolvedBindingChanged` from `emit_inner_state_changed` (which has no fan-out
   today), carrying the resolved binding + `{wp_id, mission_slug, feature_slug}`, **local-first +
   version-gated** exactly like the genesis-lane gate (`_EVENTS_SUPPORTS_GENESIS`, `emit.py:88`) →
   define `_EVENTS_SUPPORTS_RESOLVED_BINDING = hasattr(spec_kitty_events, "WPResolvedBindingChanged")`.
   When the package lacks the type, skip the fan-out (logged) — local persistence unaffected. When it
   ships the type (see below), the gate activates automatically. Do **not** vendor or hand-define the
   shared type locally; consume it only via `spec_kitty_events` public import behind the gate.

**The `spec_kitty_events` package change itself is a SEPARATE cross-repo deliverable** (tracked
independently — it needs the events repo + a `6.2.0` release + a pin bump `>=6.2.0`). WP12 does NOT block
on it: the version-gate lets spec-kitty land now and light up when the release ships. So WP12's bar is:
actor enrichment works; `WPResolvedBindingChanged` is wired + version-gated + tested (present-and-absent
package paths); the round-trip + fan-out tests pass. The pin bump + gate-on happens after the events
release lands (out of this WP's merge unit).

## Objective

Deliver the **resolved binding** (`{role, profile, tool, model}`) to the SaaS consumer across the
package boundary — **IC-09** of the mission (FR-015). The consumer is already aware; the delivery vehicle
is the **structured `actor`** on the claim/review `StatusEvent` and its existing `_saas_fan_out`.

The preferred path requires **zero shared-package change** — but the *local* emit path is `str`-typed
end-to-end, so it cannot carry a dict actor today. This WP's real work is the **local type-surface
widening** that lets a dict actor flow from `build_status_event` → `StatusEvent` → JSONL → reduce →
`_saas_fan_out` without being flattened to a string. A version-gated `WPResolvedBindingChanged` fallback
is scaffolded (local-first) so an off-transition binding change can fan out once the package ships.

**In one line:** widen `actor` to `str | dict`, guard the `str(...)` round-trip coercions, enrich the
claim/review transition + fan-out, and scaffold the version-gated fallback — with mypy-strict clean.

## Context & grounding

Read before editing:

- **plan.md → IC-09** ("SaaS fan-out of the resolved binding"): the **LOCAL PLUMBING REQUIRED**
  adversarial finding. FR-015 is *"zero **shared-package** change, non-trivial **local** type-surface
  change"* — size accordingly. The local emit path is `str`-typed end-to-end; widening it is bigger than
  "pass the dict through".
- **spec.md → FR-015** and **US6**: SaaS rides the existing structured `actor` on the claim transition;
  also emit the binding as an annotation (IC-08 owns that half) for latest-wins reduction. The fallback
  off-axis `WPResolvedBindingChanged` event stays version-gated.
- **spec.md → Out-of-Scope "Escalating to `spec_kitty_events`"**: no shared-package change on the
  preferred path; the new shared event is a version-gated fallback only, coordinated with the SaaS team.
- **research.md → D-11** (SaaS delivery rides the existing structured actor; no shared-package change on
  the preferred path; fallback is local-first + version-gated) and **D-08** (`InnerStateChanged` stays
  local; `emit_inner_state_changed` has **no** fan-out today — the fallback *adds* one).
- **contracts/resolved-binding.md → "SaaS fan-out (IC-09)"**: the preferred/fallback split, defensive
  dict-actor feature-detection, and the acceptance bullets (claim fan-out payload carries the resolved
  `{role, profile, tool, model}`; older `spec_kitty_events` → new-event fan-out skipped-and-logged, local
  persistence unaffected).

**Verified code grounding (the str-typed corruption risk):**

| Surface | Location | Today | Risk |
|---------|----------|-------|------|
| `StatusEvent.actor` | `status/models.py:258` | `actor: str` | str-typed; mypy rejects a dict; downstream string ops assume str |
| `StatusEvent.to_dict` | `status/models.py:278` | `"actor": self.actor` | passes through (OK) but the field is str-typed |
| `StatusEvent.from_dict` | `status/models.py:312` | `actor=data["actor"]` | pass-through, but str-typed — must accept dict explicitly |
| `InnerStateChanged.from_dict` | `status/models.py:506` | `actor=str(data["actor"])` | **CORRUPTION TRAP** — `str(...)` flattens a dict on round-trip |
| `ReviewOverride.from_dict` | `status/models.py:360` | `actor=str(data["actor"])` | same `str(...)` coercion class — audit before assuming safe |
| `build_status_event` | `status/emit.py:146` | `actor: str` | str-typed producer signature |
| `emit_status_transition` | `status/emit.py:512` | `actor: str \| None` | str-typed orchestrator signature |
| `_saas_fan_out` | `status/emit.py:954-1008` | `fire_saas_fanout(actor=event.actor, …)` | the delivery seam; `fire_saas_fanout(**kwargs: Any)` is permissive |
| genesis version gate | `status/emit.py:85-94` | `_EVENTS_SUPPORTS_GENESIS = hasattr/"genesis" in Lane` | the pattern to mirror for the fallback gate |
| `emit_inner_state_changed` | `status/emit.py:888-951` | persists + materializes, **no fan-out** | the fallback *adds* a version-gated fan-out here |
| reducer consumers | `status/reducer.py:89, :306` | `"actor": event.actor` / `_runtime_only_wp_state(annotation.actor)` | pass-through consumers — confirm no string op corrupts a dict |

**The load-bearing trap:** the `str(data["actor"])` coercion silently flattens a dict actor to
`"{'role': ...}"` on JSONL round-trip. A dict that survives `to_dict` but is `str()`-coerced on
`from_dict` is a *silent* corruption — no exception, wrong data. The round-trip test (T050) exists to
make this trap non-vacuously red before the guard lands.

## Subtasks

### T047 — Widen the local `actor` type surface to `str | dict`

Widen `actor` to `str | dict[str, Any]` (import-consistent alias/`JSONDict` if the module has one) across:

- `StatusEvent.actor` (`status/models.py:258`) — the dataclass field.
- `build_status_event(actor: ...)` (`status/emit.py:146`) — the pure producer.
- `emit_status_transition(actor: ...)` (`status/emit.py:512`) — the orchestrator entry point
  (keep `| None` where present).

**Guard the round-trip coercions** so a dict actor survives a JSONL write→read cycle uncorrupted:

- `StatusEvent.from_dict` (`:312`) — keep it accepting a dict actor unchanged (it is pass-through today;
  ensure the widened type flows and no incidental `str(...)` is introduced).
- `InnerStateChanged.from_dict` (`:506`) — the `str(data["actor"])` **must not** flatten a dict; branch
  so a dict passes through and only a scalar is `str()`-coerced (or drop the coercion if the field is
  now typed `str | dict`).
- `ReviewOverride.from_dict` (`:360`) — audit: if the resolved-binding path never routes a dict through
  `ReviewOverride.actor`, document that and leave it; if it can, apply the same guard. Do not assume —
  verify against the emit paths.

**Audit + fix every reducer/consumer doing string ops on `actor`** (mypy-strict will surface most):
`reducer.py:89` (`"actor": event.actor`) and `reducer.py:306` (`_runtime_only_wp_state(annotation.actor)`)
are pass-through today — confirm they stay pass-through under the widened type and add explicit handling
if a `str`-only op (e.g. `.strip()`, `.lower()`, equality-with-string, f-string identity) exists anywhere
that would misbehave on a dict. Grep the tree for `.actor` string operations and reconcile each.

**Deliverable:** the widened signatures type-check clean under `mypy --strict`, with no new suppressions.

### T048 — Enrich the structured `actor` on the claim/review transition + existing `_saas_fan_out`

On the **claim** and **review-claim** `StatusEvent` (the transitions IC-08 records the resolved binding
on), populate the structured `actor` as `{role, profile, tool, model}` sourced from the resolved binding
(never a frontmatter re-read — C-007). This is the **preferred, zero-shared-package-change** path:
`spec_kitty_events` 6.1.0 `StatusTransitionPayload.actor` already accepts `Union[str, Dict]`.

- Thread the dict actor through `emit_status_transition` → `build_status_event` → `StatusEvent` so it
  reaches `_saas_fan_out` (`emit.py:954-1008`) and flows out via `fire_saas_fanout(actor=event.actor, …)`.
- **Feature-detect the dict actor defensively** before sending: a plain-string actor (the common case)
  must continue to fan out exactly as today; only a resolved-binding dict carries the enriched shape.
  Do not fabricate a dict when the binding is absent — a bare string stays a bare string.
- Do **not** inflate `emit_status_transition` (it carries a tracked `# NOSONAR`; do not let this push its
  size/complexity up) — thread the enrichment via a small helper, not inline branching.

**Deliverable:** a claim transition whose actor is a resolved-binding dict fans out with the
`{role, profile, tool, model}` payload intact; a string-actor transition is unchanged.

### T049 — Scaffold the version-gated fallback (`WPResolvedBindingChanged` + `emit_inner_state_changed` fan-out)

For an **off-transition** binding change (e.g. a mid-WP model swap with no lane change), scaffold a
`WPResolvedBindingChanged` shared event and add a fan-out to `emit_inner_state_changed` (`emit.py:888-951`),
which has **none** today.

- **Version-gate it exactly like the genesis-lane gate** (`emit.py:85-94`): at import time compute
  `_EVENTS_SUPPORTS_RESOLVED_BINDING = hasattr(spec_kitty_events, "WPResolvedBindingChanged")` inside a
  `try/except (ImportError, AttributeError)`.
- When the installed `spec_kitty_events` lacks the event, the fan-out is a **logged, intentional skip**
  (mirror the genesis skip log at `emit.py:979-986`) — **never** a swallowed `ValidationError`.
- **Local persistence is unaffected in every case**: `emit_inner_state_changed` still
  `annotate → append → materialize`; the fan-out is best-effort and additive. Adding the fan-out must not
  change the annotation's persistence or the snapshot.

**Deliverable:** the fallback fan-out is present, gated, and logs the skip on an older package; it lands
locally now and enables automatically when the package ships (never blocks on the external release).

### T050 — Tests (ATDD) in the owned file

Author `tests/specify_cli/status/test_saas_resolved_binding_fanout.py` covering:

1. **Dict actor round-trips JSONL uncorrupted** — build a `StatusEvent` (and the annotation path) with a
   `{role, profile, tool, model}` actor, write it to a real `status.events.jsonl`, read it back via
   `from_dict`, and assert the actor is still a `dict` equal to the original — **not** the `str(...)`
   flattened form. This is the non-vacuous proof against the `models.py:506` corruption trap.
2. **Claim fan-out payload carries the resolved binding** — drive a claim transition with a resolved
   binding and assert the captured `_saas_fan_out` / `fire_saas_fanout` payload carries the resolved
   `{role, profile, tool, model}` (capture via the registered handler seam, not a network call).
3. **String actor is unchanged** — a claim with a plain-string actor fans out exactly as before (guards
   the defensive feature-detection; no dict fabricated).
4. **Older `spec_kitty_events` → fallback fan-out skipped + logged; local persistence unaffected** —
   monkeypatch `_EVENTS_SUPPORTS_RESOLVED_BINDING` (or the `hasattr` seam) to `False`, emit an inner-state
   change, assert the new-event fan-out is skipped, the skip is logged, and the annotation is still
   persisted and materialized identically (byte/slot parity).

**Deliverable:** all four tests pass via the per-file `uv run` invocation below; test 1 fails if the
`str(...)` guard is reverted (non-vacuous).

## Branch Strategy

- **Base / merge target:** `feat/runtime-state-corpus-cutover` (both). Planning artifacts were generated
  on this branch; completed changes merge back into it. No PR to origin/main from this WP.
- **Parallel with WP11:** WP12 and WP11 both depend on **WP10** and run in parallel — their owned files
  are **disjoint** (WP12 owns `tests/specify_cli/status/test_saas_resolved_binding_fanout.py`; WP11 owns
  its own surface). Do not touch WP11's files.
- **Sequential shared-module edits:** the production widening lands in `status/models.py` and
  `status/emit.py`, which were **owned by WP09 and WP04** respectively and **ran earlier** in the
  sequence — see *Risks & out-of-map edits*. These are documented, in-sequence edits, not a race with a
  concurrent owner.

## Test strategy

Run the status suite **per-file** (never the whole `tests/architectural/` dir — it hangs), using
`uv run` so a sibling checkout does not yield a false green:

```bash
# The owned test (author + drive it here):
uv run --extra test python -m pytest -p no:cacheprovider \
  tests/specify_cli/status/test_saas_resolved_binding_fanout.py

# Regression sweep for the widened type surface (round-trip / reducer / emit):
uv run --extra test python -m pytest -p no:cacheprovider \
  tests/specify_cli/status/test_models.py \
  tests/specify_cli/status/test_emit.py \
  tests/specify_cli/status/test_reducer.py

# Type + lint gate (the crux for this WP):
uv run mypy src/specify_cli/status/models.py src/specify_cli/status/emit.py
uv run ruff check src/specify_cli/status/ tests/specify_cli/status/
```

Adjust file names to the actual status-suite layout; the point is **per-file + `uv run`**, and that the
mypy-strict pass over `models.py`/`emit.py` is treated as a first-class gate.

## Definition of Done

- **FR-015 satisfied**: the resolved binding is delivered to SaaS via the structured `actor` on the
  claim/review transition + existing `_saas_fan_out`, with **zero shared-package change on the preferred
  path** (`spec_kitty_events` 6.1.0 already accepts `Union[str, Dict]`).
- **A dict actor round-trips JSONL uncorrupted** — the `str(...)` coercion traps (`models.py:506`, and
  `:360` if in-path) are guarded; test 1 proves it non-vacuously.
- **Preferred path is truly shared-package-free** — no edit/bump/vendor of `spec_kitty_events`; the dict
  actor is feature-detected defensively; a string actor is unchanged.
- **Fallback is version-gated + local-first** — `WPResolvedBindingChanged` fan-out in
  `emit_inner_state_changed` is gated on `hasattr(spec_kitty_events, "WPResolvedBindingChanged")`, logs
  the skip on an older package, and never alters local persistence/materialization.
- **`ruff` + `mypy --strict` clean** over the widened surface (`models.py`, `emit.py`, reducer consumers,
  the test) — **no** new `# noqa` / `# type: ignore` / per-file ignore. The type-surface widening is the
  crux; a suppression to pass mypy is a DoD failure.
- **Status suite green** (per-file) for the touched modules; no regression in the string-actor path.

## Risks & out-of-map edits

**This WP owns only its test file** (`tests/specify_cli/status/test_saas_resolved_binding_fanout.py`).
Its production edits are the `actor` type-surface widening in two **shared** status modules. These are
**OUT-OF-MAP (sequential — the owners ran earlier)** and are documented here explicitly:

- `src/specify_cli/status/models.py` — **owned by WP09** (ran earlier). Edits: widen `StatusEvent.actor`
  (`:258`), guard the `from_dict` `str(data["actor"])` coercion (`InnerStateChanged.from_dict:506`;
  audit `ReviewOverride.from_dict:360`; keep `StatusEvent.from_dict:312` dict-accepting).
- `src/specify_cli/status/emit.py` — **owned by WP04** (ran earlier). Edits: widen
  `build_status_event` (`:146`) / `emit_status_transition` (`:512`), enrich `_saas_fan_out`
  (`:954-1008`), and add the version-gated fallback fan-out in `emit_inner_state_changed` (`:888-951`).

Because WP09/WP04 ran earlier in the sequence, these edits are **in-sequence** — not a concurrent-owner
race. Keep them **minimal and surgical**: widen types, guard coercions, thread the enrichment via a
helper. Do **not** refactor unrelated logic in these god-modules (`emit.py` is 1008 lines;
`emit_status_transition` carries a tracked `# NOSONAR` — do not inflate it).

**The silent-corruption trap** (`str(data["actor"])` flattening a dict) is the single highest risk: it
raises no exception, so only the real round-trip test catches it. Treat test 1 as load-bearing.

**Reducer/consumer audit risk:** a `.actor` string op hiding in a consumer (`reducer.py:89, :306`,
lane_reader, validate, adapters) will only fail on a dict actor at runtime, not necessarily under mypy if
loosely typed. Grep every `.actor` use and reconcile.

## Reviewer guidance

Verify, specifically:

1. **The dict actor genuinely round-trips** — check test 1 does a *real* JSONL write + read (not an
   in-memory equality on the same object). Revert the `str(...)` guard locally and confirm the test goes
   **red** (non-vacuous). A dict must come back a dict, not the stringified form.
2. **No string op silently corrupts the dict** — audit `reducer.py:89/:306` and every other `.actor`
   consumer; confirm none applies a str-only operation that would misbehave on a dict.
3. **Preferred path is shared-package-free** — no diff under `spec_kitty_events`; the dict actor is
   feature-detected; the string-actor path is byte-for-byte unchanged in behaviour.
4. **The fallback is version-gated and never blocks local persistence** — confirm the
   `hasattr(spec_kitty_events, "WPResolvedBindingChanged")` gate mirrors the genesis pattern
   (`emit.py:85-94`), that the skip is **logged** (not swallowed), and that with the gate `False` the
   annotation still persists + materializes identically (test 4).
5. **mypy `--strict` is clean with no suppressions** over `models.py`/`emit.py`/the consumers — the
   widening is the crux; any new `# type: ignore`/`# noqa` is a reject.

## Activity Log

- 2026-07-20T19:22:41Z – claude – shell_pid=519666 – Assigned agent via action command
- 2026-07-20T20:04:59Z – claude – shell_pid=519666 – Ready for review (pre-review gate skipped: scoped gate timed out at 300s — arch-dir timeout, not a code failure; per-file evidence green). actor str|dict widening + guarded from_dict decoders (dict round-trips JSONL uncorrupted, non-vacuously proven by revert-to-red); claim/review _saas_fan_out carries resolved {role,profile,tool,model}; first-class WPResolvedBindingChanged version-gated fan-out on emit_inner_state_changed (present+absent paths tested); reducer chokepoint keeps snapshot actor slot str. mypy --strict net-clean (base 71 = branch 71), ruff clean, shared_package_boundary green, zero new suppressions. Per-file evidence: owned 9/9, status suites 1182, support/activity 1192, resolved-binding/emit 118.
- 2026-07-20T20:06:41Z – claude – shell_pid=703549 – Started review via action command
- 2026-07-20T20:27:07Z – user – shell_pid=703549 – Approved: actor widening mypy net-clean (68<=70), dict round-trip non-vacuous, WPResolvedBindingChanged first-class version-gated, feature_slug->mission_slug canon
