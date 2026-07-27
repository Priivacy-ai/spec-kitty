# Tracer: tooling friction

Append friction encountered during the mission; assess at close (feeds the next mission).

- **[specify]** Personal adversarial gate workflow `~/.claude/workflows/spec-kitty-gate.mjs`
  no-op'd on every point-cut: this harness passes `args` to the workflow script as a
  JSON **string**, but the script did object access (`args.mission`), hitting the
  `missing mission` guard with 0 agents. Fixed with a 12-line string-normalization
  prefix. Root cause is the harness/script `args` type contract, not the mission.
- **[specify/plan]** `uv run python -m pytest` rebuilds the editable package (~75s per
  invocation), making red/green iteration slow; `.venv/bin/python -m pytest -o addopts=""`
  runs the same test in ~44s without the rebuild. Documented in quickstart.
- **[plan]** `setup-plan` post-plan point-cut hook fires immediately on the (blocked)
  scaffold `plan.md`, before the plan is authored — the gate must be deferred until the
  plan is substantive + committed.
- **[implement]** `record-analysis` and `merge` both refuse on a pre-existing dirty tree.
  The untracked `.kittify/doctrine/*` + `charter/provenance/` artifacts (present at session
  start, unrelated to this mission) tripped `record-analysis` → parked with
  `git stash -u`, recorded, popped. `merge` tripped on tracked mission-bookkeeping edits
  (`meta.json`/`tasks.md`/WP frontmatter from mark-status/move-task) → commit + `--resume`.
- **[merge]** The squash-merge of the mission branch reverted `issue-matrix.md` to its
  unfilled template (the mission branch predated the fix-branch fill commit) — had to
  re-fill + re-commit on the fix branch post-merge. Fill the matrix on the coordination
  branch (or expect a post-merge re-fill).
