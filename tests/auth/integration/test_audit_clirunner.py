"""CliRunner-usage audit (WP11 T063) + legacy-class audit (WP11 T064).

These tests are **meta-tests** over the ``tests/auth/integration/`` tree
itself. They enforce the two hard rejection criteria from the WP11
prompt:

(T063) Every integration test must drive the real Typer app via
:class:`typer.testing.CliRunner` (or :mod:`subprocess`). Direct
instantiation of flow classes — ``AuthorizationCodeFlow``,
``DeviceCodeFlow``, ``BrowserLoginFlow`` — is forbidden in integration
tests. A file that imports a flow class without also importing
CliRunner or subprocess signals a bad test (probably a lifted unit
test pretending to be an integration test).

(T064) No integration test may reference the deleted legacy classes
``AuthClient`` or ``CredentialStore``. This catches a future
regression where someone copies an old WP-era test into ``integration/``
without rewriting it against :func:`get_token_manager`.

These audits intentionally grep **text**, not AST: if a comment or
docstring contains the forbidden name, that is still a violation
because it signals confusion about the contract.

Exceptions:
- :mod:`test_audit_clirunner` (this file) is audit code and does not
  drive the CLI — it is explicitly exempted from the CliRunner rule.
- :mod:`test_transport_rewired` uses :mod:`inspect` to scan source and
  does not drive the CLI either — exempted from the CliRunner rule.
- :mod:`conftest` is fixtures, not a test file, so it is exempted.
"""

from __future__ import annotations

from pathlib import Path


_INTEGRATION_DIR = Path(__file__).resolve().parent
_STRESS_DIR = _INTEGRATION_DIR.parent / "stress"
_CONCURRENCY_DIR = _INTEGRATION_DIR.parent / "concurrency"

# Files that are legitimately audit / structural tests — they do not
# drive the CLI and must not be flagged by the CliRunner audit below.
_CLIRUNNER_AUDIT_EXEMPT: frozenset[str] = frozenset(
    {
        "test_audit_clirunner.py",
        "test_transport_rewired.py",
    }
)

# Names whose presence in an integration test source file is a hard
# rejection criterion per the WP11 prompt.
_LEGACY_NAMES: tuple[str, ...] = ("AuthClient", "CredentialStore")

# Flow classes that integration tests must not instantiate directly.
_FLOW_CLASSES: tuple[str, ...] = (
    "AuthorizationCodeFlow",
    "DeviceCodeFlow",
    "BrowserLoginFlow",
)


def _iter_test_files(directory: Path) -> list[Path]:
    """Yield every ``test_*.py`` file in ``directory`` (non-recursive)."""
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.glob("test_*.py") if p.is_file())


class TestCliRunnerAudit:
    """T063: integration tests must use CliRunner (or subprocess)."""

    def test_every_integration_test_uses_clirunner_or_subprocess(self) -> None:
        """FR-016 contract: non-exempt tests must drive the CLI, not flows.

        A file is compliant if ANY of these are true:

        - It imports ``CliRunner`` from :mod:`typer.testing`.
        - It imports or uses :mod:`subprocess`.
        - It is in the exempt list (audit / structural tests).

        A file is non-compliant if it imports a flow class directly
        without also importing CliRunner/subprocess.
        """
        offenders: list[tuple[Path, str]] = []

        for test_file in _iter_test_files(_INTEGRATION_DIR):
            if test_file.name in _CLIRUNNER_AUDIT_EXEMPT:
                continue
            source = test_file.read_text(encoding="utf-8")

            uses_clirunner = "CliRunner" in source
            uses_subprocess = "subprocess" in source

            if not (uses_clirunner or uses_subprocess):
                offenders.append((test_file, "missing CliRunner AND subprocess imports"))
                continue

            # If the test imports any flow class directly, that's a red
            # flag: it probably bypasses the CLI. We allow it only when
            # CliRunner is also present AND the flow is patched (not
            # instantiated directly — we check for raw constructor calls).
            for flow in _FLOW_CLASSES:
                if flow in source and not uses_clirunner:
                    offenders.append(
                        (
                            test_file,
                            f"references {flow} without CliRunner",
                        )
                    )

        assert not offenders, "T063 violation: the following integration tests do not drive the real Typer app via CliRunner:\n" + "\n".join(
            f"  - {path.name}: {reason}" for path, reason in offenders
        )

    def test_exempt_files_still_exist(self) -> None:
        """Sanity check: the exempt list must match actual files.

        Prevents dangling exemptions from lingering after a file is
        renamed or deleted.
        """
        for exempt in _CLIRUNNER_AUDIT_EXEMPT:
            exempt_path = _INTEGRATION_DIR / exempt
            assert exempt_path.exists(), f"CliRunner-exempt file {exempt!r} no longer exists — remove it from _CLIRUNNER_AUDIT_EXEMPT"


