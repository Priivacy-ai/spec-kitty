"""LatestVersionResult.source Literal includes simple_index."""

from __future__ import annotations

from typing import get_args, get_type_hints

from specify_cli.compat.provider import LatestVersionResult
import pytest

pytestmark = pytest.mark.fast


def test_simple_index_source_literal() -> None:
    result = LatestVersionResult(version="1.0.0", source="simple_index", error=None)
    assert result.source == "simple_index"
    assert result.version == "1.0.0"


def test_source_literal_members() -> None:
    hints = get_type_hints(LatestVersionResult)
    members = set(get_args(hints["source"]))
    assert members == {"pypi", "simple_index", "none"}
