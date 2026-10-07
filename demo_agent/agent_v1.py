"""demo_agent/agent_v1.py: Flawed Production Agent using Real Runtime Tools."""

from core.agent.runtime import execute_real_agent_v1
from core.models.schema import Trajectory


async def run_agent_v1(prompt: str) -> Trajectory:
    """Runs Agent V1 with real SQLite tool execution and real time measurement."""
    tracer = execute_real_agent_v1(prompt)
    return tracer.to_trajectory()
