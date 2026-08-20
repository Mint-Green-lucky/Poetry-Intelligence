# © 2026 BUPT_Mint-Green
# All rights reserved.

from backend.agents.specialist_agent import AGENTS, SPECS, AgentSpec, SpecialistAgent


def get_agent(task: str) -> SpecialistAgent:
    return AGENTS[task]


def get_spec(task: str) -> AgentSpec:
    return SPECS[task]


__all__ = ["AGENTS", "SPECS", "AgentSpec", "SpecialistAgent", "get_agent", "get_spec"]
