"""src/optimization/ 테스트"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config import ModelTier, AgentType, AGENT_MODEL_MAP
from src.optimization.cost_tracker import CostTracker
from src.optimization.batch_processor import BatchProcessor


class TestCostTracker:
    def test_log_creates_file(self, tmp_path, monkeypatch):
        log_path = tmp_path / "cost.jsonl"
        monkeypatch.setattr("src.optimization.cost_tracker.settings.cost_log_path", log_path)

        CostTracker.log(
            agent="profiler",
            model="claude-sonnet-4-6",
            input_tokens=1000,
            output_tokens=500,
        )
        assert log_path.exists()
        entries = [json.loads(line) for line in log_path.read_text().strip().split("\n")]
        assert len(entries) == 1
        assert entries[0]["agent"] == "profiler"
        assert entries[0]["input_tokens"] == 1000

    def test_cost_calculation_sonnet(self, tmp_path, monkeypatch):
        log_path = tmp_path / "cost.jsonl"
        monkeypatch.setattr("src.optimization.cost_tracker.settings.cost_log_path", log_path)

        # Sonnet: $3/1M input, $15/1M output
        CostTracker.log(
            agent="profiler",
            model="claude-sonnet-4-6",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        entry = json.loads(log_path.read_text().strip())
        # cost = 1M * $3/1M + 1M * $15/1M = $18.0
        assert entry["cost_usd"] == 18.0

    def test_batch_discount(self, tmp_path, monkeypatch):
        log_path = tmp_path / "cost.jsonl"
        monkeypatch.setattr("src.optimization.cost_tracker.settings.cost_log_path", log_path)

        CostTracker.log(
            agent="simulator",
            model="claude-opus-4-6",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            is_batch=True,
        )
        entry = json.loads(log_path.read_text().strip())
        # Opus: (1M * $5 + 1M * $25) * 0.5 = $15.0
        assert entry["cost_usd"] == 15.0
        assert entry["is_batch"] is True

    def test_cache_read_discount(self, tmp_path, monkeypatch):
        log_path = tmp_path / "cost.jsonl"
        monkeypatch.setattr("src.optimization.cost_tracker.settings.cost_log_path", log_path)

        CostTracker.log(
            agent="simulator",
            model="claude-opus-4-6",
            input_tokens=1000,
            output_tokens=100,
            cache_read_tokens=800,  # 800 of 1000 from cache
        )
        entry = json.loads(log_path.read_text().strip())
        # regular_input = (1000 - 800) / 1M = 0.0002
        # cache_read = 800 / 1M = 0.0008
        # output = 100 / 1M = 0.0001
        # cost = 0.0002 * 5 + 0.0008 * 5 * 0.1 + 0.0001 * 25 = 0.001 + 0.0004 + 0.0025 = 0.0039
        assert abs(entry["cost_usd"] - 0.003900) < 0.0001

    def test_get_summary(self, tmp_path, monkeypatch):
        log_path = tmp_path / "cost.jsonl"
        monkeypatch.setattr("src.optimization.cost_tracker.settings.cost_log_path", log_path)

        CostTracker.log("profiler", "claude-sonnet-4-6", 1000, 500)
        CostTracker.log("simulator", "claude-opus-4-6", 2000, 800)

        summary = CostTracker.get_summary()
        assert summary["total_calls"] == 2
        assert summary["total_cost"] > 0
        assert "profiler" in summary["by_agent"]
        assert "simulator" in summary["by_agent"]
        assert "claude-sonnet-4-6" in summary["by_model"]

    def test_get_summary_empty(self, tmp_path, monkeypatch):
        log_path = tmp_path / "cost_empty.jsonl"
        monkeypatch.setattr("src.optimization.cost_tracker.settings.cost_log_path", log_path)

        summary = CostTracker.get_summary()
        assert summary["total_cost"] == 0
        assert summary["total_calls"] == 0

    def test_reset(self, tmp_path, monkeypatch):
        log_path = tmp_path / "cost.jsonl"
        monkeypatch.setattr("src.optimization.cost_tracker.settings.cost_log_path", log_path)

        CostTracker.log("profiler", "claude-sonnet-4-6", 1000, 500)
        assert log_path.exists()

        CostTracker.reset()
        assert not log_path.exists()


class TestBatchProcessor:
    def test_init(self):
        """BatchProcessor 인스턴스 생성"""
        with patch("src.optimization.batch_processor.anthropic.Anthropic"):
            bp = BatchProcessor()
            assert bp.client is not None

    @patch("src.optimization.batch_processor.anthropic.Anthropic")
    def test_create_batch(self, mock_anthropic):
        mock_client = MagicMock()
        mock_batch = MagicMock()
        mock_batch.id = "batch_test_123"
        mock_client.messages.batches.create.return_value = mock_batch
        mock_anthropic.return_value = mock_client

        bp = BatchProcessor()
        tasks = [
            {"id": "task-0", "content": "Review section 1"},
            {"id": "task-1", "content": "Review section 2"},
        ]
        batch_id = bp.create_batch(
            agent_type=AgentType.SIMULATOR,
            tasks=tasks,
            cached_system="Reviewer profile...",
        )
        assert batch_id == "batch_test_123"

        # Verify requests structure
        call_kwargs = mock_client.messages.batches.create.call_args[1]
        requests = call_kwargs["requests"]
        assert len(requests) == 2
        assert requests[0]["custom_id"] == "task-0"
        assert requests[0]["params"]["model"] == "claude-opus-4-6"
        # cache_control should be present
        assert requests[0]["params"]["system"][0]["cache_control"] == {"type": "ephemeral"}

    @patch("src.optimization.batch_processor.anthropic.Anthropic")
    def test_create_batch_without_cache(self, mock_anthropic):
        mock_client = MagicMock()
        mock_batch = MagicMock()
        mock_batch.id = "batch_no_cache"
        mock_client.messages.batches.create.return_value = mock_batch
        mock_anthropic.return_value = mock_client

        bp = BatchProcessor()
        batch_id = bp.create_batch(
            agent_type=AgentType.PROFILER,
            tasks=[{"id": "t0", "content": "Parse paper"}],
        )

        call_kwargs = mock_client.messages.batches.create.call_args[1]
        requests = call_kwargs["requests"]
        # No system key when cached_system is None
        assert "system" not in requests[0]["params"]
