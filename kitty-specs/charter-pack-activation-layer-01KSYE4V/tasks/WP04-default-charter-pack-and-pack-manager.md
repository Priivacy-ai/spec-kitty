---
work_package_id: WP04
title: Default Charter Pack + CharterPackManager
dependencies:
- WP02
- WP03
requirement_refs:
- FR-001
tracker_refs: []
planning_base_branch: pr/charter-doctrine-mission-type-configuration
merge_target_branch: pr/charter-doctrine-mission-type-configuration
branch_strategy: Planning artifacts for this mission were generated on pr/charter-doctrine-mission-type-configuration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/charter-doctrine-mission-type-configuration unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-pack-activation-layer-01KSYE4V
base_commit: 7a89ab05447996add74571261933a31b60bf92f5
created_at: '2026-05-31T13:58:08.026612+00:00'
subtasks:
- T015
- T016
- T017
- T018
- T019
agent: "claude:sonnet-4-6:python-pedro:implementer"
shell_pid: "4151579"
history:
- at: '2026-05-31T11:44:22Z'
  event: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: src/charter/pack_manager.py
execution_mode: code_change
owned_files:
- src/charter/packs/default.yaml
- src/charter/pack_manager.py
- tests/charter/test_pack_manager.py
role: implementer
tags: []
---

# WP04 — Default Charter Pack + CharterPackManager

## Overview

This WP introduces two new production artifacts:

1. `src/charter/packs/default.yaml` — the canonical list of all built-in artifact IDs across all 9 activation kinds. Shipped with spec-kitty; consumed by `CharterPackManager` as the source of truth for "what the default activation set looks like."
2. `src/charter/pack_manager.py` — `CharterPackManager` with five public methods: `activate()`, `deactivate()`, `list_activated()`, `list_available()`, and `merge_defaults()`. Also defines the `YAML_KEY_MAP` constant, `ActivationResult`, and `MergeResult` value objects.

`CharterPackManager` reads and writes `.kittify/config.yaml` using `ruamel.yaml` round-trip mode (preserves comments and formatting). Every method takes `ctx: ProjectContext` as its first parameter.

**Requirement refs**: FR-001, FR-002 (partial setup)

**ATDD rule**: T019 writes all tests in the same WP. No test deletion is required here — these are all new files.

---

## Orientation: Files to Read Before Starting

Before touching any file, read:

1. `src/charter/pack_context.py` — understand `PackContext` fields (`activated_directives`, `activated_tactics`, etc.) and how `from_config()` parses `.kittify/config.yaml`. `CharterPackManager` will write to the same file.
2. `src/charter/invocation_context.py` (WP03 output) — understand `ProjectContext.require_repo_root()` and `require_pack_context()`. All manager methods call these.
3. `src/charter/packs/` — directory does not yet exist; you will create it in T015.
4. Any existing ruamel.yaml usage in the codebase for the standard round-trip pattern:

```bash
grep -r "ruamel" src/specify_cli/ --include="*.py" -l | head -5
```

Pick one of those files and read the round-trip import pattern (typically `from ruamel.yaml import YAML`).

---

## T015 — Create `src/charter/packs/default.yaml`

**Goal**: A YAML file listing all built-in artifact IDs for all 9 activation kinds. This file is the "factory default" state that `CharterPackManager.activate()` materializes when a kind is absent from `config.yaml`.

### Step-by-step

1. Create the directory `src/charter/packs/` (new).
2. Create `src/charter/packs/__init__.py` as an empty file so the directory is a proper Python package (required for `importlib.resources` access in later WPs if needed, and for consistent layout).
3. Create `src/charter/packs/default.yaml` with the following content. The IDs are derived from the built-in doctrine files by stripping the type-suffix and extension (e.g. `001-architectural-integrity-standard.directive.yaml` → `001-architectural-integrity-standard`):

