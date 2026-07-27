# Research: Relocation-Hardened Dead-Code Scanners

Design decisions, grounded in the WP06 spike + two post-spec adversarial squads +
the live census. **Counts are re-derived on `analysis/test-change-coupling`** (not
inherited from the drifted "342/278/60" figures).

## D-1 — Key shape: content-only default, module_path tier by live cardinality

**Decision**: `SymbolKey` = `(bare_name, body_hash)` content-only by default; escalate
to `(bare_name, module_path, body_hash)` ONLY for `bare_name`s whose content resolves
to ≥2 live locations.
**Rationale**: content-only is relocation-tolerant (a pure move keeps the key). The
squad proved no single tier is correct: pure content re-blinds the ArtifactKind trio;
module_path forfeits relocation. Two-tier keyed on collision is the minimal correct design.
**Alternatives**: bare-name-alone (re-blinds T004 — rejected by the spike); vulture
(treats `__all__` as used — disqualified); module_path-always (forfeits relocation for all).

## D-2 — Collision detection is LIVE, not frozen (bite adversary Defect 1)

**Decision**: the `(bare_name → [live locations])` index is rebuilt **every gate run**;
tier assignment is recomputed, not baked into the allow-list. A content-tier key that
resolves to ≥2 live locations is dynamically escalated or fail-closed.
**Rationale**: a frozen authoring-time split is a strict reduction of the old
`module::Name` key's unconditional T004 preservation — a future byte-identical
same-name pair (e.g. collapsing the two live `GateDecision`s to one shape) would
silently re-blind. Live recomputation keeps T004 robust against corpus evolution.
**Alternatives**: one-time authoring scan (rejected — safety expires on corpus growth).
**Perf**: build the index once per run (single `src/` AST walk), not per-entry.

## D-3 — Fail-closed on both undecidable forms (bite adversary Defect 2)

**Decision**: fail-close (reject/flag, never silent-exempt) for BOTH (a) `None`-key
(a shape the resolver cannot span) and (b) a content key resolving to ≥2 live locations.
**Rationale**: the ≥2 case was unruled; it is the mechanical multi-location re-blind.
Fail-closed converts a silent false-negative into a loud false-red — the safe direction.
**Alternatives**: silent skip (forbidden — [[no_legacy_resolver_paths]]).

## D-4 — Tier-specific dangling ratchet + one-signal body-sensitivity (bite adversary Defect 3)

**Decision**: the third ratchet direction is tier-specific: module_path-tier entry →
`(bare_name, module_path)` with no live `__all__` decl → prune; content-tier entry →
`(bare_name, body_hash)` resolving to zero live locations → prune. A dead-symbol body
edit yields **exactly one** signal (offender-refresh), never offender+prune double-flag.
**Rationale**: a `(bare_name, module_path)` dangling check is undefined for the
location-free content tier — the mission's headline subset. Body-sensitivity (a body
edit changes the content key) must reconcile with the dangling check to one deterministic signal.
**Alternatives**: single dangling shape (incoherent for the content tier).

## D-5 — Body-hash substrate: reuse `anchoring.code_tokens_by_line`

**Decision**: hash normalized token lines via `anchoring.code_tokens_by_line`
(interpreter-independent, 3.11↔3.12 parity already guarded).
**Rationale**: the spike proved this stable under the motion battery + 3.11↔3.12 for
`ClassDef`/`FunctionDef`. Do NOT fork a second normalizer (S3776 / canonical-source).
**Caveat (bite adversary Defect 4)**: the spike's `definition_span` has **no AnnAssign
branch** and hashes the **whole `ImportFrom` statement**. FR-002 (AnnAssign) and FR-004
(single-alias) MUST add their own stability proofs — they do NOT inherit the spike's guarantee.

## D-6 — AnnAssign + facade-dict + single-alias: close the three keyability gaps

**Decision**: (a) add an `ast.AnnAssign` branch to `definition_span` (14 typed constants
would otherwise be `None`-key → the re-introduced T001 bug); (b) a KEY-side facade
resolver reusing the gate's caller-side `_record_facade_edges`/`_resolve_relative_module`/
`_find_facade_lazy_dict_name` for all 8 lazy `__getattr__`/`_EXPORT_MODULES` exports;
(c) scope the `ImportFrom` body-hash to the single aliased name, not the whole statement.
**Rationale**: without these, exactly the entries the mission must key resolve to `None`
and fail-close → false-reds on sanctioned dead symbols.
**Verification**: DoD (k) — all 394 entries resolve to a `SymbolKey`; DoD (j) — AnnAssign
+ single-alias stability under motion + 3.11↔3.12.

## D-7 — Symbol-granular auto-exempt categories (FR-010)

**Decision**: auto-derive exemptions symbol-granular: registered `@MigrationRegistry.register`
class ONLY (not the whole `m_*.py` module — a dead helper/constant in a migration file
is still caught); re-export shims by definition-shape; Typer sub-apps by call/decorator.
Disjointness meta-test: `auto_exempt ∩ hand_allowlist = ∅`.
**Rationale**: module-granular exemption would blind ~96 migration files' dead helpers.
**Alternatives**: module-level allow (rejected — hides real dead code).

## D-8 — Warning remediation: preserve the signal, change the channel; split cross-package

**Decision**: the ~40 warnings are almost all intentional `warnings.warn(UserWarning)`
report-only diagnostics. Remediate by routing the diagnostic off the `warnings` channel
(pytest `record_property` / captured log) OR registering an expected-warning with inline
rationale — **preserving the load-bearing signal** (migration patch-skip, duplicate-gate,
legacy-backfill). Census breakdown:
- **In-mission (arch, owned):** `test_migration_chain_integrity.py` (~13 patch-skips),
  `test_gate_coverage.py` (duplicate-selection), + any other arch emitter.
- **Tracked follow-up (cross-package):** `tests/contract/test_example_round_trip.py`
  (~13 legacy-contract-backfill) and `src/doctrine/base.py:108` + the invalid
  `terminology-guard.toolguide.yaml` (genuine src schema-skip) — named in `issue-matrix.md`,
  never silently suppressed.
**Rationale**: FR-016 forbids blanket `filterwarnings=ignore`; broad `src/`/contract
ownership would blow this test-infra mission's disjoint-ownership boundary.
**Alternatives**: blanket ignore (forbidden); fix everything in-mission (over-scopes ownership).
