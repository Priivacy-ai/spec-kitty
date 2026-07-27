# WP16 Review — Cycle 1 — REJECT

Reviewer: Reviewer Renata (claude). Commit reviewed: 49dd87faf (lane-p).

Symbol retirement (C5), fixture edits (C3-forced), ruff, and return-shape plumbing are all
correct. The WP is rejected on a single load-bearing defect: the C3 byproduct enrolment — the
stated core of this retirement — is **cosmetic**. It removes the warning but still abandons the
orphan, so C3 is not satisfied and C6 regresses.

## Blocking findings

### 1. [BLOCKING — C3] The enrolment is a no-op; the byproduct is neither committed nor reverted

`tasks_move_task.py:1630` calls the **pure** module-level helper and **discards its return value**:

```python
enroll_subprocess_byproducts(created, trusted_roots=(worktree_path,))
```

`coordination/atomic_write.py:338-361` shows that function has no registration side effect: it
runs a confinement check (`ensure_within_any`) and **returns** a `{path: None}` snapshot dict that
is the *entire* enrolment payload. In `_mt_run_transition_gates` that dict is thrown away. There is:
- no `GeneratedArtifactTransaction` in scope (grep in the module: none),
- no `restore_generated_artifact_snapshots(...)` call (grep in the module: none),
- no staging/commit of the created path.

So at runtime nothing is registered with any compensator. The child-created bytes stay on disk
exactly as under the retired behaviour. The migrated test proves it:
`test_gate_created_path_is_preserved_and_enrolled_in_owner` asserts, after a terminal gate block
(exit 1), `sentinel.read_text() == "preserve me"` — the byproduct is **still present**, not
reverted. C3's abort arm ("when the step fails or aborts → restored to pre-transaction bytes";
for a created file that means unlink) is unwired. The source comment at
`tasks_move_task.py:1620-1622` ("Enrolling them … registers them with the single
generated-artifact compensator (WP09)") is therefore false — nothing is registered.

Contrast the genuine owner-caller `merge/executor.py`: it captures the snapshots and routes them
through `restore_generated_artifact_snapshots(snapshots)` on the rollback path
(`executor.py:724`, via `_restore_and_guard_coord_coherence`). WP16 must do the equivalent —
either (a) use the **stateful** `GeneratedArtifactTransaction.enroll_subprocess_byproducts`
(`transaction.py:661`, which stores in `_byproduct_snapshots` and restores at `transaction.py:929`)
so the byproduct is committed on success and reverted on abort, or (b) retain the returned
snapshots and call `restore_generated_artifact_snapshots(...)` on the terminal/abort path. As
written, the byproduct is still "detected and abandoned" — precisely the C3 failure this
retirement was supposed to remove.

### 2. [BLOCKING — DIR-041] The migrated observability tests pin the call, not the effect

Both migrated tests assert only `enrol_spy.assert_called_once()` + the call args. They pass whether
or not the byproduct is ever committed/reverted, so they cannot detect finding 1 — a friction test
that passes for the wrong reason. `test_gate_created_path_is_preserved_and_enrolled_in_owner` is
self-contradictory: it claims "enrolled in owner" while asserting the created file is still
`"preserve me"` on disk after a terminal block. Once finding 1 is fixed, these tests must assert
the **observable byte effect** (created byproduct unlinked on the abort/terminal-block path;
present/committed on the success path), not that a spy was called.

### 3. [BLOCKING — C6] Observability regression with no functional replacement

The operator-facing warning ("Pre-review tests created or changed additional paths; preserved
without cleanup: …") was deleted (`tasks_move_task.py:1559-1563` removed; test now asserts
`"preserved without cleanup" not in result.output`) and nothing functional replaced it. Net effect
of this WP as it stands: the orphan is still manufactured **and** the operator no longer sees it —
a strict regression versus the retired behaviour. Fixing finding 1 (real commit-or-revert)
resolves this; do not ship the warning removal without the compensator wiring.

## Non-blocking / verified-correct (no action needed)

- C5 per-symbol absence: `grep -rn new_checkout_paths src/` → EMPTY; registry row
  `registry/new_checkout_paths.md` deleted; ratchet floor line removed;
  `test_exemption_registry_ratchet.py` green.
- Forced fixture edits (C3-mechanical): the 16 `tests/review/fixtures/parity/*.json` single-key
  drops + the `_capture.py` helper edit + `test_transition_gate_parity.py` are a genuine forced
  consequence of the metadata-key removal (the field vanished from `_mt_pre_review_gate_metadata`).
  Hand-editing the captured JSON rather than regenerating is correct given the generator is pinned
  to a historical base; each fixture is a consistent `-1` line. Not a red-mask. Parity suite green.
- Return-shape change: `_TransitionGateInputs.dirty_before` leg removed, `dirty_before` now
  returned as a separate tuple through `_mt_resolve_transition_gate_inputs` /
  `_mt_resolve_transition_gate_verdicts`. No external unpacker: the only cross-module reference is
  `tasks.py:468` (a re-export alias); the `dirty_before_remediation` hits in
  `_sparse_checkout_doctor.py` / `sparse_checkout_remediation.py` are an unrelated field.
- Quality: ruff clean; mypy shows exactly one error at `:1830` (`no-any-return`) which is
  pre-existing and outside every WP16 hunk (untouched, confirmed); no new suppressions.

## Required for re-review

Wire the enrolment to a live compensator so the child-created byproduct is genuinely committed on
success and reverted on the abort/terminal-block path (finding 1), then re-pin the two
observability tests on the byte effect (finding 2). Finding 3 falls out of finding 1.
