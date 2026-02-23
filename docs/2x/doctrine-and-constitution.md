# 2.x Doctrine and Constitution

## Doctrine Artifact Model

2.x doctrine artifacts are repository-native and typed:

1. Directives: `src/doctrine/directives/*.directive.yaml`
2. Tactics: `src/doctrine/tactics/*.tactic.yaml`
3. Styleguides: `src/doctrine/styleguides/**/*.styleguide.yaml`
4. Toolguides: `src/doctrine/toolguides/*.toolguide.yaml`
5. Schemas: `src/doctrine/schemas/*.schema.yaml`
6. Mission assets/templates: `src/doctrine/missions/**`

Artifact integrity is enforced by:

1. `tests/doctrine/test_schema_validation.py`
2. `tests/doctrine/test_artifact_compliance.py`
3. `tests/doctrine/test_tactic_compliance.py`

## Constitution Lifecycle in 2.x

The constitution flow is command-driven:

1. `spec-kitty constitution interview`
2. `spec-kitty constitution generate`
3. `spec-kitty constitution context --action <specify|plan|implement|review>`
4. `spec-kitty constitution status`
5. `spec-kitty constitution sync`

Primary implementation:

1. `src/specify_cli/cli/commands/constitution.py`
2. `src/specify_cli/constitution/compiler.py`
3. `src/specify_cli/constitution/context.py`

## 2.x Constitution Paths

Current bundle location:

1. `.kittify/constitution/constitution.md`
2. `.kittify/constitution/interview/answers.yaml`
3. `.kittify/constitution/references.yaml`
4. `.kittify/constitution/library/*.md`

Legacy compatibility is still handled for projects with older layout, but 2.x documentation treats `.kittify/constitution/` as canonical.

## Runtime Template Resolution

When resolving templates and mission assets, 2.x uses ordered precedence:

1. Project override
2. Project legacy location
3. User-global mission-specific location
4. User-global location
5. Packaged doctrine mission defaults

Implementation references:

1. `src/specify_cli/runtime/resolver.py`
2. `src/specify_cli/runtime/home.py`
