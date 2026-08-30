"""Interpreter-capability resolution for the sync daemon spawn (#3624).

``_spawn_sync_daemon_process`` used to launch the background daemon with a bare
``sys.executable``. On a host whose ``sys.executable`` cannot import
``specify_cli`` (framework-Python re-exec, pyenv shim, or a Homebrew ``python3``
first on PATH) the child died immediately with
``ModuleNotFoundError: No module named 'specify_cli'``. These tests pin the
probe → self-heal → fail-loud resolution and prove the spawn consumes the
resolved interpreter, never bare ``sys.executable`` directly.

Real-process isolation: the probe and the current-interpreter check spawn real
subprocesses. Run this file in its own ``-n0`` pass; a mis-mocked ``Popen`` that
leaks a real daemon must not scatter across xdist workers.
"""

from __future__ import annotations

import os
import subprocess
import sys
from unittest.mock import MagicMock

import pytest

from specify_cli.sync import daemon
from specify_cli.sync.daemon import (
    DAEMON_EXEC_ARG_PREFIX,
    DaemonSpawnError,
    _interpreter_can_import_specify_cli,
    _resolve_daemon_interpreter,
    _specify_cli_pythonpath_entry,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


# ---------------------------------------------------------------------------
# Probe: _interpreter_can_import_specify_cli
# ---------------------------------------------------------------------------


class TestImportProbe:
    def test_probe_true_for_current_interpreter(self):
        # The running interpreter imports specify_cli by construction.
        assert _interpreter_can_import_specify_cli(sys.executable) is True

    def test_probe_false_for_incapable_interpreter(self, monkeypatch):
        # The previously-untested ModuleNotFoundError path: the child exits 1.
        def fake_run(*_args, **_kwargs):
            return subprocess.CompletedProcess(
                args=[], returncode=1, stdout=b"", stderr=b"ModuleNotFoundError"
            )

        monkeypatch.setattr(daemon.subprocess, "run", fake_run)
        assert _interpreter_can_import_specify_cli("/usr/bin/python3") is False

    def test_probe_false_on_launch_error(self, monkeypatch):
        def fake_run(*_args, **_kwargs):
            raise OSError("cannot exec")

        monkeypatch.setattr(daemon.subprocess, "run", fake_run)
        assert _interpreter_can_import_specify_cli("/nope/python") is False

    def test_probe_false_on_timeout(self, monkeypatch):
        def fake_run(*_args, **_kwargs):
            raise subprocess.TimeoutExpired(cmd="python", timeout=10.0)

        monkeypatch.setattr(daemon.subprocess, "run", fake_run)
        assert _interpreter_can_import_specify_cli("/slow/python") is False

    def test_probe_false_for_empty_executable(self, monkeypatch):
        # Frozen/embedded builds report sys.executable == "". Never probe it.
        called = MagicMock()
        monkeypatch.setattr(daemon.subprocess, "run", called)
        assert _interpreter_can_import_specify_cli("") is False
        called.assert_not_called()


# ---------------------------------------------------------------------------
# PYTHONPATH self-heal entry
# ---------------------------------------------------------------------------


class TestPythonpathEntry:
    def test_entry_is_a_real_directory(self):
        entry = _specify_cli_pythonpath_entry()
        assert entry is not None
        # Placing this dir on PYTHONPATH must make `import specify_cli` resolve.
        assert os.path.isdir(entry)

    def test_entry_none_when_package_has_no_file(self, monkeypatch):
        module = MagicMock()
        module.__file__ = None
        monkeypatch.setattr(daemon.importlib, "import_module", lambda _name: module)
        assert _specify_cli_pythonpath_entry() is None


# ---------------------------------------------------------------------------
# Resolver: _resolve_daemon_interpreter
# ---------------------------------------------------------------------------


class TestResolveDaemonInterpreter:
    def test_uses_capable_executable_unchanged(self, monkeypatch):
        base_env = {"PATH": "/usr/bin", "SPEC_KITTY_CLI_VERSION": "9.9.9"}
        monkeypatch.setattr(
            daemon, "_interpreter_can_import_specify_cli", lambda _exe, _env=None: True
        )
        exe, env = _resolve_daemon_interpreter(base_env)
        assert exe == sys.executable
        assert env is base_env  # no self-heal mutation when already capable

    def test_self_heals_via_pythonpath(self, monkeypatch):
        base_env = {"PATH": "/usr/bin"}
        entry = "/opt/venv/site-packages"

        def probe(_exe, env=None):
            # Incapable with the raw env; capable once the entry is on PYTHONPATH.
            return bool(env) and entry in env.get("PYTHONPATH", "")

        monkeypatch.setattr(daemon, "_interpreter_can_import_specify_cli", probe)
        monkeypatch.setattr(daemon, "_specify_cli_pythonpath_entry", lambda: entry)

        exe, env = _resolve_daemon_interpreter(base_env)
        assert exe == sys.executable
        assert env["PYTHONPATH"].split(daemon.os.pathsep)[0] == entry

    def test_self_heal_preserves_existing_pythonpath(self, monkeypatch):
        base_env = {"PYTHONPATH": "/existing"}
        entry = "/opt/venv/site-packages"

        def probe(_exe, env=None):
            return bool(env) and entry in env.get("PYTHONPATH", "")

        monkeypatch.setattr(daemon, "_interpreter_can_import_specify_cli", probe)
        monkeypatch.setattr(daemon, "_specify_cli_pythonpath_entry", lambda: entry)

        _exe, env = _resolve_daemon_interpreter(base_env)
        parts = env["PYTHONPATH"].split(daemon.os.pathsep)
        assert parts == [entry, "/existing"]

    def test_raises_when_uncapable_and_unrecoverable(self, monkeypatch):
        monkeypatch.setattr(
            daemon, "_interpreter_can_import_specify_cli", lambda _exe, _env=None: False
        )
        monkeypatch.setattr(daemon, "_specify_cli_pythonpath_entry", lambda: None)
        with pytest.raises(DaemonSpawnError, match="cannot import"):
            _resolve_daemon_interpreter({"PATH": "/usr/bin"})

    def test_raises_when_self_heal_still_incapable(self, monkeypatch):
        # Entry exists but the interpreter is broken even with it → fail loud.
        monkeypatch.setattr(
            daemon, "_interpreter_can_import_specify_cli", lambda _exe, _env=None: False
        )
        monkeypatch.setattr(
            daemon, "_specify_cli_pythonpath_entry", lambda: "/opt/site"
        )
        with pytest.raises(DaemonSpawnError):
            _resolve_daemon_interpreter({})


# ---------------------------------------------------------------------------
# Spawn: _spawn_sync_daemon_process consumes the resolver
# ---------------------------------------------------------------------------


class TestSpawnConsumesResolver:
    def _stub_spawn_io(self, monkeypatch, tmp_path):
        log_path = tmp_path / "sync-daemon.log"
        monkeypatch.setattr(daemon, "_daemon_log_file", lambda: log_path)
        monkeypatch.setattr(daemon, "_get_package_version", lambda: "9.9.9")
        monkeypatch.setattr(daemon, "daemon_scope_marker", lambda: "--scope=test")

    def test_spawn_uses_resolved_interpreter_and_marker(self, monkeypatch, tmp_path):
        self._stub_spawn_io(monkeypatch, tmp_path)
        resolved_exe = "/opt/venv/bin/python"
        resolved_env = {"PYTHONPATH": "/opt/venv/site", "SPEC_KITTY_CLI_VERSION": "9.9.9"}
        monkeypatch.setattr(
            daemon,
            "_resolve_daemon_interpreter",
            lambda _base_env: (resolved_exe, resolved_env),
        )
        mock_popen = MagicMock(name="Popen")
        monkeypatch.setattr(daemon.subprocess, "Popen", mock_popen)

        daemon._spawn_sync_daemon_process(9400, "tok")

        argv, kwargs = mock_popen.call_args.args, mock_popen.call_args.kwargs
        argv_list = argv[0]
        # argv[0] is the RESOLVED interpreter, never bare sys.executable.
        assert argv_list[0] == resolved_exe
        assert sys.executable != resolved_exe  # guard: the assertion is meaningful
        # The exec-identity marker is built from the resolved interpreter.
        exec_markers = [a for a in argv_list if a.startswith(DAEMON_EXEC_ARG_PREFIX)]
        assert exec_markers == [DAEMON_EXEC_ARG_PREFIX + resolved_exe]
        # The resolved (self-healed) env is what the child inherits.
        assert kwargs["env"] is resolved_env

    def test_spawn_not_called_when_uncapable(self, monkeypatch, tmp_path):
        self._stub_spawn_io(monkeypatch, tmp_path)

        def raise_uncapable(_base_env):
            raise DaemonSpawnError("no capable interpreter")

        monkeypatch.setattr(daemon, "_resolve_daemon_interpreter", raise_uncapable)
        mock_popen = MagicMock(name="Popen")
        monkeypatch.setattr(daemon.subprocess, "Popen", mock_popen)

        with pytest.raises(DaemonSpawnError):
            daemon._spawn_sync_daemon_process(9400, "tok")
        mock_popen.assert_not_called()
