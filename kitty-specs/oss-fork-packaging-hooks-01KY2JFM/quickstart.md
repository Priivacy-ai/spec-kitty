# Quickstart: OSS Fork Packaging Hooks

## Stock path (no registration)

1. Install `spec-kitty-cli` from public PyPI.
2. Confirm `--version` still labels stock CLI and upgrade checks hit public PyPI.
3. Regression tests in this mission must pass without any entry points registered.

## Packager Phase 1 (identity + provider)

In the fork’s `pyproject.toml`:

```toml
[project]
name = "acme-spec-kitty-cli"

[project.entry-points."spec_kitty.cli_package"]
main = "acme_spec_kitty_dist:PACKAGE_NAME"

[project.entry-points."spec_kitty.upgrade_provider"]
acme = "acme_spec_kitty_dist:AcmeSimpleIndexProvider"
```

Thin module `acme_spec_kitty_dist.py`:

```python
PACKAGE_NAME = "acme-spec-kitty-cli"

class AcmeSimpleIndexProvider(SimpleIndexProvider):
    def __init__(self) -> None:
        super().__init__(index_url="https://example.invalid/simple/", package_prefix="acme_spec_kitty_cli")
```

Build/upload as today — **do not** overlay `src/specify_cli/**`.

## Packager Phase 2 (full profile)

Prefer a single profile entry point that sets package aliases, index URLs, freshness, and `disable_public_pypi_notifier=True`.

## Validation checklist

- [ ] Stock tests green with no entry points
- [ ] With fake entry points, session-presence refresh calls provider for fork package name
- [ ] Remediation argv includes `--index-url` when profile sets it and still passes CHK028
- [ ] Public notifier suppressed when flag set
- [ ] Docs guide linked from upgrade-cli guide
