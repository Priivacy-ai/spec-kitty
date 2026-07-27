# Quickstart / Validation — Execution-Context Unification (01KTPKST)

Validation scenarios that prove the mission's success criteria. The parity ratchet (IC-08) is the
primary regression guard; the rest are targeted repros of the drained issues.

## SC-1 — Parity ratchet (the regression guard)

EXTEND `tests/architectural/test_execution_context_parity.py` (do not fork). Assert that resolving the
context from the **primary checkout** and from a **lane/coord CWD** yields identical answers for every
fragment, across `specify → plan → tasks → analyze → implement → review → status`.

```bash
pytest tests/architectural/test_execution_context_parity.py -q
# Expect: identical fragment values from both CWDs; zero split; clean trees.
```

Add a **flattened-topology synthetic fixture** (no separate coord branch) so C-001 is *proven*:
the flattened mission must show `CommitTarget.kind == flattened`, `coordination_branch is None`,
`status_read_dir == status_write_dir`.

## SC-2 — Paused-mission blockers do not reproduce

The two failures that paused 01KTNWFC must be structurally precluded after IC-05:

```bash
# record-analysis must not deadlock on coord residue (#1814)
spec-kitty agent mission record-analysis --mission <fresh-mission> --input-file <report.md> --json
# implement-claim must not block on planning-artifact branch-split (#1816)
spec-kitty agent action implement WP01 --mission <fresh-mission> --agent claude:opus:implementer:implementer
```

Both resolve placement via the ArtifactPlacementFragment — no primary-dirty-tree vs coord-owned conflict.

## SC-3 — Each folded issue's repro passes (or is structurally precluded)

| Issue | Repro check |
|-------|-------------|
| #1737 | `status_transition` reads the carried StatusSurfaceFragment; grep confirms no independent coord-path derivation remains |
| #1357 | concurrent `CoordinationWorkspace.resolve` is lock-serialized (no race materializing divergent surfaces) |
| #1572 | status visible identically from primary and coord CWD |
| #1764 | analysis-report not falsely stale across CWDs |
| #1789/#1062 | see SC-5 |
| #1735/#1771 | retrospect reads/writes the canonical surface (no primary-only read, no gitignored write) |
| #1736/#1770 | merge consumes the context (PATH/env, baking, JSONL) |
| #1816/#1814 | see SC-2 |

## SC-4 — One resolution path (C-005 enforcement)

```bash
# No second context resolver, no forked parity test, no resurrected duplicate.
rg -n "candidate_feature_dir_for_mission" src/        # expect: gone (folded into _read_path_resolver)
rg -n "def .*parse.*worktree" src/specify_cli/workspace/root_resolver.py  # expect: gone (deleted)
rg -n "EventLogWriteTarget|StatusReadSource|read_wp_lane_actor" src/      # expect: gone (IC-09)
ruff check . && mypy <changed paths>                  # zero issues (NFR-002)
```

## SC-5 — Long rebase does not clobber status (#1789)

```bash
# On a mission branch with a daemon/dashboard active, run a long rebase.
# materialize_if_stale must NOT re-materialize tracked status mid git-op.
git rebase <base>   # completes with no status-file clobber; tree clean afterward
```

## NFR checks

```bash
pytest tests/architectural/test_no_legacy_terminology.py   # Terminology Canon (pre-push, CI-only gate)
pytest tests/architectural/test_shared_package_boundary.py
# NFR-005: changed-path LOC trends DOWN (report delete vs add in the WP handoff)
```

## Cleanup discipline
- The flattened synthetic fixture must not leak `test-feature-*` missions or `kitty/mission-test-feature-*`
  branches (known E2E leak). Clean both surfaces after the test run.
