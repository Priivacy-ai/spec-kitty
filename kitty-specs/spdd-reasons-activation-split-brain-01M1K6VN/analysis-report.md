---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: spdd-reasons-activation-split-brain-01M1K6VN
mission_id: 01M1K6VNA08KVJQ1C32JB639XE
generated_at: '2026-09-03T12:40:25.670154+00:00'
analyzer_agent: unknown
input_artifacts:
  spec.md:
    path: kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/spec.md
    sha256: 55297f40541c3e447633e4919c0958278f7f4ac71f876349f5d463df0e5bb42b
  plan.md:
    path: kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/plan.md
    sha256: 89cd695610a4b7f310b54bd5ce23928739b4e490761120cfae1cacbbeba5658f
  tasks.md:
    path: kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/tasks.md
    sha256: c4b955fa797d5481374392d10cfb61f251c6fadac8230466e66cba00e1b9d317
  charter:
    path: .kittify/charter/charter.yaml
    sha256: 137e5999a27cc10136e65984ca5fbb5e9b7675324065e6cb076f72bcfddebf96
verdict: blocked
issue_counts:
  medium: 0
  high: 1
  low: 1
  critical: 0
  info: 0
findings:
- id: A1
  severity: high
  category: coverage
  summary: WP02's Union/Exclusion Boundary Audit boundary 1 (project_directives derivation from pack_context.activated_directives, action_doctrine_bundle.py T009 step 1) asserts '_normalize_directive_id is applied' with no red-first fixture that would actually fail if that normalization were dropped or omitted on this specific (non-org-required) path -- every T007 fixture either uses already-canonical directive ids on the direct activated_directives path, or exercises stem-form normalization only via the separate org-required-union path (boundary 3, T007 step 6). WP03's structurally identical boundary (resolver.py _resolve_directive_base's activated_directives base) DOES carry this exact coverage (T011 step 6).
- id: A2
  severity: low
  category: coverage
  summary: "NFR-004 (state the this-repo SPDD activation flip in the PR body) and C-004 (PR body must cite 'Closes #3838') have no WP subtask or Definition-of-Done line assigning responsibility for satisfying them -- unlike FR-009/SC-005, which explicitly delegates its PR-time-only verification to 'reviewed at PR time instead', no artifact makes an equivalent explicit delegation for NFR-004/C-004."
---

## Specification Analysis Report

**Mission**: `spdd-reasons-activation-split-brain-01M1K6VN` (issue #3838)
**Branch**: `fix/spdd-reasons-activation-split-brain-3838`
**Analyzer**: Claude (author of this analyze-phase report), running the canonical `/spec-kitty.analyze`
detection passes plus the mission-specific investigations the dispatching orchestrator specified.

`.kittify/charter/charter.md`, `AGENTS.md`, `CLAUDE.md`, `spec.md`, `plan.md`, `tasks.md`, all five
`tasks/WP0*.md` files, and `reviews/tasks.ruling.md` were all read in full for this pass. Every `file:line`
citation quoted below was re-verified against the live checkout with `grep -n`/`sed -n`, not copied from the
mission's own claims — see the citation-verification log in the "plan.md vs live code" section.

### Standard detection passes

- **Duplication**: none found. WP01/WP02/WP03 are file-disjoint by `owned_files` (verified against
  `tasks.md`'s frontmatter: WP01 owns `activation.py` + its own parity test; WP02 owns
  `action_doctrine_bundle.py`/`delivery_table.py` + two test files; WP03 owns `resolver.py` + its own test
  file). No two WPs edit the same production line.
- **Ambiguity**: none material. T012 step 1 explicitly leaves the exact provenance-label string
  (`"activation+charter"` vs. keeping `"activation"`/`"charter"`) as implementer's choice, but states the
  load-bearing behavior (the union itself) is not ambiguous — this is a deliberate, bounded discretion, not
  an underspecified requirement.
- **Underspecification**: none found beyond A1 below. Every FR names an exact function, an exact
  file:line-verified current behavior, and a concrete red-first fixture shape.
- **Charter alignment**: consistent. The mission's own "never trust a green check ... verify against live
  code" standing order is what this analyze pass itself follows (see citation-verification below); the
  ATDD-first discipline (C-011) is honored — every WP's T0xx sequence commits red-first tests before its
  implementation commit, explicitly stated per subtask.
- **Coverage gaps**: A1 (WP02 boundary 1) and A2 (NFR-004/C-004 orphaned from any WP) — see Findings.
- **Inconsistency**: none found between spec.md/plan.md/tasks/WP0*.md beyond the noted A2 gap. plan.md
  section (a) item 3's "catalog default, not empty set" instruction for `selected_tactics`/`selected_paradigms`
  is followed consistently in WP02's T009 step 1 and Context section — no residual "empty set" framing survived
  into the tasks artifact from an earlier plan revision.
- **Terminology Canon** (Mission, never Feature): clean. The only "Feature" hit across spec.md/plan.md/
  tasks.md/tasks/WP0*.md is plan.md line 4's `**Input**: Feature specification from ...` — confirmed this is
  verbatim boilerplate inherited from the canonical `packs/built-in/missions/software-dev/templates/plan-template.md`
  header (grepped both; identical string), not mission-authored prose, and out of this mission's edit scope.
  Not raised as a finding.

### Investigation (a) — FR/NFR traceability (spec.md ↔ plan.md ↔ tasks/WP0*.md)

Every FR-001..FR-014 traces to both a plan.md mission-specific section ((a)-(m)) and at least one WP subtask
(T0xx); every WP subtask traces back to a named FR. Verified by direct cross-reference, not assumed:
FR-001→plan(a)/(h)/(i)→WP01 T004; FR-002→plan(b)→WP01 T002; FR-003→plan(h)→WP01 T004.3; FR-004→spec Edge
Cases/plan(a).1 carve-out→WP01 T001/T003/T004.a,g; FR-005→plan(a).1→WP01 T004.c,e/T002.6; FR-006→plan(a).2-3→
WP02 T009; FR-007/FR-008→plan "Phasing" WP2→WP02 T007.2-3; FR-009→plan(d)→WP05 T017/T018; FR-010→plan(i)
WP4→WP04 T014-T016; FR-011→plan(a).4→WP03 T012; FR-012/FR-013→plan "Phasing" WP3→WP03 T011.3-4/T012;
FR-014→plan(a).3→WP02 T007.4/T009.3. NFR-002/NFR-003 trace to the C-004/dead-symbols gate re-runs in every
WP's final subtask (T005/T010/T013). NFR-001 traces to plan section (m)'s per-path table, echoed in every
WP's Definition of Done. NFR-005/C-005 trace to the baseline-capture subtask (T001/T006/T011) present in
every implementer WP. C-001/C-002/C-003/C-006 are satisfied structurally (by what the WPs do NOT touch —
schema, relocation) and are not orphaned in a way that needs a dedicated task.

**Gap found (A2, low)**: NFR-004 ("this must be named explicitly in the PR body") and C-004 ("the eventual
PR body must carry `Closes #3838`") are the two spec-level requirements with no WP subtask or Definition-of-
Done line assigning responsibility for satisfying them. This is very likely intended to be carried by the
mission's standard PR-prep/close-out procedure (outside the 5 WPs, which are implementation-only) — but
unlike FR-009 (whose own SC-005 explicitly states "no red-first ATDD test should be manufactured... a
specific reviewer step at mission close owns this"), no artifact in this mission states that same delegation
for NFR-004/C-004. Low severity: the standard `mission-wrap-up-sequence` procedure (charter, Code Quality
section) already requires "Issue Closure Linkage" compliance project-wide, so this is very unlikely to be
missed in practice — flagged for completeness of the traceability audit requested, not because it threatens
correctness.

### Investigation (b) — does the ruling's invariant land in WP02/WP03's acceptance text, boundary by boundary?

The invariant (from `reviews/tasks.ruling.md`, restated verbatim in both WPs): *"Every directive, tactic and
paradigm identifier is canonicalized at the moment it enters a union, and every union and exclusion boundary
either canonicalizes its inputs or fails loud. An identifier whose form cannot be canonicalized is an error,
never a silently-excluded entry. Absent input resolves to the documented catalog default, never to an empty
set."* Checked per-boundary whether the WP's Definition of Done + Reviewer Guidance would actually **catch a
violation** if implementation silently violated that specific boundary — not whether the WP's prose
*describes* the boundary correctly (every boundary's prose is accurate; that is not what was checked).

**WP02** (`action_doctrine_bundle.py` / `delivery_table.py`), six boundaries enumerated in its own audit table:

1. `project_directives` from `pack_context.activated_directives` (T009 step 1 normalization) — **NOT
   CAUGHT**. No T007 fixture supplies a stem-form id via the direct `activated_directives` field (all of
   FR-007/FR-008/FR-014 use already-canonical `DIRECTIVE_038`/`DIRECTIVE_010` forms or an empty list; the
   tactics/paradigms-absent sibling fixture, T007 step 5, does not touch `activated_directives` at all; T007
   step 6's stem-form fixture explicitly leaves `activated_directives` absent/`None` so its stem-form
   `DIRECTIVE_001` reaches `project_directives` ONLY through the org-required union, boundary 3). A T009
   step 1 implementation that dropped `_normalize_directive_id(d)` from the comprehension (assigning
   `directives_arg` straight into `project_directives`) would pass every one of WP02's own tests. This is
   **Finding A1**.
2. `selected_tactics`/`selected_paradigms` from `activated_tactics`/`.activated_paradigms` (no normalization
   needed) — **safe by structural fact, not by dynamic test**: re-verified live that no built-in
   tactic/paradigm file's filename stem differs from its `id:` field, and no `_normalize_tactic_id`/
   `_normalize_paradigm_id` exists anywhere in `src/` (grep, zero results) — there is genuinely nothing to
   canonicalize, so "no test needed" is a correct claim here, unlike boundary 1.
3. Org-required union onto `project_directives` (T009 step 2 normalization) — **CAUGHT**. T007 step 6 is a
   concrete, named, RED-against-pre-round-text fixture (stem-form `001-architectural-integrity-standard`
   org-required directive, asserting the canonical `DIRECTIVE_001`/`directive:DIRECTIVE_001` form is what's
   delivered).
4. Org-required union onto `selected_tactics`/`selected_paradigms` (no normalization) — vacuous, same
   structural-fact backing as boundary 2.
5. `delivery_table.py`'s exclusion guard (`is not None`) — **CAUGHT**. T007 step 4 (FR-014) is a direct,
   named RED-first fixture: explicit `activated_directives: []` must exclude everything, not fall through
   bare-truthiness to "no filter."
6. `start_urns`/`roots` construction — **CAUGHT** for the "no `TypeError`, catalog-default population" claim
   via FR-008 (T007 step 3) and the tactics/paradigms-absent sibling (T007 step 5); contingent on boundaries
   1–4's conversions per the audit's own text, so boundary 1's gap (above) is the only weak link feeding into
   this one — an un-normalized stem-form id from boundary 1 would still construct a syntactically-valid but
   semantically-wrong `directive:001-architectural-integrity-standard` URN here, undetected.

**WP03** (`resolver.py`), four boundaries enumerated in its own audit table:

1. `_resolve_directive_base`'s `activated_directives` base normalization — **CAUGHT**. T011 step 6 is a
   direct, named RED-against-unmodified-`resolver.py` fixture: stem-form `activated_directives` entry (same
   `001-architectural-integrity-standard` id) must resolve to the canonical `DIRECTIVE_001` form in
   `resolve_project_governance(...).directives`. This is the exact test WP02 lacks for its structurally
   identical boundary 1.
2. Union of `doctrine.selected_directives` onto the base — **CAUGHT/safe via pre-existing, unchanged
   validation**: `_resolve_directive_base`'s existing `missing = sorted(d for d in doctrine.selected_directives
   if d not in valid_ids)` / `raise GovernanceResolutionError(...)` block (verified live,
   `resolver.py:716-726`, untouched by this WP) already fails loud for any non-canonical entry before the
   union runs; this WP does not need a new fixture since the behavior is pre-existing and independently
   already exercised by the codebase's existing resolver test suite.
3. `resolve_project_governance`'s new `activated_paradigms` base — **CAUGHT**. T011 step 4 (FR-013) is a
   direct, named fixture. Structurally vacuous for normalization (same live-verified fact as WP02 boundary
   2 — no paradigm stem/canonical split exists anywhere in `src/`).
4. Union of `doctrine.selected_paradigms` onto the paradigm base — **CAUGHT/safe via pre-existing,
   unchanged** `_validate_paradigm_selection` (verified live, `resolver.py:616-629`), same reasoning as
   boundary 2.

**Conclusion for (b)**: WP03's audit is fully fixture-backed for every boundary that needs a fixture. WP02's
audit is fixture-backed for five of its six boundaries; boundary 1 is asserted correct ("Already correct by
this round's own design") without a fixture that would actually fail if that specific correctness claim were
false. This is Finding A1.

### Investigation (c) — plan.md vs spec.md vs tasks.md consistency; live citation re-verification

Re-verified against the live checkout, not trusted from the mission's own claims, a representative sample of
every `file:line`/symbol citation load-bearing to this mission's design (not an exhaustive sweep of every
number in a 2,600-line tasks corpus, but covering every citation cited more than once across spec/plan/WP
files, i.e. the ones a drift would actually break):

| Citation | Claimed | Live (verified) | Match |
|---|---|---|---|
| `pack_context.py` `_load_charter_activation_source` | 557-585 | def at 557; body through ~588 | match |
| `pack_context.py` `_read_list_key` | 609-615 | def at 609, raises on non-list | match |
| `resolver.py` `_resolve_directive_base` def | 675 | 675 | match |
| `resolver.py` `if doctrine.selected_directives:` branch | 716 (span 716-726) | line 716, `return ...` at 726 | match |
| `resolver.py` `resolve_project_governance` def | 815 | 815 | match |
| `resolver.py` `selected_paradigms = list(...)` | 848 | 848 | match |
| `resolver.py` `collect_governance_diagnostics` def | 937-952 | def at 937 | match |
| `action_doctrine_bundle.py` `_load_action_doctrine_bundle` signature | 142-152, `pack_context` param already present | confirmed at 142 | match |
| `action_doctrine_bundle.py` `doctrine_selection = _load_doctrine_selection(repo_root)` | 185 | 185 | match |
| `action_doctrine_bundle.py` `project_directives`/`selected_tactics`/`selected_paradigms` assignment | 189-191 | 189-191 | match |
| `action_doctrine_bundle.py` `roots = (...)` | 230-235 | 230 (tuple opens) | match |
| `delivery_table.py` `_classify_artifact_urns` `or set()` lines | 211-212 | 211-212 | match |
| `delivery_table.py` `start_urns` construction | 213-215 | 213-215 | match |
| `delivery_table.py` exclusion guard | 238 | 238 | match |
| `profile_resolution.py` `_normalize_directive_id` | 203-216 | def at 203, body through 220 (minor undercite of 4 trailing lines, not material) | match (near-exact) |
| `org_pack_discovery.py` `_read_org_required_selections`/`_REQUIRED_KIND_FIELDS` | public, in `__all__` | confirmed | match |
| `catalog.py` `DoctrineCatalog.tactics`/`.paradigms`/`.directives` all `frozenset[str]` | symmetric fields | confirmed | match |
| `test_action_bundle_delivery.py` four `_classify_artifact_urns(..., set())` sites | 4 occurrences | 4 occurrences at lines 88, 190, 330, 348 | match |
| `test_activation_consumers.py::test_context_bundle_none_path_matches_no_filter_at_all` | exists | line 355 | match |
| `test_answers_inert_and_org_union.py::TestOrgRequiredIdFormNormalizedBeforePromotion` | stem `001-architectural-integrity-standard`→canonical `DIRECTIVE_001` | confirmed lines 293-403 | match |
| FR-004's `init.py:889`/`:1220`/`:1227` call-chain (`command_installer.install` before `.kittify/config.yaml` write) | pre-write ordering | confirmed live, `cli/commands/init.py:882,889,1220,1227` | match |
| `command_installer.py:260`/`command_renderer.py:384,441-443` | `_render_command_skill`/`render`/`apply_spdd_blocks_for_project` | confirmed at 260/384/441-443 | match |
| WP05's `append_spdd_reasons_guidance` location + `bootstrap_text.py` call site | `charter_context.py`, re-exported, called from `bootstrap_text.py` | confirmed (call at bootstrap_text.py:332, 1-line drift from cited :332 — negligible) | match |
| `activation.py` current (pre-fix) body reads ONLY `governance:`/`directives:`, never `.kittify/config.yaml` | as described | confirmed by full read of the live file | match |

**No citation drift found** in this sample — a notably clean result for a mission whose own tasks phase
HALTed twice specifically on citation drift (per the WP05 tooling note). The extensive re-verification
discipline baked into every WP prompt ("re-verify against the live file... do not trust a citation without
checking") appears to have actually been applied when this tasks artifact was authored.

### Investigation (d) — WP dependency declarations vs actual data flow

Verified: WP01 (`src/charter/offering/spdd_reasons/activation.py`), WP02
(`src/charter/activation/action_doctrine_bundle.py`, `.../delivery_table.py`), and WP03
(`src/charter/activation/resolver.py`) are genuinely file-disjoint (owned_files cross-checked against
tasks.md) and have no runtime call-graph coupling — grepped `is_spdd_reasons_active` across
`action_doctrine_bundle.py`/`delivery_table.py`/`resolver.py`: zero hits; none of the three call WP01's
function, confirming the "no shared code" independence claim. WP04 (dependency: WP01) is correctly scoped —
its three owned test files reference only `is_spdd_reasons_active`, never `_load_action_doctrine_bundle` or
`resolve_project_governance` (WP04's own Context section explicitly re-checked this for
`test_answers_inert_and_org_union.py`'s three non-`TestThirdLedgerUntouched` classes and found them
orthogonal — config-promotion machinery, not activation gating). WP05 (dependency: WP01+WP02+WP03) is
correctly scoped since its doc content describes all three fixed functions. No missing dependency edge and
no over-declared one found.

### Investigation (e) — hunting for a fifth instance of the silent-collapse defect class

Checked, boundary by boundary, every union/exclusion boundary named across WP01/WP02/WP03 (the same list
enumerated under Investigation (b) above), specifically for: (i) a boundary not enumerated in either audit
table at all; (ii) a three-state value tested for `None`/non-empty but not explicit-empty (or vice versa);
(iii) WP01's own T002/T004 language for whether it satisfies "canonicalizes or fails loud" for all three
fields including the numeric-hint-slug directive matching path.

- **(i) Un-enumerated boundaries**: none found beyond WP02's own boundary 1, which IS enumerated in the
  audit table (with a "already correct" claim) but not fixture-backed — this is Finding A1, not a
  fresh un-enumerated boundary; it is a coverage gap on a *named* boundary, the same shape as
  TASKS-FRESH2-001 (a coverage gap on the org-required union), just on the sibling boundary one step
  earlier in the same function.
- **(ii) Missing explicit-empty vs. absent coverage**: checked every three-state consumer named in
  plan.md section (m)'s table against its WP's fixtures. `activated_directives`: `None` case covered
  (T007 step 2/3's non-explicit-empty fixtures, T007 step 5's tactics/paradigms `None` sibling), explicit-`[]`
  case covered (T007 step 4/FR-014). `activated_tactics`/`.activated_paradigms`: `None` case covered (T007
  step 5); no WP02 test constructs an EXPLICIT `activated_tactics: []`/`activated_paradigms: []` case
  distinct from `None` — but per boundaries 2/4's structural-fact reasoning, tactics/paradigms have no
  exclusion-filter consumer analogous to `delivery_table.py`'s directive guard (`start_urns` unconditionally
  includes whatever `selected_tactics`/`selected_paradigms` resolves to; there is no "exclude if present in
  activated_tactics" filter to get wrong the way FR-014 exists for directives) — re-verified live by reading
  `delivery_table.py`'s full `_classify_artifact_urns` body: no tactic/paradigm equivalent of the
  `NodeKind.DIRECTIVE` exclusion branch exists. So this asymmetry (directives get an explicit-empty test,
  tactics/paradigms don't) is not a gap — there is genuinely no explicit-empty *exclusion* behavior for
  tactics/paradigms to test. `resolver.py`'s `activated_directives`/`.activated_paradigms`: `None` (catalog
  fallback, pre-existing/unchanged), explicit-`{ids}` (T011 step 3/4 FR-012/FR-013), stem-form (T011 step 6)
  all covered; an explicit `frozenset()` case for either field is not separately fixture-pinned in WP03, but
  the existing, unchanged `is None` guard's `else` branch (`return sorted(activated_directives), "activation"`)
  already handles `frozenset()` correctly by construction (sorting an empty set returns `[]`) and this is
  pre-existing, not new, behavior this WP introduces — lower risk than boundary 1's genuinely-new
  normalization requirement.
- **(iii) WP01's own T002/T004 for the three fields including numeric-hint-slug**: T002 step 2's fixture
  matrix explicitly includes the numeric-hint-slug form (`038-structured-prompt-boundary`) as a *separate
  parametrized case* alongside canonical `DIRECTIVE_038`, and T004 step (f) requires `_is_directive_038`
  preserved verbatim as the matching logic layered on top of the new `activated_*` source. The oracle (T002
  step 3) explicitly forbids `x or set()` and requires `is None` disjunction for all three fields
  (paradigms/tactics/directives) uniformly. No gap found in WP01's own three-field coverage — this WP's
  own audit is the most rigorously fixture-backed of the three (it IS the mission's load-bearing artifact,
  per its own Objective statement).

**Verdict for (e)**: one further instance found — Finding A1 (WP02 boundary 1). It is the same shape as the
three that HALTed the tasks phase (an absent/un-normalized identifier silently collapsing to a wrong value
at a union boundary, unpinned by any fixture) but on the SAME normalization step the round's own audit
already fixed one hop downstream (the org-required union, boundary 3) — the base-assignment normalization
(boundary 1) was evidently assumed correct "by inheritance" from the org-required fix rather than
independently re-verified with its own fixture, which is exactly the "asserted in aggregate, not enumerated
boundary by boundary" failure mode the operator ruling's acceptance signal explicitly warns against.

---

## Findings (verbatim, also in the YAML carrier above)

| ID | Severity | Category | Summary |
|----|----------|----------|---------|
| A1 | HIGH | Coverage | WP02 boundary 1 (`project_directives` from `pack_context.activated_directives`, direct path) has no red-first fixture proving `_normalize_directive_id` is applied — every existing/planned T007 fixture either uses already-canonical ids on this path or exercises normalization only via the separate org-required-union path (boundary 3). WP03's structurally identical boundary DOES carry this coverage (T011 step 6). |
| A2 | LOW | Coverage | NFR-004 and C-004 (both "state X in the PR body" requirements) have no WP subtask/DoD line assigning ownership, unlike FR-009/SC-005's explicit "reviewed at PR time instead" delegation. |

## Verdict

**BLOCKED** — one HIGH finding (A1) per the recorder's `compute_verdict_from_findings` rule (any
high/critical finding blocks). Recommended remediation before implementation proceeds: add one red-first
fixture to WP02's T007 (a sibling to T007 step 6, but supplying the stem-form directive id directly via
`pack_context.activated_directives` rather than via org-pack promotion — e.g. `activated_directives:
frozenset({"024-locality-of-change"})`, asserting `_load_action_doctrine_bundle`'s `directive_ids` contains
canonical `DIRECTIVE_024`, not the raw stem), and add the corresponding line to WP02's boundary-1 audit-table
entry citing that fixture the way boundary 3's entry already cites T007 step 6. This is a small, targeted
addition (one fixture, one audit-table sentence) — not a re-open of the WP's design, which is already
correct; only its acceptance-criteria backing is incomplete.
