"""논문 메타데이터 + 전문 텍스트를 SQLite에 저장"""
import json
import sqlite3
from pathlib import Path

import sqlite_utils

from src.config import settings
from src.utils.logging_config import logger


class PaperStore:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or settings.papers_dir / "papers.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # isolation_level=None → autocommit 모드 (모든 Python 버전 호환)
        conn = sqlite3.connect(str(self.db_path), isolation_level=None)
        self.db = sqlite_utils.Database(conn)
        self._init_tables()

    def _init_tables(self):
        """테이블 초기화 — raw SQL로 생성하여 WAL 모드 호환성 보장"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                paper_id    TEXT PRIMARY KEY,
                title       TEXT,
                abstract    TEXT,
                year        INTEGER,
                venue       TEXT,
                doi         TEXT,
                citation_count INTEGER,
                full_text   TEXT,
                pdf_path    TEXT,
                acquisition_status TEXT,
                reviewer_id TEXT
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS reviewers (
                reviewer_id   TEXT PRIMARY KEY,
                name          TEXT,
                s2_author_id  TEXT,
                affiliations  TEXT,
                h_index       INTEGER,
                profile_json  TEXT
            )
        """)

    def upsert_paper(self, paper_data: dict):
        """논문 메타데이터 upsert"""
        self.db["papers"].upsert(paper_data, pk="paper_id")
        logger.debug(f"논문 저장: {paper_data.get('title', '')[:50]}")

    def upsert_reviewer(self, reviewer_data: dict):
        """리뷰어 정보 upsert"""
        # affiliations가 리스트이면 JSON 문자열로 변환
        if isinstance(reviewer_data.get("affiliations"), list):
            reviewer_data["affiliations"] = json.dumps(
                reviewer_data["affiliations"], ensure_ascii=False
            )
        self.db["reviewers"].upsert(reviewer_data, pk="reviewer_id")
        logger.debug(f"리뷰어 저장: {reviewer_data.get('name', '')}")

    def get_paper(self, paper_id: str) -> dict | None:
        """논문 ID로 단일 논문 조회"""
        try:
            return self.db["papers"].get(paper_id)
        except sqlite_utils.db.NotFoundError:
            return None

    def get_reviewer(self, reviewer_id: str) -> dict | None:
        """리뷰어 ID로 단일 리뷰어 조회"""
        try:
            return self.db["reviewers"].get(reviewer_id)
        except sqlite_utils.db.NotFoundError:
            return None

    def get_reviewer_papers(self, reviewer_id: str) -> list[dict]:
        """특정 리뷰어의 모든 논문 목록"""
        return list(self.db["papers"].rows_where("reviewer_id = ?", [reviewer_id]))

    def get_papers_needing_upload(self) -> list[dict]:
        """업로드 대기 상태인 논문 목록"""
        return list(
            self.db["papers"].rows_where("acquisition_status = ?", ["needs_upload"])
        )

    def get_papers_by_status(self, status: str) -> list[dict]:
        """상태별 논문 목록"""
        return list(
            self.db["papers"].rows_where("acquisition_status = ?", [status])
        )

    def update_full_text(self, paper_id: str, full_text: str):
        """논문 전문 텍스트 업데이트"""
        self.db["papers"].update(paper_id, {"full_text": full_text})
        logger.debug(f"전문 텍스트 저장: {paper_id} ({len(full_text)} chars)")

    def all_reviewers(self) -> list[dict]:
        """모든 리뷰어 목록"""
        return list(self.db["reviewers"].rows)

    def all_papers(self) -> list[dict]:
        """모든 논문 목록"""
        return list(self.db["papers"].rows)

    @property
    def paper_count(self) -> int:
        return self.db["papers"].count

    @property
    def reviewer_count(self) -> int:
        return self.db["reviewers"].count
