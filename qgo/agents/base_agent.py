# Copyright (c) 2024 Rahul Chaube. All Rights Reserved.
#
# QGo — AI Coding Assistant
# Author: Rahul Chaube
# License: Apache-2.0
"""Abstract base class for all QGo agents.

Copyright (c) 2024 Rahul Chaube. All Rights Reserved.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    WORKING = "working"
    DONE = "done"
    ERROR = "error"


@dataclass
class AgentMessage:
    """A message passed between agents."""

    sender: str
    recipient: str        # agent name or "all"
    content: str
    message_type: str = "text"   # text | task | result | error
    metadata: dict = field(default_factory=dict)


@dataclass
class AgentResult:
    """The output produced by an agent after completing a task."""

    agent_name: str
    success: bool
    output: str
    artifacts: dict[str, Any] = field(default_factory=dict)  # e.g. {"files": [...]}
    error: str = ""


class BaseAgent(ABC):
    """Abstract base for all QGo specialist agents.

    Each agent has a name, a role description, and a dedicated LLM instance.
    Agents communicate through the orchestrator's message bus.

    Copyright (c) 2024 Rahul Chaube. All Rights Reserved.
    """

    #: Short identifier used in logs and messages
    name: str = "base"
    #: One-line description of what this agent does
    role: str = "Generic agent"
    #: Emoji icon shown in the terminal
    icon: str = "🤖"

    def __init__(self, llm, config=None, io=None) -> None:
        self.llm = llm
        self.config = config
        self.io = io
        self.status = AgentStatus.IDLE
        self._inbox: list[AgentMessage] = []

    # ── Core interface ────────────────────────────────────────────────

    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt that defines this agent's persona."""
        ...

    def run(self, task: str, context: dict | None = None) -> AgentResult:
        """Execute the given task and return a result.

        Args:
            task: Natural-language description of the work to do.
            context: Optional dict with extra context (files, previous results, …).
        """
        self.status = AgentStatus.THINKING
        if self.io:
            self.io.print_info(f"{self.icon} [{self.name.upper()}] starting: {task[:80]}")

        try:
            messages = self._build_messages(task, context or {})
            response = self._call_llm(messages)
            self.status = AgentStatus.DONE
            return AgentResult(
                agent_name=self.name,
                success=True,
                output=response,
            )
        except Exception as exc:
            self.status = AgentStatus.ERROR
            if self.io:
                self.io.print_error(f"{self.name}: {exc}")
            return AgentResult(
                agent_name=self.name,
                success=False,
                output="",
                error=str(exc),
            )

    def receive(self, message: AgentMessage) -> None:
        """Accept a message from another agent or the orchestrator."""
        self._inbox.append(message)

    # ── Private helpers ───────────────────────────────────────────────

    def _build_messages(self, task: str, context: dict) -> list[dict]:
        msgs: list[dict] = [{"role": "system", "content": self.system_prompt()}]
        # Inject any context files
        if context.get("files"):
            files_block = "\n\n".join(
                f"### {name}\n```\n{content}\n```"
                for name, content in context["files"].items()
            )
            msgs.append({"role": "user", "content": f"Relevant files:\n\n{files_block}"})
            msgs.append({"role": "assistant", "content": "I've reviewed the files."})

        # Inject previous agent results
        if context.get("previous_results"):
            for result in context["previous_results"]:
                msgs.append({
                    "role": "user",
                    "content": f"Output from {result.agent_name}:\n{result.output}",
                })
                msgs.append({"role": "assistant", "content": "Understood."})

        msgs.append({"role": "user", "content": task})
        return msgs

    def _call_llm(self, messages: list[dict]) -> str:
        """Call the LLM and return the full text response."""
        stream = getattr(self.config, "stream", True) if self.config else True

        if stream and self.io and hasattr(self.io, "stream_response"):
            iterator = self.llm.complete(messages, stream=True)
            # Consume iterator
            if hasattr(iterator, "__iter__"):
                return self.io.stream_response(iterator)

        result = self.llm.complete(messages, stream=False)
        return str(result)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, status={self.status})"
