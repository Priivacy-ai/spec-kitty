---
work_package_id: WP03
title: 'SK-08 rerank: canonical-verb outranks domain-keyword'
dependencies:
- WP02
requirement_refs:
- FR-006
- FR-007
- C-002
- C-004
planning_base_branch: feat/dispatch-dry-run-route-only-3840
merge_target_branch: feat/dispatch-dry-run-route-only-3840
branch_strategy: Planning artifacts for this mission were generated on feat/dispatch-dry-run-route-only-3840. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/dispatch-dry-run-route-only-3840 unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/invocation/router.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/invocation/router.py
- CHANGELOG.md
- tests/specify_cli/invocation/test_router.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP03 – SK-08 rerank: canonical-verb outranks domain-keyword

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Fix `ActionRouter.route()`'s SK-08 selection defect: today a lone/weak `domain_keyword`
candidate can outrank the request's own `canonical_verb` match via `routing_priority`, and a
lone domain-keyword candidate auto-selects instead of failing closed. After this WP, a
canonical-verb candidate always beats a domain-keyword candidate regardless of
`routing_priority`, and any zero-verb-tier resolution (one or more domain-keyword-only
candidates) raises `ROUTER_AMBIGUOUS` instead of auto-selecting (spec.md FR-006/FR-007, User
Story 3, SPEC-KITTY-LEDGER.md:2727 SK-08).

## Context

