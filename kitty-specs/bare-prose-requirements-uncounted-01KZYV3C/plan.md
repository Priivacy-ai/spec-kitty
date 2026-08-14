# Implementation Plan: Bare-Prose Requirements Are Silently Uncounted by the Coverage Gate

**Branch**: `pr/bare-prose-requirements-uncounted` | **Date**: 2026-08-14 | **Spec**: `kitty-specs/bare-prose-requirements-uncounted-01KZYV3C/spec.md`
**Input**: Feature specification from `kitty-specs/bare-prose-requirements-uncounted-01KZYV3C/spec.md`

**Note**: This template is filled in by the `/spec-kitty.plan` command. See `src/doctrine/missions/software-dev/command-templates/plan.md` for the execution workflow.

## Summary

`parse_requirement_ids_from_spec_md` (`src/specify_cli/requirement_mapping.py`) only
counts a requirement id when it is written in one of four **declared** shapes (table
row / id-naming heading / bulleted item / bold-led paragraph — settled by #3394/#3395).
A spec that declares some requirements correctly and writes others as bare,
unbulleted, unbolded prose (`FR-001 the loader must reject...`) has those bare-prose
ids silently excluded from `functional_requirement_ids` entirely — not unmapped, never
counted. `finalize-tasks`, `map-requirements`, and `spec-kitty next`'s tasks-boundary
readiness check all inherit this blindness and can report full FR coverage while
requirements were never seen.

The fix (FR-001) is a **new, per-token, per-line, section-scoped, document-declared-set
blocking predicate** — not a promotion of the existing advisory
`find_undeclared_requirement_citations` (verified inert on the mixed-declaration case:
returns `[]` against the issue's own repro) — wired into all three surfaces named in
Story 1: the `mission_finalize.py` CLI gate, the `tasks_mapping_core.py` coverage
computation, and `runtime_bridge_cores.evaluate_guards` (the pure core `spec-kitty next`
already uses). The `spec-kitty next` wiring is the mission's central engineering risk:
a prior attempt at an adjacent signal (`_zero_declared_requirement_block`, reverted at
`3823f2b00`) was provably inert because every guard that reads
`requirement_mapping_failures` checks `_tasks_dir_ready` (the `tasks_wp_files`
short-circuit) *first*. This plan's guard changes read the new signal **before** that
short-circuit in every guard they touch, and add a per-guard non-vacuity ("teeth") test
proving it (FR-002/FR-010/NFR-005).

## Technical Context

**Language/Version**: Python 3.11+ (charter-pinned; no new language-version dependency).
**Primary Dependencies**: None new. `src/specify_cli/requirement_mapping.py` stays pure
stdlib (`re`, `pathlib.Path`, `typing`) per its own module contract; `runtime_bridge_cores.py`
stays a "zero-dependency leaf" (stdlib + `runtime.next.decision` types only, per its own
docstring invariant, independently labeled "C-007" there — distinct from this mission's
spec-level C-007).
**Storage**: N/A. The new detector operates on `spec.md` text already read by the calling
CLI command / residual gather function; the frozen corpus fixture (FR-005) is a static
JSON file committed under `tests/`, read only by its own test, never at runtime.
**Testing**: pytest, targeted to the directories named in "Targeted Test Surface" below —
never the full ~17,000-test suite for iteration; the full suite is reserved for
post-merge mission-level validation per the charter's Testing Requirements.
**Target Platform**: CLI (Linux/macOS/Windows), no platform-specific behavior — pure
regex/string operations, no filesystem walking beyond what already happens.
**Project Type**: Single project (Python CLI + library). No web/mobile surface.
**Performance Goals**: NFR-006 — the detector is pure regex/string-splitting over
already-read `spec.md` content; no new filesystem or network I/O added to the hot
`spec-kitty next` path. (One caveat recorded honestly: the new `spec-kitty next` gather
step reads `spec.md` independently of `_check_requirement_mapping_ready`'s existing read,
because it must not be gated behind `tasks_dir.is_dir()` — see "Story 3 / FR-002 guard
ordering" below. This is one additional `Path.read_text()` per guard evaluation at the
tasks boundary, not a new I/O *class* — no network calls, no directory walks, no new
subprocess/git calls — and is the smallest change that satisfies FR-002's ordering
requirement.)
**Constraints**: NFR-001..NFR-006 from spec.md (no doc-wide fallback, silent-success
prohibition, static-analysis cleanliness, new-code coverage, per-guard non-vacuity,
performance).
**Scale/Scope**: Three call sites gain the new predicate
(`mission_finalize.py::_validate_requirement_mapping`,
`tasks_mapping_core.py::plan_mapping`, `runtime_bridge_cores.evaluate_guards`'s tasks
family); one new pure function in `requirement_mapping.py`; one new fact object (or
extension) threaded from `runtime_bridge.py` into `runtime_bridge_cores.py`; a
368-spec-corpus frozen fixture under `tests/`.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority** — PASS. FR-001 is a new predicate, not a second
  "declared" concept; it reuses `_requirement_named_sections` and the existing
  `_DECLARED_ID_PATTERNS`/`_declared_ids` machinery verbatim (C-001). No parallel
  requirement-extraction authority is introduced.
- **Architectural alignment** — PASS (see "Seam" below): the change lands entirely in
  `src/specify_cli/` + `src/runtime/next/`, neither of which is `src/kernel/`; the
  `runtime_bridge_cores.py` zero-dependency-leaf invariant (C-007) is preserved by
  threading the new signal as plain data via a fact object, never a new import.
  Confirmed by direct read of `runtime_bridge_cores.py`'s own module docstring
  (lines 1-68) and its existing `RequirementMappingFacts` pattern (line 241).
- **Domain-driven splits + tiered rigour** — PASS. The blocking-classification logic
  (core domain logic) gets full unit-test rigour (NFR-004); the CLI wiring at the three
  call sites is glue, tested at integration granularity via the existing per-command
  test files.
- **ATDD-first** — see "ATDD-First (charter C-011 / spec C-002)" below; ordering constraint acknowledged and
  the base-branch caveat is stated explicitly, not silently assumed.
- **Glossary & terminology** — PASS. "Mission," never "Feature" (C-004); no new
  user-facing terms are introduced that need glossary entries — "bare-prose requirement"
  is spec-internal vocabulary, not a CLI flag or public API name.

**Complexity ceiling** — one pre-existing violation found on a touched surface
(`_validate_requirement_mapping`, complexity 16 > 15 ceiling; verified with `radon cc`)
— see "Campsite-Clean Scope" below (PLAN-GOV-001). It is **remediated**, not shipped and
justified: a behaviour-preserving extraction lands in the campsite-clean FIRST commit,
before IC-03's functional addition touches the function, so no charter violation is
actually shipped by this mission's diff. The Complexity Tracking table below (for
violations shipped *with* a justification) therefore correctly stays empty — nothing is
being retained/justified, it is being fixed.

## Seam

This mission lands entirely on the **CLI** seam: `src/specify_cli/` (three CLI-command
call sites) and `src/runtime/next/` (the pure decision core + its residual gather shell).
**Neither directory is `src/kernel/`.** No CLI command in this diff reaches past a
service into kernel internals: `requirement_mapping.py` is a standalone,
dependency-free module (verified: only `re`, `pathlib.Path`, `typing` imports, confirmed
by direct read); it is not part of, and does not import, `src/kernel/`. The
`runtime_bridge_cores.py` pure core likewise imports nothing but stdlib +
`runtime.next.decision` (verified by direct read of its top-of-file imports, lines
70-77) — it has no kernel dependency to violate. This mission adds no new package, no
new cross-boundary import, and no new consumer of `src/kernel/`; the "kernel floor" CI
gate is consequently untouched by this mission's changed-files set (see "Gate Set"
below).

## Contracts

Doctrine schemas, mission step contracts, the orchestrator-api surface, and the
vendored `spec_kitty_events`/`spec_kitty_tracker` packages are **all preserved
unchanged** by this mission. Verified per surface:

- **Doctrine schemas** (`scripts/generate_schemas.py --check`, the CI doctrine-freshness
  gate): unaffected — this mission adds no new `ArtifactKind`, no new DRG node/edge
  vocabulary, no new charter-activatable artifact. It only adds Python functions and a
  test fixture.
