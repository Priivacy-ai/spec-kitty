# Post-plan adversarial squad — findings and dispositions

Point-cut: immediately after `plan`, before `tasks`. Three lenses, parallel, profile-loaded,
read-only, all on `opus`. Question: *is this decomposition real, are the DoDs closable without
doing the work, and does the approach survive contact with the codebase?*

| Lens | Profile | Verdict |
|---|---|---|
| Decomposition / boundaries | `paula-patterns` | BLOCK |
| Anti-laziness / fakeable DoDs | `reviewer-renata` | REQUEST CHANGES (blocking) |
| Implementer feasibility | `python-pedro` | NEEDS-CHANGE |

## The convergent finding — FR-008 cut from scope

**All three lenses independently concluded the "22 duplicate `_isolated_home` fixtures" are a
name collision, not a duplicated seam.** Measured on `bb2020fea9`:

- **Seven incompatible shapes** (`python-pedro`), including three files that pin **no home at
  all** — and those three are the `#3115` victims (`test_sync_status_per_project_3030.py`,
  `test_sync_doctor_per_project_3030.py`, `test_sync_migrate_backfills_h4.py`). A root owner
  pinning `SPEC_KITTY_HOME` would change behaviour in exactly the files WP02/WP03 just fixed.
- **Contradictory env policies.** Two files *set* `SPEC_KITTY_ENABLE_SAAS_SYNC="1"`; thirteen
  *delete* it. Both directions are documented as load-bearing **at the site, in opposite words**
  — `test_body_drain_consent_3030.py:49-52` ("leaving it set here keeps these tests honest about
  what they prove") versus `test_local_commit_consent_3030.py:78-82` ("deleted rather than set…
  leaving the developer's own export in place would prove nothing either way").
- **Five call `reset_coalesce_strategy()`**, which appears **zero times** in the entire mission
  dossier (`reviewer-renata`). A constraint the plan never names is one the WP would not carry.
- **Three fixture contracts** — 14 × `-> None`, 7 × `-> Iterator[None]`, 1 × `-> Path`; and
  `test_identity_value_faults_3030.py:296` is a **class method**, which a root-conftest owner
  cannot replace without changing fixture resolution.
- **The red-first criterion is internally contradictory**: a test asserting the fixture is
  "defined at most once" cannot pass at any M > 1, which `plan.md:541` explicitly allows.
- **The DoD's detector is the wrong instrument.** Collected counts do not move when a fixture
  *body* changes, so a dropped `reset_coalesce_strategy()` or a flipped arming policy is
  invisible — the counted acceptance is satisfiable by deletion that makes isolation strictly
  worse.

**Operator decision: cut FR-008 / WP08 from this mission and file a follow-up issue** carrying
the measured equivalence-class evidence. It is a cross-cutting refactor across five packages;
the mission's other work does not depend on it.

**The successor issue is `#3121`** (OPEN, `Priivacy-ai/spec-kitty`) — *the* handle for the cut
requirement, and until now it survived **only in a commit message** (`d8d0ad7eff`, *"cut FR-008
to #3121"*). Nothing in the dossier recorded it. It is written **here** and in `#3115`'s
`scope` string in `issue-matrix.json`, and **deliberately nowhere else**:
`issue_reference_discovery.py:42-50` scans `spec.md`, `plan.md`, `research.md`,
`analysis-report.md`, `tasks/*.md` and `contracts/*.md` — **`notes/` and `issue-matrix.json` are
not scanned** — so recording it in either of those places keeps the handle findable without
minting a **fourth mandatory matrix row** that this mission cannot resolve and that would then
block `--to done`. **Do not write `#3121` into `plan.md`, `spec.md` or any `tasks/*.md`.**
`#3121` inherits: the seven incompatible fixture shapes, the contradictory env policies, the
five `reset_coalesce_strategy()` callers the plan never named, the three fixture contracts and
the class-method site — plus WP03's sequencing note (**the width guard must precede any such
convergence**, since it is the only guard that would catch a hoist changing the victim files'
render surface). The count stays at **22** for the duration of this mission.

## Mechanical blockers — would have fired before any code was measured

**M1 — the mutant-plugin contract does not work as specified** (`python-pedro`, CRITICAL).
WP02, WP03, WP07 and WP11 all prove red-first by disabling a conftest fixture from a
`scripts/mutants/` plugin. Two independent failures, both probed with a known-answer baseline:
- A same-named autouse fixture in a `-p`-loaded plugin **loses to the conftest fixture** —
  pytest resolves conftest fixtures at higher precedence for items under that directory.
- **`PYTHONPATH` alone does not load a plugin.** The plan says "loaded via `PYTHONPATH`" in five
  places and never mentions `-p <mod>` or `PYTEST_PLUGINS`. A `PYTHONPATH`-only mutant is
  silently inert — the plan committing the rot mode it exists to guard against.

A hook-level plugin works: neutralising at `pytest_configure` produced a named red
(`AssertionError: seam was off`). → **Mutant contract rewritten**: loaded with `-p <module>`
(importable via `PYTHONPATH=scripts/mutants`), neutralising at hook level, never as a
same-named fixture; and the plugin must fail loudly if the symbol it patched was never called.

**M2 — the lane graph is cyclic** (`paula-patterns`, CRITICAL).
`lanes.json` is not written from the plan's hand-authored table; `compute_lanes` derives lanes
from `owned_files` glob overlap only (`compute.py:8-11`). WP02+WP08 share `tests/conftest.py` →
one lane. WP07 owns only a mutant script → a different lane. WP08 blocked by WP07, WP07 blocked
by WP02 → **mutual `depends_on_lanes` edge**: deadlock at dispatch, wrong merge base at
allocation. It would not be caught — `compute.py:624-629` claims cycles are "logged via
`compute_lanes`'s validation" and **no such validation exists** anywhere in
`src/specify_cli/lanes/`. → WP07 moved into the WP02 lane; the cycle disappears, and it matches
the plan's own critical path. (Largely moot now WP08 is cut, but the lane assignment is fixed
explicitly rather than by accident.)

