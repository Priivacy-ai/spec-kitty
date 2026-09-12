# Approach Evolution

> Track how your approach changed as the mission progressed.

Mission: `resolution-activation-foundation-01KZ9FKG` · #2657 + #3210.
Seeded at planning. **Append as the approach is refined/validated during implement; assess at close.**

**Prompting questions**
- What approach did you start with (as stated in the spec or plan)?
- What changed during implementation, and why?
- What would you try differently on a similar mission?

---

## Intended shape (seed — from spec + ADR)

Two loosely-coupled halves that edit **disjoint files** (no merge-conflict risk, no hard ordering):
- **#3210 half** — collapse the two `get_package_asset_root` doors onto one kernel authority
  (`home.py` → thin downward re-export), de-dup `_find_relocated_missions_ancestor`, make
  `default_missions_root()` honor `SPEC_KITTY_PACKS_ROOT`, correct the false re-export docstrings,
  retire the runtime second copy (survivor uses the enumeration-free wildcard).
  Files: `kernel/paths.py`, `kernel/__init__.py`, `kernel/README.md`, `specify_cli/runtime/home.py`,
  `doctrine/missions/repository.py`.
- **#2657 half** — retire the implicit "all four" fallback (`pack_context.py:601-619`), make the
  provisioned `packs/default.yaml` the activation authority, add fresh-init provisioning, keep both
  rc35 migrations, fail-closed on unprovisionable install.
  Files: `charter/pack_context.py`, `charter/mission_type_profiles.py`, `cli/commands/init.py`.

**Recommended (not required) order: land #3210 first** so a single, enumeration-free door exists
before #2657 reasons about what that door offers (soft seam W-note: the surviving
`_looks_like_missions_root` must be the wildcard one, not the enumerating copy).

**ATDD-first (C-006):** red acceptance test per FR before implementation — esp. the single-door
architectural invariant (SC-001), the `SPEC_KITTY_PACKS_ROOT` missions regression (NFR-006/SC-002),
and the before/after parity test (NFR-003/SC-004).

## Entries

<!-- YYYY-MM-DD — 1-3 sentences: what approach was tried and what shifted. -->

- 2026-08-05 — Post-plan squad reshaped the #3210 half: the "one door via thin re-export" framing is
  incomplete because `packs/built-in/missions` is resolved by TWO functions with disjoint callers
  (`get_package_asset_root` door + `default_missions_root`), and re-pointing home at the kernel door
  would strand the PACKS_ROOT-awareness on `default_missions_root` (M1) and drop home's legacy
  fallbacks (M2). Revision must add a cross-resolver-consistency contract, not just collapse one body.
  See `post-plan-review-findings.md`. Deferred to the post-#3211 revision.
- 2026-08-05 — #3211 landed (`1051c430db33`); rebased the branch (only conflict was the ADR index,
  regenerated via the freshen script). Applied the full revision: spec/plan/contracts/data-model/
  research now describe the UNIFIED pack-root primitive (DR-1) with the kernel-floor PACKS_ROOT read,
  `default_missions_root = built_in_root()/"missions"`, fail-closed (DR-2), copy-not-rescan
  provisioning (M4), and activation-authority-pinned parity (M3). All 9 revision-checklist items
  applied. Ready for a delta review then `/spec-kitty.tasks`.
