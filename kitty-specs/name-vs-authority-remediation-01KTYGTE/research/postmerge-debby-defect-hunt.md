# Post-Merge Adversarial Defect Hunt — name-vs-authority-remediation-01KTYGTE (mission #132)

**Profile:** debugger-debbie · **Mode:** bounded adversarial defect hunt (read-only; no src/test edits; no commit)
**Tree:** branch `feat/name-vs-authority-remediation-01KTYGTE` @ merged HEAD `4c028ebf8`
**Budget:** ~25 min, ≤4 hypotheses to ground, targeted tests only. All four targets pursued; one OPEN thread recorded.

---

## Findings table

| # | Finding | Severity | Fix-before-PR or ticket | Evidence |
|---|---------|----------|-------------------------|----------|
| F-1 | **Dual-era asymmetry in the branch-identity seam.** `resolve_transaction_mid8` RAISES `BranchIdentityUnresolved` for a **legacy `NNN-` slug** mission with `coordination_branch` declared but no `mission_id`/`mid8` in meta — while the sibling `mission_branch_name_required` treats the same legacy `NNN-` slug as RESOLVABLE. The function's own docstring asserts "both eras resolve". | **MEDIUM** | **Ticket** (fix-before-broad-release; not PR-blocking) | Probe below |
| F-2 | **Cross-WP topology divergence: `status_transition.py` vs `aggregate.py` on a husk.** `aggregate.py` (WP05) routes coord-topology through the registry-backed `is_registered_coord_worktree`; `status_transition.py:_is_coord_worktree_feature_dir` (used in `_resolve_transaction_anchor._fallback`) still uses raw **path-shape**. They disagree on a husk (`<slug>-coord` path present, NOT git-registered). | **LOW** | **Ticket** (documented residual; finish migration when C-002 lifts) | Confined to the no-meta `FileNotFoundError` fallback; explicitly allowlisted in the ratchet (C-002 deferral) |
| F-3 | **Accept-gate exclusion vs coord topology.** No defect. In the canonical layout `.worktrees/` is gitignored, so `git status --porcelain` from the primary cwd never emits coord-worktree accept-owned artifacts; the `relative_to` `ValueError`-skip at `acceptance/__init__.py:564-567` is harmless. The exclusion scope and the snapshot scope are consistent. | **NOISE** | none | Probe below |
| F-4 | **The 3 post-merge stale-assertion flags are analyzer noise.** `test_migration_python_only_unit.py:121`, `test_op_record_schema_v2_migration.py:335`, `test_upgrade_auto_commit_unit.py:94` assert `reason == ""` / empty-string returns from **unrelated** migration/upgrade `can_apply` + `_is_upgrade_commit_eligible` code — nothing to do with `status_transition.py:265` or the removed `+"00000000"` idiom. The analyzer matched on the `""` literal heuristically. | **NOISE** | none | All 81 tests in the 3 files pass |
| F-5 (OPEN) | **`.worktrees/` ungitignored edge.** If a consumer project fails to gitignore `.worktrees/`, accept on a coord mission trips on `?? .worktrees/` (dir-level porcelain entry) which the per-file accept-owned exclusion can never match. Pre-existing misconfiguration, not introduced by this mission. Not pursued to ground (out of mission scope). | **LOW (OPEN)** | note only | `git status --porcelain` emits `?? .worktrees/` when not ignored |

---

## Evidence

### F-1 — branch-identity dual-era asymmetry (the operational regression risk, hunt target #2)

`resolve_transaction_mid8` (`lanes/branch_naming.py:235-308`) raises only when the mid8 cascade is exhausted **AND** `coordination_branch` is truthy. The cascade is: explicit `mid8` → `mission_id[:8]` → `mid8_from_slug(slug)`. A legacy `NNN-` slug has no mid8 tail, so for an unmigrated legacy mission (no `mission_id`/`mid8` in meta) with a declared `coordination_branch`, the cascade exhausts and it RAISES:

```
A modern-flattened (coord stale + mission_id): '01KTYGTE'        # OK — mission_id present
B slug-mid8-tail   (coord stale, no mid8/id):  '01KTYGTE'        # OK — slug tail
C legacy-NNN slug  (coord stale):              RAISES BRANCH_IDENTITY_UNRESOLVED   # <-- asymmetry
D bare slug        (coord stale):              RAISES BRANCH_IDENTITY_UNRESOLVED   # intended
```

