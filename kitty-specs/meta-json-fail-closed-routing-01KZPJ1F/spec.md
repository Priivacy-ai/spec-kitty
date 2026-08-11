# Mission Specification: Meta.json Fail-Closed Read Routing

**Mission Branch**: `feat/meta-json-l1-seam-routing-3259`
**Created**: 2026-08-10
**Status**: Draft (revised after post-spec adversarial squad)
**Input**: Close epic #3259 — route every remaining `meta.json` bypass read through the canonical fail-closed seam, add the missing pure-decode tier, unify the duplicated VCS-lock comparator, and record the read-allow-list governance call. Covers GitHub issues #3228, #3229, #3230, #3240.

## Context & Problem

`meta.json` is a mission's canonical identity and VCS-lock record. When a read of it silently accepts a corrupt, truncated, or wrong-authority file, the system proceeds on false identity — the split-brain / wrong-authority failure mode the metadata-authority work exists to close. The `meta-fail-closed-3162` effort routed one such read and left the rest diagnosable-only; that work never merged to `main` (it lived on the now-superseded PR #3247), so on this branch **five** read sites still bypass the fail-closed loader, a **duplicated** lock-comparison can return contradictory verdicts on the same file, and the pure-decode tier the blob-fed reads need does not exist.

This mission finishes the routing so every `meta.json` read fails loud on corruption, unifies the lock comparison behind one predicate, and records the governance decision on the read allow-list.

### Post-spec review corrections folded in

A four-lens adversarial squad (structure, anti-laziness, live-gate, sequencing) confirmed the mission's premises (all three live gates exist and are green; site A is genuinely unrouted; the diagnosability tests are genuinely absent) and surfaced structural corrections now folded below:

- **Layer placement (C-008):** the new pure-decode primitive (L1), its typed error, and the unified VCS-lock comparator must live in `src/kernel/` (the CI-enforced zero-dependency root), because the git-plumbing site (A) may not import `specify_cli` (C-003). `mission_metadata.py` (L2) imports `specify_cli.core.*`, so L1 cannot live there without making site A un-routable.
- **Census mechanics (C-002/FR-008):** the routed-census scanner counts only calls to a fixed `ROUTED_CALLEES` set; the blob-fed sites route onto the *new* L1/L2 symbols, which do not increment the census unless those symbols are added to `ROUTED_CALLEES` in the same change. The floor is re-derived to sit within the gate's existing margin of the freshly-measured live census (strictly below), not by an unverifiable "not copied" claim.
- **Malformed vs empty (C-010):** L1's `None` return means *malformed only*; empty/whitespace-only content remains a benign caller/L2 short-circuit, preserving the existing `→ {}` contracts (notably `merge_driver`).
- **Sequencing (C-001/C-009):** parser deletion and its callers' rewiring are compile-level atomic and reviewable per module; routing work serializes on the single floor constant.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A corrupt meta.json fails loud on every read path (Priority: P1)

A maintainer or agent runs a git ref-advance, an `implement` claim/self-write check, or a merge-driver reconciliation against a mission whose `meta.json` is corrupt (malformed JSON, invalid UTF-8, or a non-object top level). Instead of silently treating the file as empty/unchanged and proceeding on false state, every read path surfaces a loud, diagnosable failure that names `meta.json` and the read's source identifier.

**Why this priority**: This is the mission's core value — it closes the silent-absorption failure mode across all five remaining sites. Without it the epic's intended effect is unmet.

