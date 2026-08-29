"""Regression guard for the hosted-sync consent fix (#3031).

Formerly the RED-FIRST P0 reproduction (ADR 2026-07-17-1); now green and
guarding the fix (the ``@pytest.mark.regression`` marker was removed once
these tests passed — landing fold: make the marker mean exactly one thing).

These tests encode the invariants a confidentiality control must satisfy.

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

import os
from pathlib import Path
from uuid import uuid4

import pytest

from specify_cli.sync.routing import (
    CheckoutSyncRouting,
    is_sync_enabled_for_checkout,
    resolve_checkout_sync_routing_readonly,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.unit, pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

# A realistic owner/repo pair: consent must not depend on the slug looking
# special, and this is the shape ``git_metadata.parse_repo_slug`` produces.
_REPO_SLUG = "regnology-example/engagement-assistant"


def _first_ancestor_with_repo_marker(start: Path) -> Path | None:
    """Return the first ancestor of ``start`` (inclusive) that is a *candidate*
    for carrying a repo marker.

    Diagnostic only, for failure messages — checks for either marker
    ``locate_project_root``'s walk-up tier looks for (``core/paths.py``: a
    ``.git`` entry or a ``.kittify`` directory), but does not reimplement that
    function's actual resolution rule, so the ancestor named here is a
    *candidate*, not necessarily where ``locate_project_root`` would land: a
    bare ``.git`` *directory* alone is NOT sufficient there — it additionally
    requires a sibling ``.kittify`` at the same candidate (or a ``.git`` *file*
    with worktree topology) — only a bare ``.kittify`` directory resolves
    unconditionally. If the candidate returned here is a ``.git`` directory
    with no sibling ``.kittify``, the actual culprit ``locate_project_root``
    would walk to is a different ancestor higher up, unreported by this helper.
    Its job is to name, in an assertion message, where a repo-root walk-up
    might land — the ``/tmp``-root-walk artifact (#3115): a developer whose
    machine has such a marker at or above the pytest tmp root gets a bare
    consent-gate failure with nothing pointing at the offending directory.
    """
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists() or (candidate / ".kittify").exists():
            return candidate
    return None


def _write_project_config(
    repo_root: Path,
    *,
    repo_slug: str = _REPO_SLUG,
    sync_enabled: bool | None = None,
) -> str:
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
    project_uuid = str(uuid4())
    lines = [
        "project:",
        f"  uuid: {project_uuid}",
        "  slug: engagement-assistant",
        "  node_id: node12345678",
        f"  repo_slug: {repo_slug}",
        "  build_id: 8a4a7da6-a97c-4bb4-893a-b31664abfee4",
    ]
    if sync_enabled is not None:
        lines += ["sync:", f"  enabled: {str(sync_enabled).lower()}"]
    (config_dir / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return project_uuid


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

    # Precondition, asserted rather than assumed (#3115): the fixture's claim of
    # "unresolvable" depends on nothing above ``stray`` carrying a ``.git``/
    # ``.kittify`` marker, and on ``SPECIFY_REPO_ROOT`` (tier-1 authoritative in
    # ``core/paths.py``) being unset. Neither was previously named on failure, so
    # a machine violating either produced the same bare "fixture must produce an
    # unresolvable checkout" message as a real regression in the routing/consent
    # code this test exists to pin — indistinguishable from the code under test.
    # Naming the candidate ancestor and the env var's value here is what turns
    # that mystery failure into "delete this directory" or "unset this variable" —
    # but ONLY when one of them is actually present. Attributing to #3115
    # unconditionally would misdiagnose a real routing regression (e.g. a future
    # change replacing the `repo_root is None -> None` branch at routing.py:81-82
    # with a fallback that resolves something): this assertion would then be the
    # only failure in the file, and an unconditional "machine artefact, go delete
    # a directory" message would send a reader looking for a marker that was
    # never there while the actual defect went unreported (the #3030 "no resolver
    # is registered" failure shape). So the attribution is conditioned on the
    # evidence actually gathered, not asserted regardless of it.
    offending_candidate = _first_ancestor_with_repo_marker(stray)
    specify_repo_root = os.environ.get("SPECIFY_REPO_ROOT")
    if offending_candidate is not None or specify_repo_root is not None:
        diagnosis = (
            f"locate_project_root would plausibly resolve one from {stray} — "
            f"candidate ancestor (inclusive) carrying a bare .git/.kittify "
            f"marker: {offending_candidate!r} (locate_project_root additionally "
            "requires .kittify alongside a bare .git directory, so the actual "
            f"walk-up may land on a different, higher ancestor); "
            f"SPECIFY_REPO_ROOT={specify_repo_root!r}. This is consistent with "
            "a machine-specific /tmp-root-walk artifact (spec-kitty#3115), not "
            "a defect in routing: delete/relocate the marker directory, or "
            "unset SPECIFY_REPO_ROOT, and retry."
        )
    else:
        diagnosis = (
            f"no ancestor of {stray} carries a .git/.kittify marker and "
            "SPECIFY_REPO_ROOT is unset, so no machine-specific cause was "
            "found. This looks like a routing regression — "
            "resolve_checkout_sync_routing_readonly (or locate_project_root) "
            "resolved a checkout here when it should have reported "
            "unresolvable — not the /tmp-root-walk artifact (spec-kitty#3115); "
            "investigate routing.py and core/paths.py rather than the "
            "filesystem."
        )
    assert resolve_checkout_sync_routing_readonly() is None, (
        f"fixture must produce an unresolvable checkout, but {diagnosis}"
    )
    assert is_sync_enabled_for_checkout() is False, (
        "unresolvable routing must fail closed; an unidentifiable checkout must "
        "never be treated as consenting"
    )


def test_unresolvable_routing_fails_closed_independent_of_filesystem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """INVARIANT pin (#3115), filesystem-independent: unresolvable routing denies.

    The test above pins the same invariant by walking a real filesystem up from
    a real ``tmp_path`` — which is exactly what lets a machine-specific repo-root
    marker (the ``/tmp``-root-walk artifact) make that fixture stop producing
    the ``None`` it depends on, without the *invariant* itself having changed.
    This pin forces the resolution seam
    (``resolve_checkout_sync_routing_readonly``) to answer "unresolvable"
    directly, so it exercises the same fail-closed branch of
    ``is_sync_enabled_for_checkout`` without walking any directory at all: no
    machine's filesystem contents can silently remove this coverage of the
    requirement. It is paired with
    ``test_unresolvable_routing_fails_closed_independent_of_filesystem_positive_control``
    below: on its own, an assertion of ``False`` here would pass for a stub that
    never reaches ``routing.effective_sync_enabled`` at all (or for a caught
    exception, or a future short-circuit) exactly as well as for the fail-closed
    branch under test; the positive control is what proves the seam was actually
    consulted, by demanding the *opposite* answer when it resolves and consents.
    """
    monkeypatch.setattr(
        "specify_cli.sync.routing.resolve_checkout_sync_routing_readonly",
        lambda start=None: None,
    )

    assert is_sync_enabled_for_checkout() is False, (
        "is_sync_enabled_for_checkout must fail closed when the routing seam "
        "reports unresolvable — regardless of what the filesystem contains — "
        "because it would otherwise have returned the forced routing's own "
        "effective_sync_enabled (see the positive control, which forces a "
        "resolvable, consenting routing through the same seam and asserts True)"
    )


def test_unresolvable_routing_fails_closed_independent_of_filesystem_positive_control(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Positive control for the pin above: the seam is genuinely consulted.

    Forces the identical resolution seam to resolve to a consenting routing and
    asserts ``True``. Without this, the fail-closed pin above would pass just as
    well for an implementation that returns ``False`` unconditionally — never
    reaching ``resolve_checkout_sync_routing_readonly`` or
    ``routing.effective_sync_enabled`` at all — as for the real fail-closed
    branch it is meant to pin. This is what discriminates the two.
    """
    consenting_routing = CheckoutSyncRouting(
        repo_root=tmp_path,
        project_uuid="00000000-0000-0000-0000-000000000000",
        project_slug="engagement-assistant",
        build_id="8a4a7da6-a97c-4bb4-893a-b31664abfee4",
        repo_slug=_REPO_SLUG,
        local_sync_enabled=True,
        repo_default_sync_enabled=None,
        effective_sync_enabled=True,
    )
    monkeypatch.setattr(
        "specify_cli.sync.routing.resolve_checkout_sync_routing_readonly",
        lambda start=None: consenting_routing,
    )

    assert is_sync_enabled_for_checkout() is True, (
        "is_sync_enabled_for_checkout must return the resolved routing's own "
        "effective_sync_enabled when the routing seam resolves to a consenting "
        "checkout; it would otherwise have returned False only because the seam "
        "was forced unresolvable in the paired pin above, not because consent "
        "was actually denied"
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

    consenting_uuid = _write_project_config(consenting, repo_slug="my-org/intended-project")
    _write_project_config(unrelated, repo_slug="client-org/confidential-work")

    # The only grant path left is the explicit UUID-owned per-project opt-in;
    # machine-global config is non-authoritative (diagnostic only). Record the
    # legacy machine-global entry anyway to prove it neither grants for the
    # sibling nor is needed for the opted-in project.
    from specify_cli.sync.consent import record_project_opt_in

    config_file = home / ".spec-kitty" / "config.toml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(
        '[sync.repo_defaults."my-org/intended-project"]\nenabled = true\n',
        encoding="utf-8",
    )
    record_project_opt_in(consenting_uuid, actor="tester")

    monkeypatch.chdir(consenting)
    assert is_sync_enabled_for_checkout() is True, (
        "the explicitly opted-in repository must remain enabled"
    )

    monkeypatch.chdir(unrelated)
    assert is_sync_enabled_for_checkout() is False, (
        "a repository with no recorded decision must not inherit consent from a "
        "sibling project's opt-in"
    )
