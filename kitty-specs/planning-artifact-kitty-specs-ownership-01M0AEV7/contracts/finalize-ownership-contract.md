# Contract — finalize-tasks kitty-specs ownership decision

**Surface**: `spec-kitty agent mission finalize-tasks [--validate-only] --mission <handle> [--json]`
**Owner predicate**: `_invalid_mission_specs_owned_files` (`cli/commands/agent/mission_parsing.py`),
invoked by `_validate_owned_files_not_in_mission_specs` (`mission_finalize.py`).

## Inputs
- Post-bootstrap `frontmatter_by_wp: dict[wp_id, WPMetadata]` (execution_mode explicit or inferred).

## Contract (given → then)

1. **planning_artifact confined to planning paths + kitty-specs owned_files → ACCEPT**
   Given a WP with `execution_mode: planning_artifact` and **every** `owned_files` entry under
   `_PLANNING_PREFIXES` (`kitty-specs/<mission>/` and/or `docs/`),
   Then `_invalid_mission_specs_owned_files` returns no entry for that WP; finalize passes the ban
   **and** the two downstream hard-gates it previously shadowed — `validate_authoritative_surface`
   and `validate_glob_matches` (the latter runs even in `--validate-only`) — and `compute_lanes`
   places `wp_id` in `.planning_artifact_wps` (`lane-planning`). *An acceptance test proves this
   end-to-end: it must satisfy the surface-prefix and glob-existence gates (inference-driven
   construction, or a kitty-specs `authoritative_surface` + `create_intent`), and assert lane
   placement — not merely "the ban did not fire".*

2. **planning_artifact owning a non-planning path → NOT exempted (confinement, INV-4)**
   Given a `planning_artifact` WP owning a `kitty-specs/` path **and** any path outside
   `_PLANNING_PREFIXES` (e.g. `src/…`),
   Then the exemption does not apply; the kitty-specs path still trips the ban → REJECT with
   `INVALID_WP_OWNED_FILES_KITTY_SPECS`.

3. **code_change + kitty-specs owned_files → REJECT (fail-closed)**
   Given a WP with `execution_mode: code_change` (or unset→inferred-`code_change`, which requires a
   code signal in the body) owning any `kitty-specs/` path,
   Then finalize exits non-zero with `error_code: INVALID_WP_OWNED_FILES_KITTY_SPECS`, naming the WP
   and path, before any write/commit.

4. **unset → inferred planning_artifact + kitty-specs-only → ACCEPT**
   Given a WP with no `execution_mode` whose `owned_files`/body carry only planning signals,
   Then inference resolves `planning_artifact`, the exemption applies, and the WP is accepted
   (pins the inference→ban ordering).

5. **overlapping planning WPs → REJECT (downstream floor)**
   Given two `planning_artifact` WPs with overlapping `kitty-specs/` scopes and no dependency edge,
   Then `validate_no_overlap` rejects — the exemption is not a blanket kitty-specs bless.

6. **Seam preservation**
   The predicate identity and the dynamic alias `_invalid_kitty_specs_owned_files` (and shim
   re-exports) remain resolvable and patchable — no rename. Compare `execution_mode` against
   `ExecutionMode.PLANNING_ARTIFACT.value` / normalized, not incidental `StrEnum` equality.

## JSON error shape (unchanged for the rejected case)
```json
{"error": "WP owned_files cannot include paths under kitty-specs/",
 "error_code": "INVALID_WP_OWNED_FILES_KITTY_SPECS",
 "invalid_owned_files": [{"wp_id": "WP02", "path": "kitty-specs/<mission>/disposition-matrix.md"}]}
```

## Regression guards (bound to seams)
- `authoritative_surface` inference covers a kitty-specs owned file — exercise `infer_authoritative_surface` (`ownership/inference.py:154`) → `validate_authoritative_surface`; no surface hard-error for the accepted case.
- Deliverable durability is **filename-scoped** — exercise `_is_coordination_owned_artifact` / `kind_for_mission_file` (`lanes/auto_rebase.py:236`): a `kitty-specs/<slug>/disposition-matrix.md` deliverable is durable (`kind is None`); a NEGATIVE assertion documents that `analysis-report.md` / `tasks/WP*.md` are managed kinds and therefore reconciled (C-003 holds only for non-managed filenames).
