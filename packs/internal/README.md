# `spec-kitty-internal` — org-tier doctrine pack (NOT shipped to consumers)

This is Spec Kitty's own **internal** doctrine pack: the doctrine that governs
*contributors, maintainers, and the core team* of the Spec Kitty project itself.
It is loaded as an **org-tier** pack (registered in `.kittify/config.yaml` under
`doctrine.org.packs`), overlaying the public `packs/built-in/` product doctrine.

## Why this is a separate pack — and why it is NOT built-in

- The `built-in` tier (`packs/built-in/`) is the **public product doctrine** that
  ships to every consumer via the PyPI wheel. It is single-rooted and resolved by
  a kernel ancestor-walk (`kernel.sibling_paths.resolve_installed_sibling`), so it
  **cannot** host a second pack.
- Maintainer-only doctrine (how *we* land PRs, process the tracker, keep main
  honest, run our internal glossary) must **not** be force-shipped to consumers.
  It is therefore an **org pack**, and `pyproject.toml` narrows the wheel/sdist
  `packs` include to `packs/built-in/` specifically so this tree never ships.
  `tests/cross_cutting/packaging/test_packaging_safety.py` guards that boundary.

## Layout (org-tier shape — differs from `built-in`)

```
packs/internal/
├── org-charter.yaml                          # pack name/description + required_* activation lists
├── drg/fragment.yaml                         # SINGLE DRG fragment (org tier), not sharded *.graph.yaml
├── glossary_packs/
│   └── spk-internal.glossary-pack.yaml       # maintainer/engineering glossary (net-new internal terms)
└── procedures/
    └── landing-contributor-prs.procedure.yaml
```

## Reference, don't duplicate

A lot of maintainer-flavoured doctrine already ships in `packs/built-in/`
(`red-main-release-discipline`, `tracker-organisation-workflow`,
`pr-agent-worktree-isolation`, `mission-tracer-files`, …). This pack **references**
those via DRG `refines` edges rather than re-authoring them. Only genuinely
repo-only residue (PR-landing specifics, the internal glossary) is authored here.

> First-step scaffold. See the initiative synthesis for the deferred decisions
> (built-in ownership inversion, open-packs as the permanent home, private-vs-public
> reconciliation with catalog pack #16 `spec-kitty-internal`).
