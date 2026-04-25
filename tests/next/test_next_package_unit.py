"""Unit tests for lazy exports in ``specify_cli.next``."""

from __future__ import annotations

import pytest

import specify_cli.next as next_pkg

pytestmark = pytest.mark.fast


def test_lazy_decision_exports_are_cached() -> None:
    next_pkg.__dict__.pop("DecisionKind", None)

    decision_kind = next_pkg.__getattr__("DecisionKind")

    assert next_pkg.DecisionKind is decision_kind
    assert next_pkg.__dict__["DecisionKind"] is decision_kind


def test_unknown_lazy_export_raises_attribute_error() -> None:
    with pytest.raises(AttributeError, match="does_not_exist"):
        next_pkg.__getattr__("does_not_exist")
