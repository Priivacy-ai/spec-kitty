"""``spec-kitty charter synthesize`` command (WP06 per-subcommand split).

Synthesis-pipeline helpers live in
:mod:`specify_cli.cli.commands.charter._synthesis`. The body here stays close
to its original layout so the FR-001 strict-JSON envelope contract is
trivially diffable against the legacy ``charter.py``.
"""
from __future__ import annotations

import json
from typing import Any

import typer
from rich.console import Console

from specify_cli.diagnostics import mark_invocation_succeeded
from specify_cli.task_utils import TaskCliError

from specify_cli.cli.commands.charter._app import charter_app, console
# Helpers that tests never patch (``_has_generated_artifacts``,
# ``_materialize_fresh_doctrine``, ``_planned_fresh_doctrine_paths``) can be
# imported directly. The patchable helpers
# (``_build_synthesis_request``, ``_collect_evidence_result``,
# ``_load_written_artifacts_from_manifest``,
# ``_run_synthesis_dry_run_with_artifacts``) are routed via ``_charter_pkg``
# below.
from specify_cli.cli.commands.charter._synthesis import (
    _has_generated_artifacts,
    _materialize_fresh_doctrine,
    _planned_fresh_doctrine_paths,
)

# NOTE: ``find_repo_root`` and the patchable synthesis helpers are intentionally
# looked up via the package module at call time (not bound at import time).
# Legacy tests patch ``specify_cli.cli.commands.charter.<name>`` and expect the
# patched value to be visible from this command body. Importing the package as
# a module reference and accessing attributes at call time preserves that
# contract across the WP06 split.
import specify_cli.cli.commands.charter as _charter_pkg

__all__ = ["charter_synthesize"]


