# Implementation Plan: Meta.json Fail-Closed Read Routing

**Branch**: `feat/meta-json-l1-seam-routing-3259` | **Date**: 2026-08-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/meta-json-fail-closed-routing-01KZPJ1F/spec.md`

## Summary

Close epic #3259 by routing all five remaining `meta.json` bypass reads through the canonical fail-closed seam. The primary requirement is **fail loud on a corrupt `meta.json` at every read path** (US1/FR-004/NFR-005). The technical approach, confirmed by the post-spec adversarial squad, is: introduce a **kernel-resident L1 pure-decode primitive** (`text|bytes → dict|None`, no I/O, `None` == malformed only) plus a kernel typed error, re-express L2 (`mission_metadata._parse_meta_text`) and L3 (`core.paths.load_meta_fail_closed`) on top of it, add a public path-level L2 entry, and delete the three private parsers — re-pointing their five call sites onto the seam. In the same work, unify the duplicated VCS-lock comparator into a single kernel symbol (absent ≠ null, C-005), teach the routed-census gate to count the new decode symbols and re-derive its floor from a live measurement within the gate's own margin, and record the #3240 allow-list governance deviation.

Kernel placement is load-bearing: the git-plumbing site (A, in `git/ref_advance.py`) may not import `specify_cli` (C-003), and L2 lives in `mission_metadata.py` which does — so L1 and the comparator must live in `src/kernel/` (the CI-enforced zero-dependency root), which both plumbing and application layers may depend on.

## Technical Context

**Language/Version**: Python 3.12 (repo targets 3.11+; CI runs 3.12)
**Primary Dependencies**: stdlib `json` only for decode; `pytest` for tests; no new runtime dependency
**Storage**: `meta.json` files on disk + git blobs (`git show` stdout / `GitPort.show_blob` bytes / temp merge blobs) — read-only in this mission
**Testing**: pytest; ATDD red-first per site (captured failing baseline against pre-routing code); architectural gates in `tests/architectural/`; real-git sites carry `[integration, git_repo]` markers (C-004)
**Target Platform**: Linux/macOS developer + CI (the spec-kitty CLI itself)
**Project Type**: single project (internal CLI/library refactor — no new API surface)
**Performance Goals**: N/A (pure decode of small JSON blobs; no hot-path change)
**Constraints**: `git/ref_advance.py` imports **0** `specify_cli` modules (C-003/NFR-004); routed-census gate stays within its margin; three named gates green; behavior-preserving except the deliberate C-005 absent≠null change
**Scale/Scope**: 5 read sites across 3 modules; 3 private parsers deleted → 1 kernel decoder; 2 comparators + 2 field-sets → 1 kernel comparator + 1 named field-set; ~3 src modules + kernel additions + the gate test file + 2 new diagnosability test files

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter mode: compact (`software-dev-default`). Relevant governing principles and their status in this plan:

- **Single canonical authority** — the mission's *purpose*: one L1 decoder owns the malformed definition; one kernel comparator owns the VCS-lock verdict. Enforced by FR-010 (enumeration gate) and NFR-002. ✅ aligned.
- **Architectural alignment / layering** — `kernel <- doctrine <- charter <- specify_cli`; kernel is zero-dep. Placing L1 + comparator in kernel respects this and relieves an existing `core.paths`↔`mission_metadata` cycle. A new ratchet (NFR-004) pins `ref_advance` free of `specify_cli`. ✅ aligned.
- **ATDD-first / red-first** — FR-007 requires a captured red baseline per site before the fix. ✅ aligned.
- **Terminology adherence** — canonical `Mission`/`meta.json`; no legacy terms introduced. ✅.
- **Tech-debt standing orders** — this mission *is* tech-debt burn-down (epic #3259); campsite rule applies (reconcile the `implement.py` shim, correct the site taxonomy). ✅.

No charter violations requiring Complexity Tracking. Layer boundary is the single hard gate — addressed by C-008 kernel placement + NFR-004 ratchet.

## Project Structure

### Documentation (this mission)

```
kitty-specs/meta-json-fail-closed-routing-01KZPJ1F/
├── plan.md              # This file
├── research.md          # Phase 0 — decisions (kernel placement, census mechanics, empty-vs-malformed)
├── data-model.md        # Phase 1 — seam tiers, L1 contract, comparator semantics, site taxonomy, gates
├── quickstart.md        # Phase 1 — how to measure the live census + run the three gates + red-first pattern
├── checklists/          # spec quality checklist
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

