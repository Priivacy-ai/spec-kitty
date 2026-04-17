"""Charter context bootstrap for prompt generation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from charter.language_scope import infer_repo_languages
from charter.resolver import GovernanceResolutionError, resolve_governance
from kernel.atomic import atomic_write


BOOTSTRAP_ACTIONS: frozenset[str] = frozenset({"specify", "plan", "implement", "review"})
BOOTSTRAP_HEADER = "Charter Context (Bootstrap):"
FIRST_LOAD_GUIDANCE = (
    "  - This is the first load for this action. Use the summary and follow references as needed."
)
POLICY_SUMMARY_HEADER = "Policy Summary:"
NO_POLICY_SUMMARY_MESSAGE = "  - No explicit policy summary section found in charter.md."
REFERENCE_DOCS_HEADER = "Reference Docs:"
NONE_LABEL = "(none)"

_MIN_EFFECTIVE_DEPTH = 2   # minimum depth for bootstrap context (full summary + references)
_EXTENDED_CONTEXT_DEPTH = 3  # depth that includes extended styleguide/toolguide lines


@dataclass(frozen=True)
class CharterContextResult:
    """Rendered charter context payload."""

    action: str
    mode: str
    first_load: bool
    text: str
    references_count: int
    depth: int


@dataclass(frozen=True)
class _ContextStateBundle:
    """First-load state bundle used while rendering charter context."""

    state_path: Path
    state: dict[str, object]
    first_load: bool
    effective_depth: int


@dataclass(frozen=True)
class _ActionDoctrineBundle:
    """Resolved action doctrine artifacts for bootstrap rendering."""

    mission: str
    directive_ids: list[str]
    tactic_ids: list[str]
    styleguide_ids: list[str]
    toolguide_ids: list[str]
    service: object


def build_charter_context(
    repo_root: Path,
    *,
    profile: str | None = None,
    action: str,
    mark_loaded: bool = True,
    depth: int | None = None,
) -> CharterContextResult:
    """Build charter context by querying the Doctrine Reference Graph."""
    _ = profile

    from charter.sync import ensure_charter_bundle_fresh

    sync_result = ensure_charter_bundle_fresh(repo_root)
    canonical_root = sync_result.canonical_root if sync_result and sync_result.canonical_root else repo_root

    normalized = action.strip().lower()
    charter_path = canonical_root / ".kittify" / "charter" / "charter.md"
    references_path = canonical_root / ".kittify" / "charter" / "references.yaml"

    if normalized not in BOOTSTRAP_ACTIONS:
        effective_depth = depth if depth is not None else 1
        return CharterContextResult(
            action=normalized,
            mode="compact",
            first_load=False,
            text=_render_compact_governance(repo_root),
            references_count=0,
            depth=effective_depth,
        )

    state_bundle = _prepare_context_state(repo_root, normalized, depth)

    if not charter_path.exists():
        text = (
            "Charter Context:\n"
            "  - Charter file not found at `.kittify/charter/charter.md`.\n"
            "  - Run `spec-kitty charter interview` then `spec-kitty charter generate`."
        )
        return CharterContextResult(
            action=normalized,
            mode="missing",
            first_load=state_bundle.first_load,
            text=text,
            references_count=0,
            depth=state_bundle.effective_depth,
        )

    if state_bundle.effective_depth < _MIN_EFFECTIVE_DEPTH:
        if mark_loaded and state_bundle.first_load:
            _mark_action_loaded(state_bundle.state, state_bundle.state_path, normalized)
        return CharterContextResult(
            action=normalized,
            mode="compact",
            first_load=state_bundle.first_load,
            text=_render_compact_governance(repo_root),
            references_count=0,
            depth=state_bundle.effective_depth,
        )

    doctrine_bundle = _load_action_doctrine_bundle(
        repo_root=repo_root,
        action=normalized,
        effective_depth=state_bundle.effective_depth,
    )
    charter_content = charter_path.read_text(encoding="utf-8")
    summary = _extract_policy_summary(charter_content)
    references = _load_references(references_path)
    text = _render_bootstrap_text(
        charter_path=charter_path,
        action=normalized,
        summary=summary,
        doctrine_bundle=doctrine_bundle,
        references=references,
        effective_depth=state_bundle.effective_depth,
    )

    if mark_loaded and state_bundle.first_load:
        _mark_action_loaded(state_bundle.state, state_bundle.state_path, normalized)

    return CharterContextResult(
        action=normalized,
        mode="bootstrap",
        first_load=state_bundle.first_load,
        text=text,
        references_count=len(references),
        depth=state_bundle.effective_depth,
    )


def _prepare_context_state(
    repo_root: Path,
    action: str,
    depth: int | None,
) -> _ContextStateBundle:
    """Resolve first-load state and effective context depth."""
    state_path = repo_root / ".kittify" / "charter" / "context-state.json"
    state = _load_state(state_path)
    actions_val = state.get("actions", {})
    first_load = action not in actions_val if isinstance(actions_val, dict) else True
    if depth is not None:
        effective_depth = depth
    elif first_load:
        effective_depth = _MIN_EFFECTIVE_DEPTH
    else:
        effective_depth = 1
    return _ContextStateBundle(
        state_path=state_path,
        state=state,
        first_load=first_load,
        effective_depth=effective_depth,
    )


def _classify_artifact_urns(
    artifact_urns: set[str],
    merged: object,
    project_directives: set[str],
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Partition resolved artifact URNs into doctrine-type buckets."""
    from doctrine.drg.models import NodeKind

    directive_ids: list[str] = []
    tactic_ids: list[str] = []
    styleguide_ids: list[str] = []
    toolguide_ids: list[str] = []
    for urn in sorted(artifact_urns):
        node = merged.get_node(urn)  # type: ignore[attr-defined]
        if node is None:
            continue
        artifact_id = urn.split(":", 1)[1] if ":" in urn else urn
        if node.kind == NodeKind.DIRECTIVE:
            if project_directives and artifact_id not in project_directives:
                continue
            directive_ids.append(artifact_id)
        elif node.kind == NodeKind.TACTIC:
            tactic_ids.append(artifact_id)
        elif node.kind == NodeKind.STYLEGUIDE:
            styleguide_ids.append(artifact_id)
        elif node.kind == NodeKind.TOOLGUIDE:
            toolguide_ids.append(artifact_id)
    return directive_ids, tactic_ids, styleguide_ids, toolguide_ids


