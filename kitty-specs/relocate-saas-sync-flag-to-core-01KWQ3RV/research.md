# Research: Relocate SaaS-Sync Flag to Core

Phase-0 decisions (verified against live code at plan time).

## D-01 — Target module: new `core/saas_sync_config.py`
**Decision**: a new focused CORE module, not a join into `core/config.py`.
**Rationale**: `core/config.py` is a *static-choices constants* module (`AI_CHOICES`, `MISSION_CHOICES`, `DEFAULT_MISSION_KEY`, …). Mixing a runtime `os.environ` flag reader there fragments concerns and bloats a constants module. A dedicated module is the single canonical owner of this one concern, imports only stdlib (`os`) so it introduces no cycle, and is unambiguously CORE-set (under `core/`, satisfying C-001 / `CORE_PACKAGES`).
**Alternatives**: join `core/config.py` (rejected: concern mismatch); `core/constants.py` (rejected: it holds constants, not readers); `kernel/` (rejected: not in the boundary's CORE set — the CORE set is `specify_cli/{core,status,readiness,invocation}`).

## D-02 — `saas/rollout.py`: retained as a thin re-export shim (NOT deleted)
**Decision**: keep `saas/rollout.py`, re-exporting the names from the core home.
**Rationale**: forced by NFR-001. `tests/saas/test_rollout.py:16` does `from specify_cli.saas.rollout import is_saas_sync_enabled, saas_sync_disabled_message` and its shim-identity tests (:107-146) assert `sync`/`tracker` `feature_flags` re-exports are the **same object** (`is`). A re-export shim preserves object identity → those tests pass unchanged. Deletion would force editing `test_rollout.py`, violating "tests pass unchanged", and would break `saas/__init__.py`, `saas/readiness.py`, `sync/daemon.py`, and 7 CLI sites that import by the `specify_cli.saas.rollout` path.
**Alternatives**: delete + repoint all ~24 importers (rejected: breaks NFR-001 identity tests + the stability contract's shim section).

## D-03 — Boundary test: tighten ratchet to `== 0` + remove the positive-control
**Decision**: change `test_allowlist_count_ratchet` from `len(ALLOWLIST) <= 1` to `== 0`, and delete the positive-control assertion in `test_allowlist_cannot_be_bypassed` (~:264-272).
**Rationale**: (a) the mission closes the exemption class permanently — `<= 1` would let a future exemption re-enter silently, so tighten to `== 0` (charter DIRECTIVE_043, close-by-construction). (b) The positive control hard-codes the (now-removed) coordinator→`saas.rollout` allowlisted crossing and asserts `_scan_trees` suppresses it; with the ALLOWLIST empty it reports the crossing and the assertion stays RED *even after relocation* (the string is hard-coded), so it must be removed. The negative control (a non-allowlisted CORE→INTEGRATION import IS reported) stays — that is what keeps the scanner non-vacuous (NFR-004).
**Alternatives**: leave the ratchet at `<= 1` and downgrade the spec claim (rejected: weaker; the whole point is zero-forever).

## D-04 — Stability contract: edit in place + version bump
**Decision**: edit `kitty-specs/082-stealth-gated-saas-sync-hardening/contracts/saas_rollout.md` in place (module-location line, "made once in saas/rollout.py" semantics, shims section), bump the contract version, keep it round-trip parse-valid.
**Rationale**: the file is a *living contract* still enforced by `tests/contract/test_example_round_trip.py:140` — it is not a frozen mission-report snapshot, so the archived-immutability norm (which protects report artifacts) does not forbid updating the contract the test keys on. Leaving it pointing at the old location would make the contract lie. A "relocated by #2252" note + version bump records the provenance.
**Alternatives**: add a superseding contract elsewhere (rejected: splits the single contract the round-trip test reads → dual authority).
