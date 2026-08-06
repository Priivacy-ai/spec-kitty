"""WP02 review cycle 2: the four degrade arms stranded on the routed call chain.

Routing ``read_primary_meta`` onto ``load_meta_fail_closed`` (WP02, census rows
10/11) changed the exception a corrupt ``meta.json`` produces from ``ValueError``
to :class:`~specify_cli.core.paths.MissionMetaReadError`, whose MRO is
``RuntimeError -> Exception -> BaseException -> object``. It is deliberately
**not** a ``ValueError`` and **not** an ``OSError``.

WP02 swept its own file for ``except`` clauses that would stop absorbing
corruption and fixed the two it found. The sweep needed to be **chain-local**:
four more arms sit on the routed function's transitive *callers*, on the chain::

    _find_feature_directory -> resolve_handle_to_read_path -> read_primary_meta

Each one reads ``except (ValueError, ActionContextError)``, so the typed error
flies straight past the structured-detection handler and lands in the command's
top-level ``except Exception``. Both still exit 1, so an exit-code assertion sees
nothing — but the **agent-facing JSON contract silently loses** ``error_code``,
``mission_flag``, ``available_missions`` and ``example_command``. That is exactly
the arm change ``C-001`` forbids.

These tests assert the *payload*, not the exit code, because the payload is where
the regression actually lives.

``setup-plan`` and ``record-analysis`` are pinned end-to-end on a corrupt-meta
fixture with no patching at all. ``check-prerequisites`` and ``finalize-tasks``
are pinned at the seam their arm guards, because each re-reads the primary meta
later at an unguarded site that keeps the end-to-end payload degraded regardless
of how the arm is written — see the comment above those two tests. All four arms
are additionally pinned statically.

Repeatable instrument for the same defect class:
``scripts/sweep_degrade_arms_on_routed_chain_3162.py``.
"""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import mission as mission_mod
from specify_cli.cli.commands.agent import mission_finalize as mission_finalize_mod
from specify_cli.core.paths import MissionMetaReadError

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

#: Truncated, syntactically invalid JSON — a REAL corrupt file, not a stub.
_CORRUPT_META = '{"mission_id":'

_MISSION_ID = "01KWP02C2ARMSWEEP7X9QZTBVK"
_MID8 = _MISSION_ID[:8]
_HUMAN_SLUG = "wp02-cycle2-arm-probe"
#: The COMPOSED handle is the only form that reaches the corrupt file: bare mid8,
#: full ULID and bare human slug are all canonicalized through an index that
#: skips dirs with unreadable meta, so they never read it. (Row-11 unreachability.)
_COMPOSED_HANDLE = f"{_HUMAN_SLUG}-{_MID8}"

#: The payload keys the degrade contract promises to agents.
_CONTRACT_KEYS = ("error_code", "mission_flag", "available_missions")


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), *args], check=True, capture_output=True, text=True
    )


def _build_corrupt_mission(repo_root: Path) -> Path:
    """Create a real git repo with ``kitty-specs/<composed>/meta.json`` corrupt."""
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "wp02-cycle2@example.test")
    _git(repo_root, "config", "user.name", "WP02 Cycle2 Probe")
    _git(repo_root, "commit", "--allow-empty", "-qm", "init")

    # The ``.kittify/`` marker is what makes this a spec-kitty project root;
    # without it resolution fails earlier, on PROJECT_ROOT_NOT_FOUND, and the
    # corrupt-meta arm is never reached (the test would go red for the wrong
    # reason and prove nothing).
    (repo_root / ".kittify").mkdir()

    feature_dir = repo_root / "kitty-specs" / _COMPOSED_HANDLE
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(_CORRUPT_META, encoding="utf-8")
    # spec.md keeps the dir a valid detection candidate, so a correct degrade
    # payload has a non-empty available_missions to assert on.
    (feature_dir / "spec.md").write_text("# probe\n", encoding="utf-8")
    return feature_dir


@pytest.fixture
def corrupt_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repo whose sole mission has a corrupt primary ``meta.json``."""
    _build_corrupt_mission(tmp_path)
    monkeypatch.chdir(tmp_path)
    # The SaaS preflight exits 2 before resolution is ever reached.
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.setenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", "1")
    return tmp_path


def _invoke(args: list[str]) -> dict[str, Any]:
    """Invoke the mission app and return the single emitted JSON object."""
    result = CliRunner().invoke(mission_mod.app, args)
    output = result.output.strip()
    start, end = output.find("{"), output.rfind("}")
    assert start != -1 and end != -1, f"no JSON object in output: {output!r}"
    payload: dict[str, Any] = json.loads(output[start : end + 1])
    return payload


def _assert_degrade_contract(payload: dict[str, Any], command: str) -> None:
    """Assert the structured detection payload survived the corrupt-meta read."""
    missing = [key for key in _CONTRACT_KEYS if key not in payload]
    assert not missing, (
        f"{command}: agent-facing degrade contract lost {missing} on a corrupt "
        f"meta.json. MissionMetaReadError (a RuntimeError) escaped the "
        f"`except (ValueError, ActionContextError)` detection arm and fell "
        f"through to the top-level `except Exception`. Payload was: {payload!r}"
    )
    assert _COMPOSED_HANDLE in payload["available_missions"]


# --------------------------------------------------------------------------
# Behavioural, fixture-driven: these two call the resolution seam unconditionally.
# --------------------------------------------------------------------------


def test_setup_plan_keeps_detection_payload_on_corrupt_meta(corrupt_repo: Path) -> None:
    """BEHAVIOURAL (fixture-driven). ``setup-plan``'s degrade arm, chain-local."""
    payload = _invoke(["setup-plan", "--json", "--mission", _COMPOSED_HANDLE])
    _assert_degrade_contract(payload, "setup-plan")