def _load_action_doctrine_bundle(
    *,
    repo_root: Path,
    action: str,
    effective_depth: int,
) -> _ActionDoctrineBundle:
    """Load DRG-backed action doctrine artifacts for bootstrap rendering."""
    from charter.catalog import resolve_doctrine_root
    from charter.sync import load_governance_config
    from doctrine.drg.loader import load_graph, merge_layers
    from doctrine.drg.query import resolve_context
    from doctrine.drg.validator import assert_valid

    doctrine_root = resolve_doctrine_root()
    shipped_graph = load_graph(doctrine_root / "graph.yaml")
    project_graph_path = repo_root / ".kittify" / "doctrine" / "graph.yaml"
    project_graph = load_graph(project_graph_path) if project_graph_path.exists() else None
    merged = merge_layers(shipped_graph, project_graph)
    assert_valid(merged)

    governance = load_governance_config(repo_root)
    mission = (governance.doctrine.template_set or "software-dev-default").removesuffix("-default")
    project_directives = {_normalize_directive_id(d) for d in governance.doctrine.selected_directives}
    action_urn = f"action:{mission}/{action}"
    resolved = resolve_context(merged, action_urn, depth=effective_depth)

    directive_ids, tactic_ids, styleguide_ids, toolguide_ids = _classify_artifact_urns(
        resolved.artifact_urns, merged, project_directives
    )
    return _ActionDoctrineBundle(
        mission=mission,
        directive_ids=directive_ids,
        tactic_ids=tactic_ids,
        styleguide_ids=styleguide_ids,
        toolguide_ids=toolguide_ids,
        service=_build_doctrine_service(repo_root),
    )


