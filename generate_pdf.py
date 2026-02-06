#!/usr/bin/env python3
"""Generate a branded PDF brochure of Spec Kitty capabilities.

Standalone script — does NOT import from specify_cli.
Requires: reportlab (pip install reportlab)
"""

import argparse
import sys
import tomllib
from pathlib import Path

try:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Image,
        Table,
        TableStyle,
    )
except ImportError:
    print(
        "ERROR: reportlab is required. Install it with: pip install reportlab",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Brand color constants
# ---------------------------------------------------------------------------
GRASSY_GREEN = HexColor("#7BB661")
BABY_BLUE = HexColor("#A7C7E7")
LAVENDER = HexColor("#C9A0DC")
SUNNY_YELLOW = HexColor("#FFF275")
SOFT_PEACH = HexColor("#FFD8B1")
CREAMY_WHITE = HexColor("#FFFDF7")
DARK_TEXT = HexColor("#2c3e50")
WHITE = HexColor("#FFFFFF")

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
LOGO_PATH = SCRIPT_DIR / "media" / "logo_small.png"
DOCS_DIR = SCRIPT_DIR / "docs"
PYPROJECT_PATH = SCRIPT_DIR / "pyproject.toml"

# ---------------------------------------------------------------------------
# A4 dimensions and margins
# ---------------------------------------------------------------------------
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 20 * mm
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN


# ---------------------------------------------------------------------------
# T002 - Version extraction
# ---------------------------------------------------------------------------
def get_version() -> str:
    """Extract version from pyproject.toml."""
    with open(PYPROJECT_PATH, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


# ---------------------------------------------------------------------------
# T003 - Input validation (hard failures, no fallbacks)
# ---------------------------------------------------------------------------
def validate_inputs() -> None:
    """Verify required files exist. Fail hard if missing."""
    if not LOGO_PATH.exists():
        raise FileNotFoundError(
            f"Logo not found at {LOGO_PATH}. "
            "Ensure media/logo_small.png exists in the project root."
        )
    if not DOCS_DIR.exists() or not any(DOCS_DIR.iterdir()):
        raise FileNotFoundError(
            f"Documentation directory not found or empty at {DOCS_DIR}. "
            "Ensure docs/ directory contains documentation files."
        )


# ---------------------------------------------------------------------------
# T001 - CLI argument parsing
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate a 2-page branded PDF brochure of Spec Kitty capabilities."
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("spec-kitty-capabilities.pdf"),
        help="Output PDF file path (default: spec-kitty-capabilities.pdf)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# T004 - Custom paragraph styles
# ---------------------------------------------------------------------------
TITLE_STYLE = ParagraphStyle(
    name="SpecKittyTitle",
    fontName="Helvetica-Bold",
    fontSize=28,
    textColor=GRASSY_GREEN,
    alignment=1,  # CENTER
    spaceAfter=4 * mm,
)

TAGLINE_STYLE = ParagraphStyle(
    name="SpecKittyTagline",
    fontName="Helvetica-Oblique",
    fontSize=14,
    textColor=DARK_TEXT,
    alignment=1,  # CENTER
    spaceAfter=2 * mm,
)

BODY_STYLE = ParagraphStyle(
    name="SpecKittyBody",
    fontName="Helvetica",
    fontSize=10,
    textColor=DARK_TEXT,
    alignment=4,  # JUSTIFY
    leading=14,
    spaceAfter=4 * mm,
)

STAT_NUMBER_STYLE = ParagraphStyle(
    name="StatNumber",
    fontName="Helvetica-Bold",
    fontSize=22,
    textColor=WHITE,
    alignment=1,  # CENTER
    spaceAfter=1 * mm,
)

STAT_LABEL_STYLE = ParagraphStyle(
    name="StatLabel",
    fontName="Helvetica",
    fontSize=9,
    textColor=WHITE,
    alignment=1,  # CENTER
)


# ---------------------------------------------------------------------------
# T004 - Stat box helper
# ---------------------------------------------------------------------------
def _build_stat_cell(number: str, label: str) -> Table:
    """Build a single stat cell with stacked number and label paragraphs."""
    num_para = Paragraph(number, STAT_NUMBER_STYLE)
    label_para = Paragraph(label, STAT_LABEL_STYLE)
    inner = Table(
        [[num_para], [label_para]],
        colWidths=[CONTENT_WIDTH / 3 - 6 * mm],
        rowHeights=[10 * mm, 8 * mm],
    )
    inner.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return inner


# ---------------------------------------------------------------------------
# T004 - Build Page 1
# ---------------------------------------------------------------------------
def build_page1() -> list:
    """Build the cover page elements: logo, title, tagline, stats, body text."""
    elements: list = []

    # --- Logo ---
    logo = Image(
        str(LOGO_PATH),
        width=50 * mm,
        height=50 * mm,
        hAlign="CENTER",
    )
    logo.preserveAspectRatio = True
    logo._restrictSize(50 * mm, 50 * mm)
    elements.append(logo)

    # --- Spacer after logo ---
    elements.append(Spacer(1, 8 * mm))

    # --- Title ---
    elements.append(Paragraph("Spec Kitty", TITLE_STYLE))

    # --- Tagline ---
    elements.append(
        Paragraph(
            "Stop wrestling with AI agents. Start shipping features.",
            TAGLINE_STYLE,
        )
    )

    # --- Spacer before stats ---
    elements.append(Spacer(1, 12 * mm))

    # --- 3 Stat boxes ---
    col_width = CONTENT_WIDTH / 3 - 2 * mm
    gap = 3 * mm

    stat1 = _build_stat_cell("12", "AI Agents Supported")
    stat2 = _build_stat_cell("40%", "Faster Development")
    stat3 = _build_stat_cell("0", "Merge Conflicts")

    stats_table = Table(
        [[stat1, stat2, stat3]],
        colWidths=[col_width, col_width, col_width],
        rowHeights=[26 * mm],
        hAlign="CENTER",
    )
    stats_table.setStyle(
        TableStyle(
            [
                # Background colors for each column
                ("BACKGROUND", (0, 0), (0, 0), BABY_BLUE),
                ("BACKGROUND", (1, 0), (1, 0), GRASSY_GREEN),
                ("BACKGROUND", (2, 0), (2, 0), LAVENDER),
                # Rounded appearance via matching-color top/bottom lines
                ("LINEABOVE", (0, 0), (0, 0), 3, BABY_BLUE),
                ("LINEBELOW", (0, 0), (0, 0), 3, BABY_BLUE),
                ("LINEABOVE", (1, 0), (1, 0), 3, GRASSY_GREEN),
                ("LINEBELOW", (1, 0), (1, 0), 3, GRASSY_GREEN),
                ("LINEABOVE", (2, 0), (2, 0), 3, LAVENDER),
                ("LINEBELOW", (2, 0), (2, 0), 3, LAVENDER),
                # Alignment and padding
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
                ("LEFTPADDING", (0, 0), (-1, -1), gap),
                ("RIGHTPADDING", (0, 0), (-1, -1), gap),
            ]
        )
    )
    elements.append(stats_table)

    # --- Spacer before body text ---
    elements.append(Spacer(1, 12 * mm))

    # --- Problem/Solution paragraph ---
    body_text = (
        "AI coding agents are powerful but chaotic. Without structure, they lose "
        "context, forget requirements, and produce code that drifts from specifications. "
        "Spec Kitty brings order to AI-assisted development with executable specifications, "
        "real-time tracking, and isolated workspaces — so your team ships features "
        "faster with zero rework."
    )
    elements.append(Paragraph(body_text, BODY_STYLE))

    # --- Breathing room at the bottom ---
    elements.append(Spacer(1, 20 * mm))

    return elements


# ---------------------------------------------------------------------------
# T005 - Main entry point
# ---------------------------------------------------------------------------
def main(output_path: Path) -> None:
    """Generate the branded capabilities PDF."""
    validate_inputs()
    version = get_version()

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title=f"Spec Kitty Capabilities v{version}",
        author="Spec Kitty",
    )

    elements: list = []
    elements.extend(build_page1())
    # Page 2 will be added in WP02

    doc.build(elements)
    print(f"PDF generated: {output_path.resolve()}")


if __name__ == "__main__":
    args = parse_args()
    main(args.output)
