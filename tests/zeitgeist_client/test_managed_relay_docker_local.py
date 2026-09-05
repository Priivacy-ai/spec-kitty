"""FIX-M2-15 acceptance criterion 3: a REAL-container contract proof that
the bundled Zeitgeist client's two-credential fix (``transport.
ClientConfig.capability_credential`` / ``filtered_stream.TeamStreamConfig.
relay_token``) actually closes the gap DQA-M2-05 found -- not against this
package's own recording/protocol-faithful doubles (``conftest.py``'s
``ManagedControlDouble``/``ManagedStreamAuthDouble``), but against the
REAL, unmodified ``dkr-m1-02-zeitgeist:contract`` image, provisioned
EXACTLY the way ``spec-kitty-saas``'s own per-team relay driver
(``apps.live_capability.provisioning_docker.DockerProvisioningDriver.
provision``) provisions a real team's deployment: a freshly-generated,
INDEPENDENT ``ZEITGEIST_TOKEN`` (the shared ``Authorization`` bearer) and
``ZEITGEIST_CAPABILITY_KEY`` (the HMAC signing key for per-actor
``X-Zeitgeist-Capability`` JWTs) -- never the same value doing double duty,
the exact shape FIX-M2-10/FIX-M2-13's own test suites never exercised (see
``test_transport.py``/``test_filtered_stream.py``'s own FIX-M2-15
regression-pin tests for the same proof against the local doubles).

Gated and SKIPPED BY DEFAULT, mirroring
``spec-kitty-saas``'s ``apps/live_capability/tests/
test_provisioning_docker_local.py`` own discipline (same image, same
"only runs when `docker` is on PATH AND the image already exists locally,
never pulled" gate): only runs when both are true on this host. Every
container/volume/network this module creates is ``zg-fix15-*``-prefixed
and torn down in a module-scoped fixture's teardown, never
``dkr-m1-03-*``/``zg-tenant-*`` -- a live DKR-M1-03 stack or a
concurrently-running spec-kitty-saas Docker-local suite, if either happens
to be up on this host, is never read, started, or stopped by this file.

The REAL, unmodified ``specify_cli.zeitgeist_client.transport.
ZeitgeistClient.offer()``/``filtered_stream.FilteredStream.watch()`` are
what run here -- no test-only wire-shape helper stands in for either (the
one exception, ``mint_capability_token`` from this package's own
``conftest.py``, mints the CALLER's own capability JWT the way a real
issuer -- ``apps.live_capability.relay_auth.mint_relay_token`` in
production -- would; it is not a stand-in for anything this test exercises
on the RECEIVING end, which is the real, unmodified relay).
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Generator, Iterator

import pytest

from kernel.clock import now_epoch
from specify_cli.zeitgeist_client import filtered_stream, transport

from .conftest import mint_capability_token

IMAGE = "dkr-m1-02-zeitgeist:contract"
NETWORK = "zg-fix15-net"
CONTAINER_NAME = "zg-fix15-relay"
VOLUME_NAME = "zg-fix15-relay-data"
CONTAINER_PORT = 8787
CMD_TIMEOUT_S = 20.0
HEALTH_TIMEOUT_S = 30.0
HEALTH_POLL_INTERVAL_S = 0.5

# Distinct team/deployment/repo scope, disjoint from any concurrently-
# running spec-kitty-saas Docker-local suite's own fixtures (both are
# caller-chosen claims signed into the capability JWT -- zeitgeist never
# looks them up against anything, see conftest.py's mint_capability_token).
TEAM = "fix-m2-15-team"
DEPLOYMENT = "fix-m2-15-deployment"
REPO = "acme/fix-m2-15-repo"


def _docker_env() -> dict[str, str]:
    """``tests/conftest.py``'s WP04 repoints ``HOME`` at a per-worker
    throwaway directory *before collection* (every test in this suite runs
    under it) -- the ``docker`` CLI resolves its current context (and
    thereby the real Docker daemon socket, e.g. Docker Desktop's own
    per-user socket path) from ``$HOME/.docker/config.json``, so under the
    isolated ``HOME`` it silently falls back to the plain
    ``unix:///var/run/docker.sock`` default, which does not exist on this
    host -- every ``docker`` invocation here hangs for its full connect
    timeout and reports "Cannot connect to the Docker daemon". Same fix as
    ``tests/ui/conftest.py``'s own Playwright-browser-cache case: read back
    the pre-isolation home the root conftest publishes via
    ``SPEC_KITTY_REAL_HOME_FOR_TESTS`` and point ``HOME`` at it for this
    subprocess only -- never mutating ``os.environ`` itself, so no other
    fixture's isolation guarantee is weakened."""
    env = dict(os.environ)
    real_home = os.environ.get("SPEC_KITTY_REAL_HOME_FOR_TESTS")
    if real_home:
        env["HOME"] = real_home
    return env


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _image_ready() -> bool:
    if not _docker_available():
        return False
    result = subprocess.run(
        ["docker", "image", "inspect", IMAGE], capture_output=True, text=True, timeout=10, env=_docker_env()
    )
    return result.returncode == 0