def _append_guidelines_lines(lines: list[str], mission: str, action: str) -> None:
    """Append action guidelines to lines, silently skipping on any error."""
    from doctrine.missions import MissionTemplateRepository

    try:
        repo = MissionTemplateRepository.default()
        result = repo.get_action_guidelines(mission, action)
        if result is not None:
            content = result.content.strip()
            if content:
                lines.append("  Guidelines:")
                for guideline_line in content.splitlines():
                    lines.append(f"    {guideline_line}")
    except Exception:  # noqa: BLE001, S110
        pass


def _render_bootstrap_text(
    *,
    charter_path: Path,
    action: str,
    summary: list[str],
    doctrine_bundle: _ActionDoctrineBundle,
    references: list[dict[str, str]],
    effective_depth: int,
) -> str:
    """Render the full bootstrap charter context text."""

    service = doctrine_bundle.service
    lines: list[str] = [
        BOOTSTRAP_HEADER,
        f"  - Source: {charter_path}",
        FIRST_LOAD_GUIDANCE,
        "",
        POLICY_SUMMARY_HEADER,
    ]
    if summary:
        for item in summary[:8]:
            lines.append(f"  - {item}")
    else:
        lines.append(NO_POLICY_SUMMARY_MESSAGE)

    lines.append("")
    lines.append(f"Action Doctrine ({action}):")
    _extend_named_artifact_lines(lines, "Directives", doctrine_bundle.directive_ids, service.directives, "title", "intent")
    _extend_named_artifact_lines(lines, "Tactics", doctrine_bundle.tactic_ids, service.tactics, "name", "purpose")

    if effective_depth >= _EXTENDED_CONTEXT_DEPTH:
        _extend_named_artifact_lines(lines, "Styleguides", doctrine_bundle.styleguide_ids, service.styleguides, "title", None)
        _extend_named_artifact_lines(lines, "Toolguides", doctrine_bundle.toolguide_ids, service.toolguides, "title", None)

    _append_guidelines_lines(lines, doctrine_bundle.mission, action)

    lines.append("")
    lines.append(REFERENCE_DOCS_HEADER)
    filtered_references = _filter_references_for_action(references, action)
    if filtered_references:
        for reference in filtered_references[:10]:
            ref_id = reference.get("id", "unknown")
            title = reference.get("title", "")
            local_path = reference.get("local_path", "")
            lines.append(f"  - {ref_id}: {title} ({local_path})")
    else:
        lines.append("  - No references manifest found.")
    return "\n".join(lines)


def _extend_named_artifact_lines(
    lines: list[str],
    heading: str,
    artifact_ids: list[str],
    repository: object,
    title_attr: str,
    summary_attr: str | None,
) -> None:
    """Append formatted artifact lines when the bucket is non-empty."""
    if not artifact_ids:
        return

    formatted: list[str] = []
    for artifact_id in artifact_ids:
        artifact = repository.get(artifact_id)
        if artifact is None:
            formatted.append(f"    - {artifact_id}")
            continue
        title = getattr(artifact, title_attr)
        summary = getattr(artifact, summary_attr) if summary_attr else None
        if isinstance(summary, str) and summary:
            formatted.append(f"    - {artifact_id}: {title} — {summary}")
        else:
            formatted.append(f"    - {artifact_id}: {title}")

    lines.append(f"  {heading}:")
    lines.extend(formatted)


