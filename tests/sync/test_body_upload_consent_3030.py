"""FR-031: the body-upload *enqueue* gate must ask the consent chain, and fail closed.

``sync/body_upload.py`` guarded ``prepare_body_uploads`` with::

    repo_root = locate_project_root(feature_dir)
    if repo_root is not None and not is_sync_enabled_for_checkout(repo_root):
        ...skip everything...

Two defects in that one line, and this module holds one red for each:

(a) **Fail-open.** ``repo_root is not None and`` makes an unresolvable project root
    skip the gate entirely — undetermined read as consent, FR-003's rule verbatim and
    its fourth independent occurrence in this codebase.

(b) **Wrong chain.** ``is_sync_enabled_for_checkout`` walks the *routing* chain, which
    honours the repo-slug-keyed ``[sync.repo_defaults]`` record. FR-019 condemns that
    record precisely because it is keyed on a mutable git remote and cannot speak for a
    project, and ``sync/__init__.py``'s own egress-consent resolver already records why
    it must not be used for an egress question. Two gates on one path reading two
    different chains is the C-003 divergence.

What travels is not metadata. ``body_upload``'s supported surfaces are ``spec.md``,
``plan.md``, ``tasks.md``, ``analysis-report.md``, ``research/``, ``contracts/``,
``checklists/`` and ``tasks/WP*.md`` — verbatim document text, and for the
2026-07-27 population those documents carry client engagement names.

The witness is the **queue**, not the returned outcomes: an outcome list says what the
function reported, the store says what it actually staged for the live drain.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from specify_cli.core.paths import locate_project_root
from specify_cli.dossier.models import ArtifactRef
from specify_cli.sync.body_queue import OfflineBodyUploadQueue
from specify_cli.sync.body_upload import prepare_body_uploads
from specify_cli.sync.config import SyncConfig
from specify_cli.sync.consent import (
    LegacyConsentMigrationRequiredError,
    record_project_opt_in,
    record_project_opt_out,
    set_project_consent,
)
from specify_cli.sync.namespace import NamespaceRef, UploadStatus
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

UUID_A = "aaaaaaaa-3030-0000-0000-00000000031a"

CONFIDENTIAL_BODY = "# Spec\n\nAcme Holdings carve-out: draft the disclosure schedule.\n"


@pytest.fixture(autouse=True)
def _isolated_home(canonical_home: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-case machine state, plus the incident's own mechanism left armed.

    ``SPEC_KITTY_ENABLE_SAAS_SYNC`` was exported machine-wide on 2026-07-27. It arms
    the machine and must never grant per-project consent, so leaving it set here keeps
    every assertion below honest about what it proves.
    """
    del canonical_home  # R1b (#3121): home isolation provided by the canonical SPEC_KITTY_HOME owner
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    # ``locate_project_root`` treats this var as authoritative when set; an inherited
    # value would silently turn the "root does not resolve" case into a different test.
    monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)


@contextmanager
def _capture_unit():
    """The UUID-owned project store's active unit of work, plus its authorities.

    ``OfflineBodyUploadQueue`` no longer takes ``db_path``: live payload stores are
    selected by ``ProjectSyncStore`` per project uuid (rooted in the per-test
    ``SPEC_KITTY_HOME``), and the queue is a short-lived adapter over one active
    unit of work.
    """
    store = ProjectSyncStore(UUID_A)
    authority = store.layout_generation()
    authority.begin_cutover("body-consent-3030-tests")
    authority.publish_project_only("body-consent-3030-tests", verify_exact=lambda: True)
    with store.unit_of_work() as unit:
        yield store, unit, authority, OfflineBodyUploadQueue(unit, authority)


@contextmanager
def _queue() -> Iterator[OfflineBodyUploadQueue]:
    with _capture_unit() as (_store, _unit, _authority, queue):
        yield queue


def _namespace(uuid: str = UUID_A) -> NamespaceRef:
    return NamespaceRef(
        project_uuid=uuid,
        mission_slug="047-acme-carve-out",
        target_branch="main",
        mission_type="software-dev",
        manifest_version="1",
    )


def _feature_dir(parent: Path) -> tuple[Path, list[ArtifactRef]]:
    """A mission dossier carrying one real, verbatim ``spec.md``."""
    import hashlib

    feature_dir = parent / "kitty-specs" / "047-acme-carve-out"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text(CONFIDENTIAL_BODY, encoding="utf-8")
    digest = hashlib.sha256(CONFIDENTIAL_BODY.encode("utf-8")).hexdigest()  # noqa: TID251 - test fixture mirrors the indexer
    return feature_dir, [
        ArtifactRef(
            artifact_key="input.spec_md",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256=digest,
            size_bytes=len(CONFIDENTIAL_BODY.encode("utf-8")),
            is_present=True,
        )
    ]


