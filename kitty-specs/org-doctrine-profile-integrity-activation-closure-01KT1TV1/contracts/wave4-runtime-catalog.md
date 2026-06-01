# Contract: Wave 4 — Runtime & Catalog UX

## C4.1 OperationalContext populated (FR-017, C-006)

- **Given** a WP claim (`implement.py` / `agent/workflow.py`) or a `next` runtime decision (`runtime_bridge.decide_next_via_runtime`)
  **When** the entry point builds context
  **Then** `build_operational_context(active_model, active_profile, active_role, current_activity, tech_stack)` returns a populated `OperationalContext` (not an all-None stub), with values resolved from the call-site inputs.
- **Given** `build_operational_context`
  **Then** it lives in `charter`, takes explicit parameters, and is never imported by `doctrine` (C-006 holds by construction).

## C4.2 Guards fail loudly (FR-018, NFR-004)

- **Given** an `OperationalContext` missing the required field
  **When** `require_active_profile()` / `require_active_role()` is called
  **Then** it raises `ContextPreconditionError` with an actionable message; and no worktree is created and no status event emitted on that precondition failure (NFR-004).

## C4.3 Dead extension point removed (FR-019, FR-020)

- **Given** the wiring from C4.1 lands first
  **Then** the OperationalContext allowlist entries (`test_no_dead_symbols.py:407-410`) are removed and the gate passes; the empty `_CATEGORY_C_WP_IN_FLIGHT_WORKFLOW_REGISTRY` category is deleted; obsolete activation-override code and the stale `activate_cmd`/sub-app export are resolved.

## C4.4 Catalog selectors (FR-022, FR-023, FR-024, FR-025, FR-026)

- **Given** `charter context --include agent-profile:<id>`
  **When** run
  **Then** it renders the named profile in human and `--json` output (hyphen token normalized via `from_operator_token`); the `--include` help advertises the agent-profile kind.
- **Given** `charter list --all` with at least one org pack and project artifacts
  **When** run
  **Then** every artifact per kind across built-in, org-pack, and project layers is listed with its source layer; `list_available()` includes org/project artifacts (roots resolved in `specify_cli`, passed as data per C-008); `--all` implies/supersedes `--show-available`.

## C4.5 Template discovery & resolution (FR-033, FR-034, #1333)

- **Given** templates in `doctrine/templates/` and per-mission `missions/<m>/templates/`
  **When** the discovery surface runs
  **Then** it enumerates templates as mission-qualified IDs (`<mission>/<name>`) annotated by source tier, without the caller knowing names in advance.
- **Given** `charter list --all`
  **Then** it includes the `template` kind; **and** `charter context --include template:software-dev/spec` resolves that template.
- **Given** the same `<name>` in two missions
  **Then** they are distinct IDs (mission qualifier disambiguates); discovery accounts for the empty glob and mission-scoped directory layout.
