---
work_package_id: WP02
title: Structural docs lint + config-SSOT
dependencies:
- WP01
requirement_refs:
- FR-007
- FR-011
- NFR-003
- NFR-005
- NFR-006
planning_base_branch: docs/common-docs-section-audit
merge_target_branch: docs/common-docs-section-audit
branch_strategy: Planning artifacts for this mission were generated on docs/common-docs-section-audit. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/common-docs-section-audit unless the human explicitly redirects the landing branch.
created_at: '2026-07-22T16:30:00+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
history:
- timestamp: '2026-07-22T16:30:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: scripts/docs/
create_intent:
- scripts/docs/docs_structural_lint.py
- tests/docs/test_docs_structural_lint.py
execution_mode: code_change
model: sonnet
owned_files:
- scripts/docs/docs_structural_lint.py
- tests/docs/test_docs_structural_lint.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP02 – Structural docs lint + config-SSOT

## ⚡ Do This First: Load Agent Profile

**Before reading any further**, load the `python-pedro` implementer profile via the `/ad-hoc-profile-load`
skill. Adopt its identity, governance scope, boundaries, and the initialization declaration it prints.
Everything below is authored for that profile: TDD-first (red-first), type-safe Python 3.11+, complexity
≤15, zero suppressions, focused tests per branch. Do not begin editing until the profile is loaded and its
init declaration is on the record.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Land `scripts/docs/docs_structural_lint.py` — the durable mechanical successor to the retired anti-sprawl
ratchet — implementing the 4 checks in `contracts/docs-structural-lint.md`, **each scoped so a POST-MOVE-SHAPED
fixture passes with zero violations and the current clean COHORTS pass** (NFR-003), and LOADING all policy from
the WP01 styleguide config block (`structural_lint_config:`) (FR-011, no hard-coded divergent policy). Ship it
red-first (a regression fixture reintroducing each of the 4 finding-classes), assert lint-behaviour ==
styleguide-config, and complete in < 5 s.

> **Timing boundary (do NOT breach — this WP does NOT gate the live tree).** The 7
> `docs/architecture/audits/2026-05-*.md` and the 3 `docs/plans/notes/` shadows are **live point-in-time /
> shadow-basename violations by design** until WP03 relocates the audits and WP04 folds the shadows. Therefore
> **WP02 does NOT run the lint over the real `docs/` tree asserting zero-TOTAL violations**, and **WP02 does NOT
> enable the CI gate** — CI wiring + the live post-move zero-violation assertion belong to **WP05** (which
> depends on WP02/WP03/WP04, so the tree is clean when it enables the gate). WP02's own zero-violation proof runs
> against a **synthetic post-move-shaped fixture** (audits placed under `plans/engineering-notes/`, no
> `plans/notes/` shadows), plus discriminating **live cohort-clean assertions** on the cohorts that ARE already
> clean.

**Success criteria**:
- `python -m scripts.docs.docs_structural_lint` runs in < 5 s; `--json` emits
  `{"violations": [{rule_id, path, message}], "checked": <int>}`.
- The 4-class fixture is caught 100% (SC-003); the **post-move-shaped fixture** is zero-violation (NFR-003).
- The live COHORT-clean assertions pass: `adr/**` era-dated (×132), `plans/{research,investigations}/**`,
  the 38 `index.md` / 38 `README.md` nav basenames, and the 3 frontmatter-less ADR READMEs.
- The lint reads the `structural_lint_config:` block; a test proves behaviour matches config (FR-011).

## Context & Constraints

- **Charter**: `.kittify/charter/charter.md` — ATDD/red-first, tiered rigour (this is glue-tier enforcement
  tooling with focused unit tests per check), no suppressions.
