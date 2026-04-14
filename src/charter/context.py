"""Charter context bootstrap for prompt generation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from charter.resolver import GovernanceResolutionError, resolve_governance
from kernel.atomic import atomic_write


BOOTSTRAP_ACTIONS: frozenset[str] = frozenset({"specify", "plan", "implement", "review"})


@dataclass(frozen=True)
class CharterContextResult:
    """Rendered charter context payload."""

    action: str
    mode: str
    first_load: bool
    text: str
    references_count: int
    depth: int


def _build_doctrine_service(repo_root: Path) -> object:
    """Build a DoctrineService for the given repo root."""
    from doctrine.service import DoctrineService
    from charter.catalog import resolve_doctrine_root

    doctrine_root = resolve_doctrine_root()
    project_root_candidates = [repo_root / "src" / "doctrine", repo_root / "doctrine"]
    project_root = next((path for path in project_root_candidates if path.is_dir()), None)
    return DoctrineService(shipped_root=doctrine_root, project_root=project_root)


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
        "Charter Context (Bootstrap):",
        f"  - Source: {charter_path}",
        "  - This is the first load for this action. Use the summary and follow references as needed.",
        "",
        "Policy Summary:",
    ]

    if summary:
        for item in summary[:8]:
            lines.append(f"  - {item}")
    else:
        lines.append("  - No explicit policy summary section found in charter.md.")

    lines.append("")

    _append_action_doctrine_lines(lines, repo_root, action, include_extended=include_extended)

    lines.append("")

    # --- Reference Docs section ---
    lines.append("Reference Docs:")

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
        "Charter Context (Bootstrap):",
        f"  - Source: {charter_path}",
        "  - This is the first load for this action. Use the summary and follow references as needed.",
        "",
        "Policy Summary:",
    ]

    if summary:
        for item in summary[:8]:
            lines.append(f"  - {item}")
    else:
        lines.append("  - No explicit policy summary section found in charter.md.")

    lines.append("")
    lines.append("Reference Docs:")
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

    paradigms = ", ".join(resolution.paradigms) if resolution.paradigms else "(none)"
    directives = ", ".join(resolution.directives) if resolution.directives else "(none)"
    tools = ", ".join(resolution.tools) if resolution.tools else "(none)"

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


def _mark_action_loaded(
    state: dict[str, object], state_path: Path, action: str
) -> None:
    """Persist first-load timestamp for *action* into context-state.json."""
    actions_obj = state.setdefault("actions", {})
    if not isinstance(actions_obj, dict):
        actions_obj = {}
        state["actions"] = actions_obj
    actions_obj[action] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    _write_state(state_path, state)


# ---------------------------------------------------------------------------
# build_charter_context -- DRG-based context assembly
# ---------------------------------------------------------------------------


def build_charter_context(
    repo_root: Path,
    *,
    profile: str | None = None,
    action: str,
    mark_loaded: bool = True,
    depth: int | None = None,
) -> CharterContextResult:
    """Build charter context by querying the Doctrine Reference Graph.

    Composes DRG query primitives from :mod:`doctrine.drg.query` -- does
    NOT embed graph traversal logic. The pre-WP03 legacy implementation
    has been deleted as part of the
    ``excise-doctrine-curation-and-inline-references-01KP54J6`` mission.

    Args:
        repo_root: Repository root directory.
        profile: Agent profile name. Accepted for forward compatibility
            (Phase 4 will add profile-based edge filtering) but currently
            unused.
        action: Workflow action name (e.g. ``"specify"``, ``"implement"``).
        mark_loaded: Whether to persist first-load state.
        depth: Context depth override. ``None`` lets state decide:
            first_load -> 2 (bootstrap), not first_load -> 1 (compact).
            Explicit depth wins but does not suppress state update.

    Returns:
        :class:`CharterContextResult` with rendered governance text.
    """
    # Lazy imports to avoid circular dependency on module load.
    from charter.catalog import resolve_doctrine_root
    from charter.sync import load_governance_config
    from doctrine.drg.loader import load_graph, merge_layers
    from doctrine.drg.models import NodeKind
    from doctrine.drg.query import resolve_context
    from doctrine.drg.validator import assert_valid
    from doctrine.missions import MissionTemplateRepository
    from doctrine.service import DoctrineService

    normalized = action.strip().lower()
    charter_path = repo_root / ".kittify" / "charter" / "charter.md"
    references_path = repo_root / ".kittify" / "charter" / "references.yaml"

    # -- 0. State management (mirrors build_charter_context) ------------------
    # Non-bootstrap actions always get compact governance.
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

    state_path = repo_root / ".kittify" / "charter" / "context-state.json"
    state = _load_state(state_path)
    actions_val = state.get("actions", {})
    first_load = normalized not in actions_val if isinstance(actions_val, dict) else True

    effective_depth = depth if depth is not None else 2 if first_load else 1

    # Charter missing -> early return
    if not charter_path.exists():
        text = (
            "Charter Context:\n"
            "  - Charter file not found at `.kittify/charter/charter.md`.\n"
            "  - Run `spec-kitty charter interview` then `spec-kitty charter generate`."
        )
        return CharterContextResult(
            action=normalized,
            mode="missing",
            first_load=first_load,
            text=text,
            references_count=0,
            depth=effective_depth,
        )

    # Compact mode for subsequent loads
    if effective_depth < 2:
        if mark_loaded and first_load:
            _mark_action_loaded(state, state_path, normalized)
        return CharterContextResult(
            action=normalized,
            mode="compact",
            first_load=first_load,
            text=_render_compact_governance(repo_root),
            references_count=0,
            depth=effective_depth,
        )

    # -- 1. Load merged DRG + validate ---------------------------------------
    doctrine_root = resolve_doctrine_root()
    shipped_graph = load_graph(doctrine_root / "graph.yaml")

    project_graph_path = repo_root / ".kittify" / "doctrine" / "graph.yaml"
    project_graph = load_graph(project_graph_path) if project_graph_path.exists() else None
    merged = merge_layers(shipped_graph, project_graph)
    assert_valid(merged)  # P1 fix: reject dangling refs, cycles, duplicates

    # -- 2. Resolve mission + project directive selection ---------------------
    governance = load_governance_config(repo_root)
    template_set = governance.doctrine.template_set or "software-dev-default"
    mission = template_set.removesuffix("-default")

    # Project directive selection filtering (mirrors legacy behavior)
    project_directives: set[str] = {
        _normalize_directive_id(d) for d in governance.doctrine.selected_directives
    }

    # -- 3. Query the DRG -----------------------------------------------------
    action_urn = f"action:{mission}/{normalized}"
    resolved = resolve_context(merged, action_urn, depth=effective_depth)

    # -- 4. Materialize artifacts via DoctrineService -------------------------
    project_root_candidates = [
        repo_root / "src" / "doctrine",
        repo_root / "doctrine",
    ]
    project_root = next(
        (p for p in project_root_candidates if p.is_dir()), None
    )
    svc = DoctrineService(shipped_root=doctrine_root, project_root=project_root)

    # Classify resolved URNs by node kind, applying directive selection
    directive_ids: list[str] = []
    tactic_ids: list[str] = []
    styleguide_ids: list[str] = []
    toolguide_ids: list[str] = []

    for urn in sorted(resolved.artifact_urns):
        node = merged.get_node(urn)
        if node is None:
            continue
        artifact_id = urn.split(":", 1)[1] if ":" in urn else urn
        if node.kind == NodeKind.DIRECTIVE:
            # Apply project directive selection (empty set = no filtering)
            if project_directives and artifact_id not in project_directives:
                continue
            directive_ids.append(artifact_id)
        elif node.kind == NodeKind.TACTIC:
            tactic_ids.append(artifact_id)
        elif node.kind == NodeKind.STYLEGUIDE:
            styleguide_ids.append(artifact_id)
        elif node.kind == NodeKind.TOOLGUIDE:
            toolguide_ids.append(artifact_id)

    # -- 5. Render formatted text ---------------------------------------------
    charter_content = charter_path.read_text(encoding="utf-8")
    summary = _extract_policy_summary(charter_content)

    lines: list[str] = [
        "Charter Context (Bootstrap):",
        f"  - Source: {charter_path}",
        "  - This is the first load for this action. Use the summary and follow references as needed.",
        "",
        "Policy Summary:",
    ]

    if summary:
        for item in summary[:8]:
            lines.append(f"  - {item}")
    else:
        lines.append("  - No explicit policy summary section found in charter.md.")

    lines.append("")

    # Action Doctrine section
    lines.append(f"Action Doctrine ({normalized}):")

    # Directives
    directive_lines: list[str] = []
    for d_id in directive_ids:
        directive = svc.directives.get(d_id)
        if directive is not None:
            directive_lines.append(f"    - {d_id}: {directive.title} — {directive.intent}")
        else:
            directive_lines.append(f"    - {d_id}")
    if directive_lines:
        lines.append("  Directives:")
        lines.extend(directive_lines)

    # Tactics
    tactic_lines: list[str] = []
    for t_id in tactic_ids:
        tactic = svc.tactics.get(t_id)
        if tactic is not None:
            desc = tactic.purpose or ""
            tactic_lines.append(f"    - {t_id}: {tactic.name} — {desc}".rstrip(" —"))
        else:
            tactic_lines.append(f"    - {t_id}")
    if tactic_lines:
        lines.append("  Tactics:")
        lines.extend(tactic_lines)

    # Extended sections (depth >= 3)
    if effective_depth >= 3:
        sg_lines: list[str] = []
        for sg_id in styleguide_ids:
            sg = svc.styleguides.get(sg_id)
            sg_lines.append(f"    - {sg_id}: {sg.title}" if sg else f"    - {sg_id}")
        if sg_lines:
            lines.append("  Styleguides:")
            lines.extend(sg_lines)

        tg_lines: list[str] = []
        for tg_id in toolguide_ids:
            tg = svc.toolguides.get(tg_id)
            tg_lines.append(f"    - {tg_id}: {tg.title}" if tg else f"    - {tg_id}")
        if tg_lines:
            lines.append("  Toolguides:")
            lines.extend(tg_lines)

    # Action guidelines (mirrors legacy _append_action_doctrine_lines)
    try:
        repo = MissionTemplateRepository.default()
        guidelines_result = repo.get_action_guidelines(mission, normalized)
        if guidelines_result is not None:
            guidelines_content = guidelines_result.content.strip()
            if guidelines_content:
                lines.append("  Guidelines:")
                for gl_line in guidelines_content.splitlines():
                    lines.append(f"    {gl_line}")
    except Exception:  # noqa: BLE001, S110
        pass  # Degrade gracefully, matching legacy behavior

    lines.append("")

    # Reference Docs section
    lines.append("Reference Docs:")
    references = _load_references(references_path)
    filtered_references = _filter_references_for_action(references, normalized)
    if filtered_references:
        for reference in filtered_references[:10]:
            ref_id = reference.get("id", "unknown")
            title = reference.get("title", "")
            local_path = reference.get("local_path", "")
            lines.append(f"  - {ref_id}: {title} ({local_path})")
    else:
        lines.append("  - No references manifest found.")

    text = "\n".join(lines)

    # Update first-load state
    if mark_loaded and first_load:
        _mark_action_loaded(state, state_path, normalized)

    return CharterContextResult(
        action=normalized,
        mode="bootstrap",
        first_load=first_load,
        text=text,
        references_count=len(references),
        depth=effective_depth,
    )
