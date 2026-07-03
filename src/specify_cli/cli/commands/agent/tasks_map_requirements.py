"""The ``map-requirements`` command family, relocated out of ``tasks.py`` (WP06, #2305).

Mission ``tasks-py-degod-wave2-01KWH9EQ`` FR-001/FR-002: ``_do_map_requirements``
+ the 11 ``_mr_*`` phase helpers + ``_MapReqState`` +
``_default_map_requirements_ports`` live here, moved VERBATIM from ``tasks.py``.
The ``@app.command`` Typer wrapper (``map_requirements``) stays in ``tasks.py``
and delegates to :func:`_do_map_requirements` (the byte-frozen ``--help``
surface is the registration shim's).

**Orchestration shape** (unchanged): the Typer command declares the CLI
surface; ``_do_map_requirements`` runs the phase helpers in the SAME order as
the original single body — validate → resolve → plan (the pure WP04
``plan_mapping`` core) → gate → write → stale gate → finalize — so the
frontmatter write still precedes the post-write stale gate
(partial-write-on-refusal timing, NFR-001/WP04). The write/commit executes
through the WP02 ports (``FsReader.primary_anchor_dir`` fold,
``commit_artifact`` on the coord WRITE authority).

**C-001 divergence wiring**: ``map_requirements`` sits on the REFUSE arm —
when auto-commit resolves on, ``_mr_resolve_context`` resolves the placement
and refuses exit-1 through ``_tasks._protected_branch_status_commit_error``
with NO ``_skip_target_branch_commit`` pre-gate (that skip-exit-0 pre-gate is
``move_task``-only). The wiring moved untouched; the coord harness refuse-arm
case (harness label T005) pins it.

**Seam bridge** (research.md D1/D7): the relocated bodies reach every patched
seam symbol through a lazy in-function import of the ``tasks`` module
(``from specify_cli.cli.commands.agent import tasks as _tasks``) and call
``_tasks.<attr>(...)``, so every historical ``@patch("...agent.tasks.<sym>")``
/ ``monkeypatch.setattr(tasks, ...)`` keeps INTERCEPTING after the move.
``tasks.py`` re-imports the family in the explicit ``as`` re-export form, so
``tasks.<name>`` stays a module attribute. Symbols with ZERO patch sites and a
canonical home outside ``tasks.py`` are imported directly at module scope
(cycle-safe: none of those modules import ``tasks``).

Per-symbol routing/interception evidence:
``kitty-specs/tasks-py-degod-wave2-01KWH9EQ/seam-checklist.md`` (Layer 4 of
the parity contract).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import typer

from kernel._safe_re import re
from mission_runtime import CommitTarget, MissionArtifactKind
from specify_cli.agent_tasks_ports import MissionHandle, TasksPorts
from specify_cli.cli.commands.agent.tasks_mapping_core import (
    TRACKER_ONLY_MODE,
    MappingPlan,
    MappingRequest,
)
from specify_cli.cli.commands.agent.tasks_outline import TASKS_MD_FILENAME
from specify_cli.missions._read_path_resolver import resolve_planning_read_dir
from specify_cli.requirement_mapping import CoverageSummary
from specify_cli.upgrade.pre30_guard import Pre30LayoutError, check_pre30_layout


def _default_map_requirements_ports(target_branch: str | None) -> TasksPorts:
    """Production port bundle for ``map_requirements`` (coord router bound to tasks.py)."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    return TasksPorts(
        fs=_tasks.RealFsReader(),
        # map_requirements threads the resolved ``target_branch`` into
        # ``commit_for_mission`` (ff-advance parity) and routes only the commit
        # seam through ``tasks`` (it inherited the base ``commit_status``).
        coord=_tasks.seam_coord_router(
            thread_target_branch=True, target_branch=target_branch
        ),
        git=_tasks.RealGitOps(),
        render=_tasks.RealRender(),
    )


