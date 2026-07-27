# Mission Specification: Refactor-Stable Gate Substrate

**Mission Branch**: `tidy/gate-substrate` (mission `refactor-stable-gate-substrate-01KWK3FY`, coord branch `kitty/mission-refactor-stable-gate-substrate-01KWK3FY`)
**Created**: 2026-07-03
**Status**: Draft (rev 3 — post-tasks squad + operator CI-green fold, 2026-07-03)
**Input**: Operator-approved tidy-cluster proposal (HiC ruling "Tidy first") + pre-spec code-state census (debugger-debbie, 2026-07-03, verified on this branch). Executes #2072 (CT1, partial), #2310 (CT8, closes), #2311 (CT9, closes) under epic #2071, milestone 3.2.x.

## Context

The operator's refactor-stable testing doctrine (2026-07-03): *"if our architecture /
acceptance tests need to change on every cleanup/refactor, they are not good tests."*
This mission applies that doctrine to the gate substrate itself — the enabler for the
upcoming unshim wave (#2289–#2293), whose deletions would otherwise churn every
line-keyed allowlist they touch.

**Census facts (2026-07-03, this branch — supersede the epic's ~113-ref claim, which
was the pre-migration-campaign peak):**

- **The one raw-line-keyed family left**: `tests/architectural/resolution_gate_allowlist.yaml`
  + `test_resolution_authority_gates.py`. `GateAllowlistKey(enclosing_qualname,
  token_line: int)` stores and compares a raw AST `lineno` — a +1 blank-line drift
  produces a false allowlist miss. **10 entries** (3 canonicalizer + 7 coord_authority),
  all function-scoped. Highest-churn gate in the suite: 12 commits on the YAML, 5 edits
  in the last two weeks alone (degod WP09s, coord-read-residuals, rebases).
- **TWO composite patterns exist in-tree, with OPPOSITE semantics** (post-spec squad,
  empirically proven): **Design-S** (`_RAW_JOIN_SITES`) re-derives the key from the live
  file at a seed line — content-FOLLOWING: drift still breaks the fixed seed, and a
  content change to an allowlisted site is INVISIBLE. **Design-P**
  (`test_no_worktree_name_guess.py`'s `_ALLOWED_SITES_FILES`) freezes the tool-derived
  `(qualname, token)` as the authoritative comparand while the live scanner re-derives
  and checks membership — drift-immune AND content-detecting. **Design-P is this
  mission's chosen design** (ADR-note in tracers/design-decisions.md). Families already
  content-addressed: `_RAW_JOIN_SITES` (4 seeds, Design-S — acceptable there, its twin
  staleness guard covers it), `test_no_write_side_rederivation` (1),
  `test_wp05_write_target_drain` (1), `test_commit_target_kind_guard` (empty),
  `test_no_worktree_name_guess.py` (Design-P reference implementation — already ships
  drift theater tests and per-file key dicts).
- **The inventory tripwires are line-sensitive AND duplicated** (squad correction —
  the audits do NOT share a mechanism; they are copy-paste twins with no shared
  import): `untrusted_path_audit/audit.py` (30 SinkRow rows) +
  `surface_resolution_audit/audit.py` (27 ResolutionRow rows PLUS a second SelectionRow
  table with its own check) + a THIRD raw-line comparison duplicated in
  `test_untrusted_path_containment.py:328` — ~4 comparison sites across 3 files. The
  raw `rel:line` compare is what red #2306 on a 1-line drift. (Post-tasks squad correction: the previously-claimed inventory→resolver-test
  split-brain does NOT exist on the current tree — the resolver test imports
  `discover_rows` LIVE and never reads inventory.md, per its own docstring :15-19/:90-96.
  The real coupling is the audit module's importable public shape:
  ResolutionRow/SelectionRow fields + the `discover_rows()` signature.) Dropping the line column is NON-VIABLE (collision-tested:
  7/30 and 6/27 identity collisions without it) — composite `(path, qualname, token)`
  identity is the only path. Neither audit has an OVERCOUNT direction today (ghost
  inventory rows for deleted sinks are silent). This is the mission's design stream —
  two sub-streams, not one item.
- **CT9 verification — CI SUPERSEDES the local census (operator fold 2026-07-03)**:
  locally 16 of the 31 quarantined tests pass (the census 15 + A16), but on CI's
  quarantine-visibility lane (run 28643092421, main @ f47a780e0) **ALL 31 FAIL** —
  total local≠CI skew, the original quarantine cause. CI failure signatures per
  file: retrospect help (flag missing from Rich-rendered help), 13× upgrade-ux
  (choice persistence None, subprocess argv empty, IndexError), decision-widen/
  decision-shape/doctor-ops-cli/doctor-ops, 2× mid8 routing, no_checklist, 10×
  daemon-reaper (#2309, real-port serial class). The un-quarantine decision is made
  on CI evidence only; local passes prove nothing (NFR-004).
- **CT8 doctrine home**: `src/doctrine/styleguides/built-in/testing-principles.styleguide.yaml`
  (schema: `principles` list + `patterns`/`anti_patterns` with good/bad examples;
  already in `.kittify/config.yaml` `activated_styleguides` and the DRG). Any edit
  requires regenerating `src/doctrine/graph.yaml` in the same change — two byte-for-byte
  freshness gates enforce it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gate allowlists survive benign refactors (Priority: P1)

A maintainer deleting a shim or moving a function (the upcoming unshim wave) no longer
reds `test_resolution_authority_gates.py` from pure line drift: the allowlist keys are
content-addressed (`(qualname, token)`), so the gate fires only when an allowlisted
site's *code* changes or a *new* offending site appears — never when unrelated edits
shift line numbers.

**Why this priority**: This is CT1's core and the direct enabler for #2289–#2293
(every deletion shifts lines) and #2293's hard dependency on #2072.

**Independent Test**: the theater triad at the top-level gate entry point — a
synthetic +1-line shift leaves the gate green; a token edit to an allowlisted site
red-fires; a synthetic new offending site red-fires (DIRECTIVE_043).

**Acceptance Scenarios**:

1. **Given** the 10 YAML entries converted to Design-P, **When** the gate loads,
   **Then** the stored keys are frozen `(file, qualname, token)` comparands (the YAML
   `line:` field is a non-authoritative locator for diagnostics), and the live scanner
   emits matching content-addressed keys with no raw lineno in any comparison.
2. **Given** a source file where an allowlisted site shifts by +1 line (synthetic,
   in-memory), **When** the gate's comparison runs, **Then** zero false misses.
3. **Given** a synthetic NEW offending site, **When** the gate runs, **Then** it fails
   with an actionable message (non-vacuity preserved).

---

### User Story 2 - The inventory tripwire stops crying wolf (Priority: P1)

A maintainer whose edit shifts a path-sink's line number no longer gets the #2306-class
false failure: the undercount tripwires in BOTH audits (copy-paste twins — each
converted in its own sub-stream, including the duplicated compare in the untrusted
test file and the surface SelectionRow check) identify rows by stable composite
identity, not raw file:line — while still catching a genuinely undocumented sink AND
(new) a ghost row whose sink no longer exists.

**Why this priority**: This exact failure red CI once (#2306) and churned the inventory
3× during one mission; the unshim deletions would multiply it.

**Independent Test**: a synthetic line-only drift of a documented sink leaves the audit
green; a synthetic undocumented sink still trips the undercount gate.

**Acceptance Scenarios**:

1. **Given** the redesigned comparison, **When** a documented sink's line shifts,
   **Then** the audit passes without editing the inventory (the line column is a
   non-authoritative locator).
2. **Given** a discovered sink absent from the inventory, **When** the audit runs,
   **Then** the undercount tripwire fails naming the missing row.
3. **Given** an inventory row whose sink was deleted, **When** the audit runs, **Then**
   the NEW overcount/staleness tripwire fails naming the ghost row (modulo
   explicitly-tagged rows).

---

### User Story 3 - The doctrine is codified where agents read it (Priority: P2)

An agent (or reviewer) consulting the testing-principles styleguide finds the
refactor-stable rules as first-class principles with good/bad examples drawn from the
live precedents — instead of the doctrine existing only in session memory and PR
history.

**Why this priority**: CT8 turns a session ruling into governance; every future gate
author inherits it via the charter/doctrine chain.

**Independent Test**: the styleguide carries the new principles/patterns; the DRG
freshness gates pass byte-for-byte; charter context still resolves.

**Acceptance Scenarios**:

1. **Given** the updated styleguide, **When** the two graph-freshness gates run,
   **Then** both pass (graph.yaml regenerated in the same change).
2. **Given** the styleguide content, **Then** it encodes: invariants over shape
   (negative AST forms, behavioral pins), no positive literal-presence scans, no
   size/LOC ceilings (Sonar owns size), convert-or-delete with surviving-coverage
   proof (never re-pin), shrink-only COUNT ratchets are sanctioned, transitional
   shape-coupled guards need a named retirement path — each with a good/bad example
   citing the PR #2308 precedents.

---

### User Story 4 - The silently-passing quarantine debt returns to duty (Priority: P2)

The 15 quarantined tests that pass today run un-skipped in their normal CI shards; the
quarantine set shrinks 31 → 16, and the 3 stay-behind cases carry HONEST reasons (the
2 uv-tool cases re-labeled from "env-dependent" to the real behavioral-drift diagnosis
with an upstream issue filed; the perf case keeps its CI-timing rationale).

**Why this priority**: CT9 is evidence-complete (verified twice); a quarantine set full
of passing tests trains people to ignore it.

**Independent Test**: the 15 nodes run and pass without the quarantine-override env var
in their normal shard selection, twice consecutively; the quarantine lane count drops
accordingly.

**Acceptance Scenarios**:

1. **Given** the 15 markers removed, **When** their files' normal shards run, **Then**
   all 15 execute (not skipped) and pass — deterministically (two consecutive local
   runs; no retry-to-green).
2. **Given** the 2 uv-tool stay-behinds, **Then** their quarantine reasons state the
   real diagnosis (env dict no longer passed; `--python` no longer threaded), an
   upstream issue documents the upgrade-domain drift per the judge-the-test framework,
   and the reason string references it.

---

### Edge Cases

- **Token collision within a function**: two allowlisted sites in one function with
  identical token content — the composite key must still disambiguate or the design
  must document the collision rule (follow the `_RAW_JOIN_SITES` precedent).
- **Seed staleness on conversion day**: a YAML `line:` locator that no longer points
  at the intended site must make the one-time freeze tooling fail LOUDLY (fail-closed),
  not silently freeze the wrong token.
- **Inventory rows for sinks in RELOCATED files**: the degod moves left inventory rows
  pointing at new modules — the redesigned identity must be stable across such moves
  (path changes ARE meaningful; only line changes are not).
- **Un-quarantined test flakes in CI but not locally**: the CT9 acceptance requires the
  shard-level determinism check; any node that flakes goes BACK behind quarantine with
  an honest reason rather than retry-to-green (DIRECTIVE_041).
- **graph.yaml regeneration is byte-sensitive**: regenerate with the canonical
  `generate_graph` entry point only; hand-edits to generated artifacts are forbidden.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Convert the resolution-authority gate to **Design-P** content-pinned keys: the tool-derived token is FROZEN in the allowlist as the authoritative comparand; `GateAllowlistKey` gains `rel_path` (the YAML gains `file:`) — qualname collisions (`implement`/`review` ×2) are disambiguated by path+token, never by line; `line:` is retained as a NON-authoritative locator for diagnostics only (violation messages keep a clickable file:line); the live scanner emits `(path, qualname, token)` via `code_tokens_by_line` with NO `node.lineno` feeding any key — full conversion including the ~6 int-line test constructors and the `derive_live_key` unit tests. All 10 entries. | US1 | High | Open |
| FR-002 | Theater TRIAD driving the TOP-LEVEL gate entry points (`check_*_gate`, the T005 self-mutation model — never helper-only): (a) drift-immunity: +1 blank line inserted in the scanned source with the allowlist untouched → 0 violations; (b) content-detection: a token edit to an allowlisted site → gate RED (the frozen-key mismatch/staleness path — NFR-001(b)); (c) non-vacuity: a synthetic NEW offender → gate RED. | US1 | High | Open |
| FR-003 | Fail-closed freeze + staleness: the one-time conversion tooling aborts loudly on a seed that does not resolve to a function-scoped site; at runtime, a frozen key with no live match fails the staleness guard with an actionable message (evict-or-re-approve) — never silent. | US1 | High | Open |
| FR-004 | Redesign BOTH audit tripwires (two sub-streams — untrusted: audit.py Check-2 locator compare :383 + the duplicated compare in test_untrusted_path_containment.py:328; surface: ResolutionRow Check-2 :526-534 + the SelectionRow Check-4 :549-561) to composite `(path, qualname, token)` row identity — line-drop STRUCK (collision-proven). The comparison logic is extracted into PURE seams (`check_undercount`/`check_overcount(discovered_keys, inventory_keys)`) that `main()` itself calls, so the theater triad drives the REAL path (helper-only theater is a review reject; the overcount check is vacuously green at conversion — its theater leg is its only non-vacuity proof). Surface sub-stream additionally guards the audit module's PUBLIC SHAPE (ResolutionRow/SelectionRow fields + discover_rows signature unchanged — the live consumer is test_single_mission_surface_resolver's imports, proven by its unmodified-green run). | US2 | High | Open |
| FR-005 | REFRAMED (squad): `test_no_worktree_name_guess.py` is the Design-P REFERENCE implementation (frozen composites + drift theater + per-file dicts already shipped) — converting it to seed-derivation would REGRESS its content-detection. Deliverable: document it as the reference pattern (docstring note + tracer), align naming with the Design-P vocabulary, and change NO key semantics. The previously-planned conversion is cancelled. | US1 | Low | Open |
| FR-006 | Encode the refactor-stable doctrine into `testing-principles.styleguide.yaml` (principles + patterns/anti_patterns per US3 scenario 2, with PR #2308-cited examples) and regenerate `src/doctrine/graph.yaml` in the same change. | US3 | High | Open |
| FR-007 | Adjudicate ALL 31 quarantined tests on CI evidence (per-test, judge-the-test framework): (a) REMEDIATE the test so it passes on CI (fixing CI-env assertion fragility is remediation; then un-quarantine it into its normal shard), or (b) DISABLE honestly (`pytest.mark.skip` with an accurate reason + issue ref — daemon-reaper→#2309, uv-tool→the upstream issue), or (c) DELETE (valueless/stub tests, with surviving-coverage judgment). Local determinism evidence (shard form ×2, bypass UNSET, restored nodes PASS + skips visible) is necessary but NOT sufficient — CI is authoritative. | US4 | High | Open |
| FR-008 | Correct the quarantine reason strings on the 2 uv-tool stay-behinds to the real behavioral-drift diagnosis, file the upstream upgrade-domain issue (judge-the-test applies: stale-or-product is that domain owner's call), and reference it from the reason strings. | US4 | Medium | Open |
| FR-009 | Tracker closeout: #2311 and #2310 close with this mission; #2072 gets a partial-completion comment (re-key + inventory fold delivered; the drain-deferred-entries remainder stays open) naming exactly what remains. | US1-US4 | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Drift immunity + content detection, measured | For every converted gate, the theater triad drives the TOP-LEVEL gate entry point: (a) +1-line shift with allowlist untouched → 0 failures; (b) token change to an allowlisted site → detected (frozen-key mismatch / staleness guard fires); (c) new offender → detected. Design-P semantics (content-PINNING) — proven at the entry point CI runs, never helper-only. | Correctness | High | Open |
| NFR-002 | Zero production changes | The mission diff contains no changes under `src/specify_cli/` or `src/runtime/` — only `tests/`, `src/doctrine/`, and `kitty-specs/`. | Scope | High | Open |
| NFR-003 | Static + freshness gates | `ruff` and `mypy --strict` zero findings on touched files (src+tests together where applicable); both DRG freshness gates byte-green; the full `tests/architectural/` suite green on the final tree. | Quality | High | Open |
| NFR-004 | No retry-to-green | Un-quarantined tests pass twice consecutively in their shard selection locally; any flake reverts to quarantine with an honest reason — never merged flaky. | Process | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Own-doctrine conformance | The mission's own deliverables obey the doctrine they codify: no new positive literal-presence scans, no size ceilings, negative/behavioral forms only; every new gate/theater test is non-vacuous (DIRECTIVE_043). | Governance | High | Open |
| C-002 | Base and rebase discipline | Based on `degod-follow-ups` tip `17fd824e4` (contains PR #2308's gate-file state — the resolution-allowlist coupling is resolved by this branching); if #2308 gains commits before this mission merges, rebase `tidy/gate-substrate` before merge. | Technical | High | Open |
| C-003 | Judge-the-test at the boundary | The 2 uv-tool stay-behinds are NOT fixed here (upgrade domain, out of scope) — reasons corrected + issue filed only; the perf-budget case stays quarantined (CI-timing evidence required to free it). | Scope | Medium | Open |
| C-004 | Canonical regeneration only | `graph.yaml` changes only via `generate_graph`; inventory line columns only via their documented freshen tooling (or become non-authoritative per FR-004) — no hand-edited generated artifacts. | Process | High | Open |
| C-005 | Terminology canon | Mission/`--mission` language throughout; the terminology guard passes before every push. | Governance | Medium | Open |

### Key Entities

- **Content-addressed gate key**: `(enclosing_qualname, token_line_str)` derived from
  source via `composite_key` — the drift-proof identity replacing raw line numbers.
- **Frozen comparand (Design-P)**: the tool-derived `(file, qualname, token)` stored
  in the allowlist as the authoritative key; the `line:` integer survives only as a
  non-authoritative locator for diagnostics — never compared.
- **Theater triad**: drift-immunity (must NOT fire on line shift) + content-detection
  (MUST fire when an allowlisted site's tokens change) + non-vacuity (MUST fire on a
  new offender) — every converted gate ships all three, driven at the top-level gate
  entry point.
- **Quarantine set**: the quarantine-marked nodes (31 → 16 after CT9).
- **Doctrine styleguide**: `testing-principles.styleguide.yaml` + its regenerated DRG
  edges.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 raw integer-line-keyed gate comparisons remain: `rg 'token_line:\s*int' tests/architectural/` returns nothing; `GateAllowlistKey.token_line` is annotated `str`; no `node.lineno` feeds any stored/compared key (grep evidence recorded); the authoritative census is BEHAVIORAL — the per-gate theater triads (SC-002).
- **SC-002**: Every converted gate ships the full theater TRIAD (drift-green / content-change-red / new-offender-red), each driving the top-level gate entry point.
- **SC-003**: The audit undercount tripwire passes under synthetic line-only drift and
  fails on a synthetic undocumented sink — the #2306 failure class is closed by
  construction.
- **SC-004**: The quarantine-visibility CI job is GREEN on the mission PR (every
  quarantined test passes or skips on CI — zero failures); every remediated test
  also passes in its NORMAL shard selection (un-quarantined); every skip carries an
  accurate reason + issue ref; the differential local evidence (bypass unset,
  restored nodes PASS, stay-behind skips VISIBLE) is recorded.
- **SC-005**: The styleguide carries the doctrine (per US3 scenario 2's enumeration) and both DRG freshness gates pass; completion is evidenced by a RECORDED acceptance check (parse the styleguide, enumerate >=6 named principles each with non-empty good/bad examples, >=1 citing PR #2308) — an acceptance-time script, NOT a new standing content-coupled suite test (C-001 conformance).
- **SC-006**: `git diff` shows zero changes under `src/specify_cli/` and `src/runtime/`.

## Assumptions

- The Design-P frozen-composite pattern (`test_no_worktree_name_guess.py`) is the
  accepted conversion template; `_RAW_JOIN_SITES`' Design-S stays as-is in its own
  family (its twin staleness guard covers it) and is NOT propagated further.
- The census's 15-node pass list is current for this branch (re-verified 2026-07-03);
  the implement WP re-runs it before removing markers.
- Sizing (squad-adjusted): **5–6 WPs** — resolution-gate conversion (WP-A), untrusted
  audit redesign (WP-B), surface audit redesign incl. SelectionRow + split-brain
  reconciliation (WP-C), doctrine+DRG (WP-D), un-quarantine (WP-E), reference-pattern
  doc + closeout (WP-F, foldable). WP-A/B/C/D/E are ownership-disjoint (different
  files) and can parallelize; closeout serializes last.
- PR #2308 lands before this mission merges (operator monitoring); C-002 covers the
  rebase path.

## Non-Goals / Deferred

- **Draining the 10 allowlisted resolver sites themselves** (the #2072
  "drain deferred-defect entries" remainder — production resolver work, other domains
  own it).
- **Fixing the uv-tool argv/env drift** (upgrade domain — issue filed, not folded).
- **Un-quarantining the perf-budget case** (needs CI-timing evidence first).
- **The unshim cluster itself** (#2289–#2293 — the next wave, enabled by this mission;
  per the HiC ruling its deletions land in the current release cycle, never deferred to
  a version boundary).
- **The daemon-reaper contract divergence** (#2309 — sync domain).
