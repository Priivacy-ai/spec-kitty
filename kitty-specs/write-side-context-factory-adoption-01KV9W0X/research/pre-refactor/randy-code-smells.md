# Randy Reducer — Pre-Refactor Code Smells (clean-BEFORE-touch, Mission B)

**Profile:** randy-reducer (semantic compression; behavior-preserving reduction; dead-code/duplication).
**Branch/HEAD:** `feat/write-side-context-factory-adoption` (re-pinned to current HEAD line numbers).
**Lens of THIS doc:** *not* the adoption itself. The pre-existing CODE smells on the write surfaces
that should land FIRST — as **behavior-preserving, bounded, separate** cleanups — so the adoption
(routing each site to a factory fragment) becomes a near-mechanical one-line swap instead of a
swap-tangled-with-a-cleanup.

**Hard rule applied (operator directive):** every item below is classified **pre-refactor (do first,
behavior-preserving)** vs **defer (out of scope / risky)**. Pre-refactors carry a behavior-preserving
proof (characterization green-suite / verification-by-deletion). They do **NOT** change which fragment
a site consumes — that is the adoption, and it stays separate.

> **One sentence:** there are **three byte/parameterized duplicates of the same two write-path
> primitives** (the topology-aware lock-root resolver, and the meta→identity reader) plus **two
> genuinely-dead surfaces** (FR-006) sitting on the adoption path. Pre-extracting the duplicates to
> ONE helper each, and deleting the dead surfaces, turns the adoption from "edit N divergent bodies"
> into "swap N call sites that already point at one seam." That is the whole win.

---

## Prioritized smell table

