"""PDF 텍스트 추출 유틸리티 (PyMuPDF 기반)"""
from pathlib import Path

import pymupdf

from src.utils.logging_config import logger


def extract_text_from_pdf(pdf_path: Path | str) -> str:
    """PDF에서 전체 텍스트를 추출

    Args:
        pdf_path: PDF 파일 경로

    Returns:
        추출된 전체 텍스트 (페이지 구분자 포함)
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        logger.error(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
        return ""

    try:
        doc = pymupdf.open(str(pdf_path))
        pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                pages.append(text)
        doc.close()

        full_text = "\n\n--- PAGE BREAK ---\n\n".join(pages)
        logger.info(f"PDF 텍스트 추출 완료: {pdf_path.name} ({len(full_text)} chars, {len(pages)} pages)")
        return full_text
    except Exception as e:
        logger.error(f"PDF 텍스트 추출 실패 ({pdf_path}): {e}")
        return ""


def extract_text_by_pages(pdf_path: Path | str) -> list[str]:
    """PDF에서 페이지별 텍스트를 리스트로 추출"""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        return []

    try:
        doc = pymupdf.open(str(pdf_path))
        pages = [doc[i].get_text() for i in range(len(doc))]
        doc.close()
        return pages
    except Exception as e:
        logger.error(f"PDF 페이지 추출 실패 ({pdf_path}): {e}")
        return []
