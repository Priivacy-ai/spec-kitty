"""Agent context file management for updating CLAUDE.md, GEMINI.md, etc."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import re


# Agent types and their file paths
AGENT_CONFIGS = {
    "claude": "CLAUDE.md",
    "gemini": "GEMINI.md",
    "copilot": ".github/copilot-instructions.md",
    "cursor": ".cursor/rules/specify-rules.mdc",
    "qwen": "QWEN.md",
    "opencode": "AGENTS.md",
    "codex": "AGENTS.md",
    "windsurf": ".windsurf/rules/specify-rules.md",
    "kilocode": ".kilocode/rules/specify-rules.md",
    "auggie": ".augment/rules/specify-rules.md",
    "roo": ".roo/rules/specify-rules.md",
    "q": "AGENTS.md",
}


def parse_plan_for_tech_stack(plan_path: Path) -> Dict[str, Optional[str]]:
    """
    Extract tech stack information from plan.md Technical Context section.

    Args:
        plan_path: Path to plan.md file

    Returns:
        Dictionary with language, dependencies, storage, testing, project_type keys

    Example return:
        {
            "language": "Python 3.11+",
            "dependencies": "Typer, Rich, pathlib, subprocess",
            "storage": "Filesystem only (no database)",
            "testing": "pytest with unit + integration tests",
            "project_type": "Single Python package"
        }
    """
    if not plan_path.exists():
        raise FileNotFoundError(f"Plan file not found: {plan_path}")

    content = plan_path.read_text()

    # Extract fields from Technical Context section using markdown patterns
    def extract_field(pattern: str) -> Optional[str]:
        # Match pattern like "**Language/Version**: Python 3.11+"
        match = re.search(rf"\*\*{pattern}\*\*:\s*(.+?)(?:\n|$)", content, re.MULTILINE)
        if match:
            value = match.group(1).strip()
            # Filter out placeholders
            if value and value != "NEEDS CLARIFICATION" and value != "N/A":
                return value
        return None

    return {
        "language": extract_field("Language/Version"),
        "dependencies": extract_field("Primary Dependencies"),
        "storage": extract_field("Storage"),
        "testing": extract_field("Testing"),
        "project_type": extract_field("Project Type"),
    }


def format_technology_stack(tech_stack: Dict[str, Optional[str]], feature_slug: str) -> List[str]:
    """
    Format tech stack data into markdown bullet points for Active Technologies section.

    Args:
        tech_stack: Dictionary from parse_plan_for_tech_stack()
        feature_slug: Current feature branch/slug (e.g., "008-unified-python-cli")

    Returns:
        List of formatted markdown lines

    Example:
        ["- Python 3.11+ (existing spec-kitty requirement) (008-unified-python-cli)",
         "- Filesystem only (no database) (008-unified-python-cli)"]
    """
    entries = []

    # Add language + dependencies as one line
    parts = []
    if tech_stack.get("language"):
        parts.append(tech_stack["language"])
    if tech_stack.get("dependencies"):
        parts.append(tech_stack["dependencies"])

    if parts:
        tech_line = " + ".join(parts)
        entries.append(f"- {tech_line} ({feature_slug})")

    # Add storage as separate line if present
    if tech_stack.get("storage"):
        entries.append(f"- {tech_stack['storage']} ({feature_slug})")

    return entries


def preserve_manual_additions(old_content: str, new_content: str) -> str:
    """
    Preserve content between <!-- MANUAL ADDITIONS START/END --> markers.

    Args:
        old_content: Original file content with manual additions
        new_content: New generated content

    Returns:
        Merged content with manual additions from old_content injected into new_content

    Note:
        If markers are not found in old_content, returns new_content unchanged.
        If markers are not found in new_content, manual section is appended.
    """
    # Extract manual additions from old content
    start_marker = "<!-- MANUAL ADDITIONS START -->"
    end_marker = "<!-- MANUAL ADDITIONS END -->"

    # Find manual additions in old content
    start_idx = old_content.find(start_marker)
    end_idx = old_content.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        # No manual additions to preserve
        return new_content

    # Extract the manual section (including markers)
    manual_section = old_content[start_idx:end_idx + len(end_marker)]

    # Find where to inject in new content
    new_start_idx = new_content.find(start_marker)
    new_end_idx = new_content.find(end_marker)

    if new_start_idx == -1 or new_end_idx == -1:
        # New content doesn't have markers, append at end
        return new_content.rstrip() + "\n\n" + manual_section + "\n"

    # Replace the section in new content with the preserved manual section
    before = new_content[:new_start_idx]
    after = new_content[new_end_idx + len(end_marker):]

    return before + manual_section + after


def update_agent_context(
    agent_type: str,
    tech_stack: Dict[str, Optional[str]],
    feature_slug: str,
    repo_root: Path,
    feature_dir: Optional[Path] = None,
) -> None:
    """
    Update agent context file with tech stack from plan.md.

    Args:
        agent_type: One of the keys in AGENT_CONFIGS (claude, gemini, etc.)
        tech_stack: Dictionary from parse_plan_for_tech_stack()
        feature_slug: Current feature branch/slug
        repo_root: Repository root directory
        feature_dir: Feature directory path (for worktree-local updates)

    Raises:
        ValueError: If agent_type is not supported
        FileNotFoundError: If agent file doesn't exist
    """
    if agent_type not in AGENT_CONFIGS:
        raise ValueError(
            f"Unsupported agent type: {agent_type}. "
            f"Supported types: {', '.join(AGENT_CONFIGS.keys())}"
        )

    agent_file_path = repo_root / AGENT_CONFIGS[agent_type]

    # If it's a worktree-local file, use feature_dir
    if feature_dir and agent_file_path.is_relative_to(repo_root):
        worktree_agent_file = feature_dir / AGENT_CONFIGS[agent_type]
        if worktree_agent_file.exists():
            agent_file_path = worktree_agent_file

    if not agent_file_path.exists():
        raise FileNotFoundError(f"Agent file not found: {agent_file_path}")

    # Read existing content
    old_content = agent_file_path.read_text()

    # Format new tech entries
    new_tech_entries = format_technology_stack(tech_stack, feature_slug)

    # Prepare change entry for Recent Changes section
    tech_parts = []
    if tech_stack.get("language"):
        tech_parts.append(tech_stack["language"])
    if tech_stack.get("dependencies"):
        tech_parts.append(tech_stack["dependencies"])

    tech_description = " + ".join(tech_parts) if tech_parts else tech_stack.get("storage", "")
    new_change_entry = f"- {feature_slug}: Added {tech_description}" if tech_description else ""

    # Process file line by line to update sections
    lines = old_content.splitlines(keepends=True)
    new_lines = []

    in_tech_section = False
    in_changes_section = False
    tech_entries_added = False
    existing_changes_count = 0
    current_date = datetime.now().strftime("%Y-%m-%d")

    for line in lines:
        # Handle Active Technologies section
        if line.strip() == "## Active Technologies":
            new_lines.append(line)
            in_tech_section = True
            continue

        # Handle Recent Changes section - MUST come before generic section exit checks
        if line.strip() == "## Recent Changes":
            # If we were in tech section, close it first
            if in_tech_section and not tech_entries_added and new_tech_entries:
                for entry in new_tech_entries:
                    new_lines.append(entry + "\n")
                tech_entries_added = True
                in_tech_section = False

            new_lines.append(line)
            in_changes_section = True
            # Add new change entry right after heading
            if new_change_entry:
                new_lines.append(new_change_entry + "\n")
            continue

        # Check if we're exiting tech section
        if in_tech_section and line.strip().startswith("##"):
            # Add new tech entries before closing section
            if not tech_entries_added and new_tech_entries:
                for entry in new_tech_entries:
                    new_lines.append(entry + "\n")
                tech_entries_added = True
            new_lines.append(line)
            in_tech_section = False
            continue

        # Check if we're exiting changes section
        if in_changes_section and line.strip().startswith("##"):
            new_lines.append(line)
            in_changes_section = False
            continue

        # In changes section: keep only first 2 existing changes, skip empty lines
        if in_changes_section:
            if line.strip().startswith("- "):
                if existing_changes_count < 2:
                    new_lines.append(line)
                    existing_changes_count += 1
                continue
            elif line.strip() == "":
                # Skip empty lines in changes section
                continue

        # Update last updated timestamp
        if "**Last updated**:" in line or "*Last updated*:" in line:
            # Replace date in format YYYY-MM-DD
            line = re.sub(r'\d{4}-\d{2}-\d{2}', current_date, line)

        new_lines.append(line)

    # Post-loop: if still in tech section and haven't added entries
    if in_tech_section and not tech_entries_added and new_tech_entries:
        for entry in new_tech_entries:
            new_lines.append(entry + "\n")

    new_content = "".join(new_lines)

    # Preserve manual additions
    final_content = preserve_manual_additions(old_content, new_content)

    # Write updated content
    agent_file_path.write_text(final_content)


def get_supported_agent_types() -> List[str]:
    """Return list of supported agent types."""
    return list(AGENT_CONFIGS.keys())


def get_agent_file_path(agent_type: str, repo_root: Path) -> Path:
    """
    Get the file path for a specific agent type.

    Args:
        agent_type: One of the keys in AGENT_CONFIGS
        repo_root: Repository root directory

    Returns:
        Path to the agent configuration file

    Raises:
        ValueError: If agent_type is not supported
    """
    if agent_type not in AGENT_CONFIGS:
        raise ValueError(
            f"Unsupported agent type: {agent_type}. "
            f"Supported types: {', '.join(AGENT_CONFIGS.keys())}"
        )

    return repo_root / AGENT_CONFIGS[agent_type]
