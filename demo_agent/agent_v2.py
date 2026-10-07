"""demo_agent/agent_v2.py: Fixed Candidate Agent using Real Runtime Tools."""

from core.agent.runtime import execute_real_agent_v2
from core.models.schema import Trajectory


async def run_agent_v2(prompt: str) -> Trajectory:
    """Runs Agent V2 with real SQLite join tool execution and real time measurement."""
    tracer = execute_real_agent_v2(prompt)
    return tracer.to_trajectory()