No `contracts/` directory: this mission adds no API/event surface (internal decode/compare refactor). Recorded as N/A in Phase 1.

### Source Code (repository root)

```
src/
├── kernel/                              # zero-dep root — NEW homes (C-008)
│   ├── meta_decode.py  (NEW)            #   L1 decode_meta(text|bytes)->dict|None + MetaDecodeError
│   └── vcs_lock.py     (NEW)            #   unified VCS-lock field-set + comparator (absent != null)
├── specify_cli/
│   ├── mission_metadata.py             # L2 _parse_meta_text re-expressed via kernel L1; public parse_meta_file()
│   ├── core/paths.py                    # L3 load_meta_fail_closed re-expressed via kernel L1 (read-only otherwise)
│   ├── git/ref_advance.py              # sites A/B: delete _parse_meta_object; route onto kernel L1; use kernel comparator; 0 specify_cli imports
│   └── cli/commands/
│       ├── implement_cores.py          # sites C/D: delete _parse_meta_mapping; route onto kernel L1
│       ├── implement.py                # reconcile the :62-70 historical-location shim re-export
│       └── merge_driver.py             # site E: route _load_json_object via public L2

tests/
├── architectural/
│   ├── test_inline_meta_read_gate.py   # extend ROUTED_CALLEES; re-derive ROUTED_LOAD_META_FLOOR; add FR-010 enumeration+completeness gate
│   ├── test_layer_rules.py             # add/extend NFR-004 ratchet: ref_advance imports no specify_cli
│   └── test_meta_decode_l1.py (NEW)    # L1 pure-decode unit coverage (valid/None/malformed/bad-unicode/non-object; str+bytes)
├── specify_cli/
│   ├── cli/commands/test_meta_bypass_diagnosability.py (NEW)   # sites C/D/E red-first [integration, git_repo]
│   └── git/test_ref_advance_meta_diagnosability.py     (NEW)   # sites A/B red-first [integration, git_repo]
└── specify_cli/test_meta_fail_closed_full_census_contract.py   # ledger stays green
```

**Structure Decision**: single-project layout. The only structural novelty is two new **kernel** modules (`src/kernel/meta_decode.py`, `src/kernel/vcs_lock.py`) that host the decode primitive and the unified comparator so both git-plumbing and application layers can depend on them without violating the layer rule.

## Complexity Tracking

No Charter Check violations. (The two new kernel modules are the *simpler* alternative — the rejected option, co-locating L1 in `mission_metadata.py`, is what makes site A un-routable.)

## Implementation Concern Map

> Concerns, not work packages. `/spec-kitty.tasks` maps these to WPs.
>
> **Census model (corrected after post-plan review — load-bearing).** The five sites route onto the **new** symbols `decode_meta` (L1) and `parse_meta_file` (public L2), which are **not** in `ROUTED_CALLEES`, and the deleted private parsers were never routed callees either. Therefore **IC-02/03/04 change the routed census by exactly 0** — the gate stays green at floor 130 / live 134 across all three; they do **not** "re-derive the floor." The census makes **one** step-change in **IC-05**, when `ROUTED_CALLEES` gains `decode_meta` + `parse_meta_file` (counting the 5 routed sites *and* every internal L1/L2/L3 call at once), after which IC-05 re-pins `ROUTED_LOAD_META_FLOOR = fresh_live − 3` (within margin 4) in the same commit. **Trap to avoid:** routing site E onto `load_meta_or_empty` (already a `ROUTED_CALLEES` member, the tempting empty→`{}` choice) would bump the census mid-WP and red the gate — E MUST route onto the still-uncounted `parse_meta_file`.
>
> **Error-type translation (load-bearing).** `kernel.meta_decode.MetaDecodeError` **extends `ValueError`** so every existing `except ValueError` boundary (L3 `paths.py:677`, `decisions/service.py`, `upgrade/feature_meta.py`) keeps catching by inheritance. L2 re-wraps L1's error into a `ValueError` carrying its **legacy path-named messages** (`"Malformed JSON in {path}"`, `"Expected JSON object in {path}, got {type}"`) so the message-pinned regressions (`test_mission_metadata.py:95,101`, `test_feature_metadata.py:85,92`, `test_load_meta_fail_closed_authority.py`) stay green. L1 owns the malformed *definition*; L2 owns the path-named *message*.

