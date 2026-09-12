# Post-Plan Review Squad — Findings & Revision Input

Mission: `resolution-activation-foundation-01KZ9FKG` (#2657 + #3210).
Squad (2026-08-05, read-only): reviewer-renata (spec↔plan quality), paula-patterns (missed folds/boy-scout),
architect-alphonso (scope-fence / sequencing / #3211 / NFR feasibility).
Full transcripts: `scratchpad/review-{renata,paula,alphonso}.md`.

**Status: input for the post-#3211 spec/plan revision. Do NOT implement until spec+plan are revised.**
All code claims in spec/plan/research were independently verified TRUE against source.

---

## Operator decisions resolving squad findings (2026-08-05)

- **DR-1 (resolves M1) — UNIFY the resolver; the `built-in` pack is installed/available from the
  default- or env-supplied pack root ("PACKS_HOME").** There is ONE resolver for the built-in pack
  tree, and the missions tree is just `<built-in-pack-root>/missions` resolved through it. The
  `get_package_asset_root` door and `default_missions_root` both route through the single pack-root
  resolution primitive, so both honor the env-supplied pack root uniformly. This supersedes the
  weaker "keep two resolvers, add a consistency contract" framing — the two collapse onto one.
  - **Layering implication (must respect C-004):** the pack-root/env resolution primitive must live
    at the **kernel** floor (kernel already owns `resolve_installed_sibling` + the door), so the
    kernel door, `doctrine.pack_paths`, and `doctrine.missions.repository.default_missions_root` all
    consume it **downward** — kernel must NOT import doctrine. Today the `SPEC_KITTY_PACKS_ROOT`
    handling lives in `doctrine/pack_paths.py` (`_PACKS_ROOT_ENV`); unifying means lifting that env
    resolution down to kernel (or exposing a kernel primitive both consume), NOT routing kernel
    through doctrine.
  - **Env-var name — confirm at revision:** the existing var is `SPEC_KITTY_PACKS_ROOT`; the operator
    phrasing "PACKS_HOME" maps to it. Revision confirms whether we keep `SPEC_KITTY_PACKS_ROOT` or
    intend a rename (a rename would be a separate terminology/bulk-edit concern — default: keep the
    existing name).
- **DR-2 (resolves M2) — dropping home.py's `specify_cli/missions`/`dev_root` legacy fallbacks is
  INTENDED.** Since the built-in pack (missions included) is authoritatively resolved from the pack
  root, the `specify_cli/missions` legacy tree is no longer a resolution source. The revision must
  state this explicitly and add the missing-`packs`/broken-install behavior contract (fail-closed,
  not fall-through to `specify_cli/missions`).

**Effect on scope/risk:** DR-1 makes the #3210 half a slightly larger refactor (kernel owns the
env-aware pack-root primitive; the door gains PACKS_ROOT-awareness), but architecturally cleaner and
single-source. NFR-003 default-env parity still holds (default pack root == installed
`packs/built-in`). Confirm the kernel↔doctrine env-resolution move does not trip the layer gate.

---

## MUST-FIX before implement (fold into the post-#3211 revision)

### M1 — The PACKS_ROOT split-brain *moves*, it doesn't die (most material)
`packs/built-in/missions` is resolved by **two functions with disjoint caller bases**:
- `get_package_asset_root` (kernel door + home shim) — callers: `init.py`, `runtime/resolver.py`,
  `bootstrap.py`, `migrate.py`, `show_origin.py`, `agent_commands.py`, `charter/catalog.py`.
- `default_missions_root` (doctrine) — callers: `template/manager.py`, `skills/command_installer.py`,
  `charter/pack_manager.py`, `mission_type_repository.py`, doctrine internals.

FR-003/FR-004 + US1-scenario-2 + C-R2/C-R3 make **only `default_missions_root`** PACKS_ROOT-aware.
**No FR/contract makes the door honor PACKS_ROOT** — yet the ADR + data-model Key Entities name the
*door* as the thing #2659 builds on. Aggravator: home.py currently delegates the door →
`default_missions_root` (`home.py:149`); the plan re-points home at the **kernel** door, which never
calls `default_missions_root`, so the new PACKS_ROOT-awareness never reaches the ~7 door consumers.
**Fix in revision:** add an FR + C-R contract stating explicitly whether the door honors
`SPEC_KITTY_PACKS_ROOT`, apply FR-004 precedence to it, and add a **cross-resolver-consistency**
contract: `default_missions_root()` and `get_package_asset_root()` resolve the *same* tree under the
*same* env (default / PACKS_ROOT / both-vars). Touches: spec FR-003/004, contracts C-R2/C-R3, plan
IC-02, data-model Seam 1↔Seam 2 (currently treated as independent; they resolve one tree).

### M2 — The thin re-export silently drops home.py's legacy fallbacks
`home.get_package_asset_root` has two fallbacks the kernel door lacks: the `importlib`
`specify_cli/missions` tree (`home.py:155-161`) and `dev_root = .../specify_cli/missions`
(`home.py:163-165`). "Thin re-export of the kernel authority" (FR-001/FR-006) removes both. C-S1
keeps `src/specify_cli/missions/` on disk but the door will no longer resolve to it; NFR-003 parity
is scoped to "default env," which hides the legacy/missing-`packs` layout where these fire.
**Fix in revision:** spec must state the drop is intended/safe (name who relied on them) or preserve
them in the surviving authority; add a contract for the missing-`packs/built-in/missions` behavior
before/after. Touches: FR-006, IC-01, NFR-003 scope note.

### M3 — NFR-003 / SC-004 "offered types" is a no-op as worded (alphonso)
"0 diff in offered mission types" is a **strict no-op** if measured via `list_available_missions` /
`_build_discovery_context` (fenced unchanged by C-003), and **real-but-tautological** via the
activation authority (`mission_type_profiles.existing_mission_types:498`, `charter/drg.py:441,471`)
— holds only because `default.yaml` == old fallback roster.
**Fix in revision:** pin NFR-003/SC-004 "offered types" to the **activation-authority surface**
(`existing_mission_types` / drg gating), explicitly NOT the C-003-fenced enumeration reader.
Resolved-path parity under default env is real — keep it.

### M4 — IC-05 must COPY default.yaml, not re-scan (latent IC-02→IC-05 edge) (alphonso)
If IC-05 provisioning re-derives the set via `builtin_mission_type_id_set()` (which flows through the
now-PACKS_ROOT-sensitive `default_missions_root`) instead of copying `default.yaml`'s authored list,
IC-02 becomes a **hard upstream dependency** of IC-05 and the "disjoint files" claim is false.
**Fix in revision/tasks:** pin "provisioning copies `default.yaml`'s authored list, does not re-scan."

---

## SHOULD-FIX — missed folds & traceability (paula + renata)

### F1 (paula) — Single authority for the sibling PATTERN literal (arguably the headline)
`PurePosixPath("packs")/"built-in"/"missions"` is a byte-identical named constant in **three**
surviving modules under drifting names — `kernel/paths.py:88` `_MISSION_ASSETS_SIBLING_PATTERN`,
`doctrine/missions/repository.py:29` `_MISSIONS_ROOT_SIBLING_PATTERN`, `agent_commands.py:93`
`_MISSIONS_SIBLING_PATTERN` (+ inline 4th at `home.py:79`, dies with FR-006). The plan unifies the
resolver *body* but leaves the *literal* forked 3×. **Fix:** kernel owns a public
`MISSION_ASSETS_SIBLING_PATTERN` (it already owns `_MISSION_ASSETS_DIR_NAME`), imported downward
(C-004-legal). `pack_paths.py:211` can't own it (missions isn't an ArtifactKind, C-001 — the reason
the copies exist). FOLD into IC-01/IC-02. **Effort: small.** Add a supporting FR/NFR so it's pinned.

