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

import json
from pathlib import Path

import typer

from ._builder import (
    BuildError,
    command_members,
    finish_build,
    get_cli_version,
)
from ..operations import ApplyConsent, AssessmentInputs, Diagnostic, OperationRoot, OwnerAssessment
from .model import BundleObservation, StagedFile
from .projection import (
    confined_output, json_bytes, observe_bundle_path, observe_tree,
    prepare_staging, read_observed_file, staging_root,
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
        assessment = self.prepare(ApplyConsent(automatic=True))
        finish_build(assessment)
        if skip_validate:
            typer.echo("Warning: Skipping Codex plugin validation (--skip-validate passed).", err=True)
        typer.echo(f"Codex marketplace.json written to {self.bundle_dir / 'marketplace.json'}")
        typer.echo(_INSTALL_HINT)
        return self.bundle_dir

    def prepare(self, consent: ApplyConsent = ApplyConsent()) -> OwnerAssessment:
        """Retain the entire CLI bundle without invoking any writer or validator."""
        root = staging_root(self.bundle_dir)
        directory = confined_output(self.bundle_dir, root)
        inputs = AssessmentInputs(root, consent=consent)
        try:
            version = get_cli_version()
            files, commands = command_members(directory / "skills", root)
            companions, observations, directories = self._companions(directory, root)
            manifest = self._manifest_payload(version, any(Path(f.path).name == _MCP_JSON_NAME for f in companions))
            files += companions + (
                StagedFile((directory / _MANIFEST_DIR / _MANIFEST_NAME).relative_to(root.path).as_posix(),
                           json_bytes(manifest, legacy=True), manifest=True),
                StagedFile((directory / "marketplace.json").relative_to(root.path).as_posix(),
                           json_bytes(self._marketplace_payload(), legacy=True), manifest=True),
            )
            return prepare_staging(inputs, files, (directory,), observations, suppliers=(commands,), version=version,
                                   supporting_dirs=directories)
        except (OSError, ValueError, BuildError) as exc:
            return OwnerAssessment("plugin_bundle", root, complete=False, consent=consent,
                                   diagnostics=(Diagnostic("bundle_input_invalid", "plugin_bundle", "error", str(exc)),))

    @staticmethod
    def _companions(directory: Path, root: OperationRoot) -> tuple[tuple[StagedFile, ...], tuple[BundleObservation, ...], tuple[tuple[str, int], ...]]:
        import charter.offering as offering

        source = Path(offering.__file__).parent.resolve()
        observations = [observe_bundle_path(source / _MCP_JSON_NAME), observe_bundle_path(source / "hooks", members=True)]
        files: list[StagedFile] = []
        directories: list[tuple[str, int]] = []
        for observation in observations:
            if observation.state.kind == "symlink":
                raise ValueError(f"Unsafe optional bundle source: {observation.path}")
        mcp = observations[0]
        if mcp.state.kind != "absent":
            if mcp.state.kind != "file":
                raise ValueError("MCP companion is not a regular file")
            content = read_observed_file(mcp)
            if not isinstance(json.loads(content), dict):
                raise ValueError("MCP companion must be a JSON object")
            files.append(StagedFile((directory / _MCP_JSON_NAME).relative_to(root.path).as_posix(), content, mcp.state.mode or 0o644))
        hooks = source / "hooks"
        if observations[1].state.kind != "absent":
            if observations[1].state.kind != "directory":
                raise ValueError("Hooks source is not a directory")
            for observed in observe_tree(hooks):
                observations.append(observed)
                if observed.state.kind == "directory":
                    assert observed.state.mode is not None
                    directories.append(((directory / "hooks" / observed.path.relative_to(hooks)).relative_to(root.path).as_posix(),
                                        observed.state.mode))
                if observed.state.kind == "file":
                    files.append(StagedFile((directory / "hooks" / observed.path.relative_to(hooks)).relative_to(root.path).as_posix(),
                                            read_observed_file(observed), observed.state.mode or 0o644))
        return tuple(files), tuple(observations), tuple(directories)

    # ------------------------------------------------------------------
    # Manifest generation
    # ------------------------------------------------------------------

    def _manifest_payload(self, version: str, has_mcp: bool) -> dict[str, object]:
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
        if has_mcp:
            manifest["mcpServers"] = _MCP_POINTER
        self._validate_manifest(manifest)
        return manifest

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
    # Marketplace catalog
    # ------------------------------------------------------------------

    @staticmethod
    def _marketplace_payload() -> dict[str, object]:
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
        return marketplace


__all__ = ["CodexBundleProjector"]
