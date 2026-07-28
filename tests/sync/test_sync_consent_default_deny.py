"""P0 red-main pins for hosted-sync consent (#3031).

These tests encode the invariants a confidentiality control must satisfy. They
fail on ``main`` **by design**, per the honest-red-P0 policy (ADR 2026-07-17-1):
a P0 that cannot be demonstrated failing is a P0 nobody can verify fixed.

Background. A live incident delivered 1,322 events belonging to five projects
that had never opted in to hosted sync, from a machine-global journal, to a
hosted instance (see ``Priivacy-ai/spec-kitty-saas#585``). The operator's
configuration was correct throughout. The defaults did it:

* ``sync/routing.py`` resolves an unconfigured checkout to
  ``effective_sync_enabled = True`` — consent is opt-*out*.
* ``is_sync_enabled_for_checkout`` returns ``True`` when routing cannot be
  resolved at all — the control fails *open*.
* The consent record lives in the machine-global ``~/.spec-kitty/config.toml``
  keyed by ``repo_slug``, not in the project's own ``.kittify/config.yaml``, so
  it is invisible in the repo it governs, unreviewable, not version-controlled,
  and keyed on a mutable git remote.

Each test below names the invariant rather than the current implementation, so
the fix is free to satisfy them however it likes. They are deliberately written
against the pre-existing public entry points (``is_sync_enabled_for_checkout``,
``resolve_checkout_sync_routing_readonly``) rather than internals.

Not covered here, and tracked in #3031 as separate work: capture is ungated
(Defect 3 — events reach the journal regardless of consent) and drain selection
filters per checkout rather than per event (Defect 5). Both need their own
fixtures; neither is pinned by this file.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from specify_cli.sync.routing import (
    is_sync_enabled_for_checkout,
    resolve_checkout_sync_routing_readonly,
)

pytestmark = pytest.mark.fast

# A realistic owner/repo pair: consent must not depend on the slug looking
# special, and this is the shape ``git_metadata.parse_repo_slug`` produces.
_REPO_SLUG = "regnology-example/engagement-assistant"


def _write_project_config(
    repo_root: Path,
    *,
    repo_slug: str = _REPO_SLUG,
    sync_enabled: bool | None = None,
) -> None:
    """Write a ``.kittify/config.yaml`` with a complete project identity.

    Mirrors the identity block a real checkout carries (``project.uuid`` /
    ``slug`` / ``node_id`` / ``repo_slug`` / ``build_id``) so routing resolves
    normally and the tests isolate the *consent* decision.

    When ``sync_enabled`` is not None a ``sync.enabled`` key is written. That
    key does not exist in the schema today — pinning it here is the point: the
    project must be able to record its own consent, in-repo and reviewable.
    """
    config_dir = repo_root / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "project:",
        f"  uuid: {uuid4()}",
        "  slug: engagement-assistant",
        "  node_id: node12345678",
        f"  repo_slug: {repo_slug}",
        "  build_id: 8a4a7da6-a97c-4bb4-893a-b31664abfee4",
    ]
    if sync_enabled is not None:
        lines += ["sync:", f"  enabled: {str(sync_enabled).lower()}"]
    (config_dir / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def isolated_machine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A checkout under a fresh HOME, with no machine-global sync config at all.

    This is the state of every project on a machine where the operator has never
    run ``sync opt-in`` or ``sync opt-out`` for it — i.e. the overwhelmingly
    common case, and the one the incident turned on.
    """
    home = tmp_path / "home"
    repo_root = tmp_path / "repo"
    home.mkdir()
    repo_root.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)
    monkeypatch.chdir(repo_root)
    return repo_root


