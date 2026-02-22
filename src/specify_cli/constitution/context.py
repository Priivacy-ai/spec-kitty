"""Constitution context bootstrap for prompt generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ruamel.yaml import YAML

from specify_cli.constitution.resolver import GovernanceResolutionError, resolve_governance


BOOTSTRAP_ACTIONS: frozenset[str] = frozenset({"specify", "plan", "implement", "review"})


@dataclass(frozen=True)
class ConstitutionContextResult:
    """Rendered constitution context payload."""

    action: str
    mode: str
    first_load: bool
    text: str
    references_count: int


def build_constitution_context(
    repo_root: Path,
    *,
    action: str,
    mark_loaded: bool = True,
) -> ConstitutionContextResult:
    """Build constitution context text for a command action.

    For first load of bootstrap actions, include summary + references.
    For later loads (or non-bootstrap actions), include compact governance context.
    """
    normalized = action.strip().lower()
    constitution_path = repo_root / ".kittify" / "constitution" / "constitution.md"
    references_path = repo_root / ".kittify" / "constitution" / "references.yaml"

    if normalized not in BOOTSTRAP_ACTIONS:
        return ConstitutionContextResult(
            action=normalized,
            mode="compact",
            first_load=False,
            text=_render_compact_governance(repo_root),
            references_count=0,
        )

    state_path = repo_root / ".kittify" / "constitution" / "context-state.json"
    state = _load_state(state_path)
    first_load = normalized not in state.get("actions", {})

    references = _load_references(references_path)

    if not constitution_path.exists():
        text = (
            "Constitution Context:\n"
            "  - Constitution file not found at `.kittify/constitution/constitution.md`.\n"
            "  - Run `spec-kitty constitution interview` then `spec-kitty constitution generate`."
        )
        mode = "missing"
    elif first_load:
        constitution_content = constitution_path.read_text(encoding="utf-8")
        summary = _extract_policy_summary(constitution_content)
        text = _render_bootstrap(constitution_path, summary, references)
        mode = "bootstrap"
    else:
        text = _render_compact_governance(repo_root)
        mode = "compact"

    if mark_loaded and first_load and mode != "missing":
        actions = state.setdefault("actions", {})
        actions[normalized] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        _write_state(state_path, state)

    return ConstitutionContextResult(
        action=normalized,
        mode=mode,
        first_load=first_load,
        text=text,
        references_count=len(references),
    )


def _render_bootstrap(constitution_path: Path, summary: list[str], references: list[dict[str, str]]) -> str:
    lines: list[str] = [
        "Constitution Context (Bootstrap):",
        f"  - Source: {constitution_path}",
        "  - This is the first load for this action. Use the summary and follow references as needed.",
        "",
        "Policy Summary:",
    ]

    if summary:
        for item in summary[:8]:
            lines.append(f"  - {item}")
    else:
        lines.append("  - No explicit policy summary section found in constitution.md.")

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
    except Exception:
        return []

    raw_references = data.get("references") if isinstance(data, dict) else []
    if not isinstance(raw_references, list):
        return []

    refs: list[dict[str, str]] = []
    for item in raw_references:
        if not isinstance(item, dict):
            continue
        refs.append({
            "id": str(item.get("id", "")),
            "title": str(item.get("title", "")),
            "local_path": str(item.get("local_path", "")),
        })
    return refs


def _load_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"schema_version": "1.0.0", "actions": {}}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"schema_version": "1.0.0", "actions": {}}

    if not isinstance(data, dict):
        return {"schema_version": "1.0.0", "actions": {}}

    actions = data.get("actions")
    if not isinstance(actions, dict):
        data["actions"] = {}

    return data


def _write_state(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