- **Mission step contracts** (`src/specify_cli/mission_step_contracts/`,
  `StepContractExecutor`): unaffected in *shape*. `StepContractExecutor.execute` runs
  the step and returns a result; the post-composition **guard** check
  (`_check_composed_action_guard` → `runtime_bridge_cores.evaluate_guards`) is a
  *separate* call made by `_dispatch_via_composition` *after* `execute` returns
  (`runtime_bridge_composition.py` lines 427-486). This mission changes what
  `evaluate_guards` returns for the `tasks` action family; it does not change
  `StepContractExecutor`'s own execution contract, its result dataclasses
  (`StepContractExecutionResult` / `StepContractStepResult`), or any mission step
  contract schema file. What *would* have to be true for the contract surface to be
  affected: if the new bare-prose failure needed to flow through
  `StepContractExecutionError` or a new field on `StepContractExecutionResult` — it does
  not; it flows through the existing `Decision(kind=blocked, ...)` guard-failure shape
  every other guard failure already uses. See "Composed-Guard Vocabulary Scope (C-009)"
  below for the full statement this mission's C-009 requires.
- **Orchestrator-api surface**: unaffected — no new/changed public orchestrator-api
  route, request/response shape, or CLI JSON schema. The new failure strings appear
  inside the *existing* `guard_failures` / `unmapped_functional_requirements` list
  fields already returned by `finalize-tasks --json`, `map-requirements --json`, and
  `spec-kitty next --json`'s `Decision.reason`/guard-failures payload — new *values* in
  an existing *shape*, not a new field.
- **`spec-kitty-events`/`spec-kitty-tracker`** (external PyPI packages per charter's
  Shared Package Boundary): untouched — this mission does not emit a new event type or
  touch the sync/tracker path at all.

## Architecture

### FR-001 — the new per-token, per-line, document-scoped bare-prose predicate

