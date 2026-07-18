"""Charter extraction pipeline.

IC-04 (consolidate-charter-bundle / WP04) retirement notice: the
heading-classification dispatch this module used to drive
``governance.testing`` / ``.quality`` / ``.commits`` / ``.performance`` /
``.branch_strategy`` and ``directives.directives`` extraction from
``charter.md`` prose (the ``SECTION_MAPPING`` table, ``_classify_section``,
and the numbered/bullet-item directive scraper) is RETIRED --
``governance``/``directives`` are hand-authored directly in ``charter.yaml``
now (``charter.sync.load_governance_config`` / ``load_directives_config``).
``Extractor.extract()`` therefore always returns an empty
``DirectivesConfig``.

Still live: doctrine-selection extraction (``template_set`` /
``available_tools`` / ``authority_paths`` / ``selected_*``) and the
activation-registry scan (``activations:`` fenced YAML blocks) -- both scan
every section unconditionally rather than via ``SECTION_MAPPING``, and
``_detect_catalog_references`` (the ``DIRECTIVE_NNN`` / tactic-slug citation
detector), kept as a standalone, independently-testable utility.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
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
    DirectivesConfig,
    ExtractionMetadata,
    GovernanceConfig,
    PerformanceConfig,
    QualityConfig,
    SectionsParsed,
    CharterTestingConfig,
)

__all__ = [
    "Extractor",
]


logger = logging.getLogger(__name__)

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

    def __init__(self, parser: CharterParser | None = None):
        """Initialize extractor with optional parser.

        IC-04 (WP04): the constructor no longer accepts ``tactic_registry``
        -- it existed only to thread a ``DoctrineService.tactics``-backed
        predicate into the now-retired directive-body citation scraper.
        :func:`_detect_catalog_references` (the citation detector itself)
        is unaffected and still takes ``tactic_registry`` directly.

        Args:
            parser: CharterParser instance (creates default if None).
        """
        self.parser = parser or CharterParser()

    def extract(self, content: str) -> ExtractionResult:
        """Full extraction pipeline: parse → map → validate → return.

        IC-04 (WP04): ``governance``'s testing/quality/commits/performance/
        branch_strategy fields and ``directives`` are no longer scraped from
        prose (see module docstring) -- ``governance`` carries only the
        still-live doctrine-selection + activation-registry scan results,
        and ``directives`` is always empty.

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
        directives = DirectivesConfig()
        metadata = self._build_metadata(content, sections)

        return ExtractionResult(
            governance=governance,
            directives=directives,
            metadata=metadata,
            warnings=warnings,
        )

    def _extract_governance(self, sections: list[CharterSection]) -> GovernanceConfig:
        """Extract governance configuration from every section, unconditionally.

        IC-04 (WP04): the ``testing``/``quality``/``commits``/``performance``/
        ``branch_strategy`` fields stay at schema defaults -- their prose
        scrape (gated on ``SECTION_MAPPING`` classification) is retired.
        ``doctrine`` (selection) and ``activations`` (the activation
        registry) are unaffected: both were already scanned unconditionally
        across every section, independent of heading classification.

        Args:
            sections: Parsed charter sections

        Returns:
            GovernanceConfig with doctrine selection + activations populated;
            testing/quality/commits/performance/branch_strategy at defaults.
        """
        testing = CharterTestingConfig()
        quality = QualityConfig()
        commits = CommitConfig()
        performance = PerformanceConfig()
        branch_strategy = BranchStrategyConfig()
        doctrine = DoctrineSelectionConfig()
        activations: list[ActivationEntry] = []

        # Scan all sections for explicit doctrine selection keys so charter
        # headings remain flexible.
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
