# Research — Drift-Proof Architectural Ratchet Allow-lists

Consolidated from the surface-investigation squad (3 briefs) and the post-spec
adversarial squad (3 lenses). Every decision is code-verified; no open
NEEDS CLARIFICATION.

## D-1 — Descriptor resolution: exactly-one, not "≥1"
**Decision**: a content descriptor MUST resolve to **exactly one** live finding;
0 or >1 is a hard RED. Staleness asserts "resolves to exactly one whose composite
key **equals** the seeded key".
**Rationale**: the adversarial lens proved "≥1 live finding" is strictly weaker
than the line-exact guards it replaces — if a sanctioned site is routed away but a
*new* offender appears in the same qualname, "≥1" stays green and **masks the new
offender**, breaching shrink-only (spec §rules) and NFR-002 bite. The codebase
already hit this class (WP07 hand-deduplicated two `feature_dir.parent.parent`
walks in `test_no_write_side_rederivation.py:133-144`).
**Alternatives**: "≥1 match" (REJECTED — bite hole); keep line seeds (REJECTED — the tax).

## D-2 — Disambiguator for same-qualname/same-token collisions
**Decision**: descriptor = `(rel_path, qualname, token_substring, occurrence, rationale)`.
Prefer a `token_substring` **unique within its qualname** (asserted at import);
where two genuinely-identical token lines coexist in one function, carry an
explicit **occurrence ordinal**. Substrings are matched against the **normalized**
space-joined token line (`parent . parent`, `get_current_branch (`), never raw source.
**Rationale**: composite_key collides for identical `(qualname, token_line)`
(anchoring.py by construction); the descriptor must therefore pin the specific
occurrence or the resolution is ambiguous (D-1 would RED). Matching raw source
silently matches nothing (vacuous green) — the f-string/token normalization in
anchoring.py:78-134 defines the only correct comparison space.
**Alternatives**: substring-only (REJECTED — ambiguous for duplicates); line seed (REJECTED).

## D-3 — Meta-guard scope: standing, all-suite, authoritative-vs-diagnostic
**Decision**: FR-004 is a **standing gate over all of `tests/architectural/`**
(Python seeds + the two YAMLs). It bans an integer line component in any
**authoritative comparand** (used for set-membership/comparison/count) and
**permits** a documented **non-authoritative `line:` locator** (the convention in
`resolution_gate_allowlist.yaml` / `inline_meta_read_allowlist.yaml`) and
**count-floor baselines**.
**Rationale**: a guard scoped to only the migrated files gives zero recurrence
protection (a new gate reintroduces the smell) — defeating the DIR-041
generalization; a naive all-tuple int scan false-positives on the two compliant
YAMLs and count floors. This is #2077's recurrence-prevention obligation.
**Alternatives**: named-files-only (REJECTED — no recurrence teeth); blanket int
scan (REJECTED — false-positives the compliant YAMLs).

## D-4 — WS2 relocation-proof symbol key: forbid bare-name-alone
**Decision**: the dead-symbol allow-list key uses a relocation-tolerant symbol
identity that **forbids bare-name-alone**, retaining a module/body disambiguator;
the change is gated behind the existing T004 no-false-negative self-tests, using
the real same-name fixtures (`ArtifactKind`×3, `GateDecision`×2, `ResolutionResult`/`ResolutionTier`×2).
**Rationale**: a bare-name key rescues *all* same-named symbols across modules, so
one genuinely-dead `ArtifactKind` is masked by a sanctioned sibling — the exact
T004 re-blinding the `known_modules` guard (test_no_dead_symbols.py:1247-1252)
exists to prevent. `composite_key` does NOT solve this (it is relocation-*tolerant*
but the dead-symbol gate keys on `module::Name`, not composite_key) — so this is
net-new design, and the tripwire (C-004) exists precisely because it is.
**Alternatives**: bare-name (REJECTED — T004 regression); body-hash-only
(REJECTED — collides for `X = str` aliases / identical enum bodies); keep
`module::Name` (REJECTED — the relocation tax).

## D-5 — FR-008 exemption scope: the registered symbol, not the module
**Decision**: auto-exempt only the **registered class symbol**
(decorator-parsed `@MigrationRegistry.register`, ~96 `m_*.py`); a dead
helper/constant in a migration module is still caught. Same for docstring/`__all__`-only
re-export shims and Typer sub-apps (exempt the registered/re-exported symbol, not
the whole module).
**Rationale**: today only ~5 migration symbols are allow-listed; a blanket
module exemption would blind genuine dead code in migration files.
**Alternatives**: blanket `m_*.py` exemption (REJECTED — over-broad).

## D-6 — Replacement disqualified; HARDEN only
**Decision**: do NOT replace the dead-code scanners with vulture/ruff.
**Rationale**: vulture treats `__all__` membership as *used* → cannot detect the
gate's primary signal (cross-module `__all__` deadness); it drowns in the ~96
registry/shim false positives; it is not a current dependency. ruff F401/F811 is
intra-module only (already enabled, orthogonal).
**Alternatives**: vulture-replace (REJECTED, C-005).

## D-7 — Completeness: the target list adds `_RAW_JOIN_SITES`
**Decision**: WS1 migrates `test_single_mission_surface_resolver._RAW_JOIN_SITES`
in addition to the write-side/wp05/trio seeds.
**Rationale**: it is the *same* `(rel,int,rationale)` seed shape with ~8
re-anchors (the highest tax, #3 on the CaaCS list the spec cites); omitting it
would "close" #2072 while a file:line ratchet remained. The two `path::qualname`
census allow-lists (`_BUILTIN_ONLY_ALLOWLIST`, `_IDENTITY_CALLSHAPE_KNOWN_RESIDUALS`)
are **deferred** (low-churn census, not the high-tax class) but **enumerated** by
the meta-guard (FR-014).

## D-8 — Sequencing + WS2 tripwire
**Decision**: WS3 first (zero deps) · IC-DESCRIPTOR keystone → WS1 migrations →
IC-METAGUARD (hard, after all WS1) · WS2 last behind a design-spike tripwire.
`_baselines.yaml`/`anchoring.py` are single-owner (C-006).
**Rationale**: the meta-guard reds any un-migrated line seed, so it can only go
green after WS1 (else NFR-004 869/0 breaks). WS2 carries all the design risk and
must not gate WS1/WS3 merge; the tripwire (>2 WPs or unstable body-hash → carve to
#2546) bounds it.
