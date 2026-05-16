---
work_package_id: WP03
title: Make build_charter_context(profile=) load-bearing
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-004
- NFR-004
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T013
agent: "claude:opus-4-7:python-pedro:implementer"
agent_profile: python-pedro
authoritative_surface: src/charter/context.py
execution_mode: code_change
owned_files:
- src/charter/context.py
- tests/charter/test_context_profile.py
role: implementer
history: []
tags: []
shell_pid: "1117321"
---

## Objective

Make the `profile=` parameter of `charter.context.build_charter_context` load-bearing.
Today the implementation at `src/charter/context.py:92` discards it with `_ = profile`.
After this WP, passing a known agent-profile ID causes the resolver to look up the
profile's `directive_references` and `tactic_references` against the doctrine catalog
and emit two new sections in `CharterContextResult.text`:

- `Profile-Cited Directives (<profile-id>):`
- `Profile-Cited Tactics (<profile-id>):`

Each entry is either the full body (inline) or a fetch + when-doing stanza. The stanza
shape is the canonical one pinned by the ATDD suite's
`_contains_either_body_or_fetch_with_conditional` helper (test file lines 215-238).

ATDD tests turned green by this WP:

- `TestImplementActionContext::test_implement_action_context_includes_profile_directive_references_when_profile_known`
- `TestProfileDirectivesSurfacedInWpPrompt::test_python_pedro_directive_010_referenced_in_implement_prompt`

---

## Context

`build_charter_context(repo_root, action=..., profile=<id>)` is the resolver entry point
called from `_governance_context` (WP06 will add the call site that actually supplies
`profile=<id>`). Today the signature accepts the parameter but throws it away. The
mission's central architectural pivot (plan.md §"The C-001-clean profile-resolution
path") is that profile lookup is a `doctrine`-layer operation —
`doctrine.agent_profiles.AgentProfileRepository` is **below** `charter` in the layer
order, so `charter.context` is permitted to import it without violating ADR
`2026-03-27-1`.

This WP delivers the **resolver-side** of FR-002 / FR-004. The **wiring side** (extracting
`agent_profile` from WP frontmatter and forwarding it in `_governance_context`) lands in
WP06.

---

## Branch Strategy

- **Planning/base branch**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Worktree**: allocated by `finalize-tasks`
- **Implement command**: `spec-kitty agent action implement WP03 --agent claude`

---

## Subtask T009 — Replace `_ = profile` with a real lookup at `src/charter/context.py:92`

**File**: `src/charter/context.py`

Locate the `_ = profile` discard near line 92 in `build_charter_context`. Replace with:

```python
profile_record = _load_agent_profile(profile) if profile else None
```

Thread `profile_record` into `_render_bootstrap_text` (and the compact renderer, where
applicable) so it can drive the two new sections.

---

## Subtask T010 — Add `_load_agent_profile(profile_id)` helper

**File**: `src/charter/context.py`

Add a small helper, centralising the single import site of `doctrine.agent_profiles`:

```python
from doctrine.agent_profiles import AgentProfileRepository


def _load_agent_profile(profile_id: str) -> AgentProfile | None:
    """Resolve *profile_id* via the doctrine layer. Returns None on miss."""
    try:
        return AgentProfileRepository.default().get(profile_id)
    except Exception:  # noqa: BLE001 — best-effort lookup; never raise into resolver
        return None
```

C-001 invariant (`kernel ← doctrine ← charter ← specify_cli`) holds: `charter` imports
from `doctrine`, which is below it.

---

## Subtask T011 — Add `_render_profile_directives(profile, service)`

**File**: `src/charter/context.py`

```python
def _render_profile_directives(
    profile: AgentProfile,
    service: DoctrineService,
) -> str:
    """Render the 'Profile-Cited Directives (<profile-id>):' section.

    For each id in profile.directive_references:
      - look up via service.directives.get(id)
      - emit ``- <id>: <title> — <rationale>`` plus the verbatim body OR
        a fetch + when-doing stanza (token-budget decides which; default = inline).
    """
```

Output shape (canonical, must match the contract in `contracts/charter-context-resolver.md`):

```
Profile-Cited Directives (python-pedro):
  - DIRECTIVE_010: Specification Fidelity Requirement
    <body verbatim>
  - DIRECTIVE_024: Locality of Change
    Run: spec-kitty charter context --include directive:DIRECTIVE_024
    When you apply a code change, run this command and apply the returned rule.
```

