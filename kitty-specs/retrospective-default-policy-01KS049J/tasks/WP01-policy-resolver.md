---
work_package_id: WP01
title: RetrospectivePolicy resolver + malformed-input handling
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-015
- FR-024
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-retrospective-default-policy-01KS049J
base_commit: b8dbb9f06d24dfd012a22bfd8b6c0a62d64f76cf
created_at: '2026-05-19T14:23:14.454370+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Foundation
assignee: ''
agent: "claude:claude-sonnet-4-6:python-pedro:implementer"
shell_pid: "81753"
history:
- timestamp: '2026-05-19T13:29:59Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/retrospective/policy.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/retrospective/policy.py
- src/specify_cli/retrospective/__init__.py
- tests/retrospective/test_policy.py
- tests/retrospective/conftest.py
role: implementer
tags: []
---

# Work Package Prompt: WP01 — RetrospectivePolicy Resolver + Malformed-Input Handling

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via the
`/ad-hoc-profile-load` skill (or by reading the profile YAML directly if the
skill is unavailable):

```
/ad-hoc-profile-load python-pedro
```

Acknowledge the initialization declaration. Internalize the
`specialization.avoidance_boundary` so you know which work falls to other
roles. Pull doctrine-scoped directives only as you need them; do not load the
full doctrine catalog.

## Objective

Land the canonical `RetrospectivePolicy` model with built-in defaults, and the resolver that reads policy from charter frontmatter and `.kittify/config.yaml` with documented precedence and source attribution. Every consumer of retrospective policy in this mission depends on this WP, so correctness here pays dividends across WP02-WP07.

## Context

Today the runtime resolves retrospective behavior from env vars (`SPEC_KITTY_RETROSPECTIVE`, `SPEC_KITTY_MODE`) and passes `facilitator_callback=None`. This mission replaces that with durable, project-level policy. The full background is in [spec.md](../spec.md) and [research.md](../research.md). Key references:

