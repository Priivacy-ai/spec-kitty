---
work_package_id: WP03
title: '#3832 substantive gate — template-derived per-type field declaration and shape detectors'
dependencies: []
requirement_refs:
- FR-006
- FR-008
- NFR-003
- NFR-004
- NFR-005
planning_base_branch: fix/custom-mission-type-second-class-3830
merge_target_branch: fix/custom-mission-type-second-class-3830
# DO NOT re-run 'finalize-tasks' without --validate-only for this mission -- its branch_strategy generator is topology-blind (see tracer-tooling-friction.md / SPEC-KITTY-LEDGER.md SK-133) and will silently overwrite this hand-corrected single_branch text. If a non-validate-only run is unavoidable, immediately re-apply this exact branch_strategy text afterward.
branch_strategy: Planning artifacts for this mission were generated on fix/custom-mission-type-second-class-3830; this mission ships as a single branch/one PR onto that existing branch (topology single_branch) — completed changes must merge back into fix/custom-mission-type-second-class-3830, never a dependency-specific or per-WP branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
- T009
- T010
phase: Phase 1 - Substantive gate
history:
- timestamp: '2026-09-02T00:00:00Z'
  agent: system
  action: Prompt generated via spec-kitty agent mission finalize-tasks
authoritative_surface: src/specify_cli/missions/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/missions/_substantive.py
- src/specify_cli/cli/commands/agent/mission_setup_plan.py
- src/specify_cli/cli/commands/agent/mission_check_prerequisites.py
- tests/specify_cli/missions/test_substantive_gate_formats.py
- tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py
- tests/specify_cli/cli/commands/agent/test_mission_check_prerequisites.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP03 – #3832 substantive gate

## Why this WP exists

`_has_substantive_technical_context` already implements the right *shape* of check
(primary field AND a peer field, tolerant of bullet markers) for one mission type, but
`## Technical Context` + `**Language/Version**` are hardcoded. `_has_substantive_fr_row`
already knows how to find non-placeholder content in a table row, but is anchored to
`FR-###`-prefixed rows only. This WP generalizes both by parameter, adds one genuinely new
detector for the one shape neither covers (nested `###` headings), and threads a
mission-type/template descriptor through `is_substantive`'s `kind="plan"` callers.

This is the most mechanism-dense of the three fixes — three shape-detectors, a per-type
declaration lookup, and a combination rule, all converging in what is today one function.
The complexity ceiling (15, ruff C901/Sonar S3776) applies with particular force here; see
T009. This WP owns FR-006, FR-008, NFR-003, NFR-004, NFR-005.

