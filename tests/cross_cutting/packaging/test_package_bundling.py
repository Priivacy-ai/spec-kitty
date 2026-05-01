"""Validate package bundling includes correct templates."""

from pathlib import Path
import tarfile
import zipfile

import pytest

LEGACY_SDIST_SEGMENT = "/src/doctrine/" + "agent" + "-" + "profiles"


def test_command_templates_not_bundled():
    """WP10: command-templates directories must not exist in src/specify_cli or src/doctrine.

    Shim generation (spec-kitty agent shim) replaces rendered template files.
    No command-templates should remain to be bundled into the distribution.

    Exception: src/specify_cli/missions/software-dev/command-templates/ is
    intentionally retained as the canonical source for prompt-driven commands
    (restored in feature 058).
    """
    spec_kitty_root = Path(__file__).parent.parent.parent.parent
    missions_dir = spec_kitty_root / "src" / "specify_cli" / "missions"

    # software-dev/command-templates/ is the canonical source for prompt-driven
    # commands and is intentionally kept (feature 058).
    allowed = {
        str((missions_dir / "software-dev" / "command-templates").relative_to(spec_kitty_root)),
    }

    found = []
    for base in [
        spec_kitty_root / "src" / "specify_cli",
        spec_kitty_root / "src" / "doctrine",
    ]:
        if base.exists():
            for d in base.rglob("command-templates"):
                if d.is_dir():
                    rel = str(d.relative_to(spec_kitty_root))
                    if rel not in allowed:
                        found.append(rel)

    assert len(found) == 0, (
        f"command-templates directories still present (WP10 deletion incomplete): {found}"
    )


@pytest.mark.slow
def test_sdist_bundles_templates(build_artifacts: dict[str, Path]):
    """Verify source distribution includes templates under src/specify_cli/."""
    sdist = build_artifacts["sdist"]

    with tarfile.open(sdist, "r:gz") as tar:
        members = tar.getnames()

        # Should have templates under src/specify_cli/
        templates = [m for m in members if "/src/specify_cli/templates/" in m]
        assert len(templates) > 0, "specify_cli/templates/ not found in sdist"

        # WP10: non-canonical command-templates must NOT be in sdist.
        # Exception: software-dev/command-templates/ is the canonical source
        # for prompt-driven commands (restored in feature 058).
        cmd_templates = [
            m for m in members
            if "command-templates" in m and m.endswith(".md")
            and "software-dev/command-templates" not in m
        ]
        assert len(cmd_templates) == 0, (
            f"Non-canonical command-templates found in sdist: {cmd_templates[:5]}"
        )
        legacy_agent_profile_paths = [m for m in members if LEGACY_SDIST_SEGMENT in m]
        assert legacy_agent_profile_paths == [], (
            f"Legacy {LEGACY_SDIST_SEGMENT} entries found in sdist: "
            f"{legacy_agent_profile_paths[:5]}"
        )

        # Git hooks are intentionally not bundled in 2.x
        git_hooks = [m for m in members if "git-hooks/" in m]
        assert len(git_hooks) == 0, f"Unexpected git hook assets bundled: {git_hooks}"


@pytest.mark.slow
def test_wheel_bundles_templates_correctly(installed_wheel_venv: dict[str, Path]):
    """Verify wheel includes templates and doctrine skills for importlib.resources."""
    import subprocess

    python = installed_wheel_venv["python"]

    result = subprocess.run(
        [
            str(python),
            "-c",
            "from importlib.resources import files; "
            "t = files('specify_cli').joinpath('templates'); "
            "print(list(t.iterdir()))",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Failed to check templates: {result.stderr}"
    output = result.stdout
    # WP10: command-templates were deleted — shims replace them
    assert "command-templates" not in output, (
        "command-templates should NOT be in bundled package (deleted in WP10)"
    )
    assert "git-hooks" not in output, "git-hooks should not be bundled in 2.x"

    result = subprocess.run(
        [
            str(python),
            "-c",
            "from importlib.resources import files; "
            "skill = files('doctrine').joinpath('skills', 'spec-kitty-setup-doctor', 'SKILL.md'); "
            "print(skill.is_file())",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Failed to check bundled doctrine skills: {result.stderr}"
    assert result.stdout.strip() == "True", "Bundled canonical skill missing from wheel"
