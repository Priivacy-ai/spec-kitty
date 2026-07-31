"""Resolution matrix for :func:`doctrine.pack_paths.resolve_pack_root` (WP02).

Covers the four-step ``built-in`` resolution order plus the ``org`` / ``project``
pass-through seam:

* **Editable** — the nearest ancestor of the module file holding ``packs/built-in/``
  is returned.
* **Installed** — a *faithful filesystem simulation* of the site-packages layout
  (``<site>/doctrine`` package dir with a sibling ``<site>/packs/built-in``) is
  resolved via the ``files("doctrine")`` step. We simulate rather than build and
  ``pip install`` a wheel into a clean venv: the simulation exercises the exact
  step-3 branch (``files("doctrine").parent / "packs" / "built-in"``) deterministically
  and in milliseconds; a real wheel install would add minutes of CI cost for the
  same code path. This trade-off is documented per the WP02 task allowance.
* **Symlinked checkout** — with the module file reached through a directory symlink,
  ``.resolve()`` (called before walking ``.parents``) still finds the *real*
  repo-root ``packs/``.
* **Env override** — ``SPEC_KITTY_PACKS_ROOT`` wins over an otherwise-resolvable
  editable tree.
* **Fail-closed** — with no packs anywhere and no env, :class:`PackRootNotFound`
  is raised and no ``src/doctrine`` path is returned.

All cases monkeypatch the module-level ``__file__`` and ``files`` names so the
resolver's three discovery steps are fully controlled and hermetic (the real
repository tree is never consulted).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from doctrine import pack_paths
from doctrine.pack_paths import PackRootNotFound, resolve_pack_root

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


def _make_pkg_file(pkg_dir: Path) -> Path:
    """Create ``pkg_dir`` and return the path a ``pack_paths.py`` would occupy in it."""
    pkg_dir.mkdir(parents=True, exist_ok=True)
    return pkg_dir / "pack_paths.py"


def _isolate(
    monkeypatch: pytest.MonkeyPatch,
    *,
    module_file: Path,
    doctrine_dir: Path | None,
) -> None:
    """Pin the resolver's discovery inputs: env cleared, ``__file__`` and ``files``."""
    monkeypatch.delenv(pack_paths._PACKS_ROOT_ENV, raising=False)
    monkeypatch.setattr(pack_paths, "__file__", str(module_file))

    def fake_files(_name: str) -> Path:
        if doctrine_dir is None:
            raise ModuleNotFoundError(_name)
        return doctrine_dir

    monkeypatch.setattr(pack_paths, "files", fake_files)


def test_editable_resolves_repo_root_packs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Editable checkout: the ancestor holding ``packs/built-in/`` is returned."""
    repo = tmp_path / "repo"
    module_file = _make_pkg_file(repo / "src" / "doctrine")
    packs_built_in = repo / "packs" / "built-in"
    packs_built_in.mkdir(parents=True)

    _isolate(monkeypatch, module_file=module_file, doctrine_dir=None)

    assert resolve_pack_root("built-in") == packs_built_in


def test_installed_resolves_site_packages_sibling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Installed layout: ``files('doctrine').parent/packs/built-in`` is returned.

    Faithful simulation of the site-packages sibling layout (documented above).
    The module file lives in an isolated tree with no ``packs/`` ancestor so the
    editable step (2) misses and step (3) fires.
    """
    site = tmp_path / "site-packages"
    doctrine_dir = site / "doctrine"
    doctrine_dir.mkdir(parents=True)
    packs_built_in = site / "packs" / "built-in"
    packs_built_in.mkdir(parents=True)

    # Isolated module location with no packs/built-in anywhere up its tree.
    module_file = _make_pkg_file(tmp_path / "isolated" / "nested" / "doctrine")

    _isolate(monkeypatch, module_file=module_file, doctrine_dir=doctrine_dir)

    assert resolve_pack_root("built-in") == packs_built_in


