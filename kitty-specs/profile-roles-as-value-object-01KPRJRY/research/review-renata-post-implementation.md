# Post-Implementation Review: Profile Roles as Value Object

**Profile:** Reviewer Renata (`reviewer-renata`)
**Mission:** `profile-roles-as-value-object-01KPRJRY`
**Branch:** `doctrine/profile_reinforcement`
**Review date:** 2026-04-22
**Scope:** WP01–WP07 (all work packages; full diff against `origin/main`)
**Directive gates:** DIRECTIVE_001 (Architectural Integrity), DIRECTIVE_024 (Locality of Change), DIRECTIVE_030 (Test and Typecheck Quality Gate), DIRECTIVE_032 (Conceptual Alignment)

---

## Verdict

**Approved with minor observations.** No critical or blocking issues found. The implementation is architecturally sound, backwards-compatible by design, and well-tested. The observations below are all LOW or MEDIUM severity — none require fixes before merge, but several are worth tracking as follow-up work.

---

## What was delivered

| Scope | Notes |
|---|---|
| `Role` half-open value object | New `str` subclass in `profile.py`; 8 well-known constants; custom roles first-class |
| `AgentProfile.roles: list[Role]` | Replaces scalar `role`; `min_length=1` enforced by Pydantic |
| Backward compat coercion | `_coerce_scalar_role` model validator emits `DeprecationWarning`, converts scalar YAML to list |
| `role` property | Returns `roles[0]`; kept for callers that only need the primary role |
| Profile renames | 7 shipped profiles renamed with character names (e.g. `implementer` → `implementer-ivan`) |
| New profile: `java-jenny` | Java specialist profile with Maven toolguide wiring |
| YAML schema update | `agent-profile.schema.yaml` now has `anyOf: [required: role, required: roles]` |
| Repository routing | `_filter_candidates_by_role` and `_exact_id_signal` updated to check `p.roles` list |
| Migration `m_3_2_4_kittify_profile_handoff` | Inserts profile-load and review-handoff blocks into installed `.kittify` and `.agents/skills/` templates |
| Test suite | `test_role_value_object.py`, updated `test_shipped_profiles.py`, migration test |
| Neutrality allowlist + doctrine tactics | Language-bias fixes across 4 tactic files; 3 new allowlist entries |

---

## DIRECTIVE_030 gate

Fast test suite passes (exit 0). Slow tests had one pre-existing import failure (`respx` not installed) unrelated to this mission's changes. Ruff clean on all new/modified files after boyscout fixes. No mypy or type errors observed in the core diff. **Gate: GREEN.**

---

## DIRECTIVE_024 gate (Locality of Change)

The diff is large (203 files, ~10,600 lines) but correctly scoped: profile renames propagate through doctrine YAML files, snapshot files (12 agents × 7 commands), and all test files that reference the old names. This is expected blast radius for a rename + model change. No unrelated functional changes detected. **Gate: GREEN.**

---

## Findings

### F-01 — LOW — Redundant field validators duplicate Pydantic `Field` constraints

**Location:** `src/doctrine/agent_profiles/profile.py:247–261`

`validate_routing_priority` re-checks `0 <= v <= 100`, which `Field(ge=0, le=100)` already enforces at the Pydantic layer. Same pattern for `validate_max_concurrent_tasks`. When `Field` constraints fire, Pydantic raises `ValidationError` before the validator even runs — so the explicit `if` checks are dead code in practice.

**Recommendation:** Remove the `@field_validator` bodies (keep the method names as no-ops if desired for documentation, or delete entirely). The `Field(...)` constraints are the authoritative gate.

---

### F-02 — MEDIUM — `DeprecationWarning` `stacklevel=2` likely points to Pydantic internals, not the callsite

**Location:** `src/doctrine/agent_profiles/profile.py:230`

When Pydantic invokes `_coerce_scalar_role` during `model_validate(data)`, the call stack is several frames deep inside Pydantic. `stacklevel=2` will generally surface the Pydantic dispatch layer, not the line of code calling `AgentProfile.model_validate(...)`. Users seeing this warning will not be able to locate the offending YAML file from the warning alone.

**Recommendation:** Either increase `stacklevel` to 3 or 4 (test empirically), or include the `profile_id` and a hint to search for `role:` in the warning message (the `profile_id` is already included, which helps). Alternatively, accept that the `profile_id` in the message is sufficient for locating the file and leave the stacklevel as-is. Not a blocker — just a DX issue for users of older YAML files.

---

### F-03 — MEDIUM — `_merge_profiles` and `_union_merge` use different list-field semantics with no documentation

**Location:** `src/doctrine/agent_profiles/repository.py:287–317` (`_merge_profiles`) vs `repository.py:151–165` (`_union_merge`)

`_merge_profiles` is used when a *project* profile overrides a *shipped* profile at load time. It calls the inner `deep_merge` which **replaces** child list values entirely. `_union_merge` is used in `resolve_profile` for the inheritance chain and **unions** list-type fields from parent to child.

