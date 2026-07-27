# Tooling Friction Log

> Log every place the tooling fought you so it can feed the tooling-gap backlog.

**Prompting questions**
- What tooling or command did you have to work around?
- What blocked you unexpectedly, and how long did it take to unblock?
- Was this a known issue or something discovered fresh?

**Mission tooling surface**: `spec-kitty` CLI (mission create / spec-commit / setup-plan /
implement / move-task / accept / merge), coordination topology worktrees, the acceptance and
merge gates this mission is repairing, `uv run --extra test pytest`, the architectural suite,
and the GitHub tracker. Note this mission runs on **coord topology deliberately**, so friction
from the defects under repair is expected and is itself evidence.

---

## Entries

2026-07-23 — WP01 tracer-placement friction (lane worktree cannot hold mission artifacts).
The WP01 prompt directs the implementer to write mission artifacts (the T001 `nfr005-baseline.md`
and appended `design-decisions.md` entries) "under the mission dir", but the implementer is
**confined to the lane-a worktree** and forbidden from editing the primary/coord worktrees.
Writing the tracers in the lane worktree lands them on the LANE branch, and `move-task
--to for_review` then **refuses**: "kitty-specs/ changes are not allowed on lane branches —
planning artifacts must live on `remediation/coord-lifecycle-gates`". There is no
implementer-available seam to route a mission-dir write from a confined lane onto the planning
branch (C-009 also forbids hand-committing into the coord tree). Workaround: the code
deliverables (`ref_advance.py` + the regression test) are committed on the lane branch; the
tracer files are left **uncommitted** in the lane working tree (move-task tolerates them as
"unrelated dirty files"). Consequence: the T001 baseline + design-decision evidence exist on
disk in the lane worktree but are NOT version-controlled from the lane — they need migrating to
`remediation/coord-lifecycle-gates` by the coordinator/operator (or a planning-artifact commit
seam the implementer can invoke). This is exactly the confined-lane / mission-artifact placement
gap the mission's coord-topology dogfooding is meant to surface.

2026-07-23 — `mission create --pr-bound` wrote `pr_bound: true` into `meta.json` and left it
uncommitted; the tree was dirty with tool-authored metadata within minutes of mission start.
This is the exact shape #2795 describes (tool metadata written at a lifecycle step, never
committed) and became corroborating evidence for IC-01 rather than a mere annoyance.

2026-07-23 — `spec-kitty spec-commit` refused a **directory** argument (`.../contracts`) with a
truncated backstop message mentioning `git checkout HEAD -- <unexpected-paths>` and "cannot be
bypassed by --force". The same files listed explicitly committed without complaint. Cost ~2
minutes. Minor papercut; not filed — revisit only if it recurs or the message misleads someone
into running the suggested `git checkout`, which would destroy uncommitted work.

2026-07-23 — Doctrine inconsistency: `mission-tracer-files.procedure.yaml` step 1 says to create
`traces/`, but all five existing missions carrying tracers use `tracers/`. Followed the
five-mission precedent. The procedure text should be corrected to match, or the two spellings
will keep diverging.

2026-07-23 — `tests/architectural/test_tid251_enforcement.py` (4 tests) fails locally in this
clone with `.venv/bin/python: No module named ruff`. Ruff resolves fine via `uv run ruff`
(0.15.14) but is not pip-installed into the clone's `.venv`, and the test shells out to
`python -m ruff`. Environmental, not diff-caused — the file has zero references to anything
under change. Will recur for every WP run locally; classify against it rather than
re-diagnosing each time.

2026-07-23 — `scripts/docs/freshen_adr_inventory.py` and `scripts/docs/docs_index.py` both need
`PYTHONPATH=.` to run, while `docs/adr/3.x/README.md` documents the bare invocation, which dies
with `ModuleNotFoundError: No module named 'scripts'`. The freshening script also does not
refresh the docs-retrieval index, so following the README exactly still leaves
`check_docs_freshness --ci` red with `DOCS-INDEX-DRIFT`. Filed as #2887.

2026-07-23 — **Mission bootstrap was broken from creation, and nobody noticed for a full
planning cycle.** `mission create` wrote `coordination_branch` into `meta.json` and created the
branch, but never materialised the coord worktree — so the mission ran spec, plan, and two squad
cycles with its coord surface absent. Consequences observed: `status.events.jsonl` sat **untracked
on the primary tree** for the whole period (a STATUS_STATE artifact on the wrong partition — a
live instance of the split-brain this mission repairs), and the coord branch stayed pinned at
`eb06ca176` while primary advanced through two rebases and 18 commits.

Found by a decomposition-readiness audit, not by the loop. `spec-kitty doctor coordination`
detects it and prints the exact remediation — but nothing runs that doctor automatically at any
point in the mission lifecycle, so the detector existed and never fired. Repaired with the
doctor's own recommended command (`git worktree add`). The base divergence between coord and
primary is left as-is; it is the #2367 adjacent condition and will be re-examined at consolidation.

Evidence for C-009 and for the mission's own thesis: a gate that exists but is never invoked is
indistinguishable from a gate that does not exist.
