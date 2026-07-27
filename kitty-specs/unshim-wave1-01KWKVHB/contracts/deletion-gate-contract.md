# Deletion-Gate Contract — unshim-wave1-01KWKVHB

This mission's executable contract is the pre-existing bidirectional
stale-allowlist guard (`tests/architectural/test_no_dead_modules.py` ~:592):

1. **Delete ⇒ drain**: a deleted module whose allowlist row survives hard-fails
   the gate (ghost row).
2. **Drain ⇒ delete**: a drained row whose module survives hard-fails the gate
   (orphan gained a caller / premature drain).
3. **Shrink-only ratchets**: every `_baselines.yaml` change in the mission diff
   is a count decrease (category_4 8→0, category_7 6→2, category_b 237-recorded
   → 216-honest); growth above baseline fails, shrink warns.
4. **No-touch surface** (C-001): `src/specify_cli/auth/transport.py`,
   `tests/**/test_auth_transport_singleton.py`, `src/specify_cli/policy/audit.py`
   are byte-identical to upstream/main — enforced as an executable negative
   invariant in `acceptance-matrix.json`.
5. **Re-anchor interception**: every rewritten `patch()` target pins the
   consumer's lookup namespace, proven by `assert_called_once` (all 10 sites) +
   red-first discrimination probes (implementer + reviewer independently).

`plan.md` records why no API/data contract exists: the mission is deletion-only;
this gate contract is the whole behavioral surface.
