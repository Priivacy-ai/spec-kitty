# Tasks: Relocation-Hardened Dead-Code Scanners

**Mission**: relocation-hardened-dead-code-scanners-01KX958P (#2546) | **Branch**: `analysis/test-change-coupling`
**Plan**: [plan.md](plan.md) (c93a4e4, 2 post-plan squads remediated) | **Spec**: [spec.md](spec.md)

6 WPs, 29 subtasks. Keystone WP01 → sequential single-owner chain WP02→WP03; WP04/WP05/WP06 parallel.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | body-hash normalizer + `definition_span` (Class/Func/Assign/AnnAssign/single-alias-ImportFrom) | WP01 | |
| T002 | AnnAssign branch (FR-002, ≤14 typed constants) | WP01 | |
| T003 | facade-dict KEY-side resolver by-shape (FR-003, sync 2-tuple + runtime 1-value) | WP01 | |
| T004 | single-alias ImportFrom hash scoping (FR-004) | WP01 | |
| T005 | live collision classifier + key_tier + ≥2-escalate/fail-close (FR-005/FR-009) | WP01 | |
| T006 | fail-closed for None-key (FR-009) | WP01 | |
| T007 | unit tests + DoD-j key-invariance probe + perf-budget assertion | WP01 | |
| T008 | extend `_walk_modules` to retain source; invert map dotted→(tree,source) | WP02 | |
| T009 | thread source/AST into `_compute_offenders` (4 in-file call sites) | WP02 | |
| T010 | re-key all 394 entries onto SymbolKey (FR-007) | WP02 | |
| T011 | drop 2 stale (FR-006) + `_baselines.yaml` doc-count 215→213 | WP02 | |
| T012 | consume FR-005 classifier + FR-009 ≥2-escalation in the gate path | WP02 | |
| T013 | symbol-granular categories (FR-010) + disjointness meta-test | WP02 | |
| T014 | bite battery DoD (a,c,e,f,h,i,k) through production path + meta-guard green (FR-014) | WP02 | |
| T015 | third dangling-entry ratchet, tier-specific (FR-008) | WP03 | |
| T016 | body-sensitivity ONE-signal reconciliation | WP03 | |
| T017 | bite battery DoD (b,d,g) through production path | WP03 | |
| T018 | gate-side DoD-j 0-false-red through production path | WP03 | |
| T019 | assess `test_no_dead_modules.py` relocatable-anchor | WP04 | [P] |
| T020 | harden-if-relocatable ELSE downgrade-to-preserve + document (FR-011) | WP04 | [P] |
| T021 | preserve 4 detectors + cross-module __all__ + ratchet byte-unchanged (FR-012) | WP04 | [P] |
| T022 | confirm census categories (arch emitters + base.py in-arch) | WP05 | [P] |
| T023 | route the 5 arch report-only emitters off the warnings channel (FR-016) | WP05 | [P] |
| T024 | fix `src/doctrine/base.py` toolguide YAML (pydantic extra_forbidden) | WP05 | [P] |
| T025 | file contract round-trip legacy-backfill follow-up (out of arch scope) | WP05 | [P] |
| T026 | re-census: 0 first-party arch warnings (NFR-006/SC-005) + update issue-matrix follow-up (FR-015) | WP05 | [P] |

> **Orchestrator-authored (not a WP):** `issue-matrix.md` + `acceptance-matrix.json` are mission
> bookkeeping authored by the orchestrator on the coord surface (issue-matrix rows: #2546 in-mission,
> #2071 parent, #2293 adjacent, + the WP05 round-trip follow-up handle). Tracer close-notes are
> appended at mission close.

---

## WP01 — IC-KEY: relocation-tolerant symbol key + live collision classifier

**Goal**: new `tests/architectural/_symbol_key.py` producing a relocation-tolerant `SymbolKey`. **Keystone — every symbol-side WP consumes it.** | **Deps**: none | **Prompt**: [tasks/WP01-symbol-key.md](tasks/WP01-symbol-key.md) (~460 lines)

- [x] T001 body-hash normalizer + definition_span (WP01)
- [x] T002 AnnAssign branch (WP01)
- [x] T003 facade-dict KEY-side resolver by-shape (WP01)
- [x] T004 single-alias ImportFrom hash (WP01)
- [x] T005 live collision classifier + key_tier + ≥2-escalate/fail-close (WP01)
- [x] T006 fail-closed for None-key (WP01)
- [x] T007 unit tests + DoD-j key-invariance + perf-budget (WP01)

**Independent test**: `uv run pytest tests/unit/test_symbol_key.py -q` — key is relocation-tolerant, no bare-name-alone, AnnAssign+single-alias stable across 3.11↔3.12, ≥2-resolution fail-closes.

## WP02 — WP-REKEY-A: re-key 394 + classifier consumption + categories (single-owner, chain 1/2)

**Goal**: re-key `test_no_dead_symbols.py`'s 394 entries onto the SymbolKey; consume the live classifier (or the re-key re-blinds T004); symbol-granular categories; bite battery a,c,e,f,h,i,k. | **Deps**: WP01 | **Prompt**: [tasks/WP02-rekey-a.md](tasks/WP02-rekey-a.md) (~560 lines)

- [ ] T008 extend `_walk_modules` to retain source (WP02)
- [ ] T009 thread source/AST into `_compute_offenders` (WP02)
- [ ] T010 re-key 394 entries (WP02)
- [ ] T011 drop 2 stale + baseline doc-count (WP02)
- [ ] T012 consume classifier + ≥2-escalation (WP02)
- [ ] T013 symbol-granular categories + disjointness (WP02)
- [ ] T014 bite battery (a,c,e,f,h,i,k) + meta-guard green (WP02)

**Independent test**: `uv run pytest tests/architectural/test_no_dead_symbols.py tests/architectural/test_ratchet_positional_anchor_ban.py -q` + full arch 0-failed.

## WP03 — WP-REKEY-B: dangling ratchet + body-sensitivity (SAME owner, chain 2/2)

**Goal**: third dangling-entry ratchet direction (tier-specific) + body-sensitivity one-signal + bite b,d,g + gate-side DoD-j. **Sequential after WP02 — never concurrent (C-003 single-owner honored).** | **Deps**: WP02 | **Prompt**: [tasks/WP03-rekey-b.md](tasks/WP03-rekey-b.md) (~380 lines)

- [ ] T015 tier-specific dangling ratchet (WP03)
- [ ] T016 body-sensitivity one-signal (WP03)
- [ ] T017 bite battery (b,d,g) (WP03)
- [ ] T018 gate-side DoD-j 0-false-red (WP03)

**Independent test**: dangling fixtures red (both tiers); body edit → one signal; full arch 0-failed.

## WP04 — IC-MODULES: relocation-harden-or-preserve test_no_dead_modules.py

**Goal**: harden if a relocatable anchor exists, else downgrade-to-explicit-preserve + say so; preserve detectors + ratchet byte-unchanged. | **Deps**: none (parallel) | **Prompt**: [tasks/WP04-modules.md](tasks/WP04-modules.md) (~280 lines)

- [x] T019 assess relocatable anchor (WP04)
- [x] T020 harden-or-preserve + document (WP04)
- [x] T021 preserve detectors + ratchet byte-unchanged (WP04)

**Independent test**: `uv run pytest tests/architectural/test_no_dead_modules.py -q`.

## WP05 — IC-WARNINGS: census + root-remediate the ~40 suite warnings

**Goal**: route the enumerated arch report-only emitters off the warnings channel (preserve the signal); fix the src schema-skip; file the contract round-trip follow-up. **NO blanket filterwarnings=ignore.** | **Deps**: none (parallel, land first) | **Prompt**: [tasks/WP05-warnings.md](tasks/WP05-warnings.md) (~360 lines)

- [x] T022 confirm census categories (WP05)
- [x] T023 route the 5 arch emitters off the channel (WP05)
- [x] T024 fix src/doctrine/base.py toolguide YAML (WP05)
- [x] T025 file contract round-trip follow-up (WP05)
- [x] T026 re-census 0 first-party arch warnings (WP05)

**Independent test**: `uv run pytest tests/architectural/ -W default -r w` → 0 first-party warnings.

*(FR-015 ticket hygiene folds into WP05 T025/T026; the issue-matrix + acceptance-matrix are
orchestrator-authored — see the note under the Subtask Index.)*

---

## Dependencies

```
WP01 ──> WP02 ──> WP03
WP04 (parallel)
WP05 (parallel, land first)
```

## MVP scope

WP01 (the keystone key) + WP02 (the re-key that delivers relocation tolerance) are the
mission's core. WP05 (warnings) is independently valuable and lands first.
