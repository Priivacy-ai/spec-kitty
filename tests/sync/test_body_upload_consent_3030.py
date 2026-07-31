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

from pathlib import Path

import pytest

from specify_cli.core.paths import locate_project_root
from specify_cli.dossier.models import ArtifactRef
from specify_cli.sync.body_queue import OfflineBodyUploadQueue
from specify_cli.sync.body_upload import prepare_body_uploads
from specify_cli.sync.config import SyncConfig
from specify_cli.sync.consent import set_project_consent
from specify_cli.sync.namespace import NamespaceRef, UploadStatus

pytestmark = [pytest.mark.fast]

UUID_A = "aaaaaaaa-3030-0000-0000-00000000031a"

CONFIDENTIAL_BODY = "# Spec\n\nAcme Holdings carve-out: draft the disclosure schedule.\n"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-case machine state, plus the incident's own mechanism left armed.

    ``SPEC_KITTY_ENABLE_SAAS_SYNC`` was exported machine-wide on 2026-07-27. It arms
    the machine and must never grant per-project consent, so leaving it set here keeps
    every assertion below honest about what it proves.
    """
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    # ``locate_project_root`` treats this var as authoritative when set; an inherited
    # value would silently turn the "root does not resolve" case into a different test.
    monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)


def _queue(tmp_path: Path) -> OfflineBodyUploadQueue:
    return OfflineBodyUploadQueue(db_path=tmp_path / "bodies.db")


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
    """The control. Without this passing, every refusal below proves nothing."""
    root = _checkout(tmp_path, "consenting", uuid=UUID_A, hosted=True)
    feature_dir, artifacts = _feature_dir(root)
    queue = _queue(tmp_path)

    outcomes = prepare_body_uploads(
        artifacts=artifacts,
        namespace_ref=_namespace(),
        body_queue=queue,
        feature_dir=feature_dir,
    )

    assert [o.status for o in outcomes] == [UploadStatus.QUEUED]
    assert queue.count_by_project() == {UUID_A: 1}


def test_machine_index_grant_enqueues_when_the_checkout_is_unresolvable(
    tmp_path: Path,
) -> None:
    """Second control, and the boundary of the fix.

    Resolving from the namespace's own ``project_uuid`` means an unresolvable checkout
    is no longer *fatal* — it is simply not a source of a project-local vote. A uuid
    with a recorded machine-index grant is still a determined answer, so it enqueues.
    This is what stops the fix from being "deny whenever ``locate_project_root``
    returns ``None``", which would be a different (and wrong) rule.
    """
    loose = tmp_path / "not-a-project"
    feature_dir, artifacts = _feature_dir(loose)
    assert locate_project_root(feature_dir) is None, "precondition: no project root"
    set_project_consent(UUID_A, True)
    queue = _queue(tmp_path)

    outcomes = prepare_body_uploads(
        artifacts=artifacts,
        namespace_ref=_namespace(),
        body_queue=queue,
        feature_dir=feature_dir,
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
    queue = _queue(tmp_path)

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


def test_repo_slug_default_does_not_consent_to_body_enqueue(tmp_path: Path) -> None:
    """FR-031(b) / FR-019: ``[sync.repo_defaults]`` is not a consent level.

    The routing chain honours a grant keyed on the git remote slug; the consent chain
    deliberately does not, because a fresh clone or a ``git init`` inherits a decision
    nobody made about it. Here the project has **no** record of its own and **no**
    entry in the uuid-keyed index — only a repo-slug default — so the two chains
    disagree, and the gate must follow the consent chain.
    """
    root = _checkout(tmp_path, "slug-default", uuid=UUID_A, hosted=None)
    feature_dir, artifacts = _feature_dir(root)
    SyncConfig().set_repository_sync_enabled("acme/carve-out", True)

    from specify_cli.sync.routing import is_sync_enabled_for_checkout

    import specify_cli.sync.git_metadata as git_metadata_mod

    # Pin the repo slug so the routing chain reaches its repo-default level. Patching
    # the metadata resolver rather than creating a git remote keeps the divergence,
    # not git plumbing, as the thing under test.
    real_resolve = git_metadata_mod.GitMetadataResolver.resolve

    def _resolve(self):  # type: ignore[no-untyped-def]
        meta = real_resolve(self)
        return type(meta)(**{**meta.__dict__, "repo_slug": "acme/carve-out"})

    git_metadata_mod.GitMetadataResolver.resolve = _resolve  # type: ignore[method-assign]
    try:
        assert is_sync_enabled_for_checkout(root) is True, (
            "precondition: the routing chain must GRANT here, or the divergence "
            "this test is about is not present"
        )
        queue = _queue(tmp_path)
        outcomes = prepare_body_uploads(
            artifacts=artifacts,
            namespace_ref=_namespace(),
            body_queue=queue,
            feature_dir=feature_dir,
        )
    finally:
        git_metadata_mod.GitMetadataResolver.resolve = real_resolve  # type: ignore[method-assign]

    assert [o.status for o in outcomes] == [UploadStatus.SKIPPED]
    assert queue.count_by_project() == {}, (
        "a repo-slug default granted egress for a project that never consented"
    )


def test_project_local_refusal_still_withholds(tmp_path: Path) -> None:
    """A committed ``sync.enabled: false`` keeps refusing after the chain swap.

    The pre-fix gate got this case right through the routing chain; the fix must not
    lose it while changing which chain answers.
    """
    root = _checkout(tmp_path, "refusing", uuid=UUID_A, hosted=False)
    feature_dir, artifacts = _feature_dir(root)
    set_project_consent(UUID_A, True)  # a stale machine-index grant must not win
    queue = _queue(tmp_path)

    outcomes = prepare_body_uploads(
        artifacts=artifacts,
        namespace_ref=_namespace(),
        body_queue=queue,
        feature_dir=feature_dir,
    )

    assert [o.status for o in outcomes] == [UploadStatus.SKIPPED]
    assert queue.count_by_project() == {}
