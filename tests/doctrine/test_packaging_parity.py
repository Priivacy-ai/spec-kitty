"""Packaging parity for the relocated built-in doctrine packs (mission
``relocate-builtin-doctrine-packs-01KYT87F``, WP05 — FR-007 / NFR-002).

``packs/built-in/`` must ship **completely** in BOTH the monolith wheel and the
sdist, and a clean-venv install must be able to ``import doctrine`` and resolve
the built-in pack root to a real, complete on-disk tree.

Why this test builds real artifacts (not a config assertion): the pre-spec
adversarial squad proved a build can exit 0 while shipping an *empty or partial*
artifact. So the acceptance gate is the built artifacts' **contents** and a live
import, never "build exited 0" or a `>=` count (a `>=` passes on duplication).

Marked ``@pytest.mark.distribution`` (slow: builds a wheel + an sdist + creates a
clean venv + installs the wheel) and ``@pytest.mark.integration``. It does not run
in the fast gate::

    pytest tests/doctrine/test_packaging_parity.py -m distribution -v
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
import venv
import zipfile
from pathlib import Path

import pytest

pytestmark = [pytest.mark.distribution, pytest.mark.integration]

_THIS = Path(__file__).resolve()
REPO_ROOT = _THIS.parents[2]
MANIFEST_JSON = _THIS.parent / "fixtures" / "content-manifest.json"

_PACKS_PREFIX = "packs/built-in/"
_SRC_DOCTRINE_PREFIX = "src/doctrine/"


# --------------------------------------------------------------------------- #
# Move-set truth: transform the pre-move manifest into the post-move pack paths
# --------------------------------------------------------------------------- #


def _to_pack_path(src_rel: str) -> str:
    """Map a pre-move ``src/doctrine/...`` manifest path to its post-move
    ``packs/built-in/...`` location.

    Two shapes exist in the manifest:

    * ``src/doctrine/<kind>/built-in/<rest>`` -> ``packs/built-in/<kind>/<rest>``
      (the ``built-in`` segment collapses into the pack root).
    * ``src/doctrine/<name>.graph.yaml`` -> ``packs/built-in/<name>.graph.yaml``
      (root DRG fragments).
    """
    assert src_rel.startswith(_SRC_DOCTRINE_PREFIX), src_rel
    tail = src_rel[len(_SRC_DOCTRINE_PREFIX) :]
    if "/built-in/" in tail:
        kind, rest = tail.split("/built-in/", 1)
        return f"{_PACKS_PREFIX}{kind}/{rest}"
    return f"{_PACKS_PREFIX}{tail}"


def _expected_pack_paths() -> set[str]:
    manifest: list[str] = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    expected = {_to_pack_path(rel) for rel in manifest}
    assert len(expected) == len(manifest), "manifest -> pack transform collided"
    return expected


# --------------------------------------------------------------------------- #
# Build both artifacts once (expensive) and share across tests
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def built_artifacts(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """Build wheel + sdist from the repo tree into a temp dir; return (whl, sdist)."""
    dist = tmp_path_factory.mktemp("wp05-dist")
    subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(dist), str(REPO_ROOT)],
        check=True,
        capture_output=True,
        text=True,
    )
    wheels = list(dist.glob("spec_kitty_cli-*.whl"))
    sdists = list(dist.glob("spec_kitty_cli-*.tar.gz"))
    assert len(wheels) == 1, f"expected exactly one wheel, found {wheels}"  # golden-count: cardinality-is-contract
    assert len(sdists) == 1, f"expected exactly one sdist, found {sdists}"  # golden-count: cardinality-is-contract
    return wheels[0], sdists[0]


def _wheel_pack_paths(wheel: Path) -> set[str]:
    with zipfile.ZipFile(wheel) as zf:
        return {
            name
            for name in zf.namelist()
            if name.startswith(_PACKS_PREFIX) and not name.endswith("/")
        }


def _sdist_pack_paths(sdist: Path) -> set[str]:
    """Return the ``packs/built-in/...`` members of the sdist, stripped of the
    single ``spec_kitty_cli-<version>/`` top-level component sdists prepend."""
    found: set[str] = set()
    with tarfile.open(sdist) as tf:
        for member in tf.getmembers():
            if not member.isfile():
                continue
            _root, _, rel = member.name.partition("/")
            if rel.startswith(_PACKS_PREFIX):
                found.add(rel)
    return found


# --------------------------------------------------------------------------- #
# NFR-002 acceptance 1 — exact set-equality in EACH artifact
# --------------------------------------------------------------------------- #


def test_wheel_ships_built_in_packs_at_exact_parity(
    built_artifacts: tuple[Path, Path],
) -> None:
    wheel, _sdist = built_artifacts
    expected = _expected_pack_paths()
    actual = _wheel_pack_paths(wheel)
    missing = expected - actual
    extra = actual - expected
    assert actual == expected, (
        f"wheel packs/built-in mismatch — missing: {sorted(missing)}, "
        f"extra: {sorted(extra)}"
    )


def test_sdist_ships_built_in_packs_at_exact_parity(
    built_artifacts: tuple[Path, Path],
) -> None:
    _wheel, sdist = built_artifacts
    expected = _expected_pack_paths()
    actual = _sdist_pack_paths(sdist)
    missing = expected - actual
    extra = actual - expected
    assert actual == expected, (
        f"sdist packs/built-in mismatch — missing: {sorted(missing)}, "
        f"extra: {sorted(extra)}"
    )


# --------------------------------------------------------------------------- #
# NFR-002 acceptance 2 (packaging truth only) — clean-venv import + resolve
#
# Scope guard: this WP depends only on WP03. The loader repoint that makes
# ``load_built_in_graph()`` read the relocated fragments is WP04, and the
# full-graph (324/892) proof from a clean install lives in WP07. Here we assert
# ONLY packaging truth: ``import doctrine`` succeeds and
# ``resolve_pack_root("built-in")`` yields a complete, real on-disk tree.
# --------------------------------------------------------------------------- #


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":  # pragma: no cover — CI runs on Linux
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def test_clean_venv_install_imports_and_resolves_built_in(
    built_artifacts: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    """Install the wheel into a clean venv (declared deps only, no repo ``src/``)
    and prove ``import doctrine`` + ``resolve_pack_root('built-in')`` reach a
    complete installed tree with 0 missing manifest files."""
    wheel, _sdist = built_artifacts
    venv_dir = tmp_path / "clean-venv"
    venv.create(venv_dir, with_pip=True, clear=True)
    py = _venv_python(venv_dir)

    subprocess.run(
        [str(py), "-m", "pip", "install", "--upgrade", "pip"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [str(py), "-m", "pip", "install", str(wheel)],
        check=True,
        capture_output=True,
        text=True,
    )

    expected = _expected_pack_paths()
    # Relative-to-root paths (drop the leading ``packs/built-in/``) so the child
    # can check each one exists under the resolved pack root.
    rel_under_root = sorted(p[len(_PACKS_PREFIX) :] for p in expected)

    probe = (
        "import json, sys\n"
        "from pathlib import Path\n"
        "import doctrine  # noqa: F401 — import must succeed from the wheel\n"
        "from doctrine.pack_paths import resolve_pack_root\n"
        "root = resolve_pack_root('built-in')\n"
        "assert root.is_dir(), f'pack root not a dir: {root}'\n"
        "# Fail-closed contract: never resolve into a src/doctrine/ tree.\n"
        "assert 'src/doctrine' not in root.as_posix(), root.as_posix()\n"
        "rels = json.loads(sys.argv[1])\n"
        "missing = [r for r in rels if not (root / r).is_file()]\n"
        "assert not missing, f'{len(missing)} missing files, e.g. {missing[:5]}'\n"
        "print(json.dumps({'root': str(root), 'checked': len(rels)}))\n"
    )

    # Run from a cwd OUTSIDE the repo worktree, and strip any packs-root override,
    # so resolution can only reach the *installed* tree — never the repo checkout.
    child_env = {k: v for k, v in os.environ.items() if k != "SPEC_KITTY_PACKS_ROOT"}
    result = subprocess.run(
        [str(py), "-c", probe, json.dumps(rel_under_root)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        env=child_env,
    )
    assert result.returncode == 0, (
        "clean-venv import/resolve failed.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["checked"] == len(rel_under_root)
    assert _PACKS_PREFIX.rstrip("/") in payload["root"]
