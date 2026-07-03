# Implementation Plan: Refactor-Stable Gate Substrate

**Branch**: `tidy/gate-substrate` | **Date**: 2026-07-03 | **Spec**: [spec.md](spec.md) (rev 2)
**Input**: Mission specification from `kitty-specs/refactor-stable-gate-substrate-01KWK3FY/spec.md`

## Summary

Apply the operator's refactor-stable testing doctrine to the gate substrate itself,
ahead of the unshim wave: convert the last raw-line-keyed architectural gate
(`resolution_gate_allowlist.yaml`, 10 entries) to **Design-P** frozen
`(file, qualname, token)` comparands; redesign BOTH audit undercount tripwires (two
copy-paste twins, ~4 comparison sites across 3 files) to composite row identity with a
NEW overcount/ghost-row guard; codify the doctrine into the testing-principles
styleguide (+ DRG regeneration); and un-quarantine the 15 verified-passing tests with
honest reasons on the 3 stay-behinds. Zero production-code changes — the diff lives in
`tests/`, `src/doctrine/`, and `kitty-specs/`.

## Technical Context

**Language/Version**: Python 3.11+ (charter-mandated; existing codebase)
**Primary Dependencies**: stdlib `ast`/`tokenize` via the existing `tests/architectural/_ratchet_keys.py` primitives (`composite_key`, `composite_key_from_file`, `code_tokens_by_line`, `enclosing_qualname`); YAML for the allowlist; pytest; NO new dependencies
**Storage**: N/A (YAML allowlist + markdown inventories are committed doc-lockfiles)
**Testing**: pytest; the deliverables are themselves tests/gates — every converted gate ships the theater TRIAD (drift-green / content-change-red / new-offender-red) driven at the top-level entry points (`check_canonicalizer_gate` :462, `check_coord_authority_gate` :604 — the T005 self-mutation model); CT9 determinism under the real CI shard invocation form (`-n auto --dist loadfile`, marker-scoped; serial `-n0` where the file's class requires); `mypy --strict` + `ruff` on all touched files; both DRG byte-freshness gates
**Target Platform**: cross-platform dev/CI (Linux/macOS/Windows shards)
**Project Type**: single (test-substrate + doctrine surfaces only)
**Performance Goals**: gate runtime parity (composite derivation already runs in the compliant families; no measurable budget change)
**Constraints**: Design-P semantics (content-PINNING) per the mission ADR; no positive literal-presence scans; no standing content-coupled styleguide test (acceptance-time script instead); `graph.yaml` only via `generate_graph` (src/doctrine/drg/migration/extractor.py:767)
**Scale/Scope**: 10 allowlist entries + ~6 int-line test constructors (IC-01); 30+27 inventory rows across 2 audits, 4 comparison sites (IC-02/03); 1 styleguide + graph regen (IC-04); 15 markers out + 3 reason rewrites + 1 upstream issue (IC-05); 5–6 WPs

## Charter Check

*Evaluated against `.kittify/charter/charter.md` v1.3.0.*

| Charter rule | Status | Evidence |
|---|---|---|
| Single canonical authority (DIRECTIVE_044) | PASS | One composite-key primitive (`_ratchet_keys`) serves all conversions; Design-P documented as THE pattern with a named reference implementation; no second mechanism invented |
| Architectural alignment | PASS | Conversions extend existing gate files in place; the audits stay twins (consolidation is a REAL improvement but out of scope — recorded as a follow-up candidate in the FR-009 #2072 comment) |
| ATDD-first (C-011, parity form) | PASS | Theater triads land WITH each conversion, red-proven at the entry points; CT9 re-verifies the pass list before touching markers |
| Adversarial squad cadence | DONE post-spec (2 lenses, both material — Design-P ADR born there); post-tasks squad after `/spec-kitty.tasks` |
| Campsite cleaning (Standing Order 2) | PASS | Folds are the mission's own scope; uv-tool drift NOT folded (issue filed instead, C-003) |
| Test remediation discipline (DIRECTIVE_041) | PASS | Per-test judgment; no retry-to-green (NFR-004: flake → back behind quarantine with an honest reason) |
| Gate discipline (DIRECTIVE_043) | PASS | Theater TRIAD per converted gate; fail-closed freeze tooling; overcount guard added |
| Refactor-stable doctrine (the mission's subject) | PASS | C-001: deliverables use negative/behavioral forms; frozen comparands are tool-derived, never hand-typed; line survives only as a non-authoritative locator |
| Tidy-first / current-cycle ruling | PASS | Enabler for #2289–#2293; nothing deferred to a version boundary |
| Terminology canon | PASS | C-005 + pre-push guard |

**No violations — Complexity Tracking not required.**

## Project Structure

### Documentation (this mission)

```
kitty-specs/refactor-stable-gate-substrate-01KWK3FY/
├── plan.md                      # This file
├── research.md                  # Phase 0 (squad-evidence consolidation + decisions)
├── data-model.md                # Phase 1 (key schemas, row identities, triad contract)
├── quickstart.md                # Phase 1 (guard-running playbook)
├── contracts/
│   ├── gate-conversion-contract.md   # Design-P conversion rules + theater triad spec
│   └── audit-identity-contract.md    # Composite row identity + over/undercount tripwires
└── tasks.md                     # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
tests/architectural/
├── test_resolution_authority_gates.py   # IC-01: GateAllowlistKey gains rel_path + frozen token:str;
│                                        #   loader freezes; scanners emit (path, qualname, token);
│                                        #   ~6 int-line test constructors re-pinned; theater triad
├── resolution_gate_allowlist.yaml       # IC-01: entries gain file: + token: (frozen); line: → locator
├── untrusted_path_audit/
│   ├── audit.py                         # IC-02: Check-2 → composite identity; NEW overcount check
│   └── inventory.md                     # IC-02: rows re-keyed (line column = locator)
├── surface_resolution_audit/
│   ├── audit.py                         # IC-03: ResolutionRow Check-2 + SelectionRow check → composite;
│   │                                    #   NEW overcount check; split-brain reconciled
│   └── inventory.md                     # IC-03: rows re-keyed
├── test_untrusted_path_containment.py   # IC-02: the duplicated raw-line compare (:328) converted
└── test_no_worktree_name_guess.py       # IC-06: docstring note — Design-P REFERENCE (no key changes)

src/doctrine/
├── styleguides/built-in/testing-principles.styleguide.yaml  # IC-04: refactor-stable principles
└── graph.yaml                                               # IC-04: regenerated via generate_graph

tests/ (quarantine files)                # IC-05: 15 markers removed (~5 files);
                                         #   2 uv-tool reasons rewritten; A16 reason kept
```

**Structure Decision**: all changes in place — no new modules; the two audits stay
twins (twin-ness documented; consolidation named as a follow-up candidate, not
attempted).

## Key Design Decisions (full detail in research.md)

1. **Design-P (content-pinning)** — the mission ADR (tracer #6): the tool-derived token
   is FROZEN in the allowlist/inventory as the authoritative comparand; the live
   scanner re-derives and checks membership. Chosen over Design-S on renata's empirical
   proof that seed re-derivation fails both NFR-001 halves.
2. **`rel_path` joins every key** (tracer #7): qualname collisions (`implement`/`review`
   ×2) are disambiguated only by line today; post-conversion by path+token. The YAML
   gains `file:`; violation messages keep a `file:line` locator (non-authoritative).
3. **Freeze tooling is fail-closed** (FR-003): the one-time converter aborts on a seed
   that does not resolve to a function-scoped site; at runtime the staleness guard
   (frozen key with no live match) fails loudly with evict-or-re-approve guidance.
4. **Audits stay twins; identity unifies** (tracer #8): both convert to
   `(path, qualname, token)` rows via `composite_key_from_file`; the overcount guard
   (inventory row without a live sink → RED, modulo explicitly-tagged rows) lands in
   both, closing the ghost-row hole before the unshim deletions could exploit it.
5. **CT9 evidence bar** (tracer #9): real CI shard invocation form, twice, plus a green
   CI run pre-merge; any flake reverts to quarantine with an honest reason.
6. **Doctrine completion evidence** is an acceptance-time parse script (≥6 principles,
   each with non-empty good/bad examples, ≥1 citing PR #2308) — NOT a standing
   content-coupled suite test (C-001).

## Implementation Concern Map

> Concerns ≠ work packages; `/spec-kitty.tasks` translates.

### IC-01 — Resolution-gate Design-P conversion

- **Purpose**: The last raw-line-keyed gate becomes drift-immune + content-detecting.
- **Relevant requirements**: FR-001, FR-002, FR-003; NFR-001; SC-001/SC-002.
- **Affected surfaces**: `tests/architectural/test_resolution_authority_gates.py`, `tests/architectural/resolution_gate_allowlist.yaml`.
- **Sequencing/depends-on**: none (foundation; its recipe is the conceptual template for IC-02/03).
- **Risks**: the ~6 int-line test constructors + `derive_live_key` unit tests convert in the same WP (mypy --strict breaks otherwise); diagnostics keep a clickable locator; within-function token collisions need the documented disambiguation rule.

### IC-02 — Untrusted-path audit identity redesign

- **Purpose**: Kill the #2306 failure class at its origin; add the ghost-row guard.
- **Relevant requirements**: FR-004 (untrusted sub-stream); NFR-001; SC-003.
- **Affected surfaces**: `tests/architectural/untrusted_path_audit/audit.py` + `inventory.md` + the duplicated compare in `tests/architectural/test_untrusted_path_containment.py:328`.
- **Sequencing/depends-on**: none (files disjoint from IC-01).
- **Risks**: inventory re-key must preserve reviewer readability (30 rows); the tagged-row escape for intentional inventory-only entries stays narrow and documented.

### IC-03 — Surface-resolution audit identity redesign

- **Purpose**: The twin's redesign PLUS reconciling the existing split-brain (its inventory line column is already consumed as a composite seed by `test_single_mission_surface_resolver.py` while its own audit compares raw lines) and converting the second SelectionRow check.
- **Relevant requirements**: FR-004 (surface sub-stream); NFR-001; SC-003.
- **Affected surfaces**: `tests/architectural/surface_resolution_audit/audit.py` + `inventory.md`; read-only coordination with `test_single_mission_surface_resolver.py` (already Design-S-compliant in its own family — must stay green UNMODIFIED).
- **Sequencing/depends-on**: none (disjoint files); reuses IC-02's recipe if serialized.
- **Risks**: TWO row types (ResolutionRow + SelectionRow) with separate checks; the reconciliation must not break the resolver test's seed consumption.

### IC-04 — Doctrine styleguide + DRG

- **Purpose**: CT8 — the refactor-stable rules become governance.
- **Relevant requirements**: FR-006; SC-005.
- **Affected surfaces**: `src/doctrine/styleguides/built-in/testing-principles.styleguide.yaml`, `src/doctrine/graph.yaml` (via `generate_graph`), the acceptance-check script (mission-dir artifact).
- **Sequencing/depends-on**: none (fully independent).
- **Risks**: byte-freshness gates; the styleguide's own bad-examples are quoted content, not live scans (C-001).

### IC-05 — CT9 un-quarantine

- **Purpose**: 15 passing tests return to duty; honest reasons on the 3 stay-behinds.
- **Relevant requirements**: FR-007, FR-008; NFR-004; SC-004.
- **Affected surfaces**: the quarantine-marked test files (~5 files: retrospect, upgrade-ux, decision-widen, decision-shape, doctor-ops); 1 upstream issue (uv-tool drift).
- **Sequencing/depends-on**: none (fully independent).
- **Risks**: implement-day re-verification may shrink the 15 (flakes revert honestly); CI-shard-form evidence required.

### IC-06 — Reference-pattern documentation + closeout

- **Purpose**: FR-005 (reframed) — document `test_no_worktree_name_guess.py` as the Design-P reference (no key changes); FR-009 tracker closeout (#2310/#2311 close; #2072 partial comment naming the drain remainder + the audit-twin-consolidation candidate).
- **Relevant requirements**: FR-005, FR-009.
- **Affected surfaces**: one docstring note; tracker; tracers close-out.
- **Sequencing/depends-on**: after IC-01..IC-05 (closeout).
- **Risks**: none material.

## Progress Tracking

- [x] Phase 0: research.md (squad-evidence consolidation: Design-P proof, collision tests, consumer graphs; entry points + generate_graph path verified live)
- [x] Phase 1: data-model.md, contracts/ (gate-conversion + audit-identity), quickstart.md
- [x] Charter Check: PASS, no violations
- [ ] Phase 2: /spec-kitty.tasks (NOT this command)
