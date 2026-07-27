---
work_package_id: WP04
title: Tool Surface Provider Self-Registrations & Conformance Test
dependencies:
- WP03
requirement_refs:
- FR-006
- FR-008
- FR-009
- FR-010
tracker_refs: []
planning_base_branch: fix/cli-bug-sweep-tool-surface-self-registration
merge_target_branch: fix/cli-bug-sweep-tool-surface-self-registration
branch_strategy: Planning artifacts for this mission were generated on fix/cli-bug-sweep-tool-surface-self-registration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/cli-bug-sweep-tool-surface-self-registration unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
- T016
- T017
- T018
- T019
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "27091"
history:
- date: '2026-06-15'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tool_surface/providers/
create_intent:
- tests/specify_cli/tool_surface/test_provider_registration.py
execution_mode: code_change
owned_files:
- src/specify_cli/tool_surface/providers/agent_profiles.py
- src/specify_cli/tool_surface/providers/command_skills.py
- src/specify_cli/tool_surface/providers/managed_skills.py
- src/specify_cli/tool_surface/providers/native_config.py
- src/specify_cli/tool_surface/providers/plugin_bundle.py
- src/specify_cli/tool_surface/providers/session_presence.py
- src/specify_cli/tool_surface/providers/slash_commands.py
- tests/specify_cli/tool_surface/test_provider_registration.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Update all 7 tool surface provider modules to call `SurfaceProviderRegistry.register(SurfaceRegistration(...))` at module level. Add a Directive-030 conformance test asserting `service.py` contains no central provider literal lists. This WP completes the self-registration seam established by WP03.

## Branch Strategy

- **Implementation branch**: allocated by `spec-kitty agent action implement WP04 --agent claude`
- **Base**: WP03 must be merged before this WP starts
- **Planning/base branch**: `fix/cli-bug-sweep-tool-surface-self-registration`
- **Final merge target**: `fix/cli-bug-sweep-tool-surface-self-registration`

## Prerequisites

WP03 must be complete (merged into the lane base). The following must exist before this WP starts:
- `src/specify_cli/tool_surface/providers/_registry.py` — `SurfaceRegistration` + `SurfaceProviderRegistry`
- `src/specify_cli/tool_surface/providers/_discovery.py` — explicit import tuple
- `service.py` refactored to consume the registry

## Context

### Reading the current service.py before touching any provider

**Before editing any provider module**, read `src/specify_cli/tool_surface/service.py` to extract the exact registration data for each provider:
- What are the current `_KIND_TOKENS` entries for this provider?
- What provider class is instantiated in `build_providers()`?
- What definition functions are called in `build_registry()`?
- What `SurfaceKind` values are used?

This is your ground truth for the `SurfaceRegistration` arguments.

### Standard provider pattern

For most providers (T012–T015, T018), the registration call looks like:

```python
from .._registry import SurfaceRegistration, SurfaceProviderRegistry
from .._kinds import SurfaceKind  # or wherever SurfaceKind is defined

SurfaceProviderRegistry.register(
    SurfaceRegistration(
        provider_class=MyProvider,
        definitions=(my_definition,),
        kind_tokens={"my-kind": SurfaceKind.MY_KIND},
        synthetic_key=None,
        order=N,  # position in current build_providers() list (0-indexed)
    )
)
```

Place this call at module level, after the class/function definitions (so the names are defined before the call).

### Special cases

**`native_config` (T015)**: `_KIND_TOKENS` has both `"native-config"` and `"native_config"` pointing to the same kind. Both must appear in `kind_tokens`.

**`plugin_bundle` (T016)**: `synthetic_key=PLUGIN_BUNDLE_TOOL_KEY`. The definition is registered once under that key, not fanned out per configured tool. **Do NOT remove or change the lazy import** of `build_plans_for_bundles` from `service.py` inside the method body of `PluginBundleProvider` — that is the anti-cycle workaround. Leave it exactly as-is.

**`session_presence` (T017)**: Contributes 3 definitions: `context_file_definition`, `hook_definition`, `rule_definition`. The `definitions` tuple has 3 elements. Also check for underscore alias tokens in `_KIND_TOKENS` for `context_file`/`context-file`.

### Order values

Use the position (0-indexed) of each provider class in the current `build_providers()` list as the `order` value. This ensures the post-refactor `build_providers()` output matches the pre-refactor output exactly (required for NFR-004).

---

## Subtask T012 — Update `agent_profiles.py`

**Steps**:
1. Read `src/specify_cli/tool_surface/providers/agent_profiles.py`.
2. Read the current `service.py` for `agent_profiles`'s `_KIND_TOKENS` entries and position in `build_providers()`.
3. Add `from .._registry import SurfaceRegistration, SurfaceProviderRegistry` (adjust the relative import depth to match the actual module location).
4. Add the `SurfaceProviderRegistry.register(...)` call at module level with the correct `provider_class`, `definitions=(agent_profile_definition,)`, `kind_tokens={"agent-profile": SurfaceKind.AGENT_PROFILE}` (use the real values from service.py), `synthetic_key=None`, `order=0` (or whatever position this provider occupies in `build_providers()`).
5. `mypy src/specify_cli/tool_surface/providers/agent_profiles.py --strict` → zero errors.

