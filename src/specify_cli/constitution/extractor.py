"""Constitution extraction pipeline.

Maps parsed constitution sections to validated Pydantic models:
- governance.yaml (testing, quality, performance, branch strategy)
- agents.yaml (agent profiles and selection strategy)
- directives.yaml (numbered rules and enforcement)
- metadata.yaml (extraction provenance and statistics)
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from specify_cli.constitution.hasher import hash_content
from specify_cli.constitution.parser import ConstitutionParser, ConstitutionSection
from specify_cli.constitution.schemas import (
    AgentProfile,
    AgentSelectionConfig,
    AgentsConfig,
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
    TestingConfig,
    emit_yaml,
)

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
    "agent": ("agents", "profiles"),
    "paradigm": ("governance", "doctrine"),
    "tool": ("governance", "doctrine"),
    "template": ("governance", "doctrine"),
    "directive": ("directives", "directives"),
    "constraint": ("directives", "directives"),
    "rule": ("directives", "directives"),
}


@dataclass
class ExtractionResult:
    """Complete extraction result with all config schemas and metadata."""

    governance: GovernanceConfig
    agents: AgentsConfig
    directives: DirectivesConfig
    metadata: ExtractionMetadata


class Extractor:
    """Extract structured configuration from parsed constitution sections."""

    def __init__(self, parser: ConstitutionParser | None = None):
        """Initialize extractor with optional parser.

        Args:
            parser: ConstitutionParser instance (creates default if None)
        """
        self.parser = parser or ConstitutionParser()

    def extract(self, content: str) -> ExtractionResult:
        """Full extraction pipeline: parse → map → validate → return.

        Args:
            content: Raw constitution markdown text

        Returns:
            ExtractionResult with all validated Pydantic models
        """
        if not isinstance(content, str):
            raise TypeError(f"content must be str, got {type(content).__name__}")
        sections = self.parser.parse(content)
        governance = self._extract_governance(sections)
        agents = self._extract_agents(sections)
        directives = self._extract_directives(sections)
        metadata = self._build_metadata(content, sections)

        return ExtractionResult(
            governance=governance,
            agents=agents,
            directives=directives,
            metadata=metadata,
        )

    def _extract_governance(self, sections: list[ConstitutionSection]) -> GovernanceConfig:
        """Extract governance configuration from classified sections.

        Args:
            sections: Parsed constitution sections

        Returns:
            Merged GovernanceConfig with testing/quality/performance/branch/commits data
        """
        # Initialize with defaults
        testing = TestingConfig()
        quality = QualityConfig()
        commits = CommitConfig()
        performance = PerformanceConfig()
        branch_strategy = BranchStrategyConfig()
        doctrine = DoctrineSelectionConfig()

        # Iterate sections in document order for deterministic merging
        for section in sections:
            classification = self._classify_section(section.heading)
            if not classification:
                continue

            schema_name, field_name = classification

            # Only process governance sections
            if schema_name != "governance":
                continue

            # Extract keywords from structured_data
            keywords = section.structured_data.get("keywords", {})

            # Map to appropriate sub-config based on field_name
            if field_name == "testing":
                if "min_coverage" in keywords:
                    testing.min_coverage = keywords["min_coverage"]
                if "tdd_required" in keywords:
                    testing.tdd_required = keywords["tdd_required"]
                if "framework" in keywords:
                    testing.framework = keywords["framework"]
                if "type_checking" in keywords:
                    testing.type_checking = keywords["type_checking"]

            elif field_name == "quality":
                if "linting" in keywords:
                    quality.linting = keywords["linting"]
                if "pr_approvals" in keywords:
                    quality.pr_approvals = keywords["pr_approvals"]
                if "pre_commit_hooks" in keywords:
                    quality.pre_commit_hooks = keywords["pre_commit_hooks"]

            elif field_name == "commits":
                if "convention" in keywords:
                    commits.convention = keywords["convention"]

            elif field_name == "performance":
                if "timeout_seconds" in keywords:
                    performance.cli_timeout_seconds = keywords["timeout_seconds"]
                # Look for dashboard limits in tables or keywords
                tables = section.structured_data.get("tables", [])
                for table_row in tables:
                    # Check specific key for max_wps value
                    for key, val in table_row.items():
                        if "max_wps" in key.lower() and val.isdigit():
                            performance.dashboard_max_wps = int(val)
                            break

            elif field_name == "branch_strategy":
                # Extract branch names from keywords or tables
                tables = section.structured_data.get("tables", [])
                for table_row in tables:
                    # Check specific branch column values
                    branch_val = table_row.get("branch", table_row.get("name", ""))
                    if branch_val.lower() == "main":
                        branch_strategy.main_branch = "main"
                    if branch_val.lower() in ("develop", "dev"):
                        branch_strategy.dev_branch = "develop"

                # Extract rules from numbered lists
                numbered_items = section.structured_data.get("numbered_items", [])
                if numbered_items:
                    branch_strategy.rules = numbered_items

            elif field_name == "doctrine":
                self._merge_doctrine_selection(section, doctrine)

        # Also scan all sections for explicit doctrine selection keys
        # so constitution headings remain flexible.
        for section in sections:
            self._merge_doctrine_selection(section, doctrine)

        return GovernanceConfig(
            testing=testing,
            quality=quality,
            commits=commits,
            performance=performance,
            branch_strategy=branch_strategy,
            doctrine=doctrine,
        )

    def _merge_doctrine_selection(self, section: ConstitutionSection, doctrine: DoctrineSelectionConfig) -> None:
        """Merge doctrine selection hints from a section into doctrine config."""
        tables = section.structured_data.get("tables", [])
        yaml_blocks = section.structured_data.get("yaml_blocks", [])

        for row in tables:
            self._apply_selection_row(row, doctrine)

        for block in yaml_blocks:
            if isinstance(block, dict):
                self._apply_selection_row(block, doctrine)

    def _apply_selection_row(self, row: dict[str, Any], doctrine: DoctrineSelectionConfig) -> None:
        """Apply one table/yaml row that may contain doctrine selection keys."""
        normalized = {str(k).strip().lower(): v for k, v in row.items()}

        paradigms = self._get_list_value(normalized, ("selected_paradigms", "paradigms"))
        if paradigms:
            doctrine.selected_paradigms = paradigms

        directives = self._get_list_value(normalized, ("selected_directives", "directives"))
        if directives:
            doctrine.selected_directives = directives

        profiles = self._get_list_value(
            normalized,
            (
                "selected_agent_profiles",
                "agent_profiles",
                "selected_profiles",
            ),
        )
        if profiles:
            doctrine.selected_agent_profiles = profiles

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

    def _extract_agents(self, sections: list[ConstitutionSection]) -> AgentsConfig:
        """Extract agent profiles and selection config from classified sections.

        Args:
            sections: Parsed constitution sections

        Returns:
            AgentsConfig with profiles and selection strategy
        """
        profiles: list[AgentProfile] = []
        selection = AgentSelectionConfig()

        for section in sections:
            classification = self._classify_section(section.heading)
            if not classification:
                continue

            schema_name, _ = classification

            # Only process agent sections
            if schema_name != "agents":
                continue

            # Extract agent profiles from tables
            tables = section.structured_data.get("tables", [])
            for table_row in tables:
                # Look for agent_key, role, model columns
                agent_key = table_row.get("agent") or table_row.get("agent_key") or table_row.get("name")
                role = table_row.get("role", "implementer")
                model = table_row.get("model") or table_row.get("preferred_model")

                if agent_key:
                    profile = AgentProfile(
                        agent_key=agent_key,
                        role=role,
                        preferred_model=model,
                    )
                    profiles.append(profile)

            # Extract selection strategy from keywords
            if "preferred" in section.content.lower():
                selection.strategy = "preferred"

        return AgentsConfig(profiles=profiles, selection=selection)

    def _extract_directives(self, sections: list[ConstitutionSection]) -> DirectivesConfig:
        """Extract numbered directives from classified sections.

        Args:
            sections: Parsed constitution sections

        Returns:
            DirectivesConfig with auto-generated DIR-XXX IDs
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

            # Extract numbered items
            numbered_items = section.structured_data.get("numbered_items", [])
            for item_text in numbered_items:
                directive_id = f"DIR-{directive_counter:03d}"
                directive = Directive(
                    id=directive_id,
                    title=item_text[:50],  # First 50 chars as title
                    description=item_text,
                    severity="warn",
                )
                directives_list.append(directive)
                directive_counter += 1

        return DirectivesConfig(directives=directives_list)

    def _build_metadata(self, content: str, sections: list[ConstitutionSection]) -> ExtractionMetadata:
        """Build extraction metadata with provenance info.

        Args:
            content: Raw constitution markdown text
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
        constitution_hash = hash_content(content)

        # ISO timestamp
        extracted_at = datetime.now(timezone.utc).isoformat()

        return ExtractionMetadata(
            schema_version="1.0.0",
            extracted_at=extracted_at,
            constitution_hash=constitution_hash,
            source_path=".kittify/constitution/constitution.md",
            extraction_mode=extraction_mode,
            sections_parsed=sections_parsed,
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


def extract_with_ai(
    prose_sections: list[ConstitutionSection],
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
    logger.info("AI extraction not yet implemented - skipping %d prose sections", len(prose_sections))

    # Return empty dict (graceful fallback)
    return {}


def write_extraction_result(result: ExtractionResult, constitution_dir: Path) -> None:
    """Write all YAML files from an extraction result.

    Args:
        result: Complete extraction result
        constitution_dir: Target directory (e.g., .kittify/constitution/)
    """
    constitution_dir.mkdir(parents=True, exist_ok=True)

    emit_yaml(result.governance, constitution_dir / "governance.yaml")
    emit_yaml(result.agents, constitution_dir / "agents.yaml")
    emit_yaml(result.directives, constitution_dir / "directives.yaml")
    emit_yaml(result.metadata, constitution_dir / "metadata.yaml")