def _build_doctrine_service(repo_root: Path) -> object:
    """Build a DoctrineService for the given repo root."""
    from doctrine.service import DoctrineService
    from charter.catalog import resolve_doctrine_root

    doctrine_root = resolve_doctrine_root()
    project_root_candidates = [repo_root / "src" / "doctrine", repo_root / "doctrine"]
    project_root = next((path for path in project_root_candidates if path.is_dir()), None)
    return DoctrineService(
        shipped_root=doctrine_root,
        project_root=project_root,
        active_languages=infer_repo_languages(repo_root),
    )


def _normalize_directive_id(raw: str) -> str:
    """Normalise a directive slug like '024-locality-of-change' -> 'DIRECTIVE_024'.

    If the raw value already looks like DIRECTIVE_NNN, return as-is.
    """
    if re.match(r"^DIRECTIVE_\d+$", raw):
        return raw
    match = re.match(r"^(\d+)", raw)
    if match:
        number = match.group(1).zfill(3)
        return f"DIRECTIVE_{number}"
    return raw.upper()


def _build_directive_lines(
    action_index: object,
    project_directives: set[str],
    doctrine_service: object,
) -> list[str]:
    """Build formatted directive lines for the action doctrine section."""
    directive_lines: list[str] = []
    for raw_id in action_index.directives:  # type: ignore[attr-defined]
        norm_id = _normalize_directive_id(raw_id)
        if project_directives and norm_id not in project_directives:
            continue
        try:
            directive = doctrine_service.directives.get(norm_id)  # type: ignore[attr-defined]
            if directive is not None:
                directive_lines.append(f"    - {norm_id}: {directive.title} — {directive.intent}")
            else:
                directive_lines.append(f"    - {norm_id}")
        except (AttributeError, KeyError):
            directive_lines.append(f"    - {norm_id}")
    return directive_lines


def _build_tactic_lines(action_index: object, doctrine_service: object) -> list[str]:
    """Build formatted tactic lines for the action doctrine section."""
    tactic_lines: list[str] = []
    for tactic_id in action_index.tactics:  # type: ignore[attr-defined]
        try:
            tactic = doctrine_service.tactics.get(tactic_id)  # type: ignore[attr-defined]
            if tactic is not None:
                desc = tactic.description or ""
                tactic_lines.append(f"    - {tactic_id}: {tactic.title} — {desc}".rstrip(" —"))
            else:
                tactic_lines.append(f"    - {tactic_id}")
        except (AttributeError, KeyError):
            tactic_lines.append(f"    - {tactic_id}")
    return tactic_lines


def _build_extended_lines(action_index: object, doctrine_service: object) -> list[str]:
    """Build styleguide + toolguide lines for depth-3 extended context."""
    extended: list[str] = []

    styleguide_lines: list[str] = []
    for sg_id in action_index.styleguides:  # type: ignore[attr-defined]
        try:
            sg = doctrine_service.styleguides.get(sg_id)  # type: ignore[attr-defined]
            styleguide_lines.append(f"    - {sg_id}: {sg.title}" if sg else f"    - {sg_id}")
        except (AttributeError, KeyError):
            styleguide_lines.append(f"    - {sg_id}")

    if styleguide_lines:
        extended.append("  Styleguides:")
        extended.extend(styleguide_lines)

    toolguide_lines: list[str] = []
    for tg_id in action_index.toolguides:  # type: ignore[attr-defined]
        try:
            tg = doctrine_service.toolguides.get(tg_id)  # type: ignore[attr-defined]
            toolguide_lines.append(f"    - {tg_id}: {tg.title}" if tg else f"    - {tg_id}")
        except (AttributeError, KeyError):
            toolguide_lines.append(f"    - {tg_id}")

    if toolguide_lines:
        extended.append("  Toolguides:")
        extended.extend(toolguide_lines)

    return extended


