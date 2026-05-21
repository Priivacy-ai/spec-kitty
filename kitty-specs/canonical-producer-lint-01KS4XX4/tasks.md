# Tasks — Canonical Producer Lint

**Spec**: [`spec.md`](spec.md) · **Plan**: [`plan.md`](plan.md)
**Mission slug**: `canonical-producer-lint-01KS4XX4`

| WP | Title | Depends on | Lane | Repo |
|----|-------|-----------|------|------|
| WP01 | Lint script + unit tests (`scripts/lint_canonical_producers.py` + `tests/lint/`) | — | a | spec-kitty |
| WP02 | Existing-exemption audit across all three producer repos | WP01 | a | spec-kitty (audit doc); inline exempts in saas/e2e if needed |
| WP03 | spec-kitty CI workflow (`.github/workflows/canonical-producer-lint.yml`) | WP02 | a | spec-kitty |
| WP04 | spec-kitty-saas CI workflow (`.github/workflows/canonical-producer-lint.yml`) | WP02 | a | spec-kitty-saas |
| WP05 | spec-kitty-end-to-end-testing CI workflow (`.github/workflows/canonical-producer-lint.yml`) | WP02 | a | spec-kitty-end-to-end-testing |

## Dependency graph

```
WP01 ──► WP02 ──┬──► WP03 (spec-kitty)
                ├──► WP04 (saas)
                └──► WP05 (e2e)
```

WP03, WP04, WP05 are independent of each other (different repos / different files).
