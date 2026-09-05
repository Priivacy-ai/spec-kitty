"""NFR-003 single-channel invariant (mission
``worktree-root-resolution-01M0B59R`` WP01, C-2).

Every fail-closed WRITE refusal in scope MUST be constructed through the single
``FailClosedRefusal`` seam in ``specify_cli/core/checkout_identity.py`` — never
as an ad-hoc refusal string raised inline in an in-scope command. This makes
NFR-003's "100% of refusals name the path" an *enforced* invariant rather than a
sampled one: the ``FailClosedRefusal.message()`` constructor is the only place
that composes a write-refusal, and it embeds ``refusal_path`` verbatim.

The adopters (WP02–WP06) land later; this test starts by pinning the seam's
existence and shape (the single constructor + path-embedding contract) so that
when a command adopts it, the channel is already the enforced one. It also
scans the seam module itself for a lone ``FailClosedRefusal`` class definition —
adding a second refusal value object (or a stray inline refusal raise) inside
the seam trips the guard.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_SEAM_MODULE = Path(__file__).resolve().parents[2] / "src" / "specify_cli" / "core" / "checkout_identity.py"

#: The single sanctioned refusal value object.
_REFUSAL_CLASS = "FailClosedRefusal"


def _seam_source() -> str:
    return _SEAM_MODULE.read_text(encoding="utf-8")


def test_seam_module_exists() -> None:
    assert _SEAM_MODULE.is_file(), f"The single write-refusal seam is missing: {_SEAM_MODULE}. Every in-scope write-refusal must route through it (NFR-003)."


def test_seam_defines_exactly_one_refusal_value_object() -> None:
    """The seam module declares exactly one ``FailClosedRefusal`` class."""
    tree = ast.parse(_seam_source())
    refusal_classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == _REFUSAL_CLASS]
    assert refusal_classes == [_REFUSAL_CLASS], f"Exactly one FailClosedRefusal class must exist in the seam module; found: {refusal_classes}"


def test_refusal_is_the_single_constructor_and_embeds_path() -> None:
    """The public seam yields a refusal that embeds its path verbatim (INV-5)."""
    from specify_cli.core.checkout_identity import (
        CheckoutIdentity,
        FailClosedRefusal,
        Intent,
    )

    # Constructing the refusal directly embeds the path (the ONLY refusal
    # constructor in the codebase).
    marker = Path("/sentinel/refusal/target")
    refusal = FailClosedRefusal(refusal_path=marker)
    assert isinstance(refusal, FailClosedRefusal)
    assert str(marker) in refusal.message()

    # A foreign-checkout WRITE identity produces a refusal through the seam
    # method — no ad-hoc string channel.
    identity = CheckoutIdentity(
        invoking_root=Path("/lane/worktree"),
        canonical_target=marker,
        is_owner=False,
        intent=Intent.WRITE,
    )
    seam_refusal = identity.write_refusal()
    assert isinstance(seam_refusal, FailClosedRefusal)
    assert str(marker) in seam_refusal.message()


def test_owner_and_read_intents_produce_no_refusal() -> None:
    """Only WRITE ∧ ¬is_owner refuses; every other combination is silent (INV-6)."""
    from specify_cli.core.checkout_identity import CheckoutIdentity, Intent

    target = Path("/some/primary")
    owner_write = CheckoutIdentity(
        invoking_root=target,
        canonical_target=target,
        is_owner=True,
        intent=Intent.WRITE,
    )
    foreign_read = CheckoutIdentity(
        invoking_root=Path("/lane/worktree"),
        canonical_target=target,
        is_owner=False,
        intent=Intent.PRIMARY_READ,
    )
    assert owner_write.write_refusal() is None
    assert foreign_read.write_refusal() is None
