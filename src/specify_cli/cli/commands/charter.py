"""Charter management commands."""

from __future__ import annotations

import contextlib
import json
import logging
import subprocess
import threading
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from specify_cli.cli.commands.charter_bundle import app as charter_bundle_app
from specify_cli.cli.selector_resolution import resolve_selector
from specify_cli.decisions import service as _dm_service
from specify_cli.decisions.models import OriginFlow as _DmOriginFlow
from specify_cli.decisions.service import DecisionError as _DecisionError
from specify_cli.tasks_support import TaskCliError, find_repo_root
from charter.sync import ensure_charter_bundle_fresh

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="charter",
    help="Charter management commands",
    no_args_is_help=True,
)

# WP01 introduced ``charter_bundle_app`` as a self-contained Typer sub-app.
# WP03 registers it under ``bundle`` so users can invoke
# ``spec-kitty charter bundle validate`` from the unified CLI surface
# (FR-013).
app.add_typer(charter_bundle_app, name="bundle")

console = Console()


def default_interview(*args, **kwargs):
    """Patchable lazy wrapper for default charter interview generation."""
    from charter.interview import default_interview as _default_interview

    return _default_interview(*args, **kwargs)


def _resolve_charter_path(repo_root: Path) -> Path:
    """Find charter.md in canonical location only.

    Does not fall back to legacy locations. Users with pre-charter state
    must run 'spec-kitty upgrade' first (handled by the charter-rename migration).
    """
    charter_path = repo_root / ".kittify" / "charter" / "charter.md"
    if charter_path.exists():
        return charter_path

    raise TaskCliError(
        f"Charter not found at {charter_path}\n"
        "  Run 'spec-kitty charter interview' to create one,\n"
        "  or 'spec-kitty upgrade' if migrating from an older version."
    )


def _resolve_actor() -> str:
    """Return the git user email or ``"cli"`` as fallback."""
    try:
        result = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        email = result.stdout.strip()
        if email:
            return email
    except Exception:  # noqa: BLE001
        pass
    return "cli"


def _parse_csv_option(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    values = [part.strip() for part in raw.split(",")]
    normalized = [value for value in values if value]
    return normalized if normalized else []


def _interview_path(repo_root: Path) -> Path:
    return repo_root / ".kittify" / "charter" / "interview" / "answers.yaml"


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _collect_charter_sync_status(repo_root: Path) -> dict[str, Any]:
    try:
        from charter.hasher import is_stale

        sync_result = ensure_charter_bundle_fresh(repo_root)
        # Generate glossary entity pages (non-blocking; silent on failure)
        try:
            from specify_cli.glossary.entity_pages import GlossaryEntityPageRenderer
            GlossaryEntityPageRenderer(repo_root).generate_all()
        except Exception as _ep_exc:  # noqa: BLE001
            logger.debug("entity page generation failed (non-fatal): %s", _ep_exc)
        canonical_root = (
            sync_result.canonical_root
            if sync_result and sync_result.canonical_root
            else repo_root
        )
        charter_path = _resolve_charter_path(canonical_root)
        output_dir = charter_path.parent
        metadata_path = output_dir / "metadata.yaml"

        stale, current_hash, stored_hash = is_stale(charter_path, metadata_path)

        files_info: list[dict[str, str | bool | float]] = []
        for filename in [
            "governance.yaml",
            "directives.yaml",
            "metadata.yaml",
            "references.yaml",
        ]:
            file_path = output_dir / filename
            if file_path.exists():
                size = file_path.stat().st_size
                size_kb = size / 1024
                files_info.append(
                    {"name": filename, "exists": True, "size_kb": size_kb}
                )
            else:
                files_info.append(
                    {"name": filename, "exists": False, "size_kb": 0.0}
                )

        library_count = (
            len(list((output_dir / "library").glob("*.md")))
            if (output_dir / "library").exists()
            else 0
        )

        last_sync = None
        if metadata_path.exists():
            from ruamel.yaml import YAML

            yaml = YAML(typ="safe")
            metadata = yaml.load(metadata_path.read_text(encoding="utf-8")) or {}
            if isinstance(metadata, dict):
                last_sync = metadata.get("timestamp_utc") or metadata.get(
                    "extracted_at"
                )

        return {
            "available": True,
            "charter_path": _display_path(charter_path, canonical_root),
            "status": "stale" if stale else "synced",
            "current_hash": current_hash,
            "stored_hash": stored_hash,
            "last_sync": last_sync,
            "library_docs": library_count,
            "files": files_info,
        }
    except TaskCliError as exc:
        return {
            "available": False,
            "error": str(exc),
        }


def _collect_generated_input_status(repo_root: Path) -> dict[str, Any]:
    input_root = repo_root / ".kittify" / "charter" / "generated"
    counts = {
        "directive": len(list((input_root / "directives").glob("*.yaml"))),
        "tactic": len(list((input_root / "tactics").glob("*.yaml"))),
        "styleguide": len(list((input_root / "styleguides").glob("*.yaml"))),
    }
    return {
        "path": _display_path(input_root, repo_root),
        "exists": input_root.exists(),
        "counts": counts,
        "total": sum(counts.values()),
    }


def _collect_manifest_status(repo_root: Path) -> tuple[dict[str, Any], Any | None]:
    from charter.synthesizer.manifest import MANIFEST_PATH, load_yaml, verify

    manifest_path = repo_root / MANIFEST_PATH
    doctrine_root = repo_root / ".kittify" / "doctrine"
    provenance_root = repo_root / ".kittify" / "charter" / "provenance"
    live_artifact_count = sum(
        len(list((doctrine_root / subdir).glob("*.yaml")))
        for subdir in ("directives", "tactics", "styleguides")
    )
    live_provenance_count = len(list(provenance_root.glob("*.yaml")))

    if not manifest_path.exists():
        state = "partial" if live_artifact_count or live_provenance_count else "missing"
        return (
            {
                "path": _display_path(manifest_path, repo_root),
                "exists": False,
                "state": state,
                "artifact_count": 0,
                "live_artifact_count": live_artifact_count,
                "live_provenance_count": live_provenance_count,
                "run_id": None,
                "created_at": None,
                "adapter_id": None,
                "adapter_version": None,
                "missing_provenance_paths": [],
                "error": None,
            },
            None,
        )

    try:
        manifest = load_yaml(manifest_path)
        try:
            verify(manifest, repo_root)
            state = "valid"
            error = None
        except Exception as exc:  # noqa: BLE001
            state = "invalid"
            error = str(exc)
    except Exception as exc:  # noqa: BLE001
        return (
            {
                "path": _display_path(manifest_path, repo_root),
                "exists": True,
                "state": "invalid",
                "artifact_count": 0,
                "live_artifact_count": live_artifact_count,
                "live_provenance_count": live_provenance_count,
                "run_id": None,
                "created_at": None,
                "adapter_id": None,
                "adapter_version": None,
                "missing_provenance_paths": [],
                "error": f"manifest could not be parsed: {exc}",
            },
            None,
        )

    missing_provenance_paths = [
        entry.provenance_path
        for entry in manifest.artifacts
        if not (repo_root / entry.provenance_path).exists()
    ]

    return (
        {
            "path": _display_path(manifest_path, repo_root),
            "exists": True,
            "state": state,
            "artifact_count": len(manifest.artifacts),
            "live_artifact_count": live_artifact_count,
            "live_provenance_count": live_provenance_count,
            "run_id": manifest.run_id,
            "created_at": manifest.created_at,
            "adapter_id": manifest.adapter_id,
            "adapter_version": manifest.adapter_version,
            "missing_provenance_paths": missing_provenance_paths,
            "error": error,
        },
        manifest,
    )


def _collect_provenance_status(
    repo_root: Path,
    manifest: Any | None,
    *,
    include_entries: bool,
) -> dict[str, Any]:
    from charter.synthesizer.provenance import load_yaml as load_provenance

    provenance_root = repo_root / ".kittify" / "charter" / "provenance"
    paths = sorted(provenance_root.glob("*.yaml"))
    warnings: list[str] = []
    entries: list[dict[str, Any]] = []
    visible_paths = {_display_path(path, repo_root) for path in paths}
    manifest_paths = (
        {entry.provenance_path for entry in manifest.artifacts}
        if manifest is not None
        else set()
    )
    corpus_snapshot_ids: set[str] = set()
    adapters: set[str] = set()

    for path in paths:
        rel_path = _display_path(path, repo_root)
        try:
            entry = load_provenance(path)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"{rel_path}: {exc}")
            continue

        if entry.corpus_snapshot_id:
            corpus_snapshot_ids.add(entry.corpus_snapshot_id)
        adapters.add(f"{entry.adapter_id}@{entry.adapter_version}")

        if include_entries:
            entries.append(
                {
                    "path": rel_path,
                    "kind": entry.artifact_kind,
                    "slug": entry.artifact_slug,
                    "artifact_urn": entry.artifact_urn,
                    "adapter_id": entry.adapter_id,
                    "adapter_version": entry.adapter_version,
                    "corpus_snapshot_id": entry.corpus_snapshot_id,
                    "evidence_bundle_hash": entry.evidence_bundle_hash,
                    "generated_at": entry.generated_at,
                }
            )

    missing_for_manifest = sorted(manifest_paths - visible_paths)
    return {
        "path": _display_path(provenance_root, repo_root),
        "count": len(paths),
        "parsed_count": len(paths) - len(warnings),
        "manifest_artifact_count": len(manifest_paths),
        "missing_for_manifest_count": len(missing_for_manifest),
        "missing_for_manifest": missing_for_manifest,
        "corpus_snapshot_ids": sorted(corpus_snapshot_ids),
        "adapters": sorted(adapters),
        "warnings": warnings,
        "entries": entries,
    }


