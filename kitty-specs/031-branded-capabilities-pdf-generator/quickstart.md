# Quickstart: Branded Capabilities PDF Generator

## Prerequisites

```bash
pip install reportlab
```

## Generate the PDF

```bash
# From the project root:
python generate_pdf.py

# Custom output location:
python generate_pdf.py --output ~/Desktop/spec-kitty-brochure.pdf
```

## Output

A 2-page A4 PDF (`spec-kitty-capabilities.pdf`) with:
- **Page 1**: Logo, tagline, key stats, problem/solution overview
- **Page 2**: 6 capability blocks in branded 2-column layout

## Updating Content

Edit the capability descriptions directly in `generate_pdf.py` — they are defined as Python string constants near the top of the file. The version number is auto-extracted from `pyproject.toml`.

## Brand Assets

- **Logo**: `media/logo_small.png`
- **Colors**: Defined as `HexColor` constants in the script
