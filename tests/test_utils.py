"""src/utils/ 테스트"""
from pathlib import Path

import pytest

from src.utils.reference_extractor import extract_references


class TestReferenceExtractor:
    def test_extracts_references(self, tmp_path):
        text = """Introduction

Some text here.

References
Abbott, Kenneth. 2000. International Relations and International Law. AJIL 94(3): 345-367.
Barnett, Michael. 2002. Eyewitness to a Genocide. Cornell University Press.
Finnemore, Martha. 1996. National Interests in International Society. Cornell UP.
"""
        path = tmp_path / "manuscript.txt"
        path.write_text(text, encoding="utf-8")
        refs = extract_references(str(path))
        assert len(refs) >= 2

    def test_no_references_section(self, tmp_path):
        text = "Introduction\n\nSome text without references."
        path = tmp_path / "no_refs.txt"
        path.write_text(text, encoding="utf-8")
        refs = extract_references(str(path))
        assert refs == []

    def test_bibliography_header(self, tmp_path):
        text = """Some text.

Bibliography
Smith, John. 2020. A Long Title That Is Definitely More Than Twenty Characters. Press.
Jones, Maria. 2019. Another Long Title Also More Than Twenty Characters. University Press.
"""
        path = tmp_path / "bib.txt"
        path.write_text(text, encoding="utf-8")
        refs = extract_references(str(path))
        assert len(refs) >= 1


class TestPdfParser:
    def test_import(self):
        from src.utils.pdf_parser import extract_text_from_pdf, extract_text_by_pages

        assert callable(extract_text_from_pdf)
        assert callable(extract_text_by_pages)


class TestDocxParser:
    def test_import(self):
        from src.utils.docx_parser import extract_text_from_docx, extract_sections_from_docx

        assert callable(extract_text_from_docx)
        assert callable(extract_sections_from_docx)
