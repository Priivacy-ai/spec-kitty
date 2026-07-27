# Quickstart: Doctrine Artifact Domain Models

## Load a directive

```python
from doctrine.directives import DirectiveRepository

repo = DirectiveRepository()
directive = repo.get("004")  # or repo.get("DIRECTIVE_004")

print(directive.title)        # "Test-Driven Implementation Standard"
print(directive.enforcement)  # "required"
print(directive.tactic_refs)  # ["acceptance-test-first", "tdd-red-green-refactor", "zombies-tdd"]
print(directive.scope)        # Multiline string describing applicability
```

## Load a tactic

```python
from doctrine.tactics import TacticRepository

repo = TacticRepository()
tactic = repo.get("zombies-tdd")

print(tactic.name)           # "ZOMBIES TDD"
print(len(tactic.steps))     # 7
for step in tactic.steps:
    print(f"  {step.title}: {step.description[:60]}...")
```

## Use the DoctrineService

```python
from doctrine.service import DoctrineService

service = DoctrineService()

# Access any artifact type through named attributes
directive = service.directives.get("004")
tactic = service.tactics.get("zombies-tdd")
paradigm = service.paradigms.get("test-first")
styleguide = service.styleguides.get("kitty-glossary-writing")
profile = service.agent_profiles.get("implementer")

# Resolve a directive's tactic references on-demand
for tactic_id in directive.tactic_refs:
    tactic = service.tactics.get(tactic_id)
    if tactic:
        print(f"  Tactic: {tactic.name} ({len(tactic.steps)} steps)")
```

## Create a new artifact

```python
from pathlib import Path
from doctrine.directives import Directive, DirectiveRepository

repo = DirectiveRepository(project_dir=Path(".kittify/constitution/directives"))

new_directive = Directive(
    id="DIRECTIVE_027",
    schema_version="1.0",
    title="My Custom Governance Rule",
    intent="Ensure compliance with project-specific requirement.",
    enforcement="advisory",
    scope="Applies to all code changes in the src/ directory.",
    tactic_refs=["tdd-red-green-refactor"],
    procedures=["Step 1: ...", "Step 2: ..."],
)

repo.save(new_directive)
# Writes: .kittify/constitution/directives/027-my-custom-governance-rule.directive.yaml
```

## List all artifacts of a type

```python
from doctrine.service import DoctrineService

service = DoctrineService()

for directive in service.directives.list_all():
    print(f"[{directive.enforcement}] {directive.id}: {directive.title}")

for tactic in service.tactics.list_all():
    print(f"{tactic.id}: {tactic.name} ({len(tactic.steps)} steps)")
```

## With project overrides

```python
from pathlib import Path
from doctrine.service import DoctrineService

# Project-level overrides merge with shipped defaults
service = DoctrineService(project_root=Path(".kittify/constitution"))

# Project directive overrides shipped directive at field level
directive = service.directives.get("004")
# Fields set in project file override; others fall through from shipped
```
