"""Generate dashboard-style DocFX pages from kitty-specs."""

from __future__ import annotations

import html
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "kitty-specs"
DEST = ROOT / "docs" / "kitty-specs"

LANES = ["planned", "doing", "for_review", "approved", "done"]
LANE_LABELS = {
    "planned": "📋 Planned",
    "doing": "🚀 Doing",
    "for_review": "👀 For Review",
    "approved": "👍 Approved",
    "done": "✅ Done",
}
ARTIFACTS = [
    ("overview", "Overview", "📊", None),
    ("spec", "Specification", "📄", "spec.md"),
    ("plan", "Implementation Plan", "🏗️", "plan.md"),
    ("tasks", "Task List", "📋", "tasks.md"),
    ("kanban", "Kanban Board", "🎯", None),
    ("research", "Research", "🔬", "research.md"),
    ("contracts", "Contracts", "📜", "contracts"),
    ("checklists", "Checklists", "✅", "checklists"),
    ("quickstart", "Quickstart Guide", "🚀", "quickstart.md"),
    ("data-model", "Data Model", "💾", "data-model.md"),
]


@dataclass(frozen=True)
class Mission:
    slug: str
    name: str
    meta: dict[str, Any]
    status: dict[str, Any]
    path: Path
    task_titles: dict[str, str]


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def mission_name(path: Path, meta: dict[str, Any]) -> str:
    return (
        meta.get("friendly_name")
        or meta.get("name")
        or meta.get("mission_slug")
        or meta.get("slug")
        or path.name
    )


def sort_key(mission: Mission) -> tuple[int, str]:
    number = mission.meta.get("mission_number")
    try:
        return (-int(number), mission.name.lower())
    except (TypeError, ValueError):
        created = str(mission.meta.get("created_at") or "")
        return (0, f"{created} {mission.name}".lower())


def parse_task_titles(tasks_md: str) -> dict[str, str]:
    titles: dict[str, str] = {}
    for line in tasks_md.splitlines():
        match = re.match(r"^#{2,4}\s+(?:Work Package\s+)?(WP\d+)\s*:?\s*(.+?)\s*$", line)
        if match:
            titles[match.group(1)] = re.sub(r"\s+", " ", match.group(2)).strip()
    return titles