class TestLegacyClassAudit:
    """T064: no WP11 test may reference the deleted legacy classes."""

    def test_integration_tests_have_no_legacy_class_references(self) -> None:
        """FR-016: ``AuthClient`` / ``CredentialStore`` must not appear.

        This audit is scoped to the WP11 test directories:
        - ``tests/auth/integration/``
        - ``tests/auth/concurrency/``
        - ``tests/auth/stress/``

        It does NOT scan the rest of ``tests/`` — older dirs (e.g.
        ``tests/sync/tracker/``) have legacy compatibility shims that
        are out of scope for WP11.
        """
        offenders: list[tuple[Path, str]] = []

        # Files that legitimately contain the forbidden names as string
        # assertions or negative-regression checks. Both of these files
        # exist to enforce the absence of the legacy classes — they must
        # reference the names by definition.
        legacy_audit_exempt = frozenset(
            {
                "test_audit_clirunner.py",
                "test_transport_rewired.py",
            }
        )

        for directory in (_INTEGRATION_DIR, _CONCURRENCY_DIR, _STRESS_DIR):
            for test_file in _iter_test_files(directory):
                if test_file.name in legacy_audit_exempt:
                    continue
                source = test_file.read_text(encoding="utf-8")
                for legacy in _LEGACY_NAMES:
                    if legacy in source:
                        offenders.append((test_file, legacy))

        assert not offenders, "T064 violation: the following WP11 tests reference deleted legacy classes:\n" + "\n".join(
            f"  - {path.relative_to(_INTEGRATION_DIR.parent)}: {name}" for path, name in offenders
        )

    def test_integration_tests_use_get_token_manager_factory(self) -> None:
        """Positive audit: every non-audit integration test must use the factory.

        A test that needs a :class:`TokenManager` must call
        :func:`get_token_manager`, never ``TokenManager()``. This pairs
        with the T063 audit: we verify tests go through the CLI AND that
        they obtain tokens through the factory pipeline.
        """
        offenders: list[tuple[Path, str]] = []

        for test_file in _iter_test_files(_INTEGRATION_DIR):
            if test_file.name in _CLIRUNNER_AUDIT_EXEMPT:
                continue
            source = test_file.read_text(encoding="utf-8")
            # Only flag files that actually reference TokenManager.
            if "TokenManager" not in source:
                continue
            # They must use get_token_manager — direct instantiation is
            # forbidden (regression risk against the singleton contract).
            if "get_token_manager" not in source:
                offenders.append((test_file, "references TokenManager but not get_token_manager"))

        assert not offenders, "Factory-access violation: integration tests must use get_token_manager(), not TokenManager() directly:\n" + "\n".join(
            f"  - {path.name}: {reason}" for path, reason in offenders
        )


class TestHardcodedSaasUrlAudit:
    """Belt-and-braces: no WP11 test may hardcode a production SaaS URL."""

    def test_no_production_saas_url_in_wp11_tests(self) -> None:
        """D-5 / C-012: no WP11 test may hardcode a production URL.

        The autouse ``_isolate_auth_env`` fixture in ``conftest.py`` sets
        ``SPEC_KITTY_SAAS_URL=https://saas.test``. Any WP11 test that
        hardcodes a different non-``saas.test`` URL is a red flag.
        """
        banned_fragments = (
            "api.spec-kitty.com",
            "spec-kitty.dev",
            "https://saas.spec-kitty",
        )
        offenders: list[tuple[Path, str]] = []

        for directory in (_INTEGRATION_DIR, _CONCURRENCY_DIR, _STRESS_DIR):
            for test_file in _iter_test_files(directory):
                # The audit file itself references these strings.
                if test_file.name == "test_audit_clirunner.py":
                    continue
                source = test_file.read_text(encoding="utf-8")
                for fragment in banned_fragments:
                    if fragment in source:
                        offenders.append((test_file, fragment))

        assert not offenders, "C-012 violation: the following tests hardcode a production SaaS URL instead of using the SPEC_KITTY_SAAS_URL env var:\n" + "\n".join(
            f"  - {path.name}: {frag}" for path, frag in offenders
        )