def _summarize_evidence(repo_root: Path) -> dict[str, Any]:
    evidence_result = _collect_evidence_result(
        repo_root,
        skip_code_evidence=False,
        skip_corpus=False,
    )
    bundle = evidence_result.bundle
    code_summary: dict[str, Any] | None = None
    if bundle.code_signals is not None:
        code_summary = {
            "stack_id": bundle.code_signals.stack_id,
            "primary_language": bundle.code_signals.primary_language,
            "frameworks": list(bundle.code_signals.frameworks),
            "test_frameworks": list(bundle.code_signals.test_frameworks),
            "representative_files_count": len(
                bundle.code_signals.representative_files
            ),
            "representative_files_preview": list(
                bundle.code_signals.representative_files[:5]
            ),
        }

    return {
        "warnings": evidence_result.warnings,
        "code": code_summary,
        "configured_urls": list(bundle.url_list),
        "configured_url_count": len(bundle.url_list),
        "corpus_snapshot_id": (
            bundle.corpus_snapshot.snapshot_id
            if bundle.corpus_snapshot is not None
            else None
        ),
        "corpus_entry_count": (
            len(bundle.corpus_snapshot.entries)
            if bundle.corpus_snapshot is not None
            else 0
        ),
    }


def _collect_synthesis_status(
    repo_root: Path,
    *,
    include_provenance: bool,
) -> dict[str, Any]:
    generated_inputs = _collect_generated_input_status(repo_root)
    manifest_status, manifest = _collect_manifest_status(repo_root)
    provenance_status = _collect_provenance_status(
        repo_root,
        manifest,
        include_entries=include_provenance,
    )
    evidence_summary = _summarize_evidence(repo_root)

    if (
        manifest_status["state"] == "valid"
        and provenance_status["missing_for_manifest_count"] == 0
        and not provenance_status["warnings"]
    ):
        generation_state = "promoted"
    elif (
        manifest_status["state"] in {"invalid", "partial"}
        or provenance_status["missing_for_manifest_count"] > 0
        or provenance_status["warnings"]
    ):
        generation_state = "needs_attention"
    elif generated_inputs["total"] > 0:
        generation_state = "ready_for_validation"
    else:
        generation_state = "not_started"

    return {
        "generation_state": generation_state,
        "generated_inputs": generated_inputs,
        "manifest": manifest_status,
        "provenance": provenance_status,
        "evidence": evidence_summary,
    }


# ---------------------------------------------------------------------------
# Widen Mode helpers (WP06)
# ---------------------------------------------------------------------------

#: Sentinel PrereqState used when widen prereqs are unavailable.
#: Defined lazily as a module-level constant after first import of PrereqState.
_WIDEN_PREREQS_ABSENT_CACHE: Any = None


def _get_widen_prereqs_absent() -> Any:
    """Return a fully-absent PrereqState (lazy singleton)."""
    global _WIDEN_PREREQS_ABSENT_CACHE  # noqa: PLW0603
    if _WIDEN_PREREQS_ABSENT_CACHE is None:
        try:
            from specify_cli.widen.models import PrereqState

            _WIDEN_PREREQS_ABSENT_CACHE = PrereqState(
                teamspace_ok=False,
                slack_ok=False,
                saas_reachable=False,
            )
        except ImportError:
            return None
    return _WIDEN_PREREQS_ABSENT_CACHE


def _get_mission_id(repo_root: Path, mission_slug: str) -> str | None:
    """Read mission_id (ULID) from kitty-specs/<slug>/meta.json.

    Returns ``None`` if the file is absent or malformed.
    """
    meta_path = repo_root / "kitty-specs" / mission_slug / "meta.json"
    with contextlib.suppress(Exception):
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        return data.get("mission_id") or None
    return None


def _is_already_widened(widen_store: Any, decision_id: str) -> bool:
    """Return True if *decision_id* already has a pending widen entry."""
    with contextlib.suppress(Exception):
        return any(e.decision_id == decision_id for e in widen_store.list_pending())
    return False


def _schedule_inactivity_reminder(
    console: Console,
    delay_seconds: int = 3600,
) -> threading.Timer:
    """Schedule an inactivity reminder for the blocked widen prompt (NFR-004).

    The timer fires once after *delay_seconds* (default 60 min).  It is a
    daemon thread so it will not prevent process exit.
    """

    def _remind() -> None:
        console.print(
            "\n[yellow]Still waiting on widened discussion.[/yellow] "
            "Check Slack, type a local answer, or press d to defer.\n"
            "Waiting > ",
            end="",
        )

    timer = threading.Timer(delay_seconds, _remind)
    timer.daemon = True
    timer.start()
    return timer


def _render_waiting_panel(
    console: Console,
    question_text: str,
    invited: list[str] | None,
    slack_thread_url: str | None = None,
) -> None:
    """Render the §4 Waiting-for-discussion panel (contracts/cli-contracts.md §4)."""
    participants_line = ", ".join(invited) if invited else "(none)"
    thread_line = f"Slack thread: {slack_thread_url}" if slack_thread_url else "Slack thread: (pending)"
    console.print(
        Panel(
            f"Question: {question_text}\n"
            f"Participants: {participants_line}\n"
            f"{thread_line}",
            title="Waiting for widened discussion",
        )
    )
    console.print(
        "\nOptions:\n"
        "  [f]etch & review   — fetch current discussion and produce candidate\n"
        "  <type an answer>   — resolve locally right now (closes Slack thread)\n"
        "  [d]efer            — defer this question for later\n"
    )


def _resolve_locally(
    decision_id: str,
    mission_slug: str,
    repo_root: Path,
    final_answer: str,
    actor: str,
    console: Console,
) -> None:
    """FR-018: resolve with source=manual at the blocked widen prompt."""
    with contextlib.suppress(_DecisionError):
        _dm_service.resolve_decision(
            repo_root=repo_root,
            mission_slug=mission_slug,
            decision_id=decision_id,
            final_answer=final_answer,
            actor=actor,
        )
    console.print("[green]Resolved locally.[/green] SaaS will close the Slack thread shortly.")


def _defer_from_blocked_prompt(
    decision_id: str,
    mission_slug: str,
    repo_root: Path,
    actor: str,
    console: Console,
) -> None:
    """T032: defer the widened decision from the blocked prompt."""
    try:
        rationale = console.input("Rationale for deferral (press Enter to skip): ").strip()
    except (KeyboardInterrupt, EOFError):
        rationale = ""

    with contextlib.suppress(_DecisionError):
        _dm_service.defer_decision(
            repo_root=repo_root,
            mission_slug=mission_slug,
            decision_id=decision_id,
            rationale=rationale or "deferred from blocked widen prompt",
            actor=actor,
        )
    console.print("[yellow]Decision deferred.[/yellow]")


def _fetch_and_review_from_blocked(
    decision_id: str,
    mission_slug: str,
    question_text: str,
    repo_root: Path,
    saas_client: Any,
    actor: str,
    console: Console,
) -> bool:
    """T031: fetch discussion + run candidate review from the blocked prompt.

    Returns True if the decision was resolved or deferred (loop should exit).
    """
    from specify_cli.saas_client import SaasClientError

    console.print("Fetching discussion...")
    try:
        discussion_raw = saas_client.fetch_discussion(decision_id)
    except SaasClientError as exc:
        console.print(f"[yellow]Discussion fetch failed:[/yellow] {exc}")
        console.print("You can type a local answer or press d to defer.")
        return False

    # WP07 review stub — run_candidate_review not yet implemented.
    # Fall back to informational display and return False so the user
    # can still type a local answer or defer.
    try:
        from specify_cli.widen.review import run_candidate_review

        result = run_candidate_review(
            discussion_data=discussion_raw,
            decision_id=decision_id,
            question_text=question_text,
            mission_slug=mission_slug,
            repo_root=repo_root,
            console=console,
            dm_service=_dm_service,
            actor=actor,
        )
        return result is not None
    except (ImportError, AttributeError):
        # WP07 stub not yet implemented — display raw data.
        console.print(
            f"[dim]Participants: {', '.join(discussion_raw.participants)}[/dim]\n"
            f"[dim]Messages: {discussion_raw.message_count}[/dim]\n"
            "[dim]Candidate review not yet available (WP07). "
            "Type a local answer or press d to defer.[/dim]"
        )
        return False


