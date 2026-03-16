"""사용자 직접 업로드 처리 — Layer 3 수동 수집"""
import shutil
from pathlib import Path

from src.config import settings
from src.acquisition.pdf_downloader import AcquisitionStatus, PaperAcquisitionResult
from src.utils.logging_config import logger


class ManualUploadHandler:
    """사용자가 직접 제공한 PDF를 논문 저장소에 등록"""

    def register_upload(
        self,
        paper_id: str,
        uploaded_path: Path,
        title: str = "",
        doi: str | None = None,
    ) -> PaperAcquisitionResult:
        """사용자가 직접 업로드한 PDF를 등록

        Args:
            paper_id: 논문 ID (S2 paperId 또는 사용자 지정 ID)
            uploaded_path: 업로드된 PDF 파일 경로
            title: 논문 제목 (선택)
            doi: DOI (선택)

        Returns:
            PaperAcquisitionResult: 등록 결과
        """
        if not uploaded_path.exists():
            logger.error(f"업로드 파일을 찾을 수 없습니다: {uploaded_path}")
            return PaperAcquisitionResult(
                paper_id=paper_id,
                title=title,
                doi=doi,
                status=AcquisitionStatus.FAILED,
                source="Manual Upload (file not found)",
            )

        dest = settings.papers_dir / paper_id / "paper.pdf"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(uploaded_path, dest)

        logger.info(f"PDF 등록 완료: {dest}")
        return PaperAcquisitionResult(
            paper_id=paper_id,
            title=title,
            doi=doi,
            status=AcquisitionStatus.UPLOADED,
            pdf_path=str(dest),
            source="Manual Upload",
        )

    def list_pending_uploads(self, paper_store) -> list[dict]:
        """업로드 대기 중인 논문 목록 조회"""
        return paper_store.get_papers_needing_upload()
