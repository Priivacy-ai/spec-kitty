# Design Decisions

> Capture the rationale that would otherwise evaporate.

**Prompting questions**
- What decision was made?
- What alternatives were considered?
- What was the rationale — why this option over the others?

---

## Entries

<!-- YYYY-MM-DD — Decision: [what]. Alternatives: [what else]. Rationale: [why this one]. -->

2026-07-04 — Decision: relocate the SaaS-sync flag reader into a NEW `core/saas_sync_config.py` (not join `core/config.py`). Alternatives: (a) join existing `core/config.py`; (b) new dedicated module; (c) put in `core/constants.py`. Rationale: `core/config.py` is a static-choices constants module (AI_CHOICES, MISSION_CHOICES) — mixing a runtime `os.environ` flag-reader there fragments concerns; a focused module is the single canonical authority for this one concern and imports only stdlib (`os`), so no cycle risk (C-001).

2026-07-04 — Decision: `saas/rollout.py` is RETAINED as a thin re-export shim, not deleted. Alternatives: delete rollout.py and repoint all ~24 importers. Rationale: forced by the post-spec gate — `tests/saas/test_rollout.py:16` hard-imports from `specify_cli.saas.rollout` and asserts shim object-IDENTITY; deletion would require editing that test, violating NFR-001 (tests-pass-unchanged). Shim preserves object identity; single `def` still lives in one place (C-002).

2026-07-04 — Decision: tighten `test_allowlist_count_ratchet` from `<= 1` to `== 0` (not just empty the ALLOWLIST). Alternatives: leave the ratchet at `<= 1`. Rationale: the mission's goal is zero exemptions PERMANENTLY; `<= 1` would let a future exemption re-enter silently. Closing the defect class by construction (charter standing order #5).

2026-07-04 (post-plan gate) — Decision: the ATDD red commit bundles {empty ALLOWLIST + delete the positive-control block :264-272} atomically. Alternatives: empty ALLOWLIST alone (red commit). Rationale: emptying ALLOWLIST reds BOTH test_no_core_imports_integration AND the positive-control (which hard-codes the removed crossing) — bundling the positive-control removal into the red commit yields exactly one meaningful red (a clean ATDD pin), not an impure double-red.

2026-07-04 (post-plan gate) — Decision: WP01 fixes 3 stale docstrings (sync/tracker feature_flags "canonical home", upgrade_ux.py:77 "shared with saas.rollout") but does NOT fold the 3-way truthy-parser triplication. Alternatives: unify all 3 truthy parsers now. Rationale: the 3 copies parse DIFFERENT flags; unification is a distinct refactor (out of scope). But do not perpetuate a false "shared" docstring — drop the claim + file a follow-up issue at PR time.

2026-07-04 (post-plan gate) — Correction: the saas_rollout.md contract is a LEGACY-ALLOWLISTED, zero-codeblock file — the round-trip test warns-not-fails and does not content-validate it. The in-place edit is SAFER than the spec framed (cannot red the test); just don't add a yaml codeblock.
