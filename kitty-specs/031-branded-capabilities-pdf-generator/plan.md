# Implementation Plan: Branded Capabilities PDF Generator
*Path: kitty-specs/031-branded-capabilities-pdf-generator/plan.md*

**Branch**: `031-branded-capabilities-pdf-generator` | **Date**: 2026-02-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/031-branded-capabilities-pdf-generator/spec.md`

## Summary

A standalone Python script (`generate_pdf.py`) at the project root that uses reportlab to produce a polished 2-page PDF brochure of Spec Kitty's capabilities. Content is extracted from the `docs/` directory. The PDF uses the full Spec Kitty brand palette and logo for a professional, conference-ready look.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: reportlab (PDF generation), Pillow (logo image handling — reportlab dependency)
**Storage**: N/A (generates a file to disk)
**Testing**: Manual visual inspection + pytest for content extraction logic
**Target Platform**: macOS, Linux, Windows (cross-platform Python script)
**Project Type**: Single standalone script
**Performance Goals**: PDF generation in < 10 seconds
**Constraints**: Output must be exactly 2 pages; must work without network access

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Python 3.11+ | PASS | Script uses Python 3.11+ |
| Testing requirements | PASS | Unit tests for content extraction; visual test for layout |
| Cross-platform | PASS | reportlab is pure Python, works on Linux/macOS/Windows |
| No new CLI subcommand | PASS | Standalone script, not integrated into spec-kitty CLI |
| PyPI distribution | N/A | Script lives in repo only, not distributed via PyPI |

No constitution violations. The script is standalone and does not modify the spec-kitty CLI architecture.

## Project Structure

### Documentation (this feature)

```
kitty-specs/031-branded-capabilities-pdf-generator/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── quickstart.md        # Phase 1 output
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks/               # Phase 2 output (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
generate_pdf.py          # The standalone script (top-level for discoverability)
media/
└── logo_small.png       # Existing brand asset (used by the script)
docs/                    # Existing documentation (content source)
├── index.md
├── explanation/         # Conceptual docs
├── how-to/              # Task guides
├── reference/           # API/command reference
└── tutorials/           # Getting started guides
```

**Structure Decision**: Single top-level script. No new directories or packages created.

## Design Decisions

### PDF Layout Design

**Page 1 — Cover & Value Proposition**:
- Spec Kitty logo (top-center, from `media/logo_small.png`)
- Tagline: "Stop wrestling with AI agents. Start shipping features."
- 3 key stats in branded accent boxes: "12 AI Agents", "40% Faster", "Zero Merge Conflicts"
- Brief problem/solution paragraph
- Grassy Green (#7BB661) header bar, Creamy White (#FFFDF7) background

**Page 2 — Capabilities Overview**:
- Section heading in Grassy Green
- 6 capability blocks in a 2-column layout:
  1. Multi-Agent Orchestration (Baby Blue accent)
  2. Spec-Driven Workflow (Grassy Green accent)
  3. Live Kanban Dashboard (Sunny Yellow accent)
  4. Parallel Development (Lavender accent)
  5. Mission System (Soft Peach accent)
  6. Quality Gates & Merge (Baby Blue accent)
- Each block: colored left-border accent, bold title, 2-3 line description
- Footer with version number and URL

### Content Extraction Strategy

The script will extract content from specific docs/ files rather than parsing all markdown generically:

1. **Curated content map** — A Python dictionary in the script maps each PDF section to a brief, hand-written description. This is more reliable than parsing arbitrary markdown and ensures the 2-page constraint is met.
2. **Version number** — Extracted from `pyproject.toml` so the PDF always shows the current version.
3. **Capability descriptions** — Drawn from the docs/ files but curated/condensed to fit the 2-page format. The script contains the condensed text directly, referencing docs/ as the authoritative source.

**Rationale**: Attempting to auto-parse and summarize 54 markdown files into exactly 2 pages would be fragile and produce inconsistent results. A curated approach with clear content constants gives full control over the brochure quality.

### reportlab Architecture

- Use `reportlab.lib.pagesizes.A4` for standard page size
- Use `reportlab.platypus` for high-level layout (frames, paragraphs, spacers)
- Use `reportlab.lib.colors.HexColor` for brand palette
- Use `reportlab.lib.styles` for consistent typography
- Use `reportlab.platypus.Image` for logo placement
- Use `reportlab.platypus.Table` for the stats row and capability grid

### Typography

- **Headings**: Helvetica-Bold (built-in, no font installation needed)
- **Body**: Helvetica (built-in)
- **Accent text**: Helvetica-Oblique for tagline
- Font sizes: Title 28pt, Section headings 16pt, Body 10pt, Footer 8pt

### Color Constants

```python
GRASSY_GREEN = HexColor("#7BB661")   # Primary headings, accents
BABY_BLUE = HexColor("#A7C7E7")      # Secondary elements
LAVENDER = HexColor("#C9A0DC")       # Highlights
SUNNY_YELLOW = HexColor("#FFF275")   # Accent details
SOFT_PEACH = HexColor("#FFD8B1")     # Warm accents
CREAMY_WHITE = HexColor("#FFFDF7")   # Background tone
DARK_TEXT = HexColor("#2c3e50")      # Body text
```

### Error Handling

The script fails hard with clear messages (per project conventions — no fallbacks):
- Missing `media/logo_small.png` → `FileNotFoundError` with message
- Missing `docs/` directory → `FileNotFoundError` with message
- reportlab not installed → `ImportError` with install instructions
- Output path not writable → `PermissionError` propagates naturally

### CLI Interface

```bash
# Default output
python generate_pdf.py

# Custom output path
python generate_pdf.py --output /path/to/brochure.pdf
```

Uses `argparse` (stdlib) for the single `--output` flag. No external CLI library needed.
