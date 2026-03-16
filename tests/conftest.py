"""공통 테스트 픽스처"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _set_env(tmp_path, monkeypatch):
    """모든 테스트에서 환경 변수 격리"""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setenv("COST_LOG_PATH", str(tmp_path / "cost_log.jsonl"))


@pytest.fixture
def tmp_cost_log(tmp_path):
    return tmp_path / "cost_log.jsonl"


@pytest.fixture
def sample_papers_data():
    """샘플 논문 메타데이터"""
    return [
        {
            "paper_id": "abc123",
            "title": "International Order and Global Governance",
            "year": 2020,
            "venue": "International Organization",
            "citation_count": 45,
            "abstract": "This paper examines the evolving nature of international order...",
            "doi": "10.1017/S0020818320000001",
            "authors": [{"name": "John Scholar", "author_id": "111"}],
            "open_access_pdf_url": None,
        },
        {
            "paper_id": "def456",
            "title": "Constructivism and World Politics",
            "year": 2018,
            "venue": "European Journal of International Relations",
            "citation_count": 120,
            "abstract": "A critical analysis of constructivist approaches to IR theory...",
            "doi": "10.1177/1354066118000002",
            "authors": [{"name": "John Scholar", "author_id": "111"}],
            "open_access_pdf_url": "https://example.com/paper.pdf",
        },
    ]


@pytest.fixture
def sample_manuscript_text():
    """샘플 원고 텍스트"""
    return """Introduction

This paper examines the role of international institutions in shaping state behavior.
We argue that constructivist approaches provide a more nuanced understanding of
institutional dynamics than rationalist frameworks.

Literature Review

Several scholars have examined institutional design (Koremenos et al. 2001).
The liberal institutionalist tradition emphasizes cooperation gains (Keohane 1984).

Method

We employ a comparative case study methodology examining three international
organizations over a twenty-year period.

Discussion

Our findings suggest that normative considerations play a crucial role
in institutional evolution, challenging purely materialist explanations.

Conclusion

This study contributes to the growing literature on institutional change
by highlighting the interplay between material and ideational factors.

References
Abbott, Kenneth. 2000. International Relations and International Law. AJIL 94(3): 345-367.
Barnett, Michael. 2002. Eyewitness to a Genocide. Cornell University Press.
Finnemore, Martha. 1996. National Interests in International Society. Cornell UP.
"""


@pytest.fixture
def sample_profile():
    return json.dumps({
        "core_frameworks": ["Constructivism", "English School"],
        "methodological_stance": "Historical-interpretive, case studies",
        "key_concepts": ["international order", "sovereignty", "legitimacy"],
        "critical_patterns": ["Neglect of historical context", "Over-reliance on rationalism"],
    })


@pytest.fixture
def mock_anthropic_response():
    """Anthropic API 응답 Mock"""
    response = MagicMock()
    response.content = [MagicMock(text='{"result": "test output"}')]
    response.model = "claude-sonnet-4-6"
    response.usage = MagicMock(
        input_tokens=500,
        output_tokens=200,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )
    return response
