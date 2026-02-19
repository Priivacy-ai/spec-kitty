"""Constitution markdown parser.

Parses constitution markdown into structured sections and extracts:
- Markdown tables (e.g., | Key | Value | rows)
- YAML code blocks (```yaml ... ```)
- Numbered lists (1. Item, 2. Item, ...)
- Keywords and quantitative patterns (90% coverage, TDD required, etc.)
"""

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ruamel.yaml import YAML

logger = logging.getLogger(__name__)
from ruamel.yaml.error import YAMLError


@dataclass
class ConstitutionSection:
    """A parsed section from the constitution markdown."""

    heading: str  # Section heading text
    level: int  # Heading level (2 = ##, 3 = ###, 0 = preamble)
    content: str  # Raw markdown content
    structured_data: dict[str, Any] = field(default_factory=dict)  # Extracted key-value pairs
    requires_ai: bool = True  # True if only prose (needs AI extraction)


class ConstitutionParser:
    """Parser for constitution markdown documents."""

    # Regex patterns for parsing
    HEADING_PATTERN = re.compile(r"^(#{2,3})\s+(.+)$", re.MULTILINE)
    TABLE_ROW_PATTERN = re.compile(r"^\|(.+)\|$", re.MULTILINE)
    TABLE_SEPARATOR_PATTERN = re.compile(r"^\|[-:| ]+\|$")
    YAML_BLOCK_PATTERN = re.compile(r"```yaml\n(.*?)\n```", re.DOTALL)
    NUMBERED_LIST_PATTERN = re.compile(r"^\d+\.\s+(.+)$", re.MULTILINE)

    # Keyword extraction patterns
    KEYWORD_PATTERNS: list[tuple[str, str, Callable[[str], Any]]] = [
        (r"(\d+)%\+?\s*(?:test\s+)?coverage", "min_coverage", int),
        (r"TDD\s+(required|mandatory)", "tdd_required", lambda _: True),
        (r"<\s*(\d+)\s*seconds?", "timeout_seconds", float),
        (r"conventional\s*commits?", "convention", lambda _: "conventional"),
        (r"pre-?commit\s+hooks?", "pre_commit_hooks", lambda _: True),
        (r"(\d+)\+?\s*approvals?", "pr_approvals", int),
        (r"mypy\s+--strict", "type_checking", lambda _: "mypy --strict"),
        (r"pytest", "framework", lambda _: "pytest"),
        (r"ruff", "linting", lambda _: "ruff"),
    ]

    def parse(self, content: str) -> list[ConstitutionSection]:
        """Split constitution markdown into sections by headings.

        Args:
            content: Full constitution markdown text

        Returns:
            List of ConstitutionSection objects with parsed content
        """
        if not content.strip():
            return []

        sections: list[ConstitutionSection] = []
        heading_matches = list(self.HEADING_PATTERN.finditer(content))

        if not heading_matches:
            # No headings found - return entire content as single section
            section = ConstitutionSection(
                heading="preamble",
                level=0,
                content=content.strip(),
                structured_data={},
                requires_ai=True,
            )
            self._parse_section_content(section)
            sections.append(section)
            return sections

        # Handle preamble (content before first heading)
        if heading_matches[0].start() > 0:
            preamble_content = content[: heading_matches[0].start()].strip()
            if preamble_content:
                section = ConstitutionSection(
                    heading="preamble",
                    level=0,
                    content=preamble_content,
                    structured_data={},
                    requires_ai=True,
                )
                self._parse_section_content(section)
                sections.append(section)

        # Parse each section
        for i, match in enumerate(heading_matches):
            heading_prefix = match.group(1)
            heading_text = match.group(2).strip()
            level = len(heading_prefix)

            # Extract content between this heading and next (or end of document)
            start = match.end()
            end = heading_matches[i + 1].start() if i + 1 < len(heading_matches) else len(content)
            section_content = content[start:end].strip()

            section = ConstitutionSection(
                heading=heading_text,
                level=level,
                content=section_content,
                structured_data={},
                requires_ai=True,
            )
            self._parse_section_content(section)
            sections.append(section)

        return sections

    def _parse_section_content(self, section: ConstitutionSection) -> None:
        """Parse structured data from section content and update section in place."""
        has_structured = False

        # Parse tables
        tables = self.parse_table(section.content)
        if tables:
            section.structured_data["tables"] = tables
            has_structured = True

        # Parse YAML blocks
        yaml_blocks = self.parse_yaml_blocks(section.content)
        if yaml_blocks:
            section.structured_data["yaml_blocks"] = yaml_blocks
            has_structured = True

        # Parse numbered lists
        numbered_items = self.parse_numbered_lists(section.content)
        if numbered_items:
            section.structured_data["numbered_items"] = numbered_items
            has_structured = True

        # Extract keywords
        keywords = self.extract_keywords(section.content)
        if keywords:
            section.structured_data["keywords"] = keywords
            has_structured = True

        # Update requires_ai flag
        if has_structured:
            section.requires_ai = False

    def parse_table(self, content: str) -> list[dict[str, str]]:
        """Extract markdown tables from content.

        Args:
            content: Markdown text potentially containing tables

        Returns:
            List of dicts representing table rows (header names as keys)
        """
        lines = content.split("\n")
        table_lines: list[str] = []
        tables: list[dict[str, str]] = []

        # Collect consecutive table lines
        for line in lines:
            if self.TABLE_ROW_PATTERN.match(line):
                table_lines.append(line)
            else:
                # Process accumulated table if any
                if table_lines:
                    table_data = self._parse_single_table(table_lines)
                    if table_data:
                        tables.extend(table_data)
                    table_lines = []

        # Process final table if any
        if table_lines:
            table_data = self._parse_single_table(table_lines)
            if table_data:
                tables.extend(table_data)

        return tables

    def _parse_single_table(self, table_lines: list[str]) -> list[dict[str, str]]:
        """Parse a single markdown table."""
        if len(table_lines) < 2:
            return []

        # Extract headers from first line
        header_line = table_lines[0]
        headers = [h.strip() for h in header_line.strip("|").split("|")]

        # Skip separator line and parse data rows
        data_rows: list[dict[str, str]] = []
        for line in table_lines[1:]:
            if self.TABLE_SEPARATOR_PATTERN.match(line):
                continue

            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) == len(headers):
                row_dict = dict(zip(headers, cells))
                data_rows.append(row_dict)

        return data_rows

    def parse_yaml_blocks(self, content: str) -> list[dict[str, Any]]:
        """Extract and parse YAML code blocks.

        Args:
            content: Markdown text potentially containing ```yaml blocks

        Returns:
            List of parsed YAML objects (dicts)
        """
        blocks: list[dict[str, Any]] = []
        yaml = YAML()

        for match in self.YAML_BLOCK_PATTERN.finditer(content):
            yaml_text = match.group(1)
            try:
                parsed = yaml.load(yaml_text)
                if isinstance(parsed, dict):
                    blocks.append(parsed)
            except YAMLError as e:
                logger.warning("Skipping invalid YAML block: %s", e)
                continue

        return blocks

    def parse_numbered_lists(self, content: str) -> list[str]:
        """Extract numbered list items.

        Args:
            content: Markdown text potentially containing numbered lists

        Returns:
            List of item texts (without numbers)
        """
        items: list[str] = []
        for match in self.NUMBERED_LIST_PATTERN.finditer(content):
            item_text = match.group(1).strip()
            items.append(item_text)
        return items

    def extract_keywords(self, content: str) -> dict[str, Any]:
        """Extract quantitative values and keywords from prose.

        Args:
            content: Markdown text containing quantitative patterns

        Returns:
            Dict mapping config keys to extracted values
        """
        keywords: dict[str, Any] = {}

        # Case-insensitive search
        lower_content = content.lower()

        for pattern, key, converter in self.KEYWORD_PATTERNS:
            match = re.search(pattern, lower_content, re.IGNORECASE)
            if match:
                try:
                    if match.lastindex and match.lastindex > 0:
                        # Pattern has capture group - extract and convert
                        value = converter(match.group(1))
                    else:
                        # Pattern has no capture group - just invoke converter
                        value = converter("")
                    keywords[key] = value
                except (ValueError, IndexError):
                    # Skip if conversion fails
                    continue

        return keywords
