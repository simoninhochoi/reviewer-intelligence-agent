"""src/acquisition/ 테스트"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.acquisition.semantic_scholar import S2Paper, S2Author, SemanticScholarClient
from src.acquisition.pdf_downloader import (
    AcquisitionStatus,
    PaperAcquisitionResult,
    PaperDownloader,
)
from src.acquisition.paper_store import PaperStore


class TestS2Models:
    def test_s2paper_creation(self):
        p = S2Paper(
            paper_id="abc",
            title="Test Paper",
            year=2020,
            venue="IO",
            citation_count=10,
            abstract="An abstract.",
        )
        assert p.paper_id == "abc"
        assert p.title == "Test Paper"

    def test_s2paper_optional_fields(self):
        p = S2Paper(paper_id="abc", title="Test")
        assert p.doi is None
        assert p.open_access_pdf_url is None

    def test_s2author_creation(self):
        a = S2Author(
            author_id="111",
            name="Jane Doe",
            h_index=25,
            paper_count=50,
        )
        assert a.author_id == "111"
        assert a.h_index == 25


class TestAcquisitionStatus:
    def test_all_statuses(self):
        expected = {"oa_fetched", "proxy_fetched", "needs_upload", "uploaded", "failed"}
        actual = {s.value for s in AcquisitionStatus}
        assert actual == expected


class TestPaperAcquisitionResult:
    def test_result_model(self):
        r = PaperAcquisitionResult(
            paper_id="abc",
            title="Test",
            doi="10.1000/test",
            status=AcquisitionStatus.OA_FETCHED,
            pdf_path="/tmp/test.pdf",
            source="OA: https://example.com",
        )
        assert r.status == AcquisitionStatus.OA_FETCHED
        assert r.pdf_path == "/tmp/test.pdf"


class TestPaperStore:
    def test_upsert_and_get_paper(self, tmp_path):
        store = PaperStore(db_path=tmp_path / "test.db")
        store.upsert_paper({
            "paper_id": "abc123",
            "title": "Test Paper",
            "year": 2020,
            "doi": "10.1000/test",
        })
        paper = store.get_paper("abc123")
        assert paper is not None
        assert paper["title"] == "Test Paper"
        assert paper["year"] == 2020

    def test_upsert_reviewer(self, tmp_path):
        store = PaperStore(db_path=tmp_path / "test.db")
        store.upsert_reviewer({
            "reviewer_id": "r1",
            "name": "Jane Doe",
            "h_index": 25,
        })
        reviewer = store.get_reviewer("r1")
        assert reviewer is not None
        assert reviewer["name"] == "Jane Doe"

    def test_get_nonexistent_paper(self, tmp_path):
        store = PaperStore(db_path=tmp_path / "test.db")
        assert store.get_paper("nonexistent") is None

    def test_update_full_text(self, tmp_path):
        store = PaperStore(db_path=tmp_path / "test.db")
        store.upsert_paper({"paper_id": "abc", "title": "Test"})
        store.update_full_text("abc", "Full text content here.")
        paper = store.get_paper("abc")
        assert paper["full_text"] == "Full text content here."

    def test_get_papers_needing_upload(self, tmp_path):
        store = PaperStore(db_path=tmp_path / "test.db")
        store.upsert_paper({"paper_id": "p1", "title": "P1", "acquisition_status": "needs_upload"})
        store.upsert_paper({"paper_id": "p2", "title": "P2", "acquisition_status": "oa_fetched"})
        store.upsert_paper({"paper_id": "p3", "title": "P3", "acquisition_status": "needs_upload"})
        pending = store.get_papers_needing_upload()
        ids = [p["paper_id"] for p in pending]
        assert "p1" in ids
        assert "p3" in ids
        assert "p2" not in ids
