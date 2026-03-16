"""Tests for registry.py — agent profiles."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from agents.registry import AgentProfile


class TestAgentProfiles:
    def test_agent_profile_dataclass(self):
        p = AgentProfile(name="Test", role="Tester", avatar="🧪", color="#000", system_prompt="You test.")
        assert p.name == "Test"
        assert p.role == "Tester"

    def test_builtin_agents_exist(self):
        from agents import registry
        # Should have at least WARREN defined
        assert hasattr(registry, 'WARREN')
        assert isinstance(registry.WARREN, AgentProfile)
        assert len(registry.WARREN.system_prompt) > 50