| # | Smell | Site (file:line, HEAD) | Pre-refactor action | Eases which adoption | LOC | Risk | Behavior-preserving proof | Class |
|---|-------|------------------------|---------------------|----------------------|-----|------|---------------------------|-------|
| **P1** | **Byte-identical lock-root resolver** — `_feature_status_lock_root` and `_repo_root_for_lock` are the *same body* (same imports, same `parent.name != KITTY_SPECS_DIR` guard, same `classify_worktree_topology`, same `resolve_canonical_root`, same 3× `.parent.parent` fallbacks). | `status/emit.py:388-424` ≡ `status/work_package_lifecycle.py:55-89` (callers: `emit.py:545`, `work_package_lifecycle.py:136,253`) | Extract ONE shared helper (e.g. `status/_lock_root.py::feature_status_lock_root(feature_dir, repo_root)`); both modules import it; delete the two private bodies. **No call-signature change.** | FR-001 (R1, R2) — after this, the adoption flips ONE helper body to `workspace.primary_root` and BOTH consumers follow; today it must edit two divergent-by-location bodies. | −~28 (one body of ~30 deleted; ~3 import lines added) | **low** | Verification-by-deletion: the two bodies are textually identical, so the extracted helper is provably equivalent. Suite: `tests/status/test_emit.py`, `tests/status/test_work_package_lifecycle.py`, `tests/stress/test_concurrent_emits.py`, `tests/git_ops/test_atomic_status_commits_unit.py` stay green. | **pre-refactor** |
| **P2** | **Parameterized-duplicate meta→identity reader** — `_identity_for_request` and `_resolve_bookkeeping_transaction_identifiers` both: load meta from the canonical-primary dir → read `coordination_branch`/`mission_id`/`mid8` → `resolve_transaction_mid8(...)` → `effective_mid8` + `effective_mission_id = … or f"legacy-{slug}"`. Same algorithm, two owners (the "second parallel factory" the spec names). | `coordination/status_transition.py:254-285` (in `_identity_for_request:234-295`) ≈ `cli/commands/implement.py:361-413` (`_resolve_bookkeeping_transaction_identifiers:344-413`) | Extract the shared **meta→(coord_branch, mission_id, mid8, effective_mission_id, effective_mid8)** read into one pure helper (it already has a clean tuple return in implement.py; lift it to a shared module, e.g. `coordination/_transaction_identity.py`). Both call sites consume it. **Pure, no I/O ordering change** (both already read meta the same way). | FR-004 + FR-007 (S1) — collapses the second factory to ONE identity body *before* the adoption, so the adoption rewires a single helper to `branch_ref.destination_ref`/`IdentityFragment`, not two. Also exposes the `resolve_transaction_mid8`-vs-`mission_id[:8]` divergence (see Defer-D1) in exactly one place. | −~25 (one ~35-line derivation deleted; shared helper ~30 + 2 imports) | **medium** | Characterization: the two derivations are proven byte-equal in the census (§6) and carry identical comments. Add a focused unit test asserting the extracted helper returns the same 5-tuple for (flattened, coord, legacy-no-mission_id) meta inputs, then delete both inline bodies. Suite: `tests/specify_cli/coordination/test_status_transition.py`, `tests/specify_cli/cli/commands/agent/test_tasks*.py` green. | **pre-refactor** |
| **P3** | **Dead fragment — `prompt_source`** — `PromptSourceFragment` + assembler + build-field + exports; **0 consumers** (`grep '\.prompt_source'` outside the def/assembly = ∅). | def `mission_runtime/context.py:181`; field `:246`; export `:254`; assembler `resolution.py:761-778`; build wiring `:908,:929` | Delete the fragment, its assembler, the build field, and the exports. Deletion only. | FR-006 — removes dead scaffolding from the factory surface the adoption reads, so the adopters see a smaller, all-live fragment set. | −~20 | **low** | Verification-by-deletion: 0 readers proven by grep; suite green after removal is the proof (SC-004). `tests/architectural/test_execution_context_parity.py` + factory tests green. | **pre-refactor** |
| **P4** | **Dead read-param — `StatusSurfaceFragment surface=`** — `MissionStatus.load(..., surface=…)` threaded to `_resolve_read_dir` with a never-taken `if surface is not None: return surface.status_read_dir` branch. The only two `MissionStatus.load()` callers (`agent/status.py:163,199`) pass `repo_root`+`mission_slug` ONLY. | param `status/aggregate.py:199`; thread `:266,:309`; dead arm `:329-332` | Delete the `surface=` param + the `if surface is not None` arm; the canonical `resolve_status_surface` path is the only live arm. | FR-006 / FR-003 — clears the dead *read*-param so the write-half adoption (`status_write_dir`) doesn't have to reason around a vestigial sibling param. | −~8 | **low** | Verification-by-deletion: both real callers proven not to pass `surface=` (grep). Suite: `tests/specify_cli/cli/commands/agent/test_tasks_mark_status.py`, status aggregate tests green. | **pre-refactor** |
| **P5** | **Literal-duplicate placement join** — `worktree_path / KITTY_SPECS_DIR / branch_name` composed verbatim **twice** in one function (reuse arm + create arm). | `core/worktree.py:384` AND `:396` (in `create_feature_worktree`) | Hoist to one local: `feature_dir = worktree_path / KITTY_SPECS_DIR / branch_name` computed once before the `if worktree_path.exists()` branch (or a one-line `_feature_dir_for(worktree_path, branch_name)` local). | FR-002 (P1/placement) — gives the adoption a SINGLE placement-join site to route to the factory's `CommitTarget`/placement projection instead of two. | −~2 | **low** | Pure refactor inside one function; the value is identical in both arms (same `worktree_path`, same `branch_name`). `tests/` worktree-creation coverage green. | **pre-refactor** |
| **P6** | **Tiny divergent root-walk twins** — `_repo_root_for_feature` (a 2-line `parent.parent` guard) and `_repo_root_for_lifecycle_log` / `_find_mission_specs_root` are *each* a small bespoke root-walk, NOT identical to P1's topology-aware resolver (these are the simpler `KITTY_SPECS_DIR`-keyed ancestor scans). | `status_transition.py:49-54`; `lifecycle_events.py:229-240`; `store.py:119-130` | **Do NOT pre-consolidate.** They are short, already single-sited, and differ in shape (2-up vs 3-up vs `.kittify` arm). Pre-extracting them buys nothing the adoption doesn't already do (each routes straight to `workspace.primary_root`). | n/a | — | n/a (leave) | Their divergence is intentional (different anchor files). Folding them now would *invent* a shared abstraction the adoption immediately deletes. | **defer (leave alone — let adoption delete in place)** |

---

## Pre-refactor vs defer — the explicit call

### DO FIRST (behavior-preserving, bounded, land before adoption)

- **P1 — extract the byte-identical lock-root helper.** Highest-confidence, lowest-risk. ~28 LOC
  net removed, textually-proven equivalent, makes FR-001's two highest-traffic sites collapse to one
  swap. This is the single most valuable pre-refactor.
