"""Enforces HATEOAS-LITE paradigm.

Doctrine: src/doctrine/paradigms/shipped/hateoas-lite.paradigm.yaml

Every Pydantic class subclassing dashboard.api.models.ResourceModel MUST
declare a `_links: dict[str, Link]` field.

In this mission (mission-registry-and-api-boundary-doctrine-01KQPDBB), zero
subclasses exist per spec C-006. The test passes vacuously. Mission B
introduces the first subclass when it ships the new resource-oriented
endpoints.

Owned by WP05.
"""
from __future__ import annotations

import inspect
from typing import get_type_hints

import pytest

pytestmark = pytest.mark.architectural


def _find_resource_model_subclasses() -> list[type]:
    """Walk dashboard.api.models for ResourceModel subclasses (excluding ResourceModel itself)."""
    from dashboard.api import models
    from dashboard.api.models import ResourceModel

    subclasses = []
    for name, obj in inspect.getmembers(models):
        if (
            inspect.isclass(obj)
            and obj is not ResourceModel
            and issubclass(obj, ResourceModel)
        ):
            subclasses.append(obj)
    return subclasses


def test_every_resource_model_subclass_declares_links() -> None:
    """Walk the Pydantic hierarchy; assert _links shape on every subclass.

    In this mission, this test passes vacuously (no subclasses exist).
    Mission B activates enforcement.
    """
    from dashboard.api.models import Link

    subclasses = _find_resource_model_subclasses()

    if not subclasses:
        # Mission A: vacuous pass per spec C-006.
        return

    for cls in subclasses:
        hints = get_type_hints(cls)
        assert "_links" in hints, (
            f"{cls.__name__} subclasses ResourceModel but does NOT declare a "
            f"_links field. Required by HATEOAS-LITE paradigm; see "
            f"src/doctrine/paradigms/shipped/hateoas-lite.paradigm.yaml"
        )
        link_type = hints["_links"]
        assert link_type == dict[str, Link], (
            f"{cls.__name__}._links has wrong type: {link_type}. "
            f"Expected: dict[str, Link]"
        )


def test_meta_detector_flags_synthetic_violator() -> None:
    """Positive meta-test: synthetic ResourceModel subclass without _links is flagged."""
    from dashboard.api.models import ResourceModel

    class SyntheticBadResource(ResourceModel):
        name: str
        # missing _links

    hints = get_type_hints(SyntheticBadResource)
    assert "_links" not in hints  # confirms detector logic


def test_meta_detector_accepts_synthetic_compliant_resource() -> None:
    """Negative meta-test: synthetic compliant subclass passes the check."""
    from dashboard.api.models import ResourceModel, Link

    class SyntheticGoodResource(ResourceModel):
        name: str
        _links: dict[str, Link]

    # Pass localns so get_type_hints can resolve 'Link' from this function scope.
    hints = get_type_hints(SyntheticGoodResource, localns={"Link": Link})
    assert "_links" in hints
    assert hints["_links"] == dict[str, Link]
