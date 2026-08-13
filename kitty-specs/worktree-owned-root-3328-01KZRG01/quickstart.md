# Quickstart: Verifying Worktree-Owned Root for Mission Create/Next

**Mission**: `worktree-owned-root-3328-01KZRG01` | **Issue**: [#3328](https://github.com/Priivacy-ai/spec-kitty/issues/3328)

This walkthrough is the manual/scripted verification path a reviewer or CI job runs once the implementation WPs land. It mirrors the automated ATDD scenario (IC-06) at a level a human can follow and re-run by hand.

## Prerequisites

- An immutable, installed build of `spec-kitty` (built wheel, installed into a throwaway virtualenv) — **never** an editable (`pip install -e .`) install (C-004). Record the wheel's SHA-256 and the source commit it was built from.
- A scratch clone of the target repository (not this development checkout) to avoid polluting real mission state.

## Steps

1. **Build the immutable artifact.**

   ```bash
   python -m build --wheel
   sha256sum dist/spec_kitty_cli-*.whl
   python -m venv /tmp/spk-verify-venv
   /tmp/spk-verify-venv/bin/pip install dist/spec_kitty_cli-*.whl
   ```

2. **Set up two real linked worktrees at generic (non-`.worktrees`) paths.**

   ```bash
   cd /tmp/scratch-repo
   git worktree add /tmp/spk-verify-agent-a some-base-branch-a
   git worktree add /tmp/spk-verify-agent-b some-base-branch-b
   ```

3. **From worktree A, create a mission with explicit ownership.**

   ```bash
   cd /tmp/spk-verify-agent-a
   /tmp/spk-verify-venv/bin/spec-kitty agent mission create verify-a \
     --owned-checkout /tmp/spk-verify-agent-a --json
   ```

   Expect: success payload naming `/tmp/spk-verify-agent-a` as `owned_checkout`. `git status --short` in `/tmp/scratch-repo` (primary) and `/tmp/spk-verify-agent-b` must both remain clean.

4. **From worktree B, concurrently create a distinct mission.**

   Run step 3's equivalent for worktree B (`verify-b`, `--owned-checkout /tmp/spk-verify-agent-b`) with process start times forced to overlap step 3 (e.g., launch both via `&` and a shared start barrier, or a short `sleep` before each does its first git write).

   Expect: two distinct mission IDs/slugs; two distinct coordination/lane refs; no file or ref from A appears in B's worktree, the primary checkout, or vice versa.

5. **Advance both missions with `next` using the same ownership declaration.**

   ```bash
   cd /tmp/spk-verify-agent-a
   /tmp/spk-verify-venv/bin/spec-kitty next --agent claude --mission verify-a \
     --owned-checkout /tmp/spk-verify-agent-a --result success --json
   ```

   Expect: the decision resolves against worktree A's own `.kittify/runtime/` (inspect `feature-runs.json`-equivalent under `/tmp/spk-verify-agent-a/.kittify/runtime/`) — not the primary checkout's.

6. **Verify no leaked locks or ref collisions after both processes exit.**

   ```bash
   find "$(git -C /tmp/scratch-repo rev-parse --git-common-dir)/spec-kitty-locks" -type f
   git -C /tmp/scratch-repo for-each-ref | grep -E 'verify-a|verify-b'
   ```

   Expect: no stale lock file; ref names for A and B are disjoint; neither overwrote the other.

7. **Verify negative/refusal cases.**

   ```bash
   # Nested worktree
   git -C /tmp/spk-verify-agent-a worktree add /tmp/spk-verify-agent-a/nested some-branch
   cd /tmp/spk-verify-agent-a/nested
   /tmp/spk-verify-venv/bin/spec-kitty agent mission create verify-nested \
     --owned-checkout /tmp/spk-verify-agent-a/nested --json
   # Expect error_code == "OWNERSHIP_NESTED"

   # Foreign repository
   git init /tmp/spk-verify-foreign
   cd /tmp/spk-verify-foreign
   /tmp/spk-verify-venv/bin/spec-kitty agent mission create verify-foreign \
     --owned-checkout /tmp/spk-verify-foreign --json
   # Expect error_code == "OWNERSHIP_FOREIGN"

   # No opt-in from a worktree — unchanged default refusal
   cd /tmp/spk-verify-agent-a
   /tmp/spk-verify-venv/bin/spec-kitty agent mission create verify-default --json
   # Expect the existing "Cannot create missions from inside a worktree" refusal, unchanged
   ```

8. **Confirm all trees are clean at the end.**

   ```bash
   for d in /tmp/scratch-repo /tmp/spk-verify-agent-a /tmp/spk-verify-agent-b; do
     echo "== $d =="; git -C "$d" status --short
   done
   ```

   Expect: clean (empty) output for every tree except the intended committed mission artifacts.

## Success Criteria Mapping

| Quickstart step | spec.md success criterion |
|---|---|
| 3, 8 | SC-001 |
| 3, 4, 6 | SC-002 |
| 7 (no-opt-in case) | SC-003 |
| 7 (nested/foreign cases) | SC-004 |
| 1 | SC-005 |
