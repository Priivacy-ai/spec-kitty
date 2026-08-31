# Phase 0 Research — Resolution & Activation Foundation

Consolidated from the pre-spec research squad (researcher-robbie / paula-patterns / architect-alphonso,
2026-08-05) and the governing ADR `docs/adr/3.x/2026-08-05-1-mission-type-availability-before-kind-promotion.md`
(incl. the 2026-08-05 DR-1/DR-2 addendum). Revised after the post-plan review squad + #3211 landing.
All NEEDS CLARIFICATION resolved; no open markers.

## D-01 — Resolution topology: UNIFY on one pack-root primitive (revised, DR-1)

- **Decision (operator, 2026-08-05)**: The `built-in` pack (missions included) is installed/available
  from the default- or env-supplied pack root. The mission-tree is `<built-in-pack-root>/missions`
  resolved through ONE primitive: `kernel` owns a `SPEC_KITTY_PACKS_ROOT`-aware built-in-pack-root
  resolver (built on the existing env-agnostic `kernel.sibling_paths.resolve_installed_sibling`);
  `doctrine.pack_paths._resolve_built_in`, `default_missions_root` (= `built_in_root()/"missions"`),
  and the `get_package_asset_root` door all delegate to it. `home.py`'s legacy
  `specify_cli/missions`/`dev_root` fallbacks are dropped (fail-closed).
- **Rationale**: The post-plan review (M1) showed the earlier "thin re-export of the kernel door"
  framing left the door and its ~7 consumers `SPEC_KITTY_PACKS_ROOT`-blind (the door never called
  `default_missions_root`), i.e. the split-brain would move, not die. Unifying on the pack-root
  primitive kills it at the source and subsumes the sibling-pattern duplication (F1).
- **Layering**: kernel reading an env var is C-004-legal (no `doctrine` import). Today the
  `SPEC_KITTY_PACKS_ROOT` read lives only in `doctrine/pack_paths.py:88,204`; it moves down to kernel.
- **Alternatives considered**: (a) earlier "thin re-export of the kernel door" — rejected (M1: door
  stays env-blind). (b) keep two resolvers + a consistency contract — rejected (leaves two sources;
  weaker than one primitive).

## D-02 — Env-var precedence (revised, DR-1)

- **Decision**: `SPEC_KITTY_PACKS_ROOT` governs built-in-pack-root **location** and wins when both env
  vars are set. `SPEC_KITTY_TEMPLATE_ROOT` retains its distinct role as the asset-copy/template
  override (used across `template/manager.py`, `asset_generator.py`, `init.py`, `bootstrap.py`, and
  upgrade migrations — a caller census confirms it is preserved, C-009).
- **Rationale**: Missions are a peer built-in kind; via unification `default_missions_root` inherits
  PACKS_ROOT-awareness by construction. TEMPLATE_ROOT's copy-path role is orthogonal and must survive.
