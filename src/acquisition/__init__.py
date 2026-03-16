"""논문 수집 파이프라인 — 3-Layer 폴백 (OA → 서울대 프록시 → 수동 업로드)"""
from src.acquisition.semantic_scholar import (
    SemanticScholarClient,
    S2Paper,
    S2Author,
)
from src.acquisition.unpaywall import UnpaywallClient
from src.acquisition.snu_proxy import SNUProxySession
from src.acquisition.pdf_downloader import (
    PaperDownloader,
    PaperAcquisitionResult,
    AcquisitionStatus,
)
from src.acquisition.manual_upload import ManualUploadHandler
from src.acquisition.paper_store import PaperStore

__all__ = [
    "SemanticScholarClient",
    "S2Paper",
    "S2Author",
    "UnpaywallClient",
    "SNUProxySession",
    "PaperDownloader",
    "PaperAcquisitionResult",
    "AcquisitionStatus",
    "ManualUploadHandler",
    "PaperStore",
]