**Binding decisions this WP implements — read `plan.md`'s Decisions 1–5 in full before
starting; do not re-derive or re-litigate them:**
- Decision 1: per-type field declaration, template-derived metadata resolved once per
  mission type, hand-maintained and co-located with the template it describes (not
  re-parsed from template prose at runtime). `research`'s checked set is **two** fields
  (`Research Question` primary, `Data Sources` peer) — `Methodology` itself carries no
  checkable content (it's a pure grouping container).
- Decision 2: section heading and primary field label are **one axis**, resolved from the
  same declaration — not two independently-generalized literals.
- Decision 3: shape (a) bold-field list — generalize the existing peer-field scan by
  parameter, plus the value-capture extension for sub-list-valued fields (e.g.
  `documentation`'s `Build Commands`, PLAN-FRESH3-002's finding). Shape (b) markdown table —
  generalize the existing table-row detector, removing the `FR-###` anchor. Shape (c) nested
  third-level heading — one new detector, dispatching on two declared sub-shapes: (c-i)
  repeatable instance (`plan`'s Decisions — container heading IS the field, at least one
  populated `### Decision D-N` instance suffices) and (c-ii) specifically-named sibling
  (`research`'s Data Sources — the ONE nested heading matching the field's declared name,
  located by name not merely nesting depth).
- Decision 4: extend `_PLACEHOLDER_PATTERNS` with the same conservative,
  enumerated-literal style (one pattern per actual bracket phrase `research` and `plan`'s
  templates scaffold) — never a generic "any bracketed span" rule (false-negative risk
  against NFR-005).
- Decision 5: thread `setup_plan`'s single upstream-resolved `plan_template` into
  `_commit_plan_if_substantive` rather than re-resolving independently at each call site.
  `kind="spec"` callers are unaffected — no signature-breaking change to the spec path.
  `mission_check_prerequisites.py`'s `kind="spec"` guard stays **behaviorally unchanged**
  (documented, not fixed — see T007).

**Sequencing reconciliation (`wps.yaml` intentionally leaves `dependencies: []` here)**:
`plan.md` §Suggested Work Package Sequencing states mission-wide that "the campsite-clean
comment fix precedes all three" WPs. That intent is satisfied by WP01's T001 alone, not by
a cross-WP dependency edge on this WP: `plan.md` §Campsite-Clean Scope found zero
qualifying campsite-clean debt in this WP's own file set (`_substantive.py`,
`mission_setup_plan.py`, `mission_check_prerequisites.py`) — no pre-existing lint/complexity
offender or stale-comment debt was found at the functions this WP touches, so a
`dependencies: ["WP01"]` edge would force this WP to wait on the whole of WP01
(T001–T007) for no file-level reason, contradicting `plan.md`'s explicit framing of these
three WPs as independent and parallelizable. **Operational instruction, binding**: because
this mission ships as a single branch/one PR (`fix/custom-mission-type-second-class-3830`,
topology `single_branch` — see frontmatter above) and nothing else enforces commit order on
that shared branch, whoever dispatches or implements this WP must confirm WP01's T001 (the
campsite-clean comment commit correcting the stale `runtime_bridge_composition.py`/
`runtime_bridge.py` comments) has already landed on
`fix/custom-mission-type-second-class-3830` before starting this WP's own commits.

## Subtasks

### T001 — RED-FIRST repro: FR-006/FR-008 false negative

