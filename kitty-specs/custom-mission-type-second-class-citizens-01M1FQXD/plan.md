# Implementation Plan: Custom mission types are second-class citizens

**Branch**: `fix/custom-mission-type-second-class-3830` | **Date**: 2026-09-02 | **Spec**: `kitty-specs/custom-mission-type-second-class-citizens-01M1FQXD/spec.md`
**Input**: Feature specification from `/kitty-specs/custom-mission-type-second-class-citizens-01M1FQXD/spec.md`

**Note**: This plan resolves the five design questions spec.md's "Deferred to Plan Phase"
section explicitly handed to this phase (ruling #2, `reviews/spec.ruling-2.md`), and the
#3831 go/split research checkpoint (Decision 2, C-005). Full schema-comparison evidence
for the SPLIT verdict lives in `research.md`; this document states the decisions and their
consequences.

## Summary

Three defects share one root cause — spec-kitty's own runtime machinery hardcodes
`software-dev`-shaped assumptions at three independent seams (composition dispatch,
the legacy mission loader, the plan-substantive gate) — and this mission fixes all three
on their existing, disjoint file sets (C-003) without inventing a fourth mechanism. The
approach at each seam is **extend the existing single-canonical-authority pattern by one
parameter**, not add a new one:

1. **Composition dispatch (#3830)** — `_composition_dispatch_inputs` already knows how to
   resolve `profile_hint` via `_resolve_step_agent_profile`/`PromptStep.agent_profile`
   (the FR-008-mandated canonical path); the bug is that this call is *skipped* precisely
   when the dispatched action is a member of the mission type's own `action_sequence`
   (`runtime_bridge_composition.py:303-336`, the early `return None, None` at the point
   `action in action_sequence` is true). The fix removes that misplaced early return so
   the canonical resolution path always runs, and separates "resolution genuinely failed"
   from "resolution succeeded, blank the hint" in the `except Exception: pass` around it.
2. **Mission loader (#3831)** — split per the research checkpoint (see §SPLIT below):
   the org-tier lookup (FR-004) is descoped as a schema-bridging project; the loud-fallback
   fix (FR-005) proceeds unconditionally by making `get_mission_for_feature`'s existing
   `warnings.warn` fallback CLI-visible.
3. **Substantive gate (#3832)** — `_has_substantive_technical_context` already implements
   the right *shape* of check (primary field AND a peer field, tolerant of bullet
   markers) for one mission type. The fix generalizes it to be parameterized by a
   per-type field declaration instead of hardcoding `## Technical Context` +
   `**Language/Version**`, adds one new detector for the one genuinely new shape (nested
   `###` headings), and extends the existing table-row detector (`_has_substantive_fr_row`)
   to arbitrary tables instead of only `FR-###` rows.

## Technical Context

**Language/Version**: Python 3.11+ (repo-wide requirement, charter Technical Standards)
**Primary Dependencies**: typer (CLI), pydantic (`MissionConfig`/`ResolutionResult`
validation), pytest (test surface); no new third-party dependency is introduced by any of
the three fixes
**Storage**: N/A — no persistence change; all three fixes are read-path/dispatch-logic
changes over existing files (`.kittify/`, `packs/built-in/missions/*/templates/*.md`)
**Testing**: pytest, targeted test surfaces per fix site (see §Gate Set) — `tests/next/`
and `tests/runtime/` for #3830, `tests/specify_cli/` (`test_mission*.py`) for #3831,
`tests/specify_cli/missions/test_substantive_gate_formats.py` and
`tests/specify_cli/cli/commands/agent/` (`mission_setup_plan`/`mission_check_prerequisites`
suites) for #3832
**Target Platform**: spec-kitty CLI, cross-platform (Linux/macOS/Windows 10+ per charter)
**Project Type**: single project — this mission adds no new package, only extends existing
modules on their existing seams
**Performance Goals**: N/A beyond the charter's standing <2s CLI-operation budget; none of
the three fixes changes I/O volume (composition dispatch already calls
`resolve_mission_type_context`; the mission loader already reads two tiers; the
substantive gate already reads one file) — a per-type field declaration (§Decision 1) adds
an in-memory dict lookup, not new I/O
**Constraints**: public repository (C-009) — no local paths/usernames in any artifact;
smallest-viable-diff + locality-of-change (charter change-scope reconciliation) — each fix
stays inside its named file set (C-003); complexity ceiling 15 (ruff C901/Sonar S3776,
see §Complexity Ceiling)
**Scale/Scope**: three FR clusters (FR-001-003, FR-004/FR-005, FR-006/FR-008), four
built-in mission types plus any custom type, no schema/data migration

## Architecture — Seam Mapping

Per the charter's single-canonical-authority principle and C-001/C-002, no new pattern or
dependency is invented anywhere this mission touches — each fix extends a seam that
already exists and already does the right thing for at least one case:

| Fix | Seam | Existing canonical authority | What changes |
|---|---|---|---|
| #3830 (FR-001-003) | Composition dispatch | `PromptStep.agent_profile` via `_resolve_step_agent_profile` (C-001) is already the FR-008-mandated resolution path; `_ACTION_PROFILE_DEFAULTS` (`executor.py:68-71`) is already built-ins-only by its own comment; the module's own `logger` (`runtime_bridge_composition.py:101`, `logging.getLogger("runtime.next.runtime_bridge")`, already used via `logger.warning`/`logger.exception` elsewhere in this file) is the existing diagnostic-surface mechanism | Remove the misplaced early `return None, None` that currently *bypasses* the canonical path for a mission type's own actions; in the surrounding `except Exception`, log (not silently pass) a genuine `resolve_mission_type_context` failure via that same module logger — see §ATDD-First's FR-002 row for the concrete before/after signal |
| #3831 (FR-005 only; FR-004 descoped) | Mission loader | `get_mission_for_feature`'s existing `warnings.warn` fallback (`mission.py:802`) already signals *something* — it just doesn't reach a normal operator; the one CLI call site, `mission_type.py`'s `current` command (`current_cmd`), already has a loud CLI-error pattern for this exact call (`console.print(f"[red]Error:[/red] {exc}")`, `mission_type.py:190-197`, using the shared `specify_cli.cli.console.console` rich console) | Named mechanism and scope: see the elaboration below this table, without altering which mission gets selected (NFR-002) |
| #3832 (FR-006/FR-008) | Substantive gate | `_has_substantive_technical_context`'s primary-AND-peer combination rule (already correct) and its FR-013 bullet-tolerant peer-field regex; `_has_substantive_fr_row`'s table-row detector (already correct for `FR-###` rows) | Both existing detectors are **generalized by parameter** (heading, primary label, table-row shape) instead of reimplemented; one genuinely new detector (nested `###` heading) is added for the one shape neither existing detector covers; `is_substantive`'s signature grows a mission-type/template-descriptor parameter for `kind="plan"` callers only |

**FR-005's loud-signal mechanism, named concretely**: `mission.py` (the fallback's fix
site) imports no `rich`/`console`/`typer` dependency today — verified by reading its full
import block; `warnings.warn` is the module's only signal mechanism. `get_mission_for_feature`
has exactly three call sites (verified by grep): `mission_type.py:190` (a `typer` CLI
command — the `current` command/`current_cmd`), `acceptance/__init__.py:1206`, and `core/worktree.py:664`
(neither of the latter two is itself a CLI command; both are library/core code invoked from
deeper in the call graph, sometimes non-interactively). Rather than inventing a new
console/logging bridge inside `mission.py` for all three callers, this fix reuses the
concrete, already-existing pattern the one CLI call site already applies to the two
sibling exceptions raised from the same `try` block right next to it
(`mission_type.py:190-197`: `console.print(f"[red]Error:[/red] {exc}")` for
`MissionNotFoundError`, `console.print(f"[red]Failed to load active mission:[/red] {exc}")`
for `MissionError`, both via the shared `specify_cli.cli.console.console` rich console
already imported into that module). **Decision**: the CLI call site becomes able to detect
that its own `get_mission_for_feature` call fell back (whether by capturing the existing
warning around that one call, or by `mission.py` exposing the already-known fallback fact
alongside its unchanged `warnings.warn` — an implementation-level choice for the WP, not a
plan-level one) and, when it did, prints a loud message through that same console object
it already uses for the two sibling exceptions right next to this call. `mission.py`'s own
`warnings.warn` stays exactly as it is today (unchanged, still the underlying signal for
every caller) — this fix adds a loud *surface* only at the one call site spec.md's "visible
in normal CLI operation" language
(User Story 2 AC2, SC-004) actually describes: an interactive `spec-kitty` CLI command's
stdout. `acceptance/__init__.py:1206` and `core/worktree.py:664` are explicitly **out of
scope** for the loud-CLI-surface half of this fix — they are not CLI command modules, they
have no console object to print through today, and inventing one for them would be
new-mechanism work spec.md's FR-005 does not ask for; they keep receiving the unchanged
`warnings.warn` signal exactly as before. This keeps the fix a parameterization/reuse of an
already-existing, already-in-scope console pattern (C-001/C-002's reuse-before-invent
principle, applied to this seam), not an invented one.

No FR in this mission adds a fourth org-tier-walking mechanism, a second profile-resolution
authority, or a second placeholder-stripping strategy — see Decisions 1-5 below for how
each seam's generalization stays a parameterization of existing code, not new code with
new failure modes.

---

## Deferred Design Decisions (spec.md's five open questions)

Per ruling #2, these are design decisions with rationale, not restated open questions and
not literal algorithms/regex. Each closes one bullet of spec.md's "Deferred to Plan Phase"
list.

### Decision 1 — Which section(s) a mission type's template designates, and how that is determined

**The generalization**: "the substantive check's target" is not always one shared
container section. `software-dev`/`documentation` share one shape (a single
`## Technical Context` heading holding all fields as bold-field lines); `research` and
`plan` do not — their fields live under independently-named headings, at `##` or nested
`###` depth, in different content shapes per field (verified in `research.md` §R4.1).
These four shapes are **not mutually inferable from raw markdown** without already knowing
which mission type produced the document — a `## Problem Decomposition` heading and a
`## Research Context` heading look structurally identical to a naive scanner; only the
per-type template tells you which fields live under which heading and in which shape.

**Decision**: a mission type's field layout — which heading(s) hold which named field, at
what depth, in what shape (bold-field list / table / nested-heading), and — for a
bold-field-list field specifically — whether its value is written inline after the colon
or in a bulleted sub-list on the lines below the label (see Decision 3(a)'s value-capture
extension for `documentation`'s `Build Commands`) — is itself **template-derived metadata
resolved once per mission type**, not re-derived by scanning arbitrary structure at check
time. This declaration is obtained from a small, explicit
per-type table checked into the fix, co-located with (and reviewed alongside) the template
file it describes — so a future edit to a template's field layout is a two-line diff in
the same PR, not a silent drift between template and declaration. It is explicitly **not**
re-parsed from the template's own prose/comments at runtime — ruling #2 already flagged
prose-inference as "a second, fragile inference layer," and a hand-maintained declaration
that ships in the same commit as the template it describes avoids exactly that failure
mode.

**Charter justification**: this does not create a second authority competing with the
template. The template remains the sole source of truth for *what fields exist and what
they mean* (an author changes the template, the mission type's plan requirements change).
The declaration is a thin index onto that authority — *where* to look and *what shape* to
expect — analogous to how `_ACTION_PROFILE_DEFAULTS` is a thin built-ins-only index onto
the canonical `PromptStep.agent_profile` authority rather than a second profile-resolution
system (C-001's precedent). If the declaration and the template it describes ever
disagree (a template edit lands without updating its declaration entry), that is a defect
in the declaration, caught the same way the built-in `_ACTION_PROFILE_DEFAULTS` table is
kept honest today — by the non-vacuity test plan in §Architectural Gate Non-Vacuity below
(a template change without a matching declaration update shows up as a newly-failing
positive fixture, not a silent pass).

**Reconciling `research`'s checked field count against spec.md's three-name list**:
spec.md's Decision 3 (BINDING) and NFR-004 both name three parallel fields for `research`
— "Research Context, Methodology, Data Sources" — because that is the vocabulary the
template's own top-level headings use. Read directly against
`packs/built-in/missions/research/templates/research-plan-template.md`, `## Research
Context` (L9) carries its own bold-field content (`**Research Question**:` at L11 and
peers), but `## Methodology` (L22) does not: its immediate body before the first nested
`###` subheading is empty — it is purely a grouping container for `### Research Design`
(L24), `### Data Sources` (L56), and `### Analysis Framework` (L73), each independently
named. "Methodology" therefore names a *section*, not a *field with its own checkable
content* — there is no bold-field line or table row directly under `## Methodology` for a
detector to check, by construction of the template itself, not by an oversight in this
design. The declaration's checked set for `research` is consequently **two** fields, not
three: **"Research Question"** (Research Context's own primary bold field — Decision 2
already establishes that the primary field lives inside a named heading, not the heading
name itself) as primary, and **"Data Sources"** (the one nested child of Methodology that
this design targets by name — see Decision 3(c)'s sub-shape (c-ii) below) as peer. This is
not a narrowing of spec.md's field list to "a convenient subset" (the anti-subset warning
NFR-004 states) — it is a resolution of *which of the three named headings actually
carries checkable content*, stated here explicitly rather than picked silently, mirroring
the correction ruling #1 already required when this mission's own spec phase over-claimed
`plan`'s field shapes. If this reconciliation is judged unacceptable, spec.md's Decision 3/
NFR-004 field list itself needs correcting before the plan can be treated as having settled
this deferred question; this plan proceeds with the two-field resolution stated above.

**Why the peer field is `Data Sources`, not a cheaper same-container alternative**:
`## Research Context` itself carries five other bold-field lines beside the primary
(`Research Type`, `Domain`, `Time Frame`, `Resources Available`, `Key Background`) that
would satisfy the AND/OR combination rule using only the already-generalized shape-(a)
detector (Decision 3(a)) — zero new detection work, versus the one genuinely new
sub-shape (c-ii) that `Data Sources` requires. That cheaper substitution was considered
and rejected, for two binding reasons, not a hunch: (1) spec.md's Decision 3 (BINDING)
names `research`'s scaffolded fields as "Research Context, Methodology, Data Sources" and
states the check "uses" those three "as the substantive-content criterion" — `Data
Sources` is one of only two of those three names (alongside `Research Context`) that
carries checkable content once `Methodology`'s own reconciliation above is applied, and
NFR-004 separately requires the checked set to cover "ALL of their own
actually-scaffolded fields — not a convenient subset." Quietly dropping `Data Sources` in
favor of an in-Research-Context field spec.md's Decision 3 never names, purely because it
is cheaper to detect, would itself be the "convenient subset" NFR-004 forbids — it
substitutes an unnamed field for a spec.md-named one for implementation-cost reasons, not
because the named field lacks checkable content (it does have checkable content, per this
Decision's own reconciliation above). (2) This is not a fresh ambiguity for the plan phase
to resolve however is cheapest: ruling #1 (`reviews/spec.ruling.md`, SPEC-FRESH2-001,
severity 4, UPHELD) already rejected narrowing `plan`'s checked-field set to its two
table-shaped fields for exactly this kind of implementation convenience ("arbitrary
partial coverage, justified by an implementation convenience... is the check that cannot
fail' class this repo's own standing orders exist to prevent") — the same reasoning bars
swapping `research`'s peer away from a spec.md-named field to a cheaper unnamed one here.
Ruling #1 also explicitly anchored `research`'s `Data Sources` to the same nested-heading
detection `plan`'s `Decisions` needs ("`Decisions` needs the nested-heading scan already
being specified for research's `### Data Sources`... Extend that scan's scope; do not
invent a second one"), and ruling #2's carried-forward "Deferred to Plan Phase" list
(spec.md item 3) names nested third-level headings among the shapes this plan phase must
detect for `research` specifically. Sub-shape (c-ii)'s detector cost is therefore not a
plan-time invention this Decision could have avoided by picking a different field — it is
the already-anticipated consequence of spec.md naming `Data Sources` as one of
`research`'s three scaffolded fields. This plan keeps `Data Sources` as the peer field and
accepts the one bounded, already-scoped detector (Decision 3(c-ii)) that follows from it,
over a substitution that would silently narrow spec.md's own named field list for cost
reasons alone.

### Decision 2 — Primary field label and section heading: one axis, not two

Ruling #2 verified both the section heading (`## Technical Context`, hardcoded at
`_substantive.py:160-161`) and the primary field label (`**Language/Version**`, hardcoded
at `_substantive.py:171-172`) are independently hardcoded literals inside the same
function (re-verified this session — confirmed exact line spans and regex bodies).

**Decision**: both become per-type parameters resolved from the **same** per-type
declaration from Decision 1 — "where does the primary field live, and what is it called" —
rather than two independently-generalized literals with two separate generalization
mechanisms. Treating them as one axis matters because they are not independently
variable in practice: a mission type's primary field is always *some* field inside *some*
heading that the same declaration already names as that type's first-scaffolded field
(the primary-field rule from spec.md's AND/OR combination rule, unchanged — "the
template's FIRST scaffolded field is the primary"). Generalizing them separately would
risk exactly the failure ruling #2 caught the first time: parameterizing only the heading
while leaving the label hardcoded (or vice versa) produces a check that still cannot pass
for a type whose heading matches but whose label doesn't, or whose label matches but whose
heading doesn't. One declaration, read once, naming both together, closes that gap by
construction rather than by review vigilance.

### Decision 3 — Per-shape detection: generalize two existing detectors, add one new one

Three shapes need a detector (per `research.md` §R4.1's verified table):

- **(a) Bold-field list** (`software-dev`'s full Technical Context, `documentation`'s full
  Technical Context, `research`'s Research Context primary field, `plan`'s Scope —
  MoSCoW): **generalize the existing peer-field scan** in
  `_has_substantive_technical_context` (`_substantive.py:185-189`) by parameterizing the
  container heading and the primary-field label from Decision 1/2's declaration. This
  detector already tolerates a leading `-`/`*` bullet marker (FR-013/#1896) — that
  behavior carries forward unchanged.

  **Value-capture extension for `documentation`'s `Build Commands`**: unlike this shape's
  other bold fields (`Documentation Framework`, `Languages Detected`, `Output Format`,
  `Hosting Platform`), `Build Commands`' value is written as a bulleted sub-list on the
  lines *below* the label (`documentation-plan-template.md:24-28`), not inline after the
  colon — verified directly against the template this session. The existing/generalized
  shape-(a) value capture (`_substantive.py:186`, `(?P<val>[^\n]*)`) only reads text up to
  end-of-line, so a faithfully-populated `Build Commands` field reads as **empty**, not
  populated — this was PLAN-FRESH3-002's finding. **Decision**: extend shape-(a)'s own
  value-capture behavior to also cover this sub-list case, rather than invent a fourth
  shape or a second detector — when a bold field's same-line value is empty after
  placeholder-stripping *and* the per-type declaration (Decision 1) marks that field as
  sub-list-valued, treat the immediately-following bulleted lines (up to the next
  bold-field line or a blank-line-then-non-bullet boundary) as the field's value, subject
  to the same non-placeholder check already applied to inline values. This is the
  value-side counterpart to the label-side bullet tolerance FR-013/#1896 already added to
  this same detector — one detector, one new declared per-field flag, not a second
  detection mechanism. This keeps the fix inside Decision 3's own reuse principle below
  (generalizing an existing, already-correct code path) rather than growing the three
  shapes into four.

  `Generator Tools` (`documentation-plan-template.md:16-20`) has the **identical**
  bulleted-sub-list shape, verified directly against the template — but it is not in
  documentation's declared peer-field set (§Blast Radius, `research.md` §R4.1); that
  omission pre-dates and is independent of this fix, so it is left as-is here (Locality of
  Change). Because the value-capture extension above is declared per-field rather than
  per-shape-globally, no further detector work would be needed if a future revision adds
  `Generator Tools` to the checked set.
- **(b) Markdown table** (`plan`'s Problem Decomposition and Sequencing & Prioritisation):
  **generalize the existing table-row detector**, `_has_substantive_fr_row`'s table half
  (`_substantive.py:71-90`), which already knows how to find non-placeholder content in a
  data row's descriptive columns. Today it is anchored to rows literally prefixed
  `FR-###`; the generalization removes that anchor and instead checks whether *any* data
  row under the declared heading's table has non-placeholder content in its descriptive
  columns — the row-scanning and placeholder-checking logic is unchanged, only the
  row-selection predicate changes from "starts with `FR-`" to "is a data row of this
  table."
- **(c) Nested third-level heading** (`research`'s Data Sources under Methodology,
  `plan`'s Decisions/`### Decision D-1`): **one new detector**, because neither existing
  detector's shape applies here — a bold-field scan finds no `**Label**:` lines at the
  container level (the content is one level deeper, under its own heading), and a table
  scan finds no table. This shape is not one uniform rule, though: the two fields that need
  it have structurally different containers, so the detector dispatches on **two
  sub-shapes**, both nested-heading, distinguished by what the field's declared container
  actually is:
  - **(c-i) Repeatable instance** (`plan`'s Decisions): the field's own container (`##
    Decisions`) holds a set of repeatable, homogeneously-named `### Decision D-N`
    instances — the container heading IS the field, and every nested instance is an
    equally-valid occurrence of it. Substantive iff **at least one** `### Decision D-N`
    instance nested directly under `## Decisions` has non-placeholder content in its body —
    any one populated instance suffices, mirroring the same "at least one real thing, not
    every possible thing" intuition the AND/OR rule already applies at the field level.
  - **(c-ii) Specifically-named sibling** (`research`'s Data Sources): the field's declared
    container is NOT its own heading but a shared, differently-purposed parent (`##
    Methodology`) that also holds other, differently-named `###` siblings (`### Research
    Design`, `### Analysis Framework`) unrelated to this field. Substantive iff the ONE
    nested `###` heading whose label matches the declared field's own name (`### Data
    Sources`) — located by name, not merely by nesting depth under the shared parent — has
    non-placeholder content in its own body. A populated sibling (`### Research Design` or
    `### Analysis Framework`) does not satisfy this; the target IS `### Data Sources`
    itself, so its own body (not a further-nested heading inside it — it has none) is what
    is scanned.

  The per-type declaration (Decision 1) records which of these two sub-shapes applies to a
  given field — `plan`'s Decisions is declared (c-i); `research`'s Data Sources is declared
  (c-ii) — so the single nested-heading detector dispatches on a declared sub-shape
  parameter rather than guessing from structure at check time. This is the same distinction
  ruling #1's remediation already drew when it directed "extend that scan's scope, don't
  invent a second one" for `research`'s Data Sources and `plan`'s Decisions: one detector,
  parameterized by which of the two real nested-heading sub-shapes a field has — not two
  independent detectors, and not one rule blind to the difference between them (a single
  undifferentiated rule is exactly what would either always-fail for Data Sources, reading
  its own heading as the container with nothing further nested inside, or silently check
  the wrong sibling, reading Methodology as the container and accepting Research
  Design/Analysis Framework content in Data Sources' place). This is a decision about what
  "substantive" means for each sub-shape, stated as behavior, not as a parsing algorithm.

**Reuse principle, stated explicitly for the charter's reuse-before-invent standing
order**: two of the three shapes (bold-field list, table) are handled by **generalizing
existing, already-correct code paths** via new parameters; only the third (nested heading)
is genuinely new work. This is the smallest-viable-diff outcome available given the four
verified shapes — inventing a fourth, unified "detect anything" parser would be strictly
more code and more surface for the exact kind of false-pass/false-fail drift the charter's
architectural-gate-discipline standing order warns against, for no shape-coverage benefit
over parameterizing what already works. (a)'s own value-capture extension for
`documentation`'s `Build Commands` (above) is the same kind of generalization — a new
declared per-field flag on an existing detector, not a fourth shape or a second detector —
so this reuse principle still holds after that extension.

### Decision 4 — Placeholder-pattern coverage: extend the existing enumerated-literal style

`research-plan-template.md` and `plan-plan-skeleton.md`'s actual bracket-placeholder
vocabulary was read directly from both files this session (full list in `research.md`
§R4.2) — e.g. `[Primary question]`, `[Academic field or industry domain]`,
`[Sub-problem statement]`, `[Cluster name]`, `[SP-# or none]`, `[High/Low]`, `[Decision
title]`, `[Chosen option, stated plainly]`, `[Why this option wins]`, `[Alternative A]`,
`[Failure scenario]`. None of these overlap the existing 17-entry
`_PLACEHOLDER_PATTERNS` list (`_substantive.py:31-49`), which is entirely
software-dev/spec-shaped (`[NEEDS CLARIFICATION...]`, `[e.g., ...]`, `[FEATURE]`, etc.).

**Decision**: extend `_PLACEHOLDER_PATTERNS` with the **same conservative,
enumerated-literal style** — one pattern per actual bracket phrase these two templates
scaffold — rather than adopting a generic "any bracketed span is a placeholder" rule.

**Justification against NFR-005 non-vacuity** (both failure directions matter, not just
one): a generic bracket-strip rule risks the false-negative direction — real, substantive
content that legitimately contains a bracketed span (for instance, a citation like
"[Smith 2024]" typed into a genuinely-filled `Data Sources` field, or a literal `[SP-3]`
cross-reference inside prose the author wrote about sub-problem 3) would be stripped and
could make a truly-populated field read as empty, which is exactly the "makes real content
disappear" failure NFR-005 names. The existing enumerated style avoids this because it
matches only the *specific* scaffold phrases the templates ship, not the general shape
"anything in brackets." The narrow-coverage failure mode (scaffold placeholders reading as
"filled in") is the one the status quo already has for these two templates — extending the
list with the templates' real vocabulary, in the same style as the 16 existing entries,
closes that gap without opening the opposite one. This is also consistent with the
existing code's own stated rationale (`_substantive.py:27-30`: "Conservative on purpose:
matches the scaffolds shipped by the spec/plan templates without snagging real prose that
incidentally includes square-bracket text") — extending the enumeration is following that
existing precedent, not choosing a new one.

### Decision 5 — Call-site routing in `mission_setup_plan.py` and the `kind="spec"` non-extension

**Verified** (re-confirmed this session against `mission_setup_plan.py`): exactly two
`kind="plan"` call sites — `_commit_plan_if_substantive` (L794) and `setup_plan` directly
(L1230). Both already receive `plan_template: ResolutionResult` in scope
(`_resolve_plan_template`, L586, returns `ResolutionResult` with `.path`, `.tier`,
`.mission` — `src/charter/offering/resolver.py:62-65`) — `setup_plan` resolves it once
(L1215) and passes the *same* object into `_commit_plan_if_substantive` (L1238) as an
explicit parameter it already declares (L777).

**Decision**: `is_substantive`'s signature grows a parameter carrying the mission type /
resolved template descriptor for `kind="plan"` callers (`kind="spec"` callers are
unaffected — no signature-breaking change to the spec path). At the call-site level:
**thread `setup_plan`'s single upstream-resolved `plan_template` into
`_commit_plan_if_substantive` rather than having each site recompute or re-resolve
independently.** Concretely, both sites should pass the *same already-in-scope*
`plan_template` value into the now-mission-type-aware `is_substantive` call —
`_commit_plan_if_substantive` does not need a new resolution step because it already
receives `plan_template` as a parameter from its one caller.

**Justification (locality/smallest-viable-diff, not "seems nicer")**: `setup_plan`
computes `plan_template` exactly once and already threads it to both
`_scaffold_plan_template` and `_commit_plan_if_substantive`; extending that existing
thread to also reach the `is_substantive` call inside `_commit_plan_if_substantive`
requires zero new resolution logic — it is passing a value one hop further along a path
that already exists. The alternative (each call site independently re-resolving the
mission type/template) would add a second resolution call for no behavioral difference
today (both reads of the same file always agree), while introducing a path where they
*could* theoretically diverge if `_resolve_plan_template`'s inputs ever changed between
the two call points in a future edit — a divergence risk with no offsetting benefit. This
is the smaller diff and the smaller blast radius, so it wins under the charter's
change-scope reconciliation order (smallest-viable-diff picks the file set and edit size
first).

**`kind="spec"` non-extension (FR-008's reconciliation, documented not fixed)**:
`mission_check_prerequisites.py:364`'s guard
(`mission_type != "software-dev" or is_substantive(spec_file, "spec")`) is confirmed the
sole `kind="spec"` call site, routing to `_has_substantive_fr_row` (`FR-###` rows).
**Verified this session**: `packs/built-in/missions/research/templates/
research-spec-template.md` and `packs/built-in/missions/plan/templates/
plan-spec-skeleton.md` contain **zero** `FR-###` rows (`grep -n "FR-"` over both files:
no matches). This is the concrete reason the FR-006 template-derived approach does **not**
extend to the `kind="spec"` check in this mission: there is no FR-vocabulary in either
type's own spec template to derive required fields from, so a template-derived spec check
for these two types would have nothing to point at. `mission_check_prerequisites.py:364`
therefore stays **behaviorally unchanged** in this mission. This is a documentation task
in the WP shape that covers it (an inline code comment at the guard, recording exactly
this reasoning and citing spec.md's FR-008/C-... discussion), not a logic change — so the
next reader finds the reasoning at the point of confusion rather than mistaking the
omission for an oversight.

---

## #3831 Split Verdict — Consequence for Scope

**VERDICT: SPLIT.** Full schema-comparison evidence (field-by-field `MissionConfig` vs.
org-tier derivability table, live `resolve_mission_type_context` resolution evidence, and
the three-schema reconciliation problem) is in `research.md` §R1-R2 — this section states
only the consequence, per the assignment's instruction not to duplicate the evidence here.

- **FR-004** (org-tier lookup in `_mission_path_by_name`/`get_mission_for_feature`) is
  **descoped** from this mission. `research.md` §R3 records the tracked follow-up issue's
  title and one-paragraph scope for a human/later mission to file; this mission does not
  file it. The follow-up is explicitly **not** folded into #2660 (different scope, per
  spec.md's "Relationship to #2660" section — carried forward unchanged).
- **FR-005** (loud, CLI-visible fallback replacing the filtered `warnings.warn` at
  `mission.py:802`) proceeds **unconditionally** — spec.md states this FR "applies
  regardless of the FR-004 split outcome." This is real, bounded work in this mission's
  #3831-touching WP: change the fallback's visibility, not which mission is selected
  (NFR-002 — see §Blast Radius).
- **PR closure**: `Closes #3830`, `Closes #3832`, `Refs #3831` (never `Closes #3831` for a
  partial fix), plus the follow-up-issue reference from `research.md` §R3 once filed — per
  spec.md SC-006 and the charter's Issue Closure Linkage Rule.

---

## Blast Radius — What Must Not Regress

Per C-003, all three fix sites sit on hot paths every built-in type traverses. Explicit
per-type non-regression statement:

| Built-in type | Composition dispatch (FR-001-003, NFR-001) | Mission loader (FR-005 only, NFR-002) | Substantive gate (FR-006/FR-008, NFR-003/004/005) |
|---|---|---|---|
| `software-dev` | Resolves `profile_hint` via `_ACTION_PROFILE_DEFAULTS` exactly as before (has table entries) | Resolves via the existing two-tier walk, unchanged selection | Must still **fail** on missing/placeholder `Language/Version`, exactly as `_has_substantive_technical_context` does today (NFR-003) — verified by existing test coverage plus new template-derived-path tests |
| `research` | Resolves via `_ACTION_PROFILE_DEFAULTS` exactly as before (has table entries) | Unchanged selection | Must be checkable against its own fields (Research Question primary + Data Sources peer — Methodology has no checkable content of its own, see Decision 1's reconciliation note) — able to **pass** when faithfully populated and **fail** when scaffold-only (NFR-004/005) |
| `documentation` | Resolves via `_ACTION_PROFILE_DEFAULTS` exactly as before (has table entries) | Unchanged selection | Must be checkable against its own fields (Documentation Framework primary + any of Languages Detected/Output Format/Hosting Platform/Build Commands) — pass/fail both directions (NFR-004/005) |
| `plan` | **Different, pre-existing failure mode left untouched**: dispatching an action in `plan`'s own `action_sequence` still raises `StepContractExecutionError("No step contract found for mission/action plan/<action>")` — not `profile_hint is required`, not any newly-introduced behavior (User Story 1 AC4, SC-001a). Registering step contracts for `plan` is out of scope. | Unchanged selection | Must be checkable against ALL FOUR of its own fields (Problem Decomposition primary + at least one of Scope—MoSCoW/Sequencing & Prioritisation/Decisions) — pass/fail both directions (NFR-004/005) |
| Any custom type (e.g. `qa`) | Resolves via `PromptStep.agent_profile`/pack `agent-profile:` entries (the fix target) | Two-tier walk unchanged unless org-tier-only (FR-004 descoped — see loud-fallback instead) | Checkable against its own resolved plan template if one exists; fails closed if template is malformed/missing/unresolvable (Edge Cases) |

**Drift note carried forward from spec.md (User Story 1 AC4)**: `_should_dispatch_via_
composition`'s header comment and `_dn_composition_dispatch`'s docstring both claim
dispatch is "hard-guarded on `mission == 'software-dev'`" — verified stale; the real gate
is `action_sequence` membership for the resolved mission type, any type. An implementer
must not "fix" this fix to match the stale comment; if anything, the comment itself is a
candidate for a one-line correction as part of the FR-001 WP's own touched-area cleanup
(Boy Scout Rule). **Verified file location of each comment**: `_should_dispatch_via_
composition`'s header comment — the "C-008: dispatch is hard-guarded on mission ==
software-dev" line — lives at `runtime_bridge_composition.py:127`, inside the declared
#3830 file set. `_dn_composition_dispatch`'s docstring making the identical stale claim
lives at `runtime_bridge.py:1777-1779` — a **second file**, not in the declared #3830 file
set. This
is a small, explicitly-scoped, comment-only extension of that file set (§Project Structure
records it), not "no file-set growth" — see §Campsite-Clean Scope below for the corrected
statement.

---

## Campsite-Clean Scope

Per Standing Order #2, the mission opens with a distinct, behavior-preserving
campsite-clean commit before the functional change, folding only domain-matched debt near
the three fix sites.

- **`runtime_bridge_composition.py` and `runtime_bridge.py`**: the stale "hard-guarded on
  `mission == 'software-dev'`" comments on `_should_dispatch_via_composition`
  (`runtime_bridge_composition.py:127`) and `_dn_composition_dispatch`
  (`runtime_bridge.py:1777-1779`) (noted above) are domain-matched — they describe the
  exact function this mission changes, and leaving them stale after the fix would actively
  mislead the next reader about what the new code does. Correct them as part of the
  campsite-clean commit (comment-only, behavior-preserving). This is a small,
  explicitly-scoped **two-file** extension of the touched set — not the "strictly inside
  the touched file, no file-set growth" framing spec.md's own drift note used — justified
  by Boy Scout Rule + Locality of Change (both docstrings describe the exact
  composition-dispatch behavior this mission changes, just from two different modules that
  both participate in the same dispatch call chain). `runtime_bridge.py` is added to
  §Project Structure's file list below, annotated comment-only.
- **`_substantive.py`**: no pre-existing lint/complexity offender was found at the
  functions this mission touches (`_has_substantive_technical_context`,
  `_has_substantive_fr_row`, `is_substantive`) — each is well under the complexity
  ceiling today (see §Complexity Ceiling). No campsite-clean debt qualifies here beyond
  what the functional change itself introduces cleanly via extraction.
- **`mission.py`**: `get_mission_for_feature`'s docstring already documents the
  fallback-for-backward-compatibility behavior; no stale-comment debt found there.
- **Everywhere else in the three fix-site file sets**: no other domain-matched debt
  qualifies. This mission does **not** open a broader campsite-clean pass — per Locality
  of Change, extending cleanup beyond the touched functions/files above is not directly
  connected to any of the three goals and would grow the file set for no fix-shaped
  reason. If a WP author finds additional debt while implementing, record what was folded
  and what was deferred (and why) in that WP's own context, per the charter's
  change-scope reconciliation order — do not silently expand scope.

---

## ATDD-First / RED-FIRST

For each FR cluster, the acceptance test is the contract (tied to spec.md's Acceptance
Scenarios/Success Criteria), reproduced RED-FIRST through the **pre-existing** entry
point — never retry-to-green:

| FR cluster | Acceptance contract (spec.md) | RED-FIRST entry point |
|---|---|---|
| FR-001/003 (#3830) | User Story 1 AC1, AC3-4, SC-001/SC-001a | `spec-kitty next` driven against a custom mission type (e.g. `qa`) whose action is a member of its own `action_sequence` — reproduce the current `profile_hint is required` failure live before touching `runtime_bridge_composition.py`/`executor.py`, then confirm it resolves and that `plan`'s distinct `StepContractExecutionError` failure mode is unchanged (AC4) |
| FR-002 (#3830) | User Story 1 AC2, Edge Cases ("malformed org pack") | Own acceptance contract, distinct from FR-001/003's: drive `_composition_dispatch_inputs` (via `spec-kitty next`) against a mission type whose `resolve_mission_type_context` call genuinely raises (e.g. a malformed org pack triggering `charter.activation.mission_type_profiles.UnknownMissionTypeError`) — reproduce live, before the fix, that the bare `except Exception: pass` swallows this with **no log record at all**, indistinguishable from the ordinary case where resolution simply succeeds. After the fix, confirm the same malformed-pack case now produces a log record via the module's own `logger` (`runtime_bridge_composition.py:101`) — the observable signal that changes — while the ordinary "resolution succeeded, action is/isn't in its own sequence" case (which must legitimately keep resolving via `_resolve_step_agent_profile` unchanged, per NFR-001 — it is not an error) continues to log nothing, so a genuine failure is now diagnosable and distinguishable from normal operation by log presence, not conflated with it |
| FR-005 (#3831) | User Story 2 AC2, SC-004 | `get_mission_for_feature`/CLI output for a mission whose type is not found — reproduce the current silent (`pytest.warns`-only-visible) fallback live before touching `mission.py`, then confirm a test capturing actual CLI stdout/stderr under default warning filters (not solely `pytest.warns`) observes the substitution, per SC-004's own stated evidence bar |
| FR-006/FR-008 (#3832) | User Story 3 AC1-8, SC-003 | `setup-plan`/`is_substantive` driven against a `qa`-type mission's plan.md fully populated per its own `test-plan-template.md` (no `Technical Context`) — reproduce the current false `is_substantive() == False` live before touching `_substantive.py`/`mission_setup_plan.py`, then confirm each of the four built-in types plus `qa` passes when faithfully populated and fails when scaffold-only |

Each RED-FIRST reproduction runs through the CLI/runtime entry point a real operator would
hit (`spec-kitty next`, the mission-loader's own call path, `setup-plan`), not a
white-box unit call that bypasses the actual dispatch/loader/gate wiring — this is what
"pre-existing entry point" means for each of the three defects, matching how they were
originally reproduced (spec.md Summary: "reproduced first-hand driving a real `qa`-type
mission").

---

## Architectural Gate Non-Vacuity

Per NFR-005 and the charter's architectural-gate-discipline standing order, the fixed
substantive gate must be demonstrably capable of BOTH passing and failing for **every**
mission type it applies to — no type structurally exempted. Each WP's test plan proves
both directions with two fixtures per type, not just the positive case:

| Mission type | Positive fixture (must PASS) | Negative fixture (must FAIL) |
|---|---|---|
| `software-dev` | plan.md with `Language/Version` + ≥1 real peer field | plan.md missing `Language/Version`, or `Language/Version` present but placeholder-only (existing NFR-003 coverage, extended not narrowed) |
| `documentation` | plan.md with `Documentation Framework` + ≥1 real peer field — **must include one fixture where `Build Commands` (sub-list-valued) is the only populated peer**, per Decision 3(a)'s value-capture extension, so the AND/OR rule's other inline-valued peers cannot mask a regression in that extension | unfilled/placeholder-only `documentation-plan-template.md` scaffold |
| `research` | plan.md with `Research Question` + real `Data Sources` content | unfilled/placeholder-only `research-plan-template.md` scaffold |
| `plan` | plan.md with `Problem Decomposition` + ≥1 real peer field (Scope—MoSCoW / Sequencing & Prioritisation / Decisions) | unfilled/placeholder-only `plan-plan-skeleton.md` scaffold |
| Custom (`qa`, in the WP that exercises it) | plan.md faithfully populated per `test-plan-template.md`'s own eight sections | unfilled/placeholder-only scaffold of `test-plan-template.md` (all eight sections present, populated only with the template's own placeholder text) — same shape as the four built-in rows above, proving the detector returns `False` through its normal per-type declaration + shape-detector + combination-rule path, not merely through error handling |

A separate edge case (not a substitute for the negative fixture above, since it exercises a
different code path — degradation/error-handling, not the detector): a malformed/missing/
unresolvable template must make the gate **fail closed**, never silently pass or crash
(spec.md Edge Cases). Both cases are required for `qa`; neither stands in for the other.

The same non-vacuity discipline applies to the mission-loader fix: the loud-fallback
signal (FR-005) must be observable when the fallback fires and absent when it does not —
SC-004's own test bar (capturing real CLI stdout/stderr under default filters) is the
proof obligation, not `pytest.warns` alone (which would only prove the warning is *raised*,
not that an operator would ever see it — the exact gap this fix closes).

---

## Gate Set

Per `research.md` §R5 (independently verified against `.github/workflows/ci-quality.yml`,
not assumed from a generic list):

**Included, with rationale:**
- **`make ruff/lint`** — applies repo-wide; run on every touched file.
- **Targeted pytest shards**, per the charter's "run only affected packages" guidance:
  `tests/next/`, `tests/runtime/` (FR-001-003); `tests/specify_cli/` mission-loader
  tests (FR-005, see coverage-job correction below — targeted by test path, not by the
  misleadingly-named CI job); `tests/specify_cli/missions/
  test_substantive_gate_formats.py`, `tests/specify_cli/cli/commands/agent/` (setup_plan /
  check_prerequisites suites) (FR-006/FR-008).
- **`diff-coverage` critical-path 90% gate** — **applies to FR-001-003's**
  `src/runtime/next/runtime_bridge_composition.py` (matches the `src/runtime/next/*`
  critical-path entry; confirmed in `research.md` §R5). Does **not** enforce a numeric
  floor on `mission_step_contracts/executor.py`, `mission.py`, `_substantive.py`,
  `mission_setup_plan.py`, or `mission_check_prerequisites.py` — those are covered only by
  the job's advisory full-diff pass. New tests for those files are still required by the
  charter's "every new branch/helper needs tests" rule; they are just not gated by this
  specific numeric threshold.
- **Commitlint** — applies to every commit this mission makes.
- **Typer JSON error surface** — `setup-plan` and `mission_check_prerequisites` both emit
  structured JSON (confirmed: both are `agent`-namespace CLI commands with `--json`
  output paths exercised directly in the FR-006/FR-008 fix); a WP touching either must
  keep the JSON error surface's shape/error-code contract intact.
- **`patch()` target validation** — applies if the FR-006/FR-008 or FR-005 test suites
  patch internals (likely, given `_mission._commit_to_branch`/`is_substantive`/
  `resolve_mission_type_context` are exactly the kind of module-level functions tests in
  this area patch); WP authors must validate patch targets per the existing hygiene gate.

**Explicitly NOT included, with rationale:**
- **Kernel coverage ≥90%** — **not applicable**. No file this mission touches lives under
  `src/kernel/`. `_substantive.py` imports `repo_tree_path` *from* `kernel.paths` but does
  not modify any kernel-owned file, so no kernel-owned code is touched.
- **"Mission-loader coverage ≥90%" (the CI job literally named `mission-loader-coverage`)**
  — **not applicable, verified as a name-based false match**: that job covers
  `src/specify_cli/mission_loader/` (a distinct package — `command.py`,
  `contract_synthesis.py`, `errors.py`, `registry.py`, `retrospective.py`, `validator.py`),
  which does not contain `_mission_path_by_name`/`get_mission_for_feature` — FR-005's file
  is `src/specify_cli/mission.py`, outside that package. This is flagged explicitly rather
  than silently assumed to apply because the name strongly suggests otherwise; the actual
  relevant coverage collector for `mission.py` is `fast-tests-missions`
  (`--cov=specify_cli.mission`, no numeric floor on that job).
- **Doctrine schema freshness** — not applicable; this mission adds no doctrine artifact
  (directive/tactic/styleguide/etc.) and does not touch `.kittify/doctrine/` schema files.
- **Contextive glossary** — not applicable; no terminology/glossary surface changes (no
  new user-facing term is introduced; existing terms — mission type, profile hint,
  substantive, Technical Context — are used, not redefined).
- **Bandit, pip-audit, `uv.lock` freshness** — not applicable; no new dependency, no
  security-sensitive surface (no subprocess/network/crypto change) is introduced by any of
  the three fixes.
- **SonarCloud Quality Gate** — runs automatically in CI on the PR; not separately
  "included" here as a local step, but the complexity-ceiling and repeated-literal
  discipline in §Complexity Ceiling is written specifically so this gate is expected to
  pass without post-hoc cleanup.
- **Architecture/docs consistency** — inert unless a WP adds/edits markdown under
  `docs/architecture/`; none of the three fixes requires an ADR, so this gate is not
  expected to fire. If a WP author later decides an ADR is warranted (e.g. to record the
  per-type field-declaration pattern from Decision 1 for future mission-type authors),
  that WP must then satisfy this gate.

"We'll run the tests" is not a gate statement — the table above names which suites, which
numeric floors apply to which files, and which named gates are inert for this mission and
why.

---

## Baseline Discipline

`main` carries #3284 (23 known-red + 2 errors) and the shared test-venv lock #3283 (C-007,
SC-005). Before the first WP starts:

1. **Capture a baseline classification** by running the targeted test surfaces from
   §Gate Set against `main`/the merge-base *before* any WP change lands, and record which
   failures are already-known #3284 entries vs. new. This baseline run is a plan-phase
   deliverable of the *implementation* kickoff, not this document, but the mechanism is
   fixed here: classify every red against #3284 by test id before attributing any red to
   this mission's own change.
2. **Any red not already covered by #3284** discovered during this mission (whether
   pre-existing-but-previously-unlisted, or a genuine regression) gets filed as its own
   GitHub issue **before** being treated as baseline — never bundled into "the suite is
   red" as an unexamined finding (C-007, charter Pre-existing Failure Reporting Rule).
   "Filed as its own issue" is a hard gate before a red can be waved through as
   pre-existing; a red this mission cannot immediately explain is guilty until classified,
   not innocent by default. **The filed issue must include** (charter Pre-existing Failure
   Reporting Rule, restated here so a WP implementer does not need a round-trip back to the
   charter text): the exact command run, the relevant failure summary, and why the agent
   believes the failures are pre-existing rather than introduced by this mission's own
   change — an issue that satisfies only "filed" without this content does not satisfy the
   charter rule.
3. Per CLAUDE.md's documented baseline-red gotcha (three categories — pre-existing known
   P0s, CI-environment-only failures, stale-install false reds) — confirm any suspected
   category-2/3 red locally against the merge-base before filing, to avoid mistakenly
   opening a tracker issue for environment noise.

---

## Complexity Ceiling

Ruff C901 / Sonar S3776 cap complexity at 15 repo-wide. This applies with particular force
to the FR-006/FR-008 substantive-check generalization — it is the most mechanism-dense of
the three fixes (three shape-detectors, a per-type declaration lookup, and a combination
rule, all converging in what is today one function). The plan expects the generalized
detectors to stay under the ceiling by construction, not by later refactor:

- The per-type declaration lookup (Decision 1), the primary/peer combination rule
  (unchanged from today), and each of the three shape detectors (Decision 3a/b/c) are
  **separate, named helpers** — mirroring how `_has_substantive_technical_context` and
  `_has_substantive_fr_row` are already two separate functions today, not one. No single
  function should need to both look up a type's declaration AND run all three shape
  detectors AND apply the combination rule; `is_substantive`'s `kind == "plan"` branch
  should read as a short composition of already-small, independently testable calls.
- If a WP finds a helper approaching the ceiling despite this decomposition, the
  responsibility is the WP's own campsite-clean discipline at that point in the diff —
  extract further, do not suppress the check.

## Project Structure

No new top-level package or directory. All three fixes land inside their existing,
disjoint file sets (C-003), with two small, explicitly-declared extensions beyond C-003's
literal per-issue file count — recorded here honestly rather than silently, per
§Blast Radius's drift note and §Architecture — Seam Mapping's FR-005 elaboration above:

```
src/runtime/next/runtime_bridge_composition.py          # FR-001, FR-002; the :127 C-008 comment fix lands in the campsite-clean commit (see §Campsite-Clean Scope), not bundled into the FR-001/FR-002 diff
src/runtime/next/runtime_bridge.py                       # #3830 campsite-clean comment-only fix (stale C-008 docstring on _dn_composition_dispatch; no functional change) — declared extension of C-003's #3830 set, see §Blast Radius
src/specify_cli/mission_step_contracts/executor.py       # FR-003 (no new entries added)
src/specify_cli/mission.py                                # FR-005 (fallback-occurred signal exposed; warnings.warn itself unchanged)
src/specify_cli/cli/commands/mission_type.py              # FR-005 CLI-visible surface at the one CLI call site (`current` command/`current_cmd`), reusing the existing specify_cli.cli.console seam per §Architecture — Seam Mapping — declared extension of C-003's #3831 set, since mission.py has no console dependency and must not gain one (layering)
src/specify_cli/missions/_substantive.py                  # FR-006 (per-type declaration + 3 detectors + is_substantive signature)
src/specify_cli/cli/commands/agent/mission_setup_plan.py  # FR-006 (call-site threading)
src/specify_cli/cli/commands/agent/mission_check_prerequisites.py  # FR-008 (comment only)
```

Test additions live alongside the existing targeted suites named in §Gate Set — no new
top-level `tests/` directory is created.

**Structure Decision**: single project, no structural change — this mission is scoped
entirely to extending existing modules on their existing seams (per §Architecture — Seam
Mapping); creating a new module/package for any of the three fixes was considered and
rejected, since each generalization is naturally an extension of code that already lives
in the file it is fixing.

## Constitution Check

*GATE: the charter (`.kittify/charter/charter.md`) is this project's binding governance
document — read in full before this plan was authored.* No violation identified against
any Governing Principle, Standing Order, or Agent Operating Discipline section: single
canonical authority is preserved at every seam (§Architecture), campsite-cleaning is
scoped and domain-matched (§Campsite-Clean Scope), ATDD/RED-FIRST is planned per FR
(§ATDD-First), architectural gate non-vacuity is explicit (§Architectural Gate
Non-Vacuity), and the git/workflow discipline (draft PR, operator merges, no direct
push) is unaffected by this plan — it is enforced by the mission runtime, not by this
document. **One named, deliberate deviation, recorded rather than silently passed
through this gate**: this plan's own §Project Structure/§Blast Radius/§Campsite-Clean
Scope extend spec.md's C-003 binding file-set enumeration by one file each for two of the
three fix sites (`src/runtime/next/runtime_bridge.py` for #3830's campsite-clean comment
fix, `src/specify_cli/cli/commands/mission_type.py` for #3831's FR-005 CLI-visible
surface) — both comment-only or seam-reuse additions, justified by the Boy Scout Rule and
Locality of Change (each file already participates in the exact behavior the corresponding
fix touches), not by convenience or scope creep; this is a knowing, bounded deviation from
C-003's literal per-issue file count, not a violation the plan is unaware of.

## Complexity Tracking

*No Constitution Check violations were identified; this table is intentionally empty.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Suggested Work Package Sequencing

The three fix sites are disjoint file sets (C-003) with no cross-dependency between them —
FR-001-003, FR-005, and FR-006/FR-008 can be implemented and reviewed as **independent,
parallelizable WPs** once the campsite-clean commit (§Campsite-Clean Scope) lands. Baseline
classification (§Baseline Discipline) is a prerequisite for all three, not itself a WP.

```
Campsite-clean (comment fix, behavior-preserving)
        │
        ├──► WP: #3830 composition dispatch (FR-001, FR-002, FR-003)
        ├──► WP: #3831 loud fallback (FR-005 only; FR-004 tracked as follow-up, not a WP here)
        └──► WP: #3832 template-derived substantive gate (FR-006, FR-008)
                        │
                        ▼
              Integration verification: run all three fixes' test surfaces together,
              confirm no cross-fix interaction regression (all three touch the same
              `spec-kitty next` / `setup-plan` control-loop family of entry points even
              though their file sets don't overlap)
```

- **Sequential work**: the campsite-clean comment fix precedes all three (small, low-risk,
  behavior-preserving per Standing Order #2's tidy-first sequencing).
- **Parallel streams**: the three FR-cluster WPs have no file overlap and no data
  dependency — they may be implemented and reviewed concurrently.
- **Agent assignments**: one implementer per WP is sufficient given the bounded, disjoint
  file sets; no ownership-map conflict is expected (charter Mission Hygiene — no-overlap
  is the real guard).
- **Coordination point**: before marking the mission merge-ready, run the full targeted
  test surface from §Gate Set across all three WPs' merged state (not just each WP in
  isolation), since all three ultimately feed the same `spec-kitty next`/`setup-plan`
  control loop a real mission drives end-to-end.