def test_record_analysis_keeps_detection_payload_on_corrupt_meta(
    corrupt_repo: Path,
) -> None:
    """BEHAVIOURAL (fixture-driven). ``record-analysis``'s degrade arm."""
    input_file = corrupt_repo / "analysis.md"
    input_file.write_text("# analysis\n", encoding="utf-8")
    payload = _invoke(
        [
            "record-analysis",
            "--json",
            "--mission",
            _COMPOSED_HANDLE,
            "--input-file",
            str(input_file),
        ]
    )
    _assert_degrade_contract(payload, "record-analysis")


# --------------------------------------------------------------------------
# Arm-contract (seam-injected). These two commands cannot be pinned end-to-end
# on a corrupt-meta fixture, for a reason discovered while remediating and
# deliberately NOT fixed here (it is outside this bounded fix-list): each reads
# the primary meta AGAIN, later, at a site guarded by no arm at all --
#
#   check-prerequisites -> mission_branch_context._resolve_feature_target_branch
#                       -> core.paths.read_target_branch_from_meta
#   finalize-tasks      -> _validate_occurrence_map_ready
#                       -> bulk_edit.gate.ensure_occurrence_classification_ready
#                          (plus a direct resolution.read_dir)
#
# So the end-to-end payload stays degraded no matter how the detection arm is
# written, and an end-to-end assertion here would be testing the UNFIXED site,
# not the fixed one. These tests therefore inject the typed error at the seam
# the arm actually guards and assert what the arm alone owns. They are red on a
# ``(ValueError, ActionContextError)`` arm and green on the widened one.
# --------------------------------------------------------------------------


def test_check_prerequisites_arm_absorbs_typed_error_into_payload(
    corrupt_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ARM-CONTRACT (seam-injected). ``check-prerequisites``'s detection arm."""

    def _raise(*_a: object, **_k: object) -> None:
        raise MissionMetaReadError(
            corrupt_repo / "kitty-specs" / _COMPOSED_HANDLE / "meta.json",
            ValueError("Malformed JSON"),
        )

    monkeypatch.setattr(mission_mod, "_primary_anchored_feature_dir", _raise)
    payload = _invoke(["check-prerequisites", "--json", "--mission", _COMPOSED_HANDLE])
    _assert_degrade_contract(payload, "check-prerequisites")


def test_finalize_tasks_arm_absorbs_typed_error_into_payload(
    corrupt_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ARM-CONTRACT (seam-injected). ``finalize-tasks``'s detection arm."""

    def _raise(*_a: object, **_k: object) -> None:
        raise MissionMetaReadError(
            corrupt_repo / "kitty-specs" / _COMPOSED_HANDLE / "meta.json",
            ValueError("Malformed JSON"),
        )

    monkeypatch.setattr(
        mission_finalize_mod,
        "_resolve_mission_dir_name_primary_anchored",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(mission_mod, "_find_feature_directory", _raise)
    payload = _invoke(["finalize-tasks", "--json", "--mission", _COMPOSED_HANDLE])
    _assert_degrade_contract(payload, "finalize-tasks")


# --------------------------------------------------------------------------
# Static pin: the four arms name MissionMetaReadError.
# --------------------------------------------------------------------------

_AGENT_DIR = Path(__file__).resolve().parents[5] / "src" / "specify_cli" / "cli" / "commands" / "agent"

#: (module file, enclosing function) — keyed by SYMBOL, never by line number, so
#: benign edits elsewhere in these files cannot make this pin false-red.
_ROUTED_DEGRADE_ARMS = [
    ("mission_setup_plan.py", "_resolve_setup_plan_feature_dir"),
    ("mission_record_analysis.py", "record_analysis"),
    ("mission_finalize.py", "_resolve_mission_slug"),
    ("mission_check_prerequisites.py", "check_prerequisites"),
]


def _handler_names(handler: ast.ExceptHandler) -> list[str]:
    if handler.type is None:
        return ["<bare>"]
    nodes = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    out = []
    for node in nodes:
        if isinstance(node, ast.Name):
            out.append(node.id)
        elif isinstance(node, ast.Attribute):
            out.append(node.attr)
    return out


@pytest.mark.parametrize(("filename", "function"), _ROUTED_DEGRADE_ARMS)
def test_routed_chain_degrade_arm_names_the_typed_error(
    filename: str, function: str
) -> None:
    """STATIC. Each detection arm on the routed chain catches MissionMetaReadError.

    Complements the behavioural tests: it pins all four arms uniformly, including
    the two whose behavioural coverage needs a patch seam, and it fails on a
    re-narrowing even if no test happens to drive that command.
    """
    path = _AGENT_DIR / filename
    tree = ast.parse(path.read_text(encoding="utf-8"))
    target = next(
        (
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) and n.name == function
        ),
        None,
    )
    assert target is not None, f"{filename}: no function {function!r}"

    detection_arms = [
        h
        for node in ast.walk(target)
        if isinstance(node, ast.Try)
        for h in node.handlers
        if "ActionContextError" in _handler_names(h)
    ]
    assert detection_arms, f"{filename}:{function}: no ActionContextError detection arm found"

    for handler in detection_arms:
        names = _handler_names(handler)
        assert "MissionMetaReadError" in names, (
            f"{path.name}:{handler.lineno} in {function}: detection arm catches "
            f"{names} — MissionMetaReadError (a RuntimeError, not a ValueError) "
            f"would escape and drop the structured payload. Widen the tuple."
        )