Through the pre-existing entry point (`setup-plan`, not a white-box unit call): drive it
against a `qa`-type mission's plan.md, fully populated per its own `test-plan-template.md`
(no `## Technical Context` — that heading doesn't exist in this template). Reproduce, live,
before touching `_substantive.py`/`mission_setup_plan.py`, the current false
`is_substantive() == False` (User Story 3, AC1-8, SC-003). Capture as a failing test.

### T002 — Per-type field declaration (Decisions 1 & 2)

Build the explicit, hand-maintained per-type declaration: for each mission type, which
heading(s) hold which named field, at what depth, in what shape (bold-field list / table /
nested-heading — and for (c), which sub-shape), and — for a bold-field-list field
specifically — whether its value is inline or sub-list-valued. Cover `software-dev`,
`documentation`, `research` (two checked fields per Decision 1's reconciliation:
`Research Question` primary, `Data Sources` peer, sub-shape c-ii), `plan` (`Problem
Decomposition` primary; peers among `Scope — MoSCoW` / `Sequencing & Prioritisation` /
`Decisions`, the last as sub-shape c-i) — **plus a fifth, test-only `qa` entry, described in
(a) below**. Co-locate the declaration with the templates it describes so a future template
edit is a two-line diff in the same PR, not silent drift.

**This declaration is the single source for every operator-facing string that names a
container heading or primary-field label** — not just the boolean shape detectors
(T003-T005). That includes `describe_technical_context_gap`'s diagnostic text and the
console/`blocked_reason` strings in `mission_setup_plan.py`, both generalized in T007. Do
not leave any of those message sites with their own independently-maintained heading/label
literal alongside this declaration (fresh-eyes finding TASKS-FRESH-001).

**(a) The declaration's scope is five entries, not four — the fifth is this WP's own `qa`
proof-of-mechanism fixture (fresh-eyes finding TASKS-FRESH3-001):** no `packs/built-in/
missions/qa/` directory and no `test-plan-template.md` file exist anywhere in this repo
today (verified) — `qa` is not a real built-in mission type, and this WP must NOT create a
real `packs/built-in/missions/qa/` pack (that would be new-mechanism work no FR in this
mission asks for). Instead, construct a synthetic, test-only `test-plan-template.md`
fixture — per spec.md's User Story 3 Independent Test, its eight sections are `Test Items`,
`Environments`, `Test-Data Strategy`, `Suite Breakdown`, `Tooling`, `Schedule`,
`Responsibilities`, `Traceability-Matrix Skeleton`, none named `Technical Context` — and add
a `qa` row to this same checked-in declaration table, following the same shape/format as
the four built-in entries (declare `Test Items` as the primary field per NFR-004's
first-scaffolded-field rule, plus at least one genuine peer among the remaining seven, in
whatever shape (a)/(b)/(c) you author the fixture's own sections in).

Match the existing test files' own fixture-authoring conventions instead of inventing a new
fixtures directory (verified: no `tests/specify_cli/missions/fixtures/` directory exists
today) — two conventions already coexist, used for two different test levels:
- **Shape/unit-level tests** (`tests/specify_cli/missions/test_substantive_gate_formats.py`,
  T003-T006, and T008's boolean-outcome fixtures): a module-level triple-quoted Python
  string constant per fixture variant, matching this file's existing
  `_BULLETED_REAL`/`_BULLETED_PLACEHOLDERS`-style constants — add `_QA_REAL`/
  `_QA_PLACEHOLDERS`-style constants built from the eight-section content above, fed
  directly to the relevant shape detector / `is_substantive`.
- **Entry-point-level tests** (`tests/specify_cli/cli/commands/agent/
  test_mission_setup_plan_phases.py`, T001's RED-FIRST repro and T008's message-content/
  shape-dispatch assertions, both of which must drive the real `setup-plan` entry point, not
  a white-box call): write the same fixture content to a file under `tmp_path`, then
  monkeypatch `_resolve_plan_template`/`resolve_mission_type_context` to return it via
  `_resolved_mission_type(mission_type="qa", ...)` and `_resolution(path)` — the identical
  pattern this file already uses for the built-in-but-non-`software-dev` `research` type at
  `test_resolve_plan_template_fails_closed_for_bad_configuration`'s `mission_type="research"`
  parametrization. This proves the mechanism through the real entry point without adding a
  real `qa` pack anywhere in the repo.

**This `qa` entry is this WP's PROOF CASE that the declaration-driven mechanism can resolve
a genuinely custom (non-built-in) mission type — it is not itself "any custom type"
support.** See (b) below for how this reconciles against NFR-005's literal "any custom
type" wording.

**(b) NFR-005 scope reconciliation (document this the same way T007 already documents the
`kind="spec"` non-extension — do not leave it implicit):** NFR-005 requires the gate to be
"demonstrably capable of both passing and failing for every mission type ... (software-dev,
documentation, research, plan, and any custom type)." This WP satisfies that requirement as
follows, and the implementer must record this reconciliation as an inline code comment
next to the declaration table (mirroring T007's `kind="spec"` comment):
1. The four built-ins plus the one `qa` proof-of-mechanism fixture are demonstrably provable
   in T008's fixture matrix — that is the literal, fixture-by-fixture proof NFR-005 asks
   for, scoped to the five types this mission can concretely construct fixtures for.
2. The mechanism's own DESIGN is declaration-driven, not hardcoded per-type logic (Decision
   1) — so a REAL third-party custom mission type can get a declaration entry added later by
   whoever owns that pack/template, without a change to `is_substantive`'s own logic. `qa`'s
   entry in the table is proof this extension path works, not a claim that every future
   custom type is already covered.
3. **A mission type with NO declaration entry at all is explicitly OUT of this mission's
   fixture-matrix proof scope.** Decided fallback behavior (binding, not left open for the
   implementer): `is_substantive(plan_file, "plan")` **fails closed** — returns `False` —
   for a mission type whose template resolves successfully but has no entry in the
   declaration table, exactly as it already does per plan.md's Blast Radius row for a
   malformed/missing/unresolvable template, even though the underlying cause is different
   (a resolvable template with nothing to check it against, vs. a template that cannot be
   read at all). Rationale: NFR-005 explicitly forbids "a neutral pass that always returns
   `True`" and the charter's architectural-gate-discipline standing order treats "a gate
   that cannot fail" as its own defect class (the exact pattern this mission's FR-008 half
   already fixes for `mission_check_prerequisites.py`'s `kind="spec"` guard) — silently
   passing an undeclared type would recreate that same defect class one call site over, so
   fail-closed is the only option consistent with the rest of this WP's own design. Give
   `describe_technical_context_gap`/`blocked_reason` (T007) a distinct diagnostic for this
   case (e.g. naming the unrecognized mission type and stating no field declaration is
   registered for it) rather than reusing the malformed-template message, since the two
   causes are operator-distinguishable and conflating them would misdirect a real
   third-party pack author toward "fix your template" when the actual fix is "add a
   declaration entry." T008's separate malformed/missing-template edge-case test (required
   regardless) exercises the *other* fail-closed path — a resolvable template with no
   declaration entry is a different code path and needs its own coverage; do not treat one
   test as satisfying both.

### T003 — Generalize shape-(a) bold-field-list detector + value-capture extension

Parameterize `_has_substantive_technical_context`'s container heading and primary-field
label from the Decision 1/2 declaration, in place of the hardcoded `## Technical Context` /
`**Language/Version**`. Preserve the existing leading `-`/`*` bullet-marker tolerance
(FR-013/#1896) unchanged. Extend the existing value-capture (`(?P<val>[^\n]*)`, currently
inline-only) to also read a bulleted sub-list on the lines below the label when the
same-line value is empty after placeholder-stripping AND the declaration marks that field
as sub-list-valued (stop at the next bold-field line or a blank-line-then-non-bullet
boundary), subject to the same non-placeholder check already applied to inline values. This
is one detector with one new declared per-field flag — not a fourth shape or a second
detector. Do not extend `documentation`'s checked peer-field set to include `Generator
Tools` (identical shape, but not in the declared peer-field set) — that omission pre-dates
this fix and is out of scope (Locality of Change).

### T004 — Generalize shape-(b) table-row detector

Generalize `_has_substantive_fr_row`'s table half: remove the `FR-###`-prefix anchor: check
whether *any* data row under the declared heading's table has non-placeholder content in
its descriptive columns. Row-scanning and placeholder-checking logic itself is unchanged —
only the row-selection predicate changes from "starts with `FR-`" to "is a data row of this
table." This covers `plan`'s Problem Decomposition and Sequencing & Prioritisation.

### T005 — New shape-(c) nested-heading detector (both sub-shapes)

One new detector, dispatching on a declared sub-shape parameter (not guessing from
structure at check time):
- (c-i) repeatable instance: substantive iff **at least one** `### Decision D-N` instance
  nested directly under `## Decisions` has non-placeholder content in its body.
- (c-ii) specifically-named sibling: substantive iff the ONE nested `###` heading whose
  label matches the declared field's own name (`### Data Sources`, under the shared `##
  Methodology` parent that also holds unrelated siblings `### Research Design` / `###
  Analysis Framework`) has non-placeholder content in its own body — a populated sibling
  does not satisfy this.

### T006 — Extend `_PLACEHOLDER_PATTERNS` (Decision 4)

Add one pattern per actual bracket phrase `research-plan-template.md` and
`plan-plan-skeleton.md` scaffold (e.g. `[Primary question]`, `[Academic field or industry
domain]`, `[Sub-problem statement]`, `[Cluster name]`, `[SP-# or none]`, `[High/Low]`,
`[Decision title]`, `[Chosen option, stated plainly]`, `[Why this option wins]`,
`[Alternative A]`, `[Failure scenario]` — verify the live template files for the complete
list, don't transcribe this list blind), in the same conservative, enumerated-literal style
as the existing 17-entry list. Do not adopt a generic "any bracketed span is a placeholder"
rule — this would risk stripping real content that legitimately contains a bracketed span
(e.g. a citation), the false-negative direction NFR-005 forbids.

### T007 — Thread `plan_template` through call sites; document the `kind="spec"` non-extension; generalize operator-facing gap messages

`is_substantive`'s signature grows a parameter carrying the mission type/resolved template
descriptor for `kind="plan"` callers only (`kind="spec"` callers are unaffected — no
signature-breaking change to that path). At the two `kind="plan"` call sites in
`mission_setup_plan.py` (`_commit_plan_if_substantive` and `setup_plan` directly): thread
`setup_plan`'s single upstream-resolved `plan_template` (`ResolutionResult`, already in
scope at both sites via the existing parameter thread) into the now-mission-type-aware
`is_substantive` call — no new resolution step, no independent re-resolution at either
site.

At `mission_check_prerequisites.py`'s `kind="spec"` guard (`mission_type != "software-dev"
or is_substantive(spec_file, "spec")`): add an inline code comment recording the
reconciliation — `research` and `plan`'s own spec templates contain zero `FR-###` rows
(verified: `grep -n "FR-" ` over both), so there is no FR-vocabulary to derive a
template-derived spec check from for these two types. This guard's **behavior stays
unchanged** in this mission — this subtask is a documentation task, not a logic change.

**Generalize the three hardcoded operator-facing message sites (fresh-eyes finding
TASKS-FRESH-001) as part of this same call-site subtask** — these independently duplicate
literals the Decision 1/2 declaration (T002) already owns, and would otherwise ship wrong
guidance text to research/plan/qa-type operators even after T003-T005 fix the boolean gate:
- `describe_technical_context_gap` in `_substantive.py` (currently lines 198-236): its
  `## Technical Context` section-heading regex (line 212), the "Technical Context section
  is missing from plan.md." message (line 217), the `**Language/Version**` field regex
  (line 220), and both diagnostic return strings (lines 226-229 and 232-236) are all
  independently hardcoded to the `software-dev` heading/label instead of reusing T002's
  declaration. **A label-only text substitution is NOT sufficient (fresh-eyes finding
  TASKS-FRESH2-001):** the function's own detection logic — the section-heading search,
  then a `\*\*{label}\*\*[ \t]*:[ \t]*` bold-field regex against the primary field, used to
  choose which of the three diagnostic strings to return — is intrinsically shape-(a)-only.
  Naively substituting in a per-type heading/label string leaves that same bold-field regex
  in place; for `plan` (`Problem Decomposition`, shape (b), a table row per T004) or
  `research`'s `Data Sources` peer (shape c-ii, nested heading per T005), that regex can
  never match, so the function would ALWAYS return the "primary field is missing or
  placeholder-only" diagnostic even when the primary field is genuinely populated and the
  real failure is a missing peer — the wrong diagnosis. Generalize this function to accept
  the same mission-type/template descriptor now threaded into `is_substantive`, **and give
  it the same per-shape dispatch T003-T005's boolean detectors already have**: reuse (or
  re-derive via the same named shape-detector helpers from T003-T005, per T009's
  decomposition — do not re-implement shape detection a second time here) the sub-result of
  which field/shape actually failed — section/heading absent, primary field absent or
  placeholder-only, or peer field(s) absent or placeholder-only — and select the diagnostic
  string from that sub-result, not by re-running a bold-field-only regex against every
  type's fields regardless of their declared shape. Build every heading/label reference in
  the chosen diagnostic from T002's declaration — so, e.g., a `research`-type gap message
  names `Research Question` and `Data Sources`, not `Language/Version` — but the SELECTION
  of which message to emit must track the real shape-(a)/(b)/(c) failure, not just relabel
  shape-(a)'s output.