- **Read before editing**: `contracts/docs-structural-lint.md` (AUTHORITATIVE — the invocation, the 4-rule
  table with exact scope/exemptions, the §Configuration SSOT, the fixture requirement, the non-goals),
  `plan.md` (IC-02), `spec.md` (FR-007/011, NFR-003/005/006, US2 acceptance scenarios 1–4; FR-008/CI wiring is
  WP05's, post-move),
  `research.md` (D2 — verified clean-tree counts), `data-model.md` (rule & violation shape).
- **Dependency on WP01 (FR-011)**: the lint LOADS policy from the `common-docs.styleguide.yaml` config block
  WP01 authored. Coordinate the exact key path with WP01's T005 follow-up note. If WP01 has not landed, start
  against a small local stub mirroring the contract's §Configuration keys, then switch to the real config
  and confirm the key path before merge — do NOT hard-code a divergent policy (C-005).
- **Clean-tree calibration (research.md D2 — verified counts, all must PASS)**: 38 `index.md`, 38 `README.md`,
  132 dated files under `adr/`, the STAY subtrees `plans/{research,investigations}/**`, and exactly 3
  frontmatter-less files (`docs/adr/{1.x,2.x,3.x}/README.md`). These are allowlisted/exempt, NOT violations.
- **Non-goals (contract)**: the lint does not move files or rewrite links; it does not resurrect the ratchet's
  `CANONICAL_SECTIONS`/`section_missing_index` absolute-count behaviour — completeness replaces existence,
  no absolute count.
- **Reverse edge**: WP01 cites this module path (`scripts/docs/docs_structural_lint.py`). Land it exactly
  there; if you must diverge, flag WP01's Activity Log so its citations reconcile.

## Branch Strategy

- **Strategy**: coord topology; execution worktree allocated per computed lane from `lanes.json`.
- **Planning base branch**: `docs/common-docs-section-audit`
- **Merge target branch**: `docs/common-docs-section-audit`

> Populated by `spec-kitty agent mission tasks` / `finalize-tasks`. Do not change manually.

## Subtasks & Detailed Guidance

### Subtask T006 — Implement the 4 scoped checks

- **Purpose**: The mechanical guard core (FR-007). Each check is independently testable and scoped to pass the
  clean tree.
- **Steps** (per `contracts/docs-structural-lint.md` rule table):
  1. Module skeleton: `python -m scripts.docs.docs_structural_lint [--json] [DOCS_ROOT=docs]`. Structure it as
     4 pure functions `check_index_completeness(...)`, `check_point_in_time_placement(...)`,
     `check_shadow_tree_basename(...)`, `check_frontmatter_contract(...)`, each returning
     `list[Violation]` where `Violation = {rule_id, path, message}` (a `@dataclass` or `TypedDict`). A `run()`
     aggregates, prints (`--json` or human), and exits nonzero iff any violation. Keep each function
     complexity ≤15 — extract walk/parse helpers.
  2. `index_completeness`: ONLY for sections in `curated_complete_sections` (initially `architecture/`). Fail
     when a non-index page in that section is absent from its `index.md`. **Subdir-recursion semantics (PIN):**
     the check recurses into the curated-complete section's SUBDIRECTORIES — a page under
     `architecture/assessments/…` (e.g. a STAYING `architecture/assessments/code-as-a-crime-scene-overview.md`)
     MUST be enumerated in `architecture/index.md` or the check fails. WP03 T017 enumerates every non-index
     `.md` under `architecture/` (incl. subdirs) to satisfy exactly this. Message names the missing page + the
     section index. Every other section index is a landing page — exempt.
  3. `point_in_time_placement`: fail when a file lives OUTSIDE `plans/**`, is not allowlisted, AND EITHER its
     basename matches a config `point_in_time_patterns` entry (e.g. `^\d{4}-\d{2}`) OR it self-declares
     point-in-time via a **config `point_in_time_markers`** signal — do NOT guess the self-declaration. Read the
     concrete markers from the styleguide `structural_lint_config:` (a machine-checkable list, e.g. frontmatter
     `field: value` pairs or a description phrase) authored by WP01 T002; the `883-*` dossiers do NOT match
     `^\d{4}-\d{2}`, so they are caught (only) via a `point_in_time_markers` signal, not by pattern. Allowlist:
     `adr/**` + `plans/research/**` + `plans/investigations/**` (from config). Message names the file + its
     canonical home.
  4. `shadow_tree_basename`: fail when the same NON-NAV content basename exists under two distinct section
     subtrees. Exempt nav basenames (`index.md`, `README.md`, `toc.yml`) + era files (`README-N.x.md`,
     `00-SYNTHESIS.md`) from config. Content-duplicate check, NOT an absolute basename-uniqueness count
     (NFR-005). Message names both paths.
  5. `frontmatter_contract`: fail when an IN-SCOPE page lacks a required frontmatter field. In-scope EXCLUDES
     section `README.md` landing pages; the 3 frontmatter-less ADR READMEs are allowlisted (#2227). Parse
     frontmatter with `yaml.safe_load` of the `---` block. Message names the file + missing field(s).
- **Files**: `scripts/docs/docs_structural_lint.py`.
- **Validation**: `--json` shape matches the contract; module imports cleanly; ruff + mypy clean.
- **Edge cases**: files with no frontmatter block at all (treat as missing all required fields, unless
  excluded); symlinks/generated files under `docs/` — skip pinned `toc.yml`/inventory by nav-exemption.

### Subtask T007 — LOAD policy from the WP01 styleguide config block (FR-011)

- **Purpose**: One policy store, not two (C-005). The lint must not hard-code policy that can diverge from
  doctrine.
- **Steps**:
  1. Add a `load_config()` that reads `src/doctrine/styleguides/built-in/common-docs.styleguide.yaml` and
     navigates to the **concrete wrapper key `structural_lint_config:`** (the constant WP01 T002 authored —
     this is the pinned interface contract; confirm it is present via WP01's T005 note). It returns a typed
     config object (dataclass) exposing: `curated_complete_sections`, `point_in_time_patterns`,
     `point_in_time_markers`, `point_in_time_allowlist`, `frontmatter_required_fields`,
     `frontmatter_in_scope_exclusions`, `shadow_tree_nav_exemptions`, `concern_bucket_to_section`.
  2. Thread the config into each check — no literal section/pattern/field lists inside the check bodies.
  3. **Fail LOUD** (clear error naming the missing `structural_lint_config:` block, nonzero exit) if the block
     is missing/malformed — do NOT silently fall back to an inline default (that recreates the drift C-005
     forbids). A missing block is a hard error, never a soft default.
- **Files**: `scripts/docs/docs_structural_lint.py`.
- **Validation**: grepping the module for a hard-coded `"architecture"` / `^\d{4}-\d{2}` / frontmatter field
  list inside check bodies finds none (they come from config); mypy clean.
- **Edge cases**: the styleguide path must resolve from the repo root regardless of CWD — anchor it off the
  module/repo root, not `os.getcwd()`.

### Subtask T008 — Red-first regression fixture (4 finding-classes)

- **Purpose**: ATDD teeth (Charter Check; SC-003). Prove each check catches its class BEFORE proving the tree
  is clean.
- **Steps**:
  1. New file `tests/docs/test_docs_structural_lint.py`. Build a temp fixture docs tree (tmp_path) OR minimal
     in-memory inputs that reintroduce ONE instance of each class:
     - a curated-complete section whose `index.md` omits a sibling page (index_completeness);
     - a `report-2026-05.md` placed OUTSIDE `plans/**` and not allowlisted (point_in_time_placement);
     - two files sharing a non-nav content basename across two section subtrees (shadow_tree_basename);
     - an in-scope page missing a required frontmatter field (frontmatter_contract).
  2. Assert each seeded instance produces exactly its `rule_id` violation (100% detection). Use realistic,
     production-shaped paths/filenames (not `foo.md`).
  3. Structure so the test is RED before T006/T007 land and GREEN after (red-first order in the Activity Log).
- **Files**: `tests/docs/test_docs_structural_lint.py`.
- **Validation**: `pytest tests/docs/test_docs_structural_lint.py -q` — each class asserted; runs fast.
- **Edge cases**: seed the fixture with its OWN styleguide config (or reuse the real one) so the fixture's
  curated-complete set/allowlist is deterministic and not coupled to future config edits.

### Subtask T009 — Post-move-shaped zero-violation fixture + live cohort-clean assertions

- **Purpose**: NFR-003 — the guard must not force churn on correctly-placed files, proven WITHOUT gating the
  live pre-move tree (the 7 audits + 3 shadows are live violations by design until WP03/WP04 land). Two proofs:
  (a) a synthetic post-move-shaped fixture is zero-violation; (b) the cohorts that ARE already clean on the
  real tree stay clean.
- **Steps**:
  1. **Post-move-shaped fixture (the zero-TOTAL proof):** build a synthetic docs tree that mirrors the tree
     AFTER WP03/WP04 land — the 2026-05 audits under `plans/engineering-notes/architecture-audits/`, no
     `plans/notes/` shadow basenames, `architecture/index.md` enumerating its (sub-)members. Run all 4 checks
     over THIS fixture and assert **zero violations**. Do **NOT** run a zero-TOTAL assertion over the real
     `docs/` tree — that tree legitimately carries the 7 audit point-in-time violations until WP03 relocates
     them (WP05 owns the live post-move zero-violation gate).
  2. **Live cohort-clean assertions (discriminating, on the real tree):** assert the already-clean cohorts do
     NOT trip: `adr/**` era-dated files (132) do NOT trip point_in_time; `plans/{research,investigations}/**`
     pass (allowlisted); the 38 `index.md` / 38 `README.md` nav basenames do NOT trip shadow_tree; the 3
     `docs/adr/{1.x,2.x,3.x}/README.md` do NOT trip frontmatter. These are cohort assertions, NOT a whole-tree
     zero-total assertion.
  3. Assert each run completes in < 5 s (time-box with a generous margin; NFR-003).
- **Files**: `tests/docs/test_docs_structural_lint.py`.
- **Validation**: the post-move fixture is zero-violation; the cohort assertions are discriminating (would fail
  if scope/allowlist were wrong); no assertion demands zero-TOTAL over the live pre-move tree.
- **Design note (NOT an edge case — by design):** the 7 `docs/architecture/audits/2026-05-*.md` are LIVE
  point-in-time placement violations on the current tree by design; they are RESOLVED by WP03's relocation to
  `plans/engineering-notes/architecture-audits/` (and the 3 `plans/notes/` shadows by WP04's folds). WP02 must
  not pretend the live tree is zero-total; it proves calibration via the post-move fixture + cohort assertions,
  and WP05 runs the real-tree zero-violation gate once the moves have landed.

### Subtask T010 — Config-SSOT agreement test (FR-011)

- **Purpose**: Prove the lint's runtime behaviour == the styleguide config (single source of truth, C-005).
- **Steps**:
  1. Load the styleguide config directly in the test; assert the lint's `load_config()` returns exactly those
     values (curated-complete set, allowlist, patterns, required fields, exclusions).
  2. Add a behavioural agreement: mutate a copy of the config (e.g. add a section to `curated_complete_sections`)
     and assert the lint's index_completeness now considers that section — proving the check READS config, not
     a constant. (Do NOT mutate the real styleguide file — operate on an in-memory/temp copy.)
- **Files**: `tests/docs/test_docs_structural_lint.py`.
- **Validation**: the agreement test fails if any check hard-codes policy (it would ignore the mutated config).
- **Edge cases**: keep this test resilient to WP01 adding EXTRA config keys — assert on the keys the lint
  consumes, not exact dict equality of the whole block.

> **CI wiring (FR-008) is deliberately NOT in WP02.** Enabling the lint in
> `.github/workflows/docs-freshness.yml` while the 7 audits are still live point-in-time violations would red
> the gate on this branch until WP03/WP04 land. CI enablement + the live post-move zero-violation assertion are
> **WP05's** (it depends on WP02/WP03/WP04, so the tree is clean when it turns the gate on). WP02 just verifies
> the lint completes in < 5 s locally (NFR-003).

## Test Strategy

- **Mandatory tests** live in `tests/docs/test_docs_structural_lint.py`: 4-class detection (T008),
  post-move-shaped fixture zero-violation + live cohort-clean assertions + < 5 s (T009), config-SSOT
  agreement (T010). No zero-TOTAL assertion over the live pre-move `docs/` tree (that gate is WP05's).
- Run: `pytest tests/docs/test_docs_structural_lint.py -q`, then `pytest tests/docs/ -q` (no regressions),
  then `ruff check scripts/docs/docs_structural_lint.py tests/docs/test_docs_structural_lint.py` and
  `mypy scripts/docs/docs_structural_lint.py`.
- Red-first: commit the fixture RED before the checks make it GREEN (Activity Log order).

## Risks & Mitigations

- **False positives on nav/dated/README files** (NFR-003): the scope/exemptions are load-bearing — T009's
  cohort assertions are the safety net; if a cohort trips, fix the scope, do not weaken the check globally.
- **Hard-coded policy drift** (FR-011): T010 catches it; keep every list/pattern in config.
- **CWD-sensitive config path**: anchor the styleguide path off the repo root, verified by running the lint
  from a subdirectory in a test.
- **Complexity creep**: 4 checks in one module can exceed the 15 ceiling — extract deterministic
  walk/parse/match helpers and test them directly.

## Review Guidance (reviewer-renata / opus)

Verify: the 4-class fixture genuinely RED-then-GREEN (not a tautology); no check body hard-codes a section /
dated pattern / frontmatter field / point-in-time marker (all from the `structural_lint_config:` block — grep
the module); the **post-move-shaped fixture** is zero-violation and the **live cohort assertions** are
discriminating (and there is **NO** zero-TOTAL assertion over the live pre-move tree, and **NO** CI enablement
— both are WP05's, post-move); `load_config()` fails LOUD on a missing `structural_lint_config:` block (no soft
default); the config-SSOT agreement test actually exercises config-reading (the mutated-config behavioural
assert); `--json` shape matches the contract; the lint lands at exactly `scripts/docs/docs_structural_lint.py`
(WP01 cites it); < 5 s; ruff/mypy clean, no suppressions.

## Activity Log

> **CRITICAL**: entries in chronological order (oldest first, newest last). Append at the END.

- 2026-07-22T16:30:00Z – system – Prompt created.
</content>
