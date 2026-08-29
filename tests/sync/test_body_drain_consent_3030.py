"""T025: the body-upload drain must resolve consent per task, from the task (#3030).

The last open egress path of the incident. ``sync now`` calls
``service.drain_body_uploads_only()`` (the command the operator ran twice on
2026-07-27), which runs ``_drain_body_queue``. Before this change that drain POSTed
**every** queued task, gated only by the machine-global ``is_saas_sync_enabled()``.

What travels is not metadata: ``body_upload.py``'s supported surfaces are
``spec.md``, ``plan.md``, ``tasks.md``, ``analysis-report.md``, ``research/``,
``contracts/``, ``checklists/`` and ``tasks/WP*.md`` — verbatim document text.

WP01's routing flip closed the *enqueue* side, so no new non-consenting bodies are
queued. It did nothing for the population that already exists: every body enqueued
before the flip is still on disk and drains on the next ``sync now``. That residual
population is what these tests are about.

Why the assertions are at the ``requests`` boundary rather than on ``push_content``:
a fail-closed claim is only worth what its witness observes. Patching
``push_content`` would prove a call was skipped; barricading the HTTP client proves
**no request left the process**, including via ``body_transport``'s stdlib fallback,
with the real payload-building and outcome-classification code in the path (SC-003's
pattern).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from specify_cli.sync.body_queue import OfflineBodyUploadQueue
from specify_cli.sync.consent import record_project_opt_in, record_project_opt_out
from specify_cli.sync.layout_generation import LayoutAuthorityError
from specify_cli.sync.namespace import NamespaceRef
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

UUID_A = "aaaaaaaa-0000-0000-0000-00000000000a"
UUID_B = "bbbbbbbb-0000-0000-0000-00000000000b"

CONFIDENTIAL_BODY = "# Spec\n\nAcme Corp engagement: migrate the payroll ledger.\n"


@pytest.fixture(autouse=True)
def _isolated_home(canonical_home: None, monkeypatch: pytest.MonkeyPatch) -> None:
    del canonical_home  # R1b (#3121): home isolation provided by the canonical SPEC_KITTY_HOME owner
    # The incident's actual mechanism: the env var was exported machine-wide. It
    # arms the machine and must never grant per-project consent, so leaving it set
    # here keeps these tests honest about what they prove.
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")


@dataclass
class _Egress:
    """Records every outbound HTTP attempt made by ``body_transport``."""

    status: int = 201
    posts: list[dict[str, Any]] = field(default_factory=list)

    def post(
        self,
        url: str,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> SimpleNamespace:
        import json

        del timeout
        payload = json.loads(data.decode("utf-8")) if data is not None else {}
        self.posts.append({"url": url, "json": payload, "headers": headers or {}})
        return SimpleNamespace(
            status_code=self.status,
            json=lambda: {
                "status": "stored",
                "artifact_path": payload.get("artifact_path"),
                "content_hash": payload.get("content_hash"),
            },
        )

    def fallback(self, method: str, url: str, **kwargs: Any) -> SimpleNamespace:
        """``body_transport``'s stdlib escape hatch — a second way bytes can leave."""
        self.posts.append({"url": url, "json": kwargs.get("json") or {}, "headers": kwargs.get("headers") or {}})
        return SimpleNamespace(status_code=self.status, json=lambda: {})

    @property
    def bodies(self) -> list[str]:
        return [str(post["json"].get("content_body", "")) for post in self.posts]

    @property
    def project_uuids(self) -> list[str]:
        return [str(post["json"].get("project_uuid", "")) for post in self.posts]


@pytest.fixture
def egress(monkeypatch: pytest.MonkeyPatch) -> _Egress:
    recorder = _Egress()
    monkeypatch.setattr(
        "specify_cli.sync.body_transport.requests",
        SimpleNamespace(
            post=recorder.post,
            ConnectionError=ConnectionError,
            Timeout=TimeoutError,
        ),
    )
    monkeypatch.setattr(
        "specify_cli.sync.body_transport.request_with_stdlib_fallback_sync",
        recorder.fallback,
    )
    return recorder