@dataclass
class _MapReqState:
    """Mutable orchestration state threaded through ``map_requirements``' phases.

    The single-body command tracked ~20 loose locals across resolve → plan →
    write → gate → finalize; the phase helpers exchange this one value object
    instead. Not frozen: each phase fills its own slice in the SAME order the
    original body did, so the frontmatter write still fires BEFORE the post-write
    stale gate (partial-write-on-refusal timing — NFR-001/WP04).
    """

    # --- raw command inputs ---
    wp: str | None
    refs: str | None
    batch: str | None
    replace: bool
    tracker_ref: list[str] | None
    mission: str | None
    json_output: bool
    auto_commit: bool | None
    # --- phase A: input-mode facts ---
    tracker_ref_values: list[str] = field(default_factory=list)
    tracker_only_mode: bool = False
    # --- phase B: resolved context ---
    repo_root: Path = field(default_factory=Path)
    mission_slug: str = ""
    main_repo_root: Path = field(default_factory=Path)
    target_branch: str = ""
    auto_commit_on: bool = False
    commit_target: CommitTarget = field(default_factory=lambda: CommitTarget(ref=""))
    # --- phase C: resolved read dirs + parsed reads ---
    feature_dir: Path = field(default_factory=Path)
    primary_dir: Path = field(default_factory=Path)
    tasks_dir: Path = field(default_factory=Path)
    all_spec_ids: set[str] = field(default_factory=set)
    functional_ids: set[str] = field(default_factory=set)
    new_mappings: dict[str, list[str]] = field(default_factory=dict)
    # --- phase D: pure decision ---
    mapping_plan: MappingPlan | None = None
    # --- phase F: finalize ---
    coverage: CoverageSummary | None = None
    committed: bool = False
    commit_sha: str | None = None
    commit_result_payload: dict[str, str] | None = None


def _mr_validate_modes(st: _MapReqState) -> None:
    """Phase A: the operator-mode gates (batch vs wp/refs vs tracker-only)."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    # T040 / FR-011 (F-10): tracker_ref values are persisted alongside
    # requirement_refs.  --tracker-ref is repeatable and requires --wp.
    st.tracker_ref_values = [t.strip() for t in (st.tracker_ref or []) if t and t.strip()]

    if st.batch and (st.wp or st.refs):
        _tasks._output_error(st.json_output, "Cannot combine --batch with --wp/--refs. Use one mode.")
        raise typer.Exit(1)

    if st.tracker_ref_values and (st.batch or st.wp is None):
        _tasks._output_error(
            st.json_output,
            "--tracker-ref requires --wp (cannot be combined with --batch).",
        )
        raise typer.Exit(1)

    # When only --tracker-ref is supplied (no --refs), allow the persistence of
    # tracker refs without changing requirement_refs.  This is the primary usage
    # shape per the WP10 spec.
    st.tracker_only_mode = bool(st.tracker_ref_values and st.wp is not None and not st.refs)

    if not st.batch and not (st.wp and st.refs) and not st.tracker_only_mode:
        _tasks._output_error(
            st.json_output,
            "Provide either --wp + --refs (individual), --batch, or --wp + --tracker-ref.",
        )
        raise typer.Exit(1)


def _mr_resolve_context(st: _MapReqState) -> None:
    """Phase B: repo/mission/target-branch resolution + the protected-branch gate."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    repo_root = _tasks.locate_project_root()
    if repo_root is None:
        _tasks._output_error(st.json_output, "Could not locate project root")
        raise typer.Exit(1)
    st.repo_root = repo_root

    # FR-010 / FR-019: one-shot sparse-checkout session warning.
    _tasks._emit_sparse_session_warning(repo_root, command="spec-kitty agent tasks map-requirements")

    st.mission_slug = _tasks._find_mission_slug(
        explicit_mission=st.mission, json_output=st.json_output, repo_root=repo_root
    )
    st.main_repo_root, st.target_branch = _tasks._ensure_target_branch_checked_out(
        repo_root, st.mission_slug, st.json_output
    )
    st.auto_commit_on = (
        _tasks.get_auto_commit_default(st.main_repo_root) if st.auto_commit is None else st.auto_commit
    )
    st.commit_target = CommitTarget(ref=st.target_branch)
    if st.auto_commit_on:
        from specify_cli.coordination.commit_router import _resolve_planning_placement

        # map-requirements edits WP prompt files → WORK_PACKAGE_TASK (primary)
        # (write-surface-coherence WP02 / T009). Resolve the destination through
        # the kind authority instead of the hardcoded target_branch above.
        st.commit_target = _resolve_planning_placement(
            st.main_repo_root, st.mission_slug, kind=MissionArtifactKind.WORK_PACKAGE_TASK
        )
        protected_error = _tasks._protected_branch_status_commit_error(
            st.commit_target.ref,
            st.main_repo_root,
            "spec-kitty agent tasks map-requirements",
        )
        if protected_error is not None:
            _tasks._output_error(st.json_output, protected_error)
            raise typer.Exit(1)