### IC-01 — Kernel decode + comparator foundation

- **Purpose**: Establish the single fail-closed decode authority and the single VCS-lock comparator in the zero-dep layer, so every site (incl. git-plumbing) can route onto them.
- **Relevant requirements**: FR-001, FR-002, FR-006 (placement), NFR-001 (authority), C-008, C-010 (empty-vs-malformed boundary lives at L2/caller, not L1).
- **Affected surfaces**: `src/kernel/meta_decode.py` (NEW — `decode_meta` + `class MetaDecodeError(ValueError)`; explicit `raw.decode("utf-8")` before `json.loads` so bad-byte input raises `UnicodeDecodeError`, not auto-detected `JSONDecodeError`), `src/kernel/vcs_lock.py` (NEW), `src/specify_cli/mission_metadata.py` (L2 re-express + public `parse_meta_file`; preserve legacy `ValueError` messages), `src/specify_cli/core/paths.py` (L3 re-express directly on kernel L1 — removes the `paths.py:670` `mission_metadata.load_meta` back-edge, relieving the cycle), `tests/architectural/test_meta_decode_l1.py` (NEW; assert `MetaDecodeError` wraps `UnicodeDecodeError` on `b"\xff\xfe\x00"`).
- **Sequencing/depends-on**: none (must land first; census-neutral — no `ROUTED_CALLEES` change, no deletions).
- **Risks**: preserving L2's empty→benign short-circuit (C-010); the L3 re-express drops L3's internal `load_meta` call, which shifts the routed census by −1 (134→133, still in band) — **measure live before/after IC-01 and stay in band** (documented 4th-recurrence trap of "re-express silently drops a counted call"); L1 typed error must be raisable by plumbing (kernel-resident) and be a `ValueError` subclass.

### IC-02 — ref_advance routing + comparator unification (atomic)

- **Purpose**: Route sites A and B fail-closed and switch ref_advance onto the kernel comparator, in one importable unit.
- **Relevant requirements**: FR-003 (delete `_parse_meta_object`; rewire B), FR-004 (route A), FR-005 (site-A **captured pre-routing baseline** + A/B valid/missing/empty preservation), FR-006 (use kernel comparator, absent≠null C-005), FR-007 (red-first A/B), NFR-004 (ref_advance imports no `specify_cli`).
- **Affected surfaces**: `src/specify_cli/git/ref_advance.py` (delete `_parse_meta_object` + `_VCS_LOCK_META_FIELDS` + `_is_vcs_lock_only_meta_change`; import kernel L1 + comparator), `tests/specify_cli/git/test_ref_advance_meta_diagnosability.py` (NEW, `[integration, git_repo]`), **`tests/specify_cli/cli/commands/test_issue_2795_claim_blocker.py`** (imports `_is_vcs_lock_only_meta_change` + `_parse_meta_object` and asserts `_parse_meta_object("{not json") is None` at `:300` — retarget onto kernel L1 red-first + kernel comparator), `tests/architectural/test_layer_rules.py` (NFR-004 ratchet — a **bespoke AST scan** mirroring `TestRuntimeBoundary:341-354`, NOT a pytestarch `LayerRule`, since ref_advance lives inside the specify_cli layer).
- **Sequencing/depends-on**: IC-01. **Census-neutral** (routes onto uncounted `decode_meta`).
- **Risks**: deletion breaks in-module callers A(:247) and B(:206) — atomic; the comparator move changes the absent-vs-null verdict by design (US2 AC1) — not behavior-preserving on that arm; the `_committed_meta_object` **absent-at-HEAD** arm (`git show` `returncode != 0`, `:204-207`) stays benign `{}` — only a present-but-unparseable committed blob fails loud.

### IC-03 — implement_cores + implement routing + second comparator retirement (atomic)

