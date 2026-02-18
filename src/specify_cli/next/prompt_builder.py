"""Prompt generation for ``spec-kitty next``.

Independent from ``workflow.py``.  Generates prompt text for each action type,
writes it to a temp file, and returns ``(prompt_text, prompt_file_path)``.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from specify_cli.runtime.resolver import resolve_command


def build_prompt(
    action: str,
    feature_dir: Path,
    feature_slug: str,
    wp_id: str | None,
    agent: str,
    repo_root: Path,
    mission_key: str,
) -> tuple[str, Path]:
    """Build a prompt for the given action.

    Returns ``(prompt_text, prompt_file_path)``.

    For planning actions (specify, plan, tasks, research, accept) the prompt is
    the command template with a feature context header prepended.

    For implement/review actions the prompt includes workspace paths, isolation
    rules, WP content, and completion instructions.
    """
    if action in ("implement", "review") and wp_id:
        prompt_text = _build_wp_prompt(action, feature_dir, feature_slug, wp_id, agent, repo_root, mission_key)
    else:
        prompt_text = _build_template_prompt(action, feature_dir, feature_slug, agent, repo_root, mission_key)

    prompt_file = _write_to_temp(action, wp_id, prompt_text, agent=agent, feature_slug=feature_slug)
    return prompt_text, prompt_file


def build_decision_prompt(
    question: str,
    options: list[str] | None,
    decision_id: str,
    feature_slug: str,
    agent: str,
) -> tuple[str, Path]:
    """Build a prompt for a decision_required response.

    Returns ``(prompt_text, prompt_file_path)``.
    """
    lines: list[str] = [
        "=" * 80,
        "DECISION REQUIRED",
        "=" * 80,
        "",
        f"Feature: {feature_slug}",
        f"Agent: {agent}",
        f"Decision ID: {decision_id}",
        "",
        f"Question: {question}",
        "",
    ]

    if options:
        lines.append("Options:")
        for i, opt in enumerate(options, 1):
            lines.append(f"  {i}. {opt}")
        lines.append("")

    lines.append("To answer:")
    lines.append(f'  spec-kitty next --agent {agent} --feature {feature_slug} --answer "<your answer>" --decision-id "{decision_id}"')

    prompt_text = "\n".join(lines)
    prompt_file = _write_to_temp(
        "decision", None, prompt_text,
        agent=agent, feature_slug=feature_slug,
    )
    return prompt_text, prompt_file


def _build_template_prompt(
    action: str,
    feature_dir: Path,
    feature_slug: str,
    agent: str,
    repo_root: Path,
    mission_key: str,
) -> str:
    """Build prompt from a command template file."""
    result = resolve_command(f"{action}.md", repo_root, mission=mission_key)
    template_content = result.path.read_text(encoding="utf-8")

    header = _feature_context_header(feature_slug, feature_dir, agent)
    return f"{header}\n\n{template_content}"


def _build_wp_prompt(
    action: str,
    feature_dir: Path,
    feature_slug: str,
    wp_id: str,
    agent: str,
    repo_root: Path,
    mission_key: str,
) -> str:
    """Build prompt for implement or review actions with WP context."""
    workspace_name = f"{feature_slug}-{wp_id}"
    workspace_path = repo_root / ".worktrees" / workspace_name

    # Read WP file content
    wp_content = _read_wp_content(feature_dir, wp_id)

    lines: list[str] = []
    lines.append("=" * 80)
    lines.append(f"{action.upper()}: {wp_id}")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Agent: {agent}")
    lines.append(f"Feature: {feature_slug}")
    lines.append(f"Mission: {mission_key}")
    lines.append(f"Workspace: {workspace_path}")
    lines.append("")

    # WP isolation rules
    lines.append("=" * 78)
    lines.append(f"  CRITICAL: WORK PACKAGE ISOLATION RULES")
    lines.append("=" * 78)
    lines.append(f"  YOU ARE {'IMPLEMENTING' if action == 'implement' else 'REVIEWING'}: {wp_id}")
    lines.append("")
    lines.append("  DO:")
    lines.append(f"    - Only modify status of {wp_id}")
    lines.append("    - Ignore git commits and status changes from other agents")
    lines.append("")
    lines.append("  DO NOT:")
    lines.append(f"    - Change status of any WP other than {wp_id}")
    lines.append("    - React to or investigate other WPs' status changes")
    lines.append("=" * 78)
    lines.append("")

    # Working directory
    lines.append(f"WORKING DIRECTORY:")
    lines.append(f"  cd {workspace_path}")
    lines.append("")

    if action == "review":
        lines.append("REVIEW COMMANDS:")
        lines.append(f"  git log main..HEAD --oneline")
        lines.append(f"  git diff main..HEAD --stat")
        lines.append("")

    # WP content
    lines.append("=" * 78)
    lines.append("  WORK PACKAGE PROMPT BEGINS")
    lines.append("=" * 78)
    lines.append("")
    lines.append(wp_content)
    lines.append("")
    lines.append("=" * 78)
    lines.append("  WORK PACKAGE PROMPT ENDS")
    lines.append("=" * 78)
    lines.append("")

    # Completion instructions
    lines.append("WHEN DONE:")
    if action == "implement":
        lines.append(f"  spec-kitty agent tasks move-task {wp_id} --to for_review --note \"Ready for review\"")
    else:
        lines.append(f"  APPROVE: spec-kitty agent tasks move-task {wp_id} --to done --note \"Review passed\"")
        lines.append(f"  REJECT:  spec-kitty agent tasks move-task {wp_id} --to planned --note \"Changes requested\"")

    return "\n".join(lines)


def _feature_context_header(feature_slug: str, feature_dir: Path, agent: str) -> str:
    """Build a feature context header for template prompts."""
    lines = [
        "=" * 80,
        f"Feature: {feature_slug}",
        f"Agent: {agent}",
        f"Feature directory: {feature_dir}",
        "=" * 80,
    ]
    return "\n".join(lines)


def _read_wp_content(feature_dir: Path, wp_id: str) -> str:
    """Read WP file content from the tasks directory."""
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        return f"[WP file not found: tasks directory missing at {tasks_dir}]"

    # Find matching WP file
    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        if wp_file.stem.startswith(wp_id):
            try:
                return wp_file.read_text(encoding="utf-8")
            except OSError:
                return f"[Error reading {wp_file}]"

    return f"[WP file not found for {wp_id} in {tasks_dir}]"


def _write_to_temp(
    action: str,
    wp_id: str | None,
    content: str,
    *,
    agent: str = "unknown",
    feature_slug: str = "unknown",
) -> Path:
    """Write prompt content to a temp file.

    Filenames include agent and feature to avoid collisions when multiple
    agents or features run concurrently.
    """
    wp_suffix = f"-{wp_id}" if wp_id else ""
    filename = f"spec-kitty-next-{agent}-{feature_slug}-{action}{wp_suffix}.md"
    prompt_path = Path(tempfile.gettempdir()) / filename
    prompt_path.write_text(content, encoding="utf-8")
    return prompt_path
