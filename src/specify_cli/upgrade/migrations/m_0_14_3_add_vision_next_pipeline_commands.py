"""Migration: Add vision, next, and pipeline slash commands.

Deploys three new central command templates to all configured agent
directories so existing projects get the commands on upgrade:

- /spec-kitty.vision  – Product vision exploration and feature map
- /spec-kitty.next    – Recommend the next step with a copy-paste command
- /spec-kitty.pipeline – Implement all WPs for a feature in one session
"""

from __future__ import annotations

from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


# Templates to deploy (source filename -> agent filename stem)
NEW_TEMPLATES = ["next", "pipeline", "vision"]


def _find_central_template(name: str) -> Path | None:
    """Find a central command template in the installed package or local repo.

    Args:
        name: Template name without extension (e.g. "next")

    Returns:
        Path to the template file, or None if not found.
    """
    filename = f"{name}.md"

    # Try from installed package
    try:
        from importlib.resources import files

        pkg_files = files("specify_cli")
        template_path = pkg_files.joinpath(
            "templates", "command-templates", filename
        )
        template_str = str(template_path)
        if Path(template_str).exists():
            return Path(template_str)
    except (ImportError, TypeError, AttributeError):
        pass

    # Try from package __file__ location
    try:
        import specify_cli

        pkg_dir = Path(specify_cli.__file__).parent
        template_file = pkg_dir / "templates" / "command-templates" / filename
        if template_file.exists():
            return template_file
    except (ImportError, AttributeError):
        pass

    # Fallback for development: walk up to repo root
    try:
        cwd = Path.cwd()
        for parent in [cwd, *list(cwd.parents)]:
            template_file = (
                parent
                / "src"
                / "specify_cli"
                / "templates"
                / "command-templates"
                / filename
            )
            pyproject = parent / "pyproject.toml"
            if template_file.exists() and pyproject.exists():
                try:
                    content = pyproject.read_text(encoding="utf-8-sig")
                    if "spec-kitty-cli" in content:
                        return template_file
                except OSError:
                    pass
    except OSError:
        pass

    return None


@MigrationRegistry.register
class AddVisionNextPipelineCommandsMigration(BaseMigration):
    """Deploy vision, next, and pipeline command templates to agent directories."""

    migration_id = "0.14.3_add_vision_next_pipeline_commands"
    description = "Add /spec-kitty.vision, /spec-kitty.next, and /spec-kitty.pipeline slash commands"
    target_version = "0.14.3"

    def detect(self, project_path: Path) -> bool:
        """Check if any configured agent is missing the new templates."""
        from specify_cli.agent_utils import get_agent_dirs_for_project

        agent_dirs = get_agent_dirs_for_project(project_path)

        for agent_root, subdir in agent_dirs:
            agent_dir = project_path / agent_root / subdir
            if not agent_dir.exists():
                continue

            for name in NEW_TEMPLATES:
                # Agent filenames use spec-kitty.{stem}.{ext} pattern
                # Most agents use .md; check for any matching file
                matches = list(agent_dir.glob(f"spec-kitty.{name}.*"))
                if not matches:
                    return True

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Verify all three source templates can be found."""
        missing = []
        for name in NEW_TEMPLATES:
            if _find_central_template(name) is None:
                missing.append(name)

        if missing:
            return (
                False,
                f"Could not locate package templates: {', '.join(missing)}. "
                "This is expected in test environments. "
                "Run 'spec-kitty upgrade' again after installation.",
            )

        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Copy the three new templates to all configured agent directories."""
        from specify_cli.agent_utils import AGENT_DIR_TO_KEY, get_agent_dirs_for_project
        from specify_cli.core.config import AGENT_COMMAND_CONFIG
        from specify_cli.template.asset_generator import render_command_template

        changes: list[str] = []
        errors: list[str] = []

        # Resolve source templates
        templates: dict[str, Path] = {}
        for name in NEW_TEMPLATES:
            path = _find_central_template(name)
            if path is None:
                errors.append(f"Could not locate template: {name}.md")
                return MigrationResult(success=False, errors=errors)
            templates[name] = path

        agent_dirs = get_agent_dirs_for_project(project_path)
        if not agent_dirs:
            return MigrationResult(
                success=True,
                changes_made=["No agents configured, skipping template deployment"],
            )

        for agent_root, subdir in agent_dirs:
            agent_dir = project_path / agent_root / subdir
            if not agent_dir.exists():
                continue

            agent_key = AGENT_DIR_TO_KEY.get(agent_root)
            if agent_key is None:
                continue

            config = AGENT_COMMAND_CONFIG.get(agent_key)
            if config is None:
                continue

            ext = config["ext"]

            for name, template_path in templates.items():
                stem = name
                if agent_key == "codex":
                    stem = stem.replace("-", "_")
                filename = f"spec-kitty.{stem}.{ext}" if ext else f"spec-kitty.{stem}"
                dest = agent_dir / filename

                if dry_run:
                    changes.append(f"Would create {agent_root}/{subdir}/{filename}")
                else:
                    try:
                        rendered = render_command_template(
                            template_path,
                            "uv",  # default script type
                            agent_key,
                            config["arg_format"],
                            ext,
                        )
                        dest.write_text(rendered, encoding="utf-8")
                        changes.append(f"Created {agent_root}/{subdir}/{filename}")
                    except OSError as e:
                        errors.append(
                            f"Failed to create {agent_root}/{subdir}/{filename}: {e}"
                        )

        return MigrationResult(
            success=len(errors) == 0,
            changes_made=changes,
            errors=errors,
        )
