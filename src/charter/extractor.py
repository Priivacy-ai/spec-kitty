"""Charter extraction pipeline.

Maps parsed charter sections to validated Pydantic models:
- governance.yaml (testing, quality, performance, branch strategy)
- directives.yaml (numbered rules and enforcement)
- metadata.yaml (extraction provenance and statistics)
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kernel._safe_re import re

from charter.activations import ActivationEntry
from charter.hasher import hash_content
from doctrine.versioning import CURRENT_BUNDLE_SCHEMA_VERSION
from charter.parser import CharterParser, CharterSection
from charter.schemas import (
    BranchStrategyConfig,
    CommitConfig,
    DoctrineSelectionConfig,
    Directive,
    DirectivesConfig,
    ExtractionMetadata,
    GovernanceConfig,
    PerformanceConfig,
    QualityConfig,
    SectionsParsed,
    CharterTestingConfig,
    emit_yaml,
)

__all__ = [
    "Extractor",
    "write_extraction_result",
]


logger = logging.getLogger(__name__)

# Section heading keywords → (target_schema, target_field)
SECTION_MAPPING: dict[str, tuple[str, str]] = {
    "testing": ("governance", "testing"),
    "test": ("governance", "testing"),
    "coverage": ("governance", "testing"),
    "quality": ("governance", "quality"),
    "lint": ("governance", "quality"),
    "commit": ("governance", "commits"),
    "performance": ("governance", "performance"),
    "branch": ("governance", "branch_strategy"),
    "paradigm": ("governance", "doctrine"),
    "tool": ("governance", "doctrine"),
    "template": ("governance", "doctrine"),
    "directive": ("directives", "directives"),
    "constraint": ("directives", "directives"),
    "rule": ("directives", "directives"),
    # WP02: "Code Review Checklist" sections produce directive entries so the
    # body of each bullet item can be scanned for catalog citations
    # (FR-006). Keyed on the compound "code review" rather than the bare
    # "checklist" to avoid accidentally classifying unrelated sections
    # (e.g. "Deployment Checklist") as directives.
    "code review": ("directives", "directives"),
}


# WP02: regex helpers for catalog-citation detection inside directive bodies.
# Per contract `contracts/charter-sync-cross-link.md`:
#   - Every ``DIRECTIVE_NNN`` match is lifted into ``Directive.references``
#     (no further filter applied — every match counts).
#   - Every kebab-case slug is lifted ONLY when ``tactic_registry(slug)`` is
#     truthy, i.e. the slug names a real ``DoctrineService.tactics`` entry.
#     This prevents false positives on incidental kebab-case words
#     (e.g. ``pre-commit-hooks`` is not a tactic; ``language-driven-design`` is).
_DIRECTIVE_CITATION_RE = re.compile(r"\bDIRECTIVE_(\d{3})\b")
_TACTIC_SLUG_RE = re.compile(r"\b([a-z][a-z0-9]*(?:-[a-z0-9]+){1,4})\b")
_GENERATED_DIRECTIVE_PLACEHOLDER_RE = re.compile(
    r"^Apply doctrine directive `(?P<directive_id>[A-Z][A-Z0-9_/-]*)` "
    r"to planning and implementation decisions\.?$"
)


# WP02: bullet-list pattern used as a fallback inside directive sections that
# carry `-` bullets rather than `1. ` numbered items (e.g. "Code Review
# Checklist"). Extraction of bullet items is gated on the section being
# classified as a directive section AND the section not already exposing
# numbered items.
_BULLET_ITEM_RE = re.compile(r"^[ \t]*-[ \t]+(.+(?:\n[ \t]+.+)*)", re.MULTILINE)


def _detect_catalog_references(
    body: str,
    *,
    tactic_registry: Callable[[str], bool],
) -> list[str]:
    """Return catalog IDs cited inside *body*.

    The detector implements the contract documented in
    ``contracts/charter-sync-cross-link.md``:

    - Every ``DIRECTIVE_NNN`` match becomes the literal string
      ``"DIRECTIVE_NNN"``.
    - Every kebab-case slug for which ``tactic_registry(slug)`` returns True
      is added as that slug.
    - Duplicates are removed; **order is first-seen** so diffs stay
      deterministic.

    ``tactic_registry`` is injected by the caller (``charter.sync.sync``)
    rather than constructed here — the extractor stays decoupled from
    ``DoctrineService`` construction. If the caller cannot build a
    registry (e.g. the built-in catalog is unavailable), it MUST pass a
    callable that always returns False; the directive detector still
    runs as a result.
    """
    if not body:
        return []

    seen: dict[str, None] = {}

    # Find DIRECTIVE_NNN and tactic-slug citations in document order, so that
    # references stay deterministic regardless of which kind appears first.
    matches: list[tuple[int, str]] = []

    for match in _DIRECTIVE_CITATION_RE.finditer(body):
        digits = match.group(1)
        matches.append((match.start(), f"DIRECTIVE_{digits}"))

    for match in _TACTIC_SLUG_RE.finditer(body):
        slug = match.group(1)
        # Membership-gate: only consider a slug a tactic when the registry
        # confirms it. The empty default callable returns False, which makes
        # this loop a no-op when the caller had no DoctrineService.
        try:
            is_tactic = bool(tactic_registry(slug))
        except Exception:  # noqa: BLE001 - defensive: registry failures must
            # never break charter sync. The contract says we silently emit no
            # tactic references when the registry cannot answer.
            is_tactic = False
        if is_tactic:
            matches.append((match.start(), slug))

    matches.sort(key=lambda pair: pair[0])

    for _pos, ref in matches:
        if ref not in seen:
            seen[ref] = None

    return list(seen.keys())


@dataclass
class ExtractionResult:
    """Complete extraction result with all config schemas and metadata."""

    governance: GovernanceConfig
    directives: DirectivesConfig
    metadata: ExtractionMetadata
    warnings: list[str]


class Extractor:
    """Extract structured configuration from parsed charter sections."""

    def __init__(
        self,
        parser: CharterParser | None = None,
        *,
        tactic_registry: Callable[[str], bool] | None = None,
    ):
        """Initialize extractor with optional parser.

        Args:
            parser: CharterParser instance (creates default if None).
            tactic_registry: Optional predicate that returns True when its
                input names a real ``DoctrineService.tactics`` entry. Used
                by :func:`_detect_catalog_references` to filter out
                false-positive kebab-case slugs (R-5 in the WP02 plan). The
                default callable always returns False — that is the
                contract-safe fallback when no doctrine service is
                available (see ``contracts/charter-sync-cross-link.md``
                §3, "DoctrineService cannot be constructed").
        """
        self.parser = parser or CharterParser()
        self._tactic_registry: Callable[[str], bool] = tactic_registry or (lambda _slug: False)

    def extract(self, content: str) -> ExtractionResult:
        """Full extraction pipeline: parse → map → validate → return.

        Args:
            content: Raw charter markdown text

        Returns:
            ExtractionResult with all validated Pydantic models
        """
        if not isinstance(content, str):
            raise TypeError(f"content must be str, got {type(content).__name__}")
        sections = self.parser.parse(content)
        warnings: list[str] = []
        governance = self._extract_governance(sections)
        directives = self._extract_directives(sections, warnings=warnings)
        metadata = self._build_metadata(content, sections)

        return ExtractionResult(
            governance=governance,
            directives=directives,
            metadata=metadata,
            warnings=warnings,
        )

    def _extract_governance(self, sections: list[CharterSection]) -> GovernanceConfig:
        """Extract governance configuration from classified sections.

        Args:
            sections: Parsed charter sections

        Returns:
            Merged GovernanceConfig with testing/quality/performance/branch/commits data
        """
        testing = CharterTestingConfig()
        quality = QualityConfig()
        commits = CommitConfig()
        performance = PerformanceConfig()
        branch_strategy = BranchStrategyConfig()
        doctrine = DoctrineSelectionConfig()
        activations: list[ActivationEntry] = []

        _FIELD_HANDLERS: dict[str, Any] = {
            "testing": lambda s: self._apply_testing_keywords(testing, s.structured_data.get("keywords", {})),
            "quality": lambda s: self._apply_quality_keywords(quality, s.structured_data.get("keywords", {})),
            "commits": lambda s: self._apply_commits_keywords(commits, s.structured_data.get("keywords", {})),
            "performance": lambda s: self._apply_performance_section(performance, s.structured_data),
            "branch_strategy": lambda s: self._apply_branch_strategy_section(branch_strategy, s.structured_data),
            "doctrine": lambda s: self._merge_doctrine_selection(s, doctrine),
        }

        for section in sections:
            classification = self._classify_section(section.heading)
            if not classification:
                continue
            schema_name, field_name = classification
            if schema_name != "governance":
                continue
            handler = _FIELD_HANDLERS.get(field_name)
            if handler:
                handler(section)

        # Also scan all sections for explicit doctrine selection keys
        # so charter headings remain flexible.
        for section in sections:
            self._merge_doctrine_selection(section, doctrine)

        # WP02 (charter-mediated-doctrine-selection) T007: scan every fenced
        # YAML block across all sections for a top-level ``activations:`` key
        # and collect the entries onto GovernanceConfig.activations. The
        # registry is intentionally section-agnostic — operators may declare
        # ``activations`` inside the doctrine block, a dedicated section, or
        # anywhere a fenced YAML block lives — so the scan mirrors the
        # ``_merge_doctrine_selection`` "look in every section" pattern.
        for section in sections:
            self._collect_activations_from_section(section, activations)

        return GovernanceConfig(
            testing=testing,
            quality=quality,
            commits=commits,
            performance=performance,
            branch_strategy=branch_strategy,
            doctrine=doctrine,
            activations=activations,
        )

    def _collect_activations_from_section(
        self,
        section: CharterSection,
        activations: list[ActivationEntry],
    ) -> None:
        """Append any ActivationEntry rows found in a section's fenced YAML.

        Each fenced YAML block is inspected for a top-level ``activations:``
        key. The value must be a list; each list item is delegated to
        :meth:`_apply_activations_block`. Blocks without an ``activations:``
        key are skipped silently — this matches the additive, schema-tolerant
        contract documented in ``contracts/activation-registry.md``.
        """
        yaml_blocks = section.structured_data.get("yaml_blocks", [])
        for block in yaml_blocks:
            if not isinstance(block, dict):
                continue
            self._apply_activations_block(block, activations)

    @staticmethod
    def _apply_activations_block(
        block: dict[str, Any],
        activations: list[ActivationEntry],
    ) -> None:
        """Append validated ActivationEntry rows from one parsed YAML block.

        Behaviour (per ``contracts/activation-registry.md`` and the WP02
        task spec):

        - ``block["activations"]`` MUST be a list when present. Non-list
          values (``activations: foo`` / ``activations: {}``) are silently
          ignored to match the schema-tolerant contract used by sibling
          resolver-input keys; validation failures (e.g. ``mission_type:
          dev`` typo) are reported by Pydantic and re-raised as ``ValueError``
          so charter sync fails loud rather than swallowing operator typos.
        - Non-dict list items (e.g. a bare string) are skipped silently;
          they don't represent a meaningful entry to validate.
        - Validation failures from :class:`ActivationEntry.model_validate`
          are wrapped in a ``ValueError`` whose message names the offending
          entry so operators can locate the bad row in ``charter.md``.
        """
        raw = block.get("activations")
        if not isinstance(raw, list):
            return
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                entry = ActivationEntry.model_validate(item)
            except Exception as exc:  # noqa: BLE001 — re-raise as ValueError
                # Pydantic raises ValidationError (subclass of ValueError),
                # but other shape mismatches (e.g. extra=forbid violations)
                # also surface here. Surface a single canonical exception
                # type so charter sync's outer try/except (sync.py) can
                # render a stable error string.
                raise ValueError(
                    f"charter activations: invalid entry {item!r}: {exc}"
                ) from exc
            activations.append(entry)

    def _apply_testing_keywords(self, testing: CharterTestingConfig, keywords: dict[str, Any]) -> None:
        """Apply testing section keyword values to the testing config."""
        if "min_coverage" in keywords:
            testing.min_coverage = keywords["min_coverage"]
        if "tdd_required" in keywords:
            testing.tdd_required = keywords["tdd_required"]
        if "framework" in keywords:
            testing.framework = keywords["framework"]
        if "type_checking" in keywords:
            testing.type_checking = keywords["type_checking"]

    def _apply_quality_keywords(self, quality: QualityConfig, keywords: dict[str, Any]) -> None:
        """Apply quality section keyword values to the quality config."""
        if "linting" in keywords:
            quality.linting = keywords["linting"]
        if "pr_approvals" in keywords:
            quality.pr_approvals = keywords["pr_approvals"]
        if "pre_commit_hooks" in keywords:
            quality.pre_commit_hooks = keywords["pre_commit_hooks"]

    def _apply_commits_keywords(self, commits: CommitConfig, keywords: dict[str, Any]) -> None:
        """Apply commits section keyword values to the commits config."""
        if "convention" in keywords:
            commits.convention = keywords["convention"]

    def _apply_performance_section(
        self, performance: PerformanceConfig, structured_data: dict[str, Any]
    ) -> None:
        """Apply performance section data (keywords + tables) to the performance config."""
        keywords = structured_data.get("keywords", {})
        if "timeout_seconds" in keywords:
            performance.cli_timeout_seconds = keywords["timeout_seconds"]
        for table_row in structured_data.get("tables", []):
            for key, val in table_row.items():
                if "max_wps" in key.lower() and str(val).isdigit():
                    performance.dashboard_max_wps = int(val)
                    break

    def _apply_branch_strategy_section(
        self, branch_strategy: BranchStrategyConfig, structured_data: dict[str, Any]
    ) -> None:
        """Apply branch strategy section data (tables + numbered items) to the branch config."""
        for table_row in structured_data.get("tables", []):
            branch_val = table_row.get("branch", table_row.get("name", ""))
            if branch_val.lower() == "main":
                branch_strategy.main_branch = "main"
            if branch_val.lower() in ("develop", "dev"):
                branch_strategy.dev_branch = "develop"
        numbered_items = structured_data.get("numbered_items", [])
        if numbered_items:
            branch_strategy.rules = numbered_items

    def _merge_doctrine_selection(self, section: CharterSection, doctrine: DoctrineSelectionConfig) -> None:
        """Merge doctrine selection hints from a section into doctrine config.

        WP02 extends the original selection-table reader so that fenced
        YAML blocks carrying top-level keys ``template_set``,
        ``available_tools``, and ``authority_paths`` are also recognised.

        For fenced YAML blocks the resolver-input keys
        (``template_set`` / ``available_tools`` / ``authority_paths``)
        are stripped from the row-shaped dict before
        :meth:`_apply_selection_row` runs, so the existing replacement
        semantics for those keys do not overwrite values previously
        merged from selection tables. The stripped keys are then handled
        by :meth:`_apply_resolver_input_block`, which is additive
        (merge + dedup, preserving order) — exactly the contract
        documented in the WP02 task spec under T007.
        """
        tables = section.structured_data.get("tables", [])
        yaml_blocks = section.structured_data.get("yaml_blocks", [])

        for row in tables:
            self._apply_selection_row(row, doctrine)

        for block in yaml_blocks:
            if not isinstance(block, dict):
                continue
            # Strip resolver-input keys so they are NOT replayed through
            # the row-style replacement path (which would clobber prior
            # selection-table values).
            resolver_keys = {
                "template_set",
                "available_tools",
                "authority_paths",
                "governance_references",
                "required_reading",
                "reading_list",
            }
            row_only = {k: v for k, v in block.items() if k not in resolver_keys}
            if row_only:
                self._apply_selection_row(row_only, doctrine)
            # Then merge top-level resolver-input declarations: these
            # are the WP02 additions (FR-007, FR-008).
            self._apply_resolver_input_block(block, doctrine)

    def _apply_resolver_input_block(
        self,
        block: dict[str, Any],
        doctrine: DoctrineSelectionConfig,
    ) -> None:
        """Apply top-level resolver-input keys from a fenced YAML block.

        Recognised top-level keys:

        - ``template_set`` (scalar): when present, **overrides** any value
          already set on ``doctrine.template_set``. The fenced YAML block
          is the more explicit declaration; an info-level diagnostic is
          emitted when an override occurs.
        - ``available_tools`` (list): merged into the existing list,
          preserving order and deduplicating.
        - ``authority_paths`` (list): merged into the existing list,
          preserving order and deduplicating. Non-string entries are
          rejected with a clear ``ValueError`` (matches the existing
          ``_apply_selection_row`` strictness).
        - ``governance_references`` (list): merged into supporting
          governance docs. ``required_reading`` and ``reading_list`` are
          accepted as aliases so early charter drafts can migrate without
          losing intent.
        """
        if not isinstance(block, dict):
            return

        self._apply_template_set_override(block, doctrine)
        doctrine.available_tools = self._merge_string_list(
            existing=doctrine.available_tools,
            new=block.get("available_tools"),
            field_name="available_tools",
        )
        doctrine.authority_paths = self._merge_string_list(
            existing=doctrine.authority_paths,
            new=block.get("authority_paths"),
            field_name="authority_paths",
        )
        for field_name in ("governance_references", "required_reading", "reading_list"):
            doctrine.governance_references = self._merge_string_list(
                existing=doctrine.governance_references,
                new=block.get(field_name),
                field_name=field_name,
            )

    def _apply_template_set_override(
        self,
        block: dict[str, Any],
        doctrine: DoctrineSelectionConfig,
    ) -> None:
        """Apply a fenced-YAML ``template_set:`` override.

        The fenced YAML block is the more explicit declaration and wins
        on conflict with a selection-table value; an info-level
        diagnostic is emitted when an override occurs (T007 in the WP02
        task spec).
        """
        new_template = block.get("template_set")
        if not isinstance(new_template, str):
            return
        cleaned = new_template.strip()
        if not cleaned:
            return
        existing = doctrine.template_set
        if existing and existing != cleaned:
            logger.info(
                "charter: fenced YAML block overrides selection-table template_set "
                "(%s -> %s)",
                existing,
                cleaned,
            )
        doctrine.template_set = cleaned

    @staticmethod
    def _merge_string_list(
        *,
        existing: list[str],
        new: Any,
        field_name: str,
    ) -> list[str]:
        """Merge a new list of strings into *existing* with dedup, preserving order.

        Returns ``existing`` unchanged when *new* is not a list. Raises
        ``ValueError`` with a charter-anchored message when any entry is
        not a string (matches the strictness of
        :meth:`_apply_selection_row` for sibling fields).
        """
        if not isinstance(new, list):
            return existing
        cleaned: list[str] = []
        for entry in new:
            if not isinstance(entry, str):
                raise ValueError(
                    f"charter fenced YAML: {field_name} entry must be a string, "
                    f"got {type(entry).__name__} ({entry!r})"
                )
            value = entry.strip()
            if value:
                cleaned.append(value)
        merged: list[str] = list(existing)
        seen: set[str] = set(merged)
        for value in cleaned:
            if value not in seen:
                merged.append(value)
                seen.add(value)
        return merged

    def _apply_selection_row(self, row: dict[str, Any], doctrine: DoctrineSelectionConfig) -> None:
        """Apply one table/yaml row that may contain doctrine selection keys.

        WP02 extends the original three ``selected_<kind>`` fields with parity
        readers for the five additional kinds exposed by ``DoctrineService``
        (``styleguides`` / ``toolguides`` / ``procedures`` / ``agent_profiles``
        / ``mission_step_contracts``). The canonical key is always
        ``selected_<plural-kind>``; the bare ``<plural-kind>`` alias (and a
        kebab-case alias for the two-word kinds) is accepted only as a
        secondary candidate per ``_get_list_value`` ordering — the prefixed
        key wins on conflict.
        """
        normalized = {str(k).strip().lower(): v for k, v in row.items()}

        paradigms = self._get_list_value(normalized, ("selected_paradigms", "paradigms"))
        if paradigms:
            doctrine.selected_paradigms = paradigms

        directives = self._get_list_value(normalized, ("selected_directives", "directives"))
        if directives:
            doctrine.selected_directives = directives

        tactics = self._get_list_value(normalized, ("selected_tactics", "tactics"))
        if tactics:
            doctrine.selected_tactics = tactics

        # WP02 (charter-mediated-doctrine-selection) T006: parity readers for
        # the five additional `selected_<kind>` fields. Each follows the same
        # pattern as the three above — canonical key first, alias(es) after.
        styleguides = self._get_list_value(normalized, ("selected_styleguides", "styleguides"))
        if styleguides:
            doctrine.selected_styleguides = styleguides

        toolguides = self._get_list_value(normalized, ("selected_toolguides", "toolguides"))
        if toolguides:
            doctrine.selected_toolguides = toolguides

        procedures = self._get_list_value(normalized, ("selected_procedures", "procedures"))
        if procedures:
            doctrine.selected_procedures = procedures

        agent_profiles = self._get_list_value(
            normalized,
            ("selected_agent_profiles", "agent_profiles", "agent" + "-profiles"),
        )
        if agent_profiles:
            doctrine.selected_agent_profiles = agent_profiles

        mission_step_contracts = self._get_list_value(
            normalized,
            (
                "selected_mission_step_contracts",
                "mission_step_contracts",
                "mission-step-contracts",
            ),
        )
        if mission_step_contracts:
            doctrine.selected_mission_step_contracts = mission_step_contracts

        tools = self._get_list_value(normalized, ("available_tools", "tools", "selected_tools"))
        if tools:
            doctrine.available_tools = tools

        template_set = self._get_scalar_value(normalized, ("template_set", "templateset"))
        if template_set:
            doctrine.template_set = template_set

    def _get_list_value(
        self,
        normalized_row: dict[str, Any],
        candidate_keys: tuple[str, ...],
    ) -> list[str]:
        """Read list value from row by trying candidate keys."""
        for key in candidate_keys:
            if key not in normalized_row:
                continue
            value = normalized_row[key]
            if isinstance(value, list):
                return [str(item).strip() for item in value if str(item).strip()]
            if isinstance(value, str):
                return [item.strip() for item in value.split(",") if item.strip()]
        return []

    def _get_scalar_value(
        self,
        normalized_row: dict[str, Any],
        candidate_keys: tuple[str, ...],
    ) -> str | None:
        """Read scalar string value from row by trying candidate keys."""
        for key in candidate_keys:
            if key in normalized_row:
                value = str(normalized_row[key]).strip()
                if value:
                    return value
        return None

    def _extract_directives(
        self,
        sections: list[CharterSection],
        *,
        warnings: list[str],
    ) -> DirectivesConfig:
        """Extract directives from classified sections.

        Args:
            sections: Parsed charter sections

        Returns:
            DirectivesConfig with auto-generated DIR-XXX IDs.

        WP02 changes:

        - Each extracted directive body is scanned via
          :func:`_detect_catalog_references` and any detected catalog IDs
          or known tactic slugs are lifted into ``Directive.references``.
        - When a directive-classified section carries no numbered items but
          does carry bullet items (the ``- item`` shape used by Code Review
          Checklist–style sections), the bullet items become directives.
          Numbered items take precedence; bullets are only consulted as a
          fallback so existing charters with both shapes still emit one
          directive per numbered line.
        """
        directives_list: list[Directive] = []
        directive_counter = 1

        for section in sections:
            classification = self._classify_section(section.heading)
            if not classification:
                continue

            schema_name, _ = classification

            # Only process directive sections
            if schema_name != "directives":
                continue

            items: list[str] = list(section.structured_data.get("numbered_items", []))
            if not items:
                # Fallback: bullet items inside a directive-classified section.
                items = self._extract_bullet_items(section.content)

            for item_text in items:
                placeholder_directive_id = _generated_directive_placeholder_id(item_text)
                if placeholder_directive_id:
                    warnings.append(_generated_directive_placeholder_warning(placeholder_directive_id))
                    logger.warning(warnings[-1])
                    continue

                # Detect cross-link catalog citations inside the body so the
                # downstream resolver can surface the catalog body on demand
                # (FR-006). The registry callable is injected at __init__
                # time so this method stays decoupled from DoctrineService.
                references = _detect_catalog_references(
                    item_text,
                    tactic_registry=self._tactic_registry,
                )
                directive_id = f"DIR-{directive_counter:03d}"
                directive = Directive(
                    id=directive_id,
                    title=item_text[:50],  # First 50 chars as title
                    description=item_text,
                    severity="warn",
                    references=references,
                )
                directives_list.append(directive)
                directive_counter += 1

        return DirectivesConfig(directives=directives_list)

    @staticmethod
    def _extract_bullet_items(content: str) -> list[str]:
        """Extract ``- item`` bullet items from raw section content.

        Used as a fallback inside directive-classified sections that carry
        bullet lists instead of numbered lists (e.g. Code Review
        Checklist). Each bullet's text becomes one directive entry.
        Multi-line bullet continuations (a single bullet whose body wraps
        onto an indented next line) are joined with a single space so the
        emitted directive description stays one-line per item.
        """
        items: list[str] = []
        for match in _BULLET_ITEM_RE.finditer(content):
            raw = match.group(1)
            # Join indented continuation lines with a single space; collapse
            # internal whitespace to keep the description compact.
            joined = " ".join(part.strip() for part in raw.splitlines() if part.strip())
            if joined:
                items.append(joined)
        return items

    def _build_metadata(self, content: str, sections: list[CharterSection]) -> ExtractionMetadata:
        """Build extraction metadata with provenance info.

        Args:
            content: Raw charter markdown text
            sections: Parsed sections

        Returns:
            ExtractionMetadata with hash, timestamp, counts
        """
        # Count section types
        structured_count = sum(1 for s in sections if not s.requires_ai)
        ai_assisted_count = sum(1 for s in sections if s.requires_ai)

        sections_parsed = SectionsParsed(
            structured=structured_count,
            ai_assisted=ai_assisted_count,
            skipped=0,
        )

        # Determine extraction mode
        extraction_mode = "deterministic" if ai_assisted_count == 0 else "hybrid"

        # Generate hash
        charter_hash = hash_content(content)

        # ISO timestamp
        extracted_at = datetime.now(UTC).isoformat()

        return ExtractionMetadata(
            schema_version="1.0.0",
            extracted_at=extracted_at,
            charter_hash=charter_hash,
            source_path=".kittify/charter/charter.md",
            extraction_mode=extraction_mode,
            sections_parsed=sections_parsed,
            bundle_schema_version=CURRENT_BUNDLE_SCHEMA_VERSION,
        )

    def _classify_section(self, heading: str) -> tuple[str, str] | None:
        """Classify section heading to target schema and field.

        Args:
            heading: Section heading text

        Returns:
            (schema_name, field_name) tuple or None if unclassifiable
        """
        heading_lower = heading.lower()

        # Find longest matching keyword (more specific wins)
        best_match: tuple[str, str] | None = None
        best_length = 0

        for keyword, (schema, field) in SECTION_MAPPING.items():
            if keyword in heading_lower and len(keyword) > best_length:
                best_match = (schema, field)
                best_length = len(keyword)

        return best_match


def _generated_directive_placeholder_id(item_text: str) -> str | None:
    """Return the catalog directive ID when *item_text* is generated placeholder prose."""
    match = _GENERATED_DIRECTIVE_PLACEHOLDER_RE.match(item_text.strip())
    if not match:
        return None
    directive_id = match.group("directive_id")
    return str(directive_id)


def _generated_directive_placeholder_warning(directive_id: str) -> str:
    return (
        f"Skipped generated placeholder for {directive_id}; "
        "run `spec-kitty charter generate --force` with current templates so "
        "directives.yaml does not mint hollow local DIR-NNN policy."
    )


def extract_with_ai(
    prose_sections: list[CharterSection],
    schema_hint: dict[str, Any],
) -> dict[str, Any]:
    """Send prose sections to configured AI agent for structured extraction.

    This is a stub implementation for WP02. Actual AI integration happens in WP05.

    Args:
        prose_sections: Sections that require AI extraction (requires_ai=True)
        schema_hint: Expected output schema as dict

    Returns:
        Extracted data as dict matching schema hint (empty dict if AI unavailable)
    """
    # Check if AI agent is available (stub for now)
    _ = schema_hint
    logger.info("AI extraction not yet implemented - skipping %d prose sections", len(prose_sections))

    # Return empty dict (graceful fallback)
    return {}


def write_extraction_result(result: ExtractionResult, charter_dir: Path) -> None:
    """Write all YAML files from an extraction result.

    Args:
        result: Complete extraction result
        charter_dir: Target directory (e.g., .kittify/charter/)
    """
    charter_dir.mkdir(parents=True, exist_ok=True)

    emit_yaml(result.governance, charter_dir / "governance.yaml")
    emit_yaml(result.directives, charter_dir / "directives.yaml")
    emit_yaml(result.metadata, charter_dir / "metadata.yaml")
