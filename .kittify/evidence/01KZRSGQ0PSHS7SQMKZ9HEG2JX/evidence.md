# WP02 planning-gap feedback

Canonical mission `worktree-owned-root-3328-01KZRG01`, WP02.

The initial RED established the new CLI contract: three real-git tests failed
because `--owned-checkout` did not exist (3 failed, 44 deselected, 122.64s;
`/tmp/core-3328-wp02-red.txt`, SHA256
`1b4f33d065d3570b89920a4a40dd1510c5d49f79f1b6a7b1387c6c5578e36a2f`).

The partial owned-surface implementation makes structured nested and foreign
refusals green, but the real linked-checkout success test remains red:

```text
assert safe_commit.call_args.kwargs["target"].ref == "owned-mission"
AssertionError: assert 'main' == 'owned-mission'
1 failed, 2 passed, 44 deselected in 47.76s
```

Root cause: the existing `placement_seam(primary, new_mission).write_target(SPEC)`
cannot read `meta.json` that intentionally exists only in the explicitly owned
linked checkout. Before the new mission identity has a primary-readable home,
the seam therefore falls back to the primary branch (`main`). Passing that
target with `worktree_root=<linked checkout>` would fail `safe_commit`'s HEAD
assertion and cannot satisfy FR-008/FR-009.

Required amendment before implementation resumes:

1. Define one canonical `mission_runtime` create-time target seam for the
   pre-readable-identity bootstrap. Its input is the explicit planning branch
   selected from the validated owned checkout; it must not read ambient CWD or
   bypass topology validation.
2. Add the seam's implementation/export files to WP02 ownership and document
   the bootstrap boundary in plan/contracts/tasks.
3. Keep the default no-opt-in path on the existing
   `placement_seam(...).write_target(SPEC)` path byte-for-byte.
4. Re-finalize tasks and rerun analysis before reclaiming WP02.

No further production edits are authorized until planner-priti amends and
reanalyzes the mission.
