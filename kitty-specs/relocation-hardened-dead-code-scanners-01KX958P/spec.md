# Feature Specification: Relocation-Hardened Dead-Code Scanners

**Mission**: relocation-hardened-dead-code-scanners-01KX958P
**Branch**: `analysis/test-change-coupling` (builds on the merged WS1 content-addressing; PRs to `main` later)
**Closes**: [#2546](https://github.com/Priivacy-ai/spec-kitty/issues/2546) (under epic [#2071](https://github.com/Priivacy-ai/spec-kitty/issues/2071)) — WS2 carved from `content-address-ratchet-allowlists-01KX8M4D`
**Coordinates with**: [#2293](https://github.com/Priivacy-ai/spec-kitty/issues/2293) (category_b burn-down — route deltas, do not fight)

---

## Overview

The architectural dead-code scanners (`tests/architectural/test_no_dead_symbols.py`
and `tests/architectural/test_no_dead_modules.py`) protect the codebase against
unreferenced public symbols and modules. `test_no_dead_symbols.py` carries a
**394-entry hand-curated allow-list** (live count on `analysis/test-change-coupling`;
19 category frozensets, 400 across categories minus 6 overlaps) keyed on
`module::Name` — a *positional* identity. Because the key embeds the symbol's **location**, a behaviour-preserving
**relocation** of a sanctioned dead symbol (moving it to a new module, or above/below
its siblings) forces a manual allow-list edit even though nothing about the symbol's
deadness changed. This is exactly the code-motion tax that the parent mission's WS1
work removed from the *ratchet* allow-lists (CaaCS #3–#5 offenders) — WS2 removes it
from the *dead-code* allow-list.

This mission re-keys that allow-list onto a **relocation-tolerant symbol identity**
so a pure relocation no longer reds the gate — **without re-blinding the T004
no-false-negative invariant** (two same-named symbols in different modules must stay
distinguishable) and **preserving the gate's full bite** (genuinely-dead symbols
still caught).

### CRITICAL — Honest, Downscoped Relocation Promise (load-bearing)

A hardening squad proved that **a correct single-tier relocation key does not exist**:

- A **pure-content** key `(bare_name, body_hash)` re-blinds T004 on the *ArtifactKind
  trio* — `ArtifactKind` is a byte-identical re-export across `doctrine.directives`,
  `doctrine.procedures`, and `doctrine.tactics`; pure content cannot tell a dead one
  from its live siblings.
- A **module_path-bearing** key forfeits relocation tolerance for every entry that
  carries it.

Therefore the relocation promise is **explicitly downscoped and must be stated as
such — not over-promised**. The 394 entries fall into two tiers, and — critically —
**which tier an entry lands in is recomputed at gate time by the live collision
classifier (FR-005), not frozen at authoring time**:

| Entry class | Key tier | Relocation |
|-------------|----------|------------|
| Simple single-definition whose `(bare_name, body_hash)` resolves to exactly one live location | content-only `(bare_name, body_hash)` | **relocation-proof** |
| Re-export / facade-dict / multi-target fan-out / any `bare_name` whose content resolves to ≥2 live locations | `(bare_name, module_path, body_hash)` (collision-safe) or fail-closed | **relocation-FORFEIT (documented, not a bug)** |

**Sizing (live census, not frozen sub-counts):** the exact simple/forfeit split is
produced by the FR-005 classifier, **not asserted up front** (quoting frozen
sub-counts is how the earlier "342 / 278 / 60" census drifted). What IS known: a
**forfeit floor of ~100+** — the named re-export/shim categories are **68**
(`MERGE_DECOMP_SHIM_REEXPORT_2057`=65 + `BACKCOMPAT_SHIM_REEXPORT`=3), plus the **8**
facade-dict exports and the **33** multi-target `ImportFrom` entries stay location-
anchored. The **214-entry `GRANDFATHERED_LEGACY`** bucket is the swing population: its
simple/re-export members are classified by the live resolver. The mission delivers
relocation tolerance for the **simple subset (the majority of the 394)** and keeps
the **≥~100 known re-export/facade/fan-out entries** collision-safe but location-
anchored, with the forfeit **documented in the key module and the spec** — never
silently promised away.

---

## User Scenarios & Testing

### Primary scenario — simple sanctioned dead symbol is relocated (happy path)

A maintainer, mid-refactor, moves a sanctioned dead symbol that is a plain
`ClassDef`/`FunctionDef`/`Assign`/`AnnAssign` (a content-tier entry) to a
new module, or reorders it among its siblings. The symbol's body is unchanged. On
the next run of `pytest tests/architectural/test_no_dead_symbols.py`, **the gate
stays green with zero allow-list edits** — the content key resolves the entry at its
new location.

### Downscoped-exception scenario — re-export/facade entry is relocated

A maintainer relocates a re-export shim, a facade-dict export, or a multi-target
`ImportFrom` entry (a module_path-tier entry). Because these are keyed with a `module_path`
tier (to stay collision-safe against same-name siblings), **the gate reds and a
manual edit is still required.** This is a **documented, deliberate limitation**, not
a regression — the key module names it explicitly and the failure message points the
maintainer at the module_path field to update.

### Bite-preserved scenarios (the gate must NOT go soft)

- **Genuinely dead symbol** — a public symbol with no live caller is still caught.
- **Same-name fan-out sibling (T004)** — marking one `ArtifactKind` dead while its
  sibling stays sanctioned → the dead one is **still caught** (no re-blinding).
- **Dead helper inside a migration file** — despite FR-008 auto-exempting the
  *registered* migration class, a dead helper/constant in an `m_*.py` file is **still
  caught** (symbol-granular exemption, not module-granular).
- **Dangling allow-list entry** — an entry whose old location was vacated (symbol
  relocated or deleted) and no longer resolves is **flagged for pruning** (new third
  ratchet direction), not silently carried.
- **Un-keyable symbol** — a symbol the key cannot resolve to a stable identity is
  **fail-closed** (rejected at load / flagged), never silently exempted.
- **Wired-away allow-listed symbol** — an allow-listed symbol that gains a live caller
  reds the existing shrink-only ratchet **body-independently** (the ratchet still
  fires regardless of the new content key).

### Body-sensitivity (new, deliberate, tested)

Because the simple-entry key hashes the symbol *body*, **editing a dead symbol's body
changes its key** and produces a false-red until the allow-list is refreshed. This is
a deliberate trade-off (the price of relocation tolerance), documented in the key
module and covered by a test asserting the behaviour is intentional.

---

## Domain Language

- **Relocation** — moving a symbol to a new module or reordering it among siblings
  **without changing its body**. The identity that WS2 must preserve across relocation.
- **Bite** — the gate's ability to catch a genuinely-dead symbol. Relocation tolerance
  must never trade away bite.
- **T004 no-false-negative** — the invariant that two same-named symbols in different
  modules stay distinguishable, so marking one dead never blinds the gate to the other.
- **Collision set** — the set of `bare_name` values that map to multiple byte-identical
  bodies across modules (proven to be exactly the ArtifactKind trio). Only these
  escalate to the `module_path` tier.
- **Facade-dict export** — a symbol exported via a lazy `__getattr__` / `_EXPORT_MODULES`
  dict rather than a direct `def`/`class`/assignment. Needs a KEY-side resolver.
- **Dangling entry** — an allow-list entry whose keyed symbol no longer resolves to a
  live `__all__` declaration at the recorded location. The third ratchet direction.

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Provide a relocation-tolerant symbol key in a **new** module `tests/architectural/_symbol_key.py`: content-only `(bare_name, body_hash)` **by default**; escalate to `(bare_name, module_path, body_hash)` **only** for `bare_name`s in a detected content-collision set. `body_hash` reuses `anchoring.code_tokens_by_line` (interpreter-independent, proven stable under the motion battery + 3.11↔3.12). | Planned |
| FR-002 | Support **`AnnAssign`** (typed module-level constants) in the key's `definition_span` — the annotated typed constants (**≤14**; several apparent constants are plain `Assign` already handled) that would otherwise be UN-KEYABLE and re-introduce the exact T001 bug WP01 fixed on the gate side. **HIGHEST-PRIORITY gap.** | Planned |
| FR-003 | Provide a **facade-dict KEY-side resolver** enumerated **by shape**: `sync/__init__.py _LAZY_IMPORTS` `{name:(module,attr)}` (2-tuple) AND `runtime/__init__.py _EXPORT_MODULES` `{name:module_const}` (1-value — the 6 `specify_cli.runtime::*` entries the gate's byte-frozen `_record_facade_edges` **skips**). **Re-derive the dict-parse KEY-side** (it must yield `name → (module, attr)` to locate the body); reuse ONLY the two **pure** helpers `_find_facade_lazy_dict_name` + `_resolve_relative_module`. Do **not** reuse/edit `_record_facade_edges` (byte-frozen C-005, caller-graph-shaped, discards the name). NOT "all 8" — src has 12 `__getattr__` modules but only 2 named-dict facades. | Planned |
| FR-004 | Scope the body hash to a **single alias** for the **33** multi-target `ImportFrom` entries — a whole-statement hash is sibling-contaminated (zero relocation tolerance). **Acceptance:** a DoD battery item proves one of the 33 stays keyable **and distinct from its statement-siblings after a sibling alias is edited** (single-alias scoping did not contaminate). | Planned |
| FR-005 | Implement the **escalation rule** as a **live, gate-time collision check**, NOT a frozen authoring-time split. On every invocation the gate resolves each content-tier `(bare_name, body_hash)` against the live corpus; a content key that resolves to **≥2 live `__all__` locations** is **dynamically escalated to the `module_path` tier or fail-closed** (FR-009). The corpus-wide scan proving today's collision set is exactly the ArtifactKind trio (`doctrine.directives`/`procedures`/`tactics`) is the *seed*, but the content/forfeit classification is **runtime-recomputed**, so a future byte-identical same-name pair cannot silently re-blind T004 (the old `module::Name` key preserved T004 unconditionally — the new key must not weaken that invariant). | Planned |
| FR-006 | Drop the **2 stale/renamed** entries (`charter_activate_app` / `charter_deactivate_app` no longer exist). | Planned |
| FR-007 | Re-key the **394-entry** `_SYMBOL_ALLOWLIST` in `test_no_dead_symbols.py` (across its 19 category frozensets) off `module::Name` onto the FR-001 key. `test_no_dead_symbols.py` is **single-owned** (re-key + FR-010 categories in one WP — no concurrent lane owners). | Planned |
| FR-008 | Add a **third "dangling-entry" ratchet direction**: the existing shrink-only ratchet fires only on "gained a caller"; relocation silently orphans an entry (its key resolves to nothing) **and** false-reds at the new location. The dangling check is **tier-specific**: for a **module_path-tier** entry, `(bare_name, module_path)` → no live `__all__` decl → red/prune; for a **content-tier** entry (location-free by construction), `(bare_name, body_hash)` → resolves to **zero** live `__all__` locations → red/prune. Reconcile with the body-sensitivity false-red (FR-009) so a dead-symbol **body edit** yields **exactly one** signal (offender-refresh), never an ambiguous offender+prune double-flag. | Planned |
| FR-009 | **Fail-closed** for undecidable keys — **never** silent-exempt — in BOTH forms: (a) an **un-keyable** symbol (`None`-key: a shape the resolver cannot span, e.g. an unhandled facade or definition kind) is rejected at load / flagged; (b) a content-tier `(bare_name, body_hash)` that resolves to **≥2 live `__all__` locations** is fail-closed (forcing dynamic escalation to the `module_path` tier per FR-005, or a loud catch) — this converts the multi-location silent-re-blind into a false-red. Also codify the new **body-sensitivity** (editing a dead symbol's body changes its key → false-red) as a deliberate, tested behaviour producing exactly one signal (FR-008). | Planned |
| FR-010 | Re-derive FR-008-parent auto-exempt categories **symbol-granular, not module-granular**: registered `@MigrationRegistry.register` class **only** (~96 `m_*.py` — a dead helper/constant in a migration file is still caught); re-export shims by definition-shape; Typer sub-apps by call/decorator parse. Include a **disjointness meta-test**: `auto_exempt ∩ hand_allowlist = ∅`. | Planned |
| FR-011 | Relocation-harden `test_no_dead_modules.py`, preserving cross-module `__all__` deadness, the 4 detectors, test-not-caller semantics, and the bidirectional ratchet. **Acceptance (measurable):** a DoD battery item relocates a sanctioned dead *module*'s allow-list anchor (rename its containing package path where the module is still dead) → the gate stays green with 0 edits **AND** a genuinely-dead module at the new path is still caught. If the module allow-list turns out to carry no relocatable anchor (pure path-set), FR-011 **downgrades to explicit-preserve** (byte-unchanged, covered by FR-012) and says so — no unmeasured scope-add. | Planned |
| FR-012 | **Preserve byte-unchanged**: the 4 dynamic-dispatch detectors (module-attr / `__getattr__`-facade / getattr-string / star-import), the `known_modules` guard (the anti-re-blind mechanism — do **not** touch `_record_*_edges` / `_imports_by_target`), the test-not-caller semantics, and the bidirectional stale-entry ratchet + its **4 T004 tests**. | Planned |
| FR-013 | Deliver the **(a–h) bite battery** (see Definition of Done), each driven through the **production `_compute_offenders` / stale path** (never the standalone key fn — a standalone-only test lets the gate self-validate green as a no-op). | Planned |
| FR-014 | Keep the merged meta-guard `test_ratchet_positional_anchor_ban.py` **green** — the new key is all-strings (no int-line anchor); assert it explicitly rather than assume it. | Planned |
| FR-015 | Ticket hygiene: `issue-matrix.md` row for #2546 (+ #2071 parent, #2293 adjacent); tracker comment naming the mission. Do **not** prescribe version numbers. | Planned |
| FR-016 | **Warning remediation** — census + categorize the ~40 warnings emitted by the arch/integration suite (`tests/architectural/`), then remediate each **at its root**: update deprecated API calls, fix mis-scoped pytest marks/fixtures, correct resource/`datetime`/collection-time deprecations. **NOT** via a blanket `filterwarnings = ignore`. A narrowly-scoped, individually-justified `filterwarnings` entry is permitted **only** for a warning owned by a third-party dependency we cannot fix at source, each carrying an inline rationale. Warnings whose source is `src/` product code are remediated in-mission **only if** doing so stays within a declared owned surface; any that would require broad cross-package `src/` ownership are split to a tracked follow-up (named in `issue-matrix.md`), never silently suppressed. | Planned |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | **Relocation tolerance (downscoped)** — relocating any **content-tier** entry (the simple subset the FR-005 classifier assigns to the content tier) produces **0 false-reds** under the motion battery: module move + sibling reorder + blank/comment insertion + **annotation-whitespace normalization for `AnnAssign` targets** (`X:int` vs `X : int`) + **single-alias-scoped `ImportFrom`** + the 3.11↔3.12 `code_tokens_by_line` dimension. The **≥~100 known re-export/facade/fan-out (module_path-tier)** entries are exempt from this promise by design. | 0 false-reds on the content-tier subset (incl. AnnAssign + single-alias shapes) | Planned |
| NFR-002 | **Bite preserved** — the (a),(c),(e),(g) offender fixtures (genuinely-dead / same-name-sibling / migration-helper / dangling) are caught **100%** of the time through the production path. | 100% caught | Planned |
| NFR-003 | **T004 no-false-negative preserved** — the 4 T004 detector tests + the `known_modules` guard machinery are **byte-unchanged** and green. | byte-diff = 0 on the named surfaces; 4/4 green | Planned |
| NFR-004 | **Suite stays green** — full `tests/architectural/` finishes with **0 failed** (current branch baseline = 887 passed). | 0 failed | Planned |
| NFR-005 | **No silent exemption** — **0** un-keyable (`None`-key) entries are silently exempted; every one is fail-closed (rejected/flagged). | 0 silent exemptions | Planned |
| NFR-006 | **Warning-clean arch suite** — the count of first-party warnings emitted by `tests/architectural/` drops from ~40 to **0**; any residual is a documented, individually-justified third-party `filterwarnings` entry (or a tracked `src/` follow-up), never a blanket ignore. | 0 first-party warnings | Planned |

---

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | **HONEST DOWNSCOPE** — the relocation promise applies to the **content-tier simple subset only** (classified live by FR-005, not a frozen count). The **≥~100 known** re-export/facade/fan-out entries are module_path-keyed or fail-closed (relocation-forfeit) and this limitation is **documented in the key module + spec**. Do **not** claim unconditional "relocate → green" for the whole allow-list, and do **not** quote a frozen simple/forfeit sub-count as if fixed. | Binding |
| C-002 | The relocation key lives in a **new** module `tests/architectural/_symbol_key.py` (test-infra, `_`-prefixed, **non-`src/`** — a `src/` module imported only by tests would red `test_no_dead_modules`). **Do NOT edit or delete** WP06's approved+merged spike files (`tests/architectural/_symbol_identity.py`, `tests/unit/test_symbol_identity_spike.py`); the new module owns its own file (may lift proven logic from the spike). | Binding |
| C-003 | `test_no_dead_symbols.py` is **single-owned** by one WP (re-key FR-007 + categories FR-010 together) — no two concurrent lane owners on that file. | Binding |
| C-004 | `_baselines.yaml` is **not owned** by a WS2 WP — route any count delta through a WS1-side/early owner (the parent mission's C-006 baseline-single-owner rule carries forward). | Binding |
| C-005 | `known_modules` / `_record_*_edges` / `_imports_by_target` (the anti-re-blind machinery) stay **byte-unchanged**. | Binding |
| C-006 | Coordinate with **#2293** (category_b burn-down) — route count deltas, do not fight its ratchet. | Binding |
| C-007 | The (a–h) bite battery MUST exercise the **production `_compute_offenders`/stale path**, not a standalone key function, so the gate cannot self-validate green as a no-op. | Binding |

---

## Success Criteria

- **SC-001** — Relocating a content-tier sanctioned dead symbol (module move or sibling
  reorder, body unchanged) leaves the gate **green with 0 allow-list edits**, for the
  content-tier subset the FR-005 classifier assigns. (Downscoped: the ≥~100 known
  re-export/facade/module_path-tier entries are exempt by design.)
- **SC-002** — Every offender fixture (genuinely-dead, same-name fan-out sibling,
  dead migration-file helper, dangling entry) is **caught through the production
  path** — 100%.
- **SC-003** — Two distinct claims: (i) **allow-list entries** — **0** allow-list
  entries are un-keyable (every one of the 394 resolves to a `SymbolKey`, proving the
  14 AnnAssign + 8 facade shapes are now handled); (ii) **arbitrary symbols** — any
  symbol the resolver *cannot* key (`None`-key) or that resolves to ≥2 live locations
  is **fail-closed** (never silent-exempt). Plus `auto_exempt ∩ hand_allowlist = ∅`.
- **SC-004** — Full `tests/architectural/` finishes **0 failed** (baseline 887), the
  merged meta-guard `test_ratchet_positional_anchor_ban.py` stays green, and the 4
  T004 detector tests + `known_modules` machinery are byte-unchanged.
- **SC-005** — The arch suite emits **0 first-party warnings** (from ~40). Any residual
  is a documented, individually-justified third-party `filterwarnings` entry or a
  tracked `src/` follow-up in `issue-matrix.md` — verifiable by re-running the census.

---

## Key Entities

- **SymbolKey** — the relocation-tolerant identity: `(bare_name, body_hash)` for
  simple entries; `(bare_name, module_path, body_hash)` for collision-set entries.
  Resolves to `None` for un-keyable symbols (→ fail-closed).
- **AllowlistEntry** — a hand-curated sanctioned dead symbol, re-keyed off `module::Name`
  onto a `SymbolKey`. Carries a rationale.
- **CollisionSet** — the `bare_name`s whose content resolves to ≥2 live locations,
  **recomputed at gate time** (FR-005), not frozen. Today's set = the ArtifactKind trio
  (+ any future byte-identical same-name pair); these escalate to `module_path` or
  fail-close, and are the only entries denied relocation tolerance.
- **DanglingEntry** — an allow-list entry whose `SymbolKey` no longer resolves to a live
  `__all__` declaration; the third ratchet direction flags it for pruning.
- **AutoExemptCategory** — symbol-granular auto-derived exemptions: registered migration
  class, re-export shim, Typer sub-app. Must be disjoint from the hand allow-list.

---

## Definition of Done — the (a–h) Bite Battery

Each item is driven through the **production `_compute_offenders` / stale path** (C-007):

- **(a)** A genuinely-dead symbol is still caught.
- **(b)** A relocated-but-WIRED simple symbol stays green. *(Document the
  dead-relocated false-red carve-out for the re-export/module_path subset.)*
- **(c)** A same-name fan-out dead sibling is still caught (T004, gate path).
- **(d)** A wired allow-listed symbol reds the stale ratchet (**body-independent**).
- **(e)** A dead helper in a migration file is still caught despite FR-010.
- **(f)** An undecidable-key symbol (`None`-key) is fail-closed.
- **(g)** A dangling entry reds the new third ratchet direction — **both tiers**: a
  module_path-tier orphan AND a content-tier `(bare_name, body_hash)` that resolves to
  zero live locations; and a dead-symbol body edit yields **exactly one** signal.
- **(h)** `known_modules` + the 4 T004 detector tests are **byte-unchanged and green**.
- **(i)** **Live-collision escalation (Defect-1 regression guard)** — introduce a NEW
  byte-identical same-name pair on a content-tier `bare_name` (the future
  `GateDecision`-collapse vector: two live symbols, one sanctioned) → the gate
  **dynamically escalates to module_path or fail-closes** so the unsanctioned sibling
  is **still caught** — driven through the production `_compute_offenders` path. This is
  the standing proof that the content/forfeit split is runtime-recomputed, not frozen.
- **(j)** **AnnAssign + single-alias stability** — relocate/normalize a top-level
  `AnnAssign` target (annotation-whitespace) and a single-alias-scoped `ImportFrom`
  entry → **0 false-red** through the gate, across the 3.11↔3.12 dimension.
- **(k)** **Full keyability** — all **394** allow-list entries resolve to a `SymbolKey`
  (the 14 AnnAssign constants + 8 facade-dict exports included) — 0 un-keyable entries.
- Plus: the merged meta-guard `test_ratchet_positional_anchor_ban.py` stays green
  (the new key is all-strings, no int-line anchor — asserted, not assumed).
- Plus: full `tests/architectural/` = **0 failed** (baseline 887).

---

## Assumptions

- The WP06 spike (`tests/architectural/_symbol_identity.py` + `tests/unit/test_symbol_identity_spike.py`)
  is the proven prototype + regression corpus. **Its stability proof covers `ClassDef` /
  `FunctionDef` targets ONLY** — its `definition_span` has no `AnnAssign` branch and its
  `ImportFrom` span hashes the whole statement. So **FR-002 (AnnAssign) and FR-004
  (single-alias `ImportFrom`) MUST add their own stability proofs** (DoD item (j)); they
  do not inherit the spike's guarantee. The new key module may lift the spike's proven
  `ClassDef`/`FunctionDef` logic + T004 no-false-negative fixtures but owns its own file.
- The **live census** (394 total; named re-export/shim = 68; 8 facade-dict; 33 multi-target
  `ImportFrom`; 14 AnnAssign; 2 stale — verified on `analysis/test-change-coupling`) is the
  research base. The **simple/forfeit sub-split is re-derived by the FR-005 live
  classifier**, not baked as a frozen count (the earlier "342 / 278 / 60" figures were a
  ~15–100% undercount and are corrected here).
- The merged WS1 content-addressing (`_ratchet_keys.py` descriptor resolver, the
  meta-guard) is present on `analysis/test-change-coupling` and stays green throughout.

## Out of Scope

- The WS1 ratchet allow-lists (already content-addressed by the parent mission).
- Any change to the `known_modules` / edge-recording machinery (C-005 preserves it).
- Version-number assignment (the PO superimposes versions at release).
- Unconditional relocation tolerance for the **≥~100 known** re-export/facade/fan-out
  (module_path-tier) entries (impossible without re-blinding T004 — explicitly out of
  scope per C-001).