def _resolve_dm_terminal(
    *,
    repo_root: Path,
    mission_slug: str,
    decision_id: str,
    actual_answer: str,
    actor: str,
) -> None:
    """Apply the correct Decision Moment terminal transition after a question answer.

    Rules (FR-012):
    - ``!cancel`` → cancel (question not applicable)
    - non-empty → resolve
    - empty → defer
    """
    if actual_answer.strip().lower() == "!cancel":
        with contextlib.suppress(_DecisionError):
            _dm_service.cancel_decision(
                repo_root=repo_root,
                mission_slug=mission_slug,
                decision_id=decision_id,
                rationale="owner canceled during charter interview (question not applicable)",
                actor=actor,
            )
    elif actual_answer.strip():
        with contextlib.suppress(_DecisionError):
            _dm_service.resolve_decision(
                repo_root=repo_root,
                mission_slug=mission_slug,
                decision_id=decision_id,
                final_answer=actual_answer,
                actor=actor,
            )
    else:
        with contextlib.suppress(_DecisionError):
            _dm_service.defer_decision(
                repo_root=repo_root,
                mission_slug=mission_slug,
                decision_id=decision_id,
                rationale="owner deferred during charter interview",
                actor=actor,
            )


def _prompt_one_question(
    *,
    question_id: str,
    prompt_text: str,
    default_value: str,
    hint_line: str,
    widen_flow: Any,
    widen_store: Any,
    current_decision_id: str | None,
    mission_id: str | None,
    mission_slug: str | None,
    repo_root: Path,
    console: Console,
    saas_client: Any,
    actor: str,
    answers_override: dict[str, str],
) -> str:
    """Prompt the user for a single interview question, handling widen dispatch.

    Returns the final answer string (may be empty for widen-pending / defer paths).
    """
    console.print(f"[dim]{hint_line}[/dim]")

    user_answer = ""
    while True:
        user_answer = typer.prompt(prompt_text, default=default_value)

        if (
            user_answer.strip().lower() == "w"
            and widen_flow is not None
            and current_decision_id is not None
            and mission_id is not None
            and mission_slug is not None
        ):
            _answer, _should_break = _dispatch_widen_input(
                widen_flow=widen_flow,
                current_decision_id=current_decision_id,
                mission_id=mission_id,
                mission_slug=mission_slug,
                question_id=question_id,
                prompt_text=prompt_text,
                hint_line=hint_line,
                widen_store=widen_store,
                answers_override=answers_override,
                repo_root=repo_root,
                console=console,
                saas_client=saas_client,
                actor=actor,
            )
            if _answer is None and not _should_break:
                continue  # CANCEL — re-prompt
            if _answer is not None:
                user_answer = _answer
            break

        else:
            break

    if question_id not in answers_override:
        answers_override[question_id] = user_answer

    return answers_override[question_id]


def _dispatch_widen_input(  # noqa: C901
    *,
    widen_flow: Any,
    current_decision_id: str,
    mission_id: str,
    mission_slug: str,
    question_id: str,
    prompt_text: str,
    hint_line: str,
    widen_store: Any,
    answers_override: dict[str, str],
    repo_root: Any,
    console: Console,
    saas_client: Any,
    actor: str,
) -> tuple[str | None, bool]:
    """T028 — Dispatch ``w`` input to WidenFlow; return (user_answer, break_loop).

    Returns:
        (user_answer, should_break):
          - user_answer: None → continue inner loop (re-prompt); else the value to use.
          - should_break: True if the outer question loop should advance to next question.
    """
    from datetime import UTC, datetime

    from specify_cli.widen.models import WidenAction, WidenPendingEntry

    result = widen_flow.run_widen_mode(
        decision_id=current_decision_id,
        mission_id=mission_id,
        mission_slug=mission_slug,
        question_text=prompt_text,
        actor=actor,
    )

    if result.action == WidenAction.CANCEL:
        # Re-show hint and re-prompt the same question
        console.print(f"[dim]{hint_line}[/dim]")
        return None, False  # continue inner loop

    if result.action == WidenAction.BLOCK:
        # Enter the blocked-prompt loop (T029)
        _run_blocked_prompt_loop(
            decision_id=result.decision_id or current_decision_id,
            question_text=prompt_text,
            invited=result.invited,
            mission_slug=mission_slug,
            repo_root=repo_root,
            console=console,
            saas_client=saas_client,
            actor=actor,
        )
        answers_override[question_id] = ""
        return "", True  # advance to next question

    if result.action == WidenAction.CONTINUE:
        # Write WidenPendingEntry (T024 pattern — caller does persistence)
        if widen_store is not None:
            with contextlib.suppress(Exception):
                widen_store.add_pending(WidenPendingEntry(
                    decision_id=result.decision_id or current_decision_id,
                    mission_slug=mission_slug,
                    question_id=f"charter.{question_id}",
                    question_text=prompt_text,
                    entered_pending_at=datetime.now(tz=UTC),
                    widen_endpoint_response={},
                ))
        answers_override[question_id] = ""
        return "", True  # advance to next question

    # Unknown action — fall through to normal answer
    return None, True


def _run_blocked_prompt_loop(
    decision_id: str,
    question_text: str,
    invited: list[str] | None,
    mission_slug: str,
    repo_root: Path,
    console: Console,
    saas_client: Any,
    actor: str,
    slack_thread_url: str | None = None,
) -> None:
    """T029: block the interview at the widened question until resolved.

    Renders the waiting panel and loops on input until the decision is
    resolved via one of:
    - [f]etch & review → run_candidate_review()
    - plain text answer → decision.resolve(manual)
    - [d]efer → decision.defer()
    """
    _render_waiting_panel(console, question_text, invited, slack_thread_url)

    # NFR-004: inactivity reminder after 60 minutes
    _inactivity_timer = _schedule_inactivity_reminder(console)

    while True:
        try:
            raw = console.input("Waiting > ")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Type d to defer or a local answer to resolve.[/dim]")
            continue

        cmd = raw.strip()

        if not cmd:
            # Blank line — re-show options summary
            console.print(
                "[dim][f]etch & review | <local answer> | [d]efer | [!cancel][/dim]"
            )
            continue
        elif cmd.lower() == "f":
            _inactivity_timer.cancel()
            resolved = _fetch_and_review_from_blocked(
                decision_id=decision_id,
                mission_slug=mission_slug,
                question_text=question_text,
                repo_root=repo_root,
                saas_client=saas_client,
                actor=actor,
                console=console,
            )
            if resolved:
                break
            # Not resolved — reschedule inactivity timer and loop
            _inactivity_timer = _schedule_inactivity_reminder(console)
        elif cmd.lower() == "d":
            _inactivity_timer.cancel()
            _defer_from_blocked_prompt(
                decision_id=decision_id,
                mission_slug=mission_slug,
                repo_root=repo_root,
                actor=actor,
                console=console,
            )
            break
        elif cmd.lower() == "!cancel":
            _inactivity_timer.cancel()
            console.print("[dim]Interview canceled.[/dim]")
            raise typer.Exit()
        else:
            # Plain text → local answer (FR-018)
            _inactivity_timer.cancel()
            _resolve_locally(
                decision_id=decision_id,
                mission_slug=mission_slug,
                repo_root=repo_root,
                final_answer=cmd,
                actor=actor,
                console=console,
            )
            break