def test_symlinked_checkout_resolves_real_repo_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dir-symlinked package still resolves the real repo-root ``packs/`` via ``.resolve()``."""
    real_repo = tmp_path / "real-repo"
    real_pkg = real_repo / "src" / "doctrine"
    real_pkg.mkdir(parents=True)
    packs_built_in = real_repo / "packs" / "built-in"
    packs_built_in.mkdir(parents=True)

    # Symlinked "site" view onto the real package dir; the symlink's own parent
    # (site/) has NO packs -- only .resolve() to the real tree finds them.
    site = tmp_path / "site"
    site.mkdir()
    link = site / "doctrine"
    link.symlink_to(real_pkg, target_is_directory=True)
    module_file = link / "pack_paths.py"

    _isolate(monkeypatch, module_file=module_file, doctrine_dir=None)

    resolved = resolve_pack_root("built-in")
    assert resolved == packs_built_in.resolve()


def test_env_override_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``SPEC_KITTY_PACKS_ROOT`` wins over an otherwise-resolvable editable tree."""
    repo = tmp_path / "repo"
    module_file = _make_pkg_file(repo / "src" / "doctrine")
    editable_packs = repo / "packs" / "built-in"
    editable_packs.mkdir(parents=True)

    env_root = tmp_path / "env-packs"
    env_built_in = env_root / "built-in"
    env_built_in.mkdir(parents=True)

    _isolate(monkeypatch, module_file=module_file, doctrine_dir=None)
    monkeypatch.setenv(pack_paths._PACKS_ROOT_ENV, str(env_root))

    resolved = resolve_pack_root("built-in")
    assert resolved == env_built_in
    assert resolved != editable_packs


def test_env_override_missing_dir_falls_through_to_editable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An env value that has no ``built-in/`` subdir does not short-circuit resolution."""
    repo = tmp_path / "repo"
    module_file = _make_pkg_file(repo / "src" / "doctrine")
    editable_packs = repo / "packs" / "built-in"
    editable_packs.mkdir(parents=True)

    _isolate(monkeypatch, module_file=module_file, doctrine_dir=None)
    monkeypatch.setenv(pack_paths._PACKS_ROOT_ENV, str(tmp_path / "empty"))

    assert resolve_pack_root("built-in") == editable_packs


def test_fail_closed_when_no_packs_anywhere(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No env, no editable, no installed -> PackRootNotFound; never a src/doctrine path."""
    module_file = _make_pkg_file(tmp_path / "isolated" / "doctrine")
    empty_site = tmp_path / "site" / "doctrine"
    empty_site.mkdir(parents=True)  # sibling packs/ deliberately absent

    _isolate(monkeypatch, module_file=module_file, doctrine_dir=empty_site)

    with pytest.raises(PackRootNotFound) as excinfo:
        resolve_pack_root("built-in")
    assert excinfo.value.tier == "built-in"


def test_fail_closed_when_files_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When ``files('doctrine')`` raises, step 3 is skipped and resolution fails closed."""
    module_file = _make_pkg_file(tmp_path / "isolated" / "doctrine")

    _isolate(monkeypatch, module_file=module_file, doctrine_dir=None)

    with pytest.raises(PackRootNotFound):
        resolve_pack_root("built-in")


@pytest.mark.parametrize(
    ("tier", "kwarg"),
    [("org", "org_root"), ("project", "project_root")],
)
def test_org_and_project_return_caller_root(
    tmp_path: Path, tier: str, kwarg: str
) -> None:
    """``org`` / ``project`` return the caller-supplied root unchanged (shared seam)."""
    supplied = tmp_path / tier
    supplied.mkdir()
    resolved = resolve_pack_root(tier, **{kwarg: supplied})  # type: ignore[arg-type]
    assert resolved == supplied


@pytest.mark.parametrize("tier", ["org", "project"])
def test_org_and_project_fail_closed_without_root(tier: str) -> None:
    """A missing caller root for ``org`` / ``project`` fails closed."""
    with pytest.raises(PackRootNotFound) as excinfo:
        resolve_pack_root(tier)  # type: ignore[arg-type]
    assert excinfo.value.tier == tier


def test_pure_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Same inputs and environment yield the same path across repeated calls."""
    repo = tmp_path / "repo"
    module_file = _make_pkg_file(repo / "src" / "doctrine")
    (repo / "packs" / "built-in").mkdir(parents=True)

    _isolate(monkeypatch, module_file=module_file, doctrine_dir=None)

    first = resolve_pack_root("built-in")
    second = resolve_pack_root("built-in")
    assert first == second


def test_module_imports_no_upward_layer() -> None:
    """C-004: pack_paths imports only stdlib -- nothing from charter/specify_cli."""
    import ast

    source = Path(pack_paths.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)

    offenders = [
        mod for mod in imported if mod.split(".")[0] in {"charter", "specify_cli"}
    ]
    assert not offenders, f"pack_paths must not import upward: {offenders}"
