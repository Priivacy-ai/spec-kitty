"""Remediation-command types and planner for the upgrade-nag.

Public surface
--------------
RemediationIntent    -- StrEnum with 3 intent values.
RemediationCommand   -- Frozen dataclass: a fully specified remediation action.
plan_remediation     -- Pure function: build a RemediationCommand from runtime + intent.

Security properties enforced here
-----------------------------------
CHK028  ``render()`` validates the composed command string against
        ``^[A-Za-z0-9 .\\-+_/=:]{1,128}$`` (identical character class
        to the one in ``compat/upgrade_hint.py``).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from specify_cli.compat._detect.runtime import InstalledCliRuntime, UvRequirement

# ---------------------------------------------------------------------------
# CHK028 validation regex (identical to upgrade_hint.py line 29)
# ---------------------------------------------------------------------------

_COMMAND_RE = re.compile(r"^[A-Za-z0-9 .\-+_/=:]{1,128}$")  # CHK028

# Version specifier validation — same pattern as upgrade_hint.py _VERSION_RE
_VERSION_RE = re.compile(r"^[A-Za-z0-9.\-+]{1,64}$")

_PACKAGE_NAME = "spec-kitty-cli"
_PYTEST_NAME = "pytest"

# Shown when a uv-tool reinstall cannot be reconstructed from the receipt
# without risking a clobber of the user's real source (unsupported/unknown
# requirement shape, or missing spec-kitty entry). Mirrors the legacy
# ``_fallback_uv_tool_reinstall_command`` guidance; the substring
# "same uv tool source" is asserted by the provenance regression tests.
_UV_PROVENANCE_FALLBACK_NOTE = (
    "Spec Kitty could not preserve uv receipt provenance automatically; "
    "reinstall the same uv tool source with --with pytest"
)


# ---------------------------------------------------------------------------
# PowerShell quoting helper  (mirrors review/__init__.py _powershell_quote)
# ---------------------------------------------------------------------------


def _powershell_quote(value: str) -> str:
    """Wrap *value* in PowerShell single quotes, escaping embedded ``'``.

    Mirrors ``_powershell_quote()`` in ``review/__init__.py`` (C-005).
    """
    return "'" + value.replace("'", "''") + "'"


# ---------------------------------------------------------------------------
# RemediationIntent enum
# ---------------------------------------------------------------------------


class RemediationIntent(StrEnum):
    """What the remediation command is attempting to do."""

    UPGRADE = "upgrade"
    REINSTALL_WITH_TEST = "reinstall_with_test"
    MANUAL_GUIDANCE = "manual_guidance"


# ---------------------------------------------------------------------------
# RemediationCommand dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RemediationCommand:
    """A fully specified remediation action.

    NFR-004: Instances are constructed by ``plan_remediation()``, a pure
    function (no I/O). Construction itself does NOT raise on invalid
    content — validation happens in ``render()`` (NFR-002).

    Invariant: if ``intent == MANUAL_GUIDANCE``, ``argv`` is None and
    ``note`` is non-None. For UPGRADE and REINSTALL_WITH_TEST, ``argv``
    is non-None when the install method supports automated remediation.
    """

    intent: RemediationIntent
    argv: tuple[str, ...] | None              # subprocess-ready args, or None for manual
    env: Mapping[str, str]                    # env vars to prepend (e.g. UV_TOOL_DIR=...)
    note: str | None                          # human-readable note, or None

    def render(self, platform: Literal["posix", "windows"]) -> str:
        """Return a CHK028-validated, env-prefixed, platform-quoted command string.

        Raises:
            ValueError: if ``self.intent`` is ``MANUAL_GUIDANCE``.
            ValueError: if ``self.argv`` is ``None``.
            ValueError: if the composed string does not match CHK028
                        (``^[A-Za-z0-9 .\\-+_/=:]{1,128}$``).

        The returned string is safe for copy-paste display.  The same
        ``argv`` and ``env`` fields can be passed directly to
        ``subprocess.run()`` for programmatic execution.
        """
        import shlex  # stdlib — deferred to keep module-level imports minimal

        if self.intent == RemediationIntent.MANUAL_GUIDANCE:
            raise ValueError(
                "cannot render MANUAL_GUIDANCE RemediationCommand"
                " — check intent before calling render()"
            )
        if self.argv is None:
            raise ValueError("argv is None")

        # --- 1. Build env prefix -------------------------------------------
        if self.env:
            if platform == "posix":
                # KEY=shlex.quote(value) per entry, space-joined with trailing space.
                env_prefix = "".join(
                    f"{k}={shlex.quote(v)} " for k, v in self.env.items()
                )
            else:
                # $env:KEY='ps-quoted-value'; per entry, concatenated with trailing space.
                env_prefix = "".join(
                    f"$env:{k}={_powershell_quote(v)}; " for k, v in self.env.items()
                )
        else:
            env_prefix = ""

        # --- 2. Build argv string -------------------------------------------
        argv_str = (
            " ".join(shlex.quote(a) for a in self.argv)
            if platform == "posix"
            else " ".join(self.argv)
        )

        # --- 3. Compose and CHK028-validate ---------------------------------
        composed = env_prefix + argv_str
        if not _COMMAND_RE.match(composed):
            raise ValueError(f"CHK028 violation: {composed!r}")

        return composed


# ---------------------------------------------------------------------------
# plan_remediation() — pure planner function (NFR-004)
# ---------------------------------------------------------------------------


def plan_remediation(
    runtime: InstalledCliRuntime,
    intent: RemediationIntent,
    target_version: str | None,
) -> RemediationCommand:
    """Return a :class:`RemediationCommand` for *runtime* and *intent*.

    NFR-004: Pure function — no I/O, no side effects.  Deterministic for
    the same inputs.

    Args:
        runtime: Immutable snapshot of the running installation.
        intent:  What the caller wants to achieve.
        target_version: Optional version specifier for the upgrade.  Only
            applied to UV_TOOL UPGRADE when the value matches
            ``^[A-Za-z0-9.\\-+]{1,64}$``.  Ignored for other methods.

    Returns:
        A :class:`RemediationCommand`.  For install methods that do not
        support automated remediation for the requested intent the returned
        command will have ``intent == MANUAL_GUIDANCE`` and ``argv == None``.
    """
    from specify_cli.compat._detect.install_method import InstallMethod  # deferred

    install_method = runtime.install_method

    if install_method == InstallMethod.UV_TOOL:
        return _plan_uv_tool(runtime, intent, target_version)
    if install_method == InstallMethod.PIPX:
        return _plan_pipx(intent)
    if install_method == InstallMethod.BREW:
        return _plan_brew(intent)
    if install_method == InstallMethod.PIP_USER:
        return _plan_pip_user(intent)
    if install_method == InstallMethod.PIP_SYSTEM:
        return _plan_pip_system(intent)

    # SOURCE, UNKNOWN, SYSTEM_PACKAGE — no automated path
    note = _manual_note(str(install_method), intent)
    return RemediationCommand(
        intent=RemediationIntent.MANUAL_GUIDANCE,
        argv=None,
        env={},
        note=note,
    )


# ---------------------------------------------------------------------------
# Per-method planning helpers
# ---------------------------------------------------------------------------


def _plan_uv_tool(
    runtime: InstalledCliRuntime,
    intent: RemediationIntent,
    target_version: str | None,
) -> RemediationCommand:
    """Build a RemediationCommand for UV_TOOL installs."""
    if intent == RemediationIntent.REINSTALL_WITH_TEST:
        return _plan_uv_tool_reinstall(runtime, target_version)
    return _plan_uv_tool_upgrade(runtime, target_version)


def _pypi_package_arg(target_version: str | None) -> str:
    """``spec-kitty-cli``, version-pinned when *target_version* is valid (CHK)."""
    return (
        f"{_PACKAGE_NAME}=={target_version}"
        if target_version is not None and _VERSION_RE.match(target_version)
        else _PACKAGE_NAME
    )


def _plan_uv_tool_upgrade(
    runtime: InstalledCliRuntime,
    target_version: str | None,
) -> RemediationCommand:
    """UPGRADE intent: pin to the PyPI release (provenance not preserved by design).

    Upgrading deliberately targets the published release; the reinstall path
    (REINSTALL_WITH_TEST) is the one that must preserve the user's source.
    """
    pkg = _pypi_package_arg(target_version)

    base: tuple[str, ...] = ("uv", "tool", "install", "--force")
    if runtime.python is not None:
        base = base + ("--python", runtime.python)
    base = base + (pkg,)

    return RemediationCommand(
        intent=RemediationIntent.UPGRADE, argv=base, env=_uv_tool_env(runtime), note=None
    )


def _plan_uv_tool_reinstall(
    runtime: InstalledCliRuntime,
    target_version: str | None,
) -> RemediationCommand:
    """REINSTALL_WITH_TEST: rebuild the install with pytest, preserving provenance.

    FR-019 / SC-003 / issue #1358: a uv-tool install from a directory, editable
    checkout, path, git, or url source MUST be reinstalled from that same source
    — never silently re-pinned to the PyPI release (which clobbers the user's
    real install). Injected deps are carried through as ``--with`` args. When the
    receipt carries an unsupported/unknown shape we refuse and return
    MANUAL_GUIDANCE rather than risk a clobber (conservative — nothing discarded).
    """
    env = _uv_tool_env(runtime)

    main_req = _find_main_requirement(runtime.requirements)
    if main_req is None:
        if runtime.receipt_path is None:
            # No receipt at all — the source is unknown, so a PyPI reinstall
            # (pinned to the running version when known) is the only option.
            return _uv_tool_reinstall_pypi_fallback(env, target_version)
        # Receipt present but no spec-kitty-cli entry — refuse to guess a PyPI
        # pin that could clobber the real (unmapped) source. Be conservative.
        return RemediationCommand(
            intent=RemediationIntent.MANUAL_GUIDANCE,
            argv=None,
            env={},
            note=_UV_PROVENANCE_FALLBACK_NOTE,
        )

    package_args = _uv_main_package_args(main_req)
    with_args = _uv_with_args(runtime.requirements)
    if package_args is None or with_args is None:
        # Unsupported receipt shape — refuse to guess; preserve the source.
        return RemediationCommand(
            intent=RemediationIntent.MANUAL_GUIDANCE,
            argv=None,
            env={},
            note=_UV_PROVENANCE_FALLBACK_NOTE,
        )

    argv: tuple[str, ...] = ("uv", "tool", "install", "--force")
    if runtime.python is not None:
        argv = argv + ("--python", runtime.python)
    argv = argv + tuple(with_args) + tuple(package_args)

    # ``note`` is the safe fallback the display consumer uses if render() trips
    # CHK028 on a path containing characters outside the safe display class.
    return RemediationCommand(
        intent=RemediationIntent.REINSTALL_WITH_TEST,
        argv=argv,
        env=env,
        note=_UV_PROVENANCE_FALLBACK_NOTE,
    )


def _uv_tool_reinstall_pypi_fallback(
    env: dict[str, str],
    target_version: str | None,
) -> RemediationCommand:
    """Reinstall command when no source provenance is available (receipt absent)."""
    pkg = _pypi_package_arg(target_version)
    argv = ("uv", "tool", "install", "--force", "--with", _PYTEST_NAME, pkg)
    return RemediationCommand(
        intent=RemediationIntent.REINSTALL_WITH_TEST,
        argv=argv,
        env=env,
        note=_UV_PROVENANCE_FALLBACK_NOTE,
    )


def _uv_tool_env(runtime: InstalledCliRuntime) -> dict[str, str]:
    """Env prefix for a uv-tool command: UV_TOOL_DIR / UV_TOOL_BIN_DIR when non-default.

    Order is load-bearing for byte-for-byte display fidelity: UV_TOOL_DIR
    first, UV_TOOL_BIN_DIR second (matches the legacy ``_uv_tool_env_values``).
    """
    env: dict[str, str] = {}
    if runtime.is_default_tool_dir is False and runtime.tool_dir is not None:
        env["UV_TOOL_DIR"] = str(runtime.tool_dir)
    if runtime.is_default_bin_dir is False and runtime.bin_dir is not None:
        env["UV_TOOL_BIN_DIR"] = str(runtime.bin_dir)
    return env


def _find_main_requirement(
    requirements: tuple[UvRequirement, ...],
) -> UvRequirement | None:
    """Return the spec-kitty-cli requirement entry, or None if absent."""
    for req in requirements:
        if req.name == _PACKAGE_NAME:
            return req
    return None


def _uv_main_package_args(req: UvRequirement) -> list[str] | None:
    """Package args preserving the main package's source provenance.

    Returns None when the entry's shape is unsupported (the caller then
    refuses and shows manual guidance rather than re-pinning to PyPI).
    """
    if not req.is_supported:
        return None
    if req.directory is not None:
        return [req.directory]
    if req.editable is not None:
        return ["--editable", req.editable]
    if req.path is not None:
        return [req.path]
    if req.git is not None:
        return [_PACKAGE_NAME, "--from", _uv_git_source(req.git)]
    if req.url is not None:
        return [req.url]
    if req.specifier is not None:
        return [f"{_PACKAGE_NAME}{req.specifier}"]
    return [_PACKAGE_NAME]


def _uv_with_args(requirements: tuple[UvRequirement, ...]) -> list[str] | None:
    """`--with`/`--with-editable` args for injected deps, ensuring pytest is present.

    Returns None when any injected dep has an unsupported shape (conservative).
    """
    args: list[str] = []
    has_pytest = False
    for req in requirements:
        if req.name == _PACKAGE_NAME:
            continue
        if req.name == _PYTEST_NAME:
            has_pytest = True
        dep_args = _uv_injected_dep_args(req)
        if dep_args is None:
            return None
        args.extend(dep_args)
    if not has_pytest:
        args.extend(["--with", _PYTEST_NAME])
    return args


def _uv_injected_dep_args(req: UvRequirement) -> list[str] | None:
    """`--with`/`--with-editable` args for a single injected dependency."""
    if not req.is_supported:
        return None
    if req.editable is not None:
        return ["--with-editable", req.editable]
    source = _uv_injected_dep_source(req)
    if source is not None:
        return ["--with", source]
    return None


def _uv_injected_dep_source(req: UvRequirement) -> str | None:
    """Resolve the `--with` source token for an injected dependency."""
    if req.directory is not None:
        return req.directory
    if req.path is not None:
        return req.path
    if req.git is not None:
        return _uv_git_source(req.git)
    if req.url is not None:
        return req.url
    return f"{req.name}{req.specifier or ''}"


def _uv_git_source(git: str) -> str:
    """Normalize a git source to uv's ``git+`` URL form."""
    return git if git.startswith("git+") else f"git+{git}"