When `profile is None` or `profile.directive_references` is empty, the helper returns
the empty string — caller filters out empty sections before joining.

When an id is in the profile but the catalog doesn't know it, emit:
`  - <id>: (catalog entry not found; verify profile references)` and continue. Do **not**
raise.

---

## Subtask T012 — Add `_render_profile_tactics(profile, service)`

**File**: `src/charter/context.py`

Same structural pattern as T011, for `profile.tactic_references` against
`service.tactics`. The fetch stanza uses `--include tactic:<id>` and the when-doing
clause derives from the tactic's `when:` field. When the tactic has no `when:`, fall
back to `apply a code change`.

---

## Subtask T013 — Unit tests in `tests/charter/test_context_profile.py`

**File**: `tests/charter/test_context_profile.py` (new)

| Test | Scenario | Expectation |
|---|---|---|
| `test_known_profile_surfaces_directive_section` | `profile="python-pedro"` (declares DIRECTIVE_010) | `result.text` contains `Profile-Cited Directives (python-pedro):` and a line citing `DIRECTIVE_010` |
| `test_known_profile_surfaces_tactic_section` | profile with `tactic_references: [language-driven-design]` | `result.text` contains `Profile-Cited Tactics (...):` and the tactic id |
| `test_unknown_profile_skips_profile_sections` | `profile="nonexistent-agent"` | `result.text` does NOT contain `Profile-Cited` (both sections omitted); no exception raised |
| `test_profile_none_skips_profile_sections` | `profile=None` | byte-identical to today's output (NFR-005 regression gate) |
| `test_empty_directive_references_omits_section` | profile with no `directive_references` | `Profile-Cited Directives` line absent; tactics section still appears if any tactic refs |
| `test_unknown_directive_id_emits_warning_not_crash` | profile cites `DIRECTIVE_999` which catalog lacks | entry emits the "catalog entry not found" line; no exception |

---

## Definition of Done

- [ ] `_ = profile` is removed from `src/charter/context.py`; the parameter drives behaviour.
- [ ] `_load_agent_profile`, `_render_profile_directives`, `_render_profile_tactics` exist and are unit-tested.
- [ ] `tests/charter/test_context_profile.py` passes (6 tests).
- [ ] ATDD test `test_implement_action_context_includes_profile_directive_references_when_profile_known` passes.
- [ ] ATDD test `test_python_pedro_directive_010_referenced_in_implement_prompt` passes.
- [ ] `tests/architectural/test_layer_rules.py` (8 tests) still passes — the new `doctrine.agent_profiles` import in `charter.context` is allowed under C-001.
- [ ] All 14 currently-passing ATDD tests remain green.
- [ ] When `profile=None`, `result.text` is byte-identical to pre-WP output (NFR-005).

---

## Risks

- **R-1**: A C-001 layer-rule regression caused by accidentally importing from
  `specify_cli`. **Mitigation**: the only new import is `doctrine.agent_profiles`;
  reviewer verifies; `tests/architectural/test_layer_rules.py` is the gate.
- **R-2**: A profile lookup is slow (NFR-002 — 1.5× latency budget).
  **Mitigation**: `AgentProfileRepository.default()` already caches; per-call cost is
  a dict lookup. WP05's baseline measurement covers the latency assertion.
- **R-3**: Test fixtures expect the previous byte-identical output and break when
  `profile=None` is passed unintentionally. **Mitigation**: `profile=None` path is
  byte-identical; if a fixture breaks, the change isn't byte-identical — fix the change.

---

## Reviewer Guidance

Check that:

1. The import `from doctrine.agent_profiles import AgentProfileRepository` is the **only**
   new cross-layer import in `charter/`. No `from specify_cli` lines.
2. `_load_agent_profile` returns `None` on every error path (catalog missing, profile
   not found, malformed YAML). The resolver never raises into `_governance_context`.
3. The two new section headers in `result.text` use the exact strings expected by the
   ATDD assertions (grep the test file for `"Profile-Cited Directives"` and
   `"Profile-Cited Tactics"` and match verbatim, including the parenthesised profile id).
4. The `profile=None` regression gate test produces byte-identical output to pre-WP.
5. Each rendered entry follows the verbatim-OR-(fetch+when-doing) shape required by
   `_contains_either_body_or_fetch_with_conditional` in
   `tests/specify_cli/next/test_wp_prompt_governance_contract.py:215-238`.

## Activity Log

- 2026-05-16T12:21:19Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1117321 – Started implementation via action command