def _append_action_doctrine_lines(
    lines: list[str],
    repo_root: Path,
    action: str,
    *,
    include_extended: bool,
) -> None:
    """Append action doctrine content to lines list. Degrades gracefully on error."""
    from doctrine.missions import MissionTemplateRepository
    from doctrine.missions.action_index import load_action_index
    from charter.sync import load_governance_config

    try:
        repo = MissionTemplateRepository.default()
        governance = load_governance_config(repo_root)
        template_set = governance.doctrine.template_set or "software-dev-default"
        mission = template_set.removesuffix("-default")
        action_index = load_action_index(repo._missions_root, mission, action)
        project_directives: set[str] = {_normalize_directive_id(d) for d in governance.doctrine.selected_directives}
        doctrine_service = _build_doctrine_service(repo_root)

        lines.append(f"Action Doctrine ({action}):")

        directive_lines = _build_directive_lines(action_index, project_directives, doctrine_service)
        if directive_lines:
            lines.append("  Directives:")
            lines.extend(directive_lines)

        tactic_lines = _build_tactic_lines(action_index, doctrine_service)
        if tactic_lines:
            lines.append("  Tactics:")
            lines.extend(tactic_lines)

        if include_extended:
            lines.extend(_build_extended_lines(action_index, doctrine_service))

        # Action guidelines
        guidelines_result = repo.get_action_guidelines(mission, action)
        if guidelines_result is not None:
            guidelines_content = guidelines_result.content.strip()
            if guidelines_content:
                lines.append("  Guidelines:")
                for gl_line in guidelines_content.splitlines():
                    lines.append(f"    {gl_line}")

    except Exception:  # noqa: BLE001, S110
        # Degrade gracefully - skip action doctrine section on any error
        pass


def _render_action_scoped(
    repo_root: Path,
    action: str,
    charter_path: Path,
    summary: list[str],
    references: list[dict[str, str]],
    *,
    include_extended: bool = False,
) -> str:
    """Render action-scoped bootstrap context (depth >= 2).

    Loads the action index, intersects project directives, fetches doctrine
    content, and renders a structured context block.
    """
    lines: list[str] = [
        BOOTSTRAP_HEADER,
        f"  - Source: {charter_path}",
        FIRST_LOAD_GUIDANCE,
        "",
        POLICY_SUMMARY_HEADER,
    ]

    if summary:
        for item in summary[:8]:
            lines.append(f"  - {item}")
    else:
        lines.append(NO_POLICY_SUMMARY_MESSAGE)

    lines.append("")

    _append_action_doctrine_lines(lines, repo_root, action, include_extended=include_extended)

    lines.append("")

    # --- Reference Docs section ---
    lines.append(REFERENCE_DOCS_HEADER)

    filtered_references = _filter_references_for_action(references, action)

    if filtered_references:
        for reference in filtered_references[:10]:
            ref_id = reference.get("id", "unknown")
            title = reference.get("title", "")
            local_path = reference.get("local_path", "")
            lines.append(f"  - {ref_id}: {title} ({local_path})")
    else:
        lines.append("  - No references manifest found.")

    return "\n".join(lines)


def _filter_references_for_action(references: list[dict[str, str]], action: str) -> list[dict[str, str]]:
    """Filter references for a specific action.

    Non-local_support references are always included.
    For local_support references:
      - If the summary contains "(action: XXX)", include only if XXX matches the requested action.
      - If no "(action: ...)" appears in the summary, include (global).
    """
    filtered: list[dict[str, str]] = []
    for ref in references:
        kind = ref.get("kind", "")
        if kind != "local_support":
            filtered.append(ref)
            continue

        # local_support: check summary for action scope
        summary = ref.get("summary", ref.get("title", ""))
        action_match = re.search(r"\(action:\s*(\w+)\)", summary)
        if action_match:
            ref_action = action_match.group(1).strip().lower()
            if ref_action == action.lower():
                filtered.append(ref)
        else:
            # No action scope in summary → include globally
            filtered.append(ref)

    return filtered


