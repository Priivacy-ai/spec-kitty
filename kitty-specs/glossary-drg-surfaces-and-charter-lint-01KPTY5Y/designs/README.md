# Design References

## Glossary Browser UI

**File**: `src/specify_cli/dashboard/templates/glossary.html`  
**Route**: `/glossary` (to be wired up in WP02)  
**Status**: Static mockup with hardcoded term data — WP02 makes it dynamic (JS fetches from `/api/glossary-terms`)

### What the mockup demonstrates

This is a full-page glossary browser that inherits the local dashboard's design language. It is the target design for the `/glossary` dashboard route delivered in WP02.

#### Design system (CSS custom properties)

| Variable | Light | Dark | Role |
|----------|-------|------|------|
| `--bg` | `#A7C7E7` | `#18222c` | Page background |
| `--surface` | `#FFFDF7` | `#1e2832` | Card / header background |
| `--green` | `#7BB661` | `#8fc97a` | Brand accent, active status |
| `--lavender` | `#C9A0DC` | `#b089c8` | Draft status |
| `--peach` | `#FFD8B1` | `#7a4a1e` | Deprecated status |
| `--yellow-dark` | `#e6d836` | — | Header bottom border |

Dark mode is handled automatically via `@media (prefers-color-scheme: dark)`.

#### Page structure

```
sticky header
  ├── logo + title ("Spec Kitty / spec_kitty_core · canonical glossary")
  └── stat pills: Total | Active | Draft | Deprecated  ← drives the WP02 tile too

sticky toolbar
  ├── search input (real-time filter across surface + definition)
  ├── filter tabs: All / Active / Draft / Deprecated
  └── result count ("N of M" or "N terms")

alpha nav bar
  └── A–Z jump buttons (dimmed if letter has no terms, green-tinted if it does)

main content
  └── letter sections: letter-char badge + horizontal rule + cards-grid

  cards-grid (auto-fill minmax(320px, 1fr))
    └── term card
          border-top: 3px solid [status color]
          card-head: surface name (monospace, bold) + status badge
          card-def: definition text (italic if deprecated, strikethrough on name)
          card-foot: confidence bar (thin, colored by status) + % label
          hover: translateY(-1px) lift
```

#### Term data shape (what WP02's `/api/glossary-terms` must return)

```json
[
  {
    "surface": "canonical-term-name",
    "definition": "What this term means.",
    "status": "active",
    "confidence": 0.95
  }
]
```

`status` values: `"active"` | `"draft"` | `"deprecated"`  
`confidence`: float 0.0–1.0 (maps to the confidence bar width)

#### Stat pills (header)

The header stat pills (Total / Active / Draft / Deprecated counts) are the same data as the WP02 dashboard glossary tile. The tile is the entry point; the full `/glossary` page is the destination when the tile is clicked.

#### Search highlight

Matched substrings are wrapped in `<mark class="hl">` — yellow background (`rgba(255,242,117,0.7)`), rounded corners.

#### Empty state

When no terms match the filter/search: centered icon `🔍` + "No terms match …" text.