def _mr_build_new_mappings(st: _MapReqState) -> None:
    """Phase C(i): build the per-WP new-mapping dict from the active input mode."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    if st.batch:
        try:
            parsed_batch = json.loads(st.batch)
        except json.JSONDecodeError as exc:
            _tasks._output_error(st.json_output, f"Invalid JSON in --batch: {exc}")
            raise typer.Exit(1) from None
        if not isinstance(parsed_batch, dict):
            _tasks._output_error(st.json_output, "--batch must be a JSON object {WP_ID: [refs]}")
            raise typer.Exit(1)
        for wp_id, ref_list in parsed_batch.items():
            if not isinstance(ref_list, list) or not all(isinstance(ref, str) for ref in ref_list):
                _tasks._output_error(
                    st.json_output,
                    f"Refs for {wp_id} must be a list of strings",
                )
                raise typer.Exit(1)
            st.new_mappings[wp_id.upper()] = [ref.upper() for ref in ref_list]
    elif st.tracker_only_mode:
        # Only --wp + --tracker-ref: no requirement refs to validate, but we still
        # register the WP key so the persistence loop visits it.
        assert st.wp is not None  # narrowed by tracker_only_mode
        st.new_mappings[st.wp.upper()] = []
    else:
        if st.wp is None or st.refs is None:
            _tasks._output_error(st.json_output, "Both --wp and --refs are required in individual mode.")
            raise typer.Exit(1)
        ref_list_parsed = [ref.strip() for ref in st.refs.split(",") if ref.strip()]
        st.new_mappings[st.wp.upper()] = [ref.upper() for ref in ref_list_parsed]


def _mr_unknown_wp_gate(st: _MapReqState) -> None:
    """Phase C(ii): reject WP ids the tasks/ dir does not carry."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    existing_wps: set[str] = set()
    if st.tasks_dir.exists():
        for wp_file in st.tasks_dir.glob("WP*.md"):
            match = re.match(r"(WP\d{2})", wp_file.name)
            if match:
                existing_wps.add(match.group(1))

    unknown_wps = sorted(wp_id for wp_id in st.new_mappings if wp_id not in existing_wps)
    if not unknown_wps:
        return
    hint = f"Available WPs: {', '.join(sorted(existing_wps))}" if existing_wps else "No WP files found in tasks/"
    if st.json_output:
        render = _tasks.RealRender()
        print(
            render.json_envelope(
                {
                    "error": "Unknown WP IDs",
                    "unknown_wps": unknown_wps,
                    "hint": hint,
                }
            )
        )
    else:
        _tasks.console.print(f"[red]Error:[/red] Unknown WP IDs: {', '.join(unknown_wps)}")
        _tasks.console.print(f"  {hint}")
    raise typer.Exit(1)


