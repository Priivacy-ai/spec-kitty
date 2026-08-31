# Research Synthesis — Charter/Doctrine Structure & Usage Completion Mission

Source: 4-facet research squad (architect-alphonso, paula-patterns, researcher-robbie, reviewer-renata),
read-only against `feat/relocate-builtin-doctrine-packs` @ c445418d2. Inputs: 9 issues (#3119/#3120/#3118/
#3116/#3106/#3105/#3104/#3101/#3102) + the 41-test CI failure set from closed PR #3117.

## Convergent root cause

The charter/doctrine surface has **multiple conceptual authorities, none exposed as a single callable that
returns the fully-composed value**, so consumers re-derive the last hop at the point of use. Three instances:
1. **Built-in on-disk location** — authority = `resolve_pack_root("built-in")` + `ArtifactKind.plural`, but the
   *join* is hand-written ~16× and one path (`DoctrineService._built_in_dir`) still encodes the pre-move NESTED shape.
2. **Charter activation vocabulary** — authority = `pack_manager.YAML_KEY_MAP` (derived from `CHARTER_KIND_TOKENS`),
   but hand-restated as literal tuples in ≥2 more places, one already drifted.
3. **Charter activation store** — config.yaml (write) vs `.kittify/charter/` bundle (read) are **disjoint with no
   compile between them**.
The import-layer order (`kernel<-doctrine<-charter<-specify_cli`) is CLEAN; what leaks is the filesystem/authority
*contract*. "Move the files" is a coupling DETECTOR — every reader carrying its own copy broke or went silent.

## Key correction (robbie): the relocation is not a rot pit

- **The org-pack collision "regression" is STALE TEST SETUP, not a product bug.** `test_org_pack_artifact_lifecycle`
  passes `built_in_root=src/doctrine` (nested, now empty) → built-in loads 0 styleguides → nothing to collide → no
  warning. Pipeline intact; prod uses `built_in_root=None` and works. Fix: `built_in_root=None`.
- **The product relocation is essentially complete** — every shipped repo self-resolves via `resolve_pack_root`; no
  shipped module reads a dead path. Incompleteness = test fixtures + provenance strings + 2 vestigial dead-in-prod paths.
- **Only 7 of 41 CI failures are mission-owned** (6 glossary ERRORs + 1 collision — both stale test). +1 latent
  false-green (`test_profile_inheritance` passes vacuously on a stale path) → sweep proactively.

## Work-streams (candidate mission scope)

### WS-A — Relocation completion (SMALL, bounded; robbie)
- Repoint stale TEST fixtures: `tests/glossary/test_gate_terms.py:35`, `test_org_pack_artifact_lifecycle.py:348`
  (via `built_in_root=None`), `test_profile_inheritance.py:381`; triage-sweep the `parents[N]/"src"/"doctrine"` test
  list for any appending a relocated `<kind>/built-in`.
- Repoint PRODUCT operator-facing strings: `src/charter/resolver.py:187,250` (error text points operators at dead paths).
- Anti-vacuity guard so a future relocation can't false-green.
- Do NOT touch the 5 architectural guard tests that name the old path as a *forbidden pattern*.

### WS-B — Seam consolidation (LOAD-BEARING; architect + paula = #3119)
- Add ONE fail-closed authority `resolve_built_in_kind_root(kind)` / `built_in_dir(kind)` in `pack_paths.py`
  (derive plural from `ArtifactKind`, kills ~14 hardcoded-plural join sites).
- Retire `DoctrineService._built_in_dir` fail-OPEN nested branch: **drop the `built_in_root` param** (preferred — makes
  the wrong shape unconstructable) or redefine as explicit flat override that RAISES on missing. Migrate ~10-15 test
  constructions that pass `built_in_root=`.
- Remove vestigial nested dual-read fallbacks: `catalog.py:283`, `compiler.py:1162`, `kind_vocabulary.py:179-181`;
  retire the CWD ancestor-walk reimpl `doctrine.py:204-210`.
- Ratchet: arch test asserting no production module resolves built-in location except via `pack_paths`
  (mirror `test_shared_package_boundary.py`).
- **OPEN DECISION P-A (paula):** `mission_step_contracts` resolves built-in via a THIRD mechanism
  (`importlib.resources` on `doctrine.missions.built_in_step_contracts`) and was NEVER relocated. Either relocate it
  into `packs/built-in/mission_step_contracts` + route through the seam, OR document it as a deliberate carve-out.
  MUST be settled before "one seam across all built-in kinds" is literally true.

### WS-C — Vocabulary unification (paula = #3106 + P-D)
- Derive `charter_yaml_io._ACTIVATION_KEYS` and the migration's `ACTIVATION_KEYS` from `YAML_KEY_MAP` (export a cheap
  plain-tuple constant to respect the migration's no-heavy-import constraint). **LIVE DRIFT:**
  `m_unify_charter_activation_finalize.ACTIVATION_KEYS` is missing `activated_glossary_packs` (10 vs 11) → would drop
  glossary-pack activation on migration.
- P-D: derive the empty-charter dimension set (`is_charter_empty`) from the vocabulary SSOT so a new kind can't
  silently make the predicate non-exhaustive.
- Guard test: the activation-key lists are set-equal to the derived vocabulary.

### WS-D — Charter usage journey (HIGH VALUE; renata = #3104 P1 + #3105 P2) [REPRODUCED]
- Root: `charter pack apply` writes config.yaml but no compile lowers it into `.kittify/charter/` (bundle), which the
  read surfaces require. Result: apply flips `is_charter_empty`→False (kills the generic-agent dispatch net →
  ROUTER_NO_MATCH, #3104) AND context/status hard-gate on the missing `charter.md` → "not found"/`[]` (#3105). Apply
  delivers *less* usable governance than doing nothing.
- **OPEN DECISION (renata):** bridge the two stores by (a) `apply` triggers a compile that materializes the bundle from
  config.yaml, OR (b) the read surfaces (`resolve_project_governance`, the `charter.md` gates in `context.py:286` +
  `_common.py:_resolve_charter_path`, `_status_collectors`) read config.yaml as a first-class source. Must be a SINGLE
  authority (unification-not-parity).
- Fix `is_charter_empty` so config-with-no-routable-profile still keeps the generic-agent net (independently shippable;
  mind the #3064 composite-predicate lesson — don't false-fallback on glossary-only/org-pack activations).
- Make `apply` output truthful (name the step or remove the need). Journey tests: empty→apply→dispatch-unmatched (NOT
  ROUTER_NO_MATCH); apply→context/status reflect the pack.

### WS-E — Shim retirement (paula = #3116; independent, test-only)
- Re-point ~62 `from charter.context import _x` test imports to leaf modules; delete the FR-009 re-export block
  (`context.py:25-145`). 0 production call sites. Lowest risk; hazard = multi-line imports.

### WS-F — Perf/hygiene (low severity)
- #3118: `is_charter_empty` double-loads charter config (2×–4× reads) — load once (folds into WS-D's predicate work).
- #3120: sweep 18 `packs/built-in/**` self-referential `related:`/`source_files:` old-path strings + docs/`.kittify`
  prose; add content-manifest SHA-256 hashes. **First verify `related:` is not runtime-resolved** (if it is → real repoint).

## Explicitly DEFERRED / out of scope (do NOT bundle)
- **#3101 wheel-split** (doctrine/charter → installable wheel) — downstream design-spike; NOT a prerequisite for #3119.
  Hidden blocker to retire first: `resolve_doctrine_root()`'s upward `specify_cli`-root fallback (`catalog.py`). The
  finalization mission should merely *de-risk* the future split by finishing the seam.
- **#3102 path-filtered CI** for doctrine/charter — gated on the seam work + #3101.
- **missions Phase 1b (#3091)** — relocating `missions/` (interacts with P-A).
- **The large SYNTHETIC-test-family migration** (~60 files building nested tmp roots) — coupled to dropping the
  `built_in_root` param; likely a follow-on unless WS-B chooses the param-drop.
- **34 pre-existing/unrelated CI reds** — sync-3030 doctor/purge cluster, review-cycle, #2804/#3086 merge-gate,
  charter-cli 3045, charter-widen json_malformed, #3092 activation-parity, and the **accept-snapshot forgotten-regen**
  (twelve_agent_parity[accept-*], command_renderer[*-accept] — from an accept-TEMPLATE change on main, NOT doctrine
  relocation; belongs to whoever changed the accept template).

## Sequencing (paula + architect converge)
1. WS-E (#3116 shim) — independent, test-only, shrinks surface.
2. WS-C (vocab) + P-D — independent; fixes the live migration drift; add guard.
3. WS-F/#3118 — small.
4. WS-B (seam: helper + drop fail-open param + repoint joins + remove dual-reads + ratchet) — the keystone; settle P-A first.
5. WS-A (relocation-completion test repoints + resolver strings + anti-vacuity) — pairs naturally with WS-B.
6. WS-D (usage journey) — highest user value; can proceed in parallel (different surface).

---

# DESIGN-PHASE RESOLUTIONS (architect-alphonso + reviewer-renata)

## Sizing correction (drives WS-B scope)
"~60 synthetic test files" conflated TWO params. `DoctrineService(built_in_root=…)` (the fail-open foot-gun) is
passed by only **20** files → **~14 coupled churn** (6 already `None`; ~5 real-repo-root = the WS-A stale readers;
~9 nested-tmp → flat). `Repository(built_in_dir=…)` is a DIFFERENT already-flat leaf param, NOT dropped (the bulk of
the 60 hits). So dropping `built_in_root` is IN-SCOPE, ~14 files.

## Resolved decisions
- **P-A → DELIBERATE CARVE-OUT.** Do not relocate `mission_step_contracts` now (that IS Phase-1b #3091, kernel-layer
  `__file__` idioms). `built_in_dir(MISSION_STEP_CONTRACT)` RAISES — named+gated exception, not a silent 2nd mechanism.
  Claim = "one seam across all FILE-BASED built-in kinds; step-contract is a documented package-resource exception."
- **WS-B → DROP the `built_in_root` param** (wrong shape becomes unconstructable). Synthetic test tiers use
  `SPEC_KITTY_PACKS_ROOT`. Target seam = `built_in_dir(kind)` in `pack_paths.py` (derives `kind.plural`); 10 repo
  `_default_built_in_dir()` collapse to it; anti-regression arch test (negative ratchet: only `pack_paths.py` may join
  `resolve_pack_root("built-in")`; positive per-kind coverage w/ `#3091` carve-out marker; anti-vacuity: shipped
  agent_profiles non-empty).
- **WS-D bridge → OPTION (a): compile via the EXISTING seam.** `compile_charter`/`write_compiled_charter` ALREADY lower
  config.yaml→`.kittify/charter/charter.yaml` (authoritative bundle) with no interview. `apply` just skips it. Fix:
  `apply` names/offers the exact compile step (`--compile` opt-in chaining the compiler seam); RETARGET the read gates
  from the display-only `charter.md` onto `charter.yaml` (`context.py:286`, `_common._resolve_charter_path`,
  `_status_collectors`); retire `resolver.py:233-260` legacy `governance.yaml.selected_directives` catalog-fallback →
  source from the compiled catalog. Reject (b) (5 readers re-derive config.yaml = the root-cause anti-pattern).
- **#3104 predicate → key the dispatch net on COMPILED-BUNDLE PRESENCE (`.kittify/charter/charter.yaml`), not the
  config aggregate.** empty→net fires; apply-minimal-without-compile→still fires (FIXED); apply+compile→net off, router
  runs (NO_MATCH now the correct signal). #3064-trap-safe (splits governance-emptiness from dispatch-routability).
  **This retires WS-C's P-D** (no dimension-set to keep set-equal) AND **folds #3118** (double-load → single
  bundle-presence check). Independently shippable, precedes the bridge.

## FINAL MISSION BOUNDARY — TWO sequenced missions (both squads converge)
- **Mission 1 `doctrine-built-in-seam-consolidation`** (structural; WS-A/B/C/E/F). Lands first. WP01 seam authority /
  WP02 drop foot-gun param + ~14 test migration (fixes collision RED) / WP03 relocation-completeness repoints +
  resolver operator strings + anti-vacuity / WP04 dual-read removal + arch ratchet / WP05 vocab unification + **live
  glossary-pack drift fix** / WP06 (#3116 shim, severable) / WP07 (#3120 hygiene, severable, verify `related:` not
  runtime-resolved first).
- **Mission 2 `charter-pack-usage-journey`** (behavioral; WS-D = #3104/#3105/#3118). Parallel/after M1. Bridge (a) +
  bundle-presence predicate + reader retarget + journey tests.
- **Cross-mission coordination:** WS-C's migration-drift fix (M1/WP05) must land BEFORE WS-D's resolver retarget
  (shared `resolver.py` + activation-store trust). Optionally peel WS-E (#3116) into its own trivial mission.