**M3 — `/spec-kitty.tasks` would hard-fail exit 1** (`paula-patterns`, HIGH).
Nine new literal paths are declared in `owned_files` with no `create_intent`;
`validation.py:420-448` treats a literal path with zero repo matches as a hard error
(`mission_finalize.py:1002`). `grep -rn create_intent` over the whole dossier returned nothing.
None are globs, so none degrade to the soft-warning branch. → `create_intent` added to every WP
declaring a new file.

**M4 — WP14's pre-allocation does not produce the lane it claims** (`paula-patterns`, HIGH).
Lane membership is computed *solely* from `owned_files` overlap, so a placeholder with empty
ownership lands in its own singleton lane, not lane-d — and outcome A would then write a file
another lane's worktree owns. → WP14 declares `tests/sync/tracker/test_saas_client.py` at
planning time; outcome B leaves it untouched (an owned file with no diff is legal).

## Feasibility corrections

**F1 — the width pin's blast radius is under-scoped** (`python-pedro`, HIGH).
`CliConsole._instances` holds three deliberately-sized specials — `charter/list_cmd.py:26`
(200), `glossary.py:46` (120), `docs.py:43` (120) — and `docs.py:40-42` states its 120 is
load-bearing. A blanket `size = (W, H)` walk overwrites all three. Two more consoles are
constructed **inside functions** (`helpers.py:234`, `logging_bootstrap.py:92`), i.e. after the
seam's setup-time walk, so FR-003's "non-zero inspected count" passes while they are unpinned.
→ Pin only the singletons or exempt instances constructed with an explicit `width=`; the guard
must assert it saw the *named* singletons, not just a non-zero count, so the per-call consoles
register as a stated gap rather than an invisible one.

**F2 — the three `COLUMNS` sets are not dead outside `TERM=dumb`** (`python-pedro`).
Under `CliRunner` in the default env, `is_terminal` is False, the early return does not fire,
and `COLUMNS` **is** consulted. `test_activation_layout.py:111` passes `COLUMNS=240` and is live
today. → The pinned width must be **≥ 240**, stated as a constraint; the "provably dead"
removal was only safe under the failing path.

**F3 — `pytest-randomly` is not installed** (`python-pedro`, MEDIUM).
Not importable, absent from `pyproject.toml:102-113` and from every workflow. So C-005 forbids a
flag that is already a no-op, and WP01's determinism criterion ("three consecutive runs, same
node-id") is **trivially satisfied because nothing randomises order** — green for the wrong
reason, in the mission built to eliminate that. → C-005 struck; the determinism criterion
replaced with one that can fail.

**F4 — FR-015's tightening is ruled out by arithmetic already taken** (`python-pedro`, MEDIUM).
The structural predicate needs enclosing-scope information `_classify(node: ast.Call)` does not
carry (`:309`, called from a flat `ast.walk` at `:347-350`), so adopting it is a scanner
restructure, not a branch edit. And the measurement was **run**: over `src/`, the minimal rule
catching the adoption-gate case yields **5 false positives** (`resolve_workspace_for_wp`,
`locate_work_package`, `behind_commits_touch_only_planning_artifacts`, `get_wp_lane`), 211 sites
across 13 files in total. By WP10's own DoD, non-zero FPs means the matcher is left alone and
FR-014 lands as two `xfail(strict=True)`. Both outcomes close `#3113`. → WP10 re-ordered so the
`src/`-wide count is taken **first**; the restructure is funded only if it returns zero. The
measured numbers are stated in the brief so the WP does not re-derive them.

