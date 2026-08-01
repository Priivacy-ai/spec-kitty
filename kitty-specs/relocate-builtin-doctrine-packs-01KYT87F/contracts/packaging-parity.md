# Contract: Packaging parity (wheel + sdist)

## Requirement

`packs/built-in/` ships **completely** in BOTH the monolith wheel and the sdist; the moved content's
`src/doctrine/**` package-data globs are removed (no duplication).

## Root `pyproject.toml` changes

- `[tool.hatch.build.targets.wheel]`: `force-include = { "packs" = "packs" }`; drop moved-content
  `src/doctrine/**` artifacts.
- `[tool.hatch.build.targets.sdist]`: `include` gains `"packs/**"` (today it is `src/**`, which
  **excludes** a top-level `packs/`).

## Acceptance (NFR-002 — non-fakeable)

1. Build wheel + sdist. For each, the set of relative paths under `packs/built-in/` **equals** the
   pre-move file manifest (exact set-equality — `≥` would pass on duplication; a partial move fails).
2. Install the wheel into a **clean venv** (declared deps only, no repo `src/` on path); `import
   doctrine`, `load_built_in_graph()` (identity fixture), and `spec-kitty doctor doctrine` all succeed
   with 0 missing-file errors.
3. The moved content is **absent** under `src/doctrine/**` (FR-009) — no dual-home duplication.

## Rationale

Pre-spec squad proved a build can succeed while shipping an empty/partial artifact; gate on the built
artifacts' contents and a live import, never on "build exited 0."
