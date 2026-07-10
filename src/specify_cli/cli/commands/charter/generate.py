"""``spec-kitty charter generate`` command + git-auto-track helpers (WP06 split)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import typer

from specify_cli.task_utils import TaskCliError

from specify_cli.cli.commands.charter._app import charter_app, console
from specify_cli.cli.commands.charter._common import _emit_error, _interview_path

# Test-patch shim: see ``synthesize.py`` for the rationale. ``find_repo_root``
# and ``default_interview`` are looked up on the package module at call time so
# legacy ``patch("…charter.X", …)`` fixtures still apply across the split.
import specify_cli.cli.commands.charter as _charter_pkg

__all__ = ["generate"]


def _build_doctrine_service_with_org_layer(repo_root: Path) -> Any:
    """Return an activation-filtered ``DoctrineService`` for charter generation.

    Constructs a :class:`doctrine.service.DoctrineService` rooted at
    built-in doctrine + project + configured org packs, then wraps it in
    :class:`charter.resolver.DoctrineService` with the current
    :class:`~charter.pack_context.PackContext`.  The wrapper applies
    per-kind activation filters (Pattern B for paradigms/procedures,
    Pattern C for agent_profiles).

    Org-layer roots are resolved from ``.kittify/config.yaml`` via
    :func:`specify_cli.doctrine.config.resolve_org_roots`.  Packs missing
    from disk are silently dropped (a fresh checkout that has not yet run
    ``spec-kitty doctrine fetch`` must not fail charter generation).

    Architectural note: this helper lives in ``specify_cli`` because it
    depends on the ``specify_cli.doctrine.config`` reader and
    ``charter.invocation_context.ProjectContext``, which the ``charter``
    layer is forbidden from importing.
    """
    from charter._doctrine_paths import resolve_project_root
    from charter.catalog import resolve_doctrine_root
    from charter.resolver import DoctrineService as ActivationDoctrineService
    from doctrine.service import DoctrineService

    from specify_cli.doctrine.config import resolve_org_roots

    doctrine_root = resolve_doctrine_root()
    project_root = resolve_project_root(repo_root) if repo_root is not None else None
    org_roots = [p for p in resolve_org_roots(repo_root) if p.exists()]

    inner = DoctrineService(
        built_in_root=doctrine_root,
        project_root=project_root,
        org_roots=org_roots,
    )

    # Obtain pack_context for activation filtering (Pattern B + C).
    # Degrades silently when charter.invocation_context is not yet available
    # (WP03 dependency) — returns unfiltered service in that case.
    pack_context = None
    if repo_root is not None:
        try:
            from charter.invocation_context import ProjectContext  # noqa: PLC0415

            ctx = ProjectContext.from_repo(repo_root)
            pack_context = ctx.require_pack_context()
        except Exception:  # noqa: BLE001 — activation filter is best-effort; degraded to unfiltered
            pass

    return ActivationDoctrineService(inner, pack_context=pack_context)


def _is_inside_git_worktree(repo_root: Path) -> bool:
    """Return True iff ``repo_root`` is inside a git working tree.

    Uses ``git rev-parse --is-inside-work-tree``. Returns False on any
    subprocess error (git missing, exit non-zero, etc.) — callers should
    treat both "not a repo" and "git unavailable" as fail-fast cases since
    the downstream auto-track step requires a working git invocation either
    way.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def _stage_charter_files(repo_root: Path, files: list[Path]) -> None:
    """Stage ``files`` via ``git add --force`` for bundle validation.

    Issue #841: ``charter generate`` must auto-track the produced ``charter.md``
    (and any other tracked-files manifest entries) so the immediately-following
    ``charter bundle validate`` succeeds without an operator ``git add``. We
    stage (not commit) — staging is what ``git ls-files`` reports as tracked,
    which is the signal ``charter bundle validate`` keys on.

    The slash-command flow commits generated files with ``spec-kitty
    safe-commit``; pre-staging keeps ``bundle validate`` green and safe-commit
    now treats requested pre-staged files as commit inputs, not unrelated
    operator staging.

    Files are passed as repo-relative ``Path``s. ``--force`` is used so that an
    operator who has gitignored ``charter.md`` for any reason still gets the
    auto-track contract honored — this is consistent with the bundle manifest
    declaring ``charter.md`` as a tracked file.
    """
    for file_path in files:
        if not (repo_root / file_path).exists():
            continue
        rel = file_path.as_posix()
        result = subprocess.run(
            ["git", "add", "--force", "--", rel],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(
                f"Failed to stage charter file {rel}. "
                f"{detail or 'git add returned a non-zero exit code.'}"
            )


def _ensure_gitignore_entries(repo_root: Path, required: list[str]) -> None:
    """Append any missing ``required`` entries to ``.gitignore``.

    Issue #841 parity: ``charter bundle validate`` requires the project's
    ``.gitignore`` to contain entries for the derived charter artifacts
    (so they are not accidentally committed). After ``charter generate``
    materializes the derived files, we make sure ``.gitignore`` is also
    primed so the very next ``bundle validate`` reports compliance without
    operator hand-edits — the same parity contract that motivates auto-track.

    The function is additive-only: existing entries are preserved, and any
    ``required`` entry already on disk is left untouched. A trailing newline
    is normalized when entries are appended.
    """
    gitignore_path = repo_root / ".gitignore"
    existing_lines: list[str] = []
    if gitignore_path.is_file():
        existing_lines = gitignore_path.read_text(encoding="utf-8").splitlines()

    existing_set = {line.rstrip("\r") for line in existing_lines}
    missing = [entry for entry in required if entry not in existing_set]
    if not missing:
        return

    # Build the new content. Preserve existing content; append a managed
    # block of missing entries with a clear header comment.
    new_lines: list[str] = list(existing_lines)
    if new_lines and new_lines[-1] != "":
        new_lines.append("")
    new_lines.append("# Spec Kitty: charter bundle derived files (auto-added by `charter generate`)")
    new_lines.extend(missing)

    gitignore_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _load_interview_for_generate(
    *,
    repo_root: Path,
    answers_path: Path,
    from_interview: bool,
    resolved_mission_type: str | None,
    profile: str,
) -> tuple[Any, str, str]:
    """Resolve interview payload, source label, and mission for generation."""
    from charter.interview import read_interview_answers

    interview_data = read_interview_answers(answers_path) if from_interview else None
    if from_interview and interview_data is None:
        raise ValueError(
            "No charter interview answers found at "
            f"{answers_path.relative_to(repo_root)}. "
            "Run `/spec-kitty.charter` so the agent can capture guidance, "
            "run `spec-kitty charter interview --defaults` for a canned bootstrap, "
            "or pass `--no-from-interview` to generate from defaults explicitly."
        )

    if interview_data is None:
        resolved_mission = resolved_mission_type or "software-dev"
        interview_data = _charter_pkg.default_interview(
            mission=resolved_mission,
            profile=profile.strip().lower(),
        )
        return interview_data, "defaults", resolved_mission

    return interview_data, "interview", resolved_mission_type or interview_data.mission


@charter_app.command()
def generate(
    mission_type: str | None = typer.Option(None, "--mission-type", help="Mission type for template-set defaults"),
    mission: str | None = typer.Option(None, "--mission", hidden=True, help="(deprecated) Use --mission-type"),
    template_set: str | None = typer.Option(
        None,
        "--template-set",
        help="Override doctrine template set (must exist in packaged doctrine missions)",
    ),
    from_interview: bool = typer.Option(
        True, "--from-interview/--no-from-interview", help="Load interview answers if present"
    ),
    profile: str = typer.Option("minimal", "--profile", help="Default profile when no interview is available"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing charter bundle"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Generate charter bundle from interview answers + doctrine references.

    Behavior contract (issue #841 / WP06 T029-T030):

    - On success in a git working tree, the produced ``.kittify/charter/charter.md``
      is auto-staged via ``git add`` so a subsequent ``charter bundle validate``
      finds it tracked without any operator ``git add`` between the two
      commands. Staging (not committing) matches the parity contract — the
      ``bundle validate`` tracked-files check keys on ``git ls-files``.
    - When the cwd is not inside a git working tree, ``generate`` exits
      non-zero before any side effect with an actionable error message that
      names the remediation (``git init``).
    - When ``.kittify/charter/charter.md`` is a symlink, ``generate`` exits
      non-zero before interview/default loading, compilation, sync,
      gitignore updates, or staging. Update the symlink target directly or
      replace it with a regular runtime charter.
    """
    from charter.compiler import compile_charter, write_compiled_charter
    from charter.pack_context import PackContext
    from charter.sync import sync as sync_charter

    try:
        repo_root = _charter_pkg.find_repo_root()

        # T030 (#841 fail-fast): verify we are inside a git working tree
        # BEFORE writing any artifact. Auto-tracking on success requires
        # git, and producing artifacts that bundle validate cannot accept
        # is exactly the silent-inconsistency bug #841 closes.
        if not _is_inside_git_worktree(repo_root):
            _emit_error(
                console,
                json_output=json_output,
                message=(
                    "charter generate requires a git repository. "
                    "Initialize one with `git init` (so the produced charter.md can be "
                    "auto-tracked and accepted by `charter bundle validate`)."
                ),
            )
            raise typer.Exit(code=1)
        charter_dir = repo_root / ".kittify" / "charter"
        charter_path = charter_dir / "charter.md"
        if charter_path.is_symlink():
            _emit_error(
                console,
                json_output=json_output,
                message=(
                    f"Refusing to overwrite symlinked charter at {charter_path}. "
                    "Remove the symlink or update the symlink target directly."
                ),
            )
            raise typer.Exit(code=1)

        answers_path = _interview_path(repo_root)
        resolved_mission_type = None
        if mission_type is not None or mission is not None:
            from specify_cli.cli.selector_resolution import resolve_selector

            resolved = resolve_selector(
                canonical_value=mission_type,
                canonical_flag="--mission-type",
                alias_value=mission,
                alias_flag="--mission",
                suppress_env_var="SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION",
                command_hint="--mission-type <name>",
            )
            resolved_mission_type = resolved.canonical_value

        interview_data, interview_source, resolved_mission = _load_interview_for_generate(
            repo_root=repo_root,
            answers_path=answers_path,
            from_interview=from_interview,
            resolved_mission_type=resolved_mission_type,
            profile=profile,
        )

        # FR-001/FR-002 (WP02): `.kittify/config.yaml` `activated_*` is the
        # activation authority the compiled reference set derives from --
        # built and passed explicitly (rather than left for `compile_charter`
        # to construct implicitly from `repo_root`) so the config-sourced
        # derivation is visible at the call site, not just an internal
        # default. `interview_data` still flows through for the interview
        # record (`_user_profile_reference`) and non-doctrine answers
        # (testing/quality/deployment prose); it is no longer read for
        # activation selection.
        compiled = compile_charter(
            mission=resolved_mission,
            interview=interview_data,
            template_set=template_set,
            repo_root=repo_root,
            doctrine_service=_build_doctrine_service_with_org_layer(repo_root),
            pack_context=PackContext.from_config(repo_root),
        )
        bundle_result = write_compiled_charter(
            charter_dir,
            compiled,
            force=force,
            repo_root=repo_root,
        )
        if interview_source == "defaults":
            # Legacy CLI contract: default generation materializes an empty
            # library/ directory for older consumers. Interview-driven flows
            # keep the newer no-materialization behavior.
            (charter_dir / "library").mkdir(exist_ok=True)

        charter_path = charter_dir / "charter.md"
        sync_result = sync_charter(charter_path, charter_dir, force=True)

        if sync_result.error:
            raise RuntimeError(sync_result.error)

        diagnostics = [*compiled.diagnostics, *sync_result.warnings]

        files_written = list(bundle_result.files_written)
        for file_name in sync_result.files_written:
            if file_name not in files_written:
                files_written.append(file_name)

        # T029 (#841 auto-track): stage every file that bundle validate
        # asserts is git-tracked AND ensure .gitignore contains the required
        # entries for derived files. CANONICAL_MANIFEST is the single source
        # of truth for both sets — we read both fields here so the
        # auto-track contract never drifts from what bundle validate checks.
        from charter.bundle import CANONICAL_MANIFEST

        _ensure_gitignore_entries(
            repo_root, list(CANONICAL_MANIFEST.gitignore_required_entries)
        )
        commit_input_files = [
            *list(CANONICAL_MANIFEST.tracked_files),
            Path(".kittify/charter/references.yaml"),
            Path(".gitignore"),
        ]
        _stage_charter_files(repo_root, commit_input_files)

        if json_output:
            local_support_files = [
                reference.source_path
                for reference in compiled.references
                if reference.kind == "local_support"
            ]
            print(
                json.dumps(
                    {
                        "result": "success",
                        "success": True,
                        "charter_path": str(charter_path.relative_to(repo_root)),
                        "interview_source": interview_source,
                        "mission": compiled.mission,
                        "template_set": compiled.template_set,
                        "selected_paradigms": compiled.selected_paradigms,
                        "selected_directives": compiled.selected_directives,
                        "available_tools": compiled.available_tools,
                        "references_count": len(compiled.references),
                        "library_files": local_support_files,
                        "files_written": files_written,
                        "diagnostics": diagnostics,
                    },
                    indent=2,
                )
            )
            return

        console.print("[green]Charter generated and synced[/green]")
        console.print(f"Charter: {charter_path.relative_to(repo_root)}")
        console.print(f"Mission: {compiled.mission}")
        console.print(f"Template set: {compiled.template_set}")
        if diagnostics:
            console.print("Diagnostics:")
            for line in diagnostics:
                console.print(f"  - {line}")
        console.print("Files written:")
        for filename in files_written:
            console.print(f"  ✓ {filename}")

    except typer.Exit:
        # Pass-through: caller already emitted an actionable message
        # (e.g. T030 fail-fast for non-git environments).
        raise
    except (FileExistsError, TaskCliError, ValueError, RuntimeError) as e:
        _emit_error(console, json_output=json_output, message=str(e))
        raise typer.Exit(code=1) from e
    except Exception as e:
        _emit_error(console, json_output=json_output, message=str(e), unexpected=True)
        raise typer.Exit(code=1) from e
