"""Unpaywall API 클라이언트 — DOI 기반 Open Access 논문 URL 탐색"""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from src.utils.logging_config import logger


UNPAYWALL_BASE = "https://api.unpaywall.org/v2"
UNPAYWALL_EMAIL = "ria-tool@example.com"


class UnpaywallClient:
    def __init__(self, email: str = UNPAYWALL_EMAIL):
        self.email = email
        self.client = httpx.Client(timeout=30.0, follow_redirects=True)

    def close(self):
        self.client.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def find_oa_pdf(self, doi: str) -> str | None:
        """DOI에 대한 OA PDF URL 반환, 없으면 None"""
        logger.info(f"Unpaywall OA 탐색: {doi}")
        try:
            resp = self.client.get(
                f"{UNPAYWALL_BASE}/{doi}",
                params={"email": self.email},
            )
            if resp.status_code == 200:
                data = resp.json()
                best_oa = data.get("best_oa_location")
                if best_oa and best_oa.get("url_for_pdf"):
                    url = best_oa["url_for_pdf"]
                    logger.info(f"Unpaywall OA 발견: {url}")
                    return url
        except Exception as e:
            logger.warning(f"Unpaywall 조회 실패: {e}")
        return None