def missions() -> list[Mission]:
    result: list[Mission] = []
    for path in SOURCE.iterdir():
        if not path.is_dir():
            continue
        meta = read_json(path / "meta.json")
        status = read_json(path / "status.json")
        if not meta and not status and not (path / "spec.md").exists():
            continue
        result.append(
            Mission(
                slug=path.name,
                name=mission_name(path, meta),
                meta=meta,
                status=status,
                path=path,
                task_titles=parse_task_titles(read_text(path / "tasks.md")),
            )
        )
    return sorted(result, key=sort_key)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def inline_md(text: str) -> str:
    value = esc(text)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", value)
    value = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<span class="sk-source-link" title="\2">\1</span>',
        value,
    )
    return value


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    in_code = False
    code_lang = ""
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            blocks.append(f"<p>{inline_md(' '.join(paragraph).strip())}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            blocks.append("<ul>" + "".join(f"<li>{item}</li>" for item in list_items) + "</ul>")
            list_items = []

    for raw in lines:
        line = raw.rstrip()
        if line.startswith("```"):
            if in_code:
                blocks.append(
                    f'<pre><code class="language-{esc(code_lang)}">{esc(chr(10).join(code_lines))}</code></pre>'
                )
                in_code = False
                code_lang = ""
                code_lines = []
            else:
                flush_paragraph()
                flush_list()
                in_code = True
                code_lang = line[3:].strip()
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not line.strip():
            flush_paragraph()
            flush_list()
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            flush_list()
            level = min(len(heading.group(1)) + 1, 6)
            blocks.append(f"<h{level}>{inline_md(heading.group(2))}</h{level}>")
            continue
        if re.match(r"^-{3,}$", line):
            flush_paragraph()
            flush_list()
            blocks.append("<hr>")
            continue
        bullet = re.match(r"^\s*[-*]\s+(.+)$", line)
        task = re.match(r"^\s*[-*]\s+\[([ xX])\]\s+(.+)$", line)
        if task:
            flush_paragraph()
            checked = task.group(1).lower() == "x"
            label = "✅" if checked else "□"
            list_items.append(f"{label} {inline_md(task.group(2))}")
            continue
        if bullet:
            flush_paragraph()
            list_items.append(inline_md(bullet.group(1)))
            continue
        paragraph.append(line.strip())
    flush_paragraph()
    flush_list()
    return "\n".join(blocks)


def artifact_exists(mission: Mission, key: str, source: str | None) -> bool:
    if key == "overview":
        return True
    if key == "kanban":
        return bool(mission.status.get("work_packages"))
    if not source:
        return False
    return (mission.path / source).exists()


def artifact_href(mission: Mission, key: str) -> str:
    if key == "overview":
        return "index.html"
    return f"{key}.html"


def dashboard_header(mission_list: list[Mission], active: Mission | None) -> str:
    options = []
    for mission in mission_list:
        selected = " selected" if active and mission.slug == active.slug else ""
        option_href = f"../{mission.slug}/index.html" if active else f"{mission.slug}/index.html"
        options.append(
            f'<option value="{esc(option_href)}"{selected}>{esc(mission.name)}</option>'
        )
    select = "\n".join(options)
    name = active.name if active else "All mission runs"
    return f"""
<div class="sk-dashboard">
  <div class="header">
    <div class="header-left">
      <div class="header-logo-wrapper">
        <img src="/assets/images/logo_small.webp" alt="Spec Kitty logo" class="header-logo">
      </div>
      <div class="header-info">
        <h1>Spec Kitty</h1>
        <pre class="tree-view">└─ kitty-specs
   └─ {esc(name)}</pre>
      </div>
      <div class="feature-selector">
        <label for="feature-select">Mission Run:</label>
        <select id="feature-select" onchange="if (this.value) location.href=this.value">
          {select}
        </select>
      </div>
    </div>
    <div class="header-right">
      <a class="docs-site-link" href="/">📚 Docs ↗</a>
    </div>
  </div>
"""


def sidebar(mission: Mission, active_key: str) -> str:
    items = []
    for key, label, icon, source in ARTIFACTS:
        exists = artifact_exists(mission, key, source)
        active = " active" if key == active_key else ""
        disabled = "" if exists else " disabled"
        if exists:
            items.append(
                f'<a class="sidebar-item{active}" href="{esc(artifact_href(mission, key))}" title="{esc(label)}">'
                f'{icon} <span class="sidebar-label">{esc(label)}</span></a>'
            )
        else:
            items.append(
                f'<span class="sidebar-item{disabled}" title="{esc(label)}">'
                f'{icon} <span class="sidebar-label">{esc(label)}</span></span>'
            )
    return "\n".join(items)


def stats(mission: Mission) -> dict[str, int | float]:
    summary = mission.status.get("summary") or {}
    wps = mission.status.get("work_packages") or {}
    lane_counts = {lane: 0 for lane in LANES}
    for wp in wps.values():
        lane = str(wp.get("lane") or "planned")
        if lane == "in_review":
            lane = "for_review"
        if lane in lane_counts:
            lane_counts[lane] += 1
    for key, value in summary.items():
        normalized = "for_review" if key == "in_review" else key
        if normalized in lane_counts and not wps:
            try:
                lane_counts[normalized] += int(value)
            except (TypeError, ValueError):
                pass
    total = sum(lane_counts.values())
    done = lane_counts["done"]
    pct = round(done / total * 100) if total else 0
    return {"total": total, **lane_counts, "weighted_percentage": pct}


def status_cards(mission: Mission, compact: bool = False) -> str:
    s = stats(mission)
    label = "Total Work Packages" if compact else "Total Tasks"
    return f"""
<div class="status-summary">
  <div class="status-card total"><div class="status-label">{label}</div><div class="status-value">{s['total']}</div><div class="status-detail">{s['planned']} planned</div></div>
  <div class="status-card progress"><div class="status-label">In Progress</div><div class="status-value">{s['doing']}</div></div>
  <div class="status-card review"><div class="status-label">Review</div><div class="status-value">{s['for_review']}</div></div>
  <div class="status-card approved"><div class="status-label">Approved</div><div class="status-value">{s['approved']}</div></div>
  <div class="status-card completed"><div class="status-label">Completed</div><div class="status-value">{s['done']}</div><div class="status-detail">{s['weighted_percentage']}% done</div><div class="progress-bar"><div class="progress-fill" style="width: {s['weighted_percentage']}%"></div></div></div>
</div>
"""


def overview(mission: Mission) -> str:
    purpose_tldr = mission.meta.get("purpose_tldr") or "View and track all artifacts for this mission run."
    purpose_context = mission.meta.get("purpose_context") or mission.meta.get("source_description") or ""
    artifact_rows = []
    for key, label, icon, source in ARTIFACTS[1:]:
        exists = artifact_exists(mission, key, source)
        cls = "available" if exists else "missing"
        text = "✅ Available" if exists else "❌ Not created"
        artifact_rows.append(
            f'<a class="artifact-row {cls}" href="{esc(artifact_href(mission, key))}">{icon} {esc(label)}: {text}</a>'
            if exists
            else f'<div class="artifact-row {cls}">{icon} {esc(label)}: {text}</div>'
        )
    return f"""
<h2>Mission Run Overview</h2>
<div class="overview-header">
  <h3>Mission Run: {esc(mission.name)}</h3>
  <p class="overview-tldr">{esc(purpose_tldr)}</p>
  <p class="overview-context">{esc(purpose_context)}</p>
</div>
{status_cards(mission)}
<h3 class="artifacts-heading">Available Artifacts</h3>
<div class="artifacts-grid">
  {''.join(artifact_rows)}
</div>
"""


def lanes(mission: Mission) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {lane: [] for lane in LANES}
    for wp_id, state in sorted((mission.status.get("work_packages") or {}).items()):
        lane = str(state.get("lane") or "planned")
        if lane == "in_review":
            lane = "for_review"
        if lane not in result:
            lane = "planned"
        result[lane].append(
            {
                "id": wp_id,
                "title": mission.task_titles.get(wp_id, "Work package"),
                "actor": str(state.get("actor") or ""),
            }
        )
    return result


def kanban(mission: Mission) -> str:
    columns = []
    for lane, tasks in lanes(mission).items():
        cards = []
        for task in tasks:
            actor = f'<span class="badge agent">{esc(task["actor"])}</span>' if task["actor"] else ""
            cards.append(
                f'<div class="card"><div class="card-id">{esc(task["id"])}</div>'
                f'<div class="card-title">{esc(task["title"])}</div><div class="card-meta">{actor}</div></div>'
            )
        body = "".join(cards) if cards else '<div class="empty-state">No tasks</div>'
        columns.append(
            f'<div class="lane {lane}"><div class="lane-header"><span>{LANE_LABELS[lane]}</span>'
            f'<span class="count">{len(tasks)}</span></div><div>{body}</div></div>'
        )
    return f"""
<h2>Kanban Board</h2>
<div id="kanban-status">{status_cards(mission, compact=True)}</div>
<div class="kanban-board">{''.join(columns)}</div>
"""


def collection_html(mission: Mission, folder: str) -> str:
    base = mission.path / folder
    if not base.exists():
        return '<div class="empty-state">No files</div>'
    parts = []
    for file_path in sorted(base.rglob("*")):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(base).as_posix()
        parts.append(f"<h3>{esc(rel)}</h3>")
        parts.append(markdown_to_html(read_text(file_path)))
    return "\n".join(parts) if parts else '<div class="empty-state">No files</div>'


def artifact_body(mission: Mission, key: str, source: str | None) -> str:
    if key == "overview":
        return overview(mission)
    if key == "kanban":
        return kanban(mission)
    if source in {"contracts", "checklists"}:
        return f"<h2>{esc(source.title())}</h2>\n{collection_html(mission, source)}"
    text = read_text(mission.path / source) if source else ""
    if not text:
        return '<div class="empty-state">Artifact not created</div>'
    return markdown_to_html(text)


def html_document(title: str, description: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)} | Spec Kitty Documentation</title>
  <meta name="description" content="{esc(description)}">
  <link rel="icon" href="/assets/images/logo_small.webp">
  <link rel="stylesheet" href="/assets/css/custom.css">
