"""Codex plugin bundle projection (WP06).

Projects the canonical tool surfaces into Codex's plugin bundle layout
(``.codex-plugin/``) and validates the result before publication.  The bundle
includes command skills and a marketplace catalog; it deliberately **excludes**
agent-level components (``"agents"`` key) and a hooks manifest pointer
(``"hooks"`` key) because the Codex plugin spec does not support either.

Per the Codex plugin contract (plugin-manifest-codex-01):

*  ``"hooks"`` MUST NOT appear as a top-level key — hooks are discovered by
   filesystem presence of the ``hooks/`` directory, not a manifest pointer.
*  ``"agents"`` MUST NOT appear at any level — Codex plugin-level agent
   packaging is unconfirmed; omit entirely.

**Scope guard (FR-016, C-006):**  :meth:`CodexBundleProjector.build` writes
only staging files under the caller-supplied ``output_dir`` and returns the
bundle directory path.  It never installs, registers, enables, or publishes the
bundle.
"""

from __future__ import annotations

from pathlib import Path

import typer

from ._builder import (
    MIN_SKILL_COUNT,
    BuildError,
    get_cli_version,
    is_semver,
    write_json,
)

# Codex plugin manifest lives under ``.codex-plugin/`` (not ``.claude-plugin/``).
_MANIFEST_DIR = ".codex-plugin"
_MANIFEST_NAME = "plugin.json"

# MCP companion file name and the manifest pointer the Codex schema expects.
# Per plugin-manifest-codex-01, ``mcpServers`` points at ``./.mcp.json`` and is
# emitted ONLY when a ``.mcp.json`` companion is present in the bundle.
_MCP_JSON_NAME = ".mcp.json"
_MCP_POINTER = f"./{_MCP_JSON_NAME}"

# Keys that Codex plugin.json must NEVER contain.
_FORBIDDEN_KEYS: frozenset[str] = frozenset({"hooks", "agents"})

# Top-level scalar fields required by the Codex plugin schema.
_REQUIRED_SCALAR_FIELDS: tuple[str, ...] = ("name", "version", "description")

# Required nested fields in the ``interface`` sub-object.
_REQUIRED_INTERFACE_FIELDS: tuple[str, ...] = ("displayName", "shortDescription")

# Maximum length for ``interface.shortDescription`` per the contract.
_SHORT_DESCRIPTION_MAX_LEN = 120

# Canonical author name.
_AUTHOR_NAME = "Priivacy AI"

# Install instructions emitted after marketplace.json is written.
_INSTALL_HINT = (
    "  To install: codex plugin marketplace add dist/spec-kitty-plugins/codex/marketplace.json\n"
    "  Or:         codex plugin install dist/spec-kitty-plugins/codex"
)