A project author who expects union semantics when overriding a shipped profile (e.g., adding a capability without repeating the whole list) will be surprised. The docstring on `_merge_profiles` says "project fields overriding shipped fields" but does not clarify whether lists are replaced or merged.

**Recommendation:** Add a docstring note to `_merge_profiles` explicitly stating "list fields are replaced, not unioned — to extend a list, repeat the full shipped list plus your additions." This is a documentation gap, not a bug, but it will cause support tickets.

---

### F-04 — LOW — `applies_to_languages` uses snake_case in the JSON schema (pre-existing)

**Location:** `src/doctrine/schemas/agent-profile.schema.yaml:308`

All other properties in the schema use kebab-case (`profile-id`, `context-sources`, etc.) except `applies_to_languages` which uses snake_case. This is a pre-existing issue not introduced by this mission, but the mission touched the schema file, making this a good time to note it.

**Recommendation:** Track as a separate ticket. Changing to `applies-to-languages` in the schema requires a coordinated update to the shipped profiles and the `AgentProfile` Pydantic field alias. Out of scope for this PR.

---

### F-05 — LOW — `AgentProfileSchema` (schema_models.py) accepts both `role` and `roles` as optional with no mutual-exclusion enforcement

**Location:** `src/doctrine/agent_profiles/schema_models.py:167–168`

The JSON schema uses `anyOf: [required: role, required: roles]` to enforce "at least one of them." The `AgentProfileSchema` Pydantic model defines both as `Optional` without a cross-field validator. If used for Pydantic-level validation (not just schema generation), it would pass a profile that has neither `role` nor `roles`.

In practice, `AgentProfileSchema` is used only for schema generation (it explicitly says so in the module docstring), so this is not a runtime bug. But if the model is ever used for validation, it will silently pass incomplete profiles.

**Recommendation:** Add a comment to `AgentProfileSchema` noting it is schema-generation-only and should not be used for runtime validation.

---

### F-06 — LOW — `human-in-charge` collaboration has no `handoff-from` defined

**Location:** `src/doctrine/agent_profiles/shipped/human-in-charge.agent.yaml`

The sentinel profile defines `handoff-to: [reviewer]` but no `handoff-from`. Since it's a sentinel and `_SENTINEL_PROFILES` exempts it from content checks, this is intentional and not a test failure. However, the collaboration contract is incomplete relative to all other profiles. This is a minor design inconsistency — if a human-in-charge WP is handed to human from a planner, that flow is undocumented.

**Recommendation:** Consider adding `handoff-from: [planner, architect]` to document the typical flow, even for the sentinel case. Low-priority.

---

### F-07 — LOW — Migration `_patch_implement` string patterns are specific to a particular template state

**Location:** `src/specify_cli/upgrade/migrations/m_3_2_4_kittify_profile_handoff.py:129–134`

The strings `"- \`profile\`"` and `"- \`tool\`"` assume the installed `implement.md` has these exact patterns. Fresh installs from 3.2.4+ onwards won't have these stale field names, so the replacements will silently no-op, which is correct. However, if a user edited their template and the pattern appears in a different context, the replacement is overly broad (not anchored to a specific section).

This is an acceptable pragmatic tradeoff for a one-time idempotent migration. Document it in the migration docstring to aid future maintainers.

---

## Positive observations

These merit explicit mention as they raise the quality bar:

1. **`Role` as a half-open `str` subclass** is the correct design. Using `StrEnum` would have sealed custom roles out of the box, which contradicts the project's extensibility goal. The open/closed principle is well-applied here.

2. **`test_no_deprecation_warnings_on_load`** is an excellent regression guard. Any shipped profile accidentally left with a scalar `role:` field will fail this test immediately.

3. **`_filter_candidates_by_role` checks `normalized in p.roles`** rather than `normalized == p.roles[0]`. This is correct and intentional — secondary roles are first-class for routing purposes.

4. **The `anyOf` schema constraint** correctly models the transitional period: old profiles with scalar `role:` still validate, new profiles with `roles:` validate, both forms are accepted.

5. **All boyscout fixes were applied cleanly**: tactic reference cycle broken, language-bias removed from generic tactics, neutrality allowlist updated, stale test mocks fixed, ruff violations resolved.

---

## Items to track post-merge

| ID | Severity | Area | Action |
|----|----------|------|--------|
| F-01 | LOW | `profile.py` | Remove redundant field validators |
| F-02 | MEDIUM | `profile.py` | Verify `DeprecationWarning` stacklevel is useful in practice |
| F-03 | MEDIUM | `repository.py` | Document list-merge vs list-replace semantics in `_merge_profiles` |
| F-04 | LOW | `agent-profile.schema.yaml` | Align `applies_to_languages` → `applies-to-languages` (separate ticket) |
| F-05 | LOW | `schema_models.py` | Add "schema-generation-only" comment to `AgentProfileSchema` |
| F-06 | LOW | `human-in-charge.agent.yaml` | Consider adding `handoff-from` for completeness |
| F-07 | LOW | Migration | Document pattern-specificity in migration docstring |

None of these are blocking. All are improvements for follow-up work.
