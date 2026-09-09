"""Red-first: the packs workflow's retired-dir ``__pycache__`` sweep (WP14, T072).

A retired test directory can leave behind only its ``__pycache__`` bytecode
orphans (the ``.py`` source deleted, the compiled ``.pyc`` left behind) --
e.g. after a WP05-style retirement scrub that removes the source but leaves
stale on-disk bytecode from a previous local/CI run. Left alone, that orphan
must never be re-collected as a test module. ``.github/workflows/packs.yml``
(T076) closes this with a dedicated "Sweep retired-dir __pycache__ orphans"
step in the built-in lane's corpus-suite job.

This file pins that step's actual behaviour, not just its presence: it reads
the step's ``run:`` shell script directly off the committed YAML (the single
authored source -- no second hand-maintained copy of the sweep logic) and
executes that *exact* script against a manufactured orphan tree, asserting
the orphan is gone afterward and that pytest collection over that tree stays
empty (the "not re-collected" half of the DoD).

**Collection-red lazy-load hygiene:** ``packs.yml`` does not exist on base.
Every read of it happens inside a test function, never at module import time,
so this file always *collects* cleanly -- the red (on base) is a failed
behavioural assertion (workflow file / sweep step absent), never a collection
or import error.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKS_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "packs.yml"

# The step we pin, identified by its `id:` (stable across a `name:` rewording).
_SWEEP_STEP_ID = "pycache-sweep"
_SWEEP_STEP_NAME_NEEDLE = "__pycache__"


def _load_packs_workflow() -> dict[str, Any]:
    """Parse the on-disk ``packs.yml``. Called lazily (never at import time)."""
    import yaml

    assert _PACKS_WORKFLOW.is_file(), f"{_PACKS_WORKFLOW} does not exist -- WP14 must author the packs workflow with a retired-dir __pycache__ sweep step (T076)"
    data = yaml.safe_load(_PACKS_WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "packs.yml must parse to a mapping"
    return data


def _find_sweep_step(workflow: dict[str, Any]) -> dict[str, Any]:
    """Find the sweep step by its stable ``id:`` across every job's steps."""
    jobs = workflow.get("jobs") or {}
    for job in jobs.values():
        for step in job.get("steps") or []:
            step_dict: dict[str, Any] = step
            if step_dict.get("id") == _SWEEP_STEP_ID:
                return step_dict
            name = step_dict.get("name") or ""
            if _SWEEP_STEP_NAME_NEEDLE in name and "sweep" in name.lower():
                return step_dict
    raise AssertionError(
        f"no step with id={_SWEEP_STEP_ID!r} (or a name mentioning "
        f"{_SWEEP_STEP_NAME_NEEDLE!r} + 'sweep') found in any packs.yml job -- "
        "T076's retired-dir __pycache__ sweep step is missing"
    )


def _plant_retired_dir_orphan(root: Path) -> Path:
    """Create a retired-dir ``__pycache__`` orphan under *root*.

    Simulates a test directory whose ``.py`` source was deleted by a
    retirement scrub but whose compiled bytecode cache was left behind: a
    ``__pycache__`` directory containing a ``.pyc`` with **no** sibling
    ``.py`` file anywhere in its parent directory.
    """
    retired_dir = root / "tests" / "retired_module"
    pycache_dir = retired_dir / "__pycache__"
    pycache_dir.mkdir(parents=True)
    orphan_pyc = pycache_dir / "test_retired.cpython-311.pyc"
    orphan_pyc.write_bytes(b"\x00\x00\x00\x00fake-bytecode-orphan")

    # Sanity: this really is an orphan (no live .py sibling anywhere in the
    # retired directory) -- otherwise the fixture wouldn't exercise the T072
    # scenario at all.
    assert not any(retired_dir.glob("*.py")), "fixture setup bug: the planted orphan has a live .py sibling"
    return pycache_dir


def test_packs_workflow_has_a_retired_dir_pycache_sweep_step() -> None:
    """The sweep step must exist and target ``__pycache__`` directories."""
    workflow = _load_packs_workflow()
    step = _find_sweep_step(workflow)
    script = step.get("run")
    assert isinstance(script, str) and script.strip(), "the sweep step must carry a non-empty `run:` shell script"
    assert "__pycache__" in script, "the sweep step's script must reference __pycache__ directly"


def test_sweep_step_removes_a_planted_retired_dir_orphan(tmp_path: Path) -> None:
    """Executing the sweep step's exact on-disk script removes the orphan."""
    workflow = _load_packs_workflow()
    step = _find_sweep_step(workflow)
    script = step["run"]

    pycache_dir = _plant_retired_dir_orphan(tmp_path)
    assert pycache_dir.is_dir(), "fixture setup bug: orphan not planted"

    result = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"sweep step script exited non-zero: stdout={result.stdout!r} stderr={result.stderr!r}"
    assert not pycache_dir.exists(), "the sweep step's script did not remove the planted retired-dir __pycache__ orphan"
    # The whole retired directory tree is inert now (no __pycache__ anywhere
    # under it) -- confirms the sweep is not merely emptying the directory.
    assert not any(tmp_path.rglob("__pycache__")), "a __pycache__ directory survived the sweep somewhere under the tree"


def test_swept_orphan_is_never_re_collected_by_pytest(tmp_path: Path) -> None:
    """After the sweep, pytest collection over the tree stays empty.

    The orphan never had a live ``.py`` file, so pytest should never have
    collected anything from it in the first place -- this corroborates the
    "not re-collected" half of the DoD by proving collection is empty both
    before and after the sweep runs.
    """
    workflow = _load_packs_workflow()
    step = _find_sweep_step(workflow)
    script = step["run"]

    _plant_retired_dir_orphan(tmp_path)

    def _collect_count() -> int:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        # Exit code 5 == "no tests collected" (pytest's own floor semantics,
        # reused by the corpus suite's exit-5 gate) -- the expected outcome
        # here, since the orphan never carried a live .py module.
        assert proc.returncode in (0, 5), f"unexpected pytest collection outcome: rc={proc.returncode} stdout={proc.stdout!r} stderr={proc.stderr!r}"
        return proc.returncode

    assert _collect_count() == 5, "orphan pyc alone must not be collectible pre-sweep"

    subprocess.run(["bash", "-c", script], cwd=tmp_path, capture_output=True, text=True, timeout=30, check=True)

    assert _collect_count() == 5, "post-sweep collection must still find nothing"