**This WP depends on WP02** — it lands strictly after WP02's `alternatives=` edits to
`route()`'s single-candidate return and tiebreaker block, per spec.md's operator decision
(Clarifications #1): the additive, lower-risk dry-run + `alternatives` work must not stall
on this riskier behavioral fix, because this fix changes selection behavior on **every real
(Op-opening) dispatch call**, not just the new dry-run path. Do not start this WP until
WP02's implementation commit has landed and its ATDD tests are GREEN.

**Write-scope overlap with WP02 (spec.md C-002, accepted, not guaranteed cleanly
revertible)**: this WP restructures the same two statements inside `route()` that WP02 just
edited — the `if len(candidates) == 1:` single-candidate return and the `routing_priority`
tiebreaker block. This WP's diff is computed against the **post-WP02** state of those lines
(which already carries `alternatives=` population) — do not attempt to write this WP's
change as if WP02 had not landed. Reverting this WP alone may require reverting or
hand-resolving WP02's `alternatives=` edits to those same lines first; this is the accepted,
stated property ("own commit, auditable and cherry-pickable," not "independently, cleanly
`git revert`-able regardless of WP2").

**The rerank rule, precisely** (FR-006/FR-007 — read both in full, they cross-reference each
other's scope boundary):
- A canonical-verb candidate beats a domain-keyword candidate **regardless of
  `routing_priority`**, cross-tier, always.
- `routing_priority` continues to break ties **within the canonical-verb tier only** —
  between two canonical-verb candidates — unchanged from today. It is *removed* only as a
  way for a domain-keyword candidate to outrank a canonical-verb one.
- `routing_priority` does **not** survive as a tiebreaker between two-or-more
  domain-keyword-tier candidates considered in isolation (zero verb-tier candidates
  present): that scenario is governed exclusively by FR-007 — whenever zero verb-tier
  candidates exist, the router **must** raise `ROUTER_AMBIGUOUS` regardless of how many
  domain-keyword-tier candidates there are or how their `routing_priority` values compare.
  The pre-existing priority-based auto-select no longer applies once there are zero
  verb-tier candidates.
- `test_router_priority_tiebreaker_selects_higher_priority` (canonical-verb-vs-canonical-verb
  intra-tier priority tiebreak) **must keep passing unmodified** — this is a hard
  requirement stated explicitly in FR-006, not a nice-to-have.

**New `ROUTER_AMBIGUOUS` raise sites and the FR-009 confidence-key obligation (C-002,
carried forward from WP01)**: this WP's restructuring of `route()` introduces **new/
restructured** `RouterAmbiguityError` raise sites — the lone-candidate case (AC-2) and the
2+-keyword-tier-candidates case (AC-4) — that did not exist when WP01 fixed the
confidence-key gap on the *one* raise site current code has (the post-tiebreaker "still
ambiguous" raise). **This WP inherits the same confidence-key obligation for every new raise
site it introduces**: every candidate dict on these new raise sites must carry the
`confidence` key, sourced the same way winning-candidate dicts already are elsewhere in
`route()`. **Do not reintroduce the pre-FR-009 candidate-dict shape
(`profile_id`/`action`/`match_reason` only) on any new raise site** — this is an explicit,
named regression FR-009 calls out by name.

**Downstream/external consumer impact (WP3's own `CHANGELOG.md` obligation)**: this WP
changes what auto-routed (no `--profile`) `dispatch` calls select or reject on the CLI's
most commonly invoked ad-hoc entry point. Every spec-kitty-managed project's own
`CLAUDE.md`/`AGENTS.md` "Skill Routing" section instructs agents to run `spec-kitty dispatch
"<request verbatim>"` with no `--profile` for ad-hoc requests — including
`team-kitty-missions`, `muster-missions`, and other spec-kitty consumer repos. After this WP
lands, some previously-succeeding auto-routed calls that today auto-select a lone/weak
domain-keyword candidate will instead raise `ROUTER_AMBIGUOUS` (exit 1) rather than silently
opening an Op under a possibly-wrong profile. **This WP's implementation commit must include
a `CHANGELOG.md` entry** stating explicitly that some previously-successful no-`--profile`
`dispatch` calls will now exit 1 with `ROUTER_AMBIGUOUS` instead of auto-selecting, so
downstream consumers upgrading their `spec-kitty` CLI pin are not surprised. `CHANGELOG.md`
is a repo-root symlink to `docs/changelog/CHANGELOG.md` — hand-edited Markdown, in scope for
markdown lint and the docs-freshness page-inventory check (it is tracked in
`docs/development/3-2-page-inventory.yaml`).

**Out of scope (C-004)**: `tk-watch`'s existing `TK_WATCH_PROFILE`/`--profile` pin
workaround for SK-08 continues to work unmodified after this fix (it uses the explicit-hint
router path, untouched by this change) and becomes unnecessary as an SK-08-specific
workaround once this WP lands — but this mission does **not** modify `tk-watch`'s code. Do
not touch any file outside this WP's `owned_files`.

**Accepted mid-mission routing-consistency risk (spec.md Clarifications #5)**: `route()` is
pure and stateless, re-evaluated on every call. A spec-kitty mission whose WP subagents
dispatch across the span of time during which this WP merges could see two auto-routed
calls for similar request text resolve to different profiles before and after the rerank
lands. This is accepted as inherent to any bug fix to `router.py`'s selection logic, already
adjudicated by the operator — not something to raise as an open question during
implementation, and not mitigated further (no mid-mission routing-version pin).

**ATDD-First (charter C-011 / spec.md C-001)**: this WP's failing-first tests (T011) are
committed as their own commit, before the implementation commit (T012–T013), with **RED
verified on WP02's final commit** (today's code auto-selects the domain-keyword candidate,
auto-selects the lone candidate, and lets `routing_priority` decide among keyword-tier-only
candidates — all three assertions fail against current behavior) and **GREEN on this WP's
final commit**.

## Marker + CI job for every new test (verified against `.github/workflows/*.yml`)

- **`tests/specify_cli/invocation/test_router.py`** — existing module marker `pytestmark =
  [pytest.mark.unit, pytest.mark.fast]`. New tests MUST carry the same markers (do not
  invent a new one). Collected by: `doctrine-charter-tests`
  (`.github/workflows/doctrine-charter-tests.yml`, path-triggered on
  `tests/specify_cli/invocation/**`, runs `-m "fast and not windows_ci and not timing"`) and
  `fast-tests-core-misc`'s `specify-cli-rest-2` shard (`.github/workflows/ci-quality.yml`,
  positional path `tests/specify_cli/invocation`, runs `-m "fast and not windows_ci and not
  regression"`).

### Subtask T011: Write the failing-first ATDD tests (own commit, before implementation)

**Purpose**: Pin every SK-08 reproduction and regression case as RED before touching
`route()`'s selection logic, built from the ledger's documented probe requests
(SPEC-KITTY-LEDGER.md:2727, SK-08).

**Steps**:
1. In `tests/specify_cli/invocation/test_router.py` (matching `pytestmark = [pytest.mark.unit,
   pytest.mark.fast]`), add:
   - `test_canonical_verb_beats_domain_keyword_regardless_of_priority` (SC-004 / AC-1) — a
     request whose tokens match a canonical verb for profile A and a domain keyword for a
     higher-`routing_priority` profile B; assert the winner is A with `confidence:
     "canonical_verb"`, and B appears in `alternatives` with `confidence: "domain_keyword"`.
   - `test_lone_domain_keyword_candidate_is_ambiguous` (SC-005 / AC-2) — a request matching
     no canonical verb for any profile but exactly one profile's domain keyword; assert
     `RouterAmbiguityError("ROUTER_AMBIGUOUS")` is raised (not an auto-select).
   - `test_lone_domain_keyword_with_explicit_profile_still_works` (AC-3) — same request as
     above, but with `--profile <id>` supplied; assert routing succeeds exactly as before
     (the explicit-hint path is untouched by this WP).
   - `test_two_plus_domain_keyword_candidates_still_ambiguous_regardless_of_priority_spread`
     (SC-006 / AC-4) — zero verb-tier candidates, two keyword-tier candidates at different
     `routing_priority` values (e.g. 80 and 10); assert `ROUTER_AMBIGUOUS` is still raised
     (today's code would auto-select the priority-80 candidate — this test pins the exact
     regression this WP closes).
   - `test_new_ambiguous_raise_sites_carry_confidence_key` — for both new raise sites
     (AC-2's lone-candidate case and AC-4's 2+-keyword-candidates case), assert
     `err.candidates` entries carry the `confidence` key.
2. In a companion dispatch-level test (same file or `test_dispatch.py` if more natural for
   the "no Op opened" assertion), assert that the AC-2 and AC-4 scenarios, run via real
   (non-dry-run) `dispatch` without `--profile`, exit 1 with no new `kitty-ops/` file
   appearing — mirroring SC-005/SC-006's exact assertion shape.
3. Run the new tests and confirm every one fails for the expected reason against WP02's
   final commit: AC-1's case still lets the domain-keyword candidate win; AC-2's case still
   auto-selects; AC-4's case still lets `routing_priority` decide. This is RED on WP02's
   final commit.
4. Also re-run (unmodified) `test_router_priority_tiebreaker_selects_higher_priority`
   (canonical-verb-vs-canonical-verb intra-tier) and confirm it still passes on WP02's final
   commit — this is the baseline this WP must not break.
5. Commit this test-only diff as its own commit, before touching `route()`'s implementation.

**Files**: `tests/specify_cli/invocation/test_router.py` (+~120 lines).

**Validation**: `pytest tests/specify_cli/invocation/test_router.py -v` shows the five new
tests RED against WP02's final commit, and
`test_router_priority_tiebreaker_selects_higher_priority` still GREEN.

### Subtask T012: Restructure `route()`'s selection logic (router.py)

**Purpose**: Implement the verb-tier-first restructuring FR-006/FR-007 require.

**Steps**:
1. In `src/specify_cli/invocation/router.py`, restructure the `if len(candidates) == 1:`
   block (currently ~L343-350, post-WP02) and the `routing_priority` tiebreaker block
   (currently ~L352-370, post-WP02) to separate the canonical-verb tier from the
   domain-keyword tier explicitly, e.g.:
   - Partition `candidates` into verb-tier (`_confidence == "canonical_verb"`) and
     keyword-tier (`_confidence == "domain_keyword"`) groups.
   - If the verb-tier group is non-empty: select from it only (apply the existing
     `routing_priority` tiebreak **within** this group only, unchanged from today's
     tiebreaker logic — do not weaken or alter this intra-tier behavior). Every
     non-selected candidate, verb-tier or keyword-tier, populates `alternatives` exactly as
     WP02 already established (this WP does not change `alternatives`' population
     mechanics, only which candidate wins and when `ROUTER_AMBIGUOUS` is raised instead).
   - If the verb-tier group is empty (zero verb-tier candidates, one or more keyword-tier
     candidates): **always** raise `RouterAmbiguityError("ROUTER_AMBIGUOUS")` — regardless
     of whether there is one keyword-tier candidate (AC-2) or several at different
     `routing_priority` values (AC-4). Do not special-case "exactly one keyword-tier
     candidate" as an auto-select — that is exactly the confident-misroute behavior this fix
     removes.
2. On every new/restructured `RouterAmbiguityError` raise site this restructuring
   introduces, populate each candidate dict's `confidence` key the same way winning-candidate
   dicts already are elsewhere in `route()` (mirroring WP01's fix to the pre-existing raise
   site) — do not reintroduce the pre-FR-009 `profile_id`/`action`/`match_reason`-only
   shape.
3. Confirm the explicit-hint path (Level 1, `profile_hint` branch) is untouched — this
   restructuring is confined to the no-`--profile` candidate-selection logic.
4. Confirm `test_router_priority_tiebreaker_selects_higher_priority` requires no change to
   pass — if it does, the restructuring has altered intra-verb-tier tiebreak behavior, which
   is out of scope; revisit the partition logic.

**Files**: `src/specify_cli/invocation/router.py` (+~40 lines, restructuring existing
~20-line block).

**Validation**: All five of T011's new tests transition RED → GREEN;
`test_router_priority_tiebreaker_selects_higher_priority` still passes unmodified; WP01's
and WP02's own ATDD suites still pass (this WP changes *which* candidate wins on the SK-08
reproduction cases, not the `alternatives`/dry-run field-presence contracts WP01/WP02
established).

### Subtask T013: `CHANGELOG.md` entry + gates + commit

**Purpose**: Document the intentional, user-visible auto-route behavior change for
downstream consumers, then confirm the diff is clean and land the implementation commit.

**Steps**:
1. Add a `CHANGELOG.md` entry (via the `docs/changelog/CHANGELOG.md` symlink target)
   stating explicitly: some previously-successful no-`--profile` `dispatch` calls will now
   exit 1 with `error_code: "ROUTER_AMBIGUOUS"` instead of auto-selecting a lone/weak
   domain-keyword candidate; a canonical-verb match now always outranks a domain-keyword
   match regardless of `routing_priority`; callers wanting a stable profile across a
   mission's lifetime should pass an explicit `--profile` hint (unaffected by this change).
   Follow the existing `CHANGELOG.md` entry format/section conventions already in the file.
2. Run:
   ```
   ruff check .
   mypy --strict src/specify_cli/invocation/ src/specify_cli/cli/commands/dispatch.py src/glossary/chokepoint.py
   pytest tests/specify_cli/invocation/ -v
   pytest tests/architectural/test_no_legacy_terminology.py
   PYTHONPATH=. uv run python scripts/docs/check_docs_freshness.py --ci
   ```
   (`check_docs_freshness.py --ci` validates `CHANGELOG.md`'s page-inventory entry per
   `docs/development/3-2-page-inventory.yaml`.)
3. Run markdown lint over `CHANGELOG.md` (`.markdownlint-cli2.jsonc` carries no exclusion
   for `docs/changelog/`).
4. Confirm WP01's and WP02's own ATDD tests still pass after this WP's changes.
5. Attribute any red per AGENTS.md's baseline-red gotcha (issue #3284/#3283), never
   green-wash pre-existing failures.
6. Commit the implementation (T012–T013) as its own commit, distinct from T011's ATDD
   commit — per spec.md C-002, this is WP3's own commit, distinct from WP1/WP2's commits.

**Files**: `CHANGELOG.md` (+~10 lines, one new entry).

**Validation**: All gates above pass modulo pre-existing tracked red; `check_docs_freshness.py
--ci` passes; markdown lint passes on `CHANGELOG.md`.

## Definition of Done

- [ ] T011's ATDD tests are committed as their own commit, verified RED on WP02's final
      commit (today's code still auto-selects the domain-keyword winner in AC-1, the lone
      candidate in AC-2, and lets `routing_priority` decide in AC-4).
- [ ] A canonical-verb candidate beats a domain-keyword candidate regardless of
      `routing_priority`, cross-tier (FR-006, AC-1/SC-004).
- [ ] `routing_priority` continues to break ties within the canonical-verb tier only,
      unchanged from today (FR-006) — `test_router_priority_tiebreaker_selects_higher_priority`
      passes unmodified.
- [ ] Zero verb-tier candidates + exactly one keyword-tier candidate raises
      `ROUTER_AMBIGUOUS`, not an auto-select (FR-007, AC-2/SC-005) — no Op opened, verified
      by a dispatch-level test.
- [ ] Zero verb-tier candidates + two-or-more keyword-tier candidates at different
      `routing_priority` values raises `ROUTER_AMBIGUOUS` regardless of the priority spread
      (FR-007, AC-4/SC-006) — no Op opened, verified by a dispatch-level test.
- [ ] The lone-domain-keyword-with-explicit-`--profile` case still succeeds exactly as
      before (AC-3) — the explicit-hint path is unaffected.
- [ ] Every new/restructured `ROUTER_AMBIGUOUS` raise site this WP introduces carries a
      `confidence` key on every candidate dict — no reintroduction of the pre-FR-009 shape
      (FR-009's extended obligation).
- [ ] `CHANGELOG.md` carries a new entry documenting the auto-route behavior change for
      downstream consumers (WP3's stated obligation).
- [ ] New tests carry the exact marker named above (`unit`+`fast` in `test_router.py`) — no
      invented markers.
- [ ] WP01's and WP02's own ATDD tests still pass after this WP's changes.
- [ ] `ruff check .`, `mypy --strict` (scoped paths), the targeted pytest paths, the
      terminology guard, and `check_docs_freshness.py --ci` all pass, modulo pre-existing
      #3284/#3283-tracked red.
- [ ] Implementation is committed as its own commit, distinct from T011's ATDD commit —
      landing as WP3's own commit per spec.md C-002.

Implement with: `spec-kitty agent action implement WP03 --agent claude`

## Risks

- **Reverting this WP in isolation may require hand-resolving WP02's `alternatives=`
  edits to the same lines first** — accepted per spec.md C-002; not a defect to "fix" by
  restructuring WP02's commit. Document this in the PR description if asked about
  revertability.
- **Weakening or altering the intra-verb-tier `routing_priority` tiebreak while
  restructuring the surrounding block** — the single named regression FR-006 explicitly
  guards against via `test_router_priority_tiebreaker_selects_higher_priority`'s
  unmodified-pass requirement. Re-run this test after every edit to the restructured block,
  not just once at the end.
- **Reintroducing the pre-FR-009 candidate-dict shape on a new raise site** — mitigated by
  `test_new_ambiguous_raise_sites_carry_confidence_key` (T011) and by mirroring WP01's
  existing confidence-key-population pattern rather than writing a fresh raise site from
  scratch.
- **Downstream consumer surprise on upgrade** (auto-routed calls that used to succeed now
  exit 1) — mitigated by the required `CHANGELOG.md` entry (T013); this is an intentional,
  accepted, user-visible behavior change per spec.md Clarifications, not a bug to soften.
- **Silently touching `tk-watch`'s code** — explicitly out of scope (C-004); do not edit
  anything outside this WP's `owned_files`.

## Reviewer Guidance

- Confirm T011's ATDD commit precedes the implementation commit, and RED was actually
  verified on WP02's final commit.
- Confirm `test_router_priority_tiebreaker_selects_higher_priority` is unmodified in the
  diff and still passes — this is the single most load-bearing regression guard for this WP.
- Confirm the zero-verb-tier branch raises `ROUTER_AMBIGUOUS` unconditionally (both the
  lone-candidate and 2+-candidate cases), with no residual `routing_priority`-based
  auto-select path left reachable when the verb tier is empty.
- Confirm every new/restructured `RouterAmbiguityError` raise site's candidate dicts carry
  `confidence` — read the raise sites directly, don't rely on the tests alone.
- Confirm `CHANGELOG.md` actually documents the behavior change in consumer-facing terms
  (not just an internal implementation note) — this is the mitigation for a real breaking
  change to the CLI's most commonly invoked entry point.
- Confirm this WP touches only `router.py`, `CHANGELOG.md`, and `test_router.py` — no
  `tk-watch` edits, no scope creep into `dispatch.py`/`executor.py`.
