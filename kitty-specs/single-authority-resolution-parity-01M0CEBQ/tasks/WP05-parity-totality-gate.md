---
work_package_id: WP05
title: Parity/totality gate (fail-loud + falsifiable)
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- C-004
- FR-002
- FR-007
- NFR-003
planning_base_branch: spec/charter-resolution-parity
merge_target_branch: spec/charter-resolution-parity
branch_strategy: Planning artifacts for this mission were generated on spec/charter-resolution-parity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into spec/charter-resolution-parity unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
- T029
history:
- Created by /spec-kitty.tasks (M1 charter-resolution program)
agent_profile: python-pedro
authoritative_surface: tests/doctrine/drg/
create_intent:
- tests/doctrine/drg/test_recursion_parity_gate.py
execution_mode: code_change
owned_files:
- tests/doctrine/drg/test_kind_mapping_totality.py
- tests/doctrine/drg/test_recursion_parity_gate.py
role: implementer
tags: []
tracker_refs:
- '3490'
- '3426'
- '2981'
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile so your boundaries, directives, and
tactics are active:

```
/ad-hoc-profile-load python-pedro
```

Then run `spec-kitty charter context --action implement --json` and apply the resolved
initialization. State which directives/tactics you applied before writing code.

## Objectives & Success Criteria

Make the two defect classes **structurally impossible to reintroduce silently**: extend the totality gate to cover **string-keyed** kind maps, add a **behavioral loader↔resolver recursion-parity** check, a **C-002 negative** test, and a **falsifiability proof** — and verify **zero golden-count movement** (C-004).

- **SC (FR-007)**: gate fails loudly when the loader/resolver recursion sets diverge, or when any kind-map authority (including string-keyed) is inconsistent.
- **SC (NFR-003)**: a deliberately reintroduced divergence reddens the gate and names the kind; restoring greens it — proven both directions on one commit.
- **SC (C-002)**: `.provenance/*.yaml` and `.md` are never captured.
- **SC (C-004)**: no cascade/DRG golden count moved by the mission.

## Context & Constraints

Read `contracts/parity-gate.md`, `data-model.md` §5, and the **existing** gate `tests/doctrine/drg/test_kind_mapping_totality.py` (AST scan; recognizes only `ArtifactKind.MEMBER`/`NodeKind.MEMBER`-keyed dict literals; has `_EXEMPT_GET_PARTIALS`). String-keyed maps (`_SINGULAR_TO_PLURAL_KIND`, `_KIND_TO_PROPERTY`, `_KIND_TO_NODE_KIND`, …) are invisible to it today.