### F2 (paula) — Second false docstring: `repository.py:37-44` `dev_roots` note
Claims a `dev_roots` tuple in home.py that "propagates before the second entry" — false today
(`home.py:148-151` catches `MissionsRootNotFound`; no such tuple). Same defect class as the FR-005
re-export lies the census caught. FOLD into IC-03 (extend the docstring-truth sweep). **Trivial.**

### F3 (paula) — Third resolver's pattern constant → kernel authority
`agent_commands.py:93` is the 4th copy; converge the **constant** (one-line downward import). The
resolver **body** stays out of scope (startup-cheap doctrine-anchored discovery; already delegates to
the door on the env path). **Verdict: converge the constant, freeze the resolver.** Trivial.

### N1 (renata) — C-R4 (fail-closed resolution) has no backing FR → add one or annotate source.
### N2 (renata) — NFR-002 / NFR-005 have no acceptance-contract row → map to named existing gates.
### N3 (renata) — FR-005/C-R5 (docstring truth) names no test → name the grep/test surface.
### N4 (renata) — C-R2 layout under-specified → pin `<PACKS_ROOT>/built-in/missions` (drop "or the documented layout").

---

## NOTES (no change / acknowledge)

- **Fence enforceability (alphonso):** C-001 & C-003 are ENFORCEABLE today (proof markers verified:
  `MissionTypeNotAnArtifactKind` `artifact_kinds.py:219`, `_MISSION_TYPE_UNIVERSE_EXTENSION`
  `org_pack_loader.py:129`; `list_available_missions` `mission.py:489`, `_build_discovery_context`
  `runtime_bridge_io.py:231`). **C-002 & C-004 are abstinence fences with NO positive marker** —
  review-only, not automatable. Optional guard: assert `built_in_dir(kind)` gains no mission-type entry.
