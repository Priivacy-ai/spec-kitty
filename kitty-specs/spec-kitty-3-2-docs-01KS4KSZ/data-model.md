# Data Model: Spec Kitty 3.2 Documentation Refresh

**Mission**: `spec-kitty-3-2-docs-01KS4KSZ` | **Phase**: 1 (Design) | **Date**: 2026-05-21

All shapes below are filesystem-backed. The Python representations are `@dataclass(slots=True, frozen=True)` (or `TypedDict` for shapes loaded from YAML where mutation is needed before validation). Every entity is read-only at run time from the docs tooling's perspective; mutation happens through editorial edits to the underlying markdown/YAML.

---

## VersionTag (enum)

Canonical version-relevance classification (FR-001).

```python
class VersionTag(StrEnum):
    CURRENT = "current"        # 3.2-current
    SUPPORTED = "supported"    # 3.1-relevant, not 3.2-complete
    ARCHIVAL = "archival"      # 1.x or 2.x
    MIGRATION = "migration"    # version transition guidance
    INTERNAL = "internal"      # dev-only / non-public
```

Validation: every docs page that appears in the page inventory must map to exactly one tag.

---

## DivioType (enum)

```python
class DivioType(StrEnum):
    TUTORIAL = "tutorial"
    HOW_TO = "how-to"
    REFERENCE = "reference"
    EXPLANATION = "explanation"
    NONE = "none"              # planning artifacts, READMEs, etc. that don't fit Divio
```

---

## PageInventoryEntry

Row in `docs/development/3-2-page-inventory.yaml`. Loaded with `ruamel.yaml`.

```python
@dataclass(slots=True, frozen=True)
class PageInventoryEntry:
    path: str                  # repo-relative path, e.g., "docs/how-to/install-macos.md"
    tag: VersionTag
    divio_type: DivioType
    owning_workstream: str     # one of "A","B","C","D","E","F" or "none"
    current_target: bool       # True if this page is expected to appear in 3.2-current nav
    citation_refs: list[str]   # external URLs cited; empty list for non-harness pages
    notes: str | None          # optional one-line context
```

YAML on disk (one row per page):

```yaml
- path: docs/how-to/install-macos.md
  tag: current
  divio_type: how-to
  owning_workstream: E
  current_target: true
  citation_refs: []
  notes: pip/pipx/uv on macOS

- path: docs/1x/index.md
  tag: archival
  divio_type: none
  owning_workstream: C
  current_target: false
  citation_refs: []
  notes: 1.x archive landing page
```

Validation rules:
- `path` must point to an existing file under `docs/`, `architecture/`, or root.
- If `tag == archival`, then `current_target == false`.
- If `tag == current`, then `current_target == true`.
- If `tag == migration`, the file body must contain a migration banner pattern (regex defined in the leakage-check contract).

---

## CommandPathEntry

Result of walking the live Typer app. Materialised in memory by `scripts/docs/_typer_walker.py`; not persisted to disk except as a build artifact under `scripts/docs/_cache/` (gitignored).

```python
@dataclass(slots=True, frozen=True)
class CommandPathEntry:
    path: tuple[str, ...]      # ("spec-kitty","agent","decision","open")
    kind: Literal["command", "group"]
    hidden: bool
    deprecated: bool
    help_summary: str          # the first line / short description rendered by Typer
    source_file: str | None    # best-effort; populated where introspection can locate it
    source_function: str | None
    requires_saas_sync: bool   # True if this path only materialises with SPEC_KITTY_ENABLE_SAAS_SYNC=1
```

Validation:
- `path[0] == "spec-kitty"` for every entry.
- `kind == "group"` implies the entry contributes only structure, not a leaf command.
- `requires_saas_sync == True` for descendants of `tracker` and for `issue-search` (per `cli-audit-3-2.md`).

---

## MetaIssueEntry

Row in `docs/development/3-2-cli-reference-audit-meta-issues.md` (FR-010). Stored as a markdown table; loadable into the shape below for `check_cli_reference_freshness.py` cross-checks.

```python
class ProblemType(StrEnum):
    INACCURATE = "inaccurate"
    INCOMPLETE = "incomplete"
    STALE = "stale"
    MISSING = "missing"
    CONFUSING = "confusing"
    VERSION_LEAKAGE = "version_leakage"

class BlockingStatus(StrEnum):
    BLOCKING = "blocking"             # blocks publication
    NON_BLOCKING = "non_blocking"     # acknowledged, not blocking
    RESOLVED = "resolved"             # fixed in code and verified

@dataclass(slots=True, frozen=True)
class MetaIssueEntry:
    command_path: str                 # space-joined, e.g., "spec-kitty agent decision open"
    source_file: str                  # e.g., "src/specify_cli/cli/commands/agent_decision.py"
    source_function: str | None
    observed_help: str
    observed_behavior_or_test_evidence: str
    problem_type: ProblemType
    recommended_fix: str
    owner_area: str                   # e.g., "agent", "tracker", "doctor", "core"
    blocking_status: BlockingStatus
```

Validation: every row references a real command path or explicitly states "PATH NO LONGER VISIBLE" in `observed_help` for stale entries.

---

## HarnessEntry

Row in the harness support matrix (`docs/reference/supported-harnesses.md`) and per-harness pages.