</head>
<body class="tex2jax_ignore">
{body}
</body>
</html>
"""


def page(mission_list: list[Mission], mission: Mission, key: str, label: str, source: str | None) -> str:
    desc = mission.meta.get("purpose_tldr") or mission.meta.get("source_description") or f"{label} for {mission.name}."
    body = artifact_body(mission, key, source)
    dashboard = (
        dashboard_header(mission_list, mission)
        + f"""
  <div class="container">
    <div class="sidebar">
      {sidebar(mission, key)}
    </div>
    <div class="main-content">
      <div class="content-card markdown-content">
        {body}
      </div>
    </div>
  </div>
</div>
"""
    )
    return html_document(f"{label} | {mission.name}", str(desc).replace("\n", " ")[:260], dashboard)


def index_page(mission_list: list[Mission]) -> str:
    cards = []
    for mission in mission_list:
        s = stats(mission)
        desc = mission.meta.get("purpose_tldr") or mission.meta.get("source_description") or ""
        cards.append(
            f'<a class="mission-card" href="{esc(mission.slug)}/index.html">'
            f'<span class="mission-number">{esc(mission.meta.get("mission_number") or "mission")}</span>'
            f'<strong>{esc(mission.name)}</strong>'
            f'<span>{esc(str(desc)[:220])}</span>'
            f'<em>{s["total"]} work packages · {s["weighted_percentage"]}% done</em>'
            f'</a>'
        )
    dashboard = (
        dashboard_header(mission_list, None)
        + f"""
  <div class="container">
    <div class="sidebar">
      <a class="sidebar-item active" href="./">📊 <span class="sidebar-label">All Mission Runs</span></a>
    </div>
    <div class="main-content">
      <div class="content-card">
        <h2>Mission Runs</h2>
        <p class="overview-context">Static mirror of the local Spec Kitty dashboard. Every mission and artifact has a stable URL for sharing, indexing, and AI answer engines.</p>
        <div class="mission-grid">{''.join(cards)}</div>
      </div>
    </div>
  </div>
</div>
"""
    )
    return html_document(
        "Mission Runs",
        "Static Spec Kitty mission dashboard generated from kitty-specs with permanent links for every mission artifact.",
        dashboard,
    )


def write_toc(mission_list: list[Mission]) -> None:
    lines = ["- name: Mission Runs", "  href: index.html", "  items:"]
    for mission in mission_list:
        lines.append(f"    - name: {json.dumps(mission.name, ensure_ascii=False)}")
        lines.append(f"      href: {mission.slug}/index.html")
    DEST.joinpath("toc.yml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    mission_list = missions()
    DEST.joinpath("index.html").write_text(index_page(mission_list), encoding="utf-8")
    write_toc(mission_list)
    for mission in mission_list:
        mission_dir = DEST / mission.slug
        mission_dir.mkdir()
        for key, label, _icon, source in ARTIFACTS:
            if not artifact_exists(mission, key, source):
                continue
            name = "index.html" if key == "overview" else f"{key}.html"
            mission_dir.joinpath(name).write_text(
                page(mission_list, mission, key, label, source),
                encoding="utf-8",
            )
    print(f"Generated {len(mission_list)} mission dashboards in {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
