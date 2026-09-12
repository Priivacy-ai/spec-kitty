# Contract — Audience Resolution (FR-002/FR-003)

- **Field**: `audience:` in page frontmatter. Value = one resolvable repo-relative `.md` path (or a
  list) targeting a persona under `docs/context/audience/`. Cardinality: single value preferred; a
  list is permitted.
- **Scope**: required on touched pages only (C-012). MUST NOT be added to
  `structural_lint_config.frontmatter_required_fields` (would red every untouched page).
- **Resolver** (`scripts/docs/audience_resolver.py` or an extension of `related_validator`):
  - Walks `docs/**.md`, collects `audience:` values, asserts each resolves to an existing file.
  - **Non-vacuous**: reuses `assert_examined_floor` with `min_files ≥` the count of audience-tagged
    pages; fails on 0 examined. Emits `checked_count`.
  - Runs `--strict` on PR in `docs-freshness.yml`; exit 1 on any dangling reference.
- **Canonization**: `042-common-docs` + `common-docs` styleguide document the field with a `tooling:`
  row naming this resolver; `047-audience-oriented-writing` references it.
