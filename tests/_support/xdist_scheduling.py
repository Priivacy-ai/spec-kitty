"""Promote xdist's unspecified ``--dist`` default from ``load`` to ``loadfile``.

``pytest-xdist`` itself upgrades an unspecified ``--dist`` from its own default
(``"no"``) to ``"load"`` the moment ``-n``/``--numprocesses`` is set
(``xdist/plugin.py::pytest_cmdline_main``, which runs before ANY
``pytest_configure``, including ``tests/conftest.py``'s). ``load`` scatters a
single file's tests across workers with no file-scoping guarantee -- this
repo's own docs (``docs/development/testing/testing-parallel.md``) already say
"Always ``--dist loadfile``, never bare ``--dist load``" for exactly that
reason, but that rule was previously enforced only by CI's explicit
``--dist loadfile`` flag and by developers remembering to type it locally. A
bare ``pytest tests/ -n <N>`` -- the exact invocation TEST-M2-03's own
acceptance criterion uses, and what ``docs/bootstrap/M2-CANONICAL-INTEGRATION.
json`` ran to produce its "240 failed" baseline -- silently got the unsafe
``load`` default instead, and a file-scoped module-level accumulator (the "ran
every declared cell" non-vacuity pattern several ``tests/sync/tracker/
test_*_3108.py`` / ``test_egress_single_authority.py`` files use) then sees
only the subset of its own file's parametrized cases that happened to land on
ITS worker -- reproduced directly: ``test_egress_single_authority.py``'s
``test_matrix_ran_every_cell_incl_permit_row_and_every_precedence_level`` reds
under bare ``-n5`` and is clean under ``-n5 --dist loadfile`` or ``-n0``.
Promoting the *default* the same way xdist promotes ``"no"`` -- only when the
user did not ask for a specific mode -- closes that gap at its root for every
such file at once, rather than opting each one in individually.

Kept out of ``tests/conftest.py`` itself (rather than defined there directly)
because that module is under a hard architectural gate
(``tests/architectural/test_home_owner_behaviour.py::
test_conftest_definition_order_is_unchanged_with_the_owner_removed``) that
permits exactly one new top-level definition beyond a frozen merge-base
snapshot. An imported name does not add an AST-visible ``FunctionDef`` to
that module, so this helper lives here instead -- see
``tests/_support/fixture_pollution.py`` for the same pattern applied earlier.
"""

from __future__ import annotations

import pytest

__all__ = ["upgrade_unspecified_xdist_load_to_loadfile"]


def upgrade_unspecified_xdist_load_to_loadfile(config: pytest.Config) -> None:
    """Called from ``tests/conftest.py::pytest_configure``. See module docstring."""
    if not getattr(config.option, "numprocesses", None):
        return
    if config.option.dist != "load":
        # Either genuinely serial ("no"), or the user/CI passed an explicit
        # --dist (loadfile/loadscope/loadgroup/worksteal/each) -- never
        # override a deliberate choice, only the silent "no" -> "load"
        # auto-upgrade xdist performs when nothing was specified.
        return
    raw_args = [str(arg) for arg in config.invocation_params.args]
    if any(arg == "--dist" or arg.startswith("--dist=") for arg in raw_args):
        return
    config.option.dist = "loadfile"
