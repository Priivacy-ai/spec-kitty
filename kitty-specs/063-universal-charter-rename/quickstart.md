# Quickstart: Universal Charter Rename

**Feature**: 063-universal-charter-rename
**Date**: 2026-04-04 (revised)

## Implementation Order

```
WP01 (core packages) ──┐
                        ├──→ WP03 (imports + build) ──┐
WP02 (CLI + runtime)  ─┘                              │
                                                       ├──→ WP07 (tests) ──┐
WP04 (doctrine + skills) → WP05 (agent artifacts)     │                    ├──→ WP08 (docs + acceptance)
                                                       │                    │
WP06 (migration overhaul) ────────────────────────────┘────────────────────┘
```

Start with WP01 + WP02 + WP04 in parallel, then cascade.

## Rename Checklist Per File

For every renamed file:
1. `git mv old_path new_path`
2. Replace "constitution" → "charter" in all content (case-preserving: Constitution → Charter, CONSTITUTION → CHARTER)
3. Rename classes/functions that contain "constitution" (see data-model.md Symbol Renames)
4. Update imports in the file itself

## Critical Rules

1. **Old migrations become STUBS** — do NOT rewrite their detect()/apply() logic; replace entire class body with no-op stub returning False/success
2. **Use `git mv`** for all renames to preserve history
3. **Case-preserving replacement**: `constitution` → `charter`, `Constitution` → `Charter`, `CONSTITUTION` → `CHARTER`
4. **Test after each WP**: `python -m pytest tests/ -x -q` (adjust for renamed test paths)
5. **Content rewriting in migration**: The charter-rename migration must find-replace "constitution" in generated `.kittify/` files AND agent prompt bootstrap commands
6. **Metadata normalization**: Must run at load time BEFORE the migration loop

## Old Migration Stub Template

```python
@MigrationRegistry.register
class CharterCleanupMigration(BaseMigration):
    migration_id = "0.10.12_charter_cleanup"
    description = "Superseded by 3.1.1_charter_rename"
    target_version = "0.10.12"

    def detect(self, project_path: Path) -> bool:
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        return False, "Superseded by charter-rename migration"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        return MigrationResult(success=True, warnings=["Superseded by charter-rename"])
```

## Metadata Normalization Template

```python
# In metadata.py
_LEGACY_MIGRATION_ID_MAP: dict[str, str] = {
    "0.10.12_constitution_cleanup": "0.10.12_charter_cleanup",
    "0.13.0_update_constitution_templates": "0.13.0_update_charter_templates",
    "2.0.0_constitution_directory": "2.0.0_charter_directory",
    "2.0.2_constitution_context_bootstrap": "2.0.2_charter_context_bootstrap",
    "2.1.2_fix_constitution_doctrine_skill": "2.1.2_fix_charter_doctrine_skill",
}

def _normalize_legacy_ids(self) -> bool:
    """Rewrite constitution-era migration IDs to charter-era IDs."""
    changed = False
    for record in self.applied_migrations:
        new_id = _LEGACY_MIGRATION_ID_MAP.get(record.id)
        if new_id:
            record.id = new_id
            changed = True
    return changed
```

## Charter-Rename Migration Template

```python
@MigrationRegistry.register
class CharterRenameMigration(BaseMigration):
    migration_id = "3.1.1_charter_rename"
    description = "Comprehensive charter rename: migrate all constitution-era state"
    target_version = "3.1.1"

    def detect(self, project_path: Path) -> bool:
        kittify = project_path / ".kittify"
        # Layout A
        if (kittify / "constitution").exists():
            return True
        # Layout B
        if (kittify / "memory" / "constitution.md").exists():
            return True
        # Layout C
        missions = kittify / "missions"
        if missions.exists():
            for m in missions.iterdir():
                if m.is_dir() and (m / "constitution").exists():
                    return True
        return False

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        changes = []
        kittify = project_path / ".kittify"
        charter_dir = kittify / "charter"

        # Phase 1: Layout normalization
        # ... handle Layout C, B, A, partial state
        
        # Phase 2: Content rewriting
        # For all text files in charter_dir:
        #   case-insensitive replace "constitution" → "charter"
        # For deployed agent prompts:
        #   replace "spec-kitty constitution context" → "spec-kitty charter context"
        
        # Phase 3: Agent artifact rename
        # Rename spec-kitty.constitution.md → spec-kitty.charter.md
        # Rename spec-kitty-constitution-doctrine/ → spec-kitty-charter-doctrine/
        
        # Phase 4: Metadata normalization
        # Rewrite old migration IDs in metadata.yaml
        
        return MigrationResult(success=True, changes_made=changes)
```

## Verification Commands

```bash
# Primary acceptance gate (zero matches outside 2 bounded exception files)
rg -n -i constitution . \
  --glob '!CHANGELOG.md' \
  --glob '!kitty-specs/' \
  --glob '!src/specify_cli/upgrade/migrations/m_3_1_1_charter_rename.py' \
  --glob '!src/specify_cli/upgrade/metadata.py'

# Filename gate (zero filenames with "constitution")
find . -name '*constitution*' -not -path './kitty-specs/*' -not -path './.git/*'

# Run tests
python -m pytest tests/ -x -q

# Type checking
mypy --strict src/charter/ src/specify_cli/charter/

# Verify old migration stubs contain zero "constitution"
for f in src/specify_cli/upgrade/migrations/m_0_10_12_*.py \
         src/specify_cli/upgrade/migrations/m_0_13_0_*.py \
         src/specify_cli/upgrade/migrations/m_2_0_0_*.py \
         src/specify_cli/upgrade/migrations/m_2_0_2_*.py \
         src/specify_cli/upgrade/migrations/m_2_1_2_*.py; do
  rg -i constitution "$f" && echo "FAIL: $f still contains constitution" || true
done
```

## Backward-Compatibility Exception Audit

After implementation, only these 2 files should contain "constitution":

| File | Expected matches | Justification |
|------|-----------------|---------------|
| `src/specify_cli/upgrade/migrations/m_3_1_1_charter_rename.py` | ~10-15 | Path literals to detect old filesystem state |
| `src/specify_cli/upgrade/metadata.py` | 5 | Legacy migration ID lookup keys |

Any other file with "constitution" (outside CHANGELOG.md and kitty-specs/) is a bug.
