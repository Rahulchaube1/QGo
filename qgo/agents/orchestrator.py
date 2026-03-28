# Copyright (c) 2024 Rahul Chaube. All Rights Reserved.
#
# QGo — AI Coding Assistant
# Author: Rahul Chaube
# License: Apache-2.0
"""Multi-agent orchestrator for QGo.

Coordinates specialist agents to complete complex tasks collaboratively.
Inspired by multi-agent frameworks but built from scratch by Rahul Chaube.

Copyright (c) 2024 Rahul Chaube. All Rights Reserved.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from qgo.agents.base_agent import AgentMessage, AgentResult, BaseAgent
from qgo.agents.specialist_agents import (
    CoderAgent,
    DebuggerAgent,
    DocWriterAgent,
    PlannerAgent,
    RefactorAgent,
    ReviewerAgent,
    SecurityAgent,
    TesterAgent,
)

if TYPE_CHECKING:
    from qgo.ui.terminal import QGoIO


class AgentOrchestrator:
    """Coordinates multiple specialist agents to complete complex tasks.

    Workflow:
    1. PlannerAgent decomposes the task into ordered sub-tasks
    2. Each sub-task is dispatched to the appropriate specialist agent
    3. Results are accumulated and passed as context to subsequent agents
    4. Final output is a summary of all agent contributions

    Example::

        orchestrator = AgentOrchestrator(llm=llm, io=io)
        result = orchestrator.run("Add authentication to the Flask app")

    Copyright (c) 2024 Rahul Chaube. All Rights Reserved.
    """

    def __init__(self, llm, config=None, io: "QGoIO | None" = None) -> None:
        self.llm = llm
        self.config = config
        self.io = io

        # Instantiate all specialist agents
        agent_kwargs = dict(llm=llm, config=config, io=io)
        self.planner = PlannerAgent(**agent_kwargs)
        self._agents: dict[str, BaseAgent] = {
            "coder":      CoderAgent(**agent_kwargs),
            "reviewer":   ReviewerAgent(**agent_kwargs),
            "tester":     TesterAgent(**agent_kwargs),
            "debugger":   DebuggerAgent(**agent_kwargs),
            "doc_writer": DocWriterAgent(**agent_kwargs),
            "security":   SecurityAgent(**agent_kwargs),
            "refactor":   RefactorAgent(**agent_kwargs),
        }
        self._message_bus: list[AgentMessage] = []

    # ── Public API ────────────────────────────────────────────────────

    def run(
        self,
        task: str,
        files: dict[str, str] | None = None,
        max_agents: int = 5,
    ) -> str:
        """Run the full multi-agent pipeline for the given task.

        Args:
            task: High-level description of what needs to be done.
            files: Dict mapping filename → content for relevant files.
            max_agents: Maximum number of agent steps to execute.

        Returns:
            A comprehensive markdown-formatted report of all agent outputs.
        """
        if self.io:
            self.io.print_info("🚀 Multi-agent pipeline starting...")

        context: dict = {"files": files or {}, "previous_results": []}

        # Step 1: Plan
        plan_result = self.planner.run(task, context)
        sub_tasks = self._parse_plan(plan_result.output)

        if self.io:
            self.io.print_info(f"📋 Plan: {len(sub_tasks)} sub-tasks identified")

        if not sub_tasks:
            # Fallback: run the coder directly
            sub_tasks = [{"agent": "coder", "task": task}]

        # Step 2: Execute sub-tasks in order (up to max_agents)
        results: list[AgentResult] = []
        for i, step in enumerate(sub_tasks[:max_agents]):
            agent_name = step.get("agent", "coder")
            sub_task = step.get("task", task)

            agent = self._agents.get(agent_name)
            if not agent:
                if self.io:
                    self.io.print_warning(f"Unknown agent: {agent_name}, using coder")
                agent = self._agents["coder"]

            if self.io:
                self.io.print_info(
                    f"\n[{i+1}/{min(len(sub_tasks), max_agents)}] "
                    f"{agent.icon} {agent.name.upper()}: {sub_task[:70]}"
                )

            # Add previous results to context so agents can build on each other
            context["previous_results"] = results.copy()
            result = agent.run(sub_task, context)
            results.append(result)

            # Broadcast result to message bus
            self._broadcast(AgentMessage(
                sender=agent.name,
                recipient="all",
                content=result.output,
                message_type="result",
            ))

        return self._compile_report(task, results)

    def run_single(self, agent_name: str, task: str, context: dict | None = None) -> AgentResult:
        """Run a single named agent directly.

        Args:
            agent_name: Name of the agent (e.g. 'coder', 'reviewer').
            task: Task description.
            context: Optional context dict.
        """
        agent = self._agents.get(agent_name)
        if not agent:
            available = ", ".join(self._agents.keys())
            raise ValueError(f"Unknown agent: {agent_name!r}. Available: {available}")
        return agent.run(task, context or {})

    def list_agents(self) -> list[dict]:
        """Return info about all available agents."""
        agents = [
            {"name": self.planner.name, "role": self.planner.role, "icon": self.planner.icon}
        ]
        for a in self._agents.values():
            agents.append({"name": a.name, "role": a.role, "icon": a.icon})
        return agents

    # ── Private helpers ───────────────────────────────────────────────

    def _parse_plan(self, plan_output: str) -> list[dict]:
        """Extract the JSON plan from planner output."""
        # Try to find a JSON array in the output
        start = plan_output.find("[")
        end = plan_output.rfind("]") + 1
        if start != -1 and end > start:
            try:
                return json.loads(plan_output[start:end])
            except json.JSONDecodeError:
                pass
        return []

    def _broadcast(self, message: AgentMessage) -> None:
        """Put a message on the bus; deliver to all registered agents."""
        self._message_bus.append(message)
        for agent in self._agents.values():
            if message.recipient in ("all", agent.name):
                agent.receive(message)

    @staticmethod
    def _compile_report(task: str, results: list[AgentResult]) -> str:
        """Build a Markdown report from all agent results."""
        lines = [
            "# Multi-Agent Report",
            f"\n**Task:** {task}\n",
            f"**Agents involved:** {len(results)}\n",
            "---",
        ]
        for result in results:
            status = "✅" if result.success else "❌"
            lines.append(f"\n## {status} {result.agent_name.upper()} Agent\n")
            if result.success:
                lines.append(result.output)
            else:
                lines.append(f"*Error: {result.error}*")

        lines.append("\n---\n*Generated by QGo Multi-Agent System — © 2024 Rahul Chaube*")
        return "\n".join(lines)
