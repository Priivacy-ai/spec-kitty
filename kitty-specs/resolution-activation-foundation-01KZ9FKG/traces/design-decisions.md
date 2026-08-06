# Design Decisions

> Capture the rationale that would otherwise evaporate.

Mission: `resolution-activation-foundation-01KZ9FKG` · #2657 + #3210.
Seeded at planning from the ADR + 3-lens pre-spec squad + operator decisions (2026-08-05).
**Append a dated entry whenever a material decision is made or revised during implement; assess at close.**

**Prompting questions**
- What decision was made? · What alternatives were considered? · Rationale — why this over the others?

---

## Decisions carried in (seed)

- **D1 — Decouple the two mission-type threads; land availability before kind-promotion.**
  Alternatives: keep bundling "relocate + promote + activate" (the shape that kept deferring).
  Rationale: the availability half (#2652 chain) needs only #2657, not the L-sized keystone #2467;
  splitting them delivers "charter-loaded mission types" on the shortest unblocked path. (ADR
  `2026-08-05-1`.)
- **D2 — Bundle #2657 + #3210 as one foundation slice.** Alternatives: two separate missions.
  Rationale: #2659 (next slice) wires the single door (#3210) + single authority (#2657) together;
  preparing both here lets #2659 repoint the readers exactly once. Coupling is loose (disjoint files)
  but the sequencing pairing is real.
- **D3 — `SPEC_KITTY_PACKS_ROOT` governs the pack tree (missions included); wins when both env vars
  set; `SPEC_KITTY_TEMPLATE_ROOT` stays the asset-copy override.** (Operator, 2026-08-05.)
  Alternatives: TEMPLATE_ROOT wins for missions; or leave `default_missions_root` env-blind.
  Rationale: matches every other built-in kind; closes the split-brain at the source rather than
  relocating it to a new seam.
- **D4 — Keep both rc35 migrations; add fresh-init provisioning as the new path.** (Operator,
  2026-08-05.) Alternatives: consolidate the two overlapping rc35 migrations into one.
  Rationale: consolidation rewrites shipped migration identity/ordering (higher regression risk);
  the real gap is fresh-init, which is genuinely unprovisioned today.
- **D5 — `home.py` becomes a thin downward re-export of the kernel authority.** Alternatives:
  keep both doors + pin equivalence with a test. Rationale: the ADR wants one door with consistent
  env semantics; the equivalence test is the safety net during the collapse, not the end state.
  C-004-legal because it is a downward import (specify_cli → kernel).
- **D6 — Surviving mission-root detector uses the enumeration-free wildcard.** Alternatives: keep
  `home.py`'s per-type enumeration via `builtin_mission_type_ids()`. Rationale: enumeration re-hides
  the "which types exist" list that #2657 makes the charter own.
- **D7 — Scope fence is a hard constraint, not a guideline.** Kind-promotion (#2468), nested-vs-flat
  path, availability-reader repoint (#2659–61), keystone (#2467), and the schema follow-up are OUT,
  each with a proof marker asserted as a regression (C-001..C-004). Rationale: the deferral history
  came from scope creep into the blocked, higher-risk work.

- **D8 — Pause after plan; wait for topology PR #3211 to land, then revise spec+plan before
  implementing.** (Operator, 2026-08-05.) Rationale: #3211 ("Review-cycle verdict-seam rebuild")
  is a large in-flight change; revising spec/plan against the landed #3211 tree avoids planning on
  a base that is about to shift. Implementation does NOT start until spec+plan are revised post-#3211.

## Entries — post-tasks squad fixes (2026-08-05)

- **WP04 T019/T020** rewritten: "provisioned = key present" (was contradictory); absent key → fail-closed
  (`CharterPackConfigError`, actionable), NOT a roster return; WP04 adds NO runtime `default.yaml` read
  (delete-only at the read boundary). Prevents re-introducing the second source WP05 guards.
- **WP03 T014** gained a copy-vs-rescan **discriminator** (fixture default.yaml differing from the disk
  roster, or PACKS_ROOT→empty tree) — the naive test passed either way because default.yaml == disk roster.
- **WP03 packaging**: added `src/specify_cli/provisioning/__init__.py` to owned_files + create_intent
  (net-new package needs its `__init__`).
- **WP01**: C-009 door-caller census promoted from Risks prose to a T003 DoD step; new primitive + sibling
  pattern exported publicly (kernel `__all__`) so WP02 imports a public symbol.
- **WP05 T023**: single-source guard scoped to actual env *reads* (`os.environ.get`), not raw string
  occurrences (else the docstring/constant name false-positive). T025 tightened to run-and-cite the gates.



<!-- YYYY-MM-DD — Decision: [what]. Alternatives: [what else]. Rationale: [why this one]. -->

- 2026-08-05 — **D-RESOLVE (operator): UNIFY the resolver.** The `built-in` pack (missions included)
  is installed/available from the default- or env-supplied pack root ("PACKS_HOME" =
  `SPEC_KITTY_PACKS_ROOT`). One pack-root resolver; missions = `<built-in-root>/missions`; the
  `get_package_asset_root` door and `default_missions_root` both route through it and honor the pack
  root uniformly. The env-aware primitive lives at the **kernel** floor (consumed downward; kernel
  must not import doctrine). This resolves **M1** (supersedes the two-resolver-consistency framing)
  and **M2** (the `specify_cli/missions`/`dev_root` legacy fallbacks are intentionally dropped —
  fail-closed instead). Confirm the exact env-var name at revision (keep `SPEC_KITTY_PACKS_ROOT`
  unless a rename is intended). See `post-plan-review-findings.md` DR-1/DR-2.
- 2026-08-05 — OPEN (post-plan squad, resolve in the post-#3211 revision): **M4** — IC-05 provisioning
  must COPY `default.yaml`'s authored list, not re-scan via the resolver (keeps IC-02→IC-05 soft).
  **M3** — pin NFR-003 "offered types" to the activation-authority surface, not `list_available_missions`.
  **F1** — hoist the sibling-pattern literal to one kernel-owned public constant instead of 3 drifting
  copies (now reinforced by D-RESOLVE — the single primitive owns the pattern).
