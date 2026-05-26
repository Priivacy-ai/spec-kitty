"""Charter-runtime umbrella package.

Groups the four runtime concerns that compose the spec-kitty charter surface:

- ``charter_runtime.lint`` — decay-detection (formerly ``specify_cli.charter_lint``)
- ``charter_runtime.freshness`` — staleness / hash-comparison (formerly ``charter_freshness``)
- ``charter_runtime.preflight`` — pre-session readiness check (formerly ``charter_preflight``)
- ``charter_runtime.facade`` — the existing charter facade (formerly ``charter``)

The legacy import paths (``specify_cli.charter_lint``, etc.) continue to resolve
via shim re-exports at the old locations for one deprecation window per spec C-008.
"""

__all__: list[str] = []