- **NFR-001 arch test scope:** must target the `mission_type_activations` fallback site specifically,
  NOT the legitimate directive/kind three-state fallbacks or `_read_activated_kinds` FR-039 fallback
  (`pack_context.py:591-676` — a DIFFERENT contract; do not harmonize).
- **N5 (renata):** ADR line 53 says `_find_relocated_missions_ancestor` is "byte-duplicated"; code
  shows logically-duplicated (spec is correct). Fix the ADR wording during revision; no spec change.
- **Doc nit (alphonso):** `plan.md:141` cites "D5" for "land #3210 first" — wrong (D5 is migration
  handling); should reference the ADR land-together / the enumeration-seam D-06. `plan.md` D6 ref is correct.
- **"Single trustworthy authority" is partly aspirational until #2659** — the only live consumers of
  the changed authority are the charter/DRG-gating readers, not the enumeration surface. In-scope it
  still holds because those readers already read `activated_mission_types`.

---

## #3211 re-anchor (the reason for the pause)

PR #3211 touches 203 files; **exactly ONE overlaps this mission's surface: `src/specify_cli/cli/commands/init.py`** (IC-05). #3211 adds `_REVIEW_CYCLE_GITATTRIBUTES_ENTRY` (~L74-83) + a `required_entries`
append (~L210) — gitattributes/merge-driver registration, **semantically unrelated** to IC-05's
provisioning. Conflict is **textual/line-drift only**. `context_contract.py` is touched by #3211 but
not referenced by our charter surfaces. No overlap on kernel, doctrine, runtime/home, runtime/next.
**Post-#3211 action: re-anchor IC-05's init.py insertion points only; re-verify nothing else drifted.**

---

## Revision checklist — APPLIED 2026-08-05 (post-#3211 rebase + revision)

1. [x] M1→DR-1 — spec FR-001 + data-model Seam 1 (unified kernel primitive; door + `default_missions_root`
       + `_resolve_built_in` delegate); ADR addendum; contract C-R1/C-R2. Layer-move rationale in NFR-002/C-005.
2. [x] M2→DR-2 — spec FR-006 + Edge Cases + contract C-R4 (legacy fallback drop intended, fail-closed).
3. [x] M3 — NFR-003/SC-004 + contract C-A6 re-pinned to the activation authority (not `list_available_missions`).
4. [x] M4 — spec FR-009 + IC-05 + data-model I-10 + research D-07 (copy default.yaml, don't re-scan).
5. [x] F1 — spec FR-012 + contract C-R1 (sibling-pattern single authority; subsumed by DR-1).
6. [x] F2/F3 — FR-005 extended to the `dev_roots` docstring; IC-02/IC-03 converge `agent_commands.py` constant.
7. [x] N1-N4 — C-R4↔FR-013; NFR-002/005 named in Charter Check + IC-06; FR-005 test surface named in IC-03;
       C-R2 layout pinned to `<PACKS_ROOT>/built-in/missions`.
8. [x] NOTES — ADR "byte-duplicated" corrected in the addendum; plan D5 citation fixed; NFR-001 scoped to the
       `mission_type_activations` fallback; C-002/C-004 marked review-only fences.
9. [x] #3211 — branch rebased onto `1051c430db33`; only `init.py` overlapped (gitattributes constant); IC-05
       notes the re-anchor. No semantic collision.