New pure function in `src/specify_cli/requirement_mapping.py`, e.g.
`find_bare_prose_requirement_ids(spec_content: str) -> BareProseResult` (a small
`NamedTuple`/`TypedDict` carrying `{section_heading: str, ids: list[str]}` entries so
callers can build a human-readable, section-attributed message — mirrors
`find_undeclared_requirement_citations`'s existing return shape closely enough to reuse
its message-building idiom without literally calling it, per C-001's "not a promotion").

**Algorithm** (document-scoped per C-006, section-scoped per FR-001's heading-reuse
clause, per-line to satisfy Story 2 AC3 without an invented exception list):

1. Compute `document_declared = _declared_ids(spec_content)` — the existing, unmodified,
   whole-document declared-id set (C-001: no widening of the four shapes).
2. For each `(heading_text, body)` in `_requirement_named_sections(spec_content)` —
   **heading-scoping is reused unmodified** (C-008 decision below: `_is_requirement_heading`
   is NOT broadened in this mission):
   - For each line in `body`:
     - If the line matches one of the four `_DECLARED_ID_PATTERNS` — **skip raw-token
       scanning of the rest of that line entirely.** This is the load-bearing rule that
       satisfies Story 2 AC3: a table row `| FR-001 | ...mentions FR-999... |` has its
       *own* id (FR-001) already counted in `document_declared`, and the line is not
       scanned further, so a foreign/malformed token in that same row's description
       column is never examined. (This also explains, without contradiction, why
       Story 4/FR-005's already-measured 9/368 corpus figure *does* include some
       description-column citations: those 9 come from lines that do **not** themselves
       match a declared shape — e.g. a non-requirement table nested inside a
       requirement-named heading, or running prose — never from a properly-declared
       table row's own description cell. Verified directly against one of the 9:
       `kitty-specs/egress-refusal-consolidation-3110-01KYW895/spec.md`'s
       `### Requirement-level falsifiers` heading contains running prose, not a
       requirements table, so its `C-1`/`C-3` citations are scanned as un-declared
       lines, exactly matching this algorithm.)
     - Else, scan the line for every `_REF_FIND_PATTERN` token (`FR-`/`NFR-`/`C-`
       shaped). Any token **not** in `document_declared` is a bare-prose candidate,
       recorded against that section's heading.
3. Candidates are grouped per section and returned; callers decide message shape.

This is genuinely a **new** predicate, not `find_undeclared_requirement_citations`
promoted: that function's trigger is `section_raw_tokens and not _declared_ids(section)`
(fires only when a section's *own* declared set is empty) and is unreachable on the
mixed-declaration case by construction. The new predicate instead asks, per line, "does
this specific line declare its token, and if not, is that token declared *anywhere in
the document*?" — a strictly finer-grained question that fires exactly on the
mixed-declaration case #3396 describes.

### C-008 decision: Constraints-heading (`C-XXX`) scoping — **option (b), explicitly narrowed, not broadened**

`_is_requirement_heading`'s substring match on `"requirement"` does not match the
corpus's canonical `### Constraints` heading (325/368 = 88.32% of specs, per direct
corpus measurement recorded in the spec). C-008 requires this plan to pick (a) broaden
the predicate to also match `"constraint"`, or (b) explicitly narrow scope with
justification.

**This plan picks (b).** Reasoning: the FR-005/Story 4 false-positive rate (9/368 =
2.45%, document-scoped) is a **settled, already-measured fact this plan must not
relitigate** (per this mission's own operating instructions). That rate was measured
against `_requirement_named_sections` using the *current*, unmodified
`_is_requirement_heading`. Broadening the heading predicate to also match
`"constraint"` would pull ~88% of the corpus's `### Constraints` sections into the
blocking detector's scope — a scope change an order of magnitude larger than the
measured 2.45%.

**Broadened-predicate FP measurement, performed for this plan-fix pass (PLAN-GOV-002):**
rather than leave the broadened-scope false-positive rate an unmeasured unknown, a
read-only corpus scan was run against the current `kitty-specs/*/spec.md` corpus (368
specs) using this plan's own documented algorithm ("Architecture" above), with
`_is_requirement_heading` broadened to also match `"constraint"` — the same corpus-scan
approach IC-07 already describes for the false-negative sample, reused here rather than
inventing a new method. **Result: only 5 of 368 specs (1.36%) are newly flagged beyond
the narrow-heading candidate set (8 candidate tokens total — raw per-occurrence count,
no dedup step, matching the Architecture section's own algorithm as literally described),
and manual review of every one of those 8 tokens found zero true positives** — the same
"foreign-id citation, not a lost requirement of this spec" class the settled 9/368 figure
already establishes. Two of
the 5 (`C-009` in
`coord-read-residuals-merge-lanes-and-identity-routing-01KW2M8V/spec.md`; `C-007` in
`doctrine-public-api-surface-01KZPDSR/spec.md`) are citations, from inside a genuine
`### Constraints` table row, of another mission's or the charter's own like-named
constraint id (compounded by a pre-existing, broadening-independent gap in
`_DECLARED_ID_PATTERNS`: a non-numeric-suffixed custom id like `C-009-mirror` or
`C-007-mission` never itself matches `_TABLE_ROW_ID_PATTERN`'s exact-digits capture, so
its own ID-column text is scanned as un-declared raw text too). The other 3
(`drg-relation-impacts-vocabulary-01KYFV87`, `foundational-values-creed-band-01KYFV8N`,
`test-quality-doctrine-series-01KYFV8H`) surface a **broadening-specific over-match risk
the narrow "requirement"-only predicate does not have**: a plain substring match on
`"constraint"` also matches non-canonical narrative headings such as `"Carried
constraints — do not lose these when speccing"` (a cross-mission-series scratch section,
not the canonical `### Constraints` requirements table C-008 is actually about) —
pulling free-text notes into blocking scope.

**Why this measured result still supports (b), not (a):** the raw FP count is small, but
shipping a production-quality broadened predicate would require the *same*
double-independent manual true/false-positive classification discipline already applied
to the settled 9/368 figure (per spec.md: "measured... twice, independently, with
identical results"), not a single read-only scan — and it would additionally require
designing a heading-match predicate smarter than a plain `"constraint"` substring test,
to exclude free-text "carried constraints" sections from the over-match this scan just
surfaced — a design question this plan phase did not scope and does not resolve here.
That combined cost (re-run the double-verification discipline; design a non-substring
heading predicate) is disproportionate to what this plan phase can responsibly absorb
without either rushing the verification rigor FR-005 itself sets as precedent, or
silently shipping a narrower ad hoc heading fix nobody asked for. This is the explicit
effort/cost justification the confirmed finding asked for — the *measurement* was not
out of scope (it is done, above, and its result is real data, not a placeholder), but
the *full remediation* (a production-quality broadened predicate) is, and disposition
(b) is kept on that basis, not because the data was unavailable. Per the spec's own Key
Entities text — "C-008 requires the plan phase to either close this asymmetry **or
explicitly document it as an accepted scope narrowing**" — narrowing is an explicitly
sanctioned outcome, not a default the plan phase invented.

**Disposition**: `_is_requirement_heading` is left byte-identical. `C-XXX` bare-prose
items under a `### Constraints` heading remain **out of blocking scope** for this
mission. Story 4 AC4's false-negative sample (below, IC-07) is the disclosure mechanism
for the *false-negative* side of this decision (specs where the detector under-fires);
the *false-positive* side is now covered too, by the corpus scan measured above (this
plan-fix pass, PLAN-GOV-002) — both figures, plus the over-match risk the scan surfaced,
are the FP/FN data-point pair a future mission needs to make an informed broaden decision
instead of guessing. IC-07's measurement helper should be extended to also record the
FP-side result documented above (not only the FN sample) so both figures live in the
same place — the detector's module docstring — at implementation time.

### C-006 in the algorithm

Already folded into the algorithm above: `document_declared` is computed once, over the
whole document, via the unmodified `_declared_ids(spec_content)` — never re-scoped to
the section body. This is the 2.45%-vs-37.77% choice C-006 makes binding; the plan does
not re-derive it, only implements it literally.

### Story 5 / FR-007 / FR-008 — fail-loud, never silently clean

Two genuinely different failure surfaces exist and must stay genuinely different
(explicit split per Story 5 AC3):

1. **The existing advisory** (`find_undeclared_requirement_citations`, wrapped by
   `_log_requirement_extraction_warnings_safely`, `runtime_bridge.py` ~line 835): stays
   completely unchanged. Its contract is "never crash into a gate" — any exception in
   its computation is swallowed and logged at DEBUG. This mission does not touch it,
   does not route the new detector through it, and does not weaken its swallow-on-error
   behavior.
2. **The new blocking detector**: gets its own, opposite contract — "never silently
   report clean." Concretely: the residual gather step that calls
   `find_bare_prose_requirement_ids` (in `runtime_bridge.py`, and equivalently in
   `mission_finalize.py` / `tasks_mapping_core.py`) does **not** wrap the call in a
   broad `except Exception: return []`. Where an exception occurs during the pure
   classification, it is caught **once**, at the single call site, and converted into an
   explicit, non-empty failure entry — e.g. `"Bare-prose requirement detection failed to
   classify {mission}'s spec.md: {exc!r} — treating as blocking (never silently clean,
   NFR-002)."` — never re-raised past the CLI boundary as a bare traceback, and never
   downgraded to a log line. This mirrors `_check_requirement_mapping_ready`'s own
   existing `except Exception as exc: return [f"Requirement mapping preflight failed:
   {exc}"]` pattern (`runtime_bridge.py` line 919) — the new detector adopts the *same*
   fail-loud shape already used one function up, not a new contract invented from
   scratch.

   For the "ambiguous shape" bucket (Story 5 AC2's narrower boundary — a token
   partially matching more than one classification rule with no tiebreak, or a
   malformed/unterminated heading/section boundary): by construction, the four
   `_DECLARED_ID_PATTERNS` are mutually exclusive on a per-line basis (each requires a
   different leading character after `lstrip()` — `|`, `#`, `-`/`*`/digit, `**` — so no
   line can match two of them; `_declared_ids` already relies on this via its
   `break`-after-first-match). This plan records honestly that the *realistic* locus of
   Story 5's "ambiguous, therefore blocking" contract is the exception/fault-injection
   case above, not a genuine multi-rule tie — the fault-injection test (Story 5's own
   Independent Test) is what proves the contract, not a hand-constructed tie case that
   the current shape structurally cannot produce. If implementation discovers a genuine
   tie case, it is handled by the same "explicit failure, blocks" path, not a silent
   default.

### Story 3 / FR-002 / FR-003 — reaching `spec-kitty next`'s actual decision

**FR-003 audit finding (traced, not assumed):** production `spec-kitty next` for the
built-in `software-dev` mission type dispatches the **composed** vocabulary at the
tasks-finalize boundary, not the CLI-native one. Trace:

- `packs/built-in/missions/software-dev/mission.yaml` combined with
  `src/doctrine/workflows/software-dev-default.workflow.yaml` (`actions:` block
  contains `action_name: tasks`) means the software-dev mission type's resolved
  `action_sequence` includes the single composed `"tasks"` action.
- `_should_dispatch_via_composition` (`runtime_bridge_composition.py` lines 150-203)
  checks `_normalize_action_for_composition(step_id) in action_sequence` — for
  `step_id="tasks_finalize"`, `_normalize_action_for_composition` maps it to `"tasks"`
  (line 137-147), which **is** in the action sequence — so this returns `True` whenever
  `repo_root` is provided.
- `decide_next_via_runtime` (`runtime_bridge.py`) threads a real `repo_root` on every
  production call (confirmed: `repo_root=repo_root` appears at every call site feeding
  `_should_dispatch_via_composition`/`_dn_composition_dispatch`), and `_dn_composition_dispatch`
  runs as an early phase (lines 1723-1799) that, on success, **short-circuits** before
  the later phase that calls `_check_cli_guards` (lines 1594, 1612) is ever reached.
- Therefore: for the built-in `software-dev` mission type — which is this mission's own
  `mission_type` (`meta.json`) and the overwhelming majority of missions in this repo —
  the **live** guard at the tasks-finalize boundary is
  `_check_composed_action_guard` → `runtime_bridge_cores._evaluate_composed_tasks_guard`
  → `_evaluate_composed_tasks_terminal_guard` (`legacy_step_id="tasks_finalize"`), which
  **already reads** `status_facts["requirement_mapping_failures"]` (confirmed by direct
  read, `runtime_bridge_cores.py` lines 524-534).
- The CLI-native `_evaluate_tasks_finalize_guard` (line 492-504), which **does not read
  `requirement_mapping_failures` at all today**, is reachable only when
  `_should_dispatch_via_composition` returns `False` — a degraded/fallback path (unknown
  mission type, charter lookup exception, no `run_dir`) rather than the production path
  for this mission's own mission type.

**Scope decision**: this plan wires the new bare-prose signal into **all four**
plausible call sites FR-010 lists — `_evaluate_tasks_packages_guard`,
`_evaluate_tasks_finalize_guard`, `_evaluate_composed_tasks_packages_guard`,
`_evaluate_composed_tasks_terminal_guard` — not only the three proven live for the
built-in mission type. Justification: (1) the CLI-native pair is not proven *dead* for
every configuration — only non-primary for the default built-in one; a custom mission
type without a matching `action_sequence` entry and without a per-step contract binding
falls back to exactly that path; (2) NFR-002's "silent-success prohibition" argues for
closing the pre-existing `_evaluate_tasks_finalize_guard` asymmetry (it reads
`occurrence_gate_failures` but not `requirement_mapping_failures` at all, a pre-existing
gap this mission's own investigation surfaced, per the spec's Edge Cases) rather than
leaving one guard in the family structurally blind by construction; (3) FR-010 already
requires a teeth test per guard actually wired, so the marginal cost of the fourth guard
is one more test, not a new class of risk.

**FR-002's ordering constraint** (the load-bearing fix): every guard above currently
gates the `requirement_mapping_failures` read behind `_tasks_dir_ready` — e.g.:

```python
def _evaluate_tasks_packages_guard(snapshot):
    if not _tasks_dir_ready(snapshot):
        return [MISSING_TASK_FILES_MESSAGE]
    return list(snapshot.status_facts["requirement_mapping_failures"])
```

This is *exactly* the shape that made `_zero_declared_requirement_block` inert: with
zero WP files, `_tasks_dir_ready` is `False` and the function returns before ever
reading the new signal. This plan's fix reads the new bare-prose fact **first,
unconditionally**, in each of the four guards.

**Test-fixture regression, resolved explicitly (PLAN-ARCH-001): read via `.get(...)`, not
a bare subscript.** `snapshot.status_facts` is a plain `Mapping[str, Any]`
(`runtime_bridge_io.py:745-746`), and `tests/runtime/test_bridge_cores.py`'s shared
`_snapshot()` helper's `base_status_facts` dict does **not** carry a
`"bare_prose_requirement_failures"` key. An unconditional
`snapshot.status_facts["bare_prose_requirement_failures"]` subscript would raise
`KeyError` in every one of `_snapshot()`'s existing callers the instant the guard is
wired — including exact-equality assertions in that same file (e.g.
`test_cli_native_tasks_packages_extends_requirement_mapping_failures`,
`test_cli_native_tasks_finalize_missing_dependency_uses_full_stem_breaks_on_first`) that
this plan's own "Targeted Test Surface" above requires to keep passing unmodified (Story
2 AC2 / SC-002). **This plan picks the `.get()`-degrades-gracefully option, not the
fixture-update option**: every touched guard reads the new key via
`snapshot.status_facts.get("bare_prose_requirement_failures", ())`, never a bare `[]`
subscript, so a snapshot/fixture that predates this mission's wiring degrades to "no
bare-prose failures" instead of crashing. This is a deliberately narrower fix than
teaching every one of `_snapshot()`'s callers (and any equivalent helper in `tests/next/`
/ `tests/specify_cli/next/`) about the new key: it makes the four guards resilient to
*any* caller that has not been updated yet, present ones included, without requiring a
coordinated fixture-update commit landed in lockstep. (`requirement_mapping_failures`
itself stays a bare subscript, unchanged — it is a pre-existing key every `_snapshot()`
caller already sets by default; only the brand-new key gets the defensive read — this is
the guard-class-wide rule, not a one-off for this single guard.)

```python
def _evaluate_tasks_packages_guard(snapshot):
    failures = list(snapshot.status_facts.get("bare_prose_requirement_failures", ()))
    if not _tasks_dir_ready(snapshot):
        failures.append(MISSING_TASK_FILES_MESSAGE)
        return failures
    failures.extend(snapshot.status_facts["requirement_mapping_failures"])
    return failures
```

This is Story 3's option (a) — "make the new signal's evaluation independent of, or
ordered before, the `tasks_wp_files`-first check" — applied literally to every touched
guard, and satisfies both of Story 3's required configurations (zero WP files; ≥1 WP
file none referencing the bare-prose ids) with the same code path, because the new
fact's presence never depends on `tasks_dir`/WP-file state at all — only on `spec.md`.
Once IC-02's wiring lands and `gather_artifact_presence` always populates
`"bare_prose_requirement_failures"` for real production snapshots, `_snapshot()`'s
`base_status_facts` dict SHOULD still be updated to include the key (matching the other
default-populated facts already in that dict) — for fixture *accuracy*, not to avoid a
crash the `.get()` read already prevents; this is a follow-up hygiene item for IC-02, not
a blocking dependency of the guard wiring itself.

### C-007 — fact-port shape: a sibling fact object, not an extension

`RequirementMappingFacts` (line 241) is WP-shaped: `wp_ids`, `wp_requirement_refs`,
`spec_requirement_ids`. The new bare-prose signal needs none of that — only `spec.md`
content and the document-declared set, which `_check_requirement_mapping_ready` does
not even compute when `tasks_dir` is absent (its early return, line 892-893). Since
FR-002 requires the new signal to fire **independent of** `tasks_dir`/WP-file state,
reusing `RequirementMappingFacts` would force an artificial coupling (populating WP
fields with dummy values just to satisfy the dataclass shape, or duplicating the
early-return logic). This plan therefore adds a **sibling** frozen dataclass in
`runtime_bridge_cores.py`:

```python
@dataclass(frozen=True)
class BareProseRequirementFacts:
    """Facts gathered from spec.md alone (T023-sibling) so the bare-prose
    classification decision can be pure, independent of tasks/ dir state."""
    flagged: Mapping[str, tuple[str, ...]]  # {section_heading: (ids...)}
    classification_error: str | None  # non-None => blocking, per Story 5/NFR-002
```

and a pure `_evaluate_bare_prose_requirements(facts: BareProseRequirementFacts) ->
list[str]` beside `_evaluate_requirement_mapping`, following the same
fact-port/pure-core split. The residual gather step lives in `runtime_bridge.py`
(new function, e.g. `_check_bare_prose_requirements_ready(feature_dir) -> list[str]`,
reading `spec.md` only — no `tasks_dir` dependency) and `runtime_bridge_io.py`'s
`gather_artifact_presence` adds one new `status_facts` key,
`"bare_prose_requirement_failures"`, populated the same way
`"requirement_mapping_failures"` already is (line 845) — a plain-data tuple, never a
new import inside `runtime_bridge_cores.py`. This is the "equivalent fact object"
C-007 explicitly permits as an alternative to extending `RequirementMappingFacts`.

**Architectural test**: per C-007's suggestion, this plan adds a focused test pinning
`runtime_bridge_cores.py`'s import set (stdlib + `runtime.next.decision` only) so a
future regression that adds a cross-package import is caught by construction, not by
convention — e.g. `tests/architectural/test_bridge_cores_import_boundary.py`, parsing
the module's AST `Import`/`ImportFrom` nodes and asserting every non-stdlib target is
`runtime.next.decision`.

### Wiring into the two non-`spec-kitty next` surfaces

`mission_finalize.py::_validate_requirement_mapping` (line 621) and
`tasks_mapping_core.py::plan_mapping` (line 123, via `compute_coverage`) are **separate
call sites** from the `runtime_bridge_cores` pure core — they duplicate its
missing/unknown/unmapped logic rather than sharing it. Both currently compute coverage
purely from `functional_spec_requirement_ids` (the *declared* set), so — exactly like
the runtime core — a bare-prose FR is invisible to them by construction (it is never in
that set to begin with). Both call sites already read the raw `spec_content` (or have
trivial access to it) before computing `functional_spec_requirement_ids`, so wiring
`find_bare_prose_requirement_ids` in is a same-shaped, same-file addition: compute the
bare-prose candidates once, and if non-empty, fail exactly like the existing
missing/unknown/unmapped path already does — `_validate_requirement_mapping` already
`raise typer.Exit(1)`s with a structured payload; `plan_mapping` already returns a
`MappingPlan` carrying `compute_coverage`'s `unmapped_functional` — the new
`bare_prose_requirement_ids` are surfaced as an **additional**, separately-labeled
field on both payloads (not merged into `unmapped_functional_requirements`, so a caller
can distinguish "declared but not yet mapped to a WP" from "never declared at all,"
which are genuinely different remediation stories for an operator).

## Composed-Guard Vocabulary Scope (C-009)

**`StepContractExecutor` itself is out of scope; `_check_composed_action_guard` is in
scope (already covered above).** Traced directly:
`_dispatch_via_composition` (`runtime_bridge_composition.py` lines 489+) calls
`StepContractExecutor.execute` to *run* the composed action, then calls
`_check_composed_action_guard` (a **separate**, subsequent call, lines 427-486) to
decide whether to advance. The new bare-prose failure message flows through the guard
path only — the same `list[str]` "guard failures" vocabulary every existing guard
(missing artifact, unknown requirement ref, occurrence-gate failure) already uses, and
the same `Decision(kind=blocked, ...)` construction those failures already produce
downstream. `StepContractExecutor`'s own execution contract
(`StepContractExecutionResult` / `StepContractStepResult` / `StepContractExecutionError`)
is untouched: the executor does not know or care why a post-execution guard blocked, and
this mission adds no new field it would need to carry that reason. **No**
`src/specify_cli/mission_step_contracts/` schema change and **no** orchestrator-api
documentation update are needed, because the new guard-failure message is not a new
*message class* at the contract layer — it is a new *string value* inside the guard
failure list that class already carries. (Compare: adding
`occurrence_gate_failures` to the guard vocabulary, an earlier precedent in this same
file, similarly required no schema change — it is a value, not a shape, change.)

## Gate Set For This Mission

Enforced CI gates this mission's changed-files set (`src/specify_cli/`,
`src/runtime/next/`, `tests/`) actually triggers, and a stated reason for every
enforced gate **not** included:

