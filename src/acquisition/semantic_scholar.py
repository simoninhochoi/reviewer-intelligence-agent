"""Semantic Scholar API 클라이언트"""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from pydantic import BaseModel
from src.config import settings
from src.utils.logging_config import logger


S2_BASE = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS_PAPER = "paperId,title,abstract,year,venue,openAccessPdf,externalIds,citationCount,authors"
S2_FIELDS_AUTHOR = "authorId,name,affiliations,homepage,paperCount,citationCount,hIndex"


class S2Paper(BaseModel):
    paper_id: str
    title: str
    abstract: str | None = None
    year: int | None = None
    venue: str | None = None
    open_access_pdf_url: str | None = None
    doi: str | None = None
    citation_count: int = 0
    authors: list[dict] = []


class S2Author(BaseModel):
    author_id: str
    name: str
    affiliations: list[str] = []
    h_index: int | None = None
    paper_count: int = 0
    citation_count: int = 0


def _parse_paper(p: dict) -> S2Paper:
    """S2 API 응답을 S2Paper로 변환하는 공통 파서"""
    oa_url = None
    if p.get("openAccessPdf"):
        oa_url = p["openAccessPdf"].get("url")
    doi = None
    if p.get("externalIds"):
        doi = p["externalIds"].get("DOI")
    return S2Paper(
        paper_id=p["paperId"],
        title=p["title"],
        abstract=p.get("abstract"),
        year=p.get("year"),
        venue=p.get("venue"),
        open_access_pdf_url=oa_url,
        doi=doi,
        citation_count=p.get("citationCount", 0),
        authors=p.get("authors", []),
    )


class SemanticScholarClient:
    def __init__(self):
        headers = {}
        if settings.s2_api_key:
            headers["x-api-key"] = settings.s2_api_key
        self.client = httpx.Client(
            base_url=S2_BASE,
            headers=headers,
            timeout=30.0,
        )

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def search_author(self, name: str) -> list[S2Author]:
        """저자 이름으로 검색"""
        logger.info(f"S2 저자 검색: {name}")
        resp = self.client.get(
            "/author/search",
            params={"query": name, "fields": S2_FIELDS_AUTHOR, "limit": 5},
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        return [
            S2Author(
                author_id=a["authorId"],
                name=a["name"],
                affiliations=a.get("affiliations") or [],
                h_index=a.get("hIndex"),
                paper_count=a.get("paperCount", 0),
                citation_count=a.get("citationCount", 0),
            )
            for a in data
        ]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def get_author_papers(self, author_id: str, limit: int = 100) -> list[S2Paper]:
        """저자의 전체 논문 목록 가져오기"""
        logger.info(f"S2 저자 논문 수집: {author_id} (limit={limit})")
        resp = self.client.get(
            f"/author/{author_id}/papers",
            params={"fields": S2_FIELDS_PAPER, "limit": limit},
        )
        resp.raise_for_status()
        return [_parse_paper(p) for p in resp.json().get("data", [])]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def search_papers(self, query: str, limit: int = 20) -> list[S2Paper]:
        """키워드로 논문 검색"""
        logger.info(f"S2 논문 검색: {query} (limit={limit})")
        resp = self.client.get(
            "/paper/search",
            params={"query": query, "fields": S2_FIELDS_PAPER, "limit": limit},
        )
        resp.raise_for_status()
        return [_parse_paper(p) for p in resp.json().get("data", [])]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def get_paper(self, paper_id: str) -> S2Paper:
        """논문 ID로 단일 논문 조회 (S2 paperId 또는 DOI:xxx 형태)"""
        logger.info(f"S2 논문 조회: {paper_id}")
        resp = self.client.get(
            f"/paper/{paper_id}",
            params={"fields": S2_FIELDS_PAPER},
        )
        resp.raise_for_status()
        return _parse_paper(resp.json())