- **P2 — extract the meta→identity reader (the second-factory body).** Collapses the "second
  parallel factory" to ONE identity derivation *before* the adoption rewires it. Medium risk
  (touches the coord write path) but the two bodies are census-proven byte-equal, so a focused 5-tuple
  characterization test makes it safe. This is what makes FR-004/FR-007 mechanical rather than a
  two-site surgery — and it isolates the `resolve_transaction_mid8`-vs-`mission_id[:8]` divergence to
  one inspectable place.
- **P3 + P4 — delete the two dead surfaces (FR-006).** Pure deletion, 0 readers each, grep-proven.
  Do these first so the adopters read a smaller, all-live fragment/param set. ~28 LOC of dead weight gone.
- **P5 — hoist the duplicated placement local in `worktree.py`.** Trivial, 2 LOC, gives FR-002 one
  join to route.

### LEAVE ALONE (risky or no-win)

- **P6 — the small divergent root-walk twins** (`_repo_root_for_feature`, `_repo_root_for_lifecycle_log`,
  `_find_mission_specs_root`). Already single-sited and *intentionally* different (different anchor
  files / depths). Pre-consolidating them would manufacture an abstraction the adoption then deletes —
  negative value. Let the adoption route each to `workspace.primary_root` in place.
- **Defer-D1 — the `effective_mid8` semantic divergence** (factory `IdentityFragment.derive` uses
  `mission_id[:8]`; both hand-rolled readers use `resolve_transaction_mid8(...)` + `legacy-<slug>`
  fallback). This is a **real behavioral difference, NOT a pre-refactor** — reconciling it is the
  *adoption's* job (FR-004), gated by the NFR-006 simple-case test + the before/after on-disk-target
  idempotency test. P2 only *co-locates* the divergence into one body; it must NOT silently "fix" it.
  Touching the mid8 derivation behavior pre-adoption is exactly the churn NFR-004 forbids.
- **Defer-D2 — `setup_feature_directory` (C=14) / `validate_feature_structure` (C=13)** in
  `worktree.py`. They are near the ≤15 ceiling but the placement adoption (FR-002, P5) does **not**
  add branches to them — P5 *removes* a join. No pre-extraction needed; flagged only so the WP-WT
  implementer knows not to grow them. (If FR-002 wiring threatens to push `create_feature_worktree`
  over 15, extract a `_feature_dir_for(worktree_path, branch_name)` local — but that is P5 already.)
- **Defer-D3 — `emit_status_transition` (C=12, carries a NOSONAR).** Central 20-param hub; FR-001
  only swaps its `lock_root = _feature_status_lock_root(...)` call (now the P1 helper). The adoption
  does not raise its complexity. Out of scope for pre-refactor; the existing NOSONAR + separate
  refactor track already owns it.

---

## Why this ordering de-risks the adoption (the mechanical-swap argument)

| Adoption FR | Today (without pre-refactor) | After pre-refactor | Net effect |
|---|---|---|---|
| FR-001 (R1,R2) | edit two divergent-by-location lock-root bodies | swap ONE P1 helper body → `primary_root`; both callers follow | 2 sites → 1 |
| FR-002 (P1) | route two placement joins | route ONE hoisted P5 local | 2 sites → 1 |
| FR-004/FR-007 (S1) | rewire identity in two parallel factories | rewire ONE P2 helper; divergence isolated | 2 sites → 1; risk localized |
| FR-006 | delete dead surfaces *while* adopting | already deleted (P3,P4) | adoption reads a clean surface |

The pre-refactors are **net-negative LOC** (~−86 across P1–P5) and **add zero behavior**. Each lands
green on the existing characterization suites listed per-row (no new fixtures required — that is the
*adoption's* NFR-002 topology-true obligation, not the cleanup's). They are independently revertible
and independently mergeable ahead of the adoption WPs.

---

## Behavior-preserving proof posture (summary)

- **P1, P5:** textual/structural identity → verification-by-deletion (suite green is the proof).
- **P2:** census-proven byte-equality + one focused 5-tuple characterization test before the body
  delete (the only pre-refactor that warrants a net-new test, and it is pure).
- **P3, P4:** 0-reader grep → deletion; suite green is the proof (SC-004 posture).
- **All:** run the per-row suites + `tests/architectural/test_execution_context_parity.py` (the
  read/write parity ratchet) green after each. No `# noqa`/`# type: ignore` added (NFR-005).