**Triggered / must pass:**
- `[ENFORCED] Run Bandit security scan`, `[ENFORCED] Run pip-audit CVE scan` — always-on,
  no path filter; pure-Python additions, expected clean.
- `[ENFORCED] banned-API lint gate (TID251)` — always-on; no banned API used
  (no `hashlib.sha256`, no direct `click.exceptions.*` catch).
- `[ENFORCED] Validate patch() target strings (closes #394)` — always-on; new tests must
  `@patch()` real symbol paths, not guessed ones (per this mission's own new mocks in
  fault-injection tests, Story 5).
- `[ENFORCED] Verify generated doctrine schemas are up to date` — always-on
  (`lint` job); this mission adds no doctrine artifact, so `--check` should be a no-op
  pass, but the job itself always runs.
- `fast-tests-next` — triggered (`needs.changes.outputs.next == 'true'`, this mission
  touches `src/runtime/next/`), runs `tests/next/ tests/specify_cli/next/ tests/runtime/`
  — not floor-enforced, but must be green.
- `uv.lock` freshness (`uv-lock-check`) — always-on; this mission adds no new dependency,
  so `uv.lock` should already be in sync; the gate still runs and must pass.
- `clean-install-verification` — always-on; unaffected in *content* by this mission
  (no dependency/package-boundary change) but the job runs unconditionally and must
  stay green.

