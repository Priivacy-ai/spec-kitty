# Spec: Drift-Proof Architectural Ratchet Allow-lists

**Mission**: content-address-ratchet-allowlists-01KX8M4D
**Type**: software-dev
**Parent epic**: #2071 (test-QA friction — audit-fed)
**Scope tickets**: #2546, #2547, #2548; folds #2072; coordinates #2077
**Surfaced by**: the CaaCS change-coupling analysis (`docs/analysis/test-change-coupling-caacs.md`) during the coord-authority trio degod (PR #2545), which paid the re-anchor tax three times.
**Hardened by**: a post-spec adversarial squad (scope/sizing, claim-verification, completeness) — see the correction notes inline.

## Overview & Context

Several `tests/architectural/` "ratchet" gates protect real invariants (no dead
public symbols, no write-side identity re-derivation, no unallowlisted I/O in a
pure core, no raw kitty-specs path joins) by carrying a small **allow-list** of
sanctioned exceptions. Those allow-lists are anchored on **file positions** —
raw line numbers and `module::Name` / `path::qualname` strings — so a
*behaviour-preserving* refactor that merely **moves code** (inserts a line,
relocates a symbol, rebases across a lane) makes the anchor stale and reds the
gate. The maintainer must then hand-edit a line number or module path with no
behaviour change whatsoever.

This is the single biggest test-maintenance tax the CaaCS analysis found: the
whole-codebase dead-code scanners changed 54 + 36 times (≈90 pure-churn edits),
and the line-pinned allow-lists re-anchor on every cross-lane landing (their
in-file comments are manual changelogs of `343→347`, `518→472→…→499` bumps).

The repo already ships the fix substrate — `contracts/anchoring.composite_key`
(a content-addressed `(qualname, token_line)` key) and the DIR-041
`is_file_line_anchor` ban on `file:NNN` positional anchors in Contract Records —
and even a fully-migrated exemplar (`test_no_worktree_name_guess`, keyed on
`(qualname, token)` derived from a live scan). This mission **generalizes that
doctrine to every ratchet allow-list**: re-key them onto stable content
descriptors so only a *genuine semantic change* can trip them, while preserving
every gate's full bite.

**Two distinct position smells (do not conflate):**
- **Line-drift** — a `(rel_path, line)` seed whose key is derived by dereferencing
  a hardcoded line. Fixed by the content descriptor (WS1). `composite_key` itself
  is *relocation-tolerant* (its `(qualname, token_line)` key is not
  module-qualified); the line seed is the only fragility for these gates.
- **Relocation** — the dead-symbol gate keys on `module::Name` (it does **not**
  use `composite_key`), so moving a symbol to another module breaks it. This
  needs a *net-new* relocation-proof key (WS2), not `composite_key`.

## User Scenarios & Testing

**Primary actor**: a maintainer (or implementing agent) performing a
behaviour-preserving refactor (a degod, a decomposition, a cross-lane rebase).

**Primary scenario (happy path).** The maintainer inserts helpers above a guarded
site, or relocates a public symbol during a decomposition. No *behaviour* changes.
CI runs the architectural ratchet gates → **all stay green**, with **zero manual
allow-list edits**.

**Critical exception (bite preserved).** The maintainer introduces a *genuine*
offender — a new un-allowlisted banned I/O call, a public symbol in `__all__` that
no `src/` code calls, a resurrected write-side re-derivation, **or a new offender
in the same function as a sanctioned exception**. CI → the relevant gate **reds**,
naming the offender. Content-addressing must never soften this.

**Edge / motion battery.** Blank/comment insertion; multi-line insertion; a symbol
moved file-to-file (WS2); a cross-lane rebase shifting every line — each MUST leave
the gates green.

**Rules that must always hold.**
- A gate only reds on a genuine semantic change (added/removed/edited banned call;
  new dead export; resurrected re-derivation; enclosing rename), never on pure
  position change.
- **Shrink-only teeth survive**: when a sanctioned exception is genuinely
  routed/removed, its allow-list entry must go stale so it is deleted — even if a
  *different* finding still exists in the same function (this is why staleness must
  be an *exactly-one, key-equal* match, never "≥1").
- No allow-list may reintroduce an **integer-line anchor** in an **authoritative
  comparand** — enforced by the standing meta-guard (FR-004), not by convention.
  (`module::Name` / `path::qualname` keys are NAME anchors, **not** line anchors:
  the meta-guard does NOT ban them — that would be circular with WS2 and
  unsatisfiable against FR-014's permanent census-list deferral. Their
  relocation-proofing is delivered by WS2's *re-keying* (FR-007), not by the ban.)

## Functional Requirements

### WS1 — Line-drift ratchet unification (folds #2547 + #2072 + the wp05 anchor)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Ratchet allow-lists MUST anchor each entry on a **content descriptor** — `(rel_path, enclosing_qualname, token_substring, rationale)` plus a disambiguator (an **occurrence ordinal** within the qualname, OR an assert-at-import that `token_substring` is **unique within its qualname**). `token_substring` MUST be matched against the **normalized, space-joined token line** (e.g. `parent . parent`, `get_current_branch (`), never raw source — matching raw source silently matches nothing (vacuous green). Never a `(rel_path, line_number)` seed. | Draft |
| FR-002 | The allow-list key MUST be populated by **scanning for the descriptor's live finding** and capturing that finding's live composite key. The descriptor MUST resolve to **exactly one** live finding; resolving to **0 or >1 is a hard failure (RED)**, never a silent pick. | Draft |
| FR-003 | Staleness twin-guards MUST assert "the descriptor resolves to **exactly one** live finding **whose composite key equals** the seeded key" — **never** "≥1 live finding". (Squad claim-lens: "≥1" lets a routed-away allowance stay green while masking a *new* sibling offender in the same qualname — a bite + shrink-only breach. This preserves the line-exact precision of the `seed_line ∈ live` guards it replaces.) | Draft |
| FR-004 | A **standing meta-guard** MUST scan **all of `tests/architectural/`** and reject an integer that reaches a **line-locator sink** in an authoritative comparand. Predicate (post-plan squad, mechanically decidable — no fragile heuristic): **Python** = an AST *int-to-line-sink* detector — an int literal reaching the **2nd positional arg of `composite_key(source, N)` / `composite_key_from_file(path, N)`** or a subscript/`.get()` into `code_tokens_by_line(...)`; **YAML** = a field-name rule — ints permitted **only** in `line` (documented non-authoritative locator), `count`, and `*_baseline` (count-floors); comparand keys (`token`/`qualname`/`file`) are non-int by construction. **Explicitly OUT of the ban** (enumerate-only, FR-014): `module::Name` / `path::qualname` name-anchors and `occurrence` ordinals (a scan index, never a lineno). Keep the contract's explicit-marker escape hatch for any genuinely new diagnostic int. Generalizes DIR-041; delivers #2077's recurrence guard. Lands **after** the WS1 migrations (red-first; green once no un-migrated line seed remains). | Draft |
| FR-005 | Migrate the line-seeded allow-lists to the FR-001 descriptor form: (a) `test_no_write_side_rederivation._ALLOW_LIST_SEED` + `_CHECKOUT_GRAMMAR_ALLOW_LIST_SEED` **and** their three line-number twin-guards; (b) **`test_single_mission_surface_resolver._RAW_JOIN_SITES`** (squad-completeness: same seed shape, ~8 re-anchors — the highest-tax gate, #3 on the CaaCS list; its omission would leave a file:line ratchet while "closing" #2072); (c) **conditional on PR #2545 merging** — `test_trio_seam_only._IO_ALLOWLIST_SITES` (already imports `composite_key`; if #2545 is still open at implement time, drop this clause to a tracked follow-up rather than block the mission — C-002). | Draft |
| FR-006 | Convert `test_wp05_write_target_drain`'s positional anchors to a pure content match — **both** the `_ALLOW_LISTED_LINE = 347` scalar constant **and** the `composite_key(source, 347)` call-argument — **preserving its two behavioural reachability probes**. | Draft |
| FR-007b | **Campsite**: on each migrated file, delete the stale re-anchor changelog comment fossils that documented the removed tax (`_RAW_JOIN_SITES` 8-entry NOTE block, the `343→347` note in wp05, the `_CHECKOUT_GRAMMAR` bump notes). | Draft |

### WS2 — Dead-code scanner relocation-hardening (#2546) — *gated last, tripwire per C-004*

| ID | Requirement | Status |
|----|-------------|--------|
| FR-007 | The symbol dead-code allow-list MUST key on a **relocation-tolerant symbol identity** that **forbids a bare-name-alone key**. (Squad claim-lens: bare-name-alone rescues same-named symbols across modules — `ArtifactKind`×3, `GateDecision`×2, `ResolutionResult`/`ResolutionTier`×2 exist today — re-blinding the T004 no-false-negative invariant the `known_modules` guard exists to prevent.) Keep a module/body disambiguator as a tiebreak; gate the change behind the existing T004 no-false-negative self-tests, using those same-name fixtures as concrete regression cases. | Draft |
| FR-008 | The mechanically-identifiable exempt categories MUST be **auto-derived at gate time**, not hand-listed: registry-discovered migrations (the **registered class symbol only** — decorator-parsed `@MigrationRegistry.register`, ~96 `m_*.py` files — **not** a blanket exemption of every symbol in a migration module; a dead helper/constant there must still be caught), docstring/`__all__`-only re-export decomposition shims, and Typer sub-app registrations. Retires Category-1/2/5 + the merge/tasks re-export blocks + the dead-code portion of the `_baselines.yaml` count-reconciliation churn. Coordinate with #2293's category_b burn-down so they do not fight. | Draft |
| FR-009 | The dead-code gates MUST preserve their non-negotiable invariants unchanged: cross-module `__all__` deadness detection; the four dynamic-dispatch detectors (module-attr, `__getattr__` facade, `getattr`-string, star-import); test-code-is-not-a-caller semantics; and the bidirectional stale-entry ratchet. | Draft |

### WS3 — Ratio=1.00 audit residue (#2548, minus the wp05 item now in WS1)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-010 | Harden `test_template_governance_payload_contract` to **derive the promised-surface set** (section names + exact CLI-command-form strings) from the contract/schema, not inlined literals that drift on wording changes. | Draft |
| FR-011 | Convert the two positive-literal `__module__ == "doctrine.missions.models"` sub-tests in `test_layer_rules` to **behavioural** assertions (importable + the resolver/facade actually uses it). | Draft |
| FR-012 | **Doc-only**: record the ratio=1.00 audit verdict — the **ten** behavioural/negative/import-layer invariants classified KEEP (plus `conftest` infra) are validated with **no change** — closing the #2548 audit obligation. | Draft |

### Cross-cutting

| ID | Requirement | Status |
|----|-------------|--------|
| FR-013 | Each migrated gate MUST carry a **plant-and-catch non-vacuity self-test** proving it still bites after the change (a planted genuine offender reds it) — including a planted **same-qualname sibling offender** proving FR-003's exactly-one staleness still deletes a routed allowance. | Draft |
| FR-014 | Make an explicit **migrate-or-defer ruling** on the two `path::qualname` census allow-lists (`test_org_activation_seam._BUILTIN_ONLY_ALLOWLIST`, `test_coord_read_residuals_closeout._IDENTITY_CALLSHAPE_KNOWN_RESIDUALS`). Default ruling: **DEFER migration** (they are low-churn census allow-lists, not the high-tax line-seed class) but the FR-004 audit MUST **enumerate** them, and a follow-up is filed. | Draft |
| FR-015 | Provide `issue-matrix.md` rows for #2546, #2547, #2548, #2072 (fold rationale), #2077 (coordination — FR-004 delivers its recurrence guard), and #2293 (adjacent — do not fold; verify FR-008 does not fight its burn-down). | Draft |

## Non-Functional Requirements

| ID | Requirement | Measure / Threshold | Status |
|----|-------------|---------------------|--------|
| NFR-001 | Pure code motion MUST NOT red any migrated gate. | A motion battery (≥1 blank-line insert, ≥1 multi-line insert, ≥1 symbol relocation for WS2, and a simulated cross-lane line shift) yields **0 false reds** across the migrated gates. | Draft |
| NFR-002 | Every migrated gate retains its bite. | **100%** of planted genuine offenders (new banned call, resurrected symbol, removed caller, boundary violation, **same-qualname sibling offender**) are caught (red). | Draft |
| NFR-003 | No **authoritative** ratchet comparand may carry a positional anchor after the mission. | The FR-004 standing meta-guard reports **0** integer-line components in authoritative seeds/keys across `tests/architectural/` (documented non-authoritative `line:` locators and count-floor baselines exempt). | Draft |
| NFR-004 | No architectural-suite regression. | Full `tests/architectural/` stays at its baseline (**869 passed / 0 failed**, 4 skipped) on the mission branch. | Draft |
| NFR-005 | Every migrated descriptor resolves uniquely. | Each descriptor resolves to **exactly one** live finding; a resolution of 0 or >1 fails the owning gate RED (verified by a self-test). | Draft |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | DIR-041 (no `file:line` positional anchors) is the **governing doctrine**; this mission generalizes it to ratchet allow-lists and MUST NOT weaken it. | Active |
| C-002 | **PR #2545 MERGED (2026-07-11).** The `test_trio_seam_only.py` migration is now **in-scope**: after the mission branch rebases onto a `main` containing #2545 (the file is absent pre-rebase), IC-WS1-TRIO becomes a normal WS1 migration (its 5 `_IO_ALLOWLIST_SITES` entries all resolve UNIQUE per the descriptor table). Re-resolve at implement time as *rebase-then-fold*, not a follow-up drop. Post-rebase, `test_trio_seam_only.py` also needs a `tests/_arch_shard_map.py` entry (it lands fresh with 0). | Active |
| C-003 | Acceptable **residual re-anchor limits** are documented, not fought: an enclosing-function/class **rename** or a **same-line token edit** legitimately changes the content key — these are genuine semantic changes, not pure motion. | Active |
| C-004 | **Committed sizing decision (squad-scope lens):** KEEP as ONE mission; sequence **WS2 last** behind a design-spike **tripwire** — if the relocation-proof symbol-identity key needs **>2 implementation WPs**, or a body-hash proves unstable under formatting/whitespace, **carve WS2 out to a standalone #2546 mission** and ship WS1+WS3 immediately. WS2's merge MUST NOT gate WS1/WS3 (they pay the re-anchor tax PR #2545 hit 3× and must not be held hostage). | Active |
| C-005 | **REPLACE-with-vulture is out of scope / disqualified** (vulture treats `__all__` membership as used → cannot detect the primary cross-module-deadness signal; drowns in the ~96 registry/shim false positives). HARDEN only. Note: `composite_key` is relocation-*tolerant*; WS2's relocation problem is specifically the dead-symbol gate's `module::Name` key, which needs a net-new key. | Active |
| C-006 | **No-overlap (post-plan squad):** (a) `_baselines.yaml` + `test_ratchet_baselines.py` MUST be owned by a **WS1-side / early WP — NOT the carvable WS2 WP** (a WS1 count bump would otherwise orphan when WS2 carves to #2546); WS2 routes its category/module count deltas *into* that owner while in-mission. (b) `test_no_dead_symbols.py` MUST be **single-owned end-to-end** (fold WS2-KEY + WS2-CATEGORIES into one owner — no two concurrent lane-owners on one file). (c) WS2's new relocation-proof key lives in a **new module**; `contracts/anchoring.py` is owned solely by the FR-004 meta-guard WP. (d) The new `test_ratchet_positional_anchor_ban.py` WP MUST also own `tests/_arch_shard_map.py` and enroll the new file in the **same WP** (else `test_arch_shard_marker_completeness` reds). | Active |

## Success Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| SC-001 | A maintainer can insert lines or relocate a symbol in a guarded module and the architectural ratchet gates stay green with **zero manual allow-list edits**. | Draft |
| SC-002 | A genuine new offender — including a **same-qualname sibling** of a sanctioned exception — still fails the gate **100%** of the time. | Draft |
| SC-003 | **Zero** authoritative ratchet comparands reference a line number, across all of `tests/architectural/` (enforced by the FR-004 standing meta-guard; non-authoritative `line:` locators and count floors exempt). | Draft |
| SC-004 | Re-running a coord-authority-trio-shaped refactor requires **no** allow-list line/position edits (the 3× re-anchor tax is not repeatable). | Draft |

## Key Entities

- **Ratchet allow-list** — the small set of sanctioned exceptions a gate carries.
- **Content descriptor** — `(rel_path, qualname, token_substring, occurrence-disambiguator, rationale)`; the position-free seed. Matched against the *normalized* token line; MUST resolve to exactly one live finding.
- **Composite key** — `(qualname, token_line)` from `contracts/anchoring.composite_key`; drift-proof against line motion **and relocation-tolerant** (not module-qualified), but re-anchors on enclosing rename.
- **Relocation-proof symbol identity** (WS2) — a net-new key for the dead-symbol allow-list; NOT bare-name-alone (T004 no-false-negative); distinct from `composite_key`.
- **Authoritative comparand vs diagnostic locator** — an anchor used for set-membership/comparison/count (must be position-free) vs a documented `line:` navigation hint (may carry a line; never compared).
- **Staleness twin-guard** — forces deletion of an allow-list entry once its sanctioned exception is gone; must be *exactly-one, key-equal* (never "≥1").
- **Standing meta-guard** (FR-004) — the all-suite gate banning positional anchors in authoritative comparands.

## Assumptions

- The gates' current *bite* is correct and must be preserved; this mission changes only the *anchoring mechanism*, never which offenders are caught.
- `contracts/anchoring` is the canonical substrate and is reused, not reinvented; `test_no_worktree_name_guess` is the migrated exemplar to follow.
- PR #2545 is coordinated with WS1's trio clause (C-002).

## Out of Scope

- Replacing the dead-code scanners with an off-the-shelf tool (vulture/ruff) — disqualified (C-005).
- Migrating the two `path::qualname` census allow-lists (FR-014 defers them; enumerate + follow-up only).
- The count-floor census ratchets (`test_resolution_authority_gates` / `test_coord_read_residuals_closeout` floors) — different (legitimate shrink-only) mechanism.
- Changing which invariants the gates enforce, or their CI wiring.
- The ten KEEP tests in the ratio=1.00 cluster (validated; no edits) beyond FR-012's recorded verdict.
- Version-number assignment (the operator superimposes versions at release).