```yaml
# Default charter pack — shipped with spec-kitty.
# Contains all built-in artifact IDs across all 9 activation kinds.
# Do not edit manually; update via spec-kitty upgrade.

mission_type_activations:
  - software-dev
  - documentation
  - research
  - plan

activated_directives:
  - 001-architectural-integrity-standard
  - 003-decision-documentation-requirement
  - 010-specification-fidelity-requirement
  - 018-doctrine-versioning-requirement
  - 024-locality-of-change
  - 025-boy-scout-rule
  - 028-search-tool-discipline
  - 029-agent-commit-signing-policy
  - 030-test-and-typecheck-quality-gate
  - 031-context-aware-design
  - 032-conceptual-alignment
  - 033-targeted-staging-policy
  - 034-test-first-development
  - 035-bulk-edit-occurrence-classification
  - 036-black-box-integration-testing
  - 037-living-documentation-sync
  - 038-structured-prompt-boundary
  - 039-lynn-cole-engineering-culture
  - 040-recurring-bug-structural-intervention

activated_tactics:
  - acceptance-test-first
  - adr-drafting-workflow
  - adversarial-qa-handoff
  - aggregate-boundary-design
  - ammerse-impact-analysis
  - analysis-extract-before-interpret
  - anti-corruption-layer
  - architecture-diagram-review-checklist
  - atdd-adversarial-acceptance
  - atomic-design-review-checklist
  - atomic-state-ownership
  - autonomous-operation-protocol
  - avoid-gold-plating
  - behavior-driven-development
  - black-box-integration-testing
  - boring-code-review
  - bounded-context-canvas-fill
  - bounded-context-identification
  - bug-fixing-checklist
  - c4-zoom-in-architecture-documentation
  - chain-of-responsibility-rule-pipeline
  - change-apply-smallest-viable-diff
  - code-documentation-analysis
  - code-review-incremental
  - compositional-stream-boundaries
  - connascence-analysis
  - context-boundary-inference
  - context-mapping-classification
  - cross-cutting-state-via-store
  - decision-marker-capture
  - deepening-opportunity-assessment
  - dependency-hygiene
  - development-bdd
  - documentation-curation-audit
  - domain-event-capture
  - easy-to-change
  - eisenhower-prioritisation
  - entity-value-object-classification
  - five-paradigm-parallel-debugging
  - focused-function-complexity-check
  - forensic-repository-audit
  - formalized-constraint-testing
  - function-over-form-testing
  - generated-code-stewardship
  - glossary-curation-interview
  - input-validation-fail-fast
  - interface-variation-design
  - language-driven-design
  - locality-of-change
  - mutation-testing-workflow
  - no-parallel-duplicate-test-runs
  - occurrence-classification-workflow
  - premortem-risk-identification
  - problem-decomposition
  - quality-gate-verification
  - reasons-canvas-fill
  - reasons-canvas-review
  - refactoring-change-function-declaration
  - refactoring-combine-functions-into-transform
  - refactoring-conditional-to-strategy
  - refactoring-consolidate-conditional-expression
  - refactoring-encapsulate-record
  - refactoring-encapsulate-variable
  - refactoring-extract-class-by-responsibility-split
  - refactoring-extract-first-order-concept
  - refactoring-guard-clauses-before-polymorphism
  - refactoring-inline-temp
  - refactoring-introduce-null-object
  - refactoring-move-field
  - refactoring-move-method
  - refactoring-replace-magic-number-with-symbolic-constant
  - refactoring-replace-temp-with-query
  - refactoring-retry-pattern
  - refactoring-state-pattern-for-behavior
  - refactoring-strangler-fig
  - reference-architectural-patterns
  - requirements-validation-workflow
  - reverse-speccing
  - review-intent-and-risk-first
  - safe-to-fail-experiment
  - secure-design-checklist
  - secure-regex-catastrophic-backtracking
  - stakeholder-alignment
  - stopping-conditions
  - strategic-domain-classification
  - tdd-red-green-refactor
  - terminology-extraction-mapping
  - test-boundaries-by-responsibility
  - testing-select-appropriate-level
  - test-minimisation
  - test-pyramid-progression
  - test-readability-clarity-check
  - test-to-system-reconstruction
  - traceable-decisions
  - usage-examples-sync
  - work-package-completion-validation
  - zombies-tdd

activated_styleguides:
  - aggregate-design-rules
  - deployable-skill-authoring
  - java-conventions
  - kitty-glossary-writing
  - mutation-aware-test-design
  - python-conventions
  - reasons-canvas-writing
  - testing-principles

activated_toolguides:
  - contextive
  - efficient-local-tooling
  - git-agent-commit-signing
  - maven-review-checks
  - mermaid-diagramming
  - plantuml-diagramming
  - python-mutation-tools
  - python-review-checks
  - rtk-search-tooling
  - typescript-mutation-tools

activated_paradigms:
  - atomic-design
  - behaviour-driven-development
  - brownfield-onboarding
  - c4-incremental-detail-modeling
  - deep-module-design
  - domain-driven-design
  - specification-by-example
  - structured-prompt-driven-development

activated_procedures:
  - bdd-scenario-lifecycle
  - disciplined-defect-diagnosis
  - documentation-gap-prioritization
  - domain-aware-decision-interview
  - drill-down-documentation
  - event-storming-discovery
  - example-mapping-workshop
  - issue-triage-state-machine
  - legacy-codebase-triage
  - migrate-project-guidance-to-spec-kitty-charter
  - refactoring
  - situational-assessment
  - test-first-bug-fixing

activated_agent_profiles:
  - architect-alphonso
  - curator-carla
  - debugger-debbie
  - designer-dagmar
  - frontend-freddy
  - generic-agent
  - human-in-charge
  - implementer-ivan
  - java-jenny
  - node-norris
  - planner-priti
  - python-pedro
  - researcher-robbie
  - retrospective-facilitator
  - reviewer-renata

activated_mission_step_contracts:
  - documentation-accept
  - documentation-audit
  - documentation-design
  - documentation-discover
  - documentation-generate
  - documentation-publish
  - documentation-validate
  - implement
  - plan
  - research-gathering
  - research-methodology
  - research-output
  - research-scoping
  - research-synthesis
  - review
  - specify
  - tasks
```

