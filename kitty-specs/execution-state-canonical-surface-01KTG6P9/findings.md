# Mission Findings & Retro Notes — execution-state-canonical-surface-01KTG6P9

Tracked findings surfaced during this mission, recorded for **mission review / retrospective**.
Each entry: what happened, root cause, how it was resolved, and the upstream gap worth fixing.

---

## F-01 — `occurrence_map.yaml` blocked `implement` start twice (planning-artifact defect)

**Severity:** Medium (workflow blocker, not data integrity). **Phase:** start of implement loop (pre-WP01). **Status:** Resolved.

When driving `spec-kitty agent action implement WP01` the claim stalled at **Validate planning state** twice, both inside `kitty-specs/<mission>/occurrence_map.yaml` (this mission is `change_mode: bulk_edit`, so the map is a hard gate).

### Symptom 1 — invalid YAML
The 25 occurrence rows were authored with `;`-separated inline pairs:
```yaml
- submodule: status.models  ; count: 38 ; decision: PROMOTE ; reason: ...
```
The colon after `count` is parsed as a mapping-value indicator → `mapping values are not allowed here`, line 25 col 48. The whole file failed to load.

**Fix:** rewrote each row as a proper YAML mapping (`submodule`/`count`/`decision`/`reason` keys), quoting colon-bearing reasons.

### Symptom 2 — schema non-conformance
After the YAML parsed, the **bulk-edit gate** (`src/specify_cli/bulk_edit/gate.py` → `validate_occurrence_map` + `check_admissibility`) rejected the map:
- `target.operation: rewrite_import` is not in the schema enum `{rename, remove, deprecate}`.
- `import_paths.action: rewrite` is not in `{rename, manual_review, do_not_change, rename_if_user_visible}`.
- Only 3 of the **8 required standard categories** were present (admissibility requires all 8).
- Top-level used `exemptions`; the schema key is `exceptions`, and each entry needs an `action`.

**Fix:** rewrote the map to the canonical schema (`src/doctrine/schemas/occurrence-map.schema.yaml`): `operation: rename`; all 8 categories present; valid per-category actions; `exceptions` with `do_not_change`. Per-submodule PROMOTE/ROUTE/REVIEW/PRIVATE governance was preserved under `import_paths.occurrences` (allowed because `category_entry.additionalProperties: true`). Verified against `validate_occurrence_map`, `check_admissibility`, and the JSON schema — all green.

### Design decision worth reviewing — `manual_review` over `do_not_change`
The **review-time** diff check (`bulk_edit/diff_check.py`) is *path-heuristic*, not AST: it classifies each changed file into ONE category by path and **BLOCKS** if that category is `do_not_change`. This mission is a *structural refactor* that legitimately edits `cli/commands/*.py` (WP14: merge.py, doctor.py), `src/*.py`, tests, and configs. The heuristic-emittable categories (code_symbols, cli_commands, tests_fixtures, user_facing_strings, serialized_keys) were therefore set to **`manual_review`** (warns; reviewer-renata adjudicates) rather than `do_not_change`, which would spuriously block real WPs. `logs_telemetry` stayed `do_not_change` (never renamed; also never emitted by the heuristic). **Reviewers must confirm no serialized key / CLI name / telemetry key was actually renamed** — the map intentionally does not enforce that mechanically because the path heuristic is too coarse for a structural refactor.

### Coord-topology friction (the failure class this mission exists to fix)
The implement claim validates the **coordination worktree** copy of the artifact
(`.worktrees/<mission>-coord/kitty-specs/.../occurrence_map.yaml`), not just the
primary checkout. The fix had to be committed on **both** the mission branch
(`feat/execution-state-strangler`) **and** the coordination branch
(`kitty/mission-<slug>`). This is the same coord-vs-primary split (#1589/#1772)
the mission targets — it surfaced here at the *planning-artifact* layer.

### Upstream gaps worth filing
1. **Bulk-edit planning let an invalid `occurrence_map.yaml` through to `implement`.** The map should be validated against the canonical schema at authoring time (`/spec-kitty.plan` bulk-edit step, or `finalize-tasks`), not first discovered as an implement-claim stall. The `validate_against_schema` + `check_admissibility` functions already exist — wire them into the planning/finalize gate so the failure is loud and early.
2. **`occurrence_map.schema.yaml` has no example of the rich `occurrences` form.** The starter template (`src/doctrine/templates/occurrence-map-template.yaml`) only shows the minimal `{ action: ... }` per category, so an author hand-rolling per-submodule governance easily invents an invalid shape. Add a commented example of the `additionalProperties:true` extra-fields pattern.
3. **Planning-artifact fixes on coord-topology missions require a manual double-commit** (primary + coord branch). Consider a helper that syncs a corrected planning artifact to the coordination branch, or have the implement claim read the primary checkout for planning artifacts.

**Commits:** `3fe19b869` / `fc8d343ba` (YAML), `febeee4ee` (+ coord mirror) (schema).