@charter_app.command("synthesize")
def charter_synthesize(  # noqa: C901
    # WP02 / FR-001..FR-005: this command body is the strict-JSON
    # envelope-emit point. Branches are deliberate: fresh-seed (dry-run +
    # real), evidence-dry-run, dry-run, real-run, and four typed
    # exception envelopes. Splitting them into helper functions would
    # obscure the FR-001 stdout contract — every branch must end with
    # exactly one ``json.dumps`` call when ``--json`` is set.
    adapter: str = typer.Option(
        "generated",
        "--adapter",
        help=(
            "Adapter to use. 'generated' (default) validates agent-authored YAML under "
            ".kittify/charter/generated/. 'fixture' is offline/testing only."
        ),
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Stage and validate artifacts but do not promote to live tree.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    skip_code_evidence: bool = typer.Option(
        False,
        "--skip-code-evidence",
        help="Skip code-reading evidence collection.",
    ),
    skip_corpus: bool = typer.Option(
        False,
        "--skip-corpus",
        help="Skip best-practice corpus loading.",
    ),
    dry_run_evidence: bool = typer.Option(
        False,
        "--dry-run-evidence",
        help="Print evidence summary and exit without running synthesis.",
    ),
) -> None:
    """Validate and promote agent-generated project-local doctrine artifacts.

    Reads the charter interview answers, resolves synthesis targets from the
    DRG + doctrine, and writes all artifacts to ``.kittify/doctrine/``.

    Doctrine generation is performed by the LLM harness (Claude Code, Codex,
    Cursor, etc.) via the spec-kitty-charter-doctrine skill. This command
    validates and promotes the artifacts the agent has written.

    Fresh-project behavior (issue #839 / WP06 T031-T033)
    ----------------------------------------------------
    On a fresh project where ``.kittify/charter/generated/`` is missing or
    empty (i.e. the LLM harness has not yet written agent artifacts), this
    command short-circuits the adapter pipeline and materializes the
    **minimal artifact set** the runtime requires:

    1. ``.kittify/doctrine/`` — directory marker. ``DoctrineService``'s
       project-root resolver (``src/charter/_doctrine_paths.py``) is a
       presence-only check; an empty directory is a valid project layer.
    2. ``.kittify/doctrine/PROVENANCE.md`` — human-readable record of the
       fresh-project seed path, citing #839.

    The runtime falls back to the built-in doctrine (``src/doctrine/``) for
    all artifact lookups until the harness writes per-target YAML and the
    operator re-runs ``synthesize`` (which then takes the normal adapter
    path). The fresh-project path is **idempotent**: re-running produces
    bytewise-identical output (T033). Charter prerequisites are still
    enforced — ``charter.md`` must exist (else ``TaskCliError`` is raised
    via ``_build_synthesis_request``).

    Examples
    --------
    Validate + promote generated artifacts written by the harness::

        spec-kitty charter synthesize

    Validate + promote with fixture adapter (offline/testing)::

        spec-kitty charter synthesize --adapter fixture

    Dry-run (stage + validate, no promote)::

        spec-kitty charter synthesize --dry-run
    """
    from charter.synthesizer.errors import NeutralityGateViolation, SynthesisError, render_error_panel

    err_console = Console(stderr=True)

    # FR-001: warnings collected so far. Initialised here (outside the
    # try/except) so failure-branch envelopes can carry the same
    # warnings the success branch would have surfaced — i.e. an
    # evidence warning followed by a synthesis error still ships its
    # warning inside the envelope rather than losing it.
    warnings_collected: list[str] = []

    try:
        repo_root = _charter_pkg.find_repo_root()

        # T032 (#839 fresh-project): When the operator runs synthesize on a
        # fresh project (post `charter generate` but before the LLM harness
        # has written YAMLs under .kittify/charter/generated/), the production
        # adapter has nothing to load and would raise GeneratedArtifactMissingError.
        # The intercept below takes the bounded fresh-project path: it requires
        # charter.md to exist (the upstream chain produced it) AND no
        # agent-authored YAMLs to be present. When both signals fire, we
        # materialize the minimal .kittify/doctrine/ artifact set documented in
        # T031 so the runtime can advance via the built-in doctrine fallback.
        #
        # When charter.md is absent we fall through to the existing pipeline so
        # callers that mock charter.synthesizer.synthesize (legacy unit tests)
        # keep their established behaviour. Real operators always reach this
        # path AFTER `charter generate`, so charter.md is reliably present in
        # the realistic fresh-project flow.
        charter_md = repo_root / ".kittify" / "charter" / "charter.md"
        is_fresh_project_synthesize = (
            adapter == "generated"
            and not _has_generated_artifacts(repo_root)
            and not dry_run_evidence
            and charter_md.is_file()
        )

        if is_fresh_project_synthesize:
            # FR-002 / FR-003 / FR-005: fresh-project seed mode emits the
            # strict four-field envelope. ``written_artifacts`` is built from
            # the already-known minimal seed file list (PROVENANCE.md). No
            # adapter actually ran, so ``adapter.id`` is the documented
            # internal "fresh-seed" sentinel — non-empty per AdapterRef
            # invariant — and ``adapter.version`` is the running CLI version.
            # ``warnings`` is intentionally empty: evidence collection has
            # not been triggered on this branch.
            from importlib.metadata import version as _pkg_version
            try:
                _seed_version = _pkg_version("spec-kitty-cli")
            except Exception:
                _seed_version = "unknown"

            if dry_run:
                planned = _planned_fresh_doctrine_paths(repo_root)
                fresh_written_artifacts: list[dict[str, Any]] = [
                    {
                        "path": p,
                        "kind": "seed",
                        "slug": "provenance",
                        "artifact_id": None,
                    }
                    for p in planned
                ]
                if json_output:
                    print(json.dumps({
                        # FR-002 contracted fields:
                        "result": "dry_run",
                        "adapter": {"id": "fresh-seed", "version": _seed_version},
                        "written_artifacts": fresh_written_artifacts,
                        "warnings": [],
                        # Compatibility / fresh-seed identification fields:
                        "success": True,
                        "mode": "fresh_project_seed_dry_run",
                        "files_planned": planned,
                        "note": (
                            "Fresh project + --dry-run: would materialize "
                            "minimal .kittify/doctrine/ (no files written). "
                            "See issue #839."
                        ),
                    }, indent=2, sort_keys=True))
                    mark_invocation_succeeded()
                    return
                console.print(
                    "[yellow]Charter synthesis (fresh project, dry-run)[/yellow]: "
                    "would materialize minimal .kittify/doctrine/ (no files written)."
                )
                for f in planned:
                    console.print(f"  • {f}")
                return

            written = _materialize_fresh_doctrine(repo_root)
            fresh_written_artifacts = [
                {
                    "path": p,
                    "kind": "seed",
                    "slug": "provenance",
                    "artifact_id": None,
                }
                for p in written
            ]

            if json_output:
                print(json.dumps({
                    # FR-002 contracted fields:
                    "result": "success",
                    "adapter": {"id": "fresh-seed", "version": _seed_version},
                    "written_artifacts": fresh_written_artifacts,
                    "warnings": [],
                    # Compatibility / fresh-seed identification fields:
                    "success": True,
                    "mode": "fresh_project_seed",
                    "files_written": written,
                    "note": (
                        "Fresh project: no agent-authored YAML under "
                        ".kittify/charter/generated/. Materialized minimal "
                        ".kittify/doctrine/ so the runtime can advance "
                        "(see issue #839)."
                    ),
                }, indent=2, sort_keys=True))
                mark_invocation_succeeded()
                return

            console.print(
                "[green]Charter synthesis (fresh project)[/green]: minimal "
                ".kittify/doctrine/ materialized."
            )
            for f in written:
                console.print(f"  ✓ {f}")
            return

        # FR-001: when --json is set, evidence warnings MUST live inside the
        # envelope's ``warnings`` array, NOT on stdout. The previous
        # implementation called ``console.print`` here unconditionally,
        # which broke ``json.loads(stdout)`` for any run that produced
        # warnings (the bug behind FR-001 / AC-001).
        evidence_result = _charter_pkg._collect_evidence_result(
            repo_root,
            skip_code_evidence=skip_code_evidence,
            skip_corpus=skip_corpus,
        )
        warnings_collected.extend(str(w) for w in evidence_result.warnings)
        if not json_output:
            for warning in warnings_collected:
                console.print(f"[yellow]⚠ {warning}[/yellow]")

        if dry_run_evidence:
            bundle = evidence_result.bundle
            if json_output:
                # FR-001 / FR-002: evidence dry-run also emits the strict
                # envelope. ``written_artifacts`` is empty because no
                # synthesis ran; warnings live in the ``warnings`` array.
                print(json.dumps({
                    # Contracted fields (FR-002):
                    "result": "success",
                    "adapter": {"id": adapter, "version": "evidence-dry-run"},
                    "written_artifacts": [],
                    "warnings": warnings_collected,
                    # Compatibility / mode-identification fields:
                    "mode": "evidence_dry_run",
                    "evidence": {
                        "code_signals": (
                            {
                                "stack_id": bundle.code_signals.stack_id,
                                "primary_language": bundle.code_signals.primary_language,
                                "representative_files_count": len(
                                    bundle.code_signals.representative_files
                                ),
                            }
                            if bundle.code_signals
                            else None
                        ),
                        "url_list_count": len(bundle.url_list),
                        "corpus": (
                            {
                                "snapshot_id": bundle.corpus_snapshot.snapshot_id,
                                "entries_count": len(bundle.corpus_snapshot.entries),
                            }
                            if bundle.corpus_snapshot
                            else None
                        ),
                    },
                }, indent=2, sort_keys=True))
                mark_invocation_succeeded()
                raise typer.Exit(0)

            console.print("[bold]Evidence dry-run summary:[/bold]")
            if bundle.code_signals:
                cs = bundle.code_signals
                console.print(f"  Code signals: stack={cs.stack_id}, lang={cs.primary_language}")
                console.print(f"  Representative files: {len(cs.representative_files)} found")
            else:
                console.print("  Code signals: none (skipped or not detected)")
            console.print(f"  URL list: {len(bundle.url_list)} URL(s) configured")
            if bundle.corpus_snapshot:
                console.print(
                    f"  Corpus: {bundle.corpus_snapshot.snapshot_id} "
                    f"({len(bundle.corpus_snapshot.entries)} entries)"
                )
            else:
                console.print("  Corpus: none")
            for w in warnings_collected:
                console.print(f"  [yellow]Warning: {w}[/yellow]")
            raise typer.Exit(0)

        request, syn_adapter = _charter_pkg._build_synthesis_request(repo_root, adapter, evidence=evidence_result.bundle)

        if dry_run:
            # FR-003 / FR-004: ``written_artifacts`` for dry-run comes from
            # the SAME ``compute_written_artifacts`` helper the real-run
            # path uses. Paths are byte-equal to what a non-dry-run with the
            # same SynthesisRequest would write (the parity guarantee that
            # tests/charter/synthesizer/test_synthesize_path_parity.py
            # locks in).
            staged_files, written_artifacts_dr = _charter_pkg._run_synthesis_dry_run_with_artifacts(
                request, syn_adapter, repo_root
            )

            if json_output:
                print(json.dumps({
                    # Contracted fields (FR-002):
                    "result": "dry_run",
                    "adapter": {
                        "id": getattr(syn_adapter, "id", adapter),
                        "version": getattr(syn_adapter, "version", "unknown"),
                    },
                    "written_artifacts": written_artifacts_dr,
                    "warnings": warnings_collected,
                    # Legacy compatibility fields (data-model.md §E-1):
                    "staged_artifacts": staged_files,
                    "artifact_count": len(staged_files),
                    "validated": True,
                }, indent=2, sort_keys=True))
                mark_invocation_succeeded()
                return

            console.print("[yellow]Dry-run:[/yellow] synthesis staged and validated (not promoted)")
            for f in staged_files:
                console.print(f"  [dim]staged:[/dim] {f}")
            return

        from charter.synthesizer import synthesize

        result = synthesize(request, adapter=syn_adapter, repo_root=repo_root)

        # FR-003: ``written_artifacts`` is sourced from the on-disk
        # synthesis manifest the write pipeline wrote last (KD-2 commit
        # marker). Each entry's ``artifact_id`` is read from the matching
        # provenance sidecar — never reconstructed by parsing the filename.
        # When ``synthesize()`` is mocked out by tests (the manifest is
        # never written), this returns ``[]`` and the four contracted
        # fields are still emitted (INV-E-2: empty list != absent field).
        written_artifacts_real = _charter_pkg._load_written_artifacts_from_manifest(repo_root)

        if json_output:
            print(json.dumps({
                # Contracted fields (FR-002):
                "result": "success",
                "adapter": {
                    "id": result.effective_adapter_id,
                    "version": result.effective_adapter_version,
                },
                "written_artifacts": written_artifacts_real,
                "warnings": warnings_collected,
                # Legacy compatibility fields (data-model.md §E-1):
                "target_kind": result.target_kind,
                "target_slug": result.target_slug,
                "inputs_hash": result.inputs_hash,
                "adapter_id": result.effective_adapter_id,
                "adapter_version": result.effective_adapter_version,
            }, indent=2, sort_keys=True))
            mark_invocation_succeeded()
            return

        console.print("[green]Charter synthesis complete[/green]")
        console.print(f"Primary artifact: {result.target_kind}:{result.target_slug}")
        console.print(f"Adapter: {result.effective_adapter_id} v{result.effective_adapter_version}")

    except typer.Exit:
        raise
    except NeutralityGateViolation as e:
        # Stderr-only (R-001): human-readable progress remains permitted on
        # stderr in --json mode. The error panel never reaches stdout.
        render_error_panel(e, err_console)
        err_console.print(
            f"\n[yellow]Staging directory preserved at:[/yellow] {e.staging_dir}\n"
            "Inspect the staged artifacts, adjust the synthesis prompt or scope, and retry."
        )
        if json_output:
            # FR-001: even in failure mode, stdout MUST contain exactly one
            # JSON document. The error message is appended to whatever
            # warnings were already collected so callers reading only
            # stdout still see both.
            print(json.dumps({
                "result": "failure",
                "adapter": {"id": adapter, "version": "unknown"},
                "written_artifacts": [],
                "warnings": warnings_collected + [f"NeutralityGateViolation: {e}"],
            }, indent=2, sort_keys=True))
        raise typer.Exit(code=1) from e
    except SynthesisError as e:
        from charter.synthesizer.errors import GeneratedArtifactMissingError as _GAME

        render_error_panel(e, err_console)
        if isinstance(e, _GAME):
            # Actionable remediation: the adapter found no agent-authored
            # YAML, which usually means `charter generate` was never run.
            _charter_hint = (
                "Charter prerequisite missing: no generated charter artifacts found. "
                "Run `spec-kitty charter generate` (or `charter interview` first) "
                "to produce the artifacts that synthesis needs."
            )
            if json_output:
                print(json.dumps({
                    "result": "failure",
                    "adapter": {"id": adapter, "version": "unknown"},
                    "written_artifacts": [],
                    "warnings": warnings_collected + [_charter_hint],
                }, indent=2, sort_keys=True))
            else:
                console.print(f"[red]Error:[/red] {_charter_hint}")
            raise typer.Exit(code=1) from e

        if json_output:
            print(json.dumps({
                "result": "failure",
                "adapter": {"id": adapter, "version": "unknown"},
                "written_artifacts": [],
                "warnings": warnings_collected + [f"SynthesisError: {e}"],
            }, indent=2, sort_keys=True))
        raise typer.Exit(code=1) from e
    except TaskCliError as e:
        if json_output:
            print(json.dumps({
                "result": "failure",
                "adapter": {"id": adapter, "version": "unknown"},
                "written_artifacts": [],
                "warnings": warnings_collected + [str(e)],
            }, indent=2, sort_keys=True))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        if json_output:
            print(json.dumps({
                "result": "failure",
                "adapter": {"id": adapter, "version": "unknown"},
                "written_artifacts": [],
                "warnings": warnings_collected + [f"Unexpected error: {e}"],
            }, indent=2, sort_keys=True))
        else:
            console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1) from e
