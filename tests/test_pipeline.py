"""src/pipeline.py 테스트"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.pipeline import ReviewerIntelligencePipeline


class TestManuscriptSplitting:
    """원고 분할 로직 테스트 (API 호출 불필요)"""

    def test_split_by_section_headers(self):
        text = """Introduction
This is the introduction.

Literature Review
Some literature here.

Method
Methodology description.

Discussion
Discussion of results.

Conclusion
Final thoughts.
"""
        # Create pipeline without initializing API clients
        with patch("src.pipeline.ReviewerIntelligencePipeline.__init__", return_value=None):
            p = ReviewerIntelligencePipeline.__new__(ReviewerIntelligencePipeline)
            sections = p._split_manuscript(text)
            assert len(sections) >= 4  # At least Intro, Lit Review, Method, Discussion

    def test_split_by_length_when_no_headers(self):
        text = " ".join(["word"] * 20000)
        with patch("src.pipeline.ReviewerIntelligencePipeline.__init__", return_value=None):
            p = ReviewerIntelligencePipeline.__new__(ReviewerIntelligencePipeline)
            sections = p._split_manuscript(text, max_chunk=8000)
            assert len(sections) >= 2

    def test_single_short_section(self):
        text = "A short manuscript text."
        with patch("src.pipeline.ReviewerIntelligencePipeline.__init__", return_value=None):
            p = ReviewerIntelligencePipeline.__new__(ReviewerIntelligencePipeline)
            sections = p._split_manuscript(text)
            assert len(sections) == 1


class TestManuscriptLoading:
    def test_load_txt_file(self, tmp_path):
        txt_path = tmp_path / "test.txt"
        txt_path.write_text("Test manuscript content.", encoding="utf-8")

        with patch("src.pipeline.ReviewerIntelligencePipeline.__init__", return_value=None):
            p = ReviewerIntelligencePipeline.__new__(ReviewerIntelligencePipeline)
            text = p._load_manuscript(str(txt_path))
            assert text == "Test manuscript content."


class TestResultSaving:
    def test_save_results(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.pipeline.settings.outputs_dir", tmp_path)

        with patch("src.pipeline.ReviewerIntelligencePipeline.__init__", return_value=None):
            p = ReviewerIntelligencePipeline.__new__(ReviewerIntelligencePipeline)
            results = {"profile": "test", "cost_summary": {"total_cost": 0.5}}
            p._save_results("Test Reviewer", results)

        output_dir = tmp_path / "Test_Reviewer"
        assert output_dir.exists()
        result_file = output_dir / "pipeline_results.json"
        assert result_file.exists()