class CodexBundleProjector:
    """CLI-driven build projector for Codex plugin bundles (WP06).

    Produces a complete bundle at ``<output_dir>/codex/`` containing:

    * ``.codex-plugin/plugin.json`` — manifest with real version from
      ``importlib.metadata``; ``"hooks"`` and ``"agents"`` keys absent.
    * ``skills/<name>/SKILL.md`` — all canonical command skills.
    * ``marketplace.json`` — repo-local marketplace catalog.

    **Scope guard (FR-016, C-006):**  :meth:`build` writes staging files only
    under the caller-supplied ``output_dir``.  It never installs, registers,
    enables, or publishes the bundle.
    """

    def __init__(self, output_dir: Path) -> None:
        self.bundle_dir = output_dir / "codex"

    def build(self, *, skip_validate: bool = False) -> Path:
        """Build the Codex plugin bundle.

        Returns the bundle directory path.

        Raises
        ------
        BuildError
            When a required build step fails (e.g. too few skills, forbidden
            keys detected in the manifest, required fields missing).
        """
        self.bundle_dir.mkdir(parents=True, exist_ok=True)

        version = get_cli_version()
        if not is_semver(version):
            typer.echo(
                f"Warning: version {version!r} is not a clean semver "
                "string; the Codex validator may reject it.",
                err=True,
            )

        # Step 1: stage the optional MCP companion BEFORE the manifest so the
        # ``mcpServers`` pointer can be emitted only when ``.mcp.json`` is
        # actually present in the bundle ("when applicable", FR-027).
        self._copy_mcp_if_present()

        # Step 2: write the plugin manifest (pointer added iff .mcp.json present).
        self._generate_plugin_json(version)

        # Step 3: copy canonical command skills.
        skill_count = self._copy_skills(version)
        typer.echo(f"Skills: {skill_count} written to {self.bundle_dir / 'skills'}")

        # Step 4: write marketplace.json.
        self._generate_marketplace_json()

        # Step 5: copy hooks/ by filesystem presence if applicable.
        self._copy_hooks_if_present()

        if skip_validate:
            typer.echo(
                "Warning: Skipping Codex plugin validation (--skip-validate passed).",
                err=True,
            )

        return self.bundle_dir

    # ------------------------------------------------------------------
    # Manifest generation
    # ------------------------------------------------------------------

    def _generate_plugin_json(self, version: str) -> None:
        """Write ``.codex-plugin/plugin.json`` with required fields.

        The manifest MUST NOT include ``"hooks"`` or ``"agents"`` keys
        (Codex plugin contract, plugin-manifest-codex-01).
        """
        manifest: dict[str, object] = {
            "name": "spec-kitty",
            "version": version,
            "description": "Spec-Driven Development toolkit.",
            "author": {"name": _AUTHOR_NAME},
            "interface": {
                "displayName": "Spec Kitty",
                "shortDescription": "Spec-Driven Development for teams.",
            },
            "skills": "skills/",
        }
        # FR-027: advertise the MCP companion only when it was actually staged
        # into the bundle ("when applicable"). Absent companion => no pointer.
        if (self.bundle_dir / _MCP_JSON_NAME).is_file():
            manifest["mcpServers"] = _MCP_POINTER
        self._validate_manifest(manifest)
        manifest_path = self.bundle_dir / _MANIFEST_DIR / _MANIFEST_NAME
        write_json(manifest_path, manifest)

    def _validate_manifest(self, manifest: dict[str, object]) -> None:
        """Assert the manifest is schema-valid for the Codex plugin format.

        Raises
        ------
        BuildError
            When forbidden keys are present or required fields are missing.
        """
        # T025: forbidden keys must be absent.
        found_forbidden = _FORBIDDEN_KEYS & set(manifest)
        if found_forbidden:
            raise BuildError(
                f"Codex plugin.json must NOT contain: {sorted(found_forbidden)}"
            )

        # Required top-level scalar fields.
        for key in _REQUIRED_SCALAR_FIELDS:
            if not manifest.get(key):
                raise BuildError(
                    f"Codex plugin.json missing required field: {key!r}"
                )

        # author.name (nested).
        author = manifest.get("author")
        if not isinstance(author, dict) or not author.get("name"):
            raise BuildError(
                "Codex plugin.json missing required field: 'author.name'"
            )

        # interface.displayName and interface.shortDescription (nested).
        iface = manifest.get("interface")
        if not isinstance(iface, dict):
            raise BuildError(
                "Codex plugin.json missing required field: 'interface'"
            )
        for sub in _REQUIRED_INTERFACE_FIELDS:
            if not iface.get(sub):
                raise BuildError(
                    f"Codex plugin.json missing required field: 'interface.{sub}'"
                )

        # shortDescription length guard.
        short_desc = iface.get("shortDescription", "")
        if isinstance(short_desc, str) and len(short_desc) > _SHORT_DESCRIPTION_MAX_LEN:
            raise BuildError(
                f"Codex plugin.json 'interface.shortDescription' exceeds "
                f"{_SHORT_DESCRIPTION_MAX_LEN} characters."
            )

    # ------------------------------------------------------------------
    # Skills copy
    # ------------------------------------------------------------------

    def _copy_skills(self, version: str) -> int:
        """Render canonical command skills into ``bundle_dir/skills/``.

        Reuses the shared renderer from :mod:`~specify_cli.skills.command_installer`
        (same path as the Claude Code bundle, same SKILL.md format).

        Returns the number of skill files written.

        Raises
        ------
        BuildError
            When fewer than :data:`~specify_cli.tool_surface.bundles._builder.MIN_SKILL_COUNT`
            skills are available.
        """
        from specify_cli.skills.command_installer import (  # noqa: PLC0415
            CANONICAL_COMMANDS,
            _render_command_skill,
        )

        skills_dst = self.bundle_dir / "skills"
        skills_dst.mkdir(parents=True, exist_ok=True)

        render_key = "codex"
        count = 0
        for command in CANONICAL_COMMANDS:
            skill_bytes = _render_command_skill(Path("/"), command, render_key, version)
            skill_dir = skills_dst / f"spec-kitty.{command}"
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_bytes(skill_bytes)
            count += 1

        if count < MIN_SKILL_COUNT:
            raise BuildError(
                f"Expected at least {MIN_SKILL_COUNT} skills, found {count}. "
                "Check CANONICAL_COMMANDS in command_installer."
            )
        return count

    # ------------------------------------------------------------------
    # Hooks (filesystem-presence only, no manifest pointer)
    # ------------------------------------------------------------------

    def _copy_hooks_if_present(self) -> None:
        """Copy ``hooks/`` from the doctrine source if it exists.

        Per the Codex plugin contract, hooks are discovered by filesystem
        presence only — the ``"hooks"`` key MUST NOT appear in ``plugin.json``
        even when the directory is present.
        """
        import shutil  # noqa: PLC0415 — deferred to avoid top-level import cost

        try:
            import doctrine  # noqa: PLC0415
        except ImportError:
            return

        doctrine_root = Path(doctrine.__file__).parent
        hooks_src = doctrine_root / "hooks"
        if not hooks_src.is_dir():
            return

        hooks_dst = self.bundle_dir / "hooks"
        if hooks_dst.exists():
            shutil.rmtree(hooks_dst)
        shutil.copytree(hooks_src, hooks_dst)

    # ------------------------------------------------------------------
    # MCP companion (filesystem-presence only, conditional manifest pointer)
    # ------------------------------------------------------------------

    def _copy_mcp_if_present(self) -> None:
        """Stage ``.mcp.json`` into the bundle when a canonical source exists.

        FR-027 / plugin-manifest-codex-01: the Codex bundle carries an MCP
        companion "when applicable". There is no canonical MCP source shipped
        in doctrine today, so this is a guarded no-op in practice — but the
        contract is now explicit and testable: when a ``.mcp.json`` is present
        at the doctrine root it is copied into the bundle and
        :meth:`_generate_plugin_json` emits the ``mcpServers`` pointer; when it
        is absent nothing is written and no pointer appears.
        """
        import shutil  # noqa: PLC0415 — deferred to avoid top-level import cost

        try:
            import doctrine  # noqa: PLC0415
        except ImportError:
            return

        mcp_src = Path(doctrine.__file__).parent / _MCP_JSON_NAME
        if not mcp_src.is_file():
            return

        self.bundle_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(mcp_src, self.bundle_dir / _MCP_JSON_NAME)

    # ------------------------------------------------------------------
    # Marketplace catalog
    # ------------------------------------------------------------------

    def _generate_marketplace_json(self) -> None:
        """Write repo-local ``marketplace.json`` for Codex plugin install.

        The file is written to ``dist/spec-kitty-plugins/codex/marketplace.json``
        (the canonical output location per C-006).  A secondary copy is NOT
        written to ``.agents/plugins/marketplace.json`` — that would violate the
        C-006 output-dir constraint and pollute the project tree.

        Emits install instructions to stdout after writing.
        """
        marketplace: dict[str, object] = {
            "name": "spec-kitty-plugins",
            "interface": {"displayName": "Spec Kitty Plugins"},
            "plugins": [
                {
                    "name": "spec-kitty",
                    "source": {"source": "local", "path": "."},
                    "policy": {
                        "installation": "AVAILABLE",
                        "authentication": "ON_INSTALL",
                    },
                    "category": "Productivity",
                }
            ],
        }
        marketplace_path = self.bundle_dir / "marketplace.json"
        write_json(marketplace_path, marketplace)
        typer.echo(f"Codex marketplace.json written to {marketplace_path}")
        typer.echo(_INSTALL_HINT)


__all__ = ["CodexBundleProjector"]
