# Copyright (c) 2024 Rahul Chaube. All Rights Reserved.
#
# QGo — AI Coding Assistant
# Author: Rahul Chaube
"""Tests for the QGo multi-agent system.

Copyright (c) 2024 Rahul Chaube. All Rights Reserved.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from qgo.agents.base_agent import AgentMessage, AgentResult, AgentStatus, BaseAgent
from qgo.agents.orchestrator import AgentOrchestrator
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


# ─── Fixtures ─────────────────────────────────────────────────────────────

def make_llm(response: str = "Mock LLM response") -> MagicMock:
    llm = MagicMock()
    llm.complete.return_value = response
    llm.count_tokens.return_value = 10
    llm.model_name = "gpt-4o"
    return llm


# ─── AgentMessage ─────────────────────────────────────────────────────────

class TestAgentMessage:
    def test_creation(self):
        msg = AgentMessage(
            sender="planner",
            recipient="coder",
            content="Write a function",
            message_type="task",
        )
        assert msg.sender == "planner"
        assert msg.recipient == "coder"
        assert msg.content == "Write a function"
        assert msg.message_type == "task"
        assert msg.metadata == {}

    def test_default_message_type(self):
        msg = AgentMessage(sender="a", recipient="b", content="hello")
        assert msg.message_type == "text"


# ─── AgentResult ──────────────────────────────────────────────────────────

class TestAgentResult:
    def test_success_result(self):
        result = AgentResult(agent_name="coder", success=True, output="def foo(): pass")
        assert result.success is True
        assert result.output == "def foo(): pass"
        assert result.error == ""

    def test_error_result(self):
        result = AgentResult(agent_name="coder", success=False, output="", error="timeout")
        assert result.success is False
        assert result.error == "timeout"


# ─── BaseAgent ────────────────────────────────────────────────────────────

class ConcreteAgent(BaseAgent):
    name = "concrete"
    role = "Test agent"
    icon = "🧩"

    def system_prompt(self) -> str:
        return "You are a test agent."


class TestBaseAgent:
    def test_initial_status(self):
        agent = ConcreteAgent(llm=make_llm())
        assert agent.status == AgentStatus.IDLE

    def test_run_success(self):
        agent = ConcreteAgent(llm=make_llm("Great code here"))
        result = agent.run("Write hello world")
        assert result.success is True
        assert result.agent_name == "concrete"
        assert "Great code here" in result.output
        assert agent.status == AgentStatus.DONE

    def test_run_with_context_files(self):
        agent = ConcreteAgent(llm=make_llm("done"))
        result = agent.run(
            "Fix the bug",
            context={"files": {"main.py": "def foo(): pass"}},
        )
        assert result.success is True

    def test_run_error_handling(self):
        llm = MagicMock()
        llm.complete.side_effect = RuntimeError("API down")
        agent = ConcreteAgent(llm=llm)
        result = agent.run("do something")
        assert result.success is False
        assert "API down" in result.error
        assert agent.status == AgentStatus.ERROR

    def test_receive_message(self):
        agent = ConcreteAgent(llm=make_llm())
        msg = AgentMessage(sender="orchestrator", recipient="concrete", content="hello")
        agent.receive(msg)
        assert msg in agent._inbox

    def test_repr(self):
        agent = ConcreteAgent(llm=make_llm())
        r = repr(agent)
        assert "ConcreteAgent" in r
        assert "concrete" in r


# ─── Specialist Agents ────────────────────────────────────────────────────

@pytest.mark.parametrize("AgentClass,expected_name", [
    (PlannerAgent, "planner"),
    (CoderAgent, "coder"),
    (ReviewerAgent, "reviewer"),
    (TesterAgent, "tester"),
    (DebuggerAgent, "debugger"),
    (DocWriterAgent, "doc_writer"),
    (SecurityAgent, "security"),
    (RefactorAgent, "refactor"),
])
class TestSpecialistAgents:
    def test_name(self, AgentClass, expected_name):
        agent = AgentClass(llm=make_llm())
        assert agent.name == expected_name

    def test_has_icon(self, AgentClass, expected_name):
        agent = AgentClass(llm=make_llm())
        assert agent.icon  # non-empty

    def test_system_prompt_nonempty(self, AgentClass, expected_name):
        agent = AgentClass(llm=make_llm())
        prompt = agent.system_prompt()
        assert len(prompt) > 50  # meaningful prompt

    def test_system_prompt_has_copyright(self, AgentClass, expected_name):
        agent = AgentClass(llm=make_llm())
        prompt = agent.system_prompt()
        assert "Rahul Chaube" in prompt

    def test_run_returns_result(self, AgentClass, expected_name):
        agent = AgentClass(llm=make_llm("output text"))
        result = agent.run("Do some task")
        assert isinstance(result, AgentResult)
        assert result.agent_name == expected_name


# ─── Orchestrator ─────────────────────────────────────────────────────────

class TestAgentOrchestrator:
    def _make_orchestrator(self, plan_response: str = "", agent_response: str = "done"):
        """Create an orchestrator where planner returns plan_response."""
        llm = make_llm(agent_response)

        orch = AgentOrchestrator(llm=llm)
        # Patch the planner to return a controlled plan
        orch.planner.llm = make_llm(plan_response)
        return orch

    def test_list_agents(self):
        orch = AgentOrchestrator(llm=make_llm())
        agents = orch.list_agents()
        names = [a["name"] for a in agents]
        assert "planner" in names
        assert "coder" in names
        assert "reviewer" in names
        assert "tester" in names
        assert "security" in names

    def test_run_with_valid_plan(self):
        plan = '[{"agent": "coder", "task": "write hello world"}]'
        orch = self._make_orchestrator(plan_response=plan, agent_response="def hello(): ...")
        result = orch.run("Write a hello world function")
        assert isinstance(result, str)
        assert "CODER" in result

    def test_run_falls_back_when_plan_empty(self):
        orch = self._make_orchestrator(plan_response="no json here", agent_response="code output")
        result = orch.run("Do something")
        assert isinstance(result, str)

    def test_run_single_agent(self):
        orch = AgentOrchestrator(llm=make_llm("security report"))
        result = orch.run_single("security", "Audit auth.py")
        assert result.agent_name == "security"
        assert result.success is True

    def test_run_single_unknown_agent_raises(self):
        orch = AgentOrchestrator(llm=make_llm())
        with pytest.raises(ValueError, match="Unknown agent"):
            orch.run_single("nonexistent_agent", "task")

    def test_parse_plan_valid_json(self):
        orch = AgentOrchestrator(llm=make_llm())
        plan_json = '[{"agent": "coder", "task": "write tests"}]'
        result = orch._parse_plan(plan_json)
        assert len(result) == 1
        assert result[0]["agent"] == "coder"

    def test_parse_plan_embedded_json(self):
        orch = AgentOrchestrator(llm=make_llm())
        text = 'Here is my plan:\n[{"agent": "tester", "task": "write tests"}]\nDone.'
        result = orch._parse_plan(text)
        assert len(result) == 1
        assert result[0]["agent"] == "tester"

    def test_parse_plan_invalid_json(self):
        orch = AgentOrchestrator(llm=make_llm())
        result = orch._parse_plan("not json at all")
        assert result == []

    def test_compile_report_includes_all_agents(self):
        results = [
            AgentResult("coder", True, "some code"),
            AgentResult("reviewer", True, "looks good"),
        ]
        report = AgentOrchestrator._compile_report("my task", results)
        assert "CODER" in report
        assert "REVIEWER" in report
        assert "my task" in report
        assert "Rahul Chaube" in report

    def test_compile_report_handles_errors(self):
        results = [AgentResult("coder", False, "", error="timeout")]
        report = AgentOrchestrator._compile_report("task", results)
        assert "❌" in report
        assert "timeout" in report

    def test_respects_max_agents(self):
        plan = '[{"agent": "coder", "task": "t1"}, {"agent": "tester", "task": "t2"}, {"agent": "reviewer", "task": "t3"}]'
        orch = self._make_orchestrator(plan_response=plan, agent_response="ok")
        result = orch.run("big task", max_agents=1)
        # Only 1 agent should have run (besides planner)
        assert result.count("Agent\n") <= 2