def _checkout(tmp_path: Path, name: str, *, uuid: str, hosted: bool | None) -> Path:
    """A checkout whose ``.kittify/config.yaml`` carries identity and consent."""
    root = tmp_path / name
    (root / ".kittify").mkdir(parents=True, exist_ok=True)
    lines = ["project:", f"  uuid: {uuid}", f"  slug: {name}"]
    if hosted is not None:
        lines += ["sync:", f"  enabled: {str(hosted).lower()}"]
    (root / ".kittify" / "config.yaml").write_text("\n".join(lines) + "\n")
    return root


def _enqueue_body(
    queue: Any,
    project_uuid: str,
    *,
    artifact_path: str = "spec.md",
    content: str = CONFIDENTIAL_BODY,
) -> None:
    """Queue one body the way ``prepare_body_uploads`` does, pre-flip."""
    import hashlib

    namespace = NamespaceRef(
        project_uuid=project_uuid,
        mission_slug="047-payroll",
        target_branch="main",
        mission_type="software-dev",
        manifest_version="1",
    )
    digest = hashlib.sha256(content.encode()).hexdigest()  # noqa: TID251 — body-integrity checksum, the queue's own protocol field
    queue.enqueue(
        namespace=namespace,
        artifact_path=artifact_path,
        content_hash=digest,
        content_body=content,
        size_bytes=len(content.encode()),
    )


def _store(project_uuid: str) -> ProjectSyncStore:
    store = ProjectSyncStore(project_uuid)
    authority = store.layout_generation()
    try:
        authority.begin_cutover("body-consent-test")
    except LayoutAuthorityError as exc:
        if "already project-only" not in str(exc):
            raise
    else:
        authority.publish_project_only("body-consent-test", verify_exact=lambda: True)
    return store


def _admit(project_uuid: str) -> ProjectSyncStore:
    record_project_opt_in(project_uuid, actor="body-consent-test")
    store = _store(project_uuid)
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, 'https://saas.example.test', 'account-1', 'teamspace-1', 1, "
            "'admitted', '1', 'private-teamspace:teamspace-1') "
            "ON CONFLICT(project_uuid) DO UPDATE SET admission_state='admitted'",
            (project_uuid,),
        )
    return store


class _ProjectBodyQueues:
    """Test facade that keeps every body operation in its owning project store."""

    def __init__(self) -> None:
        self._projects: set[str] = set()

    def enqueue(self, *, namespace: NamespaceRef, **kwargs: Any) -> object:
        project_uuid = namespace.project_uuid
        self._projects.add(project_uuid)
        store = _store(project_uuid)
        with store.unit_of_work() as unit:
            return OfflineBodyUploadQueue(unit, store.layout_generation()).enqueue(
                namespace=namespace,
                **kwargs,
            )

    def size(self) -> int:
        total = 0
        for project_uuid in self._projects:
            store = _store(project_uuid)
            with store.unit_of_work() as unit:
                total += OfflineBodyUploadQueue(unit, store.layout_generation()).size()
        return total

    def get_stats(self) -> SimpleNamespace:
        retry_counts: list[int] = []
        for project_uuid in self._projects:
            store = _store(project_uuid)
            with store.unit_of_work() as unit:
                stats = OfflineBodyUploadQueue(unit, store.layout_generation()).get_stats()
            retry_counts.append(stats.max_retry_count)
        return SimpleNamespace(max_retry_count=max(retry_counts, default=0))


class _ProjectEventQueue:
    @staticmethod
    def size() -> int:
        return 0


def _service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """A ``BackgroundSyncService`` with a real body queue and a valid token."""
    from specify_cli.sync.background import BackgroundSyncService

    monkeypatch.setattr(
        "specify_cli.sync.background._fetch_access_token_sync", lambda: "test-token"
    )
    monkeypatch.setattr(
        "specify_cli.sync.background.is_saas_sync_enabled", lambda: True
    )

    del tmp_path
    config = MagicMock()
    config.resolve_runtime_target.return_value = SimpleNamespace(
        resolved_server_url="https://saas.example.test"
    )
    manager = MagicMock()
    manager.get_current_session.return_value = SimpleNamespace(
        email="account-1",
        teams=[SimpleNamespace(id="teamspace-1", is_private_teamspace=True)],
    )
    monkeypatch.setattr("specify_cli.sync.background.get_token_manager", lambda: manager)
    service = BackgroundSyncService(queue=_ProjectEventQueue(), config=config)
    service._body_queue = _ProjectBodyQueues()
    service._drain_body_queue = service._drain_discovered_body_queues
    return service