**Independent Test**: Inject a corrupt `meta.json` at each of the five read sites and assert a diagnosable failure (a shared typed error whose message names `meta.json` + the site's source identifier); assert no site returns a silent "empty/unchanged" sentinel that lets the operation proceed. Each such test is captured red against the pre-routing code before the fix (FR-007).

**Acceptance Scenarios**:

1. **Given** a mission whose committed `meta.json` blob is malformed JSON, **When** the git ref-advance VCS-lock check reads it, **Then** the read raises the shared typed malformed error (naming `meta.json` + the `ref:path` blob spec) rather than treating fields as (un)changed silently.
2. **Given** a `show_blob` payload of invalid UTF-8 bytes, **When** `implement`'s committed-meta read decodes it, **Then** the shared typed malformed error is raised, not a silent `None`.
3. **Given** a worktree `meta.json` with a non-object top level (`[...]`), **When** any of the five sites reads it, **Then** the malformed condition is caught by the single shared decode definition and reported, not accepted.
4. **Given** a **valid** `meta.json`, **When** any of the five sites reads it, **Then** the site's pre-existing verdict on valid input is unchanged (behavior-preserving on the happy path), proven against a captured pre-routing baseline (site A specifically).
5. **Given** an **empty** or whitespace-only `meta.json` at a site whose current contract treats empty as benign (`→ {}`, e.g. `merge_driver`), **When** that site reads it, **Then** the benign `{}` outcome is preserved — empty is NOT folded into the malformed/fail-loud channel (C-010).

---

### User Story 2 - One canonical "is this diff VCS-lock-only?" verdict (Priority: P2)

A maintainer relies on the "did only the claim-time VCS-lock stamp change?" decision to gate a claim/ref-advance. Today that decision is implemented twice by two non-equivalent comparators that can return **opposite** verdicts on a `meta.json` where a lock field is present-but-`null` on one side and absent on the other. After this mission, one comparator over one named field-set — resident in `kernel/` so the git-plumbing caller can use it — answers the question everywhere.

**Why this priority**: Two gates documented as answering the same question returning contradictory verdicts is a correctness hazard. It is P2 because it does not itself absorb corruption, but it shares the ref_advance code path with site A and must be reconciled in lockstep (the ref_advance module change is a single atomic unit).

**Independent Test**: Feed the unified comparator a case where a lock field is present-but-`null` on one side and absent on the other; assert a single deterministic verdict; assert exactly one comparator symbol and one *named* field-set declaration exist tree-wide (no inline-literal field-set evades the count).

**Acceptance Scenarios**:

1. **Given** two `meta.json` states differing only in that `vcs_locked_at` is `null` on one side and absent on the other, **When** the unified comparator runs, **Then** it distinguishes absent from `null` (a present-but-`null` value is a real value, not "no change") and returns one deterministic verdict for both call paths. (Note: this deliberately *changes* the `ref_advance` `.get()!=.get()` verdict on that arm — the unification is not behavior-preserving there, by design.)
2. **Given** the codebase after the mission, **When** the VCS-lock field set and comparator are enumerated, **Then** exactly one *named* declaration of the field set and one comparator symbol exist (no inline literal duplicate), shared by both call paths, resident in `kernel/`, with the git-plumbing module importing no `specify_cli` package.

---

### User Story 3 - Honest gates and a recorded governance call (Priority: P3)

A maintainer reading CI trusts that the architectural gates over `meta.json` reads mean what they say: the routed-census scanner is taught to count the new decode family, the floor reflects a live measurement within the gate's own margin, and the read allow-list's governance status is explicitly recorded.

**Why this priority**: It protects the signal the mission produces. P3 because it is guardrail/bookkeeping around the P1/P2 behavior.

**Independent Test**: Confirm `ROUTED_CALLEES` is extended with the new decode symbols; confirm the routed floor sits within `ROUTED_LOAD_META_FLOOR_MARGIN` of the freshly-measured live census and strictly below it; confirm the allow-list governance decision is recorded (deviation record); confirm all three named live gates are green.

**Acceptance Scenarios**:

1. **Given** the newly-routed sites decode through the new L1/public-L2 symbols, **When** the change lands, **Then** those symbols are added to `ROUTED_CALLEES` (so the census counts them) and `ROUTED_LOAD_META_FLOOR` is re-derived to sit within `ROUTED_LOAD_META_FLOOR_MARGIN` of the freshly-measured live census and strictly below it, in the same change — and `test_routed_load_meta_floor` is green.
2. **Given** the inline-meta-read allow-list is not on the `_baselines.yaml` §(a) register, **When** the mission completes, **Then** the governance remedy is recorded as a deviation (documenting that `test_allowlist_matches_floor` equality + `test_allowlist_shrink_only` are strictly stronger than a `<=` baseline), closing #3240.

### Edge Cases

- Malformed JSON (`"{not json"`), invalid UTF-8 bytes (`b"\xff\xfe"`), and non-object top level (`[1,2,3]`) — all the *same* "malformed" condition, defined once in L1 (`None`/typed-raise channel).
- **Empty / whitespace-only file** — a benign caller/L2 short-circuit (`→ {}` where that is the current contract, e.g. `merge_driver`), explicitly NOT part of L1's malformed set (C-010). Missing file preserves each caller's existing benign outcome.
- A `meta.json` where a VCS-lock field is present-but-`null` vs absent — the unified comparator must distinguish them (C-005).
- The routed census sitting exactly at its margin ceiling (live − floor == margin) before the change — routing must both extend `ROUTED_CALLEES` (so live rises) and re-derive the floor within margin; failing to extend `ROUTED_CALLEES` leaves FR-008 a no-op and breaks SC-004's premise.
- Site E (`merge_driver`) is *already partially* fail-loud with two divergent parsers (one raises an unnamed `json.JSONDecodeError`, one already names the path) — the red-first tests must reflect the honest per-parser starting state.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Kernel-resident L1 pure-decode primitive | As a maintainer, I want one pure-decode primitive in `kernel/` (`text\|bytes → mapping\|None`, no I/O) plus a kernel-resident typed malformed error, owning the single "malformed" definition, so every decoder — including the git-plumbing site — agrees on what a corrupt `meta.json` is. `None` means malformed only. | High | Open |
| FR-002 | L2/L3 re-expressed via L1 + public path entry | As a maintainer, I want `_parse_meta_text` (L2) and `load_meta_fail_closed` (L3) re-expressed on the kernel L1, plus a public path-level entry point, so path-holding callers route without a private symbol and the malformed definition lives in one place. Empty/whitespace stays a benign L2/caller short-circuit. | High | Open |
| FR-003 | Retire the private parsers + rewire their parser-fed sites | As a maintainer, I want the three private parsers deleted and their parser-fed call sites re-pointed onto L1/public-L2 (sites B, D via L1; C via L1 at `implement_cores.py:427`; E via public L2), and the `implement.py:62-70` historical-location shim re-export + any external tests reconciled, so the independent-decoder set shrinks to one. | High | Open |
| FR-004 | Route the structurally-unrouted site A | As a maintainer, I want site A (`ref_advance._meta_change_is_vcs_lock_only`, unrouted on this branch and owned by no live child issue) routed onto the kernel L1, so the last silent committed-meta read fails loud. | High | Open |
| FR-005 | Preserve each site's benign outcome | As a maintainer, I want each routed site to preserve its existing outcome on valid/missing/empty input while a present-but-corrupt file fails loud, proven by a per-site valid/missing/empty assertion and a captured pre-routing baseline for site A. | High | Open |
| FR-006 | Unify the VCS-lock-only comparator in kernel | As a maintainer, I want one comparator over one named field-set, resident in `kernel/`, distinguishing absent from present-but-`null`, so both call paths return the same verdict and git-plumbing can depend on it. | High | Open |
| FR-007 | Captured red-first diagnosability tests | As a maintainer, I want a red-first behavior test per routed site whose failure is captured against pre-routing code, asserting the shared typed error AND a message naming `meta.json` + the site's source identifier (filesystem path for A-worktree/C; `ref:path` blob spec for the committed reads), with the honest per-parser starting state at E. | High | Open |
| FR-008 | Extend the census + re-derive the floor from a live count | As a maintainer, I want the new decode symbols added to `ROUTED_CALLEES` and `ROUTED_LOAD_META_FLOOR` re-derived within `ROUTED_LOAD_META_FLOOR_MARGIN` of the freshly-measured live census (strictly below) in the same change, so the gate reflects reality. | Medium | Open |
| FR-009 | Record the allow-list governance decision | As a maintainer, I want the inline-meta-read allow-list governance call recorded as a deviation (compensating controls documented), so #3240 is resolved explicitly. | Medium | Open |
| FR-010 | Enumeration gate for the single decoder | As a maintainer, I want an architectural check that fails on any `json.loads`/`json.load` applied to `meta.json` content outside the kernel L1 (and a completeness check that no un-routed bypass read hides beyond the 5), so the "one decoder / all reads routed" claim is machine-enforced, not hand-counted. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Single decode authority (enforced) | After the mission, exactly **1** symbol independently answers "is this `meta.json` well-formed" (down from 4), enforced by the FR-010 enumeration gate (`json.loads` over meta content outside kernel L1 == 0). | Correctness | High | Open |
| NFR-002 | Single lock comparator (no literal evasion) | After the mission, exactly **1** comparator symbol and **1** *named* VCS-lock field-set declaration exist (down from 2 + 2), with **0** inline-literal field-sets, verified by enumeration. | Maintainability | High | Open |
| NFR-003 | Named governance gates green | The three named live gates — `test_inline_meta_read_floor`, `test_routed_load_meta_floor` (`tests/architectural/test_inline_meta_read_gate.py`), and `test_no_unaccounted_load_meta_call_sites` (`tests/specify_cli/test_meta_fail_closed_full_census_contract.py`) — all pass, with the routed floor re-derived from a live count in the same change. | Reliability | High | Open |
| NFR-004 | Plumbing layer boundary ratcheted | `git/ref_advance.py` introduces **0** imports of `specify_cli`, enforced by a new/extended architectural ratchet (not convention alone). | Architecture | High | Open |
| NFR-005 | Zero silent absorptions | A corrupt `meta.json` injected at each of the 5 sites yields **0** silent "empty/unchanged" outcomes that let the operation proceed on false state. | Security | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Artifact-ordering + per-module atomicity | The kernel L1 primitive and public-L2 entry must exist before any site routes onto them; a private parser's deletion and its callers' rewiring are one atomic unit, reviewed per module (ref_advance / implement_cores+implement / merge_driver) — never split so the tree is non-importable between packages. | Technical | High | Open |
| C-002 | Live-count floor derivation within margin | `ROUTED_CALLEES` gains the new decode symbols and `ROUTED_LOAD_META_FLOOR` is re-derived within `ROUTED_LOAD_META_FLOOR_MARGIN` of the freshly-measured live census (strictly below) in the same change; copying a floor/band from a planning artifact is forbidden. | Technical | High | Open |
| C-003 | Git-plumbing must not depend on specify_cli | `git/ref_advance.py` must not import `specify_cli`; the shared decode primitive and comparator live in `kernel/`, which git-plumbing may depend on. | Technical | High | Open |
| C-004 | Test routing markers | New/relocated test files carry a gate-selected `pytestmark`; the corrupt-file diagnosability tests use `[integration, git_repo]`, and any `tests/runtime` test is registered in `tests/_next_shard_map.py` (addresses — does not close — #3241). | Technical | High | Open |
| C-005 | Absent ≠ null (operator decision) | The unified VCS-lock comparator distinguishes an absent field from a present-but-`null` field (adopts the sentinel semantics). | Technical | High | Open |
| C-006 | #3240 resolved by deviation record | The inline-meta-read allow-list governance call is resolved by recording the deviation, not by adding a new `_baselines.yaml` count baseline. | Technical | Medium | Open |
| C-007 | Branch-reality reconciliation | Site A is unrouted and the diagnosability tests are absent on this branch; the mission authors them fresh and does not depend on the superseded PR #3247 or the retired mission-#3162 `SC-013` gate. | Technical | High | Open |
| C-008 | Kernel placement of decode + comparator | L1 (`decode_meta`), its typed error, and the unified comparator + named field-set all live in `src/kernel/`; L2 (`mission_metadata._parse_meta_text`) and L3 (`core.paths.load_meta_fail_closed`) re-express on top. This also relieves the existing `core.paths`↔`mission_metadata` deferred-import cycle. | Technical | High | Open |
| C-009 | Routing is census-neutral; one census change at closeout | The site-routing changes route onto the new decode symbols (`decode_meta`, `parse_meta_file`), which are NOT in `ROUTED_CALLEES`, so they change the routed census by 0 (gate stays green throughout). The single census change — extend `ROUTED_CALLEES` + re-derive the floor — happens once, at closeout, after all routing lands. Site E must route onto `parse_meta_file`, NOT the already-counted `load_meta_or_empty` (which would red the gate mid-change). | Technical | High | Open |
| C-010 | Empty is benign, not malformed | Empty/whitespace-only `meta.json` is a benign caller/L2 short-circuit (`→ {}` where currently contracted, e.g. `merge_driver`), explicitly outside L1's malformed set; L1's `None` means malformed only. | Technical | High | Open |
| C-011 | Error-type preservation | L1's `MetaDecodeError` extends `ValueError` so existing `except ValueError` boundaries keep catching; L2 re-wraps into a `ValueError` carrying its legacy path-named messages, and L3/site-E re-wrap into `MissionMetaReadError`/`EventLogMergeError` — so message- and type-pinned regressions stay green. | Technical | High | Open |

### Key Entities

- **`meta.json`**: A mission's canonical identity and VCS-lock record; the file whose reads must all fail loud on corruption.
- **Seam tiers**: **L1** kernel pure-decode (`text\|bytes → mapping\|None`, no I/O, `None` == malformed only) + kernel typed error; **L2** path-level (`mission_metadata._parse_meta_text`, opens the file, owns the empty→benign short-circuit) + a public path entry; **L3** dir-level public fail-closed loader (`core.paths.load_meta_fail_closed`).
- **The five bypass read sites** (source identifier for red-first injection):
  - **A** — `ref_advance._meta_change_is_vcs_lock_only` (worktree read + committed `git show HEAD:path` subprocess; needs a `git_repo` fixture) — routes onto kernel L1; unrouted today.
  - **B** — `ref_advance._committed_meta_object` (`git show HEAD:path` stdout `str`) — kernel L1.
  - **C** — `implement_cores._is_self_write_only_diff`, real decode at `implement_cores.py:427` (`source.read_bytes()`; the byte-compare at `:471` is *not* a decode) — kernel L1.
  - **D** — `implement_cores._committed_meta_mapping` (`GitPort.show_blob` `bytes`, port-injectable — no real git) — kernel L1.
  - **E** — `merge_driver._load_json_object` (on-disk temp path; already partially fail-loud, two divergent parsers) — public L2.
- **VCS-lock-only comparator**: the predicate deciding whether a `meta.json` diff touched only the claim-time lock stamp; today duplicated (2 comparators + 2 field-sets) and divergent, to become one kernel symbol.
- **Read governance gates**: the inline-meta-read allow-list + floor, the routed-census floor/margin, and the `load_meta` call-site ledger.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: **0** of the 5 `meta.json` read sites bypass the fail-closed seam (100% routed, incl. site A), and the FR-010 completeness check proves **0** un-routed bypass reads hide beyond the enumerated 5.
- **SC-002**: A corrupt `meta.json` injected at each of the 5 sites produces the shared typed error naming `meta.json` + the site's source identifier, each captured red against pre-routing code — **0** silent absorptions (NFR-005).
- **SC-003**: Exactly **1** independent `meta.json` decoder symbol (FR-010 gate) and exactly **1** comparator symbol + **1** named field-set (NFR-002) remain (down from 4 and 2+2).
- **SC-004**: All **3** named live gates are green with `ROUTED_CALLEES` extended and the routed floor re-derived within margin of a freshly-measured live census in the same change; the #3240 governance decision is recorded — **0** copied gate constants, **0** unrecorded deviations.
- **SC-005**: On valid/missing/empty input, every routed site returns its pre-mission outcome (behavior-preserving except the deliberate C-005 absent≠null change), proven by the existing suites plus a per-site assertion and a captured site-A baseline.

## Issue Closure Map

| Child issue | Closed/served by |
|-------------|------------------|
| #3228 (duplicated VCS-lock comparator) | FR-006, NFR-002, SC-003 |
| #3229 (L1 pure-decode tier) | FR-001, FR-002, FR-003, NFR-001, SC-003 |
| #3230 (route the remaining reads + floor) | FR-004, FR-005, FR-007, FR-008, C-002/C-009, SC-001/SC-002/SC-004 |
| #3240 (allow-list baseline governance) | FR-009, C-006, SC-004 |
| #3241 (test-marker routing) | **addresses, does not close** — C-004; the `_rel()` over-count remains out of scope (already fixed separately). |

## Notes for the Plan Phase (not binding spec, carried from the post-spec squad)

Recommended reviewable WP boundaries (plan/tasks to confirm): **WP1 Foundation** — kernel L1 + typed error + public-L2 + L2/L3 re-expression (census-neutral, green alone, no deletions). **WP2 ref_advance (atomic)** — delete `_parse_meta_object`; route A + B; move comparator to kernel + unify (C-005); red-first tests A/B; re-derive floor. **WP3 implement_cores + implement (atomic)** — delete `_parse_meta_mapping`; route C + D; reconcile the `implement.py` shim + external imports; red-first tests C/D; re-derive floor. **WP4 merge_driver** — route E via public L2; red-first test E; re-derive floor. **WP5 Governance** — #3240 deviation record; FR-010 enumeration + completeness gates; pin the cumulative `ROUTED_LOAD_META_FLOOR`; NFR-004 ratchet; all three gates green. Routing WPs (2/3/4) serialize on the floor constant; WP5 (or the last routing WP) pins the final floor.