### Validation

```bash
# YAML is parseable
python -c "
import yaml
with open('src/charter/packs/default.yaml') as f:
    data = yaml.safe_load(f)
kinds = ['mission_type_activations', 'activated_directives', 'activated_tactics',
         'activated_styleguides', 'activated_toolguides', 'activated_paradigms',
         'activated_procedures', 'activated_agent_profiles',
         'activated_mission_step_contracts']
for k in kinds:
    assert k in data, f'Missing key: {k}'
    assert isinstance(data[k], list), f'Not a list: {k}'
    assert len(data[k]) > 0, f'Empty list: {k}'
print('OK —', {k: len(v) for k, v in data.items()})
"
```

---

## T016 — Create `src/charter/pack_manager.py` — value objects + YAML_KEY_MAP

**Goal**: Create the module with `ActivationResult`, `MergeResult`, `YAML_KEY_MAP`, and the `CharterPackManager` class skeleton (method signatures with `raise NotImplementedError` stubs for any not yet implemented).

### File structure

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ruamel.yaml import YAML

if TYPE_CHECKING:
    from charter.invocation_context import ProjectContext

__all__ = [
    "ActivationResult",
    "CharterPackManager",
    "MergeResult",
    "YAML_KEY_MAP",
]
```

### `ActivationResult`

```python
@dataclass
class ActivationResult:
    """Result of a single activate() or deactivate() operation."""

    activated: list[str] = field(default_factory=list)
    deactivated: list[str] = field(default_factory=list)
    cascade_activated: dict[str, list[str]] = field(default_factory=dict)
    cascade_deactivated: dict[str, list[str]] = field(default_factory=dict)
    skipped_shared: dict[str, list[str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
```

### `MergeResult`

```python
@dataclass
class MergeResult:
    """Result of a merge_defaults() operation."""

    kinds_written: list[str] = field(default_factory=list)
    backup_path: Path | None = None
    warnings: list[str] = field(default_factory=list)
```

### `YAML_KEY_MAP`

This is the single lookup table mapping CLI kind names (hyphenated, as typed on the command line) to `config.yaml` YAML keys. The outlier is `mission-type` → `mission_type_activations` (not `activated_mission_types`). Do not use a formatter or string transformation — hardcode the full dict:

```python
YAML_KEY_MAP: dict[str, str] = {
    "mission-type":           "mission_type_activations",
    "directive":              "activated_directives",
    "tactic":                 "activated_tactics",
    "styleguide":             "activated_styleguides",
    "toolguide":              "activated_toolguides",
    "paradigm":               "activated_paradigms",
    "procedure":              "activated_procedures",
    "agent-profile":          "activated_agent_profiles",
    "mission-step-contract":  "activated_mission_step_contracts",
}
```

### `CharterPackManager` skeleton

```python
class CharterPackManager:
    """Manages activation/deactivation of doctrine artifacts in a project's charter pack.

    All methods read from and write to ``.kittify/config.yaml`` using
    ``ruamel.yaml`` round-trip mode (comments and formatting preserved).
    """

    def activate(
        self,
        ctx: ProjectContext,
        kind: str,
        artifact_id: str,
        *,
        cascade: bool = False,
    ) -> ActivationResult:
        """Activate ``artifact_id`` for ``kind`` in the project charter pack."""
        raise NotImplementedError

    def deactivate(
        self,
        ctx: ProjectContext,
        kind: str,
        artifact_id: str,
        *,
        cascade: bool = False,
    ) -> ActivationResult:
        """Deactivate ``artifact_id`` for ``kind`` in the project charter pack."""
        raise NotImplementedError

    def list_activated(
        self,
        ctx: ProjectContext,
    ) -> dict[str, frozenset[str] | None]:
        """Return activated artifact IDs keyed by CLI kind name.

        A ``None`` value means the kind has no explicit activation set
        in ``config.yaml`` (the project has not yet been upgraded to
        the pack-based model for that kind).
        """
        raise NotImplementedError

    def list_available(
        self,
        ctx: ProjectContext,
        kind: str,
    ) -> frozenset[str]:
        """Return all artifact IDs available in doctrine for ``kind``."""
        raise NotImplementedError

    def merge_defaults(
        self,
        ctx: ProjectContext,
    ) -> MergeResult:
        """Merge the default pack into ``config.yaml`` for all absent kinds.

        Only absent keys are written; present keys are not overwritten.
        If ``.kittify/charter/charter.md`` exists it is backed up before any write.
        """
        raise NotImplementedError
```

### Validation

```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
python -c "from charter.pack_manager import YAML_KEY_MAP, ActivationResult, MergeResult, CharterPackManager; print('import OK')"
python -c "from charter.pack_manager import YAML_KEY_MAP; assert len(YAML_KEY_MAP) == 9, len(YAML_KEY_MAP); print('YAML_KEY_MAP OK')"
```

---

## T017 — Implement `CharterPackManager.activate()` and `deactivate()`

**Goal**: Replace the two `raise NotImplementedError` stubs with full implementations.

### Helper: ruamel.yaml round-trip reader/writer

Add a private module-level helper that every mutating method will use:

```python
def _load_config(config_path: Path) -> tuple[Any, YAML]:
    """Load config.yaml using ruamel.yaml round-trip mode.

    Returns (data_dict_or_None, yaml_instance).
    If the file does not exist, returns ({}, yaml_instance).
    """
    yaml = YAML()
    yaml.preserve_quotes = True
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as fh:
            data = yaml.load(fh)
    else:
        data = {}
    if data is None:
        data = {}
    return data, yaml


def _save_config(config_path: Path, data: Any, yaml: YAML) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as fh:
        yaml.dump(data, fh)
```

Import `Any` from `typing` at the top of the file.

### Helper: load `default.yaml`

```python
_DEFAULT_PACK_PATH = Path(__file__).parent / "packs" / "default.yaml"


def _load_default_pack() -> dict[str, list[str]]:
    """Load the built-in default pack IDs from the shipped default.yaml."""
    import yaml as _yaml  # stdlib-safe fallback; ruamel also fine

    with _DEFAULT_PACK_PATH.open("r", encoding="utf-8") as fh:
        return _yaml.safe_load(fh)  # type: ignore[return-value]
```

(Using `yaml.safe_load` from PyYAML here is fine since `default.yaml` is read-only and we do not need round-trip comment preservation for it.)

### `activate()` implementation

```python
def activate(
    self,
    ctx: ProjectContext,
    kind: str,
    artifact_id: str,
    *,
    cascade: bool = False,
) -> ActivationResult:
    repo_root = ctx.require_repo_root()
    config_path = repo_root / ".kittify" / "config.yaml"

    if kind not in YAML_KEY_MAP:
        raise ValueError(
            f"Unknown activation kind '{kind}'. "
            f"Valid kinds: {sorted(YAML_KEY_MAP)}"
        )

    yaml_key = YAML_KEY_MAP[kind]
    data, yaml_inst = _load_config(config_path)
    result = ActivationResult()

    # Materialize from default pack if this kind is absent
    if yaml_key not in data or data[yaml_key] is None:
        default_pack = _load_default_pack()
        default_ids: list[str] = default_pack.get(yaml_key, [])

        # Detect any third-party IDs already in config that would be lost
        # (only relevant if the key exists but is None — safe to skip if absent)
        # Warn if any existing IDs are not in the default pack
        # (None state → no existing IDs to warn about)

        data[yaml_key] = list(default_ids)
        result.warnings.append(
            f"Kind '{kind}' had no explicit activation set. "
            f"Initialized from default pack ({len(default_ids)} entries)."
        )

    current: list[str] = list(data[yaml_key])
    if artifact_id not in current:
        current.append(artifact_id)
        data[yaml_key] = current
        result.activated.append(artifact_id)
    else:
        result.warnings.append(f"'{artifact_id}' is already activated for kind '{kind}'.")

    # Cascade: if cascade=True, follow DRG edges and activate referenced artifacts
    # of all other kinds. For this WP the implementation is a best-effort stub:
    # cascade=True is accepted without error but DRG edge traversal is skipped;
    # a warning is added if cascade was requested.
    if cascade:
        result.warnings.append(
            f"cascade=True requested but DRG edge traversal is not yet implemented "
            f"(deferred to follow-on mission). Manual activation of cross-kind "
            f"dependencies may be required."
        )

    _save_config(config_path, data, yaml_inst)
    return result
```

### `deactivate()` implementation

```python
def deactivate(
    self,
    ctx: ProjectContext,
    kind: str,
    artifact_id: str,
    *,
    cascade: bool = False,
) -> ActivationResult:
    import sys

    repo_root = ctx.require_repo_root()
    config_path = repo_root / ".kittify" / "config.yaml"

    if kind not in YAML_KEY_MAP:
        raise ValueError(
            f"Unknown activation kind '{kind}'. "
            f"Valid kinds: {sorted(YAML_KEY_MAP)}"
        )

    yaml_key = YAML_KEY_MAP[kind]
    data, yaml_inst = _load_config(config_path)
    result = ActivationResult()

    if yaml_key not in data or data[yaml_key] is None:
        # None-state: the project has not been upgraded to the pack model.
        # Modifying individual activations is unsafe without a known baseline.
        print(
            f"Error: Kind '{kind}' has no explicit activation set. "
            f"Run 'spec-kitty upgrade' to initialize the default pack "
            f"before modifying individual activations.",
            file=sys.stderr,
        )
        sys.exit(1)

    current: list[str] = list(data[yaml_key])

    if artifact_id not in current:
        result.warnings.append(
            f"'{artifact_id}' is not in the activation set for kind '{kind}'. "
            f"Nothing to deactivate."
        )
        return result

    current.remove(artifact_id)
    data[yaml_key] = current
    result.deactivated.append(artifact_id)

    if cascade:
        result.warnings.append(
            f"cascade=True requested but DRG shared-reference analysis is not yet "
            f"implemented (deferred to follow-on mission). Cross-kind cascade "
            f"deactivation was skipped."
        )

    _save_config(config_path, data, yaml_inst)
    return result
```

### Validation

```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
python -m mypy src/charter/pack_manager.py --strict 2>&1 | head -20
```

---

## T018 — Implement `list_activated()`, `list_available()`, `merge_defaults()`

**Goal**: Replace the remaining three `raise NotImplementedError` stubs.

### `list_activated()` implementation

`list_activated()` reads the current `PackContext` from `ctx` (already parsed by `PackContext.from_config()`) and converts its `activated_*` fields to the CLI kind → frozenset mapping. A `None` value means the field was absent from `config.yaml`.

```python
def list_activated(
    self,
    ctx: ProjectContext,
) -> dict[str, frozenset[str] | None]:
    pack = ctx.require_pack_context()

    # PackContext fields may be None (absent from config) or list[str] (present).
    # Map back to CLI kind names using YAML_KEY_MAP (invert the dict).
    _yaml_to_kind: dict[str, str] = {v: k for k, v in YAML_KEY_MAP.items()}

    result: dict[str, frozenset[str] | None] = {}
    for kind, yaml_key in YAML_KEY_MAP.items():
        # PackContext stores per-kind activations as attributes
        # named after the yaml_key (e.g. activated_directives).
        raw = getattr(pack, yaml_key, None)
        if raw is None:
            result[kind] = None
        else:
            result[kind] = frozenset(raw)
    return result
```

Note: `getattr(pack, yaml_key, None)` requires that `PackContext` has attributes named exactly `activated_directives`, `activated_tactics`, etc. Verify this against the WP02 `PackContext` definition. If the attribute names differ, adjust the lookup — but do not change `PackContext` (WP02's owned file).

### `list_available()` implementation

`list_available()` scans the doctrine filesystem to find all artifacts of a given kind. It maps CLI kind names to doctrine directory paths:

```python
_KIND_TO_DOCTRINE_DIR: dict[str, tuple[str, str]] = {
    # (relative_path_from_src, filename_suffix)
    "directive":             ("doctrine/directives/built-in", ".directive.yaml"),
    "tactic":                ("doctrine/tactics/built-in", ".tactic.yaml"),
    "styleguide":            ("doctrine/styleguides/built-in", ".styleguide.yaml"),
    "toolguide":             ("doctrine/toolguides/built-in", ".toolguide.yaml"),
    "paradigm":              ("doctrine/paradigms/built-in", ".paradigm.yaml"),
    "procedure":             ("doctrine/procedures/built-in", ".procedure.yaml"),
    "agent-profile":         ("doctrine/agent_profiles/built-in", ".agent.yaml"),
    "mission-type":          ("doctrine/missions/mission_types", ".yaml"),
    "mission-step-contract": (
        "doctrine/missions/built_in_step_contracts", ".step-contract.yaml"
    ),
}


def list_available(
    self,
    ctx: ProjectContext,
    kind: str,
) -> frozenset[str]:
    if kind not in _KIND_TO_DOCTRINE_DIR:
        raise ValueError(
            f"Unknown activation kind '{kind}'. "
            f"Valid kinds: {sorted(_KIND_TO_DOCTRINE_DIR)}"
        )

    rel_dir, suffix = _KIND_TO_DOCTRINE_DIR[kind]
    # Doctrine is installed alongside the charter package in src/
    src_root = Path(__file__).parent.parent  # src/charter/.. → src/
    doctrine_dir = src_root / rel_dir

    if not doctrine_dir.is_dir():
        return frozenset()

    ids: set[str] = set()
    for yaml_file in doctrine_dir.rglob(f"*{suffix}"):
        # Strip the suffix to get the ID
        stem = yaml_file.name[: -len(suffix)]
        ids.add(stem)
    return frozenset(ids)
```

### `merge_defaults()` implementation

```python
def merge_defaults(
    self,
    ctx: ProjectContext,
) -> MergeResult:
    from datetime import datetime, timezone

    repo_root = ctx.require_repo_root()
    config_path = repo_root / ".kittify" / "config.yaml"
    charter_path = repo_root / ".kittify" / "charter" / "charter.md"

    result = MergeResult()

    # Backup charter.md if it exists before any write
    if charter_path.exists():
        ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_dir = repo_root / ".kittify" / "charter" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"charter-{ts}.md"
        backup_path.write_bytes(charter_path.read_bytes())
        result.backup_path = backup_path

    data, yaml_inst = _load_config(config_path)
    default_pack = _load_default_pack()

    for yaml_key in YAML_KEY_MAP.values():
        if yaml_key not in data or data[yaml_key] is None:
            default_ids = default_pack.get(yaml_key, [])
            data[yaml_key] = list(default_ids)
            # Map yaml_key back to CLI kind for the result
            kind = next(k for k, v in YAML_KEY_MAP.items() if v == yaml_key)
            result.kinds_written.append(kind)

    if result.kinds_written:
        _save_config(config_path, data, yaml_inst)

    return result
```

### Validation

```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
python -m mypy src/charter/pack_manager.py --strict 2>&1 | head -20
python -c "
from charter.pack_manager import CharterPackManager, YAML_KEY_MAP
mgr = CharterPackManager()
# Verify all 5 methods exist and are callable
assert callable(mgr.activate)
assert callable(mgr.deactivate)
assert callable(mgr.list_activated)
assert callable(mgr.list_available)
assert callable(mgr.merge_defaults)
print('All methods present OK')
"
```

---

## T019 — Write `tests/charter/test_pack_manager.py`

**Goal**: Full unit test coverage for `CharterPackManager` and its supporting objects.

### File location

`tests/charter/test_pack_manager.py` (new file). `tests/charter/__init__.py` must exist (created in WP03 if missing).

### Imports and fixtures

```python
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

from charter.invocation_context import ProjectContext
from charter.pack_manager import (
    ActivationResult,
    CharterPackManager,
    MergeResult,
    YAML_KEY_MAP,
)

pytestmark = pytest.mark.unit
```

### Fixture: minimal project root

```python
@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Create a minimal .kittify/ directory with an empty config.yaml."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text("# empty config\n", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def ctx(project_root: Path) -> ProjectContext:
    """ProjectContext built from the minimal project root."""
    return ProjectContext.from_repo(project_root)


@pytest.fixture()
def manager() -> CharterPackManager:
    return CharterPackManager()
```

### Test cases — `YAML_KEY_MAP`

```python
class TestYamlKeyMap:
    def test_has_exactly_nine_entries(self) -> None:
        assert len(YAML_KEY_MAP) == 9

    def test_mission_type_maps_to_correct_key(self) -> None:
        assert YAML_KEY_MAP["mission-type"] == "mission_type_activations"

    def test_directive_maps_to_activated_directives(self) -> None:
        assert YAML_KEY_MAP["directive"] == "activated_directives"

    def test_all_values_start_with_activated_or_mission(self) -> None:
        for kind, yaml_key in YAML_KEY_MAP.items():
            assert yaml_key.startswith("activated_") or yaml_key == "mission_type_activations", (
                f"Key '{kind}' maps to unexpected yaml_key '{yaml_key}'"
            )
```

### Test cases — `activate()` None-state (materialize from default)

```python
class TestActivateNoneState:
    def test_activates_new_artifact_from_empty_config(
        self, manager: CharterPackManager, ctx: ProjectContext, project_root: Path
    ) -> None:
        """Activating on a fresh config materializes the default pack then adds the ID."""
        result = manager.activate(ctx, kind="directive", artifact_id="my-custom-directive")
        assert "my-custom-directive" in result.activated
        # config.yaml must now contain the key
        config = project_root / ".kittify" / "config.yaml"
        data = yaml.safe_load(config.read_text())
        assert "my-custom-directive" in data["activated_directives"]

    def test_warns_about_initialization_from_default(
        self, manager: CharterPackManager, ctx: ProjectContext
    ) -> None:
        result = manager.activate(ctx, kind="directive", artifact_id="x-new")
        assert any("initialized from default pack" in w.lower() for w in result.warnings)

    def test_default_ids_are_present_after_materialize(
        self, manager: CharterPackManager, ctx: ProjectContext, project_root: Path
    ) -> None:
        manager.activate(ctx, kind="directive", artifact_id="x-new")
        config = project_root / ".kittify" / "config.yaml"
        data = yaml.safe_load(config.read_text())
        # At least one canonical built-in directive must be present
        assert "001-architectural-integrity-standard" in data["activated_directives"]
```

### Test cases — `activate()` existing activation set

```python
class TestActivateExistingSet:
    def test_appends_to_existing_list(
        self, manager: CharterPackManager, project_root: Path
    ) -> None:
        config = project_root / ".kittify" / "config.yaml"
        config.write_text(
            "activated_directives:\n  - 001-architectural-integrity-standard\n",
            encoding="utf-8",
        )
        ctx = ProjectContext.from_repo(project_root)
        result = manager.activate(ctx, kind="directive", artifact_id="new-directive")
        assert "new-directive" in result.activated
        data = yaml.safe_load(config.read_text())
        assert "001-architectural-integrity-standard" in data["activated_directives"]
        assert "new-directive" in data["activated_directives"]

    def test_no_duplicate_on_double_activate(
        self, manager: CharterPackManager, project_root: Path
    ) -> None:
        config = project_root / ".kittify" / "config.yaml"
        config.write_text(
            "activated_directives:\n  - already-here\n",
            encoding="utf-8",
        )
        ctx = ProjectContext.from_repo(project_root)
        manager.activate(ctx, kind="directive", artifact_id="already-here")
        data = yaml.safe_load(config.read_text())
        assert data["activated_directives"].count("already-here") == 1

    def test_comments_preserved_in_config(
        self, manager: CharterPackManager, project_root: Path
    ) -> None:
        config = project_root / ".kittify" / "config.yaml"
        config.write_text(
            "# project-level comment\nactivated_directives:\n  - existing\n",
            encoding="utf-8",
        )
        ctx = ProjectContext.from_repo(project_root)
        manager.activate(ctx, kind="directive", artifact_id="new-one")
        raw = config.read_text()
        assert "# project-level comment" in raw
```

### Test cases — `activate()` invalid kind

```python
class TestActivateInvalidKind:
    def test_raises_value_error_for_unknown_kind(
        self, manager: CharterPackManager, ctx: ProjectContext
    ) -> None:
        with pytest.raises(ValueError, match="Unknown activation kind"):
            manager.activate(ctx, kind="nonexistent-kind", artifact_id="x")
```

### Test cases — `deactivate()` None-state (exit 1)

```python
class TestDeactivateNoneState:
    def test_exits_with_upgrade_guidance_when_no_activation_set(
        self, manager: CharterPackManager, ctx: ProjectContext, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """deactivate() on a None-state kind must exit 1 with guidance message."""
        with pytest.raises(SystemExit) as exc_info:
            manager.deactivate(ctx, kind="directive", artifact_id="something")
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "spec-kitty upgrade" in captured.err
```

### Test cases — `deactivate()` existing activation set

```python
class TestDeactivateExistingSet:
    def test_removes_artifact_from_list(
        self, manager: CharterPackManager, project_root: Path
    ) -> None:
        config = project_root / ".kittify" / "config.yaml"
        config.write_text(
            "activated_directives:\n  - keep-me\n  - remove-me\n",
            encoding="utf-8",
        )
        ctx = ProjectContext.from_repo(project_root)
        result = manager.deactivate(ctx, kind="directive", artifact_id="remove-me")
        assert "remove-me" in result.deactivated
        data = yaml.safe_load(config.read_text())
        assert "remove-me" not in data["activated_directives"]
        assert "keep-me" in data["activated_directives"]

    def test_warns_when_artifact_not_in_set(
        self, manager: CharterPackManager, project_root: Path
    ) -> None:
        config = project_root / ".kittify" / "config.yaml"
        config.write_text(
            "activated_directives:\n  - something-else\n",
            encoding="utf-8",
        )
        ctx = ProjectContext.from_repo(project_root)
        result = manager.deactivate(ctx, kind="directive", artifact_id="not-present")
        assert result.deactivated == []
        assert any("not in the activation set" in w for w in result.warnings)
```

### Test cases — `merge_defaults()`

```python
class TestMergeDefaults:
    def test_writes_absent_keys(
        self, manager: CharterPackManager, ctx: ProjectContext, project_root: Path
    ) -> None:
        result = manager.merge_defaults(ctx)
        assert len(result.kinds_written) == 9  # all 9 kinds were absent
        config = project_root / ".kittify" / "config.yaml"
        data = yaml.safe_load(config.read_text())
        for yaml_key in YAML_KEY_MAP.values():
            assert yaml_key in data, f"Missing key after merge_defaults: {yaml_key}"

    def test_does_not_overwrite_present_keys(
        self, manager: CharterPackManager, project_root: Path
    ) -> None:
        config = project_root / ".kittify" / "config.yaml"
        config.write_text(
            "activated_directives:\n  - only-mine\n",
            encoding="utf-8",
        )
        ctx = ProjectContext.from_repo(project_root)
        result = manager.merge_defaults(ctx)
        data = yaml.safe_load(config.read_text())
        # existing directive key must not be overwritten
        assert data["activated_directives"] == ["only-mine"]
        # other 8 absent kinds must have been written
        assert "directive" not in result.kinds_written
        assert len(result.kinds_written) == 8

    def test_creates_backup_when_charter_exists(
        self, manager: CharterPackManager, ctx: ProjectContext, project_root: Path
    ) -> None:
        charter_dir = project_root / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        charter_file = charter_dir / "charter.md"
        charter_file.write_text("# My Charter\n", encoding="utf-8")

        result = manager.merge_defaults(ctx)
        assert result.backup_path is not None
        assert result.backup_path.exists()
        assert result.backup_path.read_text() == "# My Charter\n"
        assert result.backup_path.parent.name == "backups"

    def test_no_backup_when_no_charter(
        self, manager: CharterPackManager, ctx: ProjectContext
    ) -> None:
        result = manager.merge_defaults(ctx)
        assert result.backup_path is None
```

### Final validation commands

```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
python -m pytest tests/charter/test_pack_manager.py -x -v 2>&1 | tail -40
```

---

## Definition of Done

All of the following must hold before this WP is marked `for_review`:

1. `src/charter/packs/default.yaml` exists with all 9 activation-kind keys populated from built-in doctrine.
2. `src/charter/packs/__init__.py` exists (empty).
3. `src/charter/pack_manager.py` defines `ActivationResult`, `MergeResult`, `YAML_KEY_MAP` (9 entries), and `CharterPackManager` with all 5 public methods implemented.
4. `YAML_KEY_MAP["mission-type"] == "mission_type_activations"` (the outlier mapping is explicit, not computed).
5. `tests/charter/test_pack_manager.py` exists and all tests pass.
6. `ruamel.yaml` round-trip is used for all writes; config.yaml comments are preserved (verified by the comment-preservation test in T019).
7. **Cascade deferral explicitly documented**: `cascade=True` is accepted by `activate()` and `deactivate()` without error, but DRG edge traversal is NOT implemented in this WP (deferred to a follow-on mission). A warning message is emitted when `cascade=True` is passed. FR-008 (warn on no-cascade) is satisfied by this warning; FR-006 and FR-007 (DRG traversal cascade) are explicitly deferred. This is intentional scope control, not a defect.

### Final validation commands

```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty

# 1. Unit tests
python -m pytest tests/charter/test_pack_manager.py -x -q

# 2. mypy strict on both new modules
python -m mypy src/charter/pack_manager.py --strict

# 3. ruff
cd src && ruff check charter/pack_manager.py && ruff check charter/packs/
cd ..

# 4. default.yaml is valid and has 9 keys
python -c "
import yaml
with open('src/charter/packs/default.yaml') as f:
    data = yaml.safe_load(f)
expected = {
    'mission_type_activations', 'activated_directives', 'activated_tactics',
    'activated_styleguides', 'activated_toolguides', 'activated_paradigms',
    'activated_procedures', 'activated_agent_profiles',
    'activated_mission_step_contracts',
}
assert set(data.keys()) == expected, set(data.keys()) - expected
print('default.yaml OK')
"

# 5. YAML_KEY_MAP has exactly 9 entries with correct mission-type outlier
python -c "
from charter.pack_manager import YAML_KEY_MAP
assert len(YAML_KEY_MAP) == 9
assert YAML_KEY_MAP['mission-type'] == 'mission_type_activations'
print('YAML_KEY_MAP OK')
"
```

## Activity Log

- 2026-05-31T13:58:08Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=4151579 – Assigned agent via action command
