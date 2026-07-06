# Mission Specification: LOC-insensitive census freshness gate

> Mission: `census-freshness-loc-insensitive-01KWVD6Y`
> Type: software-dev
> Tracker: [Priivacy-ai/spec-kitty#2416](https://github.com/Priivacy-ai/spec-kitty/issues/2416)
> Status: Draft

## Summary

The CI-topology census gate exists to prove that every hot source directory routes
to a named CI test group, so a change confined to that directory is not forced to
run the whole suite. Today the same gate also pins the **exact line count** of each
worklist directory and compares it for equality against a live re-derivation. As a
result, any pull request that adds or removes even a few lines in one of those
directories fails CI, and the only remedy is to notice the failure, run a manual
regeneration command, and land a functionally-empty extra commit. This has already
happened on at least two unrelated PRs within 24 hours (#2386, #2414), each paying
the same manual-fold tax.

This mission narrows the freshness gate to what it must actually protect —
**which directories are on the worklist** and **how they route** — plus a live
check that each worklist directory still clears the LOC floor. Exact per-directory
line count is removed from the comparison surface. The three anti-tamper protections
the gate was authored to provide are preserved by construction.

## Domain Language

| Term | Meaning (canonical) |
|------|---------------------|
| Census | The committed `tests/architectural/ci_topology_census.json` artifact, construction-derived from the live source tree and the parsed CI workflows. |
| Worklist | The census's authoritative list of `src/specify_cli/*` directories at or above the LOC floor that no named src-backed CI filter group claims. |
| Routing plan | Per worklist entry: its `target_group` (named CI filter group), `target_shard` (focused integration shard), and `cone_roots` (test directories). Sourced from the committed `_COMPOSITE_ROUTING` table. |
| LOC floor (`t_loc`) | The committed line-count threshold (currently 500) for worklist membership. |
| Freshness gate | The test `test_census_worklist_matches_live_derivation` that asserts the committed census equals a live re-derivation. |
| Tooth | An anti-tamper failure mode the freshness gate must red on: hand-trim, floor-crossing, new-hot-dir. |
| `unmatched -> run_all` | The CI fall-through where a touch to an unrouted directory runs the entire suite (the blast radius the census exists to prevent). |

## User Scenarios & Testing

### Primary scenario (the maintenance-tax path being fixed)

- **Actor:** A contributor (or landing-pass agent) opening a routine PR.
- **Trigger:** The PR adds or removes a non-trivial number of lines in a source
  directory that happens to be on the census worklist (e.g. a 19-line helper added
  to `session_presence`, or de-duplication in `bulk_edit`).
- **Happy path:** The PR's change does not alter which directories are on the
  worklist, nor how any of them route. CI's topology gate stays **green**. No
  census regeneration, no extra commit.
- **Before this mission:** The same PR reds `test_census_worklist_matches_live_derivation`
  because the stored exact LOC no longer matches the live count, forcing a manual
  regen + fold commit.

### Anti-tamper scenarios (must still red — the gate's real job)

1. **Hand-trim:** A directory is deleted from the committed census worklist while it
   still qualifies live (≥ `t_loc`, unmapped). The gate must red — a trimmed census
   cannot silently under-cover the routing iteration.
2. **Floor-crossing:** A directory that was on the worklist drops below `t_loc`
   (leaving the live worklist) while the committed census still lists it — or a
   directory rises to/above `t_loc` and should join. Membership diverges; the gate
   must red.
3. **New hot directory:** A brand-new `src/specify_cli/*` directory at or above
   `t_loc`, not in the frozen pre-mission mapped baseline, is absent from the
   committed census. The live derivation grows beyond the census; the gate must red.
4. **Routing hand-edit:** A worklist entry's `target_group`, `target_shard`, or
   `cone_roots` is hand-edited to diverge from the canonical routing plan. The gate
   must red.

### Edge cases

- A refactor that moves lines **between** two worklist directories such that their
  LOC *ranking* swaps but both remain members (a **rank-swap**): gate stays green
  (order must not matter). This is a **second class of false positive** the current
  `sort by -loc` + ordered-list comparison also suffers, and it is the failure the
  red-first reproduction (C-003) must exercise so order-insensitivity is delivered,
  not merely asserted.
- A directory sitting exactly at `t_loc`: remains a member (floor is inclusive,
  `>= t_loc`), unchanged from today.

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The freshness gate MUST pass when a worklist directory's line count changes but its worklist membership and routing plan are unchanged. | Draft |
| FR-002 | The freshness gate MUST fail when a directory is removed from the committed census worklist while it still qualifies in the live derivation (hand-trim tooth). | Draft |
| FR-003 | The freshness gate MUST fail when worklist membership diverges because a directory crosses the LOC floor (leaves or should join the worklist) relative to the committed census (floor-crossing tooth). | Draft |
| FR-004 | The freshness gate MUST fail when a new source directory at or above the LOC floor, absent from the committed census worklist, appears in the live derivation (new-hot-dir tooth). | Draft |
| FR-005 | The freshness gate MUST fail when a worklist entry's committed routing plan (`target_group`, `target_shard`, or `cone_roots`) is hand-edited to diverge from the canonical routing plan. | Draft |
| FR-006 | Each committed worklist directory MUST be verified to clear the LOC floor (`t_loc`) against the live source tree, not against a stored line-count snapshot. | Draft |
| FR-007 | The freshness comparison MUST be insensitive to the ordering of worklist entries, so a LOC-rank swap between two members does not red the gate. | Draft |
| FR-008 | The pre-existing routing-completeness invariants (routes to a named src-backed group; no worklist dir falls to `unmatched -> run_all`; each worklist dir declares a focused shard; worklist is non-empty) MUST continue to hold unchanged. | Draft |

### Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | Eliminate the manual-fold tax for LOC-only churn. | For the reproduction (add or remove any number of lines in a worklist directory without changing membership or routing), the freshness gate stays green and **zero** additional commits are required. | Draft |
| NFR-002 | No new runtime cost class. | The freshness check introduces no new subprocess or pytest-collection step; it reads only the live source tree and the already-parsed CI workflow models (the current cost profile). | Draft |
| NFR-003 | Blast radius confined to enforcement surfaces. | `git diff --name-only` for the mission touches only `tests/architectural/*` and the committed census artifact; **zero** files under `src/` change. | Draft |
| NFR-004 | Gate remains non-vacuous. | A self-mutation test proves each tooth still bites: mutating the census (drop a dir, add a phantom dir, edit a routing target) and mutating the tree (simulate a floor-crossing) each turn the freshness gate red. | Draft |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | The committed census MUST NOT retain a per-directory exact line count that is compared for equality by the freshness gate. The `loc` field MUST be dropped at the **shared derivation** (`live_derived_worklist`), so the freshness test AND the `--verify-census` CLI (which consume the same derivation) both become LOC-insensitive by construction, with no stale count committed to the artifact. | Draft |
| C-002 | Membership and routing derivation MUST continue to use the existing canonical authorities — the frozen `_PRE_MISSION_MAPPED_SRC_DIRS` baseline and the committed `_COMPOSITE_ROUTING` plan — with no second authority introduced (single canonical source). | Draft |
| C-003 | ATDD red-first (charter C-011): a failing-first test MUST be committed as a separate commit before any implementation commit. The reproduction MUST use a **rank-altering** LOC churn between two adjacent worklist members, so a single failing-first test forces BOTH the loc-drop (FR-001) and order-insensitivity (FR-007) — neither can ship vacuously. | Draft |
| C-004 | Architectural-gate discipline (DIRECTIVE_043): the narrowed gate MUST ship with a non-vacuous self-mutation test; a gate change cannot self-validate. | Draft |
| C-005 | No terminology-canon regressions and no version numbers introduced into mission scope. | Draft |

## Success Criteria

| ID | Criterion (measurable, technology-agnostic) |
|----|---------------------------------------------|
| SC-001 | A PR that adds or removes lines in a worklist directory, without changing which directories are on the worklist or how they route, passes the CI-topology gate with no additional commit. |
| SC-002 | A census with a still-qualifying worklist directory removed fails the gate. |
| SC-003 | A worklist directory that drops below the LOC floor (and thus leaves the live worklist) fails the gate against a census that still lists it. |
| SC-004 | A new source directory at or above the LOC floor, absent from the census, fails the gate. |
| SC-005 | A census with a hand-edited routing target fails the gate. |
| SC-007 | A LOC change that alters the relative LOC *ranking* of two adjacent worklist members (a rank-swap), without changing membership or routing, passes the gate — proving order-insensitivity (FR-007) is delivered, not merely asserted. |
| SC-006 | Every pre-existing CI-topology worklist test still passes, and the full `tests/architectural/` suite is green. |

## Key Entities

- **CI-topology census** — committed artifact (`ci_topology_census.json`): worklist
  (membership + routing plan), mapped dirs, arch-blind groups, `t_loc` floor,
  timings baseline.
- **Worklist entry** — a directory's routing record: `dir`, `target_group`,
  `target_shard`, `cone_roots` (membership + routing; no exact LOC on the
  comparison surface after this mission).
- **Freshness gate** — the enforcement test asserting the committed census matches
  the live derivation on membership + routing, plus a live LOC-floor check.

## Assumptions

- The routing-completeness tests remain the load-bearing SC-001 protection and are
  not weakened by this mission (FR-008).
- `t_loc` stays 500; the LOC floor concept is retained, only the exact-count
  equality is removed.
- The frozen pre-mission mapped baseline (23 dirs) and the composite-routing table
  are the canonical membership/routing authorities and are unchanged.

## Out of Scope

- Re-tiering or re-sharding CI, or altering the routing plan itself.
- Auto-regenerating-and-committing the census in CI (option (b) in the ticket) —
  not needed once exact LOC is off the comparison surface.
- De-LOC'ing the `arch_blind_groups` census field. It is empty today and
  structurally pinned empty by `test_no_src_dir_is_architecturally_blind`, so any
  change there is unfalsifiable (no failing-first test can distinguish applied from
  not-applied). Deferred until a non-empty arch-blind row exists. Because C-001
  drops `loc` at the shared derivation, if such a row ever appears the same fix can
  be extended with a real self-mutation test at that time.
- Any change to production `src/` behavior.