```python
class HarnessMechanism(StrEnum):
    SLASH_COMMAND = "slash_command"
    PROMPT = "prompt"
    WORKFLOW = "workflow"
    SKILL = "skill"
    COMMAND_FILE = "command_file"
    CONFIG = "config"

class SupportTier(StrEnum):
    FIRST_CLASS = "first_class"
    SUPPORTED = "supported"
    PARTIAL = "partial"
    EXPERIMENTAL = "experimental"
    ARCHIVED = "archived"

@dataclass(slots=True, frozen=True)
class HarnessEntry:
    name: str                          # display name, e.g., "Claude Code"
    key: str                           # short identifier, e.g., "claude"
    repo_directory: str                # e.g., ".claude/commands" — installed surface
    mechanism: HarnessMechanism
    support_tier: SupportTier
    external_doc_citations: list[str]  # at least one for tier >= supported
    page_path: str | None              # docs/how-to/harnesses/<key>.md when promoted
    notes: str | None
```

Validation:
- `support_tier in {first_class, supported}` requires `external_doc_citations` non-empty.
- `support_tier == archived` requires `page_path` to live under `docs/migration/` or be absent.
- `key` is unique across the matrix.

---

## InstallTargetEntry

One cell of the (tool × OS) install matrix (FR-017).

```python
class InstallTool(StrEnum):
    PIP = "pip"
    PIPX = "pipx"
    UV_TOOL = "uv_tool"

class OS(StrEnum):
    MACOS = "macos"
    LINUX = "linux"
    WINDOWS = "windows"

@dataclass(slots=True, frozen=True)
class InstallTargetEntry:
    tool: InstallTool
    os: OS
    install_command: str               # e.g., "uv tool install spec-kitty-cli"
    upgrade_command: str
    uninstall_command: str
    verification_command: str          # e.g., "spec-kitty --version"
    platform_notes: list[str]          # PATH, PowerShell, py-launcher caveats
    docs_page: str                     # repo-relative path of the how-to that covers this cell
```

Validation: nine entries total (3 tools × 3 OSes); every entry has a non-empty `install_command`, `upgrade_command`, `uninstall_command`, and `verification_command`.

---

## FreshnessReport

Output of `scripts/docs/check_docs_freshness.py` (FR-020).

```python
@dataclass(slots=True, frozen=True)
class FreshnessFinding:
    rule_id: str                       # e.g., "REF-MISSING", "REF-EXTRA", "LEAK-CURRENT-LINKS-ARCHIVAL"
    severity: Literal["error", "warning"]
    location: str                      # path or "(virtual)"
    message: str
    suggested_action: str

@dataclass(slots=True, frozen=True)
class FreshnessReport:
    started_at: str                    # ISO8601
    cli_version: str                   # pyproject.toml version
    visible_paths_count: int
    reference_entries_count: int
    inventory_rows_count: int
    findings: list[FreshnessFinding]
    saas_sync_flag: bool               # was SPEC_KITTY_ENABLE_SAAS_SYNC=1 in effect?
    exit_code: Literal[0, 1, 2, 3]     # 0 clean / 1 violations / 2 input errors / 3 environmental setup errors
```

Validation:
- `exit_code == 0` ↔ `findings` contains no `severity == "error"` entries.
- If `saas_sync_flag == False`, the report includes a top-level `WARN: tracker/issue-search not captured` finding (rule_id `ENV-SAAS-SYNC-OFF`) but does not block publication on its own.

---

## OccurrenceMap (bulk-edit guardrail)

Loaded from `kitty-specs/spec-kitty-3-2-docs-01KS4KSZ/occurrence_map.yaml` when workstream A2 (frontmatter rollout) or workstream C (archive/migration moves) is in flight. Tasks-phase artifact, not implemented by tooling here; documented for plan completeness.

```yaml
change_mode: bulk_edit
identifier: version_tag
categories:
  code_symbols:
    action: not_applicable
  import_paths:
    action: not_applicable
  filesystem_paths:
    action: rewrite
    occurrences:
      - path: docs/1x/**
        from_pattern: docs/1x/
        to_pattern: docs/archive/1x/
      - path: docs/2x/**
        from_pattern: docs/2x/
        to_pattern: docs/archive/2x/
  serialized_keys:
    action: add
    occurrences:
      - file_glob: docs/**/*.md
        key: version_tag
        rule: per-page from page-inventory.yaml
  cli_commands:
    action: not_applicable
  user_facing_strings:
    action: review
    occurrences:
      - context: archive banners in moved 1.x/2.x pages
  tests_fixtures:
    action: not_applicable
  logs_telemetry:
    action: not_applicable
```

---

## Cross-entity invariants

1. For every `CommandPathEntry` with `hidden == False`, the `docs/reference/cli-commands.md` file contains a heading or inline mention naming the full path. Enforced by the architectural test and by `check_cli_reference_freshness.py`.
2. For every `PageInventoryEntry` with `tag == current` and `current_target == True`, the file at `path` either contains a `version_tag: current` frontmatter line or is exempt because it predates the rollout and is on the deferred-frontmatter list within `3-2-page-inventory.yaml`.
3. The set of `HarnessEntry.support_tier in {first_class, supported}` matches the set of pages under `docs/how-to/harnesses/` once decision `01KS4KTS4V300M9MMTS1AJEGXY` is resolved or its plan default ("matrix-first promotion") applies.
4. The set of `InstallTargetEntry` cells is exhaustive: nine entries, no duplicates, every entry maps to exactly one `docs_page`.
5. `MetaIssueEntry` rows with `blocking_status == BLOCKING` block the publication checklist (FR-021); rows marked `RESOLVED` may be referenced from CHANGELOG entries.
