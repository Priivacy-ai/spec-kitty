# Contract — Mission-Creation `artifact_kind` (Q1)

**Surface**: `resolve_configured_template(artifact_kind, project_dir, resolved_mission_type)` (`src/specify_cli/runtime/resolver.py:346`).

**Contract (code-verified, DD-03)**:
- At `mission create`, the runtime requests the **literal `artifact_kind="spec"`** for *every* mission type (`src/specify_cli/core/mission_creation.py:351-355`, hardcoded, generic).
- At `/plan`-setup, the runtime requests the **literal `"plan"`** (`src/specify_cli/cli/commands/agent/mission_setup_plan.py:453-457`).
- There is **no per-type/per-step derivation** and **no alias layer** on the content-template side (`decision.py:_ALIASES` maps state→*command*-template via `resolve_command`, a different surface).

**Resolution chain**: `resolve_configured_template("spec")` → `resolved_mission_type.template_set.get("spec")` → filename → 5-tier `resolve_template`. `template_set` is keyed on `MissionStepTemplateRef.artifact_key`.

**Binding requirement (FR-007 / C-003 / C-010)**: each of `documentation`/`research`/`plan` MUST author a step whose `template.artifact_key == "spec"` (creatability) and one `== "plan"` (`/plan`-setup). Authoring any other key leaves the type uncreatable despite content. The hosting step and `template_file` are the per-type authoring choices; the key is fixed.

**Fail-closed (C-001)**: a `None` projection or a missing key raises `TemplateConfigurationError`. Never relax the guard to "fix" creatability.