Depends on: WP01 (`doctrine.discovery_recursion`, loader recursive), WP02 (resolver recursive), WP03 (collapsed maps). `charter.synthesizer.project_drg._KIND_TO_NODE_KIND` stays string-keyed & intentionally partial (3 synthesizable kinds) — M1 covers it, it is **not** converted to enum-keyed (that is M6/#3038).

**Constraints**: zero suppressions (C-005). Keep the existing enum-keyed gate intact (do not weaken it).

## Branch Strategy
Planning base **`spec/charter-resolution-parity`**; merge target **`spec/charter-resolution-parity`**. Worktrees per computed lane from `lanes.json`. Depends on WP01+WP02+WP03 — this WP is the join.

## Subtasks & Detailed Guidance

### Subtask T025 – Extend the totality gate to string-keyed kind maps
In `test_kind_mapping_totality.py`, add discovery of module-level dict literals whose **string keys** are drawn from the kind vocabulary (keys ⊆ `{k.value for k in ArtifactKind}` and/or the plural forms). For each discovered string-keyed kind map:
- **Assert every key is a legit kind token** (a real `ArtifactKind` singular or plural) — a typo/removed/drifted key fails, naming the map + key.
- Maps that must be **total** (the collapsed `CHARTER_ACTIVATABLE_*` authorities) must carry all 10 activatable kinds.
- Add a **string-keyed exempt-from-totality allow-list** (analogous to `_EXEMPT_GET_PARTIALS`) containing `charter.synthesizer.project_drg::_KIND_TO_NODE_KIND` with a one-line rationale (3 synthesizable kinds; read via `.get`). Exempted maps are still **key-validated**.
Keep the AST approach; reuse `_dotted_module_name` etc. Add a self-check that the scan actually finds the known string-keyed maps (non-vacuous).

### Subtask T026 – Behavioral loader↔resolver recursion parity
Write `tests/doctrine/drg/test_recursion_parity_gate.py`. For every `ArtifactKind` with a non-empty `glob_pattern`:
1. Build a temp org (and project) root with a nested artifact `<dir>/<sub>/x.<suffix>` matching the kind's glob.
2. Discover via the **loader** (`DoctrineService`/the kind's repository) → set of ids/paths.
3. Discover via the **resolver** (`charter.kind_vocabulary._iter_artifact_paths` / `resolve_artifact_urn`) → set of ids/paths.
4. **Assert the two sets are equal** for that kind.
Kinds with no artifact-file convention (`template`; `anti_pattern` whose glob matches nothing on disk) are handled explicitly: assert both sides discover the same (possibly empty) set — they must still **agree**. Any divergence fails naming the kind.

### Subtask T027 – C-002 negative test [P]
In the nested fixture dir, drop `<dir>/<sub>/.provenance/foo.yaml` and `<dir>/<sub>/bar.md`. Assert **neither** the loader nor the resolver captures them (kind-specific globs). One assertion per side.

### Subtask T028 – Falsifiability proof (both directions)
Prove the parity check is not vacuous. Parametrize/monkeypatch **one** seam to non-recursive (e.g. patch `doctrine.discovery_recursion.overlay_scan_is_recursive` to return `False` for a chosen kind, or monkeypatch the resolver's flag) and assert the parity check **reddens and names the kind**; then restore and assert it **greens**. Both directions in one test module (so a single commit demonstrates falsifiability). Use `monkeypatch`; do not mutate source.

### Subtask T029 – Golden-count STOP verification (C-004)
Run the cascade/DRG golden-count suites and assert **zero** movement vs the mission base:
```bash
PATH=.venv/bin:$PATH SPEC_KITTY_SYNC_DISABLE=1 pytest tests -k "golden and (cascade or drg or count)" -q
```
Add (or reference) a focused assertion in this WP that the charter activation golden output for a representative built-in mission_type is unchanged by the mission (cascade reach constant). **If any golden count moved, STOP and escalate** — the ripple belongs to M2 (#3572) / M5 (#2829), not M1. Document the zero-movement result in the Activity Log.
- Record: `spec-kitty agent tasks mark-status T025 T026 T027 T028 T029 --status done --mission single-authority-resolution-parity-01M0CEBQ`.

## Test Strategy
Markers `doctrine`/`fast`. The gate must be green on the fixed tree and red when a divergence is injected (T028). Run: `PATH=.venv/bin:$PATH SPEC_KITTY_SYNC_DISABLE=1 pytest tests/doctrine/drg/test_kind_mapping_totality.py tests/doctrine/drg/test_recursion_parity_gate.py -q`.

## Risks & Mitigations
- **Vacuous gate** → T025 self-check (scan finds the known maps) + T028 falsifiability (both directions).
- **Per-kind fixture gaps** → iterate `ArtifactKind` programmatically; handle empty-glob/no-file kinds by asserting equal (agreeing) sets, not by skipping.
- **Golden ripple hidden** → T029 runs the golden suites explicitly and STOPs on any movement (C-004 guard).
- **Over-broadening the AST scan** → restrict string-keyed discovery to dicts whose keys are kind tokens; raise loudly on ambiguous shapes (mirror the existing mixed-key guard).

## Review Guidance
Verify: existing enum-keyed gate untouched/still green; string-keyed coverage finds `_SINGULAR_TO_PLURAL_KIND`, `_KIND_TO_PROPERTY`, `_KIND_TO_NODE_KIND` and validates keys; `_KIND_TO_NODE_KIND` exempted-from-totality with rationale, still key-validated; behavioral parity iterates all kinds; C-002 negative present; falsifiability proven both directions; golden-count zero-movement recorded; zero suppressions.

## Activity Log
- (implementer appends entries here)
