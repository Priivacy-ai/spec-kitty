# Step Contract Shape Contracts

One paragraph per shipped contract. The implementer renders the full YAML using the [data-model.md → Step contract shape](../data-model.md#step-contract-shape) example as the template.

Required keys for every contract (per existing schema; spec C-009 forbids new top-level fields):
- `schema_version: "1.0"`
- `id: documentation-<action>` (matches the file basename without extension)
- `action: <action>`
- `mission: documentation`
- `steps: list[StepDef]` — at least: `bootstrap` (charter context load), 1-2 delegate steps, an artifact-write step, a commit step.

Each `StepDef` requires `id`, `description`; optional `command`, `delegates_to{kind, candidates[]}`, `inputs[]`. **No** `expected_artifacts`.

---

## documentation-discover.step-contract.yaml

- `id: documentation-discover`, `action: discover`, `mission: documentation`.
- Bootstrap: `spec-kitty charter context --action discover --role discover --json`.
- Capture-needs step delegates to directives: `010-specification-fidelity-requirement`, `003-decision-documentation-requirement`.
- Validate-scope step delegates to tactic: `requirements-validation-workflow`.
- Write step: `Write spec.md in kitty-specs/{mission_slug}/`.
- Commit step delegates to directives: `029-agent-commit-signing-policy`, `033-targeted-staging-policy`.

## documentation-audit.step-contract.yaml

- `id: documentation-audit`, `action: audit`, `mission: documentation`.
- Bootstrap: `spec-kitty charter context --action audit --role audit --json`.
- Inventory-existing-docs step delegates to directive: `037-living-documentation-sync`.
- Identify-gaps step delegates to tactic: `requirements-validation-workflow`.
- Write step: `Write gap-analysis.md in kitty-specs/{mission_slug}/`.
- Commit step delegates to directives: `029-agent-commit-signing-policy`, `033-targeted-staging-policy`.

## documentation-design.step-contract.yaml

- `id: documentation-design`, `action: design`, `mission: documentation`.
- Bootstrap: `spec-kitty charter context --action design --role design --json`.
- Plan-divio-types step delegates to directive: `001-architectural-integrity-standard`.
- Architecture-decision step delegates to tactic: `adr-drafting-workflow`.
- Validate-design step delegates to tactic: `requirements-validation-workflow`.
- Write step: `Write plan.md in kitty-specs/{mission_slug}/`.
- Commit step delegates to directives: `029-agent-commit-signing-policy`, `033-targeted-staging-policy`.

## documentation-generate.step-contract.yaml

- `id: documentation-generate`, `action: generate`, `mission: documentation`.
- Bootstrap: `spec-kitty charter context --action generate --role generate --json`.
- Produce-artifacts step delegates to directive: `010-specification-fidelity-requirement`.
- Living-doc-sync step delegates to directive: `037-living-documentation-sync`.
- Validate-output step delegates to tactic: `requirements-validation-workflow`.
- Write step: `Write docs/**/*.md under kitty-specs/{mission_slug}/`.
- Commit step delegates to directives: `029-agent-commit-signing-policy`, `033-targeted-staging-policy`.

## documentation-validate.step-contract.yaml

- `id: documentation-validate`, `action: validate`, `mission: documentation`.
- Bootstrap: `spec-kitty charter context --action validate --role validate --json`.
- Quality-gates step delegates to directive: `010-specification-fidelity-requirement`.
- Risk-review step delegates to tactic: `premortem-risk-identification`.
- Validate-against-spec step delegates to tactic: `requirements-validation-workflow`.
- Write step: `Write audit-report.md in kitty-specs/{mission_slug}/`.
- Commit step delegates to directives: `029-agent-commit-signing-policy`, `033-targeted-staging-policy`.

## documentation-publish.step-contract.yaml

- `id: documentation-publish`, `action: publish`, `mission: documentation`.
- Bootstrap: `spec-kitty charter context --action publish --role publish --json`.
- Living-doc-sync step delegates to directive: `037-living-documentation-sync`.
- Specification-fidelity step delegates to directive: `010-specification-fidelity-requirement`.
- Final-validation step delegates to tactic: `requirements-validation-workflow`.
- Write step: `Write release.md in kitty-specs/{mission_slug}/`.
- Commit step delegates to directives: `029-agent-commit-signing-policy`, `033-targeted-staging-policy`.

---

**Verification**: `tests/specify_cli/mission_step_contracts/test_documentation_composition.py::test_all_six_contracts_load_cleanly` round-trips each YAML through the existing contract loader and asserts:
- `id == basename(path).removesuffix(".step-contract.yaml")`
- `action == basename(path).removeprefix("documentation-").removesuffix(".step-contract.yaml")`
- `mission == "documentation"`
- `len(steps) >= 4` (bootstrap + ≥1 delegate + write + commit)
- no `expected_artifacts` key on the contract or any step (C-009)