## DoD tightenings

- **WP06 was closable with zero test runs** (`renata`, HIGH) — its non-converging branch
  required only self-reported hours and a self-reported mechanism list. → A floor before the
  budget starts: the symptom observed red with its text quoted, or an explicit written statement
  that it could not be reproduced locally with selections tried and collected counts; each
  excluded mechanism carries a *named exclusion measurement*.
- **WP07's aggregate count could mask an inert plugin** (`renata`, HIGH). → Per-site split
  across every name the symbol is reachable by, and a non-zero suppressed count in the run that
  claims the null verdict. **Adjudicated divergence:** `renata` flagged the fifth rot mode;
  `paula` verified all five victim files import `reset_token_manager` **function-locally inside
  the fixture body** (`…doctor_per_project…:62`, `…status…:73`, `…migrate…:57`, `…purge…:83`,
  `…health…:70`), so a plugin patching the defining module binds at all five and the rot mode
  does not bite there. Resolved in `paula`'s favour on the evidence — but `renata`'s ask stands,
  because `tests/auth/integration/conftest.py:22` and `test_websocket_provisioning.py:28` bind
  eagerly via the *package* name and must be reported as deliberately-unpatched, not as zero.
- **WP13 never enumerated the 13 cases it exists to prove** (`renata`, HIGH) — its DoD checks
  only the shard's properties, so a case deselected by the marker or caught by one of the four
  `--ignore`s is invisible, with `|| test $? -eq 5` underneath. → The 13 node-ids enumerated in
  the plan; each outcome quoted from the run's own report; any node-id absent from the collected
  set named and explained; an explicit clause for naming a deferred case as an exclusion.
- **WP05's probe contradicted its own FR** (`renata`, MEDIUM) — FR-007 forbids a purpose-written
  file satisfying the criterion by construction, and the plan named exactly that. → Either bite
  a real inventoried leak from WP04, or record the synthetic-bite limitation in WP10's exact
  voice. The designated control-your-diagnostic case must be run first.
- **WP03's fold proof lacked provenance and an in-file positive anchor** (`renata`, MEDIUM). →
  Captures carry command, commit, environment and observed `Console.size`; the test asserts both
  uuid fragments *are* present, that their concatenation equals the uuid, and that the
  interleaved character count is > 0.
- **Three WPs will close on `no_coverage — skipping the gate cheaply`** (`paula`, MEDIUM) —
  WP07, WP13 and WP14-outcome-B, by design, since their `owned_files` map to zero test targets.
  Pre-allocation closes only one of the two paths to that outcome
  (`tasks_move_task.py:937-962` vs `:965-980`). → Each states in its transition note that the
  printed line is expected and names the manual evidence standing in for it.
- **WP03 must precede the convergence it is the only guard for** (`paula`, MEDIUM). Moot with
  FR-008 cut; recorded because the follow-up issue inherits it.

## Verified, and worth carrying

- **`pytest-timeout`'s `signal` method works under `xdist` on Linux** (`python-pedro`): probed
  at `--timeout=3 --timeout-method=signal -n 2` → `Failed: Timeout (>3.0s) from pytest-timeout`,
  named red, real summary, correct elapsed. Caveat: the run also emitted an `execnet
  gateway_base._thread_receiver` traceback, so the evidence must quote the **summary line**, not
  "the output was clean". `ci-windows.yml` still needs its own statement — `SIGALRM` is
  genuinely absent there.
- **The `scripts/mutants/` placement rationale is sound** (both lenses): `tests/conftest.py:245-250`'s
  `_fail_on_wall_clock_assertions` walks the whole `tests/` tree at collection and raises
  `pytest.UsageError`.
- **The width diagnosis holds under an independent probe** (`python-pedro`): unpinned singleton
  under `TERM=dumb` → `(80, 25)`, uuid not contiguous; `width` only → still `(80, 25)`;
  `width+height` → `(220, 50)`, uuid contiguous. And `sync.py:1932` prints through the `console`
  singleton, so the seam **does** reach the right object.
- **The sequential `tests/conftest.py` handoff is safe** — `paula` withdrew her own opening
  framing on the evidence: `validation.py:198-205` explicitly exempts dependency-ordered pairs,
  and `worktree_allocator.py:32-33` raises `DirtyWorktreeError` on handoff with uncommitted
  changes. The `git add -A` incident was *concurrent* implementers in one tree, not a sequential
  handoff.
- **`xfail_strict` really is unavailable** — `pytest.ini` has none and `pyproject.toml:183-192`
  forbids a `[tool.pytest.ini_options]` block, so per-`xfail` `strict=True` is the only lever.
  The plan was right.
