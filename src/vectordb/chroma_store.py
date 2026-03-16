"""ChromaDB 벡터 저장소 — 리뷰어 논문/저서 임베딩 관리

업로드된 PDF/DOCX/TXT에서 텍스트를 추출하고,
청크 단위로 ChromaDB에 저장하여 시맨틱 검색을 지원합니다.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.config import settings
from src.utils.logging_config import logger


class ChromaStore:
    """ChromaDB 기반 벡터 저장소

    Usage:
        store = ChromaStore()
        store.add_document("reviewer_name", "/path/to/paper.pdf", metadata={...})
        results = store.search("reviewer_name", "constructivism in IR", top_k=5)
    """

    def __init__(self, persist_dir: str | Path | None = None):
        persist = str(persist_dir or settings.chroma_persist_dir)
        self.client = chromadb.PersistentClient(
            path=persist,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.debug(f"ChromaDB 초기화: {persist}")

    # ─────────────────────────────────────────
    # Collection 관리
    # ─────────────────────────────────────────

    def _get_collection(self, reviewer_name: str):
        """리뷰어별 컬렉션 가져오기 (없으면 생성)"""
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", reviewer_name).strip("_")[:63]
        if len(safe_name) < 3:
            safe_name = safe_name + "_collection"
        return self.client.get_or_create_collection(
            name=safe_name,
            metadata={"reviewer": reviewer_name},
        )

    # ─────────────────────────────────────────
    # 문서 추가
    # ─────────────────────────────────────────

    def add_document(
        self,
        reviewer_name: str,
        file_path: str | Path,
        metadata: dict | None = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> int:
        """파일에서 텍스트를 추출하고 청크 단위로 벡터 저장

        Args:
            reviewer_name: 리뷰어 이름 (컬렉션 키)
            file_path: PDF, DOCX, 또는 TXT 파일 경로
            metadata: 추가 메타데이터 (title, year, doi 등)
            chunk_size: 청크 크기 (단어 수)
            chunk_overlap: 청크 간 겹침 (단어 수)

        Returns:
            저장된 청크 수
        """
        path = Path(file_path)
        text = self._extract_text(path)

        if not text.strip():
            logger.warning(f"텍스트 추출 실패 또는 빈 파일: {path}")
            return 0

        chunks = self._chunk_text(text, chunk_size, chunk_overlap)
        collection = self._get_collection(reviewer_name)

        base_meta = {
            "source_file": path.name,
            "reviewer": reviewer_name,
        }
        if metadata:
            base_meta.update(metadata)

        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{path.stem}_{uuid.uuid4().hex[:8]}_{i}"
            chunk_meta = {**base_meta, "chunk_index": i, "total_chunks": len(chunks)}
            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append(chunk_meta)

        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        logger.info(
            f"[{reviewer_name}] {path.name} → {len(chunks)}개 청크 저장 완료"
        )
        return len(chunks)

    def add_text(
        self,
        reviewer_name: str,
        text: str,
        metadata: dict | None = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> int:
        """텍스트를 직접 청크 단위로 벡터 저장

        Args:
            reviewer_name: 리뷰어 이름
            text: 저장할 텍스트
            metadata: 추가 메타데이터

        Returns:
            저장된 청크 수
        """
        if not text.strip():
            return 0

        chunks = self._chunk_text(text, chunk_size, chunk_overlap)
        collection = self._get_collection(reviewer_name)

        base_meta = {"reviewer": reviewer_name, "source": "direct_text"}
        if metadata:
            base_meta.update(metadata)

        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"text_{uuid.uuid4().hex[:8]}_{i}"
            chunk_meta = {**base_meta, "chunk_index": i, "total_chunks": len(chunks)}
            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append(chunk_meta)

        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        logger.info(f"[{reviewer_name}] 텍스트 → {len(chunks)}개 청크 저장 완료")
        return len(chunks)

    # ─────────────────────────────────────────
    # 검색
    # ─────────────────────────────────────────

    def search(
        self,
        reviewer_name: str,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        """시맨틱 검색

        Args:
            reviewer_name: 리뷰어 이름
            query: 검색 쿼리
            top_k: 반환할 결과 수

        Returns:
            [{"text": ..., "metadata": ..., "distance": ...}, ...]
        """
        collection = self._get_collection(reviewer_name)

        if collection.count() == 0:
            logger.info(f"[{reviewer_name}] 컬렉션이 비어 있습니다.")
            return []

        results = collection.query(query_texts=[query], n_results=min(top_k, collection.count()))

        items = []
        for i in range(len(results["ids"][0])):
            items.append({
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else None,
            })
        return items

    # ─────────────────────────────────────────
    # 컬렉션 정보
    # ─────────────────────────────────────────

    def get_stats(self, reviewer_name: str) -> dict:
        """리뷰어 컬렉션 통계"""
        collection = self._get_collection(reviewer_name)
        return {
            "reviewer": reviewer_name,
            "total_chunks": collection.count(),
            "collection_name": collection.name,
        }

    def list_reviewers(self) -> list[str]:
        """등록된 리뷰어 목록"""
        collections = self.client.list_collections()
        reviewers = []
        for col in collections:
            meta = col.metadata or {}
            reviewers.append(meta.get("reviewer", col.name))
        return reviewers

    def delete_reviewer(self, reviewer_name: str):
        """리뷰어 컬렉션 삭제"""
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", reviewer_name).strip("_")[:63]
        if len(safe_name) < 3:
            safe_name = safe_name + "_collection"
        try:
            self.client.delete_collection(safe_name)
            logger.info(f"[{reviewer_name}] 컬렉션 삭제 완료")
        except Exception as e:
            logger.warning(f"컬렉션 삭제 실패: {e}")

    # ─────────────────────────────────────────
    # 내부 유틸리티
    # ─────────────────────────────────────────

    def _extract_text(self, path: Path) -> str:
        """파일에서 텍스트 추출"""
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            from src.utils.pdf_parser import extract_text_from_pdf
            return extract_text_from_pdf(path)
        elif suffix == ".docx":
            from src.utils.docx_parser import extract_text_from_docx
            return extract_text_from_docx(path)
        elif suffix in (".txt", ".md"):
            return path.read_text(encoding="utf-8")
        else:
            logger.warning(f"지원하지 않는 파일 형식: {suffix}")
            return path.read_text(encoding="utf-8", errors="ignore")

    def _chunk_text(
        self, text: str, chunk_size: int, overlap: int
    ) -> list[str]:
        """텍스트를 단어 기준으로 청킹"""
        words = text.split()
        if len(words) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            start = end - overlap
        return chunks