- `mission_setup_plan.py:825`'s scaffold-only console message ("...populate Technical
  Context and re-run setup-plan.") — replace the literal "Technical Context" with the
  resolved type's own container-heading/primary-field label.
- `mission_setup_plan.py:833-834`'s `blocked_reason` base string ("...populate Technical
  Context with real values (Language/Version plus at least one peer field, such as Primary
  Dependencies)...") — replace both literals with the resolved type's own primary-field
  label and an example peer field drawn from its own declaration, not `software-dev`'s.

### T008 — Non-vacuity fixture matrix (NFR-005)

Per `plan.md` §Architectural Gate Non-Vacuity, prove the gate can PASS and FAIL for every
mission type it applies to — two fixtures per type, not just the positive case:

| Mission type | Positive fixture (must PASS) | Negative fixture (must FAIL) |
|---|---|---|
| `software-dev` | `Language/Version` + ≥1 real peer field | missing/placeholder-only `Language/Version` (existing NFR-003 coverage, extended not narrowed) |
| `documentation` | `Documentation Framework` + ≥1 real peer field — **include one fixture where `Build Commands` (sub-list-valued) is the only populated peer**, so the AND/OR rule's other inline-valued peers cannot mask a regression in T003's value-capture extension | unfilled/placeholder-only `documentation-plan-template.md` scaffold |
| `research` | `Research Question` + real `Data Sources` content | unfilled/placeholder-only `research-plan-template.md` scaffold |
| `plan` | `Problem Decomposition` + ≥1 real peer field (Scope—MoSCoW / Sequencing & Prioritisation / Decisions) | unfilled/placeholder-only `plan-plan-skeleton.md` scaffold |
| `qa` (custom) | faithfully populated per the **WP-constructed** synthetic `test-plan-template.md` fixture's own eight sections (T002(a) — this is a test-only fixture this WP builds and declares, not a pre-existing repo template; no `packs/built-in/missions/qa/` exists in this repo) | unfilled/placeholder-only scaffold of that same WP-constructed `test-plan-template.md` fixture (all eight sections present, populated only with the template's own placeholder text) — proves the detector returns `False` through the normal declaration + shape-detector + combination-rule path, not error handling |