def _plan_pipx(intent: RemediationIntent) -> RemediationCommand:
    """Build a RemediationCommand for PIPX installs."""
    if intent == RemediationIntent.UPGRADE:
        argv: tuple[str, ...] = ("pipx", "upgrade", _PACKAGE_NAME)
    else:
        argv = ("pipx", "install", "--include-deps", f"{_PACKAGE_NAME}[test]")
    return RemediationCommand(intent=intent, argv=argv, env={}, note=None)


def _plan_brew(intent: RemediationIntent) -> RemediationCommand:
    """Build a RemediationCommand for BREW installs."""
    if intent == RemediationIntent.UPGRADE:
        return RemediationCommand(
            intent=intent,
            argv=("brew", "upgrade", _PACKAGE_NAME),
            env={},
            note=None,
        )
    # REINSTALL_WITH_TEST — no standard brew test-extra path
    return RemediationCommand(
        intent=RemediationIntent.MANUAL_GUIDANCE,
        argv=None,
        env={},
        note=_manual_note("brew", intent),
    )


def _plan_pip_user(intent: RemediationIntent) -> RemediationCommand:
    """Build a RemediationCommand for PIP_USER installs."""
    if intent == RemediationIntent.UPGRADE:
        return RemediationCommand(
            intent=intent,
            argv=("pip", "install", "--user", "--upgrade", _PACKAGE_NAME),
            env={},
            note=None,
        )
    return RemediationCommand(
        intent=RemediationIntent.MANUAL_GUIDANCE,
        argv=None,
        env={},
        note=_manual_note("pip-user", intent),
    )