@app.command()
def interview(  # noqa: C901
    mission_type: str | None = typer.Option(
        None,
        "--mission-type",
        help="Mission type for charter defaults (default: software-dev)",
    ),
    mission: str | None = typer.Option(None, "--mission", hidden=True, help="(deprecated) Use --mission-type"),
    profile: str = typer.Option("minimal", "--profile", help="Interview profile: minimal or comprehensive"),
    use_defaults: bool = typer.Option(False, "--defaults", help="Use deterministic defaults without prompts"),
    selected_paradigms: str | None = typer.Option(
        None,
        "--selected-paradigms",
        help="Comma-separated paradigm IDs override",
    ),
    selected_directives: str | None = typer.Option(
        None,
        "--selected-directives",
        help="Comma-separated directive IDs override",
    ),
    available_tools: str | None = typer.Option(
        None,
        "--available-tools",
        help="Comma-separated tool IDs override",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    mission_slug: str | None = typer.Option(
        None,
        "--mission-slug",
        help="Mission slug for Decision Moment paper trail (optional)",
    ),
) -> None:
    """Capture charter interview answers for later generation."""
    from charter.interview import (
        MINIMAL_QUESTION_ORDER,
        QUESTION_ORDER,
        QUESTION_PROMPTS,
        apply_answer_overrides,
        write_interview_answers,
    )

    try:
        repo_root = find_repo_root()
        normalized_profile = profile.strip().lower()
        if normalized_profile not in {"minimal", "comprehensive"}:
            raise ValueError("--profile must be 'minimal' or 'comprehensive'")

        resolved_mission_type = "software-dev"
        if mission_type is not None or mission is not None:
            resolved = resolve_selector(
                canonical_value=mission_type,
                canonical_flag="--mission-type",
                alias_value=mission,
                alias_flag="--mission",
                suppress_env_var="SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION",
                command_hint="--mission-type <name>",
            )
            resolved_mission_type = resolved.canonical_value

        interview_data = default_interview(mission=resolved_mission_type, profile=normalized_profile)

        # Resolve actor for Decision Moment events (non-fatal fallback)
        actor = _resolve_actor()

        # ------------------------------------------------------------------
        # T026 — Widen Mode prereq check at startup (non-fatal, ≤300ms)
        # ------------------------------------------------------------------
        prereq_state: Any = _get_widen_prereqs_absent()
        widen_flow: Any = None
        widen_store: Any = None
        _saas_client: Any = None

        if mission_slug is not None:
            try:
                from specify_cli.saas_client import SaasClient
                from specify_cli.widen import check_prereqs
                from specify_cli.widen.flow import WidenFlow
                from specify_cli.widen.state import WidenPendingStore

                _saas_client = SaasClient.from_env(repo_root)
                # Resolve team_slug from the auth context
                _team_slug: str = ""
                with contextlib.suppress(Exception):
                    from specify_cli.saas_client.auth import load_auth_context
                    _auth_ctx = load_auth_context(repo_root)
                    _team_slug = _auth_ctx.team_slug or ""

                prereq_state = check_prereqs(_saas_client, team_slug=_team_slug)
                if prereq_state.all_satisfied:
                    widen_flow = WidenFlow(_saas_client, repo_root, console)
                    widen_store = WidenPendingStore(repo_root, mission_slug)
            except Exception:  # noqa: BLE001
                pass  # non-fatal; prereq_state stays ABSENT

        # Resolve mission_id for widen endpoint (ULID from meta.json)
        _mission_id: str | None = None
        if mission_slug is not None:
            _mission_id = _get_mission_id(repo_root, mission_slug)

        if not use_defaults:
            question_order = MINIMAL_QUESTION_ORDER if normalized_profile == "minimal" else QUESTION_ORDER
            answers_override: dict[str, str] = {}
            for question_id in question_order:
                prompt_text = QUESTION_PROMPTS.get(question_id, question_id.replace("_", " ").title())
                default_value = interview_data.answers.get(question_id, "")

                # Open a Decision Moment before presenting the question (non-fatal)
                current_decision_id: str | None = None
                if mission_slug is not None:
                    with contextlib.suppress(_DecisionError):
                        dm_response = _dm_service.open_decision(
                            repo_root=repo_root,
                            mission_slug=mission_slug,
                            origin_flow=_DmOriginFlow.CHARTER,
                            step_id=f"charter.{question_id}",
                            input_key=question_id,
                            question=prompt_text,
                            options=(),
                            actor=actor,
                        )
                        current_decision_id = dm_response.decision_id

                # T045 — Already-widened question prompt (§1.3 contract)
                _already_widened = (
                    widen_store is not None
                    and current_decision_id is not None
                    and _is_already_widened(widen_store, current_decision_id)
                )
                if (
                    _already_widened
                    and _saas_client is not None
                    and mission_slug is not None
                    and current_decision_id is not None
                ):
                    from specify_cli.widen.interview_helpers import render_already_widened_prompt

                    render_already_widened_prompt(
                        question_text=prompt_text,
                        decision_id=current_decision_id,
                        mission_slug=mission_slug,
                        repo_root=repo_root,
                        saas_client=_saas_client,
                        widen_store=widen_store,
                        dm_service=_dm_service,
                        actor=actor,
                        console=console,
                    )
                    answers_override[question_id] = ""
                    continue  # next question — decision already handled

                # T027 — Build hint line; append [w]iden when prereqs met
                widen_suffix = ""
                if (
                    prereq_state is not None
                    and prereq_state.all_satisfied
                    and widen_store is not None
                    and current_decision_id is not None
                    and not _already_widened
                ):
                    widen_suffix = " | [w]iden"
                hint_line = (
                    f"[enter]=accept default | [text]=type answer{widen_suffix}"
                    " | [d]efer | [!cancel]"
                )

                # Prompt the question (handles widen dispatch internally)
                actual_answer = _prompt_one_question(
                    question_id=question_id,
                    prompt_text=prompt_text,
                    default_value=default_value,
                    hint_line=hint_line,
                    widen_flow=widen_flow,
                    widen_store=widen_store,
                    current_decision_id=current_decision_id,
                    mission_id=_mission_id,
                    mission_slug=mission_slug,
                    repo_root=repo_root,
                    console=console,
                    saas_client=_saas_client,
                    actor=actor,
                    answers_override=answers_override,
                )

                # Terminal DM event (non-fatal)
                if current_decision_id is not None and mission_slug is not None:
                    _resolve_dm_terminal(
                        repo_root=repo_root,
                        mission_slug=mission_slug,
                        decision_id=current_decision_id,
                        actual_answer=actual_answer,
                        actor=actor,
                    )

            paradigms_default = ", ".join(interview_data.selected_paradigms)
            directives_default = ", ".join(interview_data.selected_directives)
            tools_default = ", ".join(interview_data.available_tools)

            selected_paradigms = typer.prompt(
                "Selected paradigms (comma-separated)",
                default=selected_paradigms or paradigms_default,
            )
            selected_directives = typer.prompt(
                "Selected directives (comma-separated)",
                default=selected_directives or directives_default,
            )
            available_tools = typer.prompt(
                "Available tools (comma-separated)",
                default=available_tools or tools_default,
            )

            interview_data = apply_answer_overrides(
                interview_data,
                answers=answers_override,
                selected_paradigms=_parse_csv_option(selected_paradigms),
                selected_directives=_parse_csv_option(selected_directives),
                available_tools=_parse_csv_option(available_tools),
            )
        else:
            # --defaults path: no interactive prompt, but we still record a
            # Decision Moment per question so the paper trail matches the
            # interactive flow.  Each defaulted answer becomes a resolved
            # decision (or deferred when the default is empty).
            if mission_slug is not None:
                question_order = MINIMAL_QUESTION_ORDER if normalized_profile == "minimal" else QUESTION_ORDER
                for question_id in question_order:
                    prompt_text = QUESTION_PROMPTS.get(question_id, question_id.replace("_", " ").title())
                    default_answer = interview_data.answers.get(question_id, "")
                    with contextlib.suppress(_DecisionError):
                        dm_response = _dm_service.open_decision(
                            repo_root=repo_root,
                            mission_slug=mission_slug,
                            origin_flow=_DmOriginFlow.CHARTER,
                            step_id=f"charter.{question_id}",
                            input_key=question_id,
                            question=prompt_text,
                            options=(),
                            actor=actor,
                        )
                        _resolve_dm_terminal(
                            repo_root=repo_root,
                            mission_slug=mission_slug,
                            decision_id=dm_response.decision_id,
                            actual_answer=default_answer,
                            actor=actor,
                        )

            interview_data = apply_answer_overrides(
                interview_data,
                selected_paradigms=_parse_csv_option(selected_paradigms),
                selected_directives=_parse_csv_option(selected_directives),
                available_tools=_parse_csv_option(available_tools),
            )

        # ------------------------------------------------------------------
        # T040 — End-of-interview pending pass (FR-010)
        # ------------------------------------------------------------------
        if widen_store is not None and _saas_client is not None and mission_slug is not None:
            from specify_cli.widen.interview_helpers import run_end_of_interview_pending_pass

            run_end_of_interview_pending_pass(
                widen_store=widen_store,
                saas_client=_saas_client,
                mission_slug=mission_slug,
                repo_root=repo_root,
                console=console,
                dm_service=_dm_service,
                actor=actor,
            )

        answers_path = _interview_path(repo_root)
        write_interview_answers(answers_path, interview_data)

        if json_output:
            print(
                json.dumps(
                    {
                        "result": "success",
                        "success": True,
                        "interview_path": str(answers_path.relative_to(repo_root)),
                        "mission": interview_data.mission,
                        "profile": interview_data.profile,
                        "selected_paradigms": interview_data.selected_paradigms,
                        "selected_directives": interview_data.selected_directives,
                        "available_tools": interview_data.available_tools,
                    },
                    indent=2,
                )
            )
            return

        console.print("[green]Charter interview answers saved[/green]")
        console.print(f"Interview file: {answers_path.relative_to(repo_root)}")
        console.print(f"Mission: {interview_data.mission}")
        console.print(f"Profile: {interview_data.profile}")

    except (TaskCliError, ValueError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1) from e


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
    """Stage ``files`` via ``git add --force`` so ``bundle validate`` accepts them.

    Issue #841: ``charter generate`` must auto-track the produced ``charter.md``
    (and any other tracked-files manifest entries) so the immediately-following
    ``charter bundle validate`` succeeds without an operator ``git add``. We
    stage (not commit) — staging is what ``git ls-files`` reports as tracked,
    which is the signal ``charter bundle validate`` keys on.

    Files are passed as repo-relative ``Path``s. ``--force`` is used so that an
    operator who has gitignored ``charter.md`` for any reason still gets the
    auto-track contract honored — this is consistent with the bundle manifest
    declaring ``charter.md`` as a tracked file.
    """
    for file_path in files:
        rel = file_path.as_posix()
        subprocess.run(
            ["git", "add", "--force", "--", rel],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
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


@app.command()
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
    """
    from charter.compiler import compile_charter, write_compiled_charter
    from charter.interview import read_interview_answers
    from charter.sync import sync as sync_charter

    try:
        repo_root = find_repo_root()

        # T030 (#841 fail-fast): verify we are inside a git working tree
        # BEFORE writing any artifact. Auto-tracking on success requires
        # git, and producing artifacts that bundle validate cannot accept
        # is exactly the silent-inconsistency bug #841 closes.
        if not _is_inside_git_worktree(repo_root):
            console.print(
                "[red]Error:[/red] charter generate requires a git repository. "
                "Initialize one with `git init` (so the produced charter.md can be "
                "auto-tracked and accepted by `charter bundle validate`)."
            )
            raise typer.Exit(code=1)
        charter_dir = repo_root / ".kittify" / "charter"
        answers_path = _interview_path(repo_root)
        resolved_mission_type = None
        if mission_type is not None or mission is not None:
            resolved = resolve_selector(
                canonical_value=mission_type,
                canonical_flag="--mission-type",
                alias_value=mission,
                alias_flag="--mission",
                suppress_env_var="SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION",
                command_hint="--mission-type <name>",
            )
            resolved_mission_type = resolved.canonical_value

        interview_data = read_interview_answers(answers_path) if from_interview else None
        if interview_data is None:
            resolved_mission = resolved_mission_type or "software-dev"
            interview_data = default_interview(
                mission=resolved_mission,
                profile=profile.strip().lower(),
            )
            interview_source = "defaults"
        else:
            interview_source = "interview"

        resolved_mission = resolved_mission_type or interview_data.mission

        compiled = compile_charter(
            mission=resolved_mission,
            interview=interview_data,
            template_set=template_set,
            repo_root=repo_root,
        )
        bundle_result = write_compiled_charter(charter_dir, compiled, force=force)
        if interview_source == "defaults":
            # Legacy CLI contract: default generation materializes an empty
            # library/ directory for older consumers. Interview-driven flows
            # keep the newer no-materialization behavior.
            (charter_dir / "library").mkdir(exist_ok=True)

        charter_path = charter_dir / "charter.md"
        sync_result = sync_charter(charter_path, charter_dir, force=True)

        if sync_result.error:
            raise RuntimeError(sync_result.error)

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
        _stage_charter_files(repo_root, list(CANONICAL_MANIFEST.tracked_files))

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
                        "diagnostics": compiled.diagnostics,
                    },
                    indent=2,
                )
            )
            return

        console.print("[green]Charter generated and synced[/green]")
        console.print(f"Charter: {charter_path.relative_to(repo_root)}")
        console.print(f"Mission: {compiled.mission}")
        console.print(f"Template set: {compiled.template_set}")
        if compiled.diagnostics:
            console.print("Diagnostics:")
            for line in compiled.diagnostics:
                console.print(f"  - {line}")
        console.print("Files written:")
        for filename in files_written:
            console.print(f"  ✓ {filename}")

    except typer.Exit:
        # Pass-through: caller already emitted an actionable message
        # (e.g. T030 fail-fast for non-git environments).
        raise
    except (FileExistsError, TaskCliError, ValueError, RuntimeError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1) from e


@app.command()
def context(
    action: str = typer.Option(..., "--action", help="Workflow action (specify|plan|implement|review)"),
    mark_loaded: bool = typer.Option(True, "--mark-loaded/--no-mark-loaded", help="Persist first-load state"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Render charter context for a specific workflow action."""
    from charter.context import BOOTSTRAP_ACTIONS, build_charter_context

    try:
        repo_root = find_repo_root()
        result = build_charter_context(repo_root, action=action, mark_loaded=mark_loaded)

        if json_output:
            print(
                json.dumps(
                    {
                        "result": "success",
                        "success": True,
                        "action": result.action,
                        "mode": result.mode,
                        "first_load": result.first_load,
                        "references_count": result.references_count,
                        "context": result.text,
                        "text": result.text,
                    },
                    indent=2,
                )
            )
            return

        if result.action in BOOTSTRAP_ACTIONS:
            console.print(f"Action: {result.action} ({result.mode})")
        console.print(result.text)

    except TaskCliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1) from e


@app.command()
def sync(
    force: bool = typer.Option(False, "--force", "-f", help="Force sync even if not stale"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Sync charter.md to structured YAML config files."""
    from charter.sync import sync as sync_charter

    try:
        repo_root = find_repo_root()
        charter_path = _resolve_charter_path(repo_root)
        output_dir = charter_path.parent

        result = sync_charter(charter_path, output_dir, force=force)

        if json_output:
            data = {
                "result": "success" if result.synced else "noop",
                "success": result.synced,
                "stale_before": result.stale_before,
                "files_written": result.files_written,
                "extraction_mode": result.extraction_mode,
                "error": result.error,
            }
            print(json.dumps(data, indent=2))
            return

        if result.error:
            console.print(f"[red]Error:[/red] {result.error}")
            raise typer.Exit(code=1)

        if result.synced:
            console.print("[green]Charter synced successfully[/green]")
            console.print(f"Mode: {result.extraction_mode}")
            console.print("\nFiles written:")
            for filename in result.files_written:
                console.print(f"  ✓ {filename}")
        else:
            console.print("[blue]Charter already in sync[/blue] (use --force to re-extract)")

    except TaskCliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1) from e


@app.command()
def status(  # noqa: C901
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    provenance: bool = typer.Option(
        False,
        "--provenance",
        help="Include per-artifact provenance details.",
    ),
) -> None:
    """Display charter sync status plus synthesis/operator state."""
    try:
        repo_root = find_repo_root()
        payload = {
            "result": "success",
            "charter_sync": _collect_charter_sync_status(repo_root),
            "synthesis": _collect_synthesis_status(
                repo_root,
                include_provenance=provenance,
            ),
        }

        if json_output:
            print(json.dumps(payload, indent=2))
            return

        sync_status = payload["charter_sync"]
        console.print("[bold]Charter sync[/bold]")
        if sync_status["available"]:
            console.print(f"Charter: {sync_status['charter_path']}")
            if sync_status["status"] == "stale":
                console.print(
                    "Status: [yellow]STALE[/yellow] (modified since last sync)"
                )
                if sync_status["stored_hash"]:
                    console.print(f"Expected hash: {sync_status['stored_hash']}")
                console.print(f"Current hash:  {sync_status['current_hash']}")
                console.print("\n[dim]Run: spec-kitty charter sync[/dim]")
            else:
                console.print("Status: [green]SYNCED[/green]")
                if sync_status["last_sync"]:
                    console.print(f"Last sync: {sync_status['last_sync']}")
                console.print(f"Hash: {sync_status['current_hash']}")

            console.print(f"Library docs: {sync_status['library_docs']}")
            console.print("\nExtracted files:")
            table = Table(show_header=True, header_style="bold")
            table.add_column("File", style="cyan")
            table.add_column("Status", justify="center")
            table.add_column("Size", justify="right")

            for file_info in sync_status["files"]:
                name = str(file_info["name"])
                exists = bool(file_info["exists"])
                size_kb = float(file_info["size_kb"])

                if exists:
                    status_icon = "[green]Y[/green]"
                    size_str = f"{size_kb:.1f} KB"
                else:
                    status_icon = "[red]N[/red]"
                    size_str = "[dim]-[/dim]"

                table.add_row(name, status_icon, size_str)

            console.print(table)
        else:
            console.print(
                f"[yellow]Unavailable[/yellow]: {sync_status['error']}"
            )

        synthesis = payload["synthesis"]
        manifest = synthesis["manifest"]
        generated_inputs = synthesis["generated_inputs"]
        evidence = synthesis["evidence"]
        provenance_status = synthesis["provenance"]

        state_styles = {
            "promoted": "green",
            "ready_for_validation": "yellow",
            "needs_attention": "red",
            "not_started": "blue",
        }
        state = synthesis["generation_state"]
        state_style = state_styles.get(state, "white")

        console.print("\n[bold]Synthesis[/bold]")
        console.print(
            f"Generation state: [{state_style}]{state.upper()}[/{state_style}]"
        )
        console.print(
            "Generated inputs: "
            f"{generated_inputs['counts']['directive']} directive, "
            f"{generated_inputs['counts']['tactic']} tactic, "
            f"{generated_inputs['counts']['styleguide']} styleguide "
            f"under {generated_inputs['path']}"
        )

        manifest_state_style = {
            "valid": "green",
            "missing": "blue",
            "partial": "yellow",
            "invalid": "red",
        }.get(manifest["state"], "white")
        console.print(
            f"Manifest: [{manifest_state_style}]{manifest['state'].upper()}[/{manifest_state_style}] "
            f"({manifest['path']})"
        )
        if manifest["exists"]:
            if manifest["run_id"] and manifest["adapter_id"] and manifest["adapter_version"]:
                console.print(
                    f"  Run: {manifest['run_id']}  Adapter: {manifest['adapter_id']} v{manifest['adapter_version']}"
                )
            console.print(
                f"  Artifacts: {manifest['artifact_count']} "
                f"(live doctrine files: {manifest['live_artifact_count']})"
            )
        if manifest["error"]:
            console.print(f"  [red]Error:[/red] {manifest['error']}")
        if manifest["missing_provenance_paths"]:
            console.print("  Missing provenance paths:")
            for path in manifest["missing_provenance_paths"]:
                console.print(f"    [red]-[/red] {path}")

        if evidence["code"] is not None:
            code = evidence["code"]
            console.print(
                "Evidence: "
                f"stack={code['stack_id']} "
                f"(lang={code['primary_language']}, "
                f"frameworks={len(code['frameworks'])}, "
                f"test_frameworks={len(code['test_frameworks'])})"
            )
        else:
            console.print("Evidence: code signals unavailable")
        console.print(
            f"  Configured URLs: {evidence['configured_url_count']}  "
            f"Corpus snapshot: {evidence['corpus_snapshot_id'] or '(none)'}"
        )
        if evidence["warnings"]:
            for warning in evidence["warnings"]:
                console.print(f"  [yellow]Warning:[/yellow] {warning}")

        console.print(
            "Provenance: "
            f"{provenance_status['parsed_count']} visible sidecar(s)"
        )
        if provenance_status["manifest_artifact_count"]:
            console.print(
                "  Manifest coverage: "
                f"{provenance_status['manifest_artifact_count'] - provenance_status['missing_for_manifest_count']}/"
                f"{provenance_status['manifest_artifact_count']}"
            )
        if provenance_status["corpus_snapshot_ids"]:
            console.print(
                "  Corpus snapshots: "
                + ", ".join(provenance_status["corpus_snapshot_ids"])
            )
        if provenance_status["warnings"]:
            for warning in provenance_status["warnings"]:
                console.print(f"  [yellow]Warning:[/yellow] {warning}")

        if provenance and provenance_status["entries"]:
            console.print("\nProvenance entries:")
            table = Table(show_header=True, header_style="bold")
            table.add_column("Kind", style="cyan")
            table.add_column("Slug", style="cyan")
            table.add_column("Artifact URN", style="magenta")
            table.add_column("Adapter")
            table.add_column("Corpus")
            table.add_column("Evidence Hash")

            for entry in provenance_status["entries"]:
                evidence_hash = entry["evidence_bundle_hash"] or ""
                table.add_row(
                    str(entry["kind"]),
                    str(entry["slug"]),
                    str(entry["artifact_urn"]),
                    f"{entry['adapter_id']} v{entry['adapter_version']}",
                    str(entry["corpus_snapshot_id"] or "-"),
                    evidence_hash[:12] if evidence_hash else "-",
                )

            console.print(table)

    except TaskCliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1) from e


# ---------------------------------------------------------------------------
# Synthesizer subcommands (Phase 3 — T030)
# ---------------------------------------------------------------------------


def _build_synthesis_request(
    repo_root: Path,
    adapter_name: str,
    evidence: Any = None,
) -> tuple[Any, Any]:
    """Build a SynthesisRequest + adapter from the project's current interview state.

    Returns ``(SynthesisRequest, adapter)`` ready for synthesize() / resynthesize().
    Raises ``TaskCliError`` if the interview answers file does not exist.
    """
    import uuid

    from charter.interview import read_interview_answers
    from charter.synthesizer.fixture_adapter import FixtureAdapter
    from charter.synthesizer.generated_artifact_adapter import GeneratedArtifactAdapter
    from charter.synthesizer.request import SynthesisRequest, SynthesisTarget

    answers_path = _interview_path(repo_root)
    interview_data = read_interview_answers(answers_path)
    if interview_data is None:
        raise TaskCliError(
            "No interview answers found. "
            "Run 'spec-kitty charter interview' first."
        )

    # Build a minimal interview snapshot from the interview data
    interview_snapshot: dict[str, Any] = {
        "mission_type": interview_data.mission,
        "selected_directives": interview_data.selected_directives,
        "selected_paradigms": interview_data.selected_paradigms,
    }
    interview_snapshot.update(dict(interview_data.answers))

    # Build a minimal doctrine snapshot (directives only for now)
    doctrine_snapshot: dict[str, Any] = {
        "directives": {},
        "tactics": {},
        "styleguides": {},
    }

    # Build a minimal DRG snapshot with shipped directives as nodes
    drg_nodes = []
    for directive_id in interview_data.selected_directives:
        drg_nodes.append({
            "urn": f"directive:{directive_id}",
            "kind": "directive",
            "id": directive_id,
        })
    drg_snapshot: dict[str, Any] = {
        "nodes": drg_nodes,
        "edges": [],
        "schema_version": "1",
    }

    # Placeholder target (synthesize() derives actual targets from interview)
    target = SynthesisTarget(
        kind="directive",
        slug="synthesize-placeholder",
        title="Synthesize Placeholder",
        artifact_id="PROJECT_000",
        source_section="mission_type",
    )

    run_id = str(uuid.uuid4()).replace("-", "").upper()[:26]

    request = SynthesisRequest(
        target=target,
        interview_snapshot=interview_snapshot,
        doctrine_snapshot=doctrine_snapshot,
        drg_snapshot=drg_snapshot,
        run_id=run_id,
        evidence=evidence,
    )

    if adapter_name == "generated":
        adapter_obj = GeneratedArtifactAdapter(repo_root=repo_root)
    elif adapter_name == "fixture":
        adapter_obj = FixtureAdapter()
    else:
        raise TaskCliError(
            f"Unknown adapter '{adapter_name}'. "
            "Supported adapters are '--adapter generated' and '--adapter fixture'. "
            "Doctrine generation is performed by the LLM harness (Claude Code, Codex, "
            "Cursor, etc.) via the spec-kitty-charter-doctrine skill. "
            "spec-kitty never calls an LLM itself."
        )

    return request, adapter_obj


def _collect_evidence_result(
    repo_root: Path,
    *,
    skip_code_evidence: bool,
    skip_corpus: bool,
) -> Any:
    from charter.evidence.orchestrator import EvidenceOrchestrator, load_url_list_from_config

    url_list = load_url_list_from_config(repo_root)
    orchestrator = EvidenceOrchestrator(
        repo_root=repo_root,
        url_list=url_list,
        skip_code=skip_code_evidence,
        skip_corpus=skip_corpus,
    )
    return orchestrator.collect()


def _build_synthesis_validation_callback(request: Any) -> Any:
    from doctrine.drg.models import DRGGraph
    from importlib.metadata import version as pkg_version

    from charter.synthesizer.interview_mapping import resolve_sections
    from charter.synthesizer.orchestrator import _shipped_drg_from_snapshot
    from charter.synthesizer.project_drg import emit_project_layer, persist as persist_project_graph
    from charter.synthesizer.targets import build_targets, detect_duplicates, order_targets
    from charter.synthesizer.validation_gate import validate as validate_project_graph

    spec_kitty_version = pkg_version("spec-kitty-cli")
    shipped_drg = DRGGraph.model_validate(_shipped_drg_from_snapshot(request.drg_snapshot))
    sections = resolve_sections(dict(request.interview_snapshot))
    targets = build_targets(
        interview_snapshot=dict(request.interview_snapshot),
        mappings=sections,
        drg_snapshot=dict(request.drg_snapshot),
    )
    targets = order_targets(targets)
    detect_duplicates(targets)
    if not targets:
        targets = [request.target]

    def _validation_callback(staged_dir: Any) -> None:
        project_graph = emit_project_layer(
            targets=targets,
            spec_kitty_version=spec_kitty_version,
            shipped_drg=shipped_drg,
        )
        persist_project_graph(project_graph, staged_dir.root, staged_dir.guard)
        validate_project_graph(staged_dir.root, shipped_drg)

    return _validation_callback


def _run_synthesis_dry_run(
    request: Any,
    syn_adapter: Any,
    repo_root: Path,
) -> list[str]:
    from charter.synthesizer.staging import StagingDir
    from charter.synthesizer.synthesize_pipeline import run_all
    from charter.synthesizer.write_pipeline import stage_and_validate

    results = run_all(request, adapter=syn_adapter)
    validation_callback = _build_synthesis_validation_callback(request)

    with StagingDir.create(repo_root, request.run_id) as staging_dir:
        staged_artifacts = stage_and_validate(
            request,
            staging_dir,
            results,
            validation_callback,
        )
        staging_dir.wipe()

    return staged_artifacts


def _list_resynthesis_topics(
    request: Any,
    repo_root: Path,
) -> dict[str, list[str]]:
    from charter.synthesizer.resynthesize_pipeline import (
        _load_merged_drg,
        _load_project_artifacts_from_provenance,
    )

    project_artifacts = _load_project_artifacts_from_provenance(repo_root)
    merged_drg = _load_merged_drg(repo_root, request)
    interview_sections = sorted(str(section) for section in request.interview_snapshot)

    artifact_topics = []
    for artifact in project_artifacts:
        selector = artifact.urn if artifact.kind == "directive" else f"{artifact.kind}:{artifact.slug}"
        artifact_topics.append(selector)

    drg_topics: list[str] = []
    for node in merged_drg.get("nodes", []):
        if isinstance(node, dict):
            urn = node.get("urn")
            if isinstance(urn, str) and urn:
                drg_topics.append(urn)

    return {
        "project_artifacts": sorted(dict.fromkeys(artifact_topics)),
        "drg_urns": sorted(dict.fromkeys(drg_topics)),
        "interview_sections": interview_sections,
        "interview_section_aliases": sorted(section.replace("_", "-") for section in interview_sections),
    }


def _has_generated_artifacts(repo_root: Path) -> bool:
    """Return True iff ``.kittify/charter/generated/`` contains agent-authored YAMLs.

    The ``generated`` adapter (production default) reads YAML files written by
    the LLM harness under ``.kittify/charter/generated/{directives,tactics,
    styleguides}/``. On a fresh project the harness has not run yet, so this
    directory is either missing or empty. The fresh-project synthesize path
    (T032 / #839) keys on this signal.
    """
    generated_root = repo_root / ".kittify" / "charter" / "generated"
    if not generated_root.is_dir():
        return False
    for sub in ("directives", "tactics", "styleguides"):
        sub_dir = generated_root / sub
        if sub_dir.is_dir() and any(sub_dir.glob("*.yaml")):
            return True
    return False


# T031 (#839 minimal artifact set): the runtime consumes ``.kittify/doctrine/``
# via ``DoctrineService(project_root=...)``. The candidate-list resolver in
# ``src/charter/_doctrine_paths.py::resolve_project_root`` treats project-root
# discovery as **directory-presence only** — an empty ``.kittify/doctrine/`` is
# a valid candidate, and the shipped layer (``src/doctrine/``) supplies content
# until the project layer is populated. The minimal artifact set
# ``charter synthesize`` must produce on a fresh project to unblock the runtime
# is therefore:
#
#   1. ``.kittify/doctrine/``                 — directory marker (REQUIRED)
#   2. ``.kittify/doctrine/PROVENANCE.md``    — human-readable provenance note
#                                                  describing the seed source
#                                                  (REQUIRED for auditability)
#
# Anything beyond this set (per-directive YAML, project-layer DRG graph,
# provenance sidecars, synthesis manifest) is produced ONLY when an LLM-authored
# corpus exists under ``.kittify/charter/generated/`` and is out of WP06 scope.
# See spec.md FR-015 / Spec Assumption A2 / GitHub issue #839.
_MINIMAL_FRESH_DOCTRINE_PROVENANCE_TEMPLATE = """\
# Spec Kitty Doctrine — Fresh Project Seed

This `.kittify/doctrine/` tree was materialized by `spec-kitty charter
synthesize` running against a **fresh project** (no LLM-authored YAML under
`.kittify/charter/generated/`). It exists so `DoctrineService` discovers a
project layer and the runtime can advance; it is intentionally empty.

The runtime falls back to the in-package shipped doctrine
(`src/doctrine/`) for all artifact lookups until the LLM harness writes
project-local artifacts under `.kittify/charter/generated/` and you re-run
`spec-kitty charter synthesize`.

References
----------
- GitHub issue: https://github.com/Priivacy-ai/spec-kitty/issues/839
- Spec assumption A2: public CLI synthesize works on a fresh project.
- Project-root resolution: `src/charter/_doctrine_paths.py`.
"""


def _materialize_fresh_doctrine(repo_root: Path) -> list[str]:
    """Materialize the minimal ``.kittify/doctrine/`` artifact set.

    Used on a fresh project where ``.kittify/charter/generated/`` has no
    agent-authored YAML (T032 / #839). Sources the canonical seed text from
    this module's in-package constant — no external file I/O, no new
    dependency, no doctrine-subsystem changes.

    Idempotent: re-runs produce bytewise-identical output (T033). Returns the
    list of repo-relative paths written.
    """
    doctrine_dir = repo_root / ".kittify" / "doctrine"
    doctrine_dir.mkdir(parents=True, exist_ok=True)

    provenance_path = doctrine_dir / "PROVENANCE.md"
    # Idempotency: only write if content differs (avoids needless mtime churn,
    # though byte-stability is preserved either way).
    new_bytes = _MINIMAL_FRESH_DOCTRINE_PROVENANCE_TEMPLATE.encode("utf-8")
    if not provenance_path.exists() or provenance_path.read_bytes() != new_bytes:
        provenance_path.write_bytes(new_bytes)

    return [
        str(provenance_path.relative_to(repo_root)),
    ]


def _planned_fresh_doctrine_paths(repo_root: Path) -> list[str]:
    """Return the repo-relative paths a fresh-project synthesize would write.

    Used by ``--dry-run`` on a fresh project (#839 follow-up): callers preview
    the materialization without touching the filesystem. Must mirror the
    output of :func:`_materialize_fresh_doctrine` exactly.
    """
    doctrine_dir = repo_root / ".kittify" / "doctrine"
    return [
        str((doctrine_dir / "PROVENANCE.md").relative_to(repo_root)),
    ]


@app.command("synthesize")
def charter_synthesize(
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

    The runtime falls back to the shipped doctrine (``src/doctrine/``) for
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

    try:
        repo_root = find_repo_root()

        # T032 (#839 fresh-project): When the operator runs synthesize on a
        # fresh project (post `charter generate` but before the LLM harness
        # has written YAMLs under .kittify/charter/generated/), the production
        # adapter has nothing to load and would raise GeneratedArtifactMissingError.
        # The intercept below takes the bounded fresh-project path: it requires
        # charter.md to exist (the upstream chain produced it) AND no
        # agent-authored YAMLs to be present. When both signals fire, we
        # materialize the minimal .kittify/doctrine/ artifact set documented in
        # T031 so the runtime can advance via the shipped-doctrine fallback.
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
            # Dry-run on a fresh project must NOT fall through to the production
            # adapter (which would raise GeneratedArtifactMissingError). Report
            # what would be materialized, write nothing, exit 0. (#839 follow-up)
            if dry_run:
                planned = _planned_fresh_doctrine_paths(repo_root)
                if json_output:
                    print(json.dumps({
                        "result": "success",
                        "success": True,
                        "mode": "fresh_project_seed_dry_run",
                        "files_planned": planned,
                        "note": (
                            "Fresh project + --dry-run: would materialize "
                            "minimal .kittify/doctrine/ (no files written). "
                            "See issue #839."
                        ),
                    }, indent=2))
                    return
                console.print(
                    "[yellow]Charter synthesis (fresh project, dry-run)[/yellow]: "
                    "would materialize minimal .kittify/doctrine/ (no files written)."
                )
                for f in planned:
                    console.print(f"  • {f}")
                return

            written = _materialize_fresh_doctrine(repo_root)

            if json_output:
                print(json.dumps({
                    "result": "success",
                    "success": True,
                    "mode": "fresh_project_seed",
                    "files_written": written,
                    "note": (
                        "Fresh project: no agent-authored YAML under "
                        ".kittify/charter/generated/. Materialized minimal "
                        ".kittify/doctrine/ so the runtime can advance "
                        "(see issue #839)."
                    ),
                }, indent=2))
                return

            console.print(
                "[green]Charter synthesis (fresh project)[/green]: minimal "
                ".kittify/doctrine/ materialized."
            )
            for f in written:
                console.print(f"  ✓ {f}")
            return

        # Collect evidence before building the synthesis request
        evidence_result = _collect_evidence_result(
            repo_root,
            skip_code_evidence=skip_code_evidence,
            skip_corpus=skip_corpus,
        )
        for warning in evidence_result.warnings:
            console.print(f"[yellow]\u26a0 {warning}[/yellow]")

        if dry_run_evidence:
            bundle = evidence_result.bundle
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
            for w in evidence_result.warnings:
                console.print(f"  [yellow]Warning: {w}[/yellow]")
            raise typer.Exit(0)

        request, syn_adapter = _build_synthesis_request(repo_root, adapter, evidence=evidence_result.bundle)

        if dry_run:
            staged_files = _run_synthesis_dry_run(request, syn_adapter, repo_root)

            if json_output:
                print(json.dumps({
                    "result": "dry_run",
                    "staged_artifacts": staged_files,
                    "artifact_count": len(staged_files),
                    "validated": True,
                }, indent=2))
                return

            console.print("[yellow]Dry-run:[/yellow] synthesis staged and validated (not promoted)")
            for f in staged_files:
                console.print(f"  [dim]staged:[/dim] {f}")
            return

        from charter.synthesizer import synthesize

        result = synthesize(request, adapter=syn_adapter, repo_root=repo_root)

        if json_output:
            print(json.dumps({
                "result": "success",
                "target_kind": result.target_kind,
                "target_slug": result.target_slug,
                "inputs_hash": result.inputs_hash,
                "adapter_id": result.effective_adapter_id,
                "adapter_version": result.effective_adapter_version,
            }, indent=2))
            return

        console.print("[green]Charter synthesis complete[/green]")
        console.print(f"Primary artifact: {result.target_kind}:{result.target_slug}")
        console.print(f"Adapter: {result.effective_adapter_id} v{result.effective_adapter_version}")

    except typer.Exit:
        raise
    except NeutralityGateViolation as e:
        render_error_panel(e, err_console)
        err_console.print(
            f"\n[yellow]Staging directory preserved at:[/yellow] {e.staging_dir}\n"
            "Inspect the staged artifacts, adjust the synthesis prompt or scope, and retry."
        )
        raise typer.Exit(code=1) from e
    except SynthesisError as e:
        render_error_panel(e, err_console)
        raise typer.Exit(code=1) from e
    except TaskCliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1) from e


@app.command("resynthesize")
def charter_resynthesize(  # noqa: C901
    topic: str | None = typer.Option(
        None,
        "--topic",
        help=(
            "Structured topic selector: "
            "<kind>:<slug> (project-local), "
            "<drg-urn> (shipped+project graph), "
            "or <interview-section-label>."
        ),
    ),
    list_topics: bool = typer.Option(
        False,
        "--list-topics",
        help="List valid structured topic selectors and exit.",
    ),
    adapter: str = typer.Option(
        "generated",
        "--adapter",
        help=(
            "Adapter to use. 'generated' (default) validates agent-authored YAML under "
            ".kittify/charter/generated/. 'fixture' is offline/testing only."
        ),
    ),
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
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Regenerate a bounded set of project-local doctrine artifacts (partial resynthesis).

    Uses a structured selector to identify the target set:

    - ``directive:PROJECT_001`` — regenerate a specific project directive.
    - ``tactic:how-we-apply-directive-003`` — regenerate one tactic.
    - ``directive:DIRECTIVE_003`` — regenerate every artifact whose provenance
      references the shipped DIRECTIVE_003 URN.
    - ``testing-philosophy`` — regenerate all artifacts from that interview section.

    Unrelated artifacts are never touched (FR-017).

    Examples
    --------
    Resynthesize a single tactic::

        spec-kitty charter resynthesize --topic tactic:how-we-apply-directive-003

    Resynthesize all artifacts referencing a shipped directive::

        spec-kitty charter resynthesize --topic directive:DIRECTIVE_003
    """
    from charter.synthesizer.errors import (
        SynthesisError,
        TopicSelectorUnresolvedError,
        render_error_panel,
    )
    from rich.panel import Panel
    from rich.text import Text

    err_console = Console(stderr=True)

    try:
        repo_root = find_repo_root()
        evidence_result = _collect_evidence_result(
            repo_root,
            skip_code_evidence=skip_code_evidence,
            skip_corpus=skip_corpus,
        )
        for warning in evidence_result.warnings:
            console.print(f"[yellow]\u26a0 {warning}[/yellow]")

        request, syn_adapter = _build_synthesis_request(repo_root, adapter, evidence=evidence_result.bundle)

        if list_topics:
            topics = _list_resynthesis_topics(request, repo_root)
            if json_output:
                print(json.dumps({
                    "result": "success",
                    "topics": topics,
                }, indent=2))
                return

            if not any(topics.values()):
                console.print("[yellow]No topic selectors available yet.[/yellow]")
                return

            if topics["project_artifacts"]:
                console.print("[bold]Project artifact selectors[/bold]")
                for selector in topics["project_artifacts"]:
                    console.print(f"  {selector}")
            if topics["drg_urns"]:
                console.print("[bold]DRG URNs[/bold]")
                for selector in topics["drg_urns"]:
                    console.print(f"  {selector}")
            if topics["interview_sections"]:
                console.print("[bold]Interview sections[/bold]")
                for selector in topics["interview_sections"]:
                    alias = selector.replace("_", "-")
                    console.print(f"  {selector}  [dim](alias: {alias})[/dim]")
            return

        if topic is None:
            raise TaskCliError("Pass --topic <selector> or use --list-topics.")

        from charter.synthesizer.resynthesize_pipeline import run as resynthesize_run

        result = resynthesize_run(
            request=request,
            adapter=syn_adapter,
            topic=topic,
            repo_root=repo_root,
        )

        if result.is_noop:
            if json_output:
                print(json.dumps({
                    "result": "noop",
                    "topic": topic,
                    "diagnostic": result.diagnostic,
                    "matched_form": result.resolved_topic.matched_form,
                    "targets_count": 0,
                }, indent=2))
                return
            console.print(f"[yellow]No-op:[/yellow] {result.diagnostic}")
            return

        regenerated = [
            f"{t.kind}:{t.slug}"
            for t in result.resolved_topic.targets
        ]

        if json_output:
            print(json.dumps({
                "result": "success",
                "topic": topic,
                "matched_form": result.resolved_topic.matched_form,
                "matched_value": result.resolved_topic.matched_value,
                "regenerated": regenerated,
                "run_id": result.manifest.run_id,
                "manifest_artifacts": len(result.manifest.artifacts),
            }, indent=2))
            return

        console.print(f"[green]Resynthesis complete[/green] (topic: {topic!r})")
        console.print(f"Matched form: {result.resolved_topic.matched_form}")
        console.print(f"Run ID: {result.manifest.run_id}")
        console.print("Regenerated artifacts:")
        for art in regenerated:
            console.print(f"  [green]✓[/green] {art}")

    except TopicSelectorUnresolvedError as e:
        # Exit code 2 — invalid usage (contracts/topic-selector.md §2.2)
        panel_body = str(e)
        if hasattr(e, "candidates") and e.candidates:
            cands = "\n".join(f"  * {c}" for c in e.candidates)
            panel_body += f"\n\nNearest candidates:\n{cands}"
        panel_body += (
            "\n\nRun 'spec-kitty charter resynthesize --list-topics' to see all valid selectors."
        )
        err_console.print(
            Panel(
                Text(panel_body),
                title=f'[bold red]Cannot resolve --topic "{e.raw}"[/]',
                border_style="red",
            )
        )
        raise typer.Exit(code=2) from e
    except SynthesisError as e:
        render_error_panel(e, err_console)
        raise typer.Exit(code=1) from e
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    except TaskCliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1) from e


@app.command("lint")
def charter_lint(
    mission: str | None = typer.Option(None, "--mission", help="Scope lint to a specific mission slug"),
    feature: str | None = typer.Option(
        None,
        "--feature",
        hidden=True,
        help="(deprecated) Use --mission",
    ),
    orphans: bool = typer.Option(False, "--orphans", help="Run only orphan checks"),
    contradictions: bool = typer.Option(False, "--contradictions", help="Run only contradiction checks"),
    stale: bool = typer.Option(False, "--stale", help="Run only staleness checks"),
    output_json: bool = typer.Option(False, "--json", help="Output findings as JSON"),
    severity: str = typer.Option("low", "--severity", help="Minimum severity (low/medium/high/critical)"),
) -> None:
    """Detect decay in charter artifacts via graph-native checks."""
    import sys

    from specify_cli.charter_lint import LintEngine

    try:
        repo_root = find_repo_root()
    except TaskCliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e

    # Resolve canonical --mission, accepting hidden --feature as a deprecated alias.
    scope = mission if mission is not None else feature

    # Resolve which checks to run
    explicit = {k for k, v in [("orphans", orphans), ("contradictions", contradictions), ("staleness", stale)] if v}
    active_checks: set[str] | None = explicit if explicit else None  # None = all

    engine = LintEngine(repo_root)
    report = engine.run(
        feature_scope=scope,
        checks=active_checks,
        min_severity=severity,
    )

    if output_json:
        sys.stdout.write(report.to_json())
        sys.stdout.write("\n")
        return

    # Human-readable output
    if not report.findings:
        console.print("[green]No decay detected[/green]")
        console.print(
            f"[dim]Scanned {report.drg_node_count} nodes in {report.duration_seconds:.2f}s[/dim]"
        )
        return

    console.print(
        f"\n[bold]Charter Lint[/bold] — {len(report.findings)} finding(s)"
        f" in {report.duration_seconds:.2f}s\n"
    )
    for finding in report.findings:
        severity_color = {
            "low": "dim",
            "medium": "yellow",
            "high": "red",
            "critical": "bold red",
        }.get(finding.severity, "white")
        console.print(
            f"  [{severity_color}][{finding.severity.upper()}][/{severity_color}]"
            f" [{finding.category}] {finding.type}: {finding.id}"
        )
        console.print(f"    {finding.message}")
        if finding.remediation_hint:
            console.print(f"    [dim]→ {finding.remediation_hint}[/dim]")
