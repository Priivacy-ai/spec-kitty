---
work_package_id: WP01
title: Narrow census freshness gate to membership + live-floor (drop exact LOC)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
tracker_refs:
- '2416'
planning_base_branch: fix/census-freshness-loc-insensitive
merge_target_branch: fix/census-freshness-loc-insensitive
branch_strategy: Planning artifacts for this mission were generated on fix/census-freshness-loc-insensitive. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/census-freshness-loc-insensitive unless the human explicitly redirects the landing branch.
created_at: '2026-07-06T10:06:04+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Fix
assignee: ''
agent: "claude"
shell_pid: "2370219"
history:
- at: '2026-07-06T10:06:04Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/_gate_coverage.py
- tests/architectural/test_ci_topology_worklist.py
- tests/architectural/ci_topology_census.json
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Narrow census freshness gate to membership + live-floor

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objective

Fix issue [#2416](https://github.com/Priivacy-ai/spec-kitty/issues/2416): the CI-topology
census freshness gate reds unrelated PRs on exact line-count churn. Narrow the gate to
compare **dir-membership + committed routing plan** (order- and LOC-insensitive), drop
exact `loc` at the **shared derivation** (`live_derived_worklist`), and re-anchor the LOC
floor to the **live** tree. Preserve every anti-tamper tooth (hand-trim, floor-crossing,
new-hot-dir) plus order-insensitivity, all proven by non-vacuous self-mutation tests.

**Zero `src/` changes** — the entire change is three files under `tests/architectural/`.

## Context (read these first)

- `kitty-specs/census-freshness-loc-insensitive-01KWVD6Y/spec.md` — FR/NFR/C + SC-001..SC-007.
- `kitty-specs/census-freshness-loc-insensitive-01KWVD6Y/research.md` — decision + reproduction.
- `kitty-specs/census-freshness-loc-insensitive-01KWVD6Y/data-model.md` — census entry before/after.
- Live surfaces: `tests/architectural/_gate_coverage.py` (`live_derived_worklist` @ ~933,
  `src_package_loc` @ ~916, `build_census` @ ~1230, `_emit_census`, `_verify_census`,
  `T_LOC=500`, `CENSUS_PATH`), `tests/architectural/test_ci_topology_worklist.py`,
  `tests/architectural/ci_topology_census.json`.

## Iteration mechanics

Run tests with the venv python to skip the ~75s `uv run` editable rebuild:
```bash
PWHEADLESS=1 .venv/bin/python -m pytest tests/architectural/test_ci_topology_worklist.py \
  -p no:cacheprovider -q -o addopts=""
```
Regenerate the census (only when T002 is done) with the module entry point:
```bash
uv run python -m tests.architectural._gate_coverage --emit-census
```

## Subtasks & Detailed Guidance

### T001 — ATDD red-first: rank-altering LOC churn stays green (COMMIT ALONE, FIRST)

**This is the ATDD contract commit (charter C-011). It MUST be committed before any
implementation change and MUST be RED on the base branch.**

Add to `test_ci_topology_worklist.py`. It must use ONLY pre-existing symbols so it is a
clean assertion-RED on base (not an import error):

```python
def test_rank_altering_loc_churn_keeps_gate_green(
    monkeypatch: pytest.MonkeyPatch,
    census: dict[str, Any],
) -> None:
    """FR-001 + FR-007 (red-first): a LOC churn that flips the relative LOC rank of two
    adjacent worklist members — pure churn, no membership/routing change — must keep the
    freshness gate green. RED on base (ordered list-equality compares exact loc + order);
    GREEN after the loc-drop + dir-keyed index compare. Issue #2416."""
    real = gc.src_package_loc()
    a, b = "tracker", "doctrine"  # two worklist members; swap flips their -loc rank
    live_dirs = {e["dir"] for e in gc.live_derived_worklist()}
    assert {a, b} <= live_dirs, "chosen pair must both be worklist members"
    assert a in real and b in real and real[a] != real[b]
    swapped = {**real, a: real[b], b: real[a]}
    monkeypatch.setattr(gc, "src_package_loc", lambda *args, **kw: swapped)
    # On the fixed code this compares membership + routing only (order/LOC-insensitive).
    assert census["worklist"] == gc.live_derived_worklist()
```

Verify RED on base: `git stash` any impl, run just this test → it must FAIL with a
list-inequality. Commit message: `test(#2416): red-first rank-altering LOC churn stays green (FR-001/FR-007)`.

> NOTE: this test asserts `census["worklist"] == gc.live_derived_worklist()`. After T002
> the committed census (T006 regen) and live derivation are both loc-free and dir-sorted,
> so the swap changes neither → GREEN. If you later prefer the index form, that is fine —
> but keep at least one red-first test that is RED on base via a pre-existing entry point.

### T002 — Derivation fix in `_gate_coverage.py` (drop loc; add index helper)

1. Add a pure helper (place near `live_derived_worklist`):
```python
def worklist_routing_index(
    entries: Sequence[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Dir-keyed routing index for the freshness guard (order/LOC-insensitive, #2416).

    Only membership (the dir keys) and the committed routing plan (cone_roots /
    target_group / target_shard) participate, so a pure line-count change or a LOC
    rank-swap between two members does not red the freshness gate. Exact LOC and list
    order are deliberately excluded — every anti-tamper tooth is a membership or routing
    change, which this index captures.
    """
    return {
        str(entry["dir"]): {
            "cone_roots": list(entry.get("cone_roots", [])),
            "target_group": entry.get("target_group"),
            "target_shard": entry.get("target_shard"),
        }
        for entry in entries
    }
```
2. In `live_derived_worklist`: stop emitting `loc`, and sort by `dir` (LOC-independent,
   diff-stable). `loc` is still read internally for the membership floor:
```python
        group, shard, cones = _COMPOSITE_ROUTING.get(dir_name, _EMPTY_ROUTING)
        worklist.append(
            {
                "dir": dir_name,
                "cone_roots": list(cones),
                "target_group": group,
                "target_shard": shard,
            },
        )
    worklist.sort(key=lambda entry: str(entry["dir"]))
    return worklist
```
3. Update the `live_derived_worklist` docstring: note `loc` is no longer emitted (#2416),
   the fix is at this shared derivation so `--verify-census` is fixed by construction, and
   membership is still floor-gated on live LOC.
4. `Sequence` is already imported under `TYPE_CHECKING`; keep mypy `--strict` clean (no
   `# type: ignore`). `build_census`/`_emit_census`/`_verify_census` consume this function
   unchanged and inherit the loc-drop — do NOT add a second comparison authority.

### T003 — Rewrite the freshness test to the dir-keyed index compare

Replace the body of `test_census_worklist_matches_live_derivation`:
```python
def test_census_worklist_matches_live_derivation(census: dict[str, Any]) -> None:
    """NFR-006 freshness guard: census worklist matches live re-derivation on
    membership + committed routing plan (order/LOC-insensitive, issue #2416). Exact LOC
    is no longer compared — a stale/hand-trimmed census still reds because trimming a
    dir, a floor-crossing, a new hot dir, or a routing hand-edit all change this index."""
    assert gc.worklist_routing_index(census["worklist"]) == gc.worklist_routing_index(
        gc.live_derived_worklist(),
    )
```

### T004 — Re-point the meets-floor test to LIVE LOC (FR-006)

The committed entries no longer carry `loc`, so read the floor from the live tree
(strictly stronger than a snapshot):
```python
def test_every_worklist_dir_meets_loc_floor(
    census: dict[str, Any],
    worklist: list[dict[str, Any]],
) -> None:
    """Each committed worklist dir clears the committed t_loc floor, checked against the
    LIVE source tree (not a stored snapshot) — FR-006."""
    t_loc = census["t_loc"]
    assert isinstance(t_loc, int)
    loc_by_dir = gc.src_package_loc()
    for entry in worklist:
        live_loc = loc_by_dir.get(entry["dir"], 0)
        assert live_loc >= t_loc, (
            f"{entry['dir']} live LOC {live_loc} < committed floor {t_loc}"
        )
```

### T005 — Non-vacuous self-mutation teeth (FR-002..FR-005, NFR-004, C-004) + durable C-001 no-loc guard

Add five tests. The four teeth MUST call the real `gc.worklist_routing_index` /
`gc.live_derived_worklist` (no private shadow comparator), or they are vacuous. The fifth
(`test_committed_census_carries_no_loc`) durably enforces C-001 independent of the
freshness test's shape (post-tasks gate fold):
```python
def test_freshness_index_reds_on_hand_trim() -> None:
    """FR-002: dropping a still-qualifying dir from the census reds the gate."""
    live = gc.live_derived_worklist()
    assert live, "worklist unexpectedly empty"
    trimmed = live[1:]
    assert gc.worklist_routing_index(trimmed) != gc.worklist_routing_index(live)

def test_freshness_index_reds_on_phantom_dir() -> None:
    """FR-004: a new hot dir absent from the census reds the gate."""
    live = gc.live_derived_worklist()
    phantom = [*live, {"dir": "zzz_phantom", "cone_roots": [],
                       "target_group": "x", "target_shard": "y"}]
    assert gc.worklist_routing_index(phantom) != gc.worklist_routing_index(live)

def test_freshness_index_reds_on_routing_edit() -> None:
    """FR-005: a hand-edited routing target reds the gate."""
    live = gc.live_derived_worklist()
    assert live, "worklist unexpectedly empty"
    tampered = [dict(e) for e in live]
    tampered[0] = {**tampered[0], "target_group": "WRONG_GROUP"}
    assert gc.worklist_routing_index(tampered) != gc.worklist_routing_index(live)

def test_freshness_index_reds_on_floor_crossing() -> None:
    """FR-003: a dir dropping below the floor leaves the live worklist; a census that
    still lists it reds. Dynamic raised floor t_high = min(member loc) + 1 guarantees at
    least one member leaves (non-vacuous, drift-proof — post-plan gate D6)."""
    members = gc.live_derived_worklist()
    loc_by_dir = gc.src_package_loc()
    t_high = min(loc_by_dir[e["dir"]] for e in members) + 1
    fewer = gc.live_derived_worklist(t_loc=t_high)
    assert gc.worklist_routing_index(fewer) != gc.worklist_routing_index(members)


def test_committed_census_carries_no_loc(census: dict[str, Any]) -> None:
    """C-001 (durable, shape-independent): the committed census worklist stores NO exact
    `loc`. Enforced directly here — NOT incidentally via a freshness test that is
    loc-blind after T003 — so a skipped/forgotten regen (or a future reintroduction of
    the field) reds regardless of the freshness test's shape. Post-tasks gate fold."""
    stale = [e["dir"] for e in census["worklist"] if "loc" in e]
    assert not stale, f"committed census entries still carry exact loc: {stale}"
```

### T006 — Regenerate the census (MANDATORY — do not hand-edit)

```bash
uv run python -m tests.architectural._gate_coverage --emit-census
```
Confirm the diff on `ci_topology_census.json` only **removes** `loc` keys from worklist
entries (and re-orders them alphabetically by `dir`). `mapped_dirs`, `arch_blind_groups`,
`t_loc`, `timings_baseline` are unchanged. `arch_blind_groups` stays `[]` (out of scope).

### T007 — Validate

```bash
PWHEADLESS=1 .venv/bin/python -m pytest tests/architectural/test_ci_topology_worklist.py -p no:cacheprovider -q -o addopts=""
ruff check tests/architectural/_gate_coverage.py tests/architectural/test_ci_topology_worklist.py
mypy tests/architectural/_gate_coverage.py
git diff --name-only   # MUST list no path under src/
```
Also confirm the SC-001 reproduction stays green: add `printf '# p\n\n\n' > src/specify_cli/bulk_edit/_zzz.py`, re-run the freshness test (GREEN), then `rm` the probe.

## Branch Strategy

- **Planning base branch**: `fix/census-freshness-loc-insensitive`
- **Final merge target**: `fix/census-freshness-loc-insensitive` (then cross-fork PR → `Priivacy-ai:main`)
- Execution worktrees are allocated per computed lane from `lanes.json`; do not reconstruct paths.

## Definition of Done

- [ ] T001 committed alone, verified RED on base, GREEN after the fix.
- [ ] `loc` dropped from `live_derived_worklist` entries; `worklist_routing_index` added; sorted by `dir`.
- [ ] Freshness test compares the dir-keyed index; meets-floor test uses live LOC.
- [ ] Four teeth tests present, each exercising the real helper/derivation; all pass.
- [ ] `test_committed_census_carries_no_loc` present (durable C-001 guard, shape-independent).
- [ ] Census regenerated via `--emit-census`; diff only removes `loc` keys.
- [ ] Targeted `tests/architectural/` green; `ruff` + `mypy --strict` clean, zero new suppressions.
- [ ] `git diff --name-only` lists no `src/` path (NFR-003).
- [ ] SC-001 reproduction (add lines to a worklist dir) stays green.

## Risks & Reviewer Guidance

- **Vacuous teeth**: reject any tooth test that builds its own comparison instead of
  calling `gc.worklist_routing_index` / `gc.live_derived_worklist`.
- **Missing regen**: if T006 is skipped, the committed census keeps stale `loc` keys. The
  loc-blind index freshness test stays GREEN on this **by design** — the dedicated
  `test_committed_census_carries_no_loc` (C-001) is the guard that reds. Do not skip the
  regen or that assertion; check the census diff.
- **Red→green evidence**: reviewer confirms T001 was RED on `fix/census-freshness-loc-insensitive`
  (the base) and GREEN on the final commit.
- **Scope**: any edit outside the three `owned_files` (especially any `src/` change) is a
  scope violation for this mission (NFR-003).
- **Complexity/Sonar**: `worklist_routing_index` is a small pure helper with a focused
  test — keep it that way; no complexity added to `live_derived_worklist`.

## Activity Log

- 2026-07-06T10:44:14Z – claude – shell_pid=2370219 – Assigned agent via action command
