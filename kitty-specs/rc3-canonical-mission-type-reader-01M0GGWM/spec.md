# Mission Specification: M5 — Canonical mission-type reader

**Mission Branch**: `[TBD-canonical-mission-type-reader]`
**Created**: 2026-08-20
**Status**: Draft (LIGHT spec — specify-phase only; NOT finalized). Operator decisions resolved 2026-08-20.
**Input**: Investigation `docs/plans/investigations/friction-bugs-processing-charter-root-cause.md` (§2.3, §6 decision #2, §11); issue #3598 "second inconsistency". One of eight specs feeding a single-branch pre-rc2 PR.

> **Scope guard.** This mission converges the hand-rolled `meta.json` mission-type readers onto one shared canonical reader in **explicit, per-reader, test-pinned steps** — NOT a blanket sweep. The *per-type unknown-mission-type resolution fix* (the primary half of #3598, `_resolve_governance_slot` project-wide probe → per-type probe) is **Mission M3** and is **out of scope here**. M5 is the reader convergence, the legacy-`mission` retirement, and the folded reader-consolidation items below.

---

## Problem & Impact (BLUF)

A single blessed canonical reader exists — **`src/specify_cli/mission.py:_canonical_meta_mission_type`** (line 542) — yet ~10–12 **hand-rolled** readers each re-derive their own field order and their own default, and they **disagree**:

- **The charter path** (`src/charter/mission_type_profiles.py:_read_meta_mission_type`, line 748/762) reads **only** `mission_type`, while the CLI path also honors legacy `mission` — so `{"mission": "software-dev"}` resolves **typeless** one way and **software-dev** the other (#3598's "second inconsistency").
- **Four readers silently default `software-dev`** (`mission_metadata.py:255`, `retrospective/generator.py:1319`, `charter/interview.py:225`, migration `migration/mission_state.py:1617`), masking typeless/typo'd missions.
- **A dashboard reader** (`dashboard/handlers/features.py:68`) reads **only** legacy `mission`, ignoring the canonical field entirely.

**Operator ruling (2026-08-20):** legacy `{"mission": …}` resolution is **retired entirely**. Every reader resolves the canonical `mission_type` field only, via one shared runtime-neutral helper; the silent `software-dev` defaults are removed. This is a **deliberate behavior change with real blast radius** — a legacy mission carrying only `{"mission": …}` (no `mission_type`) will **stop resolving** (becomes typeless) and requires a `mission_type` backfill. It **compounds with M3**: once M3's #3598 per-type hard-fail lands, an unmigrated legacy mission goes from *silently resolving* today, to *typeless* under M5 alone, to a *hard-fail* under M5+M3 together.

Two adjacent reader-consolidation items are **folded into this mission** by operator decision: #2901 (WP-frontmatter failure-classification N-reader) and #2477–#2480 (inline `meta.json` reads in frozen migrations / charter layer).

**Verified against `main`** (grep census of `mission_type` / `"mission"` reads under `src/`, 2026-08-20). Census in the Appendix.

---

## In Scope

- Introduce a shared runtime-neutral **`read_mission_type(meta: dict) -> str | None`** helper (canonical `mission_type` field → `canonical_mission_type_key` → `None`; **no legacy fallback**), and make `_canonical_meta_mission_type` a thin delegate to it.
- Route **every in-scope runtime `meta.json` mission-type reader** through the shared helper, one reader per step, each pinned by a test.
- **Retire legacy `mission`-field resolution** everywhere a runtime reader resolves a mission type (including `_canonical_meta_mission_type` itself, the charter path, dashboard, retrospective, interview).
- **Remove the silent `software-dev` substitution** from runtime readers; the neutral typeless result is returned and each caller handles it at its own boundary.
- **Migration:** provide/verify a `mission_type` backfill so legacy `{"mission": …}`-only missions gain a canonical `mission_type` before their resolution stops; verify whether `migrate backfill-identity` covers this (it currently does **not** — it mints `mission_id` only) and stand up a `mission_type` backfill if needed.
- **Fold #2901:** consolidate WP-frontmatter failure-classification behind one tolerant reader (`status/wp_metadata.py`).
- **Fold #2477–#2480:** route the inline `meta.json` reads in the frozen migrations and the charter layer onto the shared helper / a matching `load_meta*` adapter, with byte-exact replay-equivalence checks (or an explicit encoded allow-list exemption where equivalence cannot be guaranteed).
- Structural test asserting the "identical to canonical" invariant and the "no `software-dev` fallback / no legacy `mission` read" invariants.

## Out of Scope

- The per-type unknown-mission-type resolution fix (`_resolve_governance_slot`) — **Mission M3 / #3598 primary half**.
- Any redesign of `canonical_mission_type_key`'s normalization rules (it is reused as-is; only the field set feeding it changes).
- Dashboard visual/UX changes beyond correcting which field is read.
- Event-log / `status/models.py` `mission_type` reads (structured event payloads, not raw `meta.json`).
- The deep terminal-state family and other §11 fold candidates not named above (#3407, #3548, #2991, etc.).

---

## Functional Requirements

| ID | Title | Requirement | Priority | Status |
|----|-------|-------------|----------|--------|
| FR-001 | Shared canonical reader | A single runtime-neutral `read_mission_type(meta) -> str \| None` helper MUST be the sole resolution authority; `_canonical_meta_mission_type` and every in-scope reader delegate to it. | High | Open |
| FR-002 | Legacy `mission` retired | No in-scope runtime reader MAY resolve a mission type from the legacy `mission` field. Only the canonical `mission_type` field is read. | High | Open |
| FR-003 | No silent `software-dev` default | No in-scope runtime reader MAY substitute `software-dev` (or any concrete type) for an absent/blank/malformed value; the neutral typeless result (`None`/`""`) is returned. | High | Open |
| FR-004 | Layer-legal placement | The shared helper MUST sit in a layer importable by both `charter` and `specify_cli` (beside `canonical_mission_type_key` in `src/charter/mission_type_key.py`), introducing no `charter → specify_cli` edge (#2480 constraint; `test_layer_rules.py`). | High | Open |
| FR-005 | Dashboard reads canonical field | `dashboard/handlers/features.py` MUST resolve via the shared helper (canonical field only), not the legacy field. | High | Open |
| FR-006 | Per-reader, test-pinned steps | Convergence MUST land as explicit per-reader steps, each with its own regression test; a blanket search-and-replace sweep is prohibited. | High | Open |
| FR-007 | `mission_type` backfill migration | A migration MUST backfill `mission_type` (from legacy `mission`) for existing missions before legacy resolution is removed, so no in-flight legacy mission is stranded typeless. Confirm `backfill-identity` coverage; add a `mission_type` backfill if absent. | High | Open |
| FR-008 | Fold #2901 | WP-frontmatter read-failure classification MUST be answered by one tolerant reader in `status/wp_metadata.py`; the 4+ divergent catch/recovery sites route through it. | Medium | Open |
| FR-009 | Fold #2477–#2480 | The inline `meta.json` reads in the frozen migrations (`m_0_13_0`, `m_0_13_5`, `m_0_13_8`) and the two charter-layer reads (#2480) MUST route onto the shared helper / `load_meta*` with a replay-equivalence check, or carry an explicit encoded allow-list exemption. | Medium | Open |
| FR-010 | Structural invariants pinned | A repo test MUST assert (a) every in-scope reader returns identical results to the shared helper, and (b) no in-scope reader module carries a `software-dev` mission-type fallback or a legacy `mission`-field read. | High | Open |

---

## Acceptance Criteria (Given/When/Then)

**AC-1 — All readers resolve through the shared helper, structurally (FR-001, FR-006, FR-010)**
- **Given** any `meta.json`, **When** any in-scope reader resolves the mission type, **Then** it returns exactly what `read_mission_type(meta)` returns for the same dict — asserted by a **structural** table-driven test over every reader, not per-reader duplication.
- **Given** `{"mission_type": "research"}`, **When** the dashboard handler resolves it, **Then** the dashboard shows `research` (regression pin for `features.py:68`, previously `software-dev`).

**AC-2 — Legacy `{"mission": …}` no longer resolves (FR-002)**
- **Given** a `meta.json` with **only** `{"mission": "software-dev"}` (no `mission_type`),
  **When** any in-scope reader — CLI, charter, dashboard, retrospective, interview — resolves it,
  **Then** it returns the neutral typeless value (`None`/`""`) — the legacy value does **not** resolve.
- **Given** the same legacy-only input, **When** the CLI path and the charter path both resolve it, **Then** they agree (both typeless) — the #3598 split is closed by convergence *downward* to canonical-only, not by adding the fallback.

**AC-3 — No silent `software-dev` default remains (FR-003, FR-010)**
- **Given** a typeless `meta.json`, **When** each in-scope runtime reader resolves it, **Then** it returns neutral typeless; **no** reader returns `software-dev`.
- **Given** a typo'd `{"mission_type": "softwaer-dev"}`, **When** each reader resolves it, **Then** the typo is not normalized to `software-dev` (canonicalizes to typeless/unknown, surfacing the error).
- A structural test asserts no in-scope reader module contains a `"software-dev"` mission-type fallback or a legacy `mission` read (allow-list only for encoded, rationale-carrying exemptions).

**AC-4 — Charter reader stays layer-legal (FR-004)**
- **Given** convergence has landed, **When** `test_layer_rules.py::test_charter_does_not_import_specify_cli` runs, **Then** it passes.

**AC-5 — Legacy missions are backfilled before resolution stops (FR-007)**
- **Given** an existing mission whose `meta.json` carries only `{"mission": "research"}`,
  **When** the mission's `mission_type` backfill migration runs,
  **Then** the `meta.json` gains `{"mission_type": "research"}` and the mission continues to resolve as `research` after legacy resolution is removed.
- **Given** `migrate backfill-identity`, **When** its coverage is audited, **Then** the mission documents whether it backfills `mission_type` (it does not today) and which command now does.

**AC-6 — Folded consolidations land (FR-008, FR-009)**
- **Given** a malformed / wrong-shape WP `.md` frontmatter, **When** it is read, **Then** classification and recovery come from the single tolerant reader in `status/wp_metadata.py` (the divergent sites in `dossier/indexer.py`, `sync/history_import/scan.py`, `audit/classifiers/wp_files.py`, etc. route through it) — pinning the #2884 B3 "incomplete import reported as success" defect closed.
- **Given** the frozen migrations `m_0_13_0` / `m_0_13_5` / `m_0_13_8`, **When** their fixtures replay, **Then** behavior is byte-exact vs. `main` (equivalence check) OR the site carries an encoded `inline_meta_read_allowlist.yaml` exemption citing #2477–#2480.

**AC-7 — Census complete and classified (FR-006)**
- **Given** the mission is complete, **When** the Appendix census is reviewed, **Then** every reader is marked converged / already-equivalent / exempt-with-rationale, and a newly-added `meta.json` mission-type reader would trip AC-3's structural test.

---

## Key Design Decisions

1. **Shared runtime-neutral helper beside `canonical_mission_type_key`.** `canonical_mission_type_key` already lives in **`src/charter/mission_type_key.py`** — the `charter` layer, *below* `specify_cli` and importable by both. A dict-based `read_mission_type(meta) -> str | None` placed there (read `mission_type` → `canonical_mission_type_key` → `None`) becomes the one authority both layers call, **dissolving #2480's import blocker** (which is why #2480 folds in cleanly). `_canonical_meta_mission_type` collapses to a delegate. File I/O stays per-reader (dict-in helper); each reader keeps its own `meta.json` load.
2. **Convergence is *downward* to canonical-only, not upward to legacy.** The #3598 split closes because both paths stop reading legacy `mission`, not because the charter path gains it. This is the operator's deliberate legacy-retirement — the migration (FR-007) is the safety net that makes it non-breaking for real projects.
3. **Per-reader, test-pinned steps.** Suggested order: (a) shared helper + delegate `_canonical_meta_mission_type`; (b) `mission_type` backfill migration **first** among behavior-changers, so no mission is stranded; (c) charter `_read_meta_mission_type`; (d) dashboard `features.py`; (e) the `software-dev` defaulters; (f) neutral-None / field-aware hand-rolls; (g) fold #2901; (h) fold #2477–#2480.
4. **Structural invariant test over duplicated per-reader assertions (FR-010).** One table-driven test enumerating every reader and asserting parity with `read_mission_type` — makes AC-1/AC-3 a gate, not 12 hand-copies.

---

## Decisions Resolved (was OPEN QUESTIONS)

- **(a) Take the mission — YES.** Landed pre-rc2, scoped strictly to reader convergence + legacy retirement + the two folds (M3 owns the resolution fix).
- **(b) Legacy `{"mission": …}` resolution — DROPPED ENTIRELY.** No fallback anywhere; every reader resolves `mission_type` only. Deliberate behavior change; de-risked by the FR-007 `mission_type` backfill migration and gated by AC-2/AC-5. **Compounding note:** with M3's #3598 typo hard-fail, an unmigrated legacy mission moves silently-resolving → typeless (M5) → hard-fail (M5+M3); the backfill must precede both reaching real projects.
- **(c) Fold #2901 and #2477–#2480 — YES, both folded** (FR-008/FR-009). #2480's import constraint is dissolved by decision #1's shared helper; #2477–#2479 carry replay-equivalence checks or encoded allow-list exemptions; #2901 lands as one tolerant WP-frontmatter reader.

---

## Risks

- **Legacy-retirement blast radius (highest).** Every legacy `{"mission": …}`-only mission stops resolving. *Mitigation:* FR-007 backfill migration lands before behavior changes reach projects; AC-2/AC-5 pin before/after; sequencing decision #3 puts the migration first.
- **Migration coverage gap.** `migrate backfill-identity` mints `mission_id` only — it does **not** backfill `mission_type`; the sole existing writer is an internal migration step (`mission_state.py:1617`). *Mitigation:* FR-007/AC-5 require confirming coverage and standing up a dedicated `mission_type` backfill if absent (likely needed).
- **Compounding with M3.** M5 (typeless) + M3 (#3598 hard-fail) turns an unmigrated legacy mission into a hard-fail. *Mitigation:* order the backfill ahead of both; document the interaction in the shared ADR line so neither mission ships the compound break unguarded.
- **User-visible surfaces (dashboard / retrospective / interview).** A mission previously shown/recorded as `software-dev` now shows its true type or typeless. *Mitigation:* per-surface regression tests (AC-1 dashboard pin); FR-... change-log line per changed surface.
- **Frozen-migration replay drift (#2477–#2480).** Routing byte-exact legacy replays onto a newer reader can change which malformed shapes are tolerated. *Mitigation:* AC-6 equivalence check, else encoded allow-list exemption — never a silent path-exclude.
- **#2901 scope.** The WP-frontmatter fold is a distinct N-reader domain; risk of scope creep. *Mitigation:* bounded to one tolerant reader + routing the enumerated sites; no new recovery policy invented.
- **Caller assumptions on the removed default.** Callers expecting a concrete `software-dev` string must tolerate neutral typeless. *Mitigation:* per-reader step inspects each caller's boundary (the `get_mission_type` precedent).

---

## Issues

- **#3598** — the deliberately-separated "second inconsistency" (M5 is its second half; per-type resolution is M3). Parent epic **#3410** (charter/doctrine silent-drop — fail loud, never fake-green).
- **#2901** — WP-frontmatter failure-classification N-reader — **FOLDED** (FR-008).
- **#2477 / #2478 / #2479 / #2480** — inline `meta.json` reads (frozen migrations + charter layer) — **FOLDED** (FR-009); #2480's import blocker dissolved by the shared helper.
- **Epic #2400** — Metadata & profile authority: single canonical source across WP frontmatter, event log, invocation-time profile loading (the umbrella theme).
- **#3407** — hardcoded `software-dev` guard (twin of the silent-default class; adjacent, not folded).

---

## Appendix — Reader census (verified against `main`, 2026-08-20)

| # | Reader (file:line) | Current behavior | Action under M5 |
|---|--------------------|------------------|-----------------|
| 1 | `charter/mission_type_profiles.py:748/762` `_read_meta_mission_type` | reads only `mission_type` | Route through shared helper (already canonical-only; now shared) |
| 2 | `dashboard/handlers/features.py:68` | reads **only** legacy `mission`, default `software-dev` | Route through helper — drops legacy + default (visible change) |
| 3 | `mission_metadata.py:255` (`MissionIdentity`) | `mission_type or mission or "" → "software-dev"` | Route through helper — drops legacy + default |
| 4 | `retrospective/generator.py:1319` | `mission_type or "software-dev"` | Route through helper — drops default |
| 5 | `charter/interview.py:225` | legacy `mission` only, default `software-dev` | Route through helper — **confirm feature-meta vs interview payload** before converging |
| 6 | `context/resolver.py:94` | `mission_type or mission or None` | Route through helper — drops legacy |
| 7 | `cli/commands/agent/mission_create.py:374` | `mission_type or mission` (write path) | Route through helper — drops legacy |
| 8 | `verify_enhanced.py:28/31` | reads both fields separately | Route through helper — drops legacy read |
| 9 | `dashboard/diagnostics.py:31/34` | reads both fields separately | Route through helper — drops legacy read |
| 10 | `retrospective/reader.py:312` & `writer.py:408` | `mission_type` only, default `""` | Route through helper (already canonical-only) |
| 11 | `upgrade/feature_meta.py:95` | `mission_type` only | Route through helper |
| 12 | `cli/commands/_mission_type_audit.py:243/249` | reads both (the audit classifier) | Keep field-aware **iff** it is the census/audit tool; else converge (evaluate) |
| M | `migration/mission_state.py:1617`; `m_0_13_0` :57/114; `m_0_13_5`; `m_0_13_8` | frozen migration reads/writes, `software-dev` default / legacy `mission` | **#2477–#2480 fold:** route onto helper/`load_meta*` w/ replay-equivalence, or encoded allow-list exemption |
| B | `mission_type` backfill (NEW) | none today — `backfill-identity` mints `mission_id` only | **FR-007:** verify coverage; add dedicated `mission_type` backfill |
| C | `mission.py:542` `_canonical_meta_mission_type` | canonical, reads `mission_type` + legacy `mission` | **Delegate to shared helper; drop legacy `mission` read** |
| W | #2901 sites: `dossier/indexer.py`, `sync/history_import/scan.py`, `audit/classifiers/wp_files.py`, `status/bootstrap.py`, `mission_v1/guards.py`, `review/prompt_metadata.py` | divergent WP-frontmatter catch/recovery | **FR-008 fold:** one tolerant reader in `status/wp_metadata.py` |

## Cross-mission coordination (rc3 integration check)

- **M3↔M5 reader reconciliation (load-bearing).** M3's delivery path relies on `resolve_mission_type_key`; ensure it routes through M5's `read_mission_type()` so the two readers do not re-diverge (the defect M5 kills). Coordinate at plan time.
- **Same-file coordination.** M5 (#2901 fold) and **M6** both edit `audit/classifiers/wp_files.py`; M5 and **M8** both edit `retrospective/generator.py` (different symbols/lines each). Assign per-symbol ownership at plan time.
- **Program gate.** M5's legacy-resolution drop requires **M0 (`mission_type` backfill)** to have run first — see the rc3 approach doc.