def _mr_resolve_read_dirs(st: _MapReqState, ports: TasksPorts) -> None:
    """Phase C: resolve read dirs (fold via the FsReader port), parse spec ids, build mappings.

    T030: the co-located canonicalizer fold — ``primary_feature_dir_for_mission(
    _canonicalize_primary_read_handle(...))`` — routes through the WP02
    ``FsReader.primary_anchor_dir`` port (its named consumer per WP02 Note A); the
    blind primitive + the C-002 fold stay co-located INSIDE that adapter method.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    from specify_cli.requirement_mapping import parse_requirement_ids_from_spec_md

    # #2064: resolve the WP ``tasks/`` dir through the SAME seam finalize uses.
    st.feature_dir = _tasks._map_requirements_feature_dir(st.main_repo_root, st.mission_slug)
    # Boundary guard — hard-reject pre-3.0 layout before any WP mutation.
    try:
        check_pre30_layout(st.feature_dir)
    except Pre30LayoutError as e:
        _tasks._output_error(st.json_output, str(e))
        raise typer.Exit(1) from None
    # PRIMARY-input invariant: ``spec.md`` is authored on PRIMARY — unchanged.
    # FR-011 / T012: fold the handle to its canonical dir NAME first so a bare
    # mid8 / human slug resolves the durable ``<slug>-<mid8>`` home (ambiguous
    # handle RAISES — no silent pick, C-002). Routed through the port (T030).
    handle = MissionHandle(repo_root=st.main_repo_root, mission_slug=st.mission_slug)
    st.primary_dir = ports.fs.primary_anchor_dir(handle)

    if not st.feature_dir.exists():
        _tasks._output_error(st.json_output, f"Mission directory not found: {st.feature_dir}")
        raise typer.Exit(1)

    spec_md = st.primary_dir / _tasks.SPEC_MD_FILENAME
    if not spec_md.exists():
        _tasks._output_error(st.json_output, f"spec.md not found: {spec_md}")
        raise typer.Exit(1)

    spec_ids = parse_requirement_ids_from_spec_md(spec_md.read_text(encoding="utf-8"))
    st.all_spec_ids = set(spec_ids["all"])
    st.functional_ids = set(spec_ids["functional"])

    _mr_build_new_mappings(st)

    # #2107 / FR-004 (gate-read-surface-completion WP04): the WP ``tasks/*.md``
    # files are WORK_PACKAGE_TASK — a PRIMARY-partition kind. Resolve the read dir
    # through the kind-aware seam (the SAME single authority WP01 routed the rest
    # of the gate reads onto) instead of the topology-routed ``feature_dir``.
    st.tasks_dir = (
        resolve_planning_read_dir(
            st.main_repo_root,
            st.mission_slug,
            kind=MissionArtifactKind.WORK_PACKAGE_TASK,
        )
        / "tasks"
    )
    _mr_unknown_wp_gate(st)


def _mr_plan(st: _MapReqState) -> None:
    """Phase D: freeze the reads and run the pure WP04 ``plan_mapping`` core."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    from specify_cli.requirement_mapping import read_all_wp_requirement_refs

    # WP04 (FR-005 / FR-002): resolve the reads the pure mapping core consumes —
    # existing per-WP refs (the ONE read feeding BOTH the union-merge base and the
    # coverage projection) + the tasks.md union fallback — then let ``plan_mapping``
    # own the FR↔WP mapping, new-ref validation, and coverage decision.
    existing_all_refs = read_all_wp_requirement_refs(st.tasks_dir)
    tasks_md_refs: dict[str, list[str]] = {}
    tasks_md_file = st.feature_dir / TASKS_MD_FILENAME
    if tasks_md_file.exists():
        from specify_cli.cli.commands.agent.mission import (
            _parse_requirement_refs_from_tasks_md,
        )

        tasks_md_refs = _parse_requirement_refs_from_tasks_md(
            tasks_md_file.read_text(encoding="utf-8")
        )

    if st.tracker_only_mode:
        _mapping_mode = TRACKER_ONLY_MODE
    elif st.batch:
        _mapping_mode = "batch"
    else:
        _mapping_mode = "wp_refs"
    st.mapping_plan = _tasks.plan_mapping(
        MappingRequest(
            spec_all_ids=frozenset(st.all_spec_ids),
            spec_functional_ids=frozenset(st.functional_ids),
            new_mappings=st.new_mappings,
            existing_all_refs=existing_all_refs,
            tasks_md_refs=tasks_md_refs,
            mode=_mapping_mode,
            replace=st.replace,
        )
    )


