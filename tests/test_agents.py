"""src/agents/ 테스트 — API 호출은 Mock"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.config import AgentType, AGENT_MODEL_MAP, ModelTier
from src.agents.base_agent import BaseAgent
from src.agents.profiler import ProfilerAgent
from src.agents.gap_analyzer import GapAnalyzerAgent
from src.agents.simulator import SimulatorAgent
from src.agents.strategist import StrategistAgent
from src.agents.writer import WriterAgent


class TestModelRouting:
    """에이전트별 모델 라우팅 검증"""

    def test_profiler_model(self):
        assert ProfilerAgent.agent_type == AgentType.PROFILER
        assert AGENT_MODEL_MAP[AgentType.PROFILER] == ModelTier.SONNET

    def test_gap_analyzer_model(self):
        assert GapAnalyzerAgent.agent_type == AgentType.GAP_ANALYZER
        assert AGENT_MODEL_MAP[AgentType.GAP_ANALYZER] == ModelTier.SONNET

    def test_simulator_model(self):
        assert SimulatorAgent.agent_type == AgentType.SIMULATOR
        assert AGENT_MODEL_MAP[AgentType.SIMULATOR] == ModelTier.OPUS

    def test_strategist_model(self):
        assert StrategistAgent.agent_type == AgentType.STRATEGIST
        assert AGENT_MODEL_MAP[AgentType.STRATEGIST] == ModelTier.OPUS

    def test_writer_model(self):
        assert WriterAgent.agent_type == AgentType.WRITER
        assert AGENT_MODEL_MAP[AgentType.WRITER] == ModelTier.OPUS


class TestBaseAgent:
    """BaseAgent 기본 기능 테스트"""

    @patch("src.agents.base_agent.anthropic.Anthropic")
    def test_call_with_system_prompt(self, mock_anthropic, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic.return_value = mock_client

        agent = ProfilerAgent()
        result = agent.call(
            user_message="Test message",
            system_prompt="You are a test agent.",
        )
        assert result == '{"result": "test output"}'
        mock_client.messages.create.assert_called_once()

    @patch("src.agents.base_agent.anthropic.Anthropic")
    def test_call_with_cached_context(self, mock_anthropic, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic.return_value = mock_client

        agent = ProfilerAgent()
        agent.call(
            user_message="Analyze",
            cached_context="Large reviewer profile text...",
            system_prompt="You are a profiler.",
        )

        call_kwargs = mock_client.messages.create.call_args[1]
        system_blocks = call_kwargs["system"]
        # 첫 번째 블록은 cached_context with cache_control
        assert system_blocks[0]["cache_control"] == {"type": "ephemeral"}
        assert system_blocks[0]["text"] == "Large reviewer profile text..."
        # 두 번째 블록은 system_prompt
        assert system_blocks[1]["text"] == "You are a profiler."

    @patch("src.agents.base_agent.anthropic.Anthropic")
    def test_default_prompt_loaded(self, mock_anthropic, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic.return_value = mock_client

        agent = ProfilerAgent()
        # call without system_prompt or cached_context → loads default
        agent.call(user_message="Test")

        call_kwargs = mock_client.messages.create.call_args[1]
        system_blocks = call_kwargs["system"]
        # Should have loaded from prompts/profiler_system.md
        assert len(system_blocks) >= 1
        assert "type" in system_blocks[0]


class TestProfilerAgent:
    @patch("src.agents.base_agent.anthropic.Anthropic")
    def test_run(self, mock_anthropic, mock_anthropic_response, sample_papers_data):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic.return_value = mock_client

        agent = ProfilerAgent()
        result = agent.run(
            reviewer_name="John Scholar",
            papers_data=sample_papers_data,
        )
        assert "reviewer_name" in result
        assert result["reviewer_name"] == "John Scholar"
        assert "profile" in result


class TestSimulatorAgent:
    @patch("src.agents.base_agent.anthropic.Anthropic")
    def test_run(self, mock_anthropic, mock_anthropic_response, sample_profile, sample_manuscript_text):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic.return_value = mock_client

        agent = SimulatorAgent()
        result = agent.run(
            reviewer_profile=sample_profile,
            manuscript_text=sample_manuscript_text,
        )
        assert "review" in result


class TestStrategistAgent:
    @patch("src.agents.base_agent.anthropic.Anthropic")
    def test_run(self, mock_anthropic, mock_anthropic_response, sample_profile, sample_manuscript_text):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic.return_value = mock_client

        agent = StrategistAgent()
        result = agent.run(
            reviewer_profile=sample_profile,
            simulated_review="Major Issue: Insufficient theory.",
            manuscript_text=sample_manuscript_text,
            author_intent="Keep constructivist framing.",
        )
        assert "strategy" in result


class TestWriterAgent:
    @patch("src.agents.base_agent.anthropic.Anthropic")
    def test_run(self, mock_anthropic, mock_anthropic_response, sample_profile):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic.return_value = mock_client

        agent = WriterAgent()
        result = agent.run(
            reviewer_profile=sample_profile,
            revision_strategy="Add more citations to constructivist literature.",
            original_section="This paper examines international order...",
            comment="Strengthen theoretical grounding.",
        )
        assert "revision" in result
