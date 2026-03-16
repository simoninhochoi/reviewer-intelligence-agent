"""3-Layer 논문 전문 수집 파이프라인

Layer 1: Open Access (Semantic Scholar openAccessPdf + Unpaywall)
Layer 2: 서울대 프록시 (libproxy.snu.ac.kr)
Layer 3: 사용자 직접 업로드 (대기 상태로 표시)
"""
import time
from pathlib import Path
from enum import Enum

import httpx
from pydantic import BaseModel

from src.config import settings
from src.acquisition.semantic_scholar import S2Paper
from src.acquisition.unpaywall import UnpaywallClient
from src.acquisition.snu_proxy import SNUProxySession
from src.utils.logging_config import logger


class AcquisitionStatus(str, Enum):
    OA_FETCHED = "oa_fetched"           # OA로 자동 수집 완료
    PROXY_FETCHED = "proxy_fetched"     # 프록시로 수집 완료
    NEEDS_UPLOAD = "needs_upload"       # 사용자 업로드 대기
    UPLOADED = "uploaded"               # 사용자가 업로드 완료
    FAILED = "failed"                   # 수집 실패


class PaperAcquisitionResult(BaseModel):
    paper_id: str
    title: str
    doi: str | None
    status: AcquisitionStatus
    pdf_path: str | None = None
    source: str | None = None


class PaperDownloader:
    """3-Layer 폴백 전략으로 논문 PDF를 수집"""

    # 출판사별 다운로드 간격 (초) — 서울대 IP 차단 방지
    DOWNLOAD_DELAY = 5

    def __init__(self):
        self.http_client = httpx.Client(timeout=60.0, follow_redirects=True)
        self.unpaywall = UnpaywallClient()
        self.snu_proxy = SNUProxySession()

    def close(self):
        self.http_client.close()
        self.unpaywall.close()
        self.snu_proxy.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def acquire(self, paper: S2Paper) -> PaperAcquisitionResult:
        """논문 1편의 전문을 3-Layer로 수집 시도"""
        pdf_dir = settings.papers_dir / paper.paper_id
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = pdf_dir / "paper.pdf"

        # Layer 1a: S2 Open Access PDF
        if paper.open_access_pdf_url:
            logger.info(f"[Layer 1a] OA 다운로드 시도: {paper.title[:50]}...")
            if self._download_pdf(paper.open_access_pdf_url, pdf_path):
                return PaperAcquisitionResult(
                    paper_id=paper.paper_id,
                    title=paper.title,
                    doi=paper.doi,
                    status=AcquisitionStatus.OA_FETCHED,
                    pdf_path=str(pdf_path),
                    source=f"OA: {paper.open_access_pdf_url}",
                )

        # Layer 1b: Unpaywall
        if paper.doi:
            logger.info(f"[Layer 1b] Unpaywall 시도: {paper.doi}")
            unpaywall_url = self.unpaywall.find_oa_pdf(paper.doi)
            if unpaywall_url:
                if self._download_pdf(unpaywall_url, pdf_path):
                    return PaperAcquisitionResult(
                        paper_id=paper.paper_id,
                        title=paper.title,
                        doi=paper.doi,
                        status=AcquisitionStatus.OA_FETCHED,
                        pdf_path=str(pdf_path),
                        source=f"Unpaywall: {unpaywall_url}",
                    )

        # Layer 2: 서울대 프록시
        if self.snu_proxy.is_configured and paper.doi:
            logger.info(f"[Layer 2] 서울대 프록시 시도: {paper.doi}")
            if self.snu_proxy.authenticate():
                time.sleep(self.DOWNLOAD_DELAY)  # 출판사별 간격 준수
                proxy_url = self.snu_proxy.build_proxy_url(paper.doi)
                content = self.snu_proxy.download_pdf(proxy_url)
                if content:
                    pdf_path.write_bytes(content)
                    return PaperAcquisitionResult(
                        paper_id=paper.paper_id,
                        title=paper.title,
                        doi=paper.doi,
                        status=AcquisitionStatus.PROXY_FETCHED,
                        pdf_path=str(pdf_path),
                        source="SNU Proxy",
                    )

        # Layer 3: 사용자 업로드 대기
        logger.info(f"[Layer 3] 업로드 대기: {paper.title[:50]}...")
        return PaperAcquisitionResult(
            paper_id=paper.paper_id,
            title=paper.title,
            doi=paper.doi,
            status=AcquisitionStatus.NEEDS_UPLOAD,
        )

    def acquire_batch(self, papers: list[S2Paper]) -> list[PaperAcquisitionResult]:
        """여러 논문을 순차적으로 수집"""
        results = []
        for i, paper in enumerate(papers, 1):
            logger.info(f"논문 수집 [{i}/{len(papers)}]: {paper.title[:60]}...")
            result = self.acquire(paper)
            results.append(result)
            logger.info(f"  → {result.status.value}")
        return results

    def _download_pdf(self, url: str, path: Path) -> bool:
        """URL에서 PDF 다운로드"""
        try:
            resp = self.http_client.get(url)
            if resp.status_code == 200 and b"%PDF" in resp.content[:10]:
                path.write_bytes(resp.content)
                logger.info(f"PDF 다운로드 성공: {path}")
                return True
        except Exception as e:
            logger.warning(f"PDF 다운로드 실패 ({url}): {e}")
        return False