def _mr_gate_offenders(st: _MapReqState) -> None:
    """Phase D(ii): the PRE-write refusal gates driven by the core's offenders.

    Malformed FIRST, then unknown — the old inline validate_ref_format/validate_refs
    gate is deleted, not shadowed. Runs BEFORE the write loop, so a bad new ref
    refuses with NO write.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    assert st.mapping_plan is not None
    if st.mapping_plan.offenders.malformed:
        malformed = list(st.mapping_plan.offenders.malformed)
        payload = {
            "error": "Invalid requirement ref format",
            "malformed_refs": malformed,
            "hint": "Refs must match FR-NNN, NFR-NNN, or C-NNN format",
        }
        if st.json_output:
            render = _tasks.RealRender()
            print(render.json_envelope(payload))
        else:
            _tasks.console.print(f"[red]Error:[/red] Invalid ref format: {', '.join(malformed)}")
        raise typer.Exit(1)

    if st.mapping_plan.offenders.unknown_spec_id:
        unknown_refs = list(st.mapping_plan.offenders.unknown_spec_id)
        available_range = f"Available: {', '.join(sorted(st.all_spec_ids))}" if st.all_spec_ids else "No requirement IDs found in spec.md"
        payload = {
            "error": "Invalid requirement refs",
            "unknown_refs": sorted(set(unknown_refs)),
            "hint": f"Refs not found in spec.md. {available_range}",
        }
        if st.json_output:
            render = _tasks.RealRender()
            print(render.json_envelope(payload))
        else:
            _tasks.console.print(f"[red]Error:[/red] Unknown refs: {', '.join(sorted(set(unknown_refs)))}")
            _tasks.console.print(f"  {available_range}")
        raise typer.Exit(1)


def _mr_write_frontmatter(st: _MapReqState) -> None:
    """Phase E: apply the core's ``to_write`` (+ tracker refs) to WP frontmatter.

    Fires BEFORE the post-write stale gate — partial-write-on-refusal timing is
    preserved (NFR-001/WP04).
    """
    from specify_cli.frontmatter import write_frontmatter
    from specify_cli.status import read_wp_frontmatter

    assert st.mapping_plan is not None
    for wp_id in st.new_mappings:
        wp_file = next((wp_file for wp_file in st.tasks_dir.glob(f"{wp_id}*.md")), None)
        if wp_file is None:
            continue

        wp_meta, body = read_wp_frontmatter(wp_file)
        update_kwargs: dict[str, list[str]] = {}

        # Only update requirement_refs when refs were supplied; preserves backward
        # compatibility for the tracker-only invocation. The merged value is the
        # pure core's ``to_write`` (WP04) — the inline replace/union is deleted.
        if not st.tracker_only_mode:
            update_kwargs["requirement_refs"] = st.mapping_plan.to_write[wp_id]

        # T040 / FR-011 (F-10): merge tracker_refs (or replace if --replace).
        if st.tracker_ref_values and st.wp is not None and wp_id == st.wp.upper():
            if st.replace:
                merged_trackers = sorted(set(st.tracker_ref_values))
            else:
                existing_trackers = list(wp_meta.tracker_refs or [])
                merged_trackers = sorted(set(existing_trackers) | set(st.tracker_ref_values))
            update_kwargs["tracker_refs"] = merged_trackers

        if update_kwargs:
            updated_meta = wp_meta.update(**update_kwargs)
            write_frontmatter(wp_file, updated_meta.model_dump(exclude_none=True), body)


def _mr_stale_gate(st: _MapReqState) -> None:
    """Phase E(ii): post-write hard-fail on stale/invalid refs across ALL WPs.

    Runs AFTER the frontmatter write (original sequence position), so a pre-existing
    stale ref on an untouched WP still refuses (exit 1) with the partial write on
    disk — the exact partial-write-on-refusal behaviour WP04 preserved.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    from specify_cli.requirement_mapping import (
        classify_stale_refs,
        read_all_wp_raw_requirement_refs,
        validate_ref_format,
        validate_refs,
    )

    all_wp_raw = read_all_wp_raw_requirement_refs(st.tasks_dir)
    all_raw_refs: list[str] = []
    for ref_list in all_wp_raw.values():
        all_raw_refs.extend(ref_list)

    # Raw tokens preserve case; uppercase for comparison.
    uppercased_raw = [r.upper() for r in all_raw_refs if not r.startswith("<")]
    _, post_merge_malformed = validate_ref_format(uppercased_raw)
    _, post_merge_unknown = validate_refs(uppercased_raw, st.all_spec_ids)
    stale_refs: dict[str, list[str]] = {}
    if post_merge_malformed or post_merge_unknown:
        bad = set(post_merge_malformed) | set(post_merge_unknown)
        for wp_id, ref_list in all_wp_raw.items():
            wp_bad = sorted(token for token in ref_list if token.upper() in bad or token.startswith("<"))
            if wp_bad:
                stale_refs[wp_id] = wp_bad

    if not stale_refs:
        return

    # Surface the parsed spec FR set and classify each offender so a simple format
    # mismatch (e.g. FR-003a) is obvious rather than looking like invented IDs (#2066).
    stale_ref_reasons = classify_stale_refs(stale_refs, post_merge_malformed)
    parsed_spec_ids = sorted(st.all_spec_ids)
    payload = {
        "error": "Stale or invalid refs in WP frontmatter",
        "stale_refs": stale_refs,
        "stale_ref_reasons": stale_ref_reasons,
        "parsed_spec_ids": parsed_spec_ids,
        "hint": (
            "Requirement IDs must match FR-NNN, NFR-NNN, or C-NNN "
            "(e.g. FR-003, not FR-003a). 'malformed' refs violate that format; "
            "'unknown_spec_id' refs are well-formed but not declared in spec.md "
            "(see parsed_spec_ids). Re-run with --replace to correct, "
            "e.g.: map-requirements --wp WP01 --refs FR-001 --replace"
        ),
    }
    if st.json_output:
        render = _tasks.RealRender()
        print(render.json_envelope(payload))
    else:
        _tasks.console.print("[red]Error:[/red] Stale or invalid refs in WP frontmatter:")
        _tasks.console.print("  IDs must match FR-NNN, NFR-NNN, or C-NNN (e.g. FR-003, not FR-003a).")
        for wp_id, bad_refs in sorted(stale_refs.items()):
            _tasks.console.print(f"  {wp_id}: {', '.join(bad_refs)}")
        _tasks.console.print(f"  Parsed spec IDs: {', '.join(parsed_spec_ids) or '(none)'}")
        _tasks.console.print("  Use --replace to correct mappings")
    raise typer.Exit(1)


