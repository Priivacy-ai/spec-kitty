"""Doctrine service for lazy access to all doctrine repositories."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from doctrine.agent_profiles import AgentProfileRepository
from doctrine.directives import DirectiveRepository
from doctrine.mission_step_contracts import MissionStepContractRepository
from doctrine.paradigms import ParadigmRepository
from doctrine.procedures import ProcedureRepository
from doctrine.styleguides import StyleguideRepository
from doctrine.tactics import TacticRepository
from doctrine.toolguides import ToolguideRepository


class DoctrineService:
    """Lazy aggregation service for doctrine repositories."""

    def __init__(
        self,
        shipped_root: Path | None = None,
        project_root: Path | None = None,
    ) -> None:
        self._shipped_root = shipped_root
        self._project_root = project_root
        self._cache: dict[str, object] = {}

    def _shipped_dir(self, artifact: str) -> Path | None:
        if self._shipped_root is None:
            return None
        return self._shipped_root / artifact / "shipped"

    def _project_dir(self, artifact: str) -> Path | None:
        if self._project_root is None:
            return None
        return self._project_root / artifact

    @property
    def directives(self) -> DirectiveRepository:
        if "directives" not in self._cache:
            self._cache["directives"] = DirectiveRepository(
                shipped_dir=self._shipped_dir("directives"),
                project_dir=self._project_dir("directives"),
            )
        return cast(DirectiveRepository, self._cache["directives"])

    @property
    def tactics(self) -> TacticRepository:
        if "tactics" not in self._cache:
            self._cache["tactics"] = TacticRepository(
                shipped_dir=self._shipped_dir("tactics"),
                project_dir=self._project_dir("tactics"),
            )
        return cast(TacticRepository, self._cache["tactics"])

    @property
    def styleguides(self) -> StyleguideRepository:
        if "styleguides" not in self._cache:
            self._cache["styleguides"] = StyleguideRepository(
                shipped_dir=self._shipped_dir("styleguides"),
                project_dir=self._project_dir("styleguides"),
            )
        return cast(StyleguideRepository, self._cache["styleguides"])

    @property
    def toolguides(self) -> ToolguideRepository:
        if "toolguides" not in self._cache:
            self._cache["toolguides"] = ToolguideRepository(
                shipped_dir=self._shipped_dir("toolguides"),
                project_dir=self._project_dir("toolguides"),
            )
        return cast(ToolguideRepository, self._cache["toolguides"])

    @property
    def paradigms(self) -> ParadigmRepository:
        if "paradigms" not in self._cache:
            self._cache["paradigms"] = ParadigmRepository(
                shipped_dir=self._shipped_dir("paradigms"),
                project_dir=self._project_dir("paradigms"),
            )
        return cast(ParadigmRepository, self._cache["paradigms"])

    @property
    def procedures(self) -> ProcedureRepository:
        if "procedures" not in self._cache:
            self._cache["procedures"] = ProcedureRepository(
                shipped_dir=self._shipped_dir("procedures"),
                project_dir=self._project_dir("procedures"),
            )
        return cast(ProcedureRepository, self._cache["procedures"])

    @property
    def mission_step_contracts(self) -> MissionStepContractRepository:
        if "mission_step_contracts" not in self._cache:
            self._cache["mission_step_contracts"] = MissionStepContractRepository(
                shipped_dir=self._shipped_dir("mission_step_contracts"),
                project_dir=self._project_dir("mission_step_contracts"),
            )
        return cast(MissionStepContractRepository, self._cache["mission_step_contracts"])

    @property
    def agent_profiles(self) -> AgentProfileRepository:
        if "agent_profiles" not in self._cache:
            self._cache["agent_profiles"] = AgentProfileRepository(
                shipped_dir=self._shipped_dir("agent_profiles"),
                project_dir=self._project_dir("agent_profiles"),
            )
        return cast(AgentProfileRepository, self._cache["agent_profiles"])