def test_unconfigured_checkout_does_not_consent_to_sync(isolated_machine: Path) -> None:
    """INVARIANT: absence of a recorded decision is not consent.

    No checkout override and no repo default means nobody has said yes. The
    resolver currently returns ``True`` here (``routing.py:87``), which is what
    made every project on the incident machine sync-enabled without the operator
    ever choosing it.
    """
    _write_project_config(isolated_machine)

    routing = resolve_checkout_sync_routing_readonly()

    assert routing is not None, "a checkout with a valid identity must resolve routing"
    assert routing.local_sync_enabled is None, "fixture must record no local override"
    assert routing.repo_default_sync_enabled is None, "fixture must record no repo default"
    assert routing.effective_sync_enabled is False, (
        "an unconfigured checkout must not be treated as consenting to hosted sync; "
        "absence of a decision must resolve to deny"
    )


def test_unresolvable_routing_does_not_consent_to_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INVARIANT: a control that cannot determine consent must fail closed.

    A directory with no project identity yields ``routing is None``, and
    ``is_sync_enabled_for_checkout`` currently answers ``True`` for it
    (``routing.py:115-116``). An unidentifiable checkout is precisely the case
    where sending data is least defensible.
    """
    home = tmp_path / "home"
    stray = tmp_path / "not-a-spec-kitty-project"
    home.mkdir()
    stray.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)
    monkeypatch.chdir(stray)

    assert resolve_checkout_sync_routing_readonly() is None, (
        "fixture must produce an unresolvable checkout"
    )
    assert is_sync_enabled_for_checkout() is False, (
        "unresolvable routing must fail closed; an unidentifiable checkout must "
        "never be treated as consenting"
    )


def test_project_config_refusal_is_honoured(isolated_machine: Path) -> None:
    """INVARIANT: a project can record its own refusal, in its own repo.

    Consent currently lives only in machine-global config keyed by ``repo_slug``
    (``routing.read_local_sync_enabled``), so it is absent from the repository it
    governs, survives neither a fresh clone nor a remote rename, and cannot be
    reviewed in a diff. A ``sync.enabled`` key in ``.kittify/config.yaml`` must
    be read and honoured.
    """
    _write_project_config(isolated_machine, sync_enabled=False)

    assert is_sync_enabled_for_checkout() is False, (
        "an explicit `sync.enabled: false` in .kittify/config.yaml must be honoured"
    )


def test_project_config_refusal_outranks_env_override(
    isolated_machine: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INVARIANT: env may narrow consent, never widen it.

    ``SPEC_KITTY_ENABLE_SAAS_SYNC`` is process-global with no project-scoped
    form, so one shell export arms every project that shell touches — the direct
    cause of the incident. The least specific and least reviewable input must not
    override the most specific and most reviewable one.
    """
    _write_project_config(isolated_machine, sync_enabled=False)
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://example.invalid")

    assert is_sync_enabled_for_checkout() is False, (
        "an ambient env var must not override a project's explicit refusal to sync"
    )


def test_machine_global_opt_in_does_not_leak_to_sibling_projects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INVARIANT: consenting for one repository does not consent for another.

    The incident shape: one repository is legitimately opted in, and unrelated
    repositories on the same machine are silently in scope. Opting in repo A must
    leave repo B denying.
    """
    home = tmp_path / "home"
    consenting = tmp_path / "consenting-repo"
    unrelated = tmp_path / "unrelated-repo"
    for d in (home, consenting, unrelated):
        d.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)

    _write_project_config(consenting, repo_slug="my-org/intended-project")
    _write_project_config(unrelated, repo_slug="client-org/confidential-work")

    config_file = home / ".spec-kitty" / "config.toml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(
        '[sync.repo_defaults."my-org/intended-project"]\nenabled = true\n',
        encoding="utf-8",
    )

    monkeypatch.chdir(consenting)
    assert is_sync_enabled_for_checkout() is True, (
        "the explicitly opted-in repository must remain enabled"
    )

    monkeypatch.chdir(unrelated)
    assert is_sync_enabled_for_checkout() is False, (
        "a repository with no recorded decision must not inherit consent from a "
        "sibling project's opt-in"
    )