- **Purpose**: Route sites C and D fail-closed, retire `implement_cores`' *own* second comparator/field-set, and reconcile the historical-location shim.
- **Relevant requirements**: FR-003 (delete `_parse_meta_mapping`; rewire C at `implement_cores.py:427` and D at `:338`; reconcile `implement.py:62-70` shim), **FR-006 + NFR-002** (retire `implement_cores._VCS_LOCK_META_FIELDS:50` + `_is_vcs_lock_only_meta_diff:241`; adopt the kernel comparator — else IC-05's NFR-002 gate reds with no owner), FR-005 (C/D valid/missing/empty preservation), FR-007 (red-first C/D — **unit-testable via the `GitPort` fake at `implement_cores.py:112`; NO `git_repo` marker needed**).
- **Affected surfaces**: `src/specify_cli/cli/commands/implement_cores.py`, `src/specify_cli/cli/commands/implement.py` (`:62-70` shim re-exports **both** `_parse_meta_mapping` and `_is_vcs_lock_only_meta_diff` — retire/retarget, never dangle a name to a deleted symbol), `tests/specify_cli/cli/commands/test_meta_bypass_diagnosability.py` (NEW, C/D arms), and the binding tests pedro enumerated: **`test_implement_cores.py:29-30,262-268`** (imports `_parse_meta_mapping`/`_is_vcs_lock_only_meta_diff`, asserts `is None` → rewrite to `pytest.raises(MetaDecodeError)`), **`test_implement_vcs_lock_claim.py:39,405`**, **`test_specify_topology_flag.py:597`** (imports `_is_vcs_lock_only_meta_diff` via the shim), **`test_trio_seam_only.py:625,639`** + **`test_exemption_registry_ratchet.py:436`** (register `_is_self_write_only_diff`; the `:627` token-substring `"source . read_bytes ( )"` stays green **only if** site C's read stays inline in `_is_self_write_only_diff`).
- **Sequencing/depends-on**: IC-01. **Census-neutral**.
- **Risks**: the shim/external-test blast radius above must be budgeted or the gate WPs red on unbudgeted collateral; site C's real decode is at `:427` (the `:471` byte-compare is not a decode — do not force-fail it, and keep the read inline for the trio gate).

### IC-04 — merge_driver routing

- **Purpose**: Route site E through the public L2 entry with an exception-translating wrapper.
- **Relevant requirements**: FR-003 (route E onto **`parse_meta_file`**, NOT `load_meta_or_empty`), FR-005 (preserve empty→`{}`), FR-007 (red-first E reflecting its two error arms).
- **Affected surfaces**: `src/specify_cli/cli/commands/merge_driver.py` (`_load_json_object:174` stays a thin wrapper: empty→`{}` short-circuit, then `parse_meta_file(on_malformed="raise")`, **catching `MetaDecodeError` → re-raising `EventLogMergeError(path)`** to preserve `test_merge_driver_wrappers_2709.py:112-116`), `tests/specify_cli/cli/commands/test_meta_bypass_diagnosability.py` (E arm).
- **Sequencing/depends-on**: IC-01 (public L2 entry). **Census-neutral**.
- **Risks**: E's two **error arms** (malformed→currently-unnamed `JSONDecodeError`; non-object→already-named `EventLogMergeError`) — the red-first test reflects that. **Out of scope:** `_parse_json_document:337` is the row-matrix reader (`RowMatrixMergeError`), NOT a `meta.json` decode — do not route it, and IC-05's FR-010 gate must exclude it.

### IC-05 — Census extension, governance gates, and closeout

- **Purpose**: Perform the single census change, make the gates honest, and record the governance call once all routing has landed.
- **Relevant requirements**: FR-008 (extend `ROUTED_CALLEES` with `decode_meta` + `parse_meta_file`, then re-pin `ROUTED_LOAD_META_FLOOR = fresh_live − 3` within margin, same commit), FR-009 (#3240 deviation record), FR-010 (enumeration gate scoped to **meta content** — an argument/path allow-set excluding `_parse_json_document:337` and the kernel L1 itself — plus the completeness check), NFR-001/NFR-003 (single decoder; three named gates green), SC-001/SC-003/SC-004.
- **Affected surfaces**: `tests/architectural/test_inline_meta_read_gate.py` (`ROUTED_CALLEES` + floor + FR-010 gate), a governance deviation record (issue #3240 note / doc), `tests/specify_cli/test_meta_fail_closed_full_census_contract.py` (ledger).
- **Sequencing/depends-on**: IC-02, IC-03, IC-04 (all routing must be in before the single census change). This is the **only** concern that touches the floor.
- **Risks**: the floor must be measured live *after* all routing, not copied; extending `ROUTED_CALLEES` is required or the routing is invisible to the census (FR-008 no-op); the FR-010 enumeration gate must scope to meta content so it does not false-positive on the kernel L1 or the row-matrix decoder.