---

## Subtask T013 — Update `command_skills.py`

Same pattern as T012. Read `command_skills.py` and service.py to extract the correct kind tokens, definition factory, and order. Add the registration call.

---

## Subtask T014 — Update `managed_skills.py`

Same pattern. Confirm the kind token (likely `"doctrine-skill"` per service.py), definition factory name, and order.

---

## Subtask T015 — Update `native_config.py`

Same pattern, with the additional `kind_tokens` entry for the underscore alias:
```python
kind_tokens={
    "native-config": SurfaceKind.NATIVE_CONFIG,
    "native_config": SurfaceKind.NATIVE_CONFIG,
},
```
Confirm the exact token strings and kind enum from service.py `_KIND_TOKENS`.

---

## Subtask T016 — Update `plugin_bundle.py` (synthetic key)

**Steps**:
1. Read `src/specify_cli/tool_surface/providers/plugin_bundle.py` in full. Note the lazy import of `build_plans_for_bundles` from `service.py` inside a method body — do NOT touch it.
2. Find `PLUGIN_BUNDLE_TOOL_KEY` — confirm it is a constant in this module or imported from somewhere. Use the exact constant in `synthetic_key`.
3. Add the registration call:
   ```python
   SurfaceProviderRegistry.register(
       SurfaceRegistration(
           provider_class=PluginBundleProvider,
           definitions=(plugin_manifest_definition,),
           kind_tokens={"plugin-manifest": SurfaceKind.PLUGIN_MANIFEST, "plugin_manifest": SurfaceKind.PLUGIN_MANIFEST},
           synthetic_key=PLUGIN_BUNDLE_TOOL_KEY,
           order=N,
       )
   )
   ```
   Confirm the exact token strings, kind enum, and definition factory from service.py.
4. `mypy src/specify_cli/tool_surface/providers/plugin_bundle.py --strict` → zero errors.

---

## Subtask T017 — Update `session_presence.py` (3 definitions)

**Steps**:
1. Read `src/specify_cli/tool_surface/providers/session_presence.py`.
2. In service.py `build_registry()`, find the 3 definition factory calls for `session_presence` (e.g., `context_file_definition`, `hook_definition`, `rule_definition`).
3. Add the registration call with all 3 definitions:
   ```python
   SurfaceProviderRegistry.register(
       SurfaceRegistration(
           provider_class=SessionPresenceProvider,
           definitions=(
               context_file_definition,
               hook_definition,
               rule_definition,
           ),
           kind_tokens={
               "context-file": SurfaceKind.CONTEXT_FILE,
               "context_file": SurfaceKind.CONTEXT_FILE,  # underscore alias
               "hook": SurfaceKind.HOOK,
               "rule": SurfaceKind.RULE,
           },
           synthetic_key=None,
           order=N,
       )
   )
   ```
   Confirm the exact token strings from service.py `_KIND_TOKENS` and the kind values.
4. `mypy src/specify_cli/tool_surface/providers/session_presence.py --strict` → zero errors.

---

## Subtask T018 — Update `slash_commands.py`

Same pattern as T012. Confirm the kind token (likely `"command-file"`), definition factory, and order from service.py.

---

## Subtask T019 — Add Directive-030 Conformance Test

**Purpose**: Assert two structural invariants: (1) all provider modules have registrations, (2) `service.py` has no central provider literal lists. This is the ongoing regression guard for the seam.

**Steps**:

1. Create `tests/specify_cli/tool_surface/test_provider_registration.py`.

2. **Test 1 — Registration completeness**:
   ```python
   def test_all_providers_registered():
       """Every non-underscore provider module must have exactly one registration."""
       from specify_cli.tool_surface.providers._discovery import _PROVIDERS
       from specify_cli.tool_surface.providers._registry import SurfaceProviderRegistry

       # Importing _discovery fires all registrations
       registered_classes = {reg.provider_class for reg in SurfaceProviderRegistry._registrations}

       # There must be exactly 7 registrations
       assert len(SurfaceProviderRegistry._registrations) == 7

       # All registrations must have non-empty definitions and kind_tokens
       for reg in SurfaceProviderRegistry._registrations:
           assert len(reg.definitions) >= 1, f"{reg.provider_class} has no definitions"
           assert len(reg.kind_tokens) >= 1, f"{reg.provider_class} has no kind_tokens"
   ```