pytestmark = [
    # `integration`, not `slow`: `tests/architectural/test_same_tier_
    # uniqueness.py`'s CI-selection-coverage model requires every test under
    # `tests/zeitgeist_client/` to be selected by the `integration-tests-
    # core-misc` gate (the one CI job whose path list actually includes this
    # directory, `.github/workflows/ci-quality.yml`), which selects `-m
    # '... (git_repo or integration or architectural) ...'` — `slow`'s own
    # dedicated job (`slow and not windows_ci`) has an entirely different,
    # narrower path list that does not include this directory at all, so a
    # `slow`-only marker here would be a real coverage orphan (caught by
    # `test_split_preserves_zero_orphans`), not merely a taxonomy nitpick.
    # In that real CI job (no locally-built `dkr-m1-02-zeitgeist:contract`
    # image), the `skipif` below still makes this an honest skip, never an
    # attempted real-Docker run — identical discipline to spec-kitty-saas's
    # own `test_provisioning_docker_local.py`.
    pytest.mark.integration,
    pytest.mark.skipif(not _image_ready(), reason=f"docker CLI or the {IMAGE!r} image is not available on this host"),
]


def _run(args: list[str], *, tolerate: tuple[str, ...] = ()) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=CMD_TIMEOUT_S, env=_docker_env()
    )
    if result.returncode != 0 and not any(marker in (result.stderr or "").lower() for marker in tolerate):
        raise AssertionError(f"`docker {' '.join(args)}` exited {result.returncode}: {result.stderr}")
    return result


def _host_port(container: str) -> int:
    result = _run(["inspect", container])
    info = json.loads(result.stdout)[0]
    bindings = info["NetworkSettings"]["Ports"][f"{CONTAINER_PORT}/tcp"]
    return int(bindings[0]["HostPort"])


def _wait_healthy(base_url: str) -> None:
    deadline = time.monotonic() + HEALTH_TIMEOUT_S
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=3) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, OSError, TimeoutError):
            pass
        time.sleep(HEALTH_POLL_INTERVAL_S)
    raise AssertionError(f"{CONTAINER_NAME!r} did not become healthy within {HEALTH_TIMEOUT_S}s")


class _RelayHandle:
    def __init__(self, *, base_url: str, shared_token: str, capability_key: str) -> None:
        self.base_url = base_url
        self.shared_token = shared_token
        self.capability_key = capability_key


@pytest.fixture(scope="module")
def relay() -> Generator[_RelayHandle, None, None]:
    """Provisions ONE real ``zg-fix15-relay`` container for every test in
    this module (real container startup dominates wall-clock if repeated
    per test) -- teardown here mirrors ``DockerProvisioningDriver.
    deprovision``'s own idempotent ``rm -f``/``volume rm`` exactly, always
    running (even if setup partially failed) so this module's own
    ``zg-fix15-*`` resources never outlive the test run."""
    _run(["network", "create", NETWORK], tolerate=("already exists",))
    # Idempotent-clean start: a prior interrupted run's leftovers (if any)
    # must not collide with this one -- tolerate "no such X" exactly like
    # DockerProvisioningDriver's own teardown does.
    _run(["rm", "-f", CONTAINER_NAME], tolerate=("no such container",))
    _run(["volume", "rm", VOLUME_NAME], tolerate=("no such volume",))

    shared_token = secrets.token_hex(16)
    capability_key = secrets.token_hex(32)
    _run(["volume", "create", VOLUME_NAME])
    try:
        _run(
            [
                "run",
                "-d",
                "--name",
                CONTAINER_NAME,
                "--network",
                NETWORK,
                "-p",
                f"127.0.0.1::{CONTAINER_PORT}",
                "-v",
                f"{VOLUME_NAME}:/data",
                "-e",
                "ZEITGEIST_HOST=0.0.0.0",
                "-e",
                "ZEITGEIST_MCP_HOST=0.0.0.0",
                "-e",
                "ZEITGEIST_DB=/data/zeitgeist.db",
                "-e",
                f"ZEITGEIST_CAPABILITY_KEY={capability_key}",
                "-e",
                f"ZEITGEIST_TOKEN={shared_token}",
                # `managed` profile: the one that allows managed.control AND
                # (re-)enables push/ambient/pull/live -- exactly
                # provisioning_docker.py's own recipe/rationale, reproduced
                # here rather than imported (spec-kitty-saas is a separate,
                # git-ignored sibling repo with no package dependency).
                "-e",
                "ZEITGEIST_PROFILE=managed",
                "-e",
                "ZEITGEIST_CAPABILITIES_ENABLE=push,ambient,pull,live",
                "--label",
                "zg-fix15=1",
                IMAGE,
                "zeitgeist-server",
            ]
        )
        base_url = f"http://127.0.0.1:{_host_port(CONTAINER_NAME)}"
        _wait_healthy(base_url)
        yield _RelayHandle(base_url=base_url, shared_token=shared_token, capability_key=capability_key)
    finally:
        _run(["rm", "-f", CONTAINER_NAME], tolerate=("no such container",))
        _run(["volume", "rm", VOLUME_NAME], tolerate=("no such volume",))
        _run(["network", "rm", NETWORK], tolerate=("no such network", "has active endpoints"))