def _plan_pip_system(intent: RemediationIntent) -> RemediationCommand:
    """Build a RemediationCommand for PIP_SYSTEM installs."""
    if intent == RemediationIntent.UPGRADE:
        return RemediationCommand(
            intent=intent,
            argv=("pip", "install", "--upgrade", _PACKAGE_NAME),
            env={},
            note=None,
        )
    return RemediationCommand(
        intent=RemediationIntent.MANUAL_GUIDANCE,
        argv=None,
        env={},
        note=_manual_note("pip-system", intent),
    )


# ---------------------------------------------------------------------------
# Manual-guidance note catalogue
# ---------------------------------------------------------------------------

_MANUAL_NOTES: dict[str, dict[str, str]] = {
    RemediationIntent.UPGRADE: {
        "source": "Rebuild from source using your normal dev workflow.",
        "unknown": (
            "Reinstall spec-kitty-cli using your original install method. "
            "See https://spec-kitty.dev/docs/how-to/install-and-upgrade for guidance."
        ),
        "system-package": (
            "Use your system package manager to upgrade spec-kitty-cli."
        ),
    },
    RemediationIntent.REINSTALL_WITH_TEST: {
        "brew": (
            "Homebrew does not support test extras automatically. "
            "Run: pip install spec-kitty-cli[test] in a virtual environment."
        ),
        "pip-user": "Run: pip install --user spec-kitty-cli[test]",
        "pip-system": "Run: pip install spec-kitty-cli[test]",
        "source": "Run: pip install -e .[test] to reinstall with test extras.",
        "unknown": (
            "Install spec-kitty-cli with test extras using your original install method."
        ),
        "system-package": (
            "Use your system package manager to install spec-kitty-cli, "
            "then add test extras via pip."
        ),
    },
}


def _manual_note(install_method_str: str, intent: RemediationIntent) -> str:
    """Return a human-readable note for MANUAL_GUIDANCE cases."""
    return _MANUAL_NOTES.get(intent, {}).get(
        install_method_str,
        f"Manually manage spec-kitty-cli ({install_method_str}).",
    )