# --- FR-002: absence of a consent record denies, at drain time -------------


def test_body_for_a_project_with_no_consent_record_is_never_posted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, egress: _Egress
) -> None:
    """The residual population: enqueued pre-flip, drained by the next ``sync now``.

    Project A has no record anywhere — not an explicit opt-out. Silence, not
    refusal, is what the five leaked projects actually had, and a predicate that
    reads absence as consent is the defect itself.
    """
    service = _service(tmp_path, monkeypatch)
    _enqueue_body(service._body_queue, UUID_A)

    service.drain_body_uploads_only()

    assert egress.posts == [], (
        "a queued body for a project with no consent record must not reach the "
        f"network; the drain sent: {egress.bodies}"
    )
    assert CONFIDENTIAL_BODY not in "".join(egress.bodies)


def test_a_withheld_body_stays_queued_rather_than_being_dropped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, egress: _Egress
) -> None:
    """Residual-state decision: retained-and-ignored, not deleted.

    Deleting on refusal would destroy the operator's only evidence of what a
    pre-gate build queued, and would silently discard work that becomes sendable
    the moment the project consents. FR-016's ``sync purge`` (WP08) is the
    operator's explicit deletion path — this drain is not it. Mirrors
    ``flush_pending_local_commits``'s recorded choice for LocalCommit frames.
    """
    service = _service(tmp_path, monkeypatch)
    _enqueue_body(service._body_queue, UUID_A)

    service.drain_body_uploads_only()
    service.drain_body_uploads_only()  # idempotent: still withheld, still there

    assert egress.posts == []
    assert service._body_queue.size() == 1, "a refused body is retained, not dropped"
    assert service._body_queue.get_stats().max_retry_count == 0, (
        "withholding is not a delivery failure; it must not burn retry budget, "
        "or remove_stale() would eventually delete the evidence"
    )


def test_a_withheld_body_becomes_sendable_once_the_project_consents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, egress: _Egress
) -> None:
    """Retention has a point: the refusal is re-evaluated, not final."""
    service = _service(tmp_path, monkeypatch)
    _enqueue_body(service._body_queue, UUID_A)

    service.drain_body_uploads_only()
    assert egress.posts == []

    _admit(UUID_A)
    service.drain_body_uploads_only()

    assert egress.project_uuids == [UUID_A]
    assert service._body_queue.size() == 0


# --- C-006: consenting projects must keep working -------------------------


def test_body_for_a_consenting_project_still_drains(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, egress: _Egress
) -> None:
    """The gate must not be a body-upload kill switch."""
    service = _service(tmp_path, monkeypatch)
    _admit(UUID_A)
    _enqueue_body(service._body_queue, UUID_A)

    service.drain_body_uploads_only()

    # Whose body drained, not how many did. The sibling test below proves a drain
    # can hold two projects' bodies at once, so "one POST went out" is satisfied
    # just as well by A's body being withheld and some other project's shipped —
    # the exact confusion this gate exists to prevent. Assert the identity on the
    # wire, matching this file's refusal assertions.
    assert egress.project_uuids == [UUID_A]
    assert egress.posts[0]["url"].endswith("/api/dossier/push-content/")
    assert egress.bodies == [CONFIDENTIAL_BODY]
    assert service._body_queue.size() == 0


def test_consenting_and_non_consenting_bodies_are_separated_within_one_drain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, egress: _Egress
) -> None:
    """One drain, two projects, one decision each — not one decision for the batch."""
    service = _service(tmp_path, monkeypatch)
    _admit(UUID_B)
    _enqueue_body(service._body_queue, UUID_A, artifact_path="spec.md")
    _enqueue_body(service._body_queue, UUID_B, artifact_path="plan.md")

    service.drain_body_uploads_only()

    assert egress.project_uuids == [UUID_B]
    assert service._body_queue.size() == 1, "A's body is retained, B's is delivered"


# --- NFR-001: the decision comes from the task, never from cwd ------------