- Schema: [contracts/retrospective-policy.schema.json](../contracts/retrospective-policy.schema.json)
- Resolution rules: [data-model.md § RetrospectivePolicy](../data-model.md#retrospectivepolicy)
- Malformed-input handling: [data-model.md § Malformed-input handling (FR-024)](../data-model.md#malformed-input-handling-fr-024)
- Decision records: [DM-01KS051316C8Z0SDEKZ2B088CS](../decisions/DM-01KS051316C8Z0SDEKZ2B088CS.md), ADR [`architecture/3.x/adr/2026-05-19-1-retrospective-default-policy-architecture.md`](../../../architecture/3.x/adr/2026-05-19-1-retrospective-default-policy-architecture.md)

The existing `src/specify_cli/retrospective/config.py` and `mode.py` are env-var-driven. **Do not delete them in this WP** — WP06 owns their retirement decision per FR-023. Your new `policy.py` is the canonical surface going forward; legacy callers transition in subsequent WPs.

## Branch Strategy

- Planning base: `main`
- Final merge target: `main`
- This WP runs in its execution worktree allocated by `lanes.json` after `finalize-tasks`. Do not switch branches; `spec-kitty implement WP01` resolves the workspace.

## Subtasks

### T001 — Define `RetrospectivePolicy` + `RetrospectivePermissions` models

**Purpose**: Codify the policy schema as in-process Python types matching `contracts/retrospective-policy.schema.json`.

**Steps**:

1. Create `src/specify_cli/retrospective/policy.py` with two dataclass (or Pydantic v2) types:
   - `RetrospectivePermissions` — 7 boolean fields per contract: `write_record`, `inspect_mission_artifacts`, `propose_glossary_changes`, `propose_drg_changes`, `propose_doctrine_changes`, `apply_low_risk_changes`, `apply_structural_changes`.
   - `RetrospectivePolicy` — fields `enabled: bool`, `timing: Literal["post_completion","before_completion"]`, `failure_policy: Literal["warn","block"]`, `write_record: bool`, `generate_proposals: bool`, `apply_proposals: Literal["require_human","low_risk_auto"]`, `permissions: RetrospectivePermissions`, plus forward-compat fields `precedence: Literal["charter","config"] | None`, `generator: Literal["python"] = "python"`.
2. Built-in defaults per FR-002 — provide a `default_policy()` factory that returns:
   ```python
   RetrospectivePolicy(
       enabled=True, timing="post_completion", failure_policy="warn",
       write_record=True, generate_proposals=True, apply_proposals="require_human",
       permissions=RetrospectivePermissions(
           write_record=True, inspect_mission_artifacts=True,
           propose_glossary_changes=True, propose_drg_changes=True,
           propose_doctrine_changes=True,
           apply_low_risk_changes=False, apply_structural_changes=False,
       ),
   )
   ```
3. Hard invariant on `RetrospectivePermissions.apply_structural_changes`: this field MUST be `False` in the built-in default. Add a `__post_init__` validator that asserts no code path constructs a default-permissions object with this set to True.

**Files**:
- `src/specify_cli/retrospective/policy.py` (new, ~120 lines)
- `src/specify_cli/retrospective/__init__.py` (extend public surface to export `RetrospectivePolicy`, `RetrospectivePermissions`, `default_policy`)

**Validation**:
- [ ] Models match `contracts/retrospective-policy.schema.json` field-for-field
- [ ] `default_policy()` returns a policy that passes schema validation
- [ ] Constructing a `RetrospectivePermissions` with `apply_structural_changes=True` is permitted (operators may explicitly opt in) but the default factory NEVER sets it true

---

### T002 — Implement the resolver with source attribution

**Purpose**: A pure function `resolve_policy(repo_root) -> (RetrospectivePolicy, source_map)` that reads charter and config and produces the effective policy.

**Steps**:

1. Add `resolve_policy(repo_root: Path) -> tuple[RetrospectivePolicy, dict[str, str]]` to `policy.py`.
2. Resolution order per [data-model.md](../data-model.md#resolution-rules):
   - Start with `default_policy()` and a `source_map` where every key resolves to `"<default>"`.
   - Load charter frontmatter (existing `specify_cli.charter` reader). For each present key under `retrospective:`, overwrite the policy field and set `source_map[key] = "<charter-path>:retrospective.<key>"`.
   - Load `.kittify/config.yaml` (`ruamel.yaml`). For each present key under `retrospective:`, overwrite the policy field ONLY IF charter did not set it OR charter explicitly delegated via `retrospective.precedence: config`. Set `source_map[key] = ".kittify/config.yaml#retrospective.<key>"`.
3. `source_map` keys are dotted paths matching every leaf of the resolved policy (e.g. `"enabled"`, `"timing"`, `"permissions.write_record"`).
4. Return `(policy, source_map)`.

**Files**:
- `src/specify_cli/retrospective/policy.py` (extend, ~80 lines added)

**Validation**:
- [ ] Empty charter + empty config returns built-in defaults with every source_map entry == `"<default>"`
- [ ] Charter-only override: source_map cites the charter path; config absent leaves other fields at default
- [ ] Config-only override (no charter): source_map cites config; built-in defaults fill the rest

---

### T003 — Implement charter `retrospective.precedence: config` delegation

**Purpose**: When charter explicitly sets `retrospective.precedence: config`, config wins for any field present in config.

**Steps**:

1. Detect `precedence: config` in charter frontmatter before applying overrides.
2. If detected: charter STILL wins for any field present in charter, but config wins over charter ONLY for fields present in config but absent in charter. (Charter authority is preserved for what charter explicitly set; config fills the rest, even where defaults would otherwise apply.)
3. Add the `precedence` field to the resolved `RetrospectivePolicy` (already in T001's schema; just thread it through) so observers can see what mode was active.

**Files**:
- `src/specify_cli/retrospective/policy.py` (extend, ~30 lines added)

**Validation**:
- [ ] Charter says `enabled: false`, config says `enabled: true`, no precedence: charter wins (resolved `enabled=False`)
- [ ] Same setup with charter `precedence: config`: config wins for fields charter didn't explicitly set; charter's explicit `enabled: false` is preserved
- [ ] Source map reflects the actual winning source per field

---

### T004 — `PolicyResolutionError` + malformed-input handling

**Purpose**: Resolver never raises an unhandled exception. Malformed input produces a structured error.

**Steps**:

1. Define `PolicyResolutionError(Exception)` in `policy.py` with fields `source: str`, `reason: str`, `detail: str`.
2. Implement all failure modes from [data-model.md § Malformed-input handling (FR-024)](../data-model.md#malformed-input-handling-fr-024):
   - Invalid YAML → `reason="invalid_yaml"`, `detail=<parser msg>`.
   - Wrong type for `retrospective:` block → `reason="invalid_type_for_retrospective_block"`.
   - Unknown keys when `retrospective.strict_keys: true` is set → `reason="unknown_key"`, `detail=<key list>`. Default lenient mode: log a warning, ignore.
   - Invalid enum value (e.g. `timing: foo`) → `reason="invalid_enum"`, `detail="<field>: got 'foo', expected one of [...]"`.
3. The resolver catches the error internally on the "happy" return path: `resolve_policy()` returns `(default_policy(), source_map_with_resolution_error)` AND raises a wrapped `PolicyResolutionError` to the caller. The runtime catches the raised error and routes per failure policy (WP04's responsibility).
4. Implementation pattern: separate `_load_charter_retrospective_block()` and `_load_config_retrospective_block()` helpers that each return `(parsed_dict | None, error: PolicyResolutionError | None)`. `resolve_policy()` aggregates.

**Files**:
- `src/specify_cli/retrospective/policy.py` (extend, ~80 lines added including helpers)

**Validation**:
- [ ] `.kittify/config.yaml` with invalid YAML → resolver raises `PolicyResolutionError(source="...", reason="invalid_yaml", ...)` and source_map reflects the error
- [ ] `retrospective: "not_a_dict"` → `reason="invalid_type_for_retrospective_block"`
- [ ] `retrospective.timing: foo` → `reason="invalid_enum"` with helpful detail
- [ ] Unknown key with strict_keys=true → `reason="unknown_key"`
- [ ] Unknown key with strict_keys=false → warning logged, no error
- [ ] Resolver never raises a non-`PolicyResolutionError` exception under any input

---

### T005 — Env-var observation into `source_map`

**Purpose**: During the FR-015 deprecation cycle, env vars are observed but never override durable config or charter. When set, source_map records they were observed.

**Steps**:

1. After resolving charter + config, check `SPEC_KITTY_RETROSPECTIVE` and `SPEC_KITTY_MODE`.
2. If `SPEC_KITTY_RETROSPECTIVE` is set AND the resolved `enabled` field came from `"<default>"` (no charter/config opinion): record `source_map["enabled"] = "<env:SPEC_KITTY_RETROSPECTIVE>"` for observability. The policy field stays at the default (true); the env var does NOT flip it.
3. Same logic for `SPEC_KITTY_MODE` → `timing` + `failure_policy` fields.
4. Env vars NEVER win. Charter and config always take precedence when present.
5. The actual deprecation warning emission belongs to WP06 (T030). Your job here is just the source_map observation.

**Files**:
- `src/specify_cli/retrospective/policy.py` (extend, ~30 lines added)

**Validation**:
- [ ] `SPEC_KITTY_RETROSPECTIVE=1` and no charter/config: source_map records `"<env:...>"` but resolved policy is unchanged from defaults (which already have `enabled=True`)
- [ ] `SPEC_KITTY_RETROSPECTIVE=0` and no charter/config: source_map records the env observation; resolved `enabled` stays True (env never wins)
- [ ] Charter `enabled: false` + `SPEC_KITTY_RETROSPECTIVE=1`: source_map shows charter source; env observation does NOT appear in source_map (charter is authoritative)

---

### T006 — Unit tests for the resolver

**Purpose**: Lock the resolver's behavior with focused unit tests.

**Steps**:

1. Create `tests/retrospective/test_policy.py` with test classes `TestPolicyDefaults`, `TestResolver`, `TestPrecedenceDelegation`, `TestMalformedInput`, `TestEnvObservation`.
2. Use `tmp_path` fixtures to scaffold `.kittify/config.yaml` and charter files for each scenario.
3. Coverage target ≥ 90% for `src/specify_cli/retrospective/policy.py` (NFR-004).
4. Add a `conftest.py` helper that builds a charter file with a `retrospective:` block in frontmatter (mimics the existing charter format).

**Files**:
- `tests/retrospective/test_policy.py` (new, ~250 lines covering ~25 scenarios)
- `tests/retrospective/conftest.py` (new helpers, ~50 lines)

**Validation**:
- [ ] `uv run pytest tests/retrospective/test_policy.py -q` exits 0
- [ ] `uv run coverage report --include='src/specify_cli/retrospective/policy.py'` reports ≥ 90%
- [ ] No `os.environ` mutation in the resolver tests except in the dedicated `TestEnvObservation` class (per FR-016 spirit)

---

## Definition of Done

- [ ] All 6 subtasks complete
- [ ] `uv run pytest tests/retrospective/test_policy.py -q` exits 0
- [ ] Coverage on `src/specify_cli/retrospective/policy.py` ≥ 90%
- [ ] `uv run ruff check src/specify_cli/retrospective/policy.py tests/retrospective/test_policy.py` exits 0
- [ ] `resolve_policy()` is byte-deterministic given the same input (verified by a golden-snapshot test)
- [ ] Public API exported from `src/specify_cli/retrospective/__init__.py`: `RetrospectivePolicy`, `RetrospectivePermissions`, `default_policy`, `resolve_policy`, `PolicyResolutionError`
- [ ] No edits outside `owned_files`

## Risks & Reviewer Guidance

- **Risk**: charter frontmatter parser may already exist with a specific shape. Do NOT introduce a second parser; reuse the existing `specify_cli.charter` reader. If its API doesn't expose the `retrospective:` subtree cleanly, surface this in WP01's review and propose a tiny extension rather than duplicating.
- **Risk**: env-var observation logic is subtle (env never wins, but is recorded). Reviewer should verify every test case checks both the resolved policy field AND the source_map entry.
- **Reviewer**: focus on (1) precedence correctness under `precedence: config` delegation, (2) malformed-input branches each emit their canonical `PolicyResolutionError` shape, (3) source_map keys cover every leaf field of the resolved policy.

## Next

After this WP merges, WP02 (Generator) and WP06 (Env Deprecation) can both depend on the new `RetrospectivePolicy` surface.

Implementation command:

```bash
spec-kitty agent action implement WP01 --agent claude
```

## Activity Log

- 2026-05-19T14:23:15Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=81753 – Assigned agent via action command
