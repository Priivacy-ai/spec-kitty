"""spec-kitty charter bundle - Typer sub-app for bundle validation.

This module is self-contained. WP03 will register it into the main
``charter`` CLI as a sub-command group. The canonical-root resolver is
sourced from ``charter.resolution.resolve_canonical_repo_root`` (WP02),
which uses ``git rev-parse --git-common-dir`` to return the main checkout
correctly under both plain checkouts and linked worktrees.

Implements the contract at
``kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/contracts/bundle-validate-cli.contract.md``.
"""
from __future__ import annotations

import json as _json
import subprocess
import sys
from pathlib import Path
from typing import Any

import typer
from pydantic import ValidationError
from rich.console import Console

from charter.bundle import CANONICAL_MANIFEST, CharterBundleManifest
from charter.resolution import (
    GitCommonDirUnavailableError,
    NotInsideRepositoryError,
    resolve_canonical_repo_root,
)
from charter.synthesizer.synthesize_pipeline import ProvenanceEntry
from doctrine.versioning import check_bundle_compatibility, get_bundle_schema_version
from ruamel.yaml import YAML as _YAML

app = typer.Typer(
    name="bundle",
    help="Charter bundle validation commands.",
    no_args_is_help=True,
)


@app.callback()
def _bundle_callback() -> None:
    """Charter bundle validation commands.

    A no-op callback whose presence forces Typer to treat ``app`` as a
    subcommand group even when only one command is registered. WP03 will
    register additional bundle subcommands alongside ``validate``.
    """
    return None


# Out-of-scope warning catalog. Keyed by path relative to canonical_root.
# These entries carry producer-specific rationale per the CLI contract; any
# other undeclared file under .kittify/charter/ falls through to a generic
# informational warning.
_OUT_OF_SCOPE_WARNINGS: dict[str, str] = {
    ".kittify/charter/references.yaml": (
        "File '.kittify/charter/references.yaml' is present but out of "
        "v1.0.0 manifest scope (produced by the compiler pipeline); "
        "leaving untouched."
    ),
    ".kittify/charter/context-state.json": (
        "File '.kittify/charter/context-state.json' is present but out of "
        "v1.0.0 manifest scope (runtime state written by "
        "build_charter_context); leaving untouched."
    ),
}


def _enumerate_out_of_scope_files(
    canonical_root: Path,
    manifest: CharterBundleManifest,
) -> tuple[list[str], list[str]]:
    """Return (out_of_scope_files, warnings) for files under .kittify/charter/.

    Every file under ``.kittify/charter/`` that is not declared in the
    manifest (neither tracked nor derived) is surfaced as an informational
    warning. The two canonical producer-specific messages for
    ``references.yaml`` and ``context-state.json`` are preserved; all other
    undeclared files fall through to a generic warning.
    """
    charter_dir = canonical_root / ".kittify" / "charter"
    if not charter_dir.is_dir():
        return [], []

    declared = {str(p) for p in manifest.tracked_files} | {
        str(p) for p in manifest.derived_files
    }

    out_of_scope: list[str] = []
    warnings: list[str] = []
    for entry in sorted(charter_dir.rglob("*")):
        if not entry.is_file():
            continue
        rel = entry.relative_to(canonical_root).as_posix()
        if rel in declared:
            continue
        out_of_scope.append(rel)
        specific = _OUT_OF_SCOPE_WARNINGS.get(rel)
        if specific is not None:
            warnings.append(specific)
        else:
            warnings.append(
                f"File '{rel}' is present but out of v1.0.0 manifest "
                "scope; leaving untouched."
            )
    return out_of_scope, warnings


def _read_gitignore_lines(canonical_root: Path) -> list[str]:
    path = canonical_root / ".gitignore"
    if not path.is_file():
        return []
    return [line.rstrip("\r\n") for line in path.read_text(encoding="utf-8").splitlines()]


