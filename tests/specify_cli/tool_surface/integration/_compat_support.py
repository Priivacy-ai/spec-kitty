"""Shared helpers for the ToolSurfaceContract migration compatibility gate.

These helpers run the **checkout-local** ``specify_cli`` package (never the
globally-installed ``spec-kitty`` console script) and provide deterministic,
controlled fixtures so the compatibility tests do not depend on ambient
machine state (configured agents, installed tools, etc.).

The helpers are deliberately importable as a plain module (rather than living
only inside ``conftest.py``) so each branch can be exercised directly by a
focused unit test in :mod:`test_compat_support`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Stable controlled-fixture content. A single minimal agent keeps doctor output
# deterministic regardless of what the developer has configured locally.
CONTROLLED_AGENT = "codex"
EMPTY_MANIFEST: dict[str, Any] = {"schema_version": 1, "entries": []}

# Wide terminal so Rich does not wrap table content unpredictably across hosts.
_WIDE_COLUMNS = "200"


def project_root() -> Path:
    """Return the checkout root by walking up to the nearest ``pyproject.toml``.

    Works from both the main checkout and a lane worktree, where the test file
    sits at a different depth than the simple ``parents[N]`` assumption.
    """
    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    # Fallback: should not happen inside the repo, but keep the contract honest.
    raise RuntimeError("Could not locate checkout root (no pyproject.toml found)")


@dataclass(frozen=True)
class CliResult:
    """Outcome of a checkout-local ``specify_cli`` invocation."""

    returncode: int
    stdout: str
    stderr: str

    def json(self) -> Any:
        """Parse ``stdout`` as JSON (raises if not valid JSON)."""
        return json.loads(self.stdout)


def run_spec_kitty(*args: str, cwd: Path | None = None) -> CliResult:
    """Run ``specify_cli`` from the checkout under test.

    IMPORTANT: this MUST NOT shell out to ``["spec-kitty", ...]`` -- that would
    invoke the globally-installed version, not the checkout being verified.
    ``sys.executable -m specify_cli`` guarantees the checkout's package runs.
    """
    env = dict(os.environ)
    env["COLUMNS"] = _WIDE_COLUMNS
    # Pin the project root explicitly so resolution never escapes to an
    # ancestor checkout when ``cwd`` is a temporary fixture directory.
    env["SPECIFY_REPO_ROOT"] = str(cwd) if cwd is not None else str(project_root())
    completed = subprocess.run(
        [sys.executable, "-m", "specify_cli", *args],
        capture_output=True,
        text=True,
        cwd=str(cwd or project_root()),
        env=env,
        check=False,
    )
    return CliResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def write_controlled_project(root: Path, *, agents: list[str] | None = None) -> Path:
    """Create a minimal, deterministic ``.kittify`` project under ``root``.

    Returns the project directory (``root`` itself). The project contains a
    fixed agent list and an empty command-skills manifest so that
    ``doctor skills`` and ``agent config`` produce machine-independent output.
    """
    available = agents if agents is not None else [CONTROLLED_AGENT]
    kittify = root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "config.yaml").write_text(
        _render_config_yaml(available),
        encoding="utf-8",
    )
    (kittify / "command-skills-manifest.json").write_text(
        json.dumps(EMPTY_MANIFEST),
        encoding="utf-8",
    )
    return root


def _render_config_yaml(available: list[str]) -> str:
    """Render a minimal ``config.yaml`` without depending on a YAML writer."""
    lines = ["agents:", "  available:"]
    if available:
        lines.extend(f"    - {agent}" for agent in available)
    else:
        lines[-1] = "  available: []"
    return "\n".join(lines) + "\n"


def schema_shape(value: Any) -> Any:
    """Reduce a JSON value to its *shape* (keys + types), discarding content.

    - dicts -> mapping of key -> shape(value), keys sorted for stability
    - lists -> single-element list describing the element shape (or ``[]``)
    - scalars -> the type name string ("str", "int", "bool", "float", "null")

    This lets baseline fixtures capture structure that is independent of the
    machine the test runs on (no paths, no ambient tool config, no counts).
    """
    if isinstance(value, dict):
        return {key: schema_shape(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        if not value:
            return []
        # Merge element shapes so a heterogeneous list still yields one shape.
        merged: dict[str, Any] = {}
        non_dict_shape: Any = None
        for item in value:
            item_shape = schema_shape(item)
            if isinstance(item_shape, dict):
                merged.update(item_shape)
            else:
                non_dict_shape = item_shape
        return [merged] if merged else [non_dict_shape]
    if value is None:
        return "null"
    return type(value).__name__
