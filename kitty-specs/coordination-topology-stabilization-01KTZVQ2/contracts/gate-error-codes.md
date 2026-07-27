# Gate Error Codes Contract

## MISSION_NOT_FOUND (new, IC-05)

**Trigger**: `spec-kitty next --mission <handle>` where `<handle>` resolves to no known mission.

**Exit code**: 1

**Human output** (stderr):
```
Error: Mission not found: '<handle>'
No mission matching '<handle>' exists in this repository.
Run 'spec-kitty mission list' to see available missions.
```

**JSON output** (stdout):
```json
{
  "result": "error",
  "error_code": "MISSION_NOT_FOUND",
  "handle": "<handle>",
  "remediation": "Run 'spec-kitty mission list' to see available missions."
}
```

**Replaces**: `{"result": "success", "state": "unknown", ...}` (exit 0) — the current broken behavior.

---

## SafeCommitPathPolicyError (new, IC-02)

**Trigger**: `safe_commit` receives a requested path under `.worktrees/`.

**Exit code**: 1

**Message**: `safe_commit: refusing to stage path under .worktrees/: <path>. Planning artifacts must be committed from the coordination worktree, not the primary repo root.`

---

## is_committed() — Coordination-Aware Gate Contract (IC-01)

**When coordination topology active**: Returns True if the file is present at `git cat-file -e <coord_ref>:<rel>` OR at `git cat-file -e HEAD:<rel>`.

**When flat topology**: Returns True if the file is present at `git cat-file -e HEAD:<rel>` (existing behavior, unchanged).

**False-positive risk**: None — OR logic means a file committed to either branch is considered committed.

**False-negative risk**: None — if coordination branch doesn't exist, falls back to primary HEAD as before.

---

## RetrospectiveSkipped event (IC-08)

**When emitted**: `spec-kitty merge` completes and `kitty-specs/<slug>/retrospective.yaml` does not exist.

**Schema**: See `data-model.md` section 6.

**Invariant enforcement**: Downstream `spec-kitty doctor` checks that every merged mission has either `retrospective.yaml` or a `retrospective.skipped` event.