def _mr_auto_commit(st: _MapReqState, ports: TasksPorts) -> None:
    """Phase F(i): route the WP-file auto-commit through the WP02 ``commit_artifact`` port.

    map-requirements edits WP prompt files → WORK_PACKAGE_TASK (a primary kind,
    write-surface-coherence WP03 / T014). The coord router carries the resolved
    ``target_branch`` so the WP09 ff-advance fires for a coord write; the ``--json``
    ``commit_result`` envelope shape (#1891 / FR-013) is reconstructed byte-identically.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    if not st.auto_commit_on:
        return
    written_files: list[Path] = []
    for wp_id in st.new_mappings:
        wp_file = next((f for f in st.tasks_dir.glob(f"{wp_id}*.md")), None)
        if wp_file is not None:
            written_files.append(wp_file.resolve())
    if not written_files:
        return
    spec_number = st.mission_slug.split("-")[0] if "-" in st.mission_slug else st.mission_slug
    commit_msg = f"chore: Map requirements for {', '.join(sorted(st.new_mappings))} on spec {spec_number}"
    handle = MissionHandle(repo_root=st.main_repo_root, mission_slug=st.mission_slug)
    try:
        _router_result = ports.coord.commit_artifact(
            handle,
            tuple(written_files),
            commit_msg,
            kind=MissionArtifactKind.WORK_PACKAGE_TASK,
            policy=_tasks.ProtectionPolicy.resolve(st.main_repo_root),
        )
        if _router_result.status == "committed":
            st.committed = True
            st.commit_sha = _router_result.commit_hash
            st.commit_result_payload = {
                "sha": _router_result.commit_hash or "",
                "destination_ref": _router_result.placement_ref,
                "worktree_root": str(st.main_repo_root),
            }
    except Exception as exc_commit:
        if not st.json_output:
            _tasks.console.print(f"[yellow]Warning:[/yellow] Auto-commit skipped: {exc_commit}")


def _mr_emit_output(st: _MapReqState) -> None:
    """Phase F(ii): reconstruct coverage from the core + emit the success envelope."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    from specify_cli.requirement_mapping import read_all_wp_requirement_refs

    assert st.mapping_plan is not None
    # ``total_mappings`` reflects the post-write disk state (unchanged read). The
    # coverage summary is reconstructed from the core's ``unmapped_fr``: every
    # functional FR is either mapped or unmapped, so ``mapped = total - len(unmapped)``
    # is byte-identical to ``compute_coverage`` over the post-write state (WP04).
    all_wp_refs = read_all_wp_requirement_refs(st.tasks_dir)
    coverage: CoverageSummary = {
        "total_functional": len(st.functional_ids),
        "mapped_functional": len(st.functional_ids) - len(st.mapping_plan.unmapped_fr),
        "unmapped_functional": st.mapping_plan.unmapped_fr,
    }
    st.coverage = coverage

    payload = {
        "result": "success",
        **_tasks._mission_identity_payload(st.primary_dir),
        "mapped": {wp_id: sorted(refs) for wp_id, refs in st.new_mappings.items()},
        "total_mappings": {wp_id: sorted(refs) for wp_id, refs in all_wp_refs.items() if refs},
        "coverage": coverage,
        "committed": st.committed,
        "commit_sha": st.commit_sha,
        "commit_result": st.commit_result_payload,
    }
    if st.json_output:
        render = _tasks.RealRender()
        print(render.json_envelope(payload))
    else:
        _tasks.console.print("[green]✓[/green] Requirement mappings saved")
        for wp_id, ref_list in sorted(st.new_mappings.items()):
            _tasks.console.print(f"  {wp_id}: {', '.join(ref_list)}")
        _tasks.console.print(f"\n  Coverage: {coverage['mapped_functional']}/{coverage['total_functional']} FRs mapped")
        if coverage["unmapped_functional"]:
            _tasks.console.print(f"  [yellow]Unmapped:[/yellow] {', '.join(coverage['unmapped_functional'])}")
        if st.committed:
            _tasks.console.print("[cyan]→ Committed mapping changes[/cyan]")