Asymmetry vs the sibling seam fn, same legacy slug, `mission_id=None`:
```
mission_branch_name_required('083-legacy-feature', None) -> 'kitty/mission-083-legacy-feature'   # RESOLVES
resolve_transaction_mid8('083-legacy-feature', ..., coordination_branch='x') -> RAISES            # DIVERGES
```

`mission_branch_name_required` (line 230) gives legacy `NNN-` an explicit resolvable branch (`_NUMERIC_PREFIX_RE.match(...) → legacy compose`). `resolve_transaction_mid8` has **no equivalent NNN- branch** — once `mid8`/`mission_id`/slug-tail miss, the only escape is "no coord_branch → return ''". So a legacy coord mission raises.

**Reachability:** `_identity_for_request` (`status_transition.py:228`) calls `resolve_transaction_mid8` **unconditionally** at line 269 with `mission_id` taken straight from meta — no topology guard precedes it; it derives `mid8 = mission_id[:8]` only when `mission_id` exists (line 261-262). So the raise needs an **unmigrated legacy mission (no `mission_id`) that still carries `coordination_branch`** doing any routine status transition (claim, done-recording, etc.) → the call propagates `BranchIdentityUnresolved` and wedges the transition. This is exactly the "stale `coordination_branch` flatten gotcha" population the mission and `spec-kitty doctor identity` target.

**Why MEDIUM not BLOCKING:** post-083 + backfilled repos always have `mission_id`, so the raise is dormant for them; it bites only an unmigrated legacy + coord-topology mission. But it contradicts the binding dual-era rule (FR-006: "legacy `\d{3}-` AND mid8-era names both RESOLVE; only the unresolvable case rejects") and the function's own docstring. **Recommended fix:** mirror `mission_branch_name_required`'s legacy carve-out — treat `_NUMERIC_PREFIX_RE.match(mission_slug)` as resolvable (route to bare-slug/legacy surface, return `""`) before the coord-branch raise. **Ticket it** with a pinning test (`legacy NNN- + coordination_branch → resolves, not raises`). No such test exists today (`grep resolve_transaction_mid8 tests/` → only the ratchet references it, none assert the NNN+coord case).

### F-3 — accept-gate exclusion vs coord topology (hunt target #3)

`_resolve_git_context` runs `git_status_lines(repo_root)` from the primary cwd; `_accept_owned_relpaths(repo_root, feature_dir, status_feature_dir)` computes owned paths `relative_to(repo_root)`, skipping (ValueError) any artifact outside repo_root. Empirically, in the canonical layout where `.worktrees/` is gitignored, primary `git status --porcelain` emits **nothing** for the coord worktree:

```
# .worktrees/ gitignored (canonical): git status --porcelain -> (empty)
# .worktrees/ NOT ignored:            git status --porcelain -> "?? .worktrees/"   (F-5 edge)
```

So coord-dir accept-owned writes are never in the primary porcelain output to begin with — the exclusion scope matches the snapshot scope. No defect.

### F-4 — stale-assertion flags (hunt target #4)

All three flagged lines assert empty-string returns from migration/upgrade code unrelated to `status_transition.py`:
- `test_migration_python_only_unit.py:121` → `assert reason == ""` from `migration.can_apply(...)`
- `test_op_record_schema_v2_migration.py:335` → `assert ok is True and reason == ""` from `OpRecordSchemaV2Migration.can_apply`
- `test_upgrade_auto_commit_unit.py:94` → `_is_upgrade_commit_eligible("kitty-specs/001/WP01.md", ...) is True`

`pytest` on all three files: **81 passed**. The analyzer matched the `""` literal, not the FR-007 fabrication idiom. Pure noise.

### Ratchet (hunt support)

`tests/architectural/test_topology_resolution_boundary.py`: **3 passed**. The `status_transition.py` path-shape predicate is an **explicitly documented allowlist entry** (lines 90-95) attributed to C-002 (upstream coord-merge-stabilization owns those function ranges) — confirming F-2 is a known, traceable residual, not a re-grown predicate.

---

## Verdict

**tree defensible: YES** — the four merged seams hold under adversarial probing; the only material finding (F-1, MEDIUM) is a dormant dual-era asymmetry reachable solely by an unmigrated legacy coord-topology mission, ticketable with a pinning test rather than PR-blocking; F-2 is a C-002-documented residual, F-3/F-4 are noise.