def _mint(relay: _RelayHandle, *, sub: str, kind: str = "presence", ttl_s: float = 300.0) -> str:
    now = now_epoch()
    return mint_capability_token(
        relay.capability_key, sub=sub, team=TEAM, deployment=DEPLOYMENT, repo=REPO, kind=kind, iat=now, exp=now + ttl_s
    )


def _raw_status(relay: _RelayHandle, *, authorization_value: str, capability_value: str) -> int:
    """A bare, direct HTTP POST -- independent of ``OfferResult``, which
    only ever reports ``SENT``/``REJECTED`` and never the real status code
    -- confirming the EXACT 401-vs-403 split the module docstring/bead
    describe, not merely "not 2xx"."""
    envelope = {
        "schema_version": transport._SCHEMA_VERSION,
        "op": "presence.publish",
        "request_id": str(uuid.uuid4()),
        "args": {"session_id": "raw-status-sess", "repo": REPO, "kind": "file_edit", "path": "src/raw.py"},
    }
    req = urllib.request.Request(
        f"{relay.base_url}/managed/control",
        data=json.dumps(envelope).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {authorization_value}",
            "X-Zeitgeist-Capability": capability_value,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


def _client(relay: _RelayHandle, *, token: str, capability_credential: str | None, session_id: str) -> transport.ZeitgeistClient:
    return transport.ZeitgeistClient(
        transport.ClientConfig(
            relay_url=relay.base_url,
            token=token,
            capability_credential=capability_credential,
            harness="fix-m2-15-contract-test",
            session_id=session_id,
            agent_id=None,
            repo=REPO,
            branch="main",
        )
    )


# --- criterion 3, positive half: two genuinely independent secrets --------


def test_offer_reaches_202_with_two_independent_secrets(relay: _RelayHandle) -> None:
    """The REAL, unmodified ``ZeitgeistClient.offer()`` -- the exact code
    path DQA-M2-05 found could never succeed against this recipe -- now
    reaches a genuine ``2xx`` (``OfferOutcome.SENT``) presenting
    ``relay.shared_token`` as ``Authorization`` and a real,
    ``relay.capability_key``-signed JWT as ``X-Zeitgeist-Capability``."""
    capability_jwt = _mint(relay, sub="offer-actor")
    client = _client(relay, token=relay.shared_token, capability_credential=capability_jwt, session_id="offer-sess")
    result = client.presence("file_edit", path="src/offer_demo.py")
    assert result.outcome == transport.OfferOutcome.SENT


def test_watch_receives_a_real_frame_with_two_independent_secrets(relay: _RelayHandle) -> None:
    """The REAL, unmodified ``FilteredStream.watch()`` receives a REAL
    frame over a REAL SSE connection, admitted by the SAME real relay
    using ``relay_token``/``capability_credential`` as two independent
    values -- the exact shape ``subscription.resolve_stream`` now builds
    from a SaaS-issued two-credential checkout."""
    watch_jwt = _mint(relay, sub="watch-actor")
    stream = filtered_stream.FilteredStream(
        filtered_stream.TeamStreamConfig(
            relay_url=relay.base_url, relay_token=relay.shared_token, capability_credential=watch_jwt
        )
    )
    frames: list[filtered_stream.LiveFrame] = []
    error: list[BaseException] = []

    def _watch() -> None:
        gen: Iterator[filtered_stream.LiveFrame] = stream.watch(idle_timeout_s=15.0)
        try:
            for frame in gen:
                frames.append(frame)
                return
        except BaseException as exc:  # noqa: BLE001 -- surfaced via `error` to the main thread's assertion
            error.append(exc)
        finally:
            gen.close()

    watch_thread = threading.Thread(target=_watch, daemon=True)
    watch_thread.start()
    try:
        # Publish real presence into the SAME (team, deployment, repo)
        # scope the watch side's own capability JWT is bound to, retrying a
        # few times in case the SSE connection has not yet been accepted
        # server-side (a real network handshake, not a synchronous
        # callback this test can await directly -- see module docstring's
        # "no test-only wire-shape helper" note: DQA-M2-05's own two-actor
        # probes hit the identical race and resolved it the same way, a
        # bounded retry rather than a fixed sleep-and-hope).
        publish_jwt = _mint(relay, sub="publish-actor")
        publish_client = _client(
            relay, token=relay.shared_token, capability_credential=publish_jwt, session_id="publish-sess"
        )
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline and not frames:
            result = publish_client.presence("file_edit", path="src/watch_demo.py")
            assert result.outcome == transport.OfferOutcome.SENT
            watch_thread.join(timeout=1.0)
    finally:
        watch_thread.join(timeout=5.0)

    assert not error, f"watch() raised: {error}"
    assert frames, "no frame arrived on the real SSE stream within the bound"
    assert frames[0].frame_type == "presence"


# --- #186: presence and focus are separate grants on the real relay -------


def test_presence_kind_grants_presence_but_not_focus(relay: _RelayHandle) -> None:
    """The lease split #186 wires around, proven against the real relay:
    zeitgeist grants ``presence.publish`` to the ``presence`` kind (which is
    why the moment credential carries presence frames for free) and the
    ``focus.*`` ops ONLY to the ``focus`` kind -- a presence-kind JWT offering
    ``focus.start`` earns a real 403 ``op_not_granted``, which is exactly why
    ``resolution.resolve_focus_capability`` mints a second lease instead of
    reusing the first."""
    presence_jwt = _mint(relay, sub="presence-kind-actor", kind="presence")
    focus_jwt = _mint(relay, sub="focus-kind-actor", kind="focus")

    presence_client = _client(relay, token=relay.shared_token, capability_credential=presence_jwt, session_id="kind-split-sess")
    assert presence_client.presence("command").outcome == transport.OfferOutcome.SENT

    focus_client = _client(relay, token=relay.shared_token, capability_credential=focus_jwt, session_id="kind-split-sess")
    started = focus_client.focus_start("mvp-smoke-mission", wp_id="WP01")
    assert started.outcome == transport.OfferOutcome.SENT

    same_session_wrong_kind = _client(relay, token=relay.shared_token, capability_credential=presence_jwt, session_id="kind-split-sess")
    # focus.start (not .heartbeat): a fresh client refuses a heartbeat
    # locally -- REFUSED_LOCAL, no socket -- because it holds no focus
    # lease of its own; only an attempted START reaches the relay's kind
    # check at all.
    assert same_session_wrong_kind.focus_start("other-mission", wp_id="WP02").outcome == (transport.OfferOutcome.REJECTED)


# --- criterion 3, negative half: the pre-fix single-credential shape ------
# --- fails closed against this SAME real, two-secret relay ----------------


def test_single_credential_capability_jwt_as_bearer_is_401(relay: _RelayHandle) -> None:
    """The exact pre-FIX-M2-15 shape (``capability_credential`` left
    unset, so ``offer()`` falls back to sending the SAME value for both
    headers) presenting a valid capability JWT: it passes
    ``managed_auth.py``'s HMAC check but is rejected by the OUTER
    ``AuthenticationMiddleware`` gate FIRST, since it does not equal
    ``relay.shared_token`` -- a real, reproduced ``401``, exactly what
    DQA-M2-05 found by hand."""
    capability_jwt = _mint(relay, sub="misconfig-bearer-actor")
    client = _client(relay, token=capability_jwt, capability_credential=None, session_id="misconfig-bearer-sess")
    result = client.presence("file_edit", path="src/misconfig_bearer.py")
    assert result.outcome == transport.OfferOutcome.REJECTED
    status = _raw_status(relay, authorization_value=capability_jwt, capability_value=capability_jwt)
    assert status == 401


def test_single_credential_shared_token_as_capability_is_403(relay: _RelayHandle) -> None:
    """The same pre-fix shape presenting the shared token instead: it
    passes the outer ``Authorization`` gate (it IS ``relay.shared_token``)
    but ``managed_auth.py`` rejects it as an invalid capability signature
    -- a real, reproduced ``403``."""
    client = _client(
        relay, token=relay.shared_token, capability_credential=None, session_id="misconfig-capability-sess"
    )
    result = client.presence("file_edit", path="src/misconfig_capability.py")
    assert result.outcome == transport.OfferOutcome.REJECTED
    status = _raw_status(relay, authorization_value=relay.shared_token, capability_value=relay.shared_token)
    assert status == 403