**Triggered but NOT floor-gating this mission's own coverage (stated why):**
- `kernel-tests` (90% floor) — condition is
  `needs.changes.outputs.kernel == 'true' || github.event_name == 'push'`. This
  mission's changed files are entirely outside `src/kernel/`, so `changes.outputs.kernel`
  evaluates `false` for a pull-request run; the job (and its 90% floor) is **not
  triggered** by this mission's diff on a PR run. (It may still run on a `push` event
  per the `||` clause — an existing, pre-existing repo-wide behavior this mission does
  not change or rely on.)
- `mission-loader-coverage` (90% floor, `src/specify_cli/mission_loader/` only) — the
  *job* may execute (its trigger condition includes `changes.outputs.next == 'true'`,
  which this mission's `src/runtime/next/` changes do satisfy), but its `--cov-fail-under=90`
  is scoped to `src/specify_cli/mission_loader/`, a package this mission does not touch.
  The floor is therefore vacuously satisfied by this mission's diff (unaffected
  baseline), not exercised by it.

**Not triggered at all on this mission's PR (corrected, PLAN-VERIFY-002 — was
mis-listed above as "Triggered / must pass"):**
- **SonarCloud Scan + Quality Gate** — the `sonarcloud` job's own trigger condition,
  `.github/workflows/ci-quality.yml:3648`
  (`if: always() && (github.event_name == 'schedule' || github.event_name ==
  'workflow_dispatch')`), restricts it to `schedule`/`workflow_dispatch` events only — it
  **never** runs on a `pull_request` event. The job comment at
  `ci-quality.yml:3585-3589` states this explicitly: "PRs skip Sonar entirely to keep
  review latency low." The job is also absent from the `quality-gate` aggregator's
  `needs:` list (`ci-quality.yml:4361-4416`), confirming it is not part of the blocking
  set for a PR run either directly or transitively. This mission's PR will not run
  SonarCloud at all — the earlier claim that it is "always attempted when `SONAR_TOKEN`
  is configured" was wrong for the `pull_request` event this mission's own PR runs
  under. **NFR-004's per-branch focused-test requirement (every new branch/helper gets a
  focused test in the same work package) is therefore the sole enforcement mechanism for
  new-code coverage on this mission's actual PR review surface** — not Sonar's new-code
  coverage gate, which never executes here.

**Not triggered at all (path-scoped, this mission's diff does not touch the gating
paths):**
- `[ENFORCED] Run architecture/docs consistency tests on changed markdown` and
  `[ENFORCED] Run markdown style linting on changed files` — both scoped to *changed
  markdown*; this mission's PR-visible markdown changes are `plan.md`/tracer files
  (planning artifacts, not doc-tree content under `docs/`), so these should no-op
  cleanly rather than being "not triggered" in the job-skip sense — recorded here so a
  reviewer does not mistake a clean pass for an untriggered gate.
- `[ENFORCED] Check Contextive glossary files are up-to-date` — condition requires a
  change under `glossary/`, `src/specify_cli/`, or `.kittify/traceability/`; this
  mission *does* touch `src/specify_cli/`, so this gate **is** triggered — included here
  for completeness since the mission-brief's gate list named it conditional. No new
  glossary term is introduced, so it should pass cleanly.
- `[ENFORCED] Typer 0.26 JSON error surface` — this mission adds no new Typer command or
  option; the existing `finalize-tasks`/`map-requirements` commands' JSON error surface
  is extended with a new field (not a new command), so this gate's fixed test file
  (`tests/agent/test_json_group_typer_surface.py`) is unaffected by this mission's
  scope and should pass without modification.

**Advisory, not a gate** (explicitly not claimed as a CI safety net): `make lint`
(ruff) and `mypy --strict` run as `[INFO]` in CI — local discipline only. This mission's
own charter obligation (NFR-003, and the charter's Code Style section) is to run both
locally before commit; neither is claimed here as something CI will independently catch.

## Baseline Capture on `ab15225ea`

**Binding**: the baseline MUST be captured on `ab15225ea` (tip of
`origin/op/3394-requirement-citation-scope`), **not** `main`. Confirmed by direct git
inspection this plan phase performed: `git cat-file -t ab15225ea` resolves to `commit`;
`git merge-base --is-ancestor ab15225ea HEAD` succeeds; `git rev-parse
origin/op/3394-requirement-citation-scope` equals `ab15225ea8b08c93779da904a4c7f7f30f3efbac`
exactly.

**Falsifiability note, fixed-ref not self-moving `HEAD` (PLAN-VERIFY-003):** the original
draft of this section stated the commit count and tip hash relative to `HEAD` — a claim
that goes stale the instant this file's own commit lands, since that commit *becomes*
`HEAD` and is neither the hash originally named nor one of the four
spec-authoring-shaped prefixes originally enumerated (this happened for real, between
this plan's authoring and its own adversarial-review fix pass: the tip moved from
`2e088fbe0` to `38a216f92`, an 8th, `plan(...)`-prefixed commit above `ab15225ea`, before
this fix pass added a 9th). The durable claim is pinned to a fixed ref instead: **as of
the pre-plan-commit tip `2e088fbe0`**, `git log --oneline ab15225ea..2e088fbe0` shows 7
commits above `ab15225ea`, all `spec(...)`/`fix(spec: ...)`/`reviews(spec: ...)`/meta-add
commits — zero implementation commits. `HEAD` moves again with every subsequent
`plan(...)`-prefixed planning/review-fix commit (this mission's own plan commit, this
fix-pass commit, and any future one), so **whoever executes the baseline capture
re-verifies live, at execution time**, that every commit strictly between `ab15225ea`
and the then-current tip matches one of `spec(...)` / `fix(spec: ...)` /
`reviews(spec: ...)` / `plan(...)` / meta-add — never an implementation-shaped commit.
The substantive conclusion that must hold is "zero implementation commits above
`ab15225ea`," not a specific literal count or hash.

**Tooling-friction note** (recorded here and in `tracer-tooling-friction.md`):
`spec-kitty plan --mission ... --json`'s own computed `planning_base_branch` field
returned `pr/bare-prose-requirements-uncounted` (the current branch itself) — **not**
`ab15225ea`/`op/3394-requirement-citation-scope`. This is a real tool gap for this
mission's deliberately non-standard topology (branching from an open PR's branch rather
than from a lane/worktree root), not a correction to the spec's binding decision. The
CLI's branch-context resolver infers `planning_base_branch` from `meta.json`'s
`target_branch` field (`pr/bare-prose-requirements-uncounted`) for this
`topology: coord` mission, which is correct for *where completed work lands* but wrong
for *what the red-first baseline must be measured against*. **Whoever executes the
baseline capture must use `ab15225ea` explicitly, not the CLI-reported
`planning_base_branch` value, for this one mission.**

**Procedure**: before any implementation change, run (bounded to the directories named
in "Targeted Test Surface" below — not the full suite):

```bash
git worktree add /tmp/baseline-ab15225ea ab15225ea   # or checkout in an isolated clone
cd /tmp/baseline-ab15225ea && uv sync --all-extras
PWHEADLESS=1 .venv/bin/python -m pytest \
  tests/specify_cli/test_requirement_mapping.py \
  tests/specify_cli/test_requirement_mapping_coord_surface.py \
  tests/next/ tests/specify_cli/next/ tests/runtime/ \
  -n 8 --dist loadfile -q
```

and record the red count and the failing test IDs.