3. **Test 2 — service.py has no central provider literals** (Directive-030):
   ```python
   import ast
   import pathlib

   def test_service_py_has_no_central_provider_literals():
       """service.py must not contain central provider literal lists (Directive-030)."""
       service_source = pathlib.Path("src/specify_cli/tool_surface/service.py").read_text()

       # The old build_providers() had a list literal containing provider instances.
       # The refactored version must not.
       # A simple heuristic: the old pattern was something like
       # `return [AgentProfilesProvider(), ...]` — a list literal with Provider() calls.
       # Assert this pattern is absent.
       tree = ast.parse(service_source)
       for node in ast.walk(tree):
           if isinstance(node, ast.FunctionDef) and node.name == "build_providers":
               # If build_providers has a return statement with a list literal
               # containing Call nodes to provider classes, that's the old pattern.
               for child in ast.walk(node):
                   if isinstance(child, ast.List) and child.elts:
                       for elt in child.elts:
                           if isinstance(elt, ast.Call):
                               raise AssertionError(
                                   "service.py build_providers() contains a central "
                                   "provider list literal — registry not used"
                               )
   ```

   Adapt this AST check to the actual code structure. The goal is to assert that `service.py` no longer contains a hardcoded list of provider instantiations. A regex check on the source is also acceptable if the AST approach is overly complex.

4. Add `mypy` and `ruff` to the test file's standard CI targets.

**Validation**:
- `pytest tests/specify_cli/tool_surface/test_provider_registration.py -v` → both tests pass.
- Full `pytest tests/specify_cli/tool_surface/ -v` → all pass.

---

## Integration Check

After all subtasks:

```bash
# Registry has 7 registrations
python -c "
from specify_cli.tool_surface.providers._discovery import _PROVIDERS
from specify_cli.tool_surface.providers._registry import SurfaceProviderRegistry
print('Registrations:', len(SurfaceProviderRegistry._registrations))
for r in sorted(SurfaceProviderRegistry._registrations, key=lambda r: r.order):
    print(f'  order={r.order} class={r.provider_class.__name__} defs={len(r.definitions)} tokens={list(r.kind_tokens.keys())}')
"

# Existing tool surface behavior unchanged
PWHEADLESS=1 pytest tests/specify_cli/tool_surface/ -v

# Full suite
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider -q

# Branch coverage on new provider registration code (NFR-003)
.venv/bin/pytest tests/specify_cli/tool_surface/ \
  --cov=src/specify_cli/tool_surface/providers \
  --cov-report=term-missing \
  --cov-fail-under=90

# Type check
.venv/bin/mypy src/ --strict

# Lint
.venv/bin/ruff check .
```

## Definition of Done

- [ ] All 7 provider modules call `SurfaceProviderRegistry.register(...)` at module level.
- [ ] `SurfaceProviderRegistry._registrations` contains exactly 7 entries after importing `_discovery`.
- [ ] `session_presence` registration has 3 definitions.
- [ ] `plugin_bundle` registration has `synthetic_key` set.
- [ ] `native_config` registration has both hyphen and underscore kind tokens.
- [ ] `test_provider_registration.py` conformance tests pass.
- [ ] `spec-kitty doctor tool-surface` behavior is unchanged from pre-refactor.
- [ ] Branch coverage on `src/specify_cli/tool_surface/providers/` is ≥ 90% (NFR-003): `pytest tests/specify_cli/tool_surface/ --cov=src/specify_cli/tool_surface/providers --cov-fail-under=90` passes.
- [ ] `mypy src/specify_cli/tool_surface/ --strict` → zero errors.
- [ ] `ruff check src/specify_cli/tool_surface/` → zero issues.
- [ ] All pre-existing `tool_surface` tests pass.

## Risks for Reviewer

- **Order values must match the pre-refactor `build_providers()` order exactly** to avoid behavioral regressions (NFR-004). Verify by running `spec-kitty doctor tool-surface` on a test project before and after and diffing the output.
- **`plugin_bundle.py`'s lazy import** of `build_plans_for_bundles` from `service.py` must be preserved unchanged. Do not attempt to resolve the circular import.
- The conformance test's AST check (T019) may need tuning for the exact refactored `build_providers()` form. If the delegation call is itself a function call (not a list), adjust the assertion to check that there is no inner list literal with provider instantiations.
- At the end of WP04, `_KIND_TOKENS` in `service.py` is now populated from the registry at module import time. If any existing test patches `service._KIND_TOKENS` directly, it will no longer work — find those tests and update them to patch the registry output instead.

## Activity Log

- 2026-06-15T12:15:27Z – claude:sonnet:python-pedro:implementer – shell_pid=11390 – Assigned agent via action command
- 2026-06-15T12:24:41Z – claude:sonnet:python-pedro:implementer – shell_pid=11390 – T012-T018 provider self-registrations verified present (landed via WP03 sequential lane); T019 conformance test added. 503 tool_surface tests pass, mypy --strict clean (39 files), ruff clean.
- 2026-06-15T12:25:19Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=27091 – Started review via action command
- 2026-06-15T12:36:14Z – user – shell_pid=27091 – Review passed: 7 providers registered correctly (session_presence 3 defs, plugin_bundle synthetic_key, native_config dual tokens native-config/native_config, unique orders 0-60); T019 conformance test asserts registration completeness (7 distinct classes, each >=1 def & >=1 token) + Directive-030 no-central-literals via AST walk of build_providers() for *Provider() list literals. 503 tool_surface tests pass, mypy --strict and ruff clean. (--force used to bypass lane-branch kitty-specs guard; workspace-topology condition, not a review defect.)
