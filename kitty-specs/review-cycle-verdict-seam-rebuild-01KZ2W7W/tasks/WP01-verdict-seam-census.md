---
work_package_id: WP01
title: Verdict-seam census and its architectural check
dependencies: []
requirement_refs:
- NFR-007
planning_base_branch: pr/review-verdict-write-integrity-01KZ1CGF
merge_target_branch: pr/review-verdict-write-integrity-01KZ1CGF
branch_strategy: Planning artifacts for this mission were generated on pr/review-verdict-write-integrity-01KZ1CGF. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/review-verdict-write-integrity-01KZ1CGF unless the human explicitly redirects the landing branch.
created_at: '2026-08-03T08:13:56Z'
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: claude
history:
- at: '2026-08-03T08:13:56Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_verdict_seam_census.py
- tests/architectural/census/verdict_seam_IC01.yaml
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_verdict_seam_census.py
- tests/architectural/_baselines.yaml
- tests/_arch_shard_map.py
- tests/architectural/census/verdict_seam_IC01.yaml
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP01 - Verdict-seam census and its architectural check

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

## Objective

Three successive spec revisions of this mission pinned a count of verdict writers,
resolvers and readers — and all three were wrong ("3 writers, 2 resolvers, 5
frontmatter readers" measured out to ≥5 / ≥3 / ~20). NFR-007 exists because a
number an implementer cannot re-derive is not a requirement, it is folklore. This
WP builds the architectural check that *produces* the census — every later WP's
reduction target (WP07's reader count, WP08's retired-resolver list, WP13's
twelve consumer sites, WP14's five-reader polarity table) is derived from this
check's output, not asserted in prose.

**Independent test** (tasks.md): introduce a new verdict writer, location
resolver, or frontmatter reader anywhere in `src/`, and the check must go red.

This WP does **not** fix anything the census finds — it is a pure enumeration
tool. Do not "helpfully" patch a fail-open reader or a divergent resolver while
you are looking at it; that is WP07/WP08/WP14's work, and folding a fix in here
makes this WP's own diff-coverage and review surface unreviewable.

## Context & Constraints

Read in full before starting:

- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/spec.md` — "Verdict
  authority (the split, measured)", the Domain Language table, and User Story 4's
  four-reader table (kanban fail-open, cycle.py skip-and-continue, merge-gate
  fail-closed, arbiter uncaught crash)
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/plan.md` — IC-01
  ("Census and architectural checks")
- `tests/architectural/test_2093_authority_invariant.py` — **read this file
  fully before writing a line of the new check.** It already imports
  `_EVENT_SLOTS` (line 80: `_EVENT_SLOTS: frozenset[str] = frozenset(_RUNTIME_SLOTS)`,
  sourced from `src/specify_cli/status/reducer.py`'s `_RUNTIME_SLOTS`) as its
  single source of truth for which runtime fields are event-authoritative, and
  its `_READER_AUTHORITY_ROOTS` (line 303: `("status", "cli", "core",
  "task_utils", "dashboard")`) names the package roots it scans for a
  frontmatter-authority violation. Its AST helpers
  (`_reads_dynamic_field_via_extract_scalar`, `_is_frontmatter_attr_read`,
  `_reads_dynamic_field_via_attribute_access`, `_derive_reader_authority_modules`
  — lines 329-389) are the existing pattern for "derive a live set of modules
  that read frontmatter dynamically, then compare it to a declared authority
  set." This WP's reader enumeration reuses that pattern; it does not invent a
  second one.
- `tests/_arch_shard_map.py` — read the module docstring in full. The `arch` row
  is registered through `tests/_shard_registry.py`'s `register()`/`ShardGroup`
  seam and carries `default_fallback=True`, so a brand-new file under
  `tests/architectural/` is auto-covered by a deterministic hash bucket even
  without a manual table edit — but the surrounding `_ARCH_SHARD_N_FILES`
  tuples show the house convention is still to append new files to whichever
  shard is currently lightest by `def test_` count, for CI balance. Follow that
  convention rather than relying on the fallback.
- `tests/architectural/_baselines.yaml` — the existing baseline-registration
  file for architectural checks with a measured starting count; read its
  existing entries for the expected shape before adding one for this check.

**Constraints (binding)**:
- **A `retire` row with no retiring FR is a census failure.** This is the rule
  that stops WP08's reconciliation target being self-set at zero — see T002.
- **Reconcile, do not duplicate, the reducer's authority set.** `test_2093_
  authority_invariant.py` already treats `_EVENT_SLOTS` (from
  `status/reducer.py`) as authoritative and deliberately excludes `review`,
  `post_merge`, and `agent_utils` from `_READER_AUTHORITY_ROOTS` — those three
  packages are exactly where this mission's readers live. A second census with
  a different denominator over the same concept is a second authority, which is
  the exact defect class this mission exists to close. See T003.
- **Scope by concept, not by symbol signature.** `pre_review_gate.py`'s
  `SOURCE_MISMATCH` outcome (`src/specify_cli/review/pre_review_gate.py:583`) is
  a deliberate fail-open owned by a different mission (FR-009/FR-011,
  baseline/head `ScopeSource` identity) — it is not a review-cycle verdict
  reader and must not appear in this census. `src/specify_cli/review/
  verdict_aggregation.py` uses "verdict" for a different concept entirely
  (aggregating acceptance-criterion verdicts, not review-cycle approve/reject)
  and is likewise out of scope. See T004.

## Subtask T001 — Author the verdict-seam census check enumerating writers, resolvers and readers

- **Purpose**: Produce the one architectural check every later WP's reduction
  target derives from. Without this, WP07/WP08/WP13/WP14 each re-derive their
  own denominator by hand, and disagreements between them become invisible
  until an adversarial squad finds them — which is exactly how this mission's
  own three wrong pinned counts happened.
- **Steps**:
  1. Create `tests/architectural/test_verdict_seam_census.py`. Model its
     structure on `test_2093_authority_invariant.py`'s dual shape: an AST-driven
     *derivation* pass over a fixed set of scoped modules, plus a declared
     *expected-set* fixture the derivation is compared against.
  2. Enumerate three categories over the concept-scoped module set (T004 defines
     the scope precisely; do not scan all of `src/` — that is how the prior
     wrong counts happened):
     - **Writers** — functions that create or mutate a verdict record or the
       event's `ReviewResult`. Known members to seed the derivation against:
       `create_rejected_review_cycle` (`src/specify_cli/review/cycle.py:434`),
       `persist_arbiter_decision` (`src/specify_cli/review/arbiter.py:400`),
       `_persist_review_artifact_override`
       (`src/specify_cli/cli/commands/agent/tasks_materialization.py` — grep for
       the exact line, it moves between mission landings), and the `ReviewResult`
       construction inside `status/emit.py` (read-only for this mission per
       plan.md, but still a census member — the check must still be able to see
       it when auditing "does every writer have a resolver and a reader").
     - **Resolvers** — functions deriving a review-cycle directory from WP
       identity. Known members: `_review_cycle_wp_dir`
       (`src/specify_cli/review/cycle.py:35`), `_artifact_dirs_for_wp`
       (`src/specify_cli/post_merge/review_artifact_consistency.py:112` — note
       it returns a **list**, the exact-dir-plus-every-sibling fan-out plan.md's
       IC-06 risk note names), `_resolve_wp_slug`
       (`src/specify_cli/cli/commands/agent/tasks_materialization.py`), and
       `arbiter.py`'s own resolver inside `_find_review_cycle_artifact`
       (`src/specify_cli/review/arbiter.py:370` — it probes `feature_dir /
       "tasks" / wp_id`, the **bare** id, at line 388, which is the divergent-
       path defect IC-09 fixes later).
     - **Readers** — functions that parse a review-cycle artifact's frontmatter
       for its verdict. Known members: `agent_utils/status.py`'s kanban reader
       (fail-open `except Exception: return None` at
       `src/specify_cli/agent_utils/status.py:61`), `review/cycle.py`'s
       provenance scan (skip-and-continue, fold `97a9ecfae`),
       `post_merge/review_artifact_consistency.py`'s conflict finder
       (fail-closed structured finding), `review/arbiter.py`'s override reader
       (uncaught crash — no `except` at all around its frontmatter parse), and
       `cli/commands/agent/tasks_parsing_validation.py:296`'s
       `_get_latest_review_cycle_verdict`, which carries an explicit `# noqa:
       BLE001 — review-cycle artifact may be malformed; fail-open` comment (this
       is spec.md's "measured **five**, not four" correction — do not under-seed
       the derivation with only the four spec.md's User Story 4 table names in
       prose; the fifth is real and already commented as such in the code).
  3. Each category's derivation should use an AST or call-graph heuristic (mirror
     `test_2093_authority_invariant.py`'s `_reads_dynamic_field_via_attribute_access`
     shape) scoped to the concept boundary from T004 — a plain hand-typed list
     with no derivation mechanism would not go red when a new writer/resolver/
     reader is introduced, which is the exact NFR-007 failure mode this check
     must not have.
  4. Compare the derived set against the frozen expected-set fixture (T005's
     `tests/architectural/census/verdict_seam_IC01.yaml`) and fail on any drift in either direction —
     growth (a new member not yet classified) or shrinkage (a member silently
     disappearing, e.g. because a module was deleted without updating the
     contract).
- **Files**: `tests/architectural/test_verdict_seam_census.py`
- **Validation checklist**:
  - [ ] The check enumerates at minimum the five writers/resolvers/readers named
        above per category (adjust the exact count from what your derivation
        actually finds — do not hand-pin a number the check itself should be
        producing).
  - [ ] Adding a new function matching the writer/resolver/reader AST pattern
        anywhere in the scoped module set (proven by temporarily adding one,
        running the check, confirming red, then removing it) makes the check
        fail.
  - [ ] `mypy --strict` and `ruff` are clean on the new file.
- **Edge Cases**: A function that is both a resolver and a reader in one body
  (e.g. a helper that resolves a directory and then immediately reads the
  latest file's frontmatter) must be classified in **both** categories, not
  forced into one — the census's purpose is honest enumeration, not a tidy
  partition.

## Subtask T002 — Enforce: a `retire` row with no retiring FR is a census failure

- **Purpose**: Without this rule, a later WP (WP08's reconciliation, WP13's
  consumer unification) can mark a resolver `retire` in the contract fixture
  without actually landing the FR that retires it — silently self-setting the
  reduction target to zero and making WP17's mission-exit verification
  unable to tell the difference between "retired" and "never checked."
- **Steps**:
  1. In the contract fixture format (T005), give every census row a `status`
     field with allowed values including `active` and `retire`.
  2. When `status == "retire"`, require a non-empty `retiring_fr` field naming
     the FR that retires it (e.g. `FR-008` for a resolver WP08's reconciliation
     retires, `FR-007` for one WP13's unification retires).
  3. Add a check-level assertion: for every row where `status == "retire"`, the
     named `retiring_fr` must exist in `spec.md`'s Functional Requirements
     table (parse `spec.md`'s FR table or hard-code the known FR-id set — prefer
     parsing, since the FR table can grow) and must not itself be a `Status:
     Open` requirement this mission has not started (a "retire" claim pointing
     at an FR nobody has landed is exactly the self-set-to-zero failure this
     rule exists to catch).
  4. A `retire` row with an empty, missing, or unresolvable `retiring_fr` is a
     hard failure of this check — not a warning.
- **Files**: `tests/architectural/test_verdict_seam_census.py`,
  `tests/architectural/census/verdict_seam_IC01.yaml`
- **Validation checklist**:
  - [ ] A test fixture row with `status: retire` and no `retiring_fr` fails the
        check (prove it with a temporary malformed row, then remove it).
  - [ ] A `retire` row naming a real, landed FR passes.
  - [ ] Every row in the initial `IC-01.md` fixture that WP01 itself produces
        is `status: active` — this WP retires nothing; that comes later.
- **Edge Cases**: An FR-id typo (`FR-08` instead of `FR-008`) must fail loudly,
  not silently match nothing and pass by vacuous truth.

## Subtask T003 — Reconcile the denominator against `test_2093_authority_invariant.py`'s `_EVENT_SLOTS`

- **Purpose**: Prevent this census from becoming the second authority
  `test_2093_authority_invariant.py` already exists to prevent. That file
  imports `_EVENT_SLOTS` directly from `status/reducer.py`'s `_RUNTIME_SLOTS`
  (line 80) as its single source of truth for which runtime fields the event
  log is authoritative over, and its `_READER_AUTHORITY_ROOTS` (line 303)
  names `status`, `cli`, `core`, `task_utils`, `dashboard` as the package roots
  it audits for frontmatter-authority violations — deliberately excluding
  `review`, `post_merge`, and `agent_utils`, the three packages this mission's
  readers live in.
- **Steps**:
  1. Do not add `review`, `post_merge`, or `agent_utils` to
     `test_2093_authority_invariant.py`'s `_READER_AUTHORITY_ROOTS` as a way to
     "reuse" that check for this mission's readers — that file's authority
     model is about runtime-state fields dual-homed between the event log and
     WP frontmatter, not about review-cycle verdict readers. It is a distinct
     concept even though the mechanism (AST frontmatter-read detection) looks
     similar. Widening its root tuple would change what that file's own
     regression protects.
  2. Instead, in the new `test_verdict_seam_census.py`, import `_EVENT_SLOTS`
     from `status/reducer.py` directly (the same import
     `test_2093_authority_invariant.py` uses) wherever this check needs to know
     whether a given field is event-authoritative, rather than re-deriving that
     fact from a second read of `_RUNTIME_SLOTS` or hand-typing the field list.
  3. Add a short module-level comment in the new file naming
     `test_2093_authority_invariant.py` and stating explicitly why its
     `_READER_AUTHORITY_ROOTS` scope and this census's scope do not overlap —
     future maintainers must not "helpfully" merge the two checks.
- **Files**: `tests/architectural/test_verdict_seam_census.py`
- **Validation checklist**:
  - [ ] `test_2093_authority_invariant.py` is unmodified by this WP.
  - [ ] The new check imports `_EVENT_SLOTS` rather than re-deriving an
        equivalent constant.
  - [ ] The reconciliation rationale is documented in the new file's module
        docstring, not left implicit.
- **Edge Cases**: If a future reducer change removes `_EVENT_SLOTS` or renames
  it, both checks should fail identically (same import, same breakage) — that
  is a feature of sharing the import, not a risk to work around.

## Subtask T004 — Scope the census by concept, derived subtractively, excluding `pre_review_gate` and `verdict_aggregation`

- **Purpose**: "Verdict" is an overloaded word in this codebase, and a fixed
  allowlist of "known" modules is exactly the failure mode NFR-007 exists to
  close — it reads as compliant while it is blind to a new writer, resolver,
  or reader landing in a module nobody hand-typed into the list. The scope
  must be *derived* from the codebase each run and then narrowed by named,
  reasoned exclusions — it must never be built by additively listing today's
  known members.
- **Steps**:
  1. Derive the census's module scope programmatically each run: grep `src/`
     for `review-cycle` / `review_cycle` references (module names, string
     literals, docstrings, imports) to produce a candidate module set, then
     AST-classify each candidate module's functions against the writer/
     resolver/reader shapes from T001. Do not hand-type a fixed list of
     module paths as the scope — a grep-derived-then-excluded set is the only
     shape that reds when a wholly new *module* (not just a wholly new
     function in an already-known module) is introduced anywhere under
     `src/`.
  2. Subtractively exclude, by name and recorded reason, exactly the two known
     false positives the "review-cycle"/"review_cycle" grep will otherwise
     sweep in:
     - `src/specify_cli/review/pre_review_gate.py`'s `SOURCE_MISMATCH`
       outcome (line 583) — a deliberate fail-open over baseline/head
       `ScopeSource` identity divergence (FR-009/FR-011 of a different,
       already-landed mission), not a review-cycle verdict concept.
     - `src/specify_cli/review/verdict_aggregation.py` — aggregates
       **acceptance-criterion** verdicts (the `acceptance-verdict` CLI
       command's domain), a different sense of "verdict" than a review
       cycle's approve/reject/override.
     Record both exclusions, and the reason for each, as named constants the
     derivation consults — never a silent absence from the candidate set.
  3. Prove the derivation is concept-honest, not module-honest: temporarily
     add a **new module** under `src/specify_cli/review/` (not an edit to an
     already-known module) containing a function shaped like a writer (it
     writes a `review-cycle-*.md` file), run the check, confirm it reds
     naming the new module, then remove the temporary module. A check that
     only reds on a new function inside an already-known module has not
     proven concept-level derivation — that is the exact allowlist failure
     mode this subtask exists to close.
  4. Add a short comment in the new test file naming both exclusions and why,
     so a future contributor extending the census does not "helpfully" widen
     scope to catch a string match in either file.
- **Files**: `tests/architectural/test_verdict_seam_census.py`
- **Validation checklist**:
  - [ ] The scope is derived each run by grepping `src/` for
        `review-cycle`/`review_cycle` references and AST-classifying the
        result — it is not a hand-typed module allowlist.
  - [ ] Neither `pre_review_gate.py` nor `verdict_aggregation.py` contributes
        any writer/resolver/reader row to the census output, and both
        exclusions are named constants with recorded reasons, not silent
        absences from the candidate set.
  - [ ] A **new module** added under `src/specify_cli/review/` containing a
        function that writes `review-cycle-*.md` is proven to red the check
        (temporarily added, confirmed red, then removed) — an allowlist-
        shaped scope cannot satisfy this case, which is why it is required
        proof, not optional polish.
  - [ ] Each of the three categories (writer/resolver/reader) is
        independently red-provable: adding a new resolver reds the
        resolver row-set specifically, not merely the aggregate/global
        census count.
- **Edge Cases**: If a future refactor moves a genuine review-cycle-verdict
  function into `pre_review_gate.py` or `verdict_aggregation.py` (unlikely, but
  not impossible), the exclusion becomes wrong silently — the module docstring
  should state the exclusion is by *content*, not by filename, so a reviewer
  re-checks it if either file's purpose ever changes.

## Subtask T005 — Emit `tests/architectural/census/verdict_seam_IC01.yaml` and register the shard-map row

- **Purpose**: FR-020 makes the contract artifact the check's own expected-set
  fixture, not decorative prose nothing consults — a document the check does
  not read would go stale immediately, which is the exact failure this mission
  exists to close for the *code*'s naming, and must not be reintroduced for the
  *contract*'s own naming.
- **Steps**:
  1. Create `tests/architectural/census/verdict_seam_IC01.yaml`
     as the check's literal expected-set fixture (a machine-parseable table or
     embedded YAML/JSON block the test file loads at collection time — do not
     make the test read a second, separately-maintained Python constant while
     the Markdown file drifts unread).
  2. Give every row: category (`writer`/`resolver`/`reader`), module, function
     name, and `status` (`active` for this WP — see T002 for the `retire` shape
     later WPs will use).
  3. This file alone owns `tests/architectural/census/verdict_seam_IC01.yaml` —
     per plan.md's fragmented-census design (FR-020), do not write into the
     shared fold target `tests/architectural/verdict_seam_census.yaml` here;
     that fold is WP16/IC-12's job, after every retiring WP has landed its own
     `verdict_seam_IC0N.yaml` fragment. A legacy planning-era Markdown artifact
     exists elsewhere in this mission's directory tree from an earlier pass
     that predates the fragmented-census design named above — it is not the
     fold target and is not read or written by this WP.
  4. Register the new test file with `tests/_arch_shard_map.py`: append
     `"tests/architectural/test_verdict_seam_census.py"` to whichever of
     `_ARCH_SHARD_1_FILES` / `_ARCH_SHARD_2_FILES` / `_ARCH_SHARD_3_FILES` is
     currently lightest by `def test_` count (grep-count each shard's files;
     do not guess). This is a convention, not a hard requirement — the row's
     `default_fallback=True` auto-covers an unregistered file via a
     deterministic hash bucket — but every existing row follows the explicit
     convention and this WP should not be the first exception.
  5. Add an entry to `tests/architectural/_baselines.yaml` for the new check
     following the existing entries' shape, recording the measured starting
     census size this WP's own derivation produces.
- **Files**: `tests/architectural/census/verdict_seam_IC01.yaml`,
  `tests/_arch_shard_map.py`, `tests/architectural/_baselines.yaml`
- **Validation checklist**:
  - [ ] `verdict_seam_IC01.yaml` is the literal fixture `test_verdict_seam_census.py`
        loads — editing a row in the YAML and re-running the check changes its
        pass/fail outcome (prove this once).
  - [ ] `tests/architectural/verdict_seam_census.yaml` (the fold target, not
        yet created — WP16/IC-12's job) is untouched by this WP.
  - [ ] The new test file appears in exactly one `_ARCH_SHARD_N_FILES` tuple.
  - [ ] `_baselines.yaml`'s new entry matches the existing entries' schema.
- **Edge Cases**: If `tests/architectural/census/` does not yet exist as a
  directory, create it — do not flatten `verdict_seam_IC01.yaml` directly into
  `tests/architectural/`.

## Branch Strategy

Planning artifacts for this mission were generated on
`pr/review-verdict-write-integrity-01KZ1CGF`. This WP is a root WP with no
dependencies; worktrees are allocated per lane from `lanes.json` at
`spec-kitty implement WP01` time. Completed changes merge back into
`pr/review-verdict-write-integrity-01KZ1CGF` unless the human explicitly
redirects the landing branch.

## Definition of Done

- `tests/architectural/test_verdict_seam_census.py` exists, derives a live
  writer/resolver/reader set by grepping `src/` for `review-cycle`/
  `review_cycle` references and AST-classifying the result, subtractively
  excluding `pre_review_gate.py` and `verdict_aggregation.py` as named,
  reasoned exclusions — not by an additive, hand-typed module allowlist — and
  fails when a new member is introduced anywhere in that derived scope
  (proven, not asserted) (T004).
- A **new module** added under `src/specify_cli/review/` containing a function
  that writes `review-cycle-*.md` reds the check — proven by temporarily
  adding one, confirming red, then removing it. This is the specific case a
  hand-typed allowlist cannot satisfy, and is distinct from (and in addition
  to) a new function landing in an already-known module (T004).
- Each classification leg (writer, resolver, reader) is independently
  red-provable: adding a new resolver reds the resolver row-set specifically,
  not merely the aggregate/global census count (T001, T004).
- The `retire`-with-no-`retiring_fr` rule (T002) is implemented and proven with
  a temporary malformed fixture row.
- `test_2093_authority_invariant.py` is untouched; the new check imports its
  `_EVENT_SLOTS` rather than duplicating it (T003).
- `pre_review_gate.py` and `verdict_aggregation.py` contribute zero rows to the
  census (T004).
- `tests/architectural/census/verdict_seam_IC01.yaml` is the check's actual
  fixture, not a parallel document (T005).
- The new test file is registered in `tests/_arch_shard_map.py` and
  `tests/architectural/_baselines.yaml`.
- `mypy --strict` and `ruff` are clean on every touched file, zero new
  suppressions.
- [ ] **NFR-002** — every function this WP touches ends at cyclomatic complexity ≤15: `uv run ruff check --select C901 <touched files>` is clean. Extract helpers rather than leaving a function at 16+.

## Risks & Mitigations

- **Under-scoping the reader category** (spec.md's own history: three prior
  revisions undercounted). Mitigate by seeding the derivation with all five
  named readers above, including the easily-missed `tasks_parsing_validation.py:296`
  fail-open leg, and by proving the AST/call-graph heuristic actually catches a
  freshly-added sixth reader before considering T001 done.
- **Scope creep into a second authority table.** Mitigate by T003's explicit
  reconciliation comment and by never widening
  `test_2093_authority_invariant.py`'s own root tuple.
- **The contract fixture becoming decorative.** Mitigate by making the check
  load `IC-01.md` at collection time (not import a separately-maintained
  Python literal that happens to agree with it today) — a fixture the check
  does not actually read is FR-020's exact failure mode.
- **Conflating this WP's enumeration with a later WP's fix.** Mitigate by
  treating every census finding as `status: active` in this WP's own fixture —
  resist fixing a fail-open reader or divergent resolver while it is in front
  of you; that work belongs to WP07/WP08/WP14.

## Reviewer Guidance

- Confirm the census actually reds on a freshly-introduced writer, resolver,
  and reader — ask for the before/after proof, do not accept a check that only
  passes on the current tree.
- Confirm the fifth reader (`tasks_parsing_validation.py`'s fail-open helper)
  is present — a common shortcut is to seed the derivation from spec.md's
  four-row User Story 4 table alone and miss the fifth the code itself already
  comments as fail-open.
- Confirm `test_2093_authority_invariant.py` was not edited, and that the new
  check imports rather than duplicates `_EVENT_SLOTS`.
- Confirm no row in `IC-01.md` is `status: retire` — this WP retires nothing.
- Confirm `pre_review_gate.py` / `verdict_aggregation.py` are named as explicit
  exclusions with a stated reason, not silently absent from the scope list.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-03T08:13:56Z – system – lane=planned – Prompt created.

---

### Updating Lane Status

Use: `spec-kitty agent tasks move-task WP01 --to <lane> --note "message"`

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