def _is_git_tracked(canonical_root: Path, rel: str) -> bool:
    """Return True iff ``rel`` is a path tracked by git at ``canonical_root``.

    Uses ``git ls-files --error-unmatch`` so tracking is the sole signal: a
    file that exists on disk but was never ``git add``ed returns ``False``.
    If the dispatch itself fails (e.g. git unavailable, exit 128), we treat
    the file as not tracked — callers surface the mismatch via the normal
    missing-path path rather than crash.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", rel],
            cwd=str(canonical_root),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


def _classify_paths(
    canonical_root: Path,
    paths: list[Path],
    *,
    require_tracked: bool = False,
) -> tuple[list[str], list[str]]:
    """Return (present_rel, missing_rel) for the given manifest paths.

    When ``require_tracked`` is True, a path is considered "present" only
    when it both exists on disk *and* is tracked by git (``git ls-files``).
    Files that exist but are untracked are surfaced as missing — this
    matches the bundle-validate CLI contract which treats ``tracked_files``
    as a git-tracking assertion, not a filesystem assertion.
    """
    present: list[str] = []
    missing: list[str] = []
    for rel_path in paths:
        rel = rel_path.as_posix()
        absolute = canonical_root / rel_path
        if not absolute.exists():
            missing.append(rel)
            continue
        if require_tracked and not _is_git_tracked(canonical_root, rel):
            missing.append(rel)
            continue
        present.append(rel)
    return present, missing


def _classify_gitignore(
    canonical_root: Path,
    required: list[str],
) -> tuple[list[str], list[str]]:
    lines = set(_read_gitignore_lines(canonical_root))
    present: list[str] = []
    missing: list[str] = []
    for entry in required:
        if entry in lines:
            present.append(entry)
        else:
            missing.append(entry)
    return present, missing


def _render_human(report: dict[str, Any], console: Console) -> None:
    console.print("[bold]Charter bundle validation[/bold]")
    console.print(f"  Canonical root: {report['canonical_root']}")
    console.print(f"  Manifest schema: {report['manifest_schema_version']}")
    console.print("")

    console.print("  Tracked files:")
    for rel in report["tracked_files"]["expected"]:
        ok = rel in report["tracked_files"]["present"]
        marker = "[green][OK][/green]" if ok else "[red][MISSING][/red]"
        console.print(f"    {marker} {rel}")
    console.print("")

    console.print("  Derived files (v1.0.0 scope):")
    for rel in report["derived_files"]["expected"]:
        ok = rel in report["derived_files"]["present"]
        marker = "[green][OK][/green]" if ok else "[red][MISSING][/red]"
        console.print(f"    {marker} {rel}")
    console.print("")

    gi = report["gitignore"]
    missing_entries = gi["missing_entries"]
    if missing_entries:
        console.print("  Gitignore:")
        for entry in missing_entries:
            console.print(f"    [red][MISSING][/red] {entry}")
    else:
        console.print(
            f"  Gitignore:\n    [green][OK][/green] {len(gi['expected_entries'])} "
            "required entries present"
        )
    console.print("")

    if report["out_of_scope_files"]:
        console.print("  Out-of-scope files present (informational):")
        for rel in report["out_of_scope_files"]:
            console.print(f"    [yellow]{rel}[/yellow]")
        console.print("")

    if report["bundle_compliant"]:
        console.print("[green]Bundle is compliant (v1.0.0).[/green]")
    else:
        console.print("[red]Bundle is NOT compliant (v1.0.0).[/red]")


def _assert_bundle_compatible_bundle(charter_dir: Path, console: Console) -> None:
    """Check bundle compatibility and exit 1 with an upgrade prompt if needed.

    Only called when the charter directory is known to exist; never called
    for a fresh-synthesis path (where metadata.yaml is absent).
    """
    bundle_version = get_bundle_schema_version(charter_dir)
    result = check_bundle_compatibility(bundle_version)
    if not result.is_compatible:
        console.print(f"[red]Error:[/red] {result.message}")
        raise typer.Exit(code=1)


@app.command("validate")
def validate(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON to stdout instead of a human-readable report.",
    ),
) -> None:
    """Validate the charter bundle against CharterBundleManifest v1.0.0."""
    console = Console()
    err_console = Console(stderr=True)

    try:
        canonical_root = resolve_canonical_repo_root(Path.cwd())
    except (NotInsideRepositoryError, GitCommonDirUnavailableError) as exc:
        # Exit 2: resolver failure. Message on stderr per contract.
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2)

    # FR-009: Block reads of incompatible bundles before any structure checks.
    charter_dir = canonical_root / ".kittify" / "charter"
    if (charter_dir / "metadata.yaml").exists():
        _assert_bundle_compatible_bundle(charter_dir, console)

    manifest = CANONICAL_MANIFEST

    tracked_present, tracked_missing = _classify_paths(
        canonical_root, list(manifest.tracked_files), require_tracked=True
    )
    derived_present, derived_missing = _classify_paths(
        canonical_root, list(manifest.derived_files)
    )
    gitignore_present, gitignore_missing = _classify_gitignore(
        canonical_root, list(manifest.gitignore_required_entries)
    )
    out_of_scope, warnings = _enumerate_out_of_scope_files(canonical_root, manifest)

    # Fresh-clone state: charter.md present, all derived absent -> acceptable.
    fresh_clone = (
        not tracked_missing
        and len(derived_missing) == len(manifest.derived_files)
    )

    derived_is_compliant = fresh_clone or not derived_missing
    bundle_compliant = (
        not tracked_missing
        and derived_is_compliant
        and not gitignore_missing
    )

    report: dict[str, Any] = {
        "result": "success" if bundle_compliant else "failure",
        "canonical_root": str(canonical_root),
        "manifest_schema_version": manifest.schema_version,
        "bundle_compliant": bundle_compliant,
        "tracked_files": {
            "expected": [p.as_posix() for p in manifest.tracked_files],
            "present": tracked_present,
            "missing": tracked_missing,
        },
        "derived_files": {
            "expected": [p.as_posix() for p in manifest.derived_files],
            "present": derived_present,
            "missing": [] if fresh_clone else derived_missing,
        },
        "gitignore": {
            "expected_entries": list(manifest.gitignore_required_entries),
            "present_entries": gitignore_present,
            "missing_entries": gitignore_missing,
        },
        "out_of_scope_files": out_of_scope,
        "warnings": warnings,
    }

    # FR-006 / FR-007: Validate provenance sidecar content.
    # Parse each sidecar as ProvenanceEntry; fail closed on validation errors.
    _yaml_loader = _YAML(typ="safe")
    provenance_dir = canonical_root / ".kittify" / "charter" / "provenance"
    sidecar_errors: list[str] = []
    if provenance_dir.exists():
        for sidecar_path in sorted(provenance_dir.glob("*.yaml")):
            raw = _yaml_loader.load(sidecar_path)
            if isinstance(raw, dict):
                try:
                    ProvenanceEntry(**raw)
                except ValidationError as e:
                    sidecar_errors.append(f"{sidecar_path.name}: {e}")

    # FR-007: Every artifact listed in synthesis-manifest.yaml must have a
    # provenance sidecar file on disk.  Missing sidecars fail closed.
    manifest_yaml_path = canonical_root / ".kittify" / "charter" / "synthesis-manifest.yaml"
    if manifest_yaml_path.exists():
        raw_manifest = _yaml_loader.load(manifest_yaml_path)
        if isinstance(raw_manifest, dict):
            for artifact in raw_manifest.get("artifacts", []) or []:
                if not isinstance(artifact, dict):
                    continue
                prov_rel = artifact.get("provenance_path")
                if not prov_rel:
                    continue
                if not (canonical_root / prov_rel).exists():
                    slug = artifact.get("slug", "?")
                    sidecar_errors.append(
                        f"Missing provenance sidecar for artifact '{slug}': {prov_rel}"
                    )

    if sidecar_errors:
        for msg in sidecar_errors:
            console.print(f"[red]Provenance validation error:[/red] {msg}")
        raise typer.Exit(code=1)

    if json_output:
        # Use plain stdout for JSON; the contract requires the exact JSON
        # shape to be parseable without Rich markup.
        sys.stdout.write(_json.dumps(report, indent=2) + "\n")
    else:
        _render_human(report, console)

    raise typer.Exit(code=0 if bundle_compliant else 1)
