# Research: Branded Capabilities PDF Generator

**Date**: 2026-02-06
**Feature**: 031-branded-capabilities-pdf-generator

## Decision: PDF Library

**Decision**: reportlab
**Rationale**: User explicitly requested a library with full aesthetic control. reportlab provides pixel-level control over layout, typography, color, and image placement via its `platypus` high-level API and `canvas` low-level API. It is the most mature Python PDF library (20+ years), well-documented, and has no system-level dependencies (unlike weasyprint which requires cairo/pango).
**Alternatives considered**:
- **weasyprint** — HTML/CSS-to-PDF. Easier for web developers but requires system dependencies (cairo, pango, gdk-pixbuf). Less control over exact positioning.
- **fpdf2** — Lightweight but less feature-rich than reportlab for complex layouts (tables, multi-column).
- **pdfkit/wkhtmltopdf** — Requires wkhtmltopdf binary. Heavy dependency for a simple 2-page document.

## Decision: Content Strategy

**Decision**: Curated content constants in the script, with version extracted from pyproject.toml
**Rationale**: The docs/ directory contains 54 markdown files across 5 categories. Auto-parsing and summarizing this into exactly 2 pages would be fragile, produce inconsistent results, and require NLP or heuristic summarization. A curated approach ensures the brochure reads like marketing material, not auto-generated documentation.
**Alternatives considered**:
- **Full auto-extraction** — Parse all markdown, rank by importance, truncate to fit. Rejected: too fragile, poor quality control.
- **Template-based with YAML data** — Separate YAML file for content, script reads it. Rejected: Over-engineering for a single script; the content IS the script's purpose.

## Decision: Page Size

**Decision**: A4 (210mm x 297mm)
**Rationale**: International standard, works for both print and digital distribution. US Letter is close enough that A4 content displays well on both sizes.

## Decision: Script Location

**Decision**: Top-level `generate_pdf.py`
**Rationale**: User explicitly chose (B) for maximum discoverability. The script is not part of the spec-kitty package.

## Decision: Typography

**Decision**: Built-in Helvetica family (Helvetica, Helvetica-Bold, Helvetica-Oblique)
**Rationale**: reportlab includes 14 standard PDF fonts (the "Base 14") that require no font files. Helvetica is clean, professional, and universally supported in all PDF readers. No font installation or embedding needed.

## Brand Assets Inventory

**Logo**: `media/logo_small.png` (1481 KB, PNG format — confirmed present)
**Color palette**: Extracted from `src/specify_cli/dashboard/static/dashboard/dashboard.css`:
- Grassy Green: #7BB661
- Baby Blue: #A7C7E7
- Lavender: #C9A0DC
- Sunny Yellow: #FFF275
- Soft Peach: #FFD8B1
- Creamy White: #FFFDF7
- Dark Text: #2c3e50

**Tagline**: "Stop wrestling with AI agents. Start shipping features." (from README.md)

## Content Sources (docs/ directory)

Key files for capability descriptions:
- `docs/explanation/spec-driven-development.md` — SDD philosophy
- `docs/explanation/multi-agent-orchestration.md` — Agent coordination
- `docs/explanation/workspace-per-wp.md` — Parallel development model
- `docs/reference/supported-agents.md` — 12-agent list
- `docs/reference/missions.md` — Mission types
- `docs/how-to/use-dashboard.md` — Dashboard features
- `docs/how-to/parallel-development.md` — Parallelization workflow
