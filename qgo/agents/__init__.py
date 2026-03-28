# Copyright (c) 2024 Rahul Chaube. All Rights Reserved.
#
# QGo — AI Coding Assistant
# Author: Rahul Chaube
# License: Apache-2.0
#
# This file is part of QGo, created and maintained by Rahul Chaube.
# Unauthorized copying, modification, or distribution is prohibited
# without prior written permission from Rahul Chaube.
"""Multi-agent orchestration for QGo.

This package provides a powerful multi-agent system where specialised AI agents
collaborate to complete complex coding tasks — each agent has a distinct role
and they communicate through a shared message bus.

Copyright (c) 2024 Rahul Chaube. All Rights Reserved.
"""

from qgo.agents.base_agent import BaseAgent
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

__all__ = [
    "AgentOrchestrator",
    "BaseAgent",
    "PlannerAgent",
    "CoderAgent",
    "ReviewerAgent",
    "TesterAgent",
    "DebuggerAgent",
    "DocWriterAgent",
    "SecurityAgent",
    "RefactorAgent",
]