def _checkout(tmp_path: Path, name: str, *, uuid: str, hosted: bool | None) -> Path:
    """A checkout whose ``.kittify/config.yaml`` carries identity and (maybe) consent."""
    root = tmp_path / name
    (root / ".kittify").mkdir(parents=True, exist_ok=True)
    lines = ["project:", f"  uuid: {uuid}", f"  slug: {name}"]
    if hosted is not None:
        lines += ["sync:", f"  enabled: {str(hosted).lower()}"]
    (root / ".kittify" / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


# --------------------------------------------------------------------------
# Positive control — the harness must be able to enqueue at all.
# --------------------------------------------------------------------------


def test_consenting_project_still_enqueues_its_bodies(tmp_path: Path) -> None:
    """The control. Without this passing, every refusal below proves nothing.

    Consent is recorded through the only surviving grant path: the explicit
    UUID-owned project opt-in (``record_project_opt_in``). The checkout's own
    ``sync.enabled: true`` is a legacy diagnostic and never grants.

    The control runs the *explicit* same-UoW authority path — production's only
    positive path since the per-project store cutover (``dossier_pipeline`` always
    mints the context from the active unit). The legacy keyword path below cannot
    grant while the queue's own unit of work is live, because a second same-store
    consent read reports UNREADABLE, and undetermined is not consent (FR-003).
    So this proves the store plumbing can enqueue at all, which is what makes the
    refusals' empty queues below evidence rather than a fixture artefact.
    """
    root = _checkout(tmp_path, "consenting", uuid=UUID_A, hosted=True)
    feature_dir, artifacts = _feature_dir(root)
    record_project_opt_in(UUID_A, actor="body-consent-3030-tests")

    with _capture_unit() as (store, unit, authority, queue):
        outcomes = prepare_body_uploads(
            artifacts=artifacts,
            namespace_ref=_namespace(),
            body_queue=queue,
            feature_dir=feature_dir,
            project_context=store.create_context_from_unit(unit),
            project_unit=unit,
            project_layout=authority,
        )

        assert [o.status for o in outcomes] == [UploadStatus.QUEUED]
        assert queue.count_by_project() == {UUID_A: 1}


def test_explicit_uuid_grant_enqueues_when_the_checkout_is_unresolvable(
    tmp_path: Path,
) -> None:
    """Second control, and the boundary of the fix.

    Resolving from the namespace's own ``project_uuid`` means an unresolvable checkout
    is no longer *fatal* — it is simply not a source of a project-local vote. A uuid
    with an explicit UUID-owned opt-in (the machine index is retired and
    non-authoritative) still has a determined answer, so it enqueues. This is what
    stops the fix from being "deny whenever ``locate_project_root`` returns
    ``None``", which would be a different (and wrong) rule.
    """
    loose = tmp_path / "not-a-project"
    feature_dir, artifacts = _feature_dir(loose)
    assert locate_project_root(feature_dir) is None, "precondition: no project root"
    record_project_opt_in(UUID_A, actor="body-consent-3030-tests")

    with _capture_unit() as (store, unit, authority, queue):
        outcomes = prepare_body_uploads(
            artifacts=artifacts,
            namespace_ref=_namespace(),
            body_queue=queue,
            feature_dir=feature_dir,
            project_context=store.create_context_from_unit(unit),
            project_unit=unit,
            project_layout=authority,
        )

        assert [o.status for o in outcomes] == [UploadStatus.QUEUED]
        assert queue.count_by_project() == {UUID_A: 1}


# --------------------------------------------------------------------------
# (a) Fail-open: an unresolvable project root skipped the gate entirely.
# --------------------------------------------------------------------------


def test_unresolvable_project_root_does_not_consent_to_body_enqueue(
    tmp_path: Path,
) -> None:
    """FR-031(a) / FR-003: undetermined is not consent.

    Before the fix ``repo_root is not None and ...`` short-circuited to ``False``, the
    whole gate was skipped, and the verbatim ``spec.md`` text was staged into the queue
    the body drain reads.
    """
    loose = tmp_path / "not-a-project"
    feature_dir, artifacts = _feature_dir(loose)
    assert locate_project_root(feature_dir) is None, "precondition: no project root"

    with _queue() as queue:
        outcomes = prepare_body_uploads(
            artifacts=artifacts,
            namespace_ref=_namespace(),
            body_queue=queue,
            feature_dir=feature_dir,
        )

        assert [o.status for o in outcomes] == [UploadStatus.SKIPPED]
        assert queue.count_by_project() == {}, (
            "a project whose consent could not be determined had its spec.md staged "
            "for the body drain"
        )


# --------------------------------------------------------------------------
# (b) Wrong chain: a repo-slug default granted where the project never did.
# --------------------------------------------------------------------------


def test_repo_slug_default_does_not_consent_to_body_enqueue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-031(b) / FR-019: ``[sync.repo_defaults]`` is not a consent level.

    FR-019 condemned the repo-slug default because a fresh clone or a ``git init``
    inherits a decision nobody made about it. The C-003 divergence — the routing
    chain granting from it while the consent chain refused — is now closed at the
    source: the writer refuses (``LegacyConsentMigrationRequiredError``), and even a
    legacy on-disk record survives only as a *diagnostic*. The routing chain answers
    from the UUID-owned decision, so no chain grants, and the gate must withhold.
    """
    root = _checkout(tmp_path, "slug-default", uuid=UUID_A, hosted=None)
    feature_dir, artifacts = _feature_dir(root)

    # The retired writer must refuse — a repo-slug default can no longer be minted.
    with pytest.raises(LegacyConsentMigrationRequiredError):
        SyncConfig().set_repository_sync_enabled("acme/carve-out", True)

    # Plant the legacy record directly on disk, as a machine migrated from the old
    # world would carry it. It must be visible as a diagnostic and grant nothing.
    config = SyncConfig()
    config.config_file.parent.mkdir(parents=True, exist_ok=True)
    config.config_file.write_text(
        '[sync.repo_defaults."acme/carve-out"]\nenabled = true\n',
        encoding="utf-8",
    )
    assert SyncConfig().get_repository_sync_enabled("acme/carve-out") is True, (
        "precondition: the legacy repo-slug default must be present on disk, or the "
        "level this test is about is not exercised"
    )

    import specify_cli.sync.git_metadata as git_metadata_mod

    from specify_cli.sync.routing import (
        is_sync_enabled_for_checkout,
        resolve_checkout_sync_routing_readonly,
    )

    # Pin the repo slug so the routing chain reaches its repo-default level. Patching
    # the metadata resolver rather than creating a git remote keeps the level,
    # not git plumbing, as the thing under test.
    real_resolve = git_metadata_mod.GitMetadataResolver.resolve

    def _resolve(self):  # type: ignore[no-untyped-def]
        meta = real_resolve(self)
        return type(meta)(**{**meta.__dict__, "repo_slug": "acme/carve-out"})

    monkeypatch.setattr(git_metadata_mod.GitMetadataResolver, "resolve", _resolve)

    routing = resolve_checkout_sync_routing_readonly(start=root)
    assert routing is not None
    assert routing.repo_default_sync_enabled is True, (
        "precondition: the routing chain must SEE the repo-slug default, or the "
        "level this test is about is not present"
    )
    # Stronger than the original divergence premise: the routing chain itself no
    # longer grants from the repo-slug default, so the two gates cannot diverge.
    assert is_sync_enabled_for_checkout(root) is False

    with _queue() as queue:
        outcomes = prepare_body_uploads(
            artifacts=artifacts,
            namespace_ref=_namespace(),
            body_queue=queue,
            feature_dir=feature_dir,
        )

        assert [o.status for o in outcomes] == [UploadStatus.SKIPPED]
        assert queue.count_by_project() == {}, (
            "a repo-slug default granted egress for a project that never consented"
        )


def test_project_local_refusal_still_withholds(tmp_path: Path) -> None:
    """An explicit refusal keeps refusing, and no stale grant can outrank it.

    The refusal authority moved from the committed ``sync.enabled: false`` (now a
    diagnostic) to the explicit UUID-owned opt-out. Two properties survive the move:

    * a refusal recorded *after* a genuine grant wins — later explicit decisions
      outrank earlier ones; and
    * the retired machine-index writer (``set_project_consent``) cannot mint a
      stale grant at all any more — it raises instead of writing.
    """
    root = _checkout(tmp_path, "refusing", uuid=UUID_A, hosted=False)
    feature_dir, artifacts = _feature_dir(root)
    record_project_opt_in(UUID_A, actor="body-consent-3030-tests")  # a real prior grant
    with pytest.raises(LegacyConsentMigrationRequiredError):
        set_project_consent(UUID_A, True)  # a stale machine-index grant cannot even be written
    record_project_opt_out(UUID_A, actor="body-consent-3030-tests")  # the refusal must win

    with _queue() as queue:
        outcomes = prepare_body_uploads(
            artifacts=artifacts,
            namespace_ref=_namespace(),
            body_queue=queue,
            feature_dir=feature_dir,
        )

        assert [o.status for o in outcomes] == [UploadStatus.SKIPPED]
        assert queue.count_by_project() == {}
