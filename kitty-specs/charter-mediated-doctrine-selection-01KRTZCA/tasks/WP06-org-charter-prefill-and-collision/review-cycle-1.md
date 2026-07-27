---
affected_files: []
cycle_number: 1
mission_slug: charter-mediated-doctrine-selection-01KRTZCA
reproduction_command:
reviewed_at: '2026-05-17T18:08:26Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP06
---

# WP06 Review Feedback — Cycle 1

**Verdict:** Reject (narrow, trivial fix required).

## What's right (do not change)

The substantive WP06 implementation is in excellent shape. Confirmed:

- **`OrgCharterPolicy` extended with all 8 `required_<kind>` fields** (directives, tactics, paradigms, styleguides, toolguides, procedures, agent_profiles, mission_step_contracts) using `list[str]` defaults — matches WP01's plural field-name decision.
- **Selection completeness ATDDs are now 3/3 green** (`tests/architectural/test_artifact_selection_completeness.py` — was 1/3 after WP01, now full parity).
- **Case-2 org-pack lifecycle ATDDs are 4/4 green** (`tests/integration/test_org_pack_artifact_lifecycle.py` — pack-rendered, required-prefill, collision-warn, missing-pack-loud-fail).
- **`MissingDoctrinePackError`** is a clear `RuntimeError` subclass with an actionable message naming both the pack and the missing path plus a remediation hint (`spec-kitty doctrine fetch --pack <name>` or remove the entry).
- **4-tuple activation dedup** `(activation_context, doctrine_pack_id, artifact_id, artifact_kind)` is **defensible** and is the canonical identity per `data-model.md §5` line 127-128 — the data-model spec was updated as part of this WP to match, not a deviation. `artifact_kind` is a real disambiguator when an `artifact_id` is reused across kinds inside the same pack.
- **`assert_pack_local_paths_exist`** is called early at context-resolution boundaries (charter `context.py` plus surfaces in `specify_cli.doctrine`) and raises the named error class.
- **Collision warnings now cover all 8 kinds** with parametrised coverage in `tests/specify_cli/doctrine/test_collision_warnings.py`.
- **Layer rule preserved:** `org_charter.py` imports only `from charter.activations import ActivationEntry`, no `from doctrine.*` direct imports. Zero `from specify_cli` imports in `src/charter/`.
- **WP04/WP05 regression check is clean** — `test_user_doctrine_artifact_lifecycle.py`, `test_context_selection_render.py`, `test_context_activation_render.py`, `test_trigger_registry_coverage.py`, `test_activation_registry_schema.py`, `test_wp_prompt_build_latency.py` all green (47/47).
- **Pre-existing failures confirmed** (not regressions): `test_wrapper_delegation` × 2, `test_neutrality_lint` × 1, `test_upgrade_command` × 1.

### Context.py +200 lines scope assessment

The +283 lines in `src/charter/context.py` are **legitimate scope for WP06**, not overreach. Rationale:

- `_enumerate_org_pack_paths`, `_missing_pack_diagnostic`, `_read_org_required_selections`, the `_load_doctrine_selection` union extension, and the `_render_selection_block` provenance map merge are all **org-pack-integration code that could not exist before T002** introduced `required_<kind>` fields on `OrgCharterPolicy`. WP04 set up the renderer infrastructure (provenance maps, selection block, render hooks) using a project-only view; WP06 is the first WP where the org-pack code path becomes renderable, so the wiring legitimately lands here.
- None of the changes reverse or rewrite WP04/WP05 logic — they extend `_render_selection_block`'s signature additively with a keyword-only `repo_root: Path | None = None` parameter and inject an extra `_merge` helper that runs **after** the existing catalog-derived map is built. The catalog-derived map still wins on collisions, preserving per-artifact DoctrineService provenance.
- The fallback `effective_org_root` resolution at lines 174-185 of the new context.py is a defensible UX improvement — direct callers of `build_charter_context` (e.g. the ATDD harness) now get the same three-layer service shape that `specify_cli`-wrapped callers get, with zero change to existing callers that pass `org_root` explicitly.

## What must change before approval

### 1. Ruff F401 — unused `textwrap` import in new test file (BLOCKER)

```
F401 [*] `textwrap` imported but unused
  --> tests/specify_cli/doctrine/test_missing_pack_policy.py:14:8
```

Implementer report claimed ruff was clean, but `ruff check src/specify_cli/doctrine/ src/charter/context.py tests/specify_cli/doctrine/` reports one finding. Per the charter's Code Quality directives, ruff must be clean on touched paths.

**Fix:**

```python
# tests/specify_cli/doctrine/test_missing_pack_policy.py
# Remove the unused import on line 14:
-import textwrap
```

If `textwrap.dedent` is intended for use inside the YAML fixtures (look at the fixture-builder helpers — `textwrap.dedent` is a common idiom for inline YAML literals), then either use it or drop the import. Do not silence the warning with `# noqa`.

After the fix, run:

```bash
ruff check src/specify_cli/doctrine/ src/charter/context.py tests/specify_cli/doctrine/
```

…and confirm zero findings.

## No other changes required

Everything else passes review. The substantive WP06 design and implementation are sound; only the lint regression in the new test file blocks approval.
