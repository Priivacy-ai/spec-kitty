"""charter.neutrality — Language-neutrality lint for shipped doctrine artifacts.

Public API (importable directly from this package):

  - :func:`run_neutrality_lint` — scan configured roots and return a result.
  - :class:`BannedTermHit` — a single banned-term match (file, line, column, term_id, match).
  - :class:`NeutralityLintResult` — aggregated scan result with ``passed`` property.

Configuration files (edit these to extend the lint):

  - ``src/charter/neutrality/banned_terms.yaml`` — banned term definitions.
    Schema: ``contracts/banned-terms-schema.yaml`` (C-4).
  - ``src/charter/neutrality/language_scoped_allowlist.yaml`` — allowlisted paths.
    Schema: ``contracts/language-scoped-allowlist-schema.yaml`` (C-5).

Test harness contract: ``contracts/neutrality-lint-contract.md`` (C-3).

Mission: charter-ownership-consolidation-and-neutrality-hardening-01KPD880
"""

from charter.neutrality.lint import (
    BannedTermHit,
    NeutralityLintResult,
    run_neutrality_lint,
)

__all__ = [
    "BannedTermHit",
    "NeutralityLintResult",
    "run_neutrality_lint",
]
