# Branded Document Generation

Maintainer tooling for turning a Markdown source into a Spec Kitty branded PDF.
The pipeline is a two-stage render: `pandoc` converts Markdown to HTML, then
WeasyPrint converts that HTML to a print-ready PDF that honours the brand's
`@page`, `@font-face`, and local-file rules. The generator script lives beside
this guide in the internal pack at `assets/spec-kitty-branded-pdf.py`.

## Purpose and when to use

Use this tool when a deliverable is audience-facing and warrants the Spec Kitty
brand: release reports, development-cycle postmortems, announcements, and other
documents that leave the maintainer team. It first served the 3.2.6
development-cycle postmortem.

Do not reach for it for internal scratch, notes, or throwaway drafts. The
decision of *when* a deliverable warrants branding, and the review workflow
around it, belong to the `branded-deliverable` tactic; this guide is the *how*.

## What the pipeline enforces

The generator bakes the Spec Kitty print identity into the output. These are
constraints, not suggestions:

- **Print treatment is light cream/paper.** The page surface is
  `--sk-surface-page` in its print form, `#F8F5EC` (warm cream), with white
  cards. This is deliberately NOT the dark-mode website surface (`#0D0E11`).
- **Signature yellow leads.** `#F5C518` carries the top rule, heading
  underlines and left-rules, table headers, and list markers. It is the lead
  brand colour and is used with intent, never as body text.
- **Dark ink for headings and body.** Headings and prose sit in `#231D12` ink
  with a softer `#5A5342` for secondary text.
- **Sage green is never a lead colour.** `--sk-color-sage` (`#4F8F4F`) is
  reserved by the design system for light-mode *headings* only; the print
  pipeline does not promote it to a lead or accent role. Do not reintroduce it.
- **Typefaces.** Falling Sky for display and headings, Swansea for body,
  JetBrains Mono for code, labels, and the eyebrow. Falling Sky and Swansea are
  loaded as local `@font-face` files from the sibling `spec-kitty-design` repo;
  JetBrains Mono is pulled over the network via a Google Fonts `@import`, so an
  offline run falls back to the platform monospace face for those spans.
- **Voice.** Composed, direct, concrete. Sentence case. No emoji. No
  exclamation marks. Source prose you feed the generator must already comply —
  the tool renders what you give it.

The brand authority for these values is the `spec-kitty-design` repo:
`docs/design-system/brand-guidelines.md` and
`packages/tokens/dist/tokens.css`.

## Dependencies

- **`pandoc`** on PATH — Markdown (GFM) to HTML.
- **WeasyPrint** importable by the Python you run the generator with, or
  `weasyprint` on PATH — HTML to PDF. The generator prefers the importable
  library and falls back to the CLI.
- **The sibling `spec-kitty-design` repo** — supplies the brand fonts
  (`packages/tokens/dist/fonts`) and the logo
  (`packages/tokens/assets/logo.png`). If the fonts are absent, WeasyPrint
  falls back to system faces and the PDF renders off-brand.

Install the Python dependencies into an environment that also has WeasyPrint's
native libraries available:

```bash
pip install weasyprint
# pandoc is a system package:
#   macOS:        brew install pandoc
#   Ubuntu/Debian: sudo apt install pandoc
# verification tools ship with poppler:
#   macOS:        brew install poppler
#   Ubuntu/Debian: sudo apt install poppler-utils
```

## Generating the PDF

The generator takes a Markdown input and a PDF output, plus optional cover and
running-footer metadata. A `--title` produces a full branded cover page; omit
it for a bare content render.

```bash
python assets/spec-kitty-branded-pdf.py \
  --input report.md \
  --output report.pdf \
  --title "3.2.6 Cycle Report" \
  --subtitle "Development-cycle postmortem" \
  --lede "What shipped, what slipped, and what the team changed." \
  --eyebrow "Spec Kitty · Release Report" \
  --footer-center "3.2.6 CYCLE REPORT" \
  --meta "DATE=2026-09-04" \
  --meta "AUTHOR=Maintainer team" \
  --design-repo /path/to/spec-kitty-design
```

Flags:

- `--input` / `--output` — required source Markdown and destination PDF.
- `--title` — cover title; omit for no cover page.
- `--subtitle`, `--lede`, `--eyebrow` — cover copy. The eyebrow renders in
  ALL-CAPS monospace with wide tracking.
- `--footer-center` — the centred running-footer label on every non-cover page.
- `--meta "LABEL=value"` — repeatable cover meta chip.
- `--design-repo` — path to the `spec-kitty-design` repo. See the auto-detect
  note below.

## Verifying the output

Do not trust that a PDF is correct because the command exited zero. Verify it:

```bash
# Confirm page count, size, and that a PDF was actually produced:
pdfinfo report.pdf

# Rasterise pages to PNG for a visual/design-review pass:
pdftoppm -png -r 150 report.pdf review-page
# produces review-page-1.png, review-page-2.png, ...
```

Rendering the pages to PNG is not optional polish — it is how the design-review
step in the `branded-deliverable` tactic inspects real output. A designer
review pass (profile `designer-dagmar`) on the rendered pages caught
eyebrow-contrast and body-measure issues that were invisible in the source
Markdown.

## Known gotchas

- **WeasyPrint under a pyenv shim fails with exit 127 in a subprocess.** If the
  generator falls back to the `weasyprint` CLI and that CLI is a pyenv shim, the
  subprocess can fail to resolve (`127`). Run the generator with a Python
  interpreter that has `weasyprint` importable so the in-process path is taken,
  rather than relying on a shimmed CLI on PATH.
- **The design-repo auto-detect only finds a sibling checkout.** The generator
  walks parent directories looking for a `spec-kitty-design` sibling. When you
  run it from elsewhere, pass `--design-repo` explicitly, or the fonts and logo
  will be missing and the PDF renders off-brand.
- **pandoc GFM breaks a bold span that starts with `~`.** A `**~...**` bold span
  placed immediately after another bold span on the same line can be
  mis-parsed by pandoc's GFM reader (the `~` is read as strikethrough). Reword
  the source so the two bold spans are not adjacent, or so the second does not
  lead with `~`.
