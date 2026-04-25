"""Prompt generation for ``spec-kitty next``.

Independent from ``workflow.py``.  Generates prompt text for each action type,
writes it to a temp file, and returns ``(prompt_text, prompt_file_path)``.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

_EMPTY_LIST_PLACEHOLDER = "(none)"

from charter.context import build_charter_context
from charter.resolver import GovernanceResolutionError, resolve_governance
from specify_cli.core.paths import get_feature_target_branch
from runtime.discovery.resolver import resolve_command
from specify_cli.status.wp_metadata import read_wp_frontmatter
from specify_cli.workspace_context import resolve_workspace_for_wp


def build_prompt(
    action: str,
    feature_dir: Path,
    mission_slug: str,
    wp_id: str | None,
    agent: str,
    repo_root: Path,
    mission_type: str,
) -> tuple[str, Path]:
    """Build a prompt for the given action.

    Returns ``(prompt_text, prompt_file_path)``.

    For planning actions (specify, plan, tasks, research, accept) the prompt is
    the command template with a feature context header prepended.

    For implement/review actions the prompt includes workspace paths, isolation
    rules, WP content, and completion instructions.
    """
    if action in ("implement", "review") and wp_id:
        prompt_text = _build_wp_prompt(action, feature_dir, mission_slug, wp_id, agent, repo_root, mission_type)
    else:
        prompt_text = _build_template_prompt(action, feature_dir, mission_slug, agent, repo_root, mission_type)

    prompt_file = _write_to_temp(action, wp_id, prompt_text, agent=agent, mission_slug=mission_slug)
    return prompt_text, prompt_file


def build_decision_prompt(
    question: str,
    options: list[str] | None,
    decision_id: str,
    mission_slug: str,
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
        f"Mission: {mission_slug}",
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
    lines.append(f'  spec-kitty next --agent {agent} --mission {mission_slug} --answer "<your answer>" --decision-id "{decision_id}"')

    prompt_text = "\n".join(lines)
    prompt_file = _write_to_temp(
        "decision",
        None,
        prompt_text,
        agent=agent,
        mission_slug=mission_slug,
    )
    return prompt_text, prompt_file


def _build_template_prompt(
    action: str,
    feature_dir: Path,
    mission_slug: str,
    agent: str,
    repo_root: Path,
    mission_type: str,
) -> str:
    """Build prompt from a command template file."""
    result = resolve_command(f"{action}.md", repo_root, mission=mission_type)
    template_content = result.path.read_text(encoding="utf-8")

    header = _mission_context_header(mission_slug, feature_dir, agent)
    governance = _governance_context(repo_root, action=action)
    return f"{header}\n\n{governance}\n\n{template_content}"


def _build_wp_context_header(
    action: str,
    wp_id: str,
    agent: str,
    mission_slug: str,
    mission_type: str,
    workspace: Any,
    workspace_path: Any,
    repo_root: Path,
) -> list[str]:
    """Build the banner + governance block at the top of a WP prompt."""
    lines: list[str] = [
        "=" * 80,
        f"{action.upper()}: {wp_id}",
        "=" * 80,
        "",
        f"Agent: {agent}",
        f"Mission: {mission_slug}",
        f"Mission Type: {mission_type}",
        f"Workspace: {workspace_path}",
    ]
    if workspace.lane_id:
        shared = ", ".join(workspace.lane_wp_ids or [wp_id])
        lines.append(f"Workspace contract: lane {workspace.lane_id} shared by {shared}")
    else:
        lines.append("Workspace contract: repository root planning workspace")
    lines += ["", _governance_context(repo_root, action=action), ""]
    return lines


def _build_isolation_rules_lines(action: str, wp_id: str) -> list[str]:
    """Build the WP isolation rules warning block."""
    verb = "IMPLEMENTING" if action == "implement" else "REVIEWING"
    return [
        "=" * 78,
        "  CRITICAL: WORK PACKAGE ISOLATION RULES",
        "=" * 78,
        f"  YOU ARE {verb}: {wp_id}",
        "",
        "  DO:",
        f"    - Only modify status of {wp_id}",
        "    - Ignore git commits and status changes from other agents",
        "",
        "  DO NOT:",
        f"    - Change status of any WP other than {wp_id}",
        "    - React to or investigate other WPs' status changes",
        "=" * 78,
        "",
    ]


def _build_working_dir_lines(workspace: Any, workspace_path: Any) -> list[str]:
    """Build the WORKING DIRECTORY section."""
    lines = ["WORKING DIRECTORY:", f"  cd {workspace_path}"]
    if not workspace.lane_id:
        lines.append("  # Planning-artifact work for this WP happens in the repository root")
    lines.append("")
    return lines


def _build_review_pathspec(wp_files: list[Path], mission_slug: str) -> str:
    """Derive ``-- pathspec`` string for planning-workspace review diffs."""
    if not wp_files:
        return ""
    wp_meta, _ = read_wp_frontmatter(wp_files[0])
    if not wp_meta.owned_files:
        return ""
    specs = list(wp_meta.owned_files)
    mission_root = f"kitty-specs/{mission_slug}/"
    if any(p.startswith(mission_root) for p in specs):
        specs += [
            f":(exclude){mission_root}tasks/**",
            f":(exclude){mission_root}tasks.md",
            f":(exclude){mission_root}status.events.jsonl",
            f":(exclude){mission_root}status.json",
        ]
    return " -- " + " ".join(specs)


def _find_wp_claim_commit(wp_id: str, wp_files: list[Path], repo_root: Path) -> str | None:
    """Return the git SHA of the commit that claimed wp_id for implementation."""
    claim = subprocess.run(
        ["git", "log", "--format=%H%x00%s", "--", *(str(p) for p in wp_files)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    for raw in claim.stdout.splitlines():
        commit_hash, _, subject = raw.partition("\x00")
        if not commit_hash:
            continue
        claim_subjects = (
            f"Move {wp_id} to in_progress",
            f"{wp_id} claimed for implementation",
            f"Start {wp_id} implementation",
        )
        if any(s in subject for s in claim_subjects):
            return commit_hash.strip()
    return None


def _build_review_commands_lines(
    wp_id: str,
    wp_files: list[Path],
    mission_slug: str,
    feature_dir: Path,
    workspace: Any,
    repo_root: Path,
) -> list[str]:
    """Build the REVIEW COMMANDS section (only emitted when action == 'review')."""
    lines = ["REVIEW COMMANDS:"]
    if workspace.lane_id:
        base = (
            workspace.context.base_branch
            if workspace.context and workspace.context.base_branch
            else get_feature_target_branch(repo_root, mission_slug)
        )
        lines += [
            f"  git log {base}..HEAD --oneline",
            f"  git diff {base}..HEAD --stat",
        ]
    else:
        review_paths = _build_review_pathspec(wp_files, mission_slug)
        review_base = _find_wp_claim_commit(wp_id, wp_files, repo_root)
        if review_base is None:
            lines.append("  unavailable: no deterministic implementation claim commit found for this WP")
        else:
            lines += [
                f"  git log {review_base}..HEAD --oneline{review_paths}",
                f"  git diff {review_base}..HEAD --stat{review_paths}",
            ]
    lines.append("")
    return lines


def _build_completion_lines(
    action: str, wp_id: str, subtask_cmd: str, mission_slug: str
) -> list[str]:
    """Build the WHEN DONE completion instructions."""
    lines = ["WHEN DONE:"]
    if action == "implement":
        lines += [
            f"  spec-kitty agent tasks mark-status {subtask_cmd} --status done --mission {mission_slug}",
            f'  spec-kitty agent tasks move-task {wp_id} --to for_review --mission {mission_slug} --note "Ready for review"',
        ]
    else:
        lines += [
            f'  APPROVE: spec-kitty agent tasks move-task {wp_id} --to approved --mission {mission_slug} --note "Review passed"',
            "           approved means review-passed; merge will later record done",
            f"  REJECT:  spec-kitty agent tasks move-task {wp_id} --to planned --review-feedback-file <feedback-file> --mission {mission_slug}",
        ]
    return lines


def _build_wp_prompt(
    action: str,
    feature_dir: Path,
    mission_slug: str,
    wp_id: str,
    agent: str,
    repo_root: Path,
    mission_type: str,
) -> str:
    """Build prompt for implement or review actions with WP context."""
    workspace = resolve_workspace_for_wp(repo_root, mission_slug, wp_id)
    workspace_path = workspace.worktree_path
    wp_files = sorted((feature_dir / "tasks").glob(f"{wp_id}*.md"))
    wp_meta = None
    if wp_files:
        wp_meta, _ = read_wp_frontmatter(wp_files[0])
    subtask_ids = [str(t) for t in (wp_meta.subtasks if wp_meta is not None else []) if isinstance(t, str)]
    subtask_cmd = " ".join(subtask_ids) if subtask_ids else "<subtask-ids>"
    wp_content = _read_wp_content(feature_dir, wp_id)

    lines: list[str] = []
    lines += _build_wp_context_header(action, wp_id, agent, mission_slug, mission_type, workspace, workspace_path, repo_root)
    lines += _build_isolation_rules_lines(action, wp_id)
    lines += _build_working_dir_lines(workspace, workspace_path)
    if action == "review":
        lines += _build_review_commands_lines(wp_id, wp_files, mission_slug, feature_dir, workspace, repo_root)
    lines += ["=" * 78, "  WORK PACKAGE PROMPT BEGINS", "=" * 78, "", wp_content, "", "=" * 78, "  WORK PACKAGE PROMPT ENDS", "=" * 78, ""]
    lines += _build_completion_lines(action, wp_id, subtask_cmd, mission_slug)
    return "\n".join(lines)


def _mission_context_header(mission_slug: str, feature_dir: Path, agent: str) -> str:
    """Build a mission context header for template prompts."""
    lines = [
        "=" * 80,
        f"Mission: {mission_slug}",
        f"Agent: {agent}",
        f"Mission directory: {feature_dir}",
        "=" * 80,
    ]
    return "\n".join(lines)


def _governance_context(repo_root: Path, action: str | None = None) -> str:
    """Render governance context for prompt preamble.

    For bootstrap actions, charter context is injected on first load.
    Falls back to compact governance rendering if charter artifacts are missing.
    """
    if action:
        try:
            context = build_charter_context(repo_root, action=action, mark_loaded=True)
            if context.mode != "missing":
                return context.text
        except Exception:
            # Non-fatal: fall back to compact governance rendering.
            pass

    return _legacy_governance_context(repo_root)


def _legacy_governance_context(repo_root: Path) -> str:
    """Render compact governance context via resolver."""
    try:
        resolution = resolve_governance(repo_root)
    except GovernanceResolutionError as exc:
        return f"Governance: unresolved ({exc})"
    except Exception as exc:
        return f"Governance: unavailable ({exc})"

    paradigms = ", ".join(resolution.paradigms) if resolution.paradigms else _EMPTY_LIST_PLACEHOLDER
    directives = ", ".join(resolution.directives) if resolution.directives else _EMPTY_LIST_PLACEHOLDER
    tools = ", ".join(resolution.tools) if resolution.tools else _EMPTY_LIST_PLACEHOLDER

    lines = [
        "Governance:",
        f"  - Template set: {resolution.template_set}",
        f"  - Paradigms: {paradigms}",
        f"  - Directives: {directives}",
        f"  - Tools: {tools}",
    ]
    if resolution.diagnostics:
        lines.append(f"  - Diagnostics: {' | '.join(resolution.diagnostics)}")
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
    mission_slug: str = "unknown",
) -> Path:
    """Write prompt content to a temp file.

    Filenames include agent and feature to avoid collisions when multiple
    agents or features run concurrently.
    """
    wp_suffix = f"-{wp_id}" if wp_id else ""
    filename = f"spec-kitty-next-{agent}-{mission_slug}-{action}{wp_suffix}.md"
    prompt_path = Path(tempfile.gettempdir()) / filename
    prompt_path.write_text(content, encoding="utf-8")
    return prompt_path