def _render_bootstrap(charter_path: Path, summary: list[str], references: list[dict[str, str]]) -> str:
    lines: list[str] = [
        BOOTSTRAP_HEADER,
        f"  - Source: {charter_path}",
        FIRST_LOAD_GUIDANCE,
        "",
        POLICY_SUMMARY_HEADER,
    ]

    if summary:
        for item in summary[:8]:
            lines.append(f"  - {item}")
    else:
        lines.append(NO_POLICY_SUMMARY_MESSAGE)

    lines.append("")
    lines.append(REFERENCE_DOCS_HEADER)
    if references:
        for reference in references[:10]:
            ref_id = reference.get("id", "unknown")
            title = reference.get("title", "")
            local_path = reference.get("local_path", "")
            lines.append(f"  - {ref_id}: {title} ({local_path})")
    else:
        lines.append("  - No references manifest found.")

    return "\n".join(lines)


def _render_compact_governance(repo_root: Path) -> str:
    try:
        resolution = resolve_governance(repo_root)
    except GovernanceResolutionError as exc:
        return f"Governance: unresolved ({exc})"
    except Exception as exc:
        return f"Governance: unavailable ({exc})"

    paradigms = ", ".join(resolution.paradigms) if resolution.paradigms else NONE_LABEL
    directives = ", ".join(resolution.directives) if resolution.directives else NONE_LABEL
    tools = ", ".join(resolution.tools) if resolution.tools else NONE_LABEL

    lines = [
        "Governance:",
        f"  - Template set: {resolution.template_set}",
        f"  - Paradigms: {paradigms}",
        f"  - Directives: {directives}",
        f"  - Tools: {tools}",
    ]
    if resolution.diagnostics:
        lines.append(f"  - Diagnostics: {' | '.join(resolution.diagnostics)}")
    return "\n".join(lines)


def _extract_policy_summary(content: str) -> list[str]:
    lines = content.splitlines()
    start = _find_section_start(lines, "## Policy Summary")

    if start is None:
        # Fallback: return the first meaningful bullet points in the document.
        fallback = [line.strip().lstrip("- ").strip() for line in lines if line.strip().startswith("-")]
        return [item for item in fallback if item][:8]

    summary: list[str] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if stripped.startswith("-"):
            summary.append(stripped.lstrip("- ").strip())
    return summary


def _find_section_start(lines: list[str], heading: str) -> int | None:
    for index, line in enumerate(lines):
        if line.strip() == heading:
            return index
    return None


def _load_references(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    yaml = YAML(typ="safe")
    try:
        data = yaml.load(path.read_text(encoding="utf-8")) or {}
    except (YAMLError, UnicodeDecodeError, OSError):
        return []

    raw_references = data.get("references") if isinstance(data, dict) else []
    if not isinstance(raw_references, list):
        return []

    refs: list[dict[str, str]] = []
    for item in raw_references:
        if not isinstance(item, dict):
            continue
        refs.append(
            {
                "id": str(item.get("id", "")),
                "title": str(item.get("title", "")),
                "local_path": str(item.get("local_path", "")),
                "kind": str(item.get("kind", "")),
                "summary": str(item.get("summary", "")),
            }
        )
    return refs


def _load_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"schema_version": "1.0.0", "actions": {}}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return {"schema_version": "1.0.0", "actions": {}}

    if not isinstance(data, dict):
        return {"schema_version": "1.0.0", "actions": {}}

    actions = data.get("actions")
    if not isinstance(actions, dict):
        data["actions"] = {}

    return data


def _write_state(path: Path, state: dict[str, object]) -> None:
    atomic_write(path, json.dumps(state, indent=2, sort_keys=True), mkdir=True)


def _mark_action_loaded(state: dict[str, object], state_path: Path, action: str) -> None:
    """Persist first-load timestamp for *action* into context-state.json."""
    actions_obj = state.setdefault("actions", {})
    if not isinstance(actions_obj, dict):
        actions_obj = {}
        state["actions"] = actions_obj
    actions_obj[action] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    _write_state(state_path, state)
