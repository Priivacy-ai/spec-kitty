# Developer Quickstart: installed-runtime-domain

This quickstart covers the new surfaces introduced by this mission and
how to use them in extension or testing contexts.

---

## detect_runtime() — the single probe call

```python
from specify_cli.compat._detect.runtime import detect_runtime

runtime = detect_runtime()

# Full snapshot in one call — no subsequent receipt reads needed
print(runtime.install_method)        # InstallMethod.UV_TOOL
print(runtime.receipt_path)          # Path(...)/uv-receipt.toml or None
print(runtime.tool_dir)              # Path to UV tool dir, or None
print(runtime.is_default_tool_dir)   # False if custom UV_TOOL_DIR
print(runtime.python)                # "3.11" or None
print(runtime.requirements)          # (UvRequirement(name='spec-kitty-cli', ...), ...)
print(runtime.safe_for_auto_upgrade) # True for PIPX, UV_TOOL, BREW, PIP_USER, PIP_SYSTEM
print(runtime.platform)              # "posix" or "windows"
```

`detect_runtime()` never raises (NFR-001). Any probe failure returns a
valid record with None/empty/default fields.

---

## plan_remediation() — get the canonical upgrade command

```python
from specify_cli.compat.remediation import plan_remediation, RemediationIntent

runtime = detect_runtime()
cmd = plan_remediation(runtime, RemediationIntent.UPGRADE, target_version="3.3.0")

# Display to user
print(cmd.render("posix"))
# e.g. "UV_TOOL_DIR=/opt uv tool install --force --python 3.11 spec-kitty-cli==3.3.0"

# Subprocess execution
import subprocess
if cmd.argv is not None:
    subprocess.run(cmd.argv, env={**os.environ, **cmd.env})
```

`plan_remediation()` is a pure function — no I/O, deterministic for the
same inputs (NFR-004).

---

## build_upgrade_hint() — backward compat (unchanged public API)

```python
from specify_cli.compat.upgrade_hint import build_upgrade_hint
from specify_cli.compat._detect.install_method import InstallMethod

hint = build_upgrade_hint(InstallMethod.UV_TOOL, target_version="3.3.0")
print(hint.command)   # "uv tool install --force spec-kitty-cli==3.3.0"
print(hint.note)      # None
```

After WP03, `build_upgrade_hint()` is implemented on top of
`plan_remediation()` but the public signature and return type are
unchanged.

---

## UpgradeAttemptStore — query upgrade history

```python
from specify_cli.compat.history import UpgradeAttemptStore, UpgradeAttemptRecord, UpgradeAttemptOutcome
from specify_cli.compat._detect.install_method import InstallMethod
from specify_cli.compat.remediation import RemediationIntent
from datetime import datetime, UTC
import ulid

# Append a record (best-effort, never raises)
store = UpgradeAttemptStore()
record = UpgradeAttemptRecord(
    attempt_id=str(ulid.new()),
    timestamp=datetime.now(UTC),
    install_method=InstallMethod.UV_TOOL,
    intent=RemediationIntent.UPGRADE,
    outcome=UpgradeAttemptOutcome.SUCCESS,
    exit_code=0,
    target_version="3.3.0",
)
store.append(record)

# Query: was this version already upgraded?
is_done = store.is_idempotent(record)   # True after append above

# Query: how many consecutive failures?
failures = store.consecutive_failure_count(InstallMethod.UV_TOOL, window_seconds=300)

# Query: when did we last succeed?
last_ok = store.last_success_timestamp(InstallMethod.UV_TOOL)
```

---

## Writing tests

### Test detect_runtime() with a fake uv environment

```python
import os
import tomllib
from pathlib import Path
from unittest.mock import patch

def test_detect_runtime_uv_tool(tmp_path):
    tool_env = tmp_path / "tools" / "spec-kitty-cli"
    bin_dir = tool_env / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "python").write_text("")  # fake executable

    receipt = tool_env / "uv-receipt.toml"
    receipt.write_text(
        '[tool]\npython = "3.11"\n'
        '[[tool.requirements]]\nname = "spec-kitty-cli"\nspecifier = "==3.2.0"\n'
        '[[tool.entrypoints]]\nname = "spec-kitty"\n"install-path" = "/opt/bin/spec-kitty"\n'
    )

    with patch("sys.executable", str(bin_dir / "python")):
        with patch.dict(os.environ, {"UV_TOOL_DIR": str(tmp_path / "tools")}, clear=False):
            from specify_cli.compat._detect.runtime import detect_runtime
            runtime = detect_runtime()

    assert runtime.install_method.value == "uv-tool"
    assert runtime.receipt_path == receipt
    assert runtime.python == "3.11"
    assert len(runtime.requirements) == 1
    assert runtime.requirements[0].name == "spec-kitty-cli"
    assert runtime.is_default_tool_dir is False
```

### Test plan_remediation() snapshot parity

Snapshot tests committed in WP03 assert `render()` output equals the
pre-migration output of the corresponding legacy site for every
`(install_method, intent, platform)` combination. These tests run as
part of the regular test suite and gate WP03 merge (SC-003).

```python
from specify_cli.compat.remediation import plan_remediation, RemediationIntent
from specify_cli.compat._detect.runtime import InstalledCliRuntime, PackageSource
from specify_cli.compat._detect.install_method import InstallMethod

def test_pipx_upgrade_render():
    runtime = InstalledCliRuntime(
        install_method=InstallMethod.PIPX,
        executable="/home/user/.local/pipx/venvs/spec-kitty-cli/bin/python",
        receipt_path=None, tool_dir=None, bin_dir=None,
        is_default_tool_dir=None, is_default_bin_dir=None,
        python=None, requirements=(),
        package_source=PackageSource.UNKNOWN,
        platform="posix",
        safe_for_auto_upgrade=True,
    )
    cmd = plan_remediation(runtime, RemediationIntent.UPGRADE, None)
    assert cmd.render("posix") == "pipx upgrade spec-kitty-cli"
```

### Test UpgradeAttemptStore in isolation

```python
def test_history_store_idempotency(tmp_path):
    from specify_cli.compat.history import UpgradeAttemptStore, UpgradeAttemptRecord, UpgradeAttemptOutcome
    store = UpgradeAttemptStore(db_path=tmp_path / "history.db")
    record = UpgradeAttemptRecord(
        attempt_id="01KW0NR6E9XCH0QAREQWQ5ZDPB",
        timestamp=datetime(2026, 6, 26, tzinfo=UTC),
        install_method=InstallMethod.UV_TOOL,
        intent="upgrade",
        outcome=UpgradeAttemptOutcome.SUCCESS,
        exit_code=0,
        target_version="3.3.0",
    )
    store.append(record)
    assert store.is_idempotent(record) is True
```

---

## Running the test suite

```bash
# Full suite
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider

# Compat layer tests only
PWHEADLESS=1 pytest tests/specify_cli/compat/ -n auto --dist loadfile

# Terminology guard (run before pushing any doctrine/prose changes)
pytest tests/architectural/test_no_legacy_terminology.py
```
