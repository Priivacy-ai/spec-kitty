"""Pure cancellation projection for mission finalization inputs."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TypeVar

from specify_cli.status import Lane

_T = TypeVar("_T")


@dataclass(frozen=True, slots=True, order=True)
class StaleCanceledDependency:
    """A direct dependency from executable work to a canceled prerequisite."""

    dependent_wp_id: str
    canceled_dependency_wp_id: str

    @property
    def recovery(self) -> str:
        return f"Remove the dependency or repoint {self.dependent_wp_id} to a non-canceled prerequisite."

    def to_dict(self) -> dict[str, str]:
        return {
            "dependent_wp_id": self.dependent_wp_id,
            "canceled_dependency_wp_id": self.canceled_dependency_wp_id,
            "recovery": self.recovery,
        }


@dataclass(frozen=True, slots=True)
class FinalizationEligibility:
    """Current-state projection used by finalization execution consumers."""

    known_wp_ids: tuple[str, ...]
    eligible_wp_ids: tuple[str, ...]
    canceled_wp_ids: tuple[str, ...]
    eligible_dependencies: Mapping[str, tuple[str, ...]]
    stale_dependencies: tuple[StaleCanceledDependency, ...]

    @property
    def all_canceled(self) -> bool:
        return bool(self.known_wp_ids) and len(self.canceled_wp_ids) == len(self.known_wp_ids)


def project_finalization_eligibility(
    known_wp_ids: Iterable[str],
    dependencies: Mapping[str, Iterable[str]],
    lifecycle_lanes: Mapping[str, Lane],
) -> FinalizationEligibility:
    """Partition executable/canceled work and remove canceled edges."""
    known = tuple(sorted(set(known_wp_ids)))
    known_set = set(known)
    canceled = tuple(wp_id for wp_id in known if lifecycle_lanes.get(wp_id) is Lane.CANCELED)
    canceled_set = set(canceled)
    eligible = tuple(wp_id for wp_id in known if wp_id not in canceled_set)

    stale = tuple(
        sorted(
            {
                StaleCanceledDependency(wp_id, prerequisite)
                for wp_id in eligible
                for prerequisite in dependencies.get(wp_id, ())
                if prerequisite in known_set and prerequisite in canceled_set
            }
        )
    )
    projected = MappingProxyType(
        {wp_id: tuple(sorted(prerequisite for prerequisite in dependencies.get(wp_id, ()) if prerequisite not in canceled_set)) for wp_id in eligible}
    )
    return FinalizationEligibility(
        known_wp_ids=known,
        eligible_wp_ids=eligible,
        canceled_wp_ids=canceled,
        eligible_dependencies=projected,
        stale_dependencies=stale,
    )


def filter_by_wp_ids(values: Mapping[str, _T], wp_ids: Iterable[str]) -> dict[str, _T]:
    """Return the requested keyed subset without inventing missing entries."""
    return {wp_id: values[wp_id] for wp_id in wp_ids if wp_id in values}