def test_standing_in_a_consenting_checkout_does_not_authorize_another_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, egress: _Egress
) -> None:
    """The cwd-derived defect, made observable.

    The queued body belongs to project A, which has no consent record. The drain
    runs with cwd inside project B, which consents. ``is_sync_enabled_for_checkout``
    (or any resolution keyed on the working directory) answers "yes" here and ships
    A's document. Resolving from ``task.project_uuid`` refuses.

    This is the same substitution T027 names for LocalCommit frames and M1 names for
    the capture path — a daemon, a monorepo of worktrees, or any agent session that
    ``cd``s between checkouts hits it.
    """
    service = _service(tmp_path, monkeypatch)
    consenting_b = _checkout(tmp_path, "project-b", uuid=UUID_B, hosted=True)
    _enqueue_body(service._body_queue, UUID_A)
    monkeypatch.chdir(consenting_b)

    service.drain_body_uploads_only()

    assert egress.posts == [], (
        "consent was resolved from the working directory, not from the task: "
        f"project B's grant shipped project A's body ({egress.project_uuids})"
    )
    assert service._body_queue.size() == 1


def test_standing_in_an_opted_out_checkout_does_not_block_a_consenting_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, egress: _Egress
) -> None:
    """The mirror image, and the reason a cwd-derived fix is not merely equivalent.

    A consents (recorded uuid-keyed, as ``enable_checkout_sync`` writes it); cwd is
    inside B, which is explicitly opted out. A cwd-derived gate withholds A's body —
    silently, indefinitely — which is C-006's "do not break body uploads for
    consenting projects" failing in the quiet direction.
    """
    service = _service(tmp_path, monkeypatch)
    _admit(UUID_A)
    opted_out_b = _checkout(tmp_path, "project-b", uuid=UUID_B, hosted=False)
    _enqueue_body(service._body_queue, UUID_A)
    monkeypatch.chdir(opted_out_b)

    service.drain_body_uploads_only()

    assert egress.project_uuids == [UUID_A]


def test_the_projects_own_committed_refusal_is_honoured_from_its_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, egress: _Egress
) -> None:
    """Level 1 of the chain is reachable from the drain (FR-019).

    A prior grant must not survive the project's current durable refusal. The
    checkout remains a narrowing input, never the replacement authority.
    """
    service = _service(tmp_path, monkeypatch)
    _admit(UUID_A)
    refusing_a = _checkout(tmp_path, "project-a", uuid=UUID_A, hosted=False)
    _enqueue_body(service._body_queue, UUID_A)
    record_project_opt_out(UUID_A, actor="body-consent-test")
    monkeypatch.chdir(refusing_a)

    service.drain_body_uploads_only()

    assert egress.posts == []


def test_a_body_with_no_resolvable_project_identity_is_never_posted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, egress: _Egress
) -> None:
    """NFR-001's second half: ``None`` ∉ delivered.

    The project-owned queue refuses a blank ``project_uuid`` before persistence,
    so no unresolved row can become a production discovery candidate.
    """
    service = _service(tmp_path, monkeypatch)
    _admit(UUID_A)
    _enqueue_body(service._body_queue, UUID_A, artifact_path="plan.md")
    with pytest.raises(ValueError):
        _enqueue_body(service._body_queue, "", artifact_path="spec.md")

    service.drain_body_uploads_only()

    assert egress.project_uuids == [UUID_A], "only the identified, consenting body ships"
    assert service._body_queue.size() == 0


# --- NFR-002: the predicate precedes the row limit ------------------------


def test_a_wall_of_withheld_bodies_does_not_starve_a_consenting_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, egress: _Egress
) -> None:
    """Filtering after ``LIMIT`` would strand the consenting project permanently.

    ``drain()`` reads 50 rows ordered by ``created_at``. Withheld rows stay queued,
    so if the predicate ran after the window, the same 50 non-consenting rows would
    fill every window of every tick and the consenting body behind them would never
    be reached — not "later", never. This is NFR-002's starvation on the body store.
    """
    service = _service(tmp_path, monkeypatch)
    _admit(UUID_B)
    for index in range(60):
        _enqueue_body(service._body_queue, UUID_A, artifact_path=f"tasks/WP{index:02d}-x.md")
    _enqueue_body(service._body_queue, UUID_B, artifact_path="spec.md")

    service.drain_body_uploads_only()

    assert egress.project_uuids == [UUID_B], (
        "the consenting project's body sat behind 60 withheld rows and was never "
        "reached — the consent predicate ran after the LIMIT"
    )
    assert service._body_queue.size() == 60
