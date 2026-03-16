"""서울대 도서관 프록시(libproxy.snu.ac.kr) 세션 관리"""
import httpx
from src.config import settings
from src.utils.logging_config import logger


class SNUProxySession:
    """서울대 프록시 인증 세션 관리

    패턴: https://libproxy.snu.ac.kr/link.n2s?url=https://doi.org/{doi}
    인증: mySNU 포털 또는 도서관 계정
    """

    LOGIN_URL = "https://libproxy.snu.ac.kr/login"

    def __init__(self):
        self.client = httpx.Client(timeout=60.0, follow_redirects=True)
        self._authenticated = False

    def close(self):
        self.client.close()

    @property
    def is_configured(self) -> bool:
        """프록시 자격증명이 설정되어 있는지 확인"""
        return bool(settings.snu_proxy_id and settings.snu_proxy_pw)

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    def authenticate(self) -> bool:
        """서울대 프록시 로그인"""
        if self._authenticated:
            return True
        if not self.is_configured:
            logger.warning("서울대 프록시 자격증명이 설정되지 않았습니다")
            return False

        logger.info("서울대 프록시 로그인 시도 중...")
        try:
            resp = self.client.post(
                self.LOGIN_URL,
                data={
                    "login": settings.snu_proxy_id,
                    "password": settings.snu_proxy_pw,
                },
            )
            if resp.status_code in (200, 302):
                self._authenticated = True
                logger.info("서울대 프록시 로그인 성공")
                return True
            else:
                logger.warning(f"서울대 프록시 로그인 실패: HTTP {resp.status_code}")
        except Exception as e:
            logger.warning(f"서울대 프록시 로그인 오류: {e}")
        return False

    def build_proxy_url(self, doi: str) -> str:
        """DOI에 대한 서울대 프록시 URL 생성"""
        return f"https://libproxy.snu.ac.kr/link.n2s?url=https://doi.org/{doi}"

    def download_pdf(self, url: str) -> bytes | None:
        """프록시를 통해 PDF 다운로드, 실패 시 None"""
        try:
            resp = self.client.get(url)
            if resp.status_code == 200 and b"%PDF" in resp.content[:10]:
                return resp.content
        except Exception as e:
            logger.warning(f"프록시 다운로드 실패: {e}")
        return None
