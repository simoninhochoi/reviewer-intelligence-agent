"""원고에서 참고문헌 목록 추출 (간단 구현)

References/Bibliography/Works Cited 섹션을 찾아
개별 참고문헌 항목으로 분리합니다.
"""
from __future__ import annotations

import re
from pathlib import Path


def extract_references(path: str) -> list[str]:
    """원고 파일에서 References 섹션을 찾아 개별 항목으로 분리

    Args:
        path: 원고 파일 경로 (PDF, DOCX, 또는 텍스트)

    Returns:
        참고문헌 문자열 리스트
    """
    p = Path(path)

    if p.suffix.lower() == ".pdf":
        from src.utils.pdf_parser import extract_text_from_pdf

        text = extract_text_from_pdf(p)
    elif p.suffix.lower() == ".docx":
        from src.utils.docx_parser import extract_text_from_docx

        text = extract_text_from_docx(p)
    else:
        text = p.read_text(encoding="utf-8")

    # References 섹션 추출
    ref_match = re.search(
        r"(?:References|Bibliography|Works Cited)\s*\n(.*)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not ref_match:
        return []

    ref_text = ref_match.group(1)

    # 개별 참고문헌 항목 분리 (저자명 패턴으로)
    refs = re.split(r"\n(?=[A-Z][a-z]+,?\s)", ref_text)
    return [r.strip() for r in refs if len(r.strip()) > 20]