def _do_map_requirements(
    wp: str | None,
    refs: str | None,
    batch: str | None,
    replace: bool,
    tracker_ref: list[str] | None,
    mission: str | None,
    json_output: bool,
    auto_commit: bool | None,
    *,
    ports: TasksPorts | None = None,
) -> None:
    """Orchestrate ``map-requirements`` over the WP04 core + WP02 ports (C-005 seam).

    ``ports=None`` builds the production bundle AFTER ``target_branch`` resolves
    (the coord router threads it for the ff-advance). Tests inject a Fake bundle to
    observe the executed side-effects (T032). The phase helpers run in the SAME
    order as the original single body: validate → resolve → plan → write → stale
    gate → finalize — so the frontmatter write still precedes the post-write stale
    gate (partial-write-on-refusal timing, NFR-001/WP04).
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    st = _MapReqState(
        wp=wp,
        refs=refs,
        batch=batch,
        replace=replace,
        tracker_ref=tracker_ref,
        mission=mission,
        json_output=json_output,
        auto_commit=auto_commit,
    )
    try:
        _mr_validate_modes(st)
        _mr_resolve_context(st)
        ports = ports or _default_map_requirements_ports(st.target_branch)
        _mr_resolve_read_dirs(st, ports)
        _mr_plan(st)
        _mr_gate_offenders(st)
        _mr_write_frontmatter(st)
        _mr_stale_gate(st)
        _mr_auto_commit(st, ports)
        _mr_emit_output(st)
    except typer.Exit:
        raise
    except Exception as exc:
        _tasks._output_error(json_output, str(exc))
        raise typer.Exit(1) from None


# ===========================================================================
# WP09 (tasks-py-degod-wave2-01KWH9EQ / FR-008, IC-07): the final
# registration-shim sweep relocates the map_requirements-family straggler that
# remained ``tasks.py``-resident after WP06 — the kind-aware ``tasks/`` read
# resolver (``_map_requirements_feature_dir``). Moved VERBATIM
# (``resolve_planning_read_dir`` / ``MissionArtifactKind`` are module-scope
# imports here already; neither is a ``tasks``-namespace patch seam). The
# ``_mr_resolve_read_dirs`` call site above keeps routing through
# ``_tasks.<attr>``, so the pre30-guard-wiring / read-surface
# ``@patch("...agent.tasks._map_requirements_feature_dir")`` contracts keep
# INTERCEPTING; ``tasks.py`` re-imports the name in the explicit ``as``
# re-export form (NFR-002).
# ===========================================================================


def _map_requirements_feature_dir(main_repo_root: Path, mission_slug: str) -> Path:
    """Resolve the WP ``tasks/`` read surface for ``map-requirements`` (#2064).

    Routes through ``resolve_planning_read_dir(kind=WORK_PACKAGE_TASK)`` — the
    per-leg seam split (WP03 / FR-001 / C-001): the WP-frontmatter read always
    lands on the PRIMARY checkout regardless of topology (INV-5 symmetry), so a
    coord-topology mission no longer routes to the STATUS-only coord husk for this
    planning-artifact read.

    ``resolve_planning_read_dir`` delegates to the topology-blind
    :func:`primary_feature_dir_for_mission`, which never raises — preserving the
    user-facing contract that ``map-requirements`` surfaces its own
    ``"Mission directory not found: …"`` message via the caller's existence guard
    on the returned path (Risk #1 — unchanged user-facing behaviour).
    """
    # WP03 / FR-001 / C-001: tasks/ is WORK_PACKAGE_TASK (PRIMARY-partition).
    # The topology-blind primary_feature_dir_for_mission never raises, so the
    # caller's existence guard preserves the historical user-facing contract.
    resolved: Path = resolve_planning_read_dir(
        main_repo_root, mission_slug, kind=MissionArtifactKind.WORK_PACKAGE_TASK
    )
    return resolved