Add a separate edge-case test (not a substitute for the negative fixture above — different
code path): a malformed/missing/unresolvable template must make the gate **fail closed**,
never silently pass or crash. Both the `qa` negative fixture and this edge case are
required; neither stands in for the other.

Add a second, distinct edge-case test per T002(b)'s decided fallback: a mission type whose
template **resolves successfully** but has **no entry** in the T002 declaration table must
also make the gate fail closed (`is_substantive` returns `False`) — this is a different code
path from the malformed/missing/unresolvable-template case above (there, template
resolution itself fails; here, resolution succeeds but the declaration lookup has nothing to
check against) and from the `qa` negative fixture above (there, `qa` HAS a declaration entry
and fails on content; here, the type has none at all). Construct this fixture by resolving
to a real, well-formed template (any built-in template, or the `qa` fixture from T002(a)) but
under a mission-type name deliberately absent from the declaration table (e.g. `"unlisted"`)
— per T002(b), assert both the boolean outcome (`False`) and that `describe_technical_context_gap`/`blocked_reason`
emit the distinct "no field declaration is registered for mission type ..." diagnostic
rather than a malformed-template message.

**Message-content assertion (not just boolean outcome, TASKS-FRESH-001):** for at least one
non-`software-dev` negative fixture above (`research` or `plan`'s unfilled scaffold is
sufficient), add an assertion on the actual message text — not just that `is_substantive()`
returns `False`. Assert that `blocked_reason` (via `mission_setup_plan.py`'s
`_commit_plan_if_substantive`, per T007's generalization) and, where the fixture reaches it,
`describe_technical_context_gap`'s returned string name that type's OWN primary-field/
heading label (e.g. `Research Question` for `research`) and do NOT contain the literal
"Technical Context" or "Language/Version". This is the only way the fixture matrix would
catch a regression back to T007's hardcoded literals — the existing pattern in
`test_mission_setup_plan_phases.py` only asserts `blocked_reason is not None`.

**Shape-dispatch fixture (required, TASKS-FRESH2-001):** the assertion above alone would
still pass if T007's generalization is a naive label-only substitution that keeps the old
shape-(a)-only detection (see T007's strengthened instruction) — a wrong-but-relabeled
message still names the right label and omits the old literals. Add, for at least one
non-`software-dev` type whose primary field is NOT shape (a) (`plan`'s `Problem
Decomposition`, shape (b), is sufficient; `research`'s `Data Sources` peer, shape c-ii, is
an acceptable alternative or addition), a SEPARATE negative fixture where the PRIMARY field
is populated with real content but the declared PEER field(s) are not (or, for the
`research` alternative, the primary `Research Question` is populated but the `Data Sources`
peer is not). Assert the returned message names the field that ACTUALLY failed (the peer),
not the primary field, and does not fall back to a "primary field is missing or
placeholder-only" diagnostic when the primary is genuinely populated. This is the only
assertion shape that forces the shape-(b)/(c) dispatch gap in `describe_technical_context_gap`
to surface during implementation instead of shipping silently — a fixture where BOTH primary
and peer are unfilled (the existing scaffold-negative case) cannot distinguish a correct
per-shape diagnosis from an always-wrong shape-(a)-only fallback.

### T009 — Complexity-ceiling check

Confirm the per-type declaration lookup, the primary/peer combination rule (unchanged from
today), and each of the three shape detectors are **separate, named helpers** — mirroring
how `_has_substantive_technical_context` and `_has_substantive_fr_row` are already two
separate functions today. No single function should both look up a type's declaration AND
run all three shape detectors AND apply the combination rule; `is_substantive`'s
`kind == "plan"` branch should read as a short composition of already-small,
independently-testable calls. If any helper approaches the ceiling (15, ruff C901/Sonar
S3776) despite this decomposition, extract further as part of this WP's own diff — do not
suppress the check.

### T010 — Gate run (includes the mission's coordination point)

Per `plan.md` §Gate Set:
- `make ruff/lint` on every file this WP touches.
- Targeted pytest: `tests/specify_cli/missions/test_substantive_gate_formats.py`,
  `tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py`,
  `tests/specify_cli/cli/commands/agent/test_mission_check_prerequisites.py`.
- No diff-coverage numeric floor applies to `_substantive.py`/`mission_setup_plan.py`/
  `mission_check_prerequisites.py`; new tests are still required by the charter's
  every-new-branch-needs-tests rule.
- Typer JSON error surface: `setup-plan` and `mission_check_prerequisites` both emit
  structured JSON via `--json` — keep the JSON error surface's shape/error-code contract
  intact.
- Validate any `patch()` targets used in new/changed tests per the repo's patch-target
  hygiene gate.
- Before attributing any red to this WP, classify it against #3284's known-red baseline (23
  failures + 2 errors) and the #3283 shared test-venv lock — run the same test against
  `main`/the merge-base first. A red not covered by #3284 gets filed as its own GitHub issue
  (with the exact command, failure summary, and why it's believed pre-existing) before being
  treated as baseline — never silently waved through.

**Coordination point (mission-level, not a separate WP)**: per `plan.md` §Suggested Work
Package Sequencing, before the mission is marked merge-ready, run the full targeted test
surface from `plan.md` §Gate Set across all three WPs' merged state (not just each WP in
isolation) — WP01, WP02, and this WP all ultimately feed the same `spec-kitty next`/
`setup-plan` control-loop family of entry points even though their file sets don't overlap.
Confirm no cross-fix interaction regression at that point.

## Definition of Done

- FR-006/FR-008: the substantive gate is template-derived and generalizes by parameter, not
  reimplemented per type; `kind="spec"`'s non-extension is documented (T007), not silently
  left unexplained.
- Operator-facing gap messages (`describe_technical_context_gap`,
  `mission_setup_plan.py`'s scaffold console message and `blocked_reason` string) are
  generalized off the same Decision 1/2 declaration as the boolean gate (T002, T007), not
  left independently hardcoded to "Technical Context"/"Language/Version"; proven by a
  message-content assertion for at least one non-`software-dev` type (T008).
- NFR-003: `software-dev`'s existing pass/fail behavior is unchanged.
- NFR-004: each type's checked field set matches spec.md's own named fields (per Decision
  1's reconciliation for `research`), not a convenience subset.
- NFR-005: per the T002(b) scope reconciliation, satisfied for the four built-in types plus
  the one `qa` proof-of-mechanism fixture — full non-vacuity fixture matrix (T008), every one
  of those five types proven to both PASS and FAIL, plus both fail-closed edge cases (a
  malformed/missing/unresolvable template, and a resolvable template whose mission type has
  no declaration entry). This is NOT a claim that literally "any custom type" that will ever
  exist is fixture-proven — only that the mechanism is declaration-driven so a real
  third-party type can be added later without a code change, per T002(b).
- Complexity ceiling respected by construction (T009), not by post-hoc refactor.
- Gate Set items (T010) all green, or every red explicitly classified against #3284 with a
  filed issue for anything new; the mission-level coordination point run and clean.
