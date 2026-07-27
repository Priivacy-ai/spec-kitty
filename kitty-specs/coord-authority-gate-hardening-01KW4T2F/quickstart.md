# Quickstart — Validating Coord-Authority Gate Hardening (01KW4T2F)

How to run and validate every gate this mission ships. All commands run from the repo root on `feat/coord-authority-gate-hardening`.

## 1. The hardened call-shape arm + census (IC-A — FR-001/002/003/008)

```bash
# The arm + its synthetic self-tests (param + attribute shapes → RED; clean → GREEN)
PWHEADLESS=1 pytest tests/architectural/test_gate_read_literal_ban.py -q

# The live scan over the real tree + named shrink-only census + scope-unify
PWHEADLESS=1 pytest tests/architectural/test_coord_read_residuals_closeout.py -q
```

Expect: clean live scans, the new cross-function (FR-001) and attribute (FR-008) self-mutation tests present and green, `test_callshape_arm_identity_passes_parameter_dir` re-pinned and consistent with FR-001, the identity scan family now covering `merge/`+`lanes/`+`core/worktree_topology.py` (FR-002).

**SC-001 / SC-006 self-mutation (manual spot-check)**: temporarily reintroduce `resolve_mission_identity(run.feature_dir)` in `merge/executor.py` — the scope-unified arm must flag BOTH the parameter shape and the attribute shape. Revert → GREEN.

## 2. Partition-stability + rationale map (IC-C — FR-006)

```bash
PWHEADLESS=1 pytest tests/architectural/test_write_surface_placement_guard.py -q
```

Expect: `test_full_partition_resolves_per_membership` green; the new machine-read `PARTITION_RATIONALE` map asserts (a) every `MissionArtifactKind` has an entry, (b) the map's split equals the live frozensets, (c) the parametrized anti-mutant across ALL load-bearing kinds.

**SC-003 self-mutation**: re-home any kind across `_PRIMARY_ARTIFACT_KINDS`/`_PLACEMENT_ARTIFACT_KINDS` in `src/mission_runtime/artifacts.py` WITHOUT editing its rationale entry → RED. Add a new enum member without a map entry → RED. Revert → GREEN.

## 3. #2197 routing — behavioral revert-fails (IC-B — FR-004 / SC-002)

```bash
# The behavioral preview proof against the divergent coord fixture
PWHEADLESS=1 pytest tests/integration/ -k "coord and preview" -q
```

Expect: on coord topology, `spec-kitty next`'s claimable-preview resolves `preview.wp_id` from the PRIMARY surface. **Revert-fails**: temporarily revert the `runtime_bridge.py` caller to `preview_claimable_wp(feature_dir)` (single-arg) → the preview reads the STATUS-only coord husk → wrong/empty `wp_id` → the test goes RED (asserts the DOMAIN value, not a path equality). Revert → GREEN.

## 4. runtime/next scan-scope un-mask + floor (IC-B — FR-005)

```bash
PWHEADLESS=1 pytest tests/architectural/test_coord_read_residuals_closeout.py \
  -k "runtime_next or non_vacuous or floor" -q
```

Expect: the identity/lanes scan now includes `src/runtime/next/`; the `runtime/next` read-site floor proves the extension is non-vacuous (not green merely because FR-004 already routed the one site).

## 5. check_pre30_layout husk no-op (IC-C — FR-007 / SC-004)

```bash
PWHEADLESS=1 pytest tests/integration/ -k "pre30 or husk" -q
```

Expect: `check_pre30_layout` is a clean no-op against (a) the production-shaped STATUS-only husk (real status payload + meta, no `tasks/`) and (b) the `tasks/`-present-but-non-legacy variant (exercises the `LEGACY_LANE_DIRS`/`.md` branch).

## 6. Pre-merge full-gate dry-run (NFR-003 — MANDATORY)

The FR-005 scan-scope un-mask cannot self-validate. Before merge, run the verbatim full architectural suite and record it in the PR body:

```bash
PWHEADLESS=1 pytest tests/architectural/ -q
```

Also run the CI-only shards locally (post-merge arch-gate adjudication discipline):

```bash
PWHEADLESS=1 pytest tests/integration/ tests/git/ -q
```

## 7. Lint / type gates

```bash
ruff check .
mypy src tests   # zero new issues; no new noqa / type: ignore / per-file ignores
```

## Acceptance map

| Success criterion | Validated by |
|-------------------|--------------|
| SC-001 cross-function param caught | §1 self-mutation (`_VIOLATION_CROSS_FUNCTION`) |
| SC-002 preview resolves from primary | §3 behavioral revert-fails on `preview.wp_id` |
| SC-003 partition re-home is conscious red | §2 rationale-map split equality + all-kinds anti-mutant |
| SC-004 pre30 no-op on production husk | §5 production-shaped + tasks/-present-non-legacy |
| SC-005 zero new file:line anchors | grep for new `\.py:\d+` ratchet keys = none; §1/§2 self-mutation |
| SC-006 executor identity caught (param + attribute) | §1 manual spot-check; FR-002 scope-unify + FR-008 attribute branch |