**Charter compliance**: the charter's Pre-existing Failure Reporting Rule is binding —
any red test discovered here needs an upstream GitHub issue **before** being accepted
as baseline, with the command run, the failure summary, and why it is believed
pre-existing (not introduced by this mission's own, not-yet-started, changes). **This
plan explicitly does NOT assume the `ab15225ea` red set matches issue #3284's ~23
known-red-on-`main` set** — the base here is `ab15225ea`, not `main`; #3284 was measured
against `main`, and `main` and `ab15225ea` have diverged (this branch carries #3395's
~863-line unreviewed parser rewrite that `main` does not). Whoever executes the baseline
capture must diff the actual `ab15225ea` red set against #3284's named tests and state
explicitly, in the mission's implementation record, whether it matches — and if it does
not match (new reds introduced by #3395's still-unreviewed rewrite, or reds #3395's
rewrite happens to fix), open a new upstream issue naming the delta before treating it
as accepted baseline, per the charter rule.

## ATDD-First (charter C-011 / spec C-002)

`planning_base_branch` for this mission is explicitly **`ab15225ea` /
`origin/op/3394-requirement-citation-scope`** — not `main`, and not the CLI-computed
`pr/bare-prose-requirements-uncounted` value (see "Baseline Capture" above for why the
CLI value is wrong for this topology).

**The `main`-relative RED impossibility is stated explicitly, not silently assumed
away**: on `main`, the declared-shape extraction mechanism this mission extends
(`_DECLARED_ID_PATTERNS`, `_declared_ids`, `_requirement_named_sections`,
`find_undeclared_requirement_citations`) **does not exist** — it is #3395's own
still-unreviewed addition. A red-first ATDD test for this mission's bare-prose blocking
behavior imports and exercises functions that are simply absent on `main`; running it
there would fail with an `ImportError`/`AttributeError`, not a meaningful semantic RED.
Therefore the ATDD-First discipline's "RED on `planning_base_branch`, GREEN on final
commit" check for this mission's implementing work package **must** run against
`ab15225ea`, never against `main` — a RED-on-`main` run would be a category error, not
a stronger proof.

**Commit ordering**: the failing-first test(s) — at minimum, one exercising the issue's
exact repro shape through `spec-kitty agent tasks finalize-tasks` (Story 1's Independent
Test) — land as a separate commit, verified RED against `ab15225ea`, **before** any
implementation commit that makes it pass. This mirrors the charter's stated "often the
first commit of the lane" pattern.

## Campsite-Clean Scope (Standing Order 2)

A distinct, behaviour-preserving FIRST commit is scoped to the files this mission's
functional change touches: `src/specify_cli/requirement_mapping.py`,
`src/runtime/next/runtime_bridge_cores.py`, `src/runtime/next/runtime_bridge.py`,
`src/runtime/next/runtime_bridge_io.py`, `src/specify_cli/cli/commands/agent/mission_finalize.py`,
`src/specify_cli/cli/commands/agent/tasks_mapping_core.py`.

**Complexity debt finding (verified, not by inspection alone): one function is already
over the charter's ceiling.** `_validate_requirement_mapping`
(`src/specify_cli/cli/commands/agent/mission_finalize.py:621-677`) measures at
**cyclomatic complexity 16** — one over the charter's binding ceiling of 15 — verified
directly during this plan-fix pass with `radon cc -s
src/specify_cli/cli/commands/agent/mission_finalize.py -n A`, which reports `F 621:0
_validate_requirement_mapping - C (16)`, not merely eyeballed. IC-03 below schedules
exactly this function to gain a new branch (surfacing `bare_prose_requirement_ids`
alongside the existing missing/unknown/unmapped fields), which would push it further
over the ceiling if landed without remediation first. Per Standing Order 2, this is
in-scope, domain-matched debt on a surface this mission is about to functionally change,
and it is folded into the campsite-clean FIRST commit, not deferred:

- **Extraction (behaviour-preserving, no observable-output change)**: split
  `_validate_requirement_mapping` into (1) a pure classification helper — e.g.
  `_classify_wp_requirement_refs(wp_ids, wp_requirement_refs, all_spec_requirement_ids) ->
  tuple[list[str], dict[str, list[str]], set[str]]` — that owns the per-WP loop
  (missing/unknown/mapped bucketing) currently inline in the function, and (2) a
  report-formatting helper — e.g. `_emit_requirement_mapping_report(payload, *,
  json_output)` — that owns the JSON-vs-console branch and the three `console.print`
  loops. `_validate_requirement_mapping` itself becomes a thin orchestrator: call (1),
  compute `unmapped_functional_requirements`, early-return if clean, else call (2) and
  raise. This is the exact split the confirmed finding names: split the per-WP
  classification loop from the report-formatting branch into two helpers.
- **Sequencing**: this extraction lands in the campsite-clean FIRST commit, before IC-03's
  functional addition (the new `bare_prose_requirement_ids` field) touches the same
  function — so IC-03's diff lands against the already-decomposed, sub-ceiling shape,
  never adding a branch to the still-16-complexity original.
- **Verification**: re-run `radon cc` (or `ruff check --select C901` once available) on
  both extracted helpers and the orchestrator after the split, confirming each is
  comfortably under 15, before IC-03's commit is authored.

**The other five files/functions show no complexity debt worth folding.** All are
recently-touched, actively-maintained modules (`requirement_mapping.py` and
`runtime_bridge_cores.py` both carry #3394/#3395/#2531-era docstrings dated within the
last review cycle; `tasks_mapping_core.py` shows no lint/complexity red flags in the
sections this plan phase read). None of `_evaluate_tasks_packages_guard`,
`_evaluate_composed_tasks_packages_guard`, `_evaluate_composed_tasks_terminal_guard`,
`_evaluate_tasks_finalize_guard`, `_check_requirement_mapping_ready`, or `plan_mapping`
is within reach of the repo's complexity ceiling (15) — each is a short, linear sequence
of guard checks; `radon cc` was run against the full `runtime_bridge_cores.py` and
`mission_finalize.py` files (not only the touched functions) during this plan-fix pass
and surfaced no other function at or above 15 among the files this mission touches
(`_run_bootstrap_loop` in `mission_finalize.py` reports `C (14)` — below ceiling, and
outside this mission's touched-function set — recorded here only so a reviewer does not
rediscover it and wonder why it wasn't named). This is an honest, now-verified
campsite-clean, not an invented one; if implementation discovers further real debt in
these files once editing them line-by-line, it folds it there and records it in the
tracer files per Standing Order 2.

## Targeted Test Surface

Per-WP/per-PR validation targets these directories (never the full `pytest tests/`,
reserved for post-merge mission-level validation and release-candidate verification per
the charter):

- `tests/specify_cli/test_requirement_mapping.py` — new pure-function unit tests for
  `find_bare_prose_requirement_ids` (Story 2 AC3's per-line skip rule, C-006's
  document-scoping, Story 5's fault-injection case).
- `tests/specify_cli/test_requirement_mapping_coord_surface.py` — existing coord-surface
  regression coverage; must stay green unmodified (Story 2 AC2).
- `tests/next/test_runtime_bridge_unit.py` — the CLI-native guard family
  (`_evaluate_tasks_packages_guard`/`_evaluate_tasks_finalize_guard`) and
  `_check_cli_guards` integration tests.
- `tests/runtime/test_bridge_cores.py` — the pure-core `evaluate_guards`/
  `_evaluate_composed_tasks_*_guard` fixtures (SC-007's content-and-order-identical
  pinning); new per-guard teeth tests (FR-010) land here.
- `tests/next/` (broader directory) — composition-dispatch integration
  (`test_runtime_bridge_composition.py` equivalents live under
  `tests/specify_cli/next/` — see next bullet) and the zero-WP-files /
  ≥1-WP-file-no-match configurations from Story 3's Independent Test.
- `tests/specify_cli/next/` — `test_runtime_bridge_composition.py`,
  `test_runtime_bridge_dispatch.py`: the composed-guard dispatch path
  (`_check_composed_action_guard`, `_dispatch_via_composition`) this mission's C-009
  finding depends on staying correctly wired.
- `tests/runtime/` (broader directory, `fast-tests-next`'s own scope) —
  `_bridge_oracle.py`/`fixtures/` if new fixture data is added there instead of a bespoke
  `tests/fixtures/` path (implementation decision, not fixed by this plan).
- New: a corpus-ratchet test (module TBD by implementation, suggested
  `tests/architectural/test_bare_prose_corpus_ratchet.py` to sit beside the existing
  `test_ratchet_baselines.py` precedent) plus its committed fixture (suggested
  `tests/fixtures/bare_prose_corpus_baseline.json`).
- New (or extended): CLI-command-level tests for
  `src/specify_cli/cli/commands/agent/mission_finalize.py` and
  `tasks_map_requirements.py`/`tasks_mapping_core.py` — wherever those commands'
  existing test files already live (this plan phase did not exhaustively enumerate
  them; implementation locates via `git grep -l mission_finalize tests/` /
  `git grep -l plan_mapping tests/` before adding new test files, per the charter's
  "use canonical sources" rule — do not create a parallel test file if an existing one
  already covers the command).

## PR Shape

**Base: `op/3394-requirement-citation-scope`** (not `main`).

Justification: this mission's diff, if based on `main`, would carry #3395's entire
~863-line unreviewed parser rewrite as part of *this* mission's PR — making the PR
unreviewable in isolation (a reviewer cannot tell #3395's diff from #3396's diff) and
attributing #3395's un-landed risk to this mission's review surface. Basing on
`op/3394-requirement-citation-scope` keeps this mission's PR diff to *only* the
bare-prose-detection changes; GitHub's PR UI auto-retargets the PR to `main` once #3395
merges (standard GitHub behavior for a PR whose base branch is deleted/merged), at which
point the diff view becomes the union automatically and correctly — no manual rebase
needed for that specific transition. This is the documented, deliberate operator
decision already recorded in spec.md's Clarifications (accepted consequence: this
mission eats a rebase if #3395's shape changes before merge — see next section).

One PR per mission (charter default) — no split into multiple PRs.

## #3395 Churn Risk

The pinned base is `ab15225ea`. If #3395 changes shape (force-push, additional review
commits, a rewritten function signature) before this mission merges:

1. `origin/op/3394-requirement-citation-scope`'s tip moves past `ab15225ea`.
2. This mission's branch (spec-authoring and plan-phase commits above `ab15225ea` — see
   "Baseline Capture" above for the fixed-ref accounting rather than a literal count,
   since the live count changes with every planning/review-fix commit — soon plus
   implementation commits) must be rebased onto the new tip.
3. Because this mission's new code is additive (a new function, a new fact object, new
   guard-body statements) rather than a modification of #3395's own changed lines, the
   *expected* rebase shape is a clean, non-conflicting fast-forward-style rebase in the
   common case — but this is **not guaranteed**: if #3395's rewrite renames
   `_declared_ids`/`_requirement_named_sections`/`_DECLARED_ID_PATTERNS` or changes
   `parse_requirement_ids_from_spec_md`'s return shape, this mission's FR-001 predicate
   (which calls those symbols directly) breaks and needs a real rebase-time fix, not a
   mechanical replay.
4. **Absorb story**: whoever executes the rebase re-runs the full targeted test surface
   (above) after rebasing, treats any newly-red test the same way as a freshly
   discovered pre-existing failure would be treated (charter Pre-existing Failure
   Reporting Rule does not directly apply here since these would be *this mission's own*
   post-rebase regressions, not pre-existing ones — they must be fixed, not filed), and
   re-verifies the ATDD red-first commit is still RED against the *new* `ab15225ea`-equivalent
   tip before re-verifying GREEN on the rebased implementation tip.
5. This is an accepted, explicitly disclosed consequence (C-005) of the operator's
   "branch now" decision — not a defect in this plan.

## The False-Positive Fixture (FR-005 / Story 4 AC3, SC-006)

Precedent: `tests/architectural/_baselines.yaml` + `tests/architectural/test_ratchet_baselines.py`
(read directly for this plan) — a committed YAML mapping test-name → integer ceiling,
compared against a live count every run; growth fails, shrinkage warns (informational);
per-PR edit policy requires a `# justification:` comment on any growth. This mission's
fixture follows the same *shrink-only, non-vacuous, committed* shape but needs a
**signature**, not a count (FR-005: "per-spec detector signatures... committed"), because
a bare count could not distinguish "detector correctly still flags the same 9 specs" from
"detector now flags 9 *different* specs" (a real regression a count-only ratchet would
miss — the non-vacuity property Standing Order 5 requires).

**Fixture shape** (`tests/fixtures/bare_prose_corpus_baseline.json`, suggested path):
a JSON array of `{"spec_path": "kitty-specs/.../spec.md", "flagged_ids":
["FR-021", ...]}` entries — exactly the 9 specs FR-005 already measured and named in
spec.md, re-verified at implementation time against the then-current corpus (the
Independent Test's own requirement).

**Ratchet test** (`tests/architectural/test_bare_prose_corpus_ratchet.py`, suggested):
walks `kitty-specs/*/spec.md`, runs the live `find_bare_prose_requirement_ids` against
each, and asserts:
1. Every spec **not** in the fixture has an empty live result (no newly-flagged spec).
2. Every spec **in** the fixture has a live `flagged_ids` set that is a subset of (or
   equal to — never a superset of) the fixture's recorded set (shrink/stay-equal only).

**Non-vacuity requirement (PLAN-VERIFY-001, load-bearing).** Charter Standing Order 5
requires "a NON-VACUOUS call-site gate (concrete floor + self-mutation test +
shrink-only allowlist); a gate-unmask cannot self-validate" — cite
`architectural-gate-non-vacuity` here alongside the `frozen-baseline-shrink-only-ratchet`
citation above, which covers only the shrink-only-allowlist half. Assertions 1+2 alone
are vacuous against a fully-collapsed, always-empty detector: a detector that returns
`[]` for every spec passes both trivially (empty is empty for non-fixture specs; the
empty set is a subset of any recorded set for fixture specs), reproducing inside this
mission's own regression safety net the exact "counts 0 and calls it clean"
silent-success failure class this mission exists to fix. The ratchet test therefore
**also** asserts, in the same test module:
3. **Concrete floor**: for each of the 9 fixture specs, the LIVE `flagged_ids` result is
   **non-empty** (`assert live_ids`, not only `assert live_ids <= recorded_ids`) — the
   floor that (1)+(2) alone do not provide; a collapsed detector fails this assertion for
   all 9 specs simultaneously, where it would pass (1)+(2) vacuously.
4. **Self-mutation ("teeth") test**: a dedicated test (same module, or
   `test_bare_prose_corpus_ratchet_teeth.py` alongside it) monkeypatches/stubs
   `find_bare_prose_requirement_ids` to always return `[]` and asserts the ratchet test
   above then **fails** (not errors, not skips) — proving the gate itself is
   load-bearing, not merely present.

This is deliberately **not** a live-scored percentage re-run — it never computes "9/368"
at CI time; it only asks "did the flagged *set* grow, and is it still non-empty where it
should be." A future, unrelated mission adding a new `kitty-specs/*/spec.md` cannot flip
this gate red by merely existing (satisfies check 1 vacuously as long as its own spec has
no bare-prose token — which, per Story 6 AC2, this mission's *own* spec.md already
satisfies by construction). Growth requires a deliberate re-snapshot with a recorded
reason, mirroring `_baselines.yaml`'s per-PR edit policy exactly.

## Reflexivity (Story 6 / FR-009)

This plan.md documents, per FR-009: at plan-authoring time (2026-08-14), this plan phase
did not enumerate every currently-in-flight mission's spec.md for bare-prose shapes
(that census is the implementing WP's job, closer to merge time, since the in-flight set
changes daily) — but it **does** confirm, per Story 6 AC2, that this mission's own
spec.md contains zero bare-prose requirements: every FR/NFR/C row in
`kitty-specs/bare-prose-requirements-uncounted-01KZYV3C/spec.md` is a proper markdown
table row (`| FR-001 | Title | ... |`), the declared shape, by construction — verified
directly by re-reading the Requirements section during this plan phase. The implementing
WP's PR description must run the corpus scan against every `kitty-specs/*/spec.md`
belonging to a mission not yet merged at merge time, name any that would newly block, and
state the remediation (rewrite into a declared shape — no code-level grandfathering, per
the spec's own stated policy).

## Project Structure

### Documentation (this mission)

```
kitty-specs/bare-prose-requirements-uncounted-01KZYV3C/
├── spec.md                    # Input (settled, do not touch)
├── plan.md                    # This file
├── tracer-approach.md         # Appended, not recreated
├── tracer-design-decisions.md # Appended, not recreated
├── tracer-tooling-friction.md # Appended, not recreated
└── tasks.md                   # Phase 2 output (/spec-kitty.tasks — not this phase)
```

No `research.md`/`data-model.md`/`quickstart.md`/`contracts/` are needed: this mission
has no new data model (it adds pure functions over an existing text format) and no new
external contract (see "Contracts" above — all preserved unchanged).

### Source Code (repository root)

Single project (Python CLI + library) — Option 1 of the template, concretized to the
actual touched paths (no unused options retained):

```
src/
├── specify_cli/
│   ├── requirement_mapping.py                    # FR-001: new predicate
│   ├── cli/commands/agent/
│   │   ├── mission_finalize.py                   # FR-002 sibling wiring (finalize-tasks)
│   │   └── tasks_mapping_core.py                 # FR-002 sibling wiring (map-requirements)
│   └── mission_step_contracts/executor.py         # read-only reference; C-009, unmodified
└── runtime/next/
    ├── runtime_bridge_cores.py                    # new fact object + pure evaluator + 4 guards
    ├── runtime_bridge.py                          # residual gather step (spec.md read)
    ├── runtime_bridge_io.py                       # new status_facts key
    └── runtime_bridge_composition.py              # read-only reference; C-009, unmodified

tests/
├── specify_cli/
│   ├── test_requirement_mapping.py
│   └── test_requirement_mapping_coord_surface.py
├── specify_cli/next/
│   ├── test_runtime_bridge_composition.py
│   └── test_runtime_bridge_dispatch.py
├── next/
│   └── test_runtime_bridge_unit.py
├── runtime/
│   └── test_bridge_cores.py
├── architectural/
│   └── test_bare_prose_corpus_ratchet.py          # new (suggested path)
└── fixtures/
    └── bare_prose_corpus_baseline.json            # new (suggested path)
```

**Structure Decision**: single project, no new top-level directory. All new code lands
inside existing packages/modules named above; the only new *file* is the committed
corpus fixture (a data file, not source) and its ratchet test.

## Complexity Tracking

*Fill ONLY if Charter Check has violations that must be justified*

One pre-existing complexity-ceiling violation was found (`_validate_requirement_mapping`,
16 > 15 — see "Charter Check" and "Campsite-Clean Scope," PLAN-GOV-001), but it is
**remediated** in the campsite-clean FIRST commit, not shipped-and-justified — so this
table, which is for violations accepted *with* a justification, is left empty, honestly,
rather than populated to satisfy a template requirement.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| — none — | — | — |

## Implementation Concern Map

### IC-01 — New bare-prose predicate (pure function)

- **Purpose**: Add `find_bare_prose_requirement_ids` to `requirement_mapping.py`,
  implementing the per-line/document-scoped algorithm ("Architecture" above), with its
  measured-rate docstring (FR-005: 9/368 = 2.45% document-scoped, 139/368 = 37.77%
  section-scoped, both recorded, zero true positives, corpus size + measurement date).
- **Relevant requirements**: FR-001, FR-004, FR-005, C-001, C-006, C-008, NFR-001,
  NFR-006.
- **Affected surfaces**: `src/specify_cli/requirement_mapping.py`.
- **Sequencing/depends-on**: none — this is the foundation every other concern wires
  into.
- **Risks**: getting the per-line skip rule wrong would either reopen #3394 (doc-wide
  fallback) or reintroduce the description-column false-positive class #3395 already
  measured and rejected. Story 2 AC3 and the corpus fixture (IC-06) are the load-bearing
  regression guards.

### IC-02 — `spec-kitty next` wiring (fact-port + four guards)

- **Purpose**: Thread the new signal through `runtime_bridge_io.py` →
  `runtime_bridge_cores.py` (`BareProseRequirementFacts` +
  `_evaluate_bare_prose_requirements`) → the four guard functions, ordered before the
  `_tasks_dir_ready` short-circuit in each.
- **Relevant requirements**: FR-002, FR-003, FR-010, NFR-002, NFR-005, C-007.
- **Affected surfaces**: `src/runtime/next/runtime_bridge.py`,
  `runtime_bridge_io.py`, `runtime_bridge_cores.py`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: this is the mission's central, named risk (repeating the
  `3823f2b00`-shaped dead-path). Mitigated by the explicit ordering fix and the
  per-guard teeth tests (IC-05). Each guard reads the new `status_facts` key via
  `.get(..., ())` (PLAN-ARCH-001, see the FR-002 code sketch above), never a bare
  subscript, so pre-existing test fixtures/snapshots that do not yet populate the key
  degrade instead of raising `KeyError` — `tests/runtime/test_bridge_cores.py`'s
  `_snapshot()` should still be updated to set the key by default as a fixture-accuracy
  hygiene item, not a blocking prerequisite of this concern.

### IC-03 — `finalize-tasks` / `map-requirements` CLI wiring

- **Purpose**: Wire the same predicate into `mission_finalize.py::_validate_requirement_mapping`
  and `tasks_mapping_core.py::plan_mapping`, surfacing bare-prose ids as a distinct
  payload field alongside the existing missing/unknown/unmapped fields.
- **Relevant requirements**: FR-001 (Story 1 AC1/AC2), FR-004.
- **Affected surfaces**: `src/specify_cli/cli/commands/agent/mission_finalize.py`,
  `tasks_mapping_core.py`.
- **Sequencing/depends-on**: IC-01, and the campsite-clean FIRST commit's
  `_validate_requirement_mapping` extraction (see "Campsite-Clean Scope" above,
  PLAN-GOV-001) — IC-03's new branch lands against the already-decomposed helper split,
  never adding a branch to the pre-extraction 16-complexity function.
- **Risks**: low — both call sites already have direct access to `spec_content`; the
  main risk is payload-shape drift between the two CLI commands' JSON output (mitigate
  by using the same field name, `bare_prose_requirement_ids`, in both).