- **Alternatives considered**: TEMPLATE_ROOT wins for missions (more special-casing); leave
  `default_missions_root` env-blind (contradicts #3210). Both rejected.

## D-03 — Activation authority & the implicit fallback

- **Decision**: The provisioned `src/charter/packs/default.yaml` is the activation authority. Remove the config-absent backfill at `charter/pack_context.py:619` (`_read_activated_mission_types` returns `builtin_mission_type_id_set()` when the key is absent). Absent config resolves via provisioning or fails closed.
- **Rationale**: The implicit backfill is the hidden second availability source; removing it is what makes `activated_mission_types` trustworthy. Resolves #3183 (activated-vs-available vocabulary collision).
- **Corrections to issue text**: the fallback is at `pack_context.py:601-619`, NOT `mission_type_profiles.py:388-395` (line drift; those are now the `governance` property). There is **no `CANONICAL_MISSION_TYPES` constant** — the roster is the disk-scanned, cached `builtin_mission_type_id_set()`.
- **Alternatives considered**: none viable — leaving the fallback keeps the second source.

## D-04 — Fresh-init provisioning (the load-bearing risk)

- **Decision**: `spec-kitty init` seeds `mission_type_activations` (and the activation surface) from `packs/default.yaml` for brand-new projects; fail closed with an actionable error if `default.yaml` is missing.
- **Rationale**: Today `init` writes no activation key and both rc35 migrations fail-*open* on absent config — so removing the fallback without init provisioning yields zero mission types for new projects. This is the single load-bearing risk.
- **Alternatives considered**: rely on migration only (does not cover fresh-init); silently default (reintroduces the fallback). Both rejected.

## D-05 — Migration handling

- **Decision**: Keep both `m_3_2_0rc35_default_charter_pack` and `m_3_2_0rc35_activate_builtin_mission_types` unchanged; add fresh-init provisioning as the new path. (Operator decision, 2026-08-05.)
- **Rationale**: Consolidating shipped migrations rewrites identity/ordering (regression risk); both are idempotent and legacy-only.
- **Alternatives considered**: consolidate into one migration — rejected for regression risk.

## D-06 — Surviving content detector

- **Decision**: The surviving `_looks_like_missions_root` uses the enumeration-free glob wildcard (`kernel/paths.py:101`), not `home.py`'s per-type enumeration via `builtin_mission_type_ids()`.
- **Rationale**: Enumeration re-hides the "which types exist" list that #2657 makes the charter own.

## D-07 — Provisioning copies default.yaml, does not re-scan (M4)

- **Decision**: Fresh-init/migration provisioning **copies** `packs/default.yaml`'s authored
  `mission_type_activations` list; it does NOT re-derive the set via `builtin_mission_type_id_set()`.
- **Rationale**: Re-deriving would route through the now-PACKS_ROOT-sensitive resolver, making the
  activation half (IC-05) depend on the resolver half (IC-02) at runtime. Copying keeps them decoupled
  and keeps the "disjoint halves" claim true.

## D-08 — NFR-003 parity measured at the activation authority (M3)

- **Decision**: NFR-003/SC-004 "offered types" parity is measured at the **activation authority**
  (`existing_mission_types` / drg gating), explicitly NOT `list_available_missions`.
- **Rationale**: `list_available_missions` is fenced-unchanged by C-003, so measuring parity there is a
  guaranteed no-op that proves nothing about the fallback removal.

## Fold census (campsite — DIRECTIVE_025, domain-matched only)

Candidates found in-scope; final fold/freeze decided per-WP at implement:
- **Fold (FR-005)**: the false re-export docstrings (`kernel/__init__.py`, `kernel/README.md`) AND the
  non-existent `dev_roots` note (`doctrine/missions/repository.py:37-44`, fold F2 from the review squad).
- **Fold (FR-012)**: the three drifting sibling-pattern constants (`kernel/paths.py`,
  `doctrine/missions/repository.py`, `agent_commands.py`) collapse onto the kernel authority —
  subsumed by DR-1's unified primitive (F1).
- **Fold**: parallel `test_home_unit.py`/`test_paths.py` scenario duplication — collapse where the
  resolver collapses.
- **Third resolver (F3)**: converge `agent_commands.py`'s pattern **constant** onto the kernel
  authority; its `_get_command_templates_dir` **body** stays out of scope (startup-cheap doctrine-
  anchored discovery; already delegates to the door on the env path). Converge constant, freeze body.
- **Freeze (out-of-domain, do NOT fold here)**: nested-vs-flat `mission_types/` path (C-002, #2468);
  availability readers `list_available_missions`/`runtime_bridge_io` (C-003, #2659); ArtifactKind
  cleanup (C-001, #2468); the `_read_activated_kinds` FR-039 fallback (a different activation contract).

## Dependency status

- **#3211** ("Review-cycle verdict-seam rebuild") **LANDED** 2026-08-05 (`1051c430db33`). The feature
  branch was rebased onto it; the only surface overlap was `init.py` (a gitattributes constant), so
  FR-009 provisioning re-anchors around it — no semantic collision (confirmed by the review squad).