### IC-04 — Fail-loud contract (Story 5 / FR-007 / FR-008)

- **Purpose**: Ensure every call site above (IC-02, IC-03) wraps the detector call so an
  exception becomes an explicit blocking failure, never a swallowed "0 uncounted."
  Add the fault-injection test proving it.
- **Relevant requirements**: FR-007, FR-008, NFR-002.
- **Affected surfaces**: the same files as IC-02/IC-03 (the try/except wrapper at each
  call site), plus new tests.
- **Sequencing/depends-on**: IC-01, IC-02, IC-03 (wraps their call sites).
- **Risks**: conflating this with the existing advisory's swallow-and-log contract —
  explicitly guarded against by keeping the two code paths textually separate (no shared
  wrapper function between `_log_requirement_extraction_warnings_safely` and the new
  detector's error handling).

### IC-05 — Per-guard teeth tests (FR-010 / NFR-005 / Story 3 AC4)

- **Purpose**: One synthetic-reversion test per guard function actually wired in IC-02
  (up to four), each failing when that specific guard's wiring alone is reverted.
- **Relevant requirements**: FR-010, NFR-005.
- **Affected surfaces**: `tests/runtime/test_bridge_cores.py` (pure-core guards),
  `tests/next/test_runtime_bridge_unit.py` (CLI-native integration),
  `tests/specify_cli/next/test_runtime_bridge_composition.py` (composed-dispatch
  integration).
- **Sequencing/depends-on**: IC-02.
- **Risks**: a single existence-proof test masquerading as coverage for all four guards
  — explicitly disallowed by FR-010's own text; each guard needs its own test.

### IC-06 — Frozen corpus fixture + ratchet (FR-005 / SC-006)

- **Purpose**: Commit the 9-spec baseline signature and the shrink-only, **non-vacuous**
  ratchet test — shrink-only assertions (1)+(2) PLUS the concrete-floor assertion (3) and
  the self-mutation teeth test (4) specified in "The False-Positive Fixture" section
  above (PLAN-VERIFY-001; charter's `architectural-gate-non-vacuity` doctrine, not only
  `frozen-baseline-shrink-only-ratchet`).
- **Relevant requirements**: FR-005, SC-006.
- **Affected surfaces**: new `tests/fixtures/bare_prose_corpus_baseline.json`, new
  `tests/architectural/test_bare_prose_corpus_ratchet.py`.
- **Sequencing/depends-on**: IC-01 (needs the live detector to snapshot against).
- **Risks**: snapshotting at the wrong point (before IC-01 is finalized) bakes in a
  stale signature; sequence this concern last among the detector-adjacent work.

### IC-07 — False-negative sample (Story 4 AC4, informational)

- **Purpose**: A throwaway measurement (not shipped production code) that runs the
  corpus through a heading predicate broadened to also match `"constraint"`, records how
  many sampled specs contain a genuine undetected bare-prose `C-XXX`/`NFR-XXX` item
  (false-negative side), and additionally records — re-verified against the
  then-current corpus — the broadened-predicate false-positive result already measured
  during this plan's PLAN-GOV-002 fix pass (see "C-008 decision" above: 5/368 = 1.36%
  newly flagged, zero true positives), so both figures live together in the detector's
  module docstring, following FR-005's own re-verification precedent.
- **Relevant requirements**: Story 4 AC4, C-008 (disclosure half of the decision).
- **Affected surfaces**: a script/test under `tests/` or `scripts/`, output recorded in
  the detector's module docstring alongside the FP rate (does not touch
  `_is_requirement_heading` in production code — C-008's option (b) is explicit that
  production scope stays narrow).
- **Sequencing/depends-on**: IC-01.
- **Risks**: none functional (informational only) — the risk is scope creep if an
  implementer mistakes this measurement helper for a mandate to broaden production
  scope; C-008's decision above forecloses that reading explicitly.

### IC-08 — Architectural import-boundary test (C-007)

- **Purpose**: Pin `runtime_bridge_cores.py`'s import set so a future cross-package
  import regresses loudly.
- **Relevant requirements**: C-007.
- **Affected surfaces**: new `tests/architectural/test_bridge_cores_import_boundary.py`.
- **Sequencing/depends-on**: none (can land any time; suggested early, alongside IC-01,
  since it protects every subsequent concern's edits to `runtime_bridge_cores.py`).
- **Risks**: low; a mechanical AST-walk test.
