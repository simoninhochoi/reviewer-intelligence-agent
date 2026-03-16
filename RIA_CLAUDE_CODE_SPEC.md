# Reviewer Intelligence Agent (RIA) — Claude Code 구현 가이드

> 까다로운 학술 리뷰어의 저서·논문을 학습하고, 리뷰를 시뮬레이션하여, 논문 수정 전략을 자동으로 수립하는 멀티 에이전트 시스템

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [기술 스택 & 프로젝트 구조](#2-기술-스택--프로젝트-구조)
3. [Phase 1: 프로젝트 셋업 & 핵심 인프라](#3-phase-1-프로젝트-셋업--핵심-인프라)
4. [Phase 2: 논문 수집 파이프라인 (Paper Acquisition)](#4-phase-2-논문-수집-파이프라인)
5. [Phase 3: 5개 에이전트 구현](#5-phase-3-5개-에이전트-구현)
6. [Phase 4: API 최적화 엔진 (Batch + Cache)](#6-phase-4-api-최적화-엔진)
7. [Phase 5: 프론트엔드 & CLI](#7-phase-5-프론트엔드--cli)
8. [Phase 6: 테스트 & 배포](#8-phase-6-테스트--배포)
9. [부록: 전체 비용 구조](#9-부록-비용-구조)

---

## 1. 프로젝트 개요

### 1.1 핵심 아이디어

학술 저널에 논문을 투고하면 익명의 리뷰어(peer reviewer)가 심사합니다. 하지만 리뷰 코멘트의 내용, 인용 요구, 이론적 관점 등에서 리뷰어의 정체를 추론할 수 있는 단서가 많습니다. 이 시스템은:

1. **예상 리뷰어의 학술적 프로필**을 LLM으로 자동 구축합니다
2. 그 프로필을 기반으로 **가상 리뷰를 시뮬레이션**합니다
3. 시뮬레이션 결과에 따라 **원고 수정 전략을 수립**하고 **텍스트 수정안을 생성**합니다

### 1.2 두 가지 운영 모드

- **투고 전 모드 (Pre-submission)**: 타겟 저널의 편집위원/예상 리뷰어를 식별하고, 투고 전에 원고를 강화
- **R&R 대응 모드 (Post-review)**: 실제 리뷰 수령 후, 리뷰어의 학술적 배경을 분석하여 효과적 대응

### 1.3 5개 전문 에이전트

| 에이전트 | 역할 | 모델 | 이유 |
|---------|------|------|------|
| 🔬 프로파일러 (Profiler) | 리뷰어 저작 수집·분석, 학술 프로필 구축 | Sonnet | 구조화된 정보 추출, 반복적 태스크 |
| 📚 갭 분석기 (Gap Analyzer) | 원고 참고문헌과 리뷰어 핵심 문헌 간 갭 분석 | Sonnet | 목록 비교, 교차 매칭 |
| 🎭 리뷰 시뮬레이터 (Simulator) | 리뷰어 관점에서 가상 리뷰 생성 | **Opus** | 깊은 학술적 비판, 페르소나 유지 |
| 🧭 수정 전략가 (Strategist) | 시뮬레이션 리뷰 기반 대응 전략 수립 | **Opus** | 이론적 맥락 이해, 복합 전략 수립 |
| ✍️ 작문 코치 (Writing Coach) | 실제 텍스트 수정안 생성 | **Opus** | 학술적 뉘앙스 유지, 창작 품질 |

---

## 2. 기술 스택 & 프로젝트 구조

### 2.1 기술 스택

```
LLM 백본:       Claude API (Sonnet 4.6 + Opus 4.6), 모델 라우팅
문헌 수집:       Semantic Scholar API, Unpaywall API, CrossRef API
지식 저장:       ChromaDB (벡터DB), SQLite (메타데이터)
문서 처리:       PyMuPDF (PDF 파싱), python-docx (DOCX 파싱), GROBID (인용 추출)
프론트엔드:      Streamlit (빠른 프로토타입) 또는 Next.js (프로덕션)
CLI:            Click (Python CLI)
```

### 2.2 프로젝트 디렉토리 구조

```
reviewer-intelligence-agent/
├── CLAUDE.md                          # 이 파일 — Claude Code 지시사항
├── pyproject.toml                     # Python 프로젝트 설정
├── .env.example                       # 환경변수 템플릿
│
├── src/
│   ├── __init__.py
│   │
│   ├── config.py                      # 전역 설정, 모델 라우팅 테이블
│   │
│   ├── acquisition/                   # Phase 2: 논문 수집 파이프라인
│   │   ├── __init__.py
│   │   ├── semantic_scholar.py        # S2 API 클라이언트
│   │   ├── unpaywall.py              # Unpaywall OA 탐색
│   │   ├── snu_proxy.py              # 서울대 프록시 연동
│   │   ├── pdf_downloader.py         # 3-Layer 다운로드 엔진
│   │   ├── manual_upload.py          # 사용자 업로드 처리
│   │   └── paper_store.py            # 논문 메타데이터 + 전문 저장
│   │
│   ├── agents/                        # Phase 3: 5개 에이전트
│   │   ├── __init__.py
│   │   ├── base_agent.py             # 에이전트 기본 클래스
│   │   ├── profiler.py               # 🔬 리뷰어 프로파일러
│   │   ├── gap_analyzer.py           # 📚 문헌 갭 분석기
│   │   ├── simulator.py              # 🎭 리뷰 시뮬레이터
│   │   ├── strategist.py             # 🧭 수정 전략가
│   │   └── writer.py                 # ✍️ 학술 작문 코치
│   │
│   ├── optimization/                  # Phase 4: API 최적화
│   │   ├── __init__.py
│   │   ├── model_router.py           # Sonnet/Opus 자동 라우팅
│   │   ├── batch_processor.py        # Batch API 매니저
│   │   ├── cache_manager.py          # Prompt Caching 전략
│   │   └── cost_tracker.py           # 비용 추적·리포팅
│   │
│   ├── vectordb/                      # 벡터DB 관리
│   │   ├── __init__.py
│   │   ├── embeddings.py             # 임베딩 생성 (Voyage AI 또는 S2 SPECTER2)
│   │   ├── chroma_store.py           # ChromaDB 저장·검색
│   │   └── retriever.py              # RAG 검색기
│   │
│   ├── pipeline.py                    # 전체 파이프라인 오케스트레이터
│   │
│   └── utils/
│       ├── __init__.py
│       ├── pdf_parser.py             # PDF 텍스트 추출
│       ├── docx_parser.py            # DOCX 파싱
│       ├── reference_extractor.py    # 참고문헌 목록 추출
│       └── logging_config.py         # 로깅 설정
│
├── ui/                                # Phase 5: 프론트엔드
│   ├── streamlit_app.py              # Streamlit 프로토타입
│   └── components/
│       ├── reviewer_input.py
│       ├── paper_manager.py
│       ├── review_display.py
│       └── revision_editor.py
│
├── cli/                               # Phase 5: CLI
│   └── main.py                       # Click 기반 CLI
│
├── tests/
│   ├── test_acquisition.py
│   ├── test_agents.py
│   ├── test_optimization.py
│   └── test_pipeline.py
│
├── data/                              # 로컬 데이터 (gitignore)
│   ├── papers/                       # 수집된 논문 PDF
│   ├── profiles/                     # 리뷰어 프로필 JSON
│   ├── chroma_db/                    # 벡터DB 파일
│   └── outputs/                      # 생성된 결과물
│
└── prompts/                           # 에이전트 프롬프트 템플릿
    ├── profiler_system.md
    ├── gap_analyzer_system.md
    ├── simulator_system.md
    ├── strategist_system.md
    └── writer_system.md
```

---

## 3. Phase 1: 프로젝트 셋업 & 핵심 인프라

### 3.1 프로젝트 초기화

```bash
# 프로젝트 생성
mkdir reviewer-intelligence-agent && cd reviewer-intelligence-agent
```

### 3.2 pyproject.toml

```toml
[project]
name = "reviewer-intelligence-agent"
version = "0.1.0"
description = "Multi-agent system for anticipating and responding to academic peer reviewers"
requires-python = ">=3.11"
dependencies = [
    "anthropic>=0.42.0",
    "httpx>=0.27.0",
    "python-dotenv>=1.0.0",
    "chromadb>=0.5.0",
    "pymupdf>=1.24.0",
    "python-docx>=1.1.0",
    "click>=8.1.0",
    "streamlit>=1.38.0",
    "rich>=13.7.0",
    "pydantic>=2.8.0",
    "tenacity>=8.2.0",
    "sqlite-utils>=3.36",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "ruff>=0.6"]

[project.scripts]
ria = "cli.main:cli"
```

### 3.3 환경변수 (.env.example)

```env
# Claude API
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Semantic Scholar (선택, 없으면 공개 API 사용)
S2_API_KEY=

# 서울대 프록시 (선택)
SNU_PROXY_ID=
SNU_PROXY_PW=
SNU_AUTH_METHOD=portal  # 'portal' 또는 'library'

# 벡터DB
CHROMA_PERSIST_DIR=./data/chroma_db

# 비용 추적
COST_LOG_PATH=./data/cost_log.jsonl
```

### 3.4 전역 설정 (src/config.py)

```python
"""전역 설정 및 모델 라우팅 테이블"""
from enum import Enum
from pathlib import Path
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()


class ModelTier(str, Enum):
    SONNET = "claude-sonnet-4-6"
    OPUS = "claude-opus-4-6"


class AgentType(str, Enum):
    PROFILER = "profiler"
    GAP_ANALYZER = "gap_analyzer"
    SIMULATOR = "simulator"
    STRATEGIST = "strategist"
    WRITER = "writer"


# ═══════════════════════════════════════════════════
# 모델 라우팅: 수집·구조화는 Sonnet, 분석·작성은 Opus
# ═══════════════════════════════════════════════════

AGENT_MODEL_MAP: dict[AgentType, ModelTier] = {
    AgentType.PROFILER:     ModelTier.SONNET,    # 수집·구조화
    AgentType.GAP_ANALYZER: ModelTier.SONNET,    # 문헌 비교
    AgentType.SIMULATOR:    ModelTier.OPUS,      # 깊은 분석
    AgentType.STRATEGIST:   ModelTier.OPUS,      # 전략 추론
    AgentType.WRITER:       ModelTier.OPUS,      # 학술 작문
}

# 모델별 가격 (USD per 1M tokens)
MODEL_PRICING = {
    ModelTier.SONNET: {"input": 3.0, "output": 15.0},
    ModelTier.OPUS:   {"input": 5.0, "output": 25.0},
}

# Batch/Cache 할인율
BATCH_DISCOUNT = 0.5          # 50% 할인
CACHE_WRITE_MULTIPLIER = 1.25  # 첫 캐시 쓰기
CACHE_READ_MULTIPLIER = 0.1    # 캐시 히트 시 90% 절감


class Settings(BaseModel):
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    s2_api_key: str | None = os.getenv("S2_API_KEY")
    snu_proxy_id: str | None = os.getenv("SNU_PROXY_ID")
    snu_proxy_pw: str | None = os.getenv("SNU_PROXY_PW")
    snu_auth_method: str = os.getenv("SNU_AUTH_METHOD", "portal")
    chroma_persist_dir: Path = Path(os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db"))
    cost_log_path: Path = Path(os.getenv("COST_LOG_PATH", "./data/cost_log.jsonl"))
    papers_dir: Path = Path("./data/papers")
    profiles_dir: Path = Path("./data/profiles")
    outputs_dir: Path = Path("./data/outputs")

    def ensure_dirs(self):
        for d in [self.chroma_persist_dir, self.papers_dir, self.profiles_dir, self.outputs_dir]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
```

---

## 4. Phase 2: 논문 수집 파이프라인

### 4.1 Semantic Scholar 클라이언트 (src/acquisition/semantic_scholar.py)

API 키 없이도 사용 가능하지만, 키가 있으면 rate limit이 향상됩니다 (100req/5min → 1req/sec).

```python
"""Semantic Scholar API 클라이언트"""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from pydantic import BaseModel
from src.config import settings


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


class SemanticScholarClient:
    def __init__(self):
        headers = {}
        if settings.s2_api_key:
            headers["x-api-key"] = settings.s2_api_key
        self.client = httpx.Client(
            base_url=S2_BASE,
            headers=headers,
            timeout=30.0
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def search_author(self, name: str) -> list[S2Author]:
        """저자 이름으로 검색"""
        resp = self.client.get(
            "/author/search",
            params={"query": name, "fields": S2_FIELDS_AUTHOR, "limit": 5}
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        return [S2Author(
            author_id=a["authorId"],
            name=a["name"],
            affiliations=a.get("affiliations") or [],
            h_index=a.get("hIndex"),
            paper_count=a.get("paperCount", 0),
            citation_count=a.get("citationCount", 0),
        ) for a in data]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def get_author_papers(self, author_id: str, limit: int = 100) -> list[S2Paper]:
        """저자의 전체 논문 목록 가져오기"""
        resp = self.client.get(
            f"/author/{author_id}/papers",
            params={"fields": S2_FIELDS_PAPER, "limit": limit}
        )
        resp.raise_for_status()
        papers = []
        for p in resp.json().get("data", []):
            oa_url = None
            if p.get("openAccessPdf"):
                oa_url = p["openAccessPdf"].get("url")
            doi = None
            if p.get("externalIds"):
                doi = p["externalIds"].get("DOI")
            papers.append(S2Paper(
                paper_id=p["paperId"],
                title=p["title"],
                abstract=p.get("abstract"),
                year=p.get("year"),
                venue=p.get("venue"),
                open_access_pdf_url=oa_url,
                doi=doi,
                citation_count=p.get("citationCount", 0),
                authors=p.get("authors", []),
            ))
        return papers

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def search_papers(self, query: str, limit: int = 20) -> list[S2Paper]:
        """키워드로 논문 검색"""
        resp = self.client.get(
            "/paper/search",
            params={"query": query, "fields": S2_FIELDS_PAPER, "limit": limit}
        )
        resp.raise_for_status()
        # S2Paper 변환은 위와 동일한 패턴
        papers = []
        for p in resp.json().get("data", []):
            oa_url = None
            if p.get("openAccessPdf"):
                oa_url = p["openAccessPdf"].get("url")
            doi = None
            if p.get("externalIds"):
                doi = p["externalIds"].get("DOI")
            papers.append(S2Paper(
                paper_id=p["paperId"],
                title=p["title"],
                abstract=p.get("abstract"),
                year=p.get("year"),
                venue=p.get("venue"),
                open_access_pdf_url=oa_url,
                doi=doi,
                citation_count=p.get("citationCount", 0),
                authors=p.get("authors", []),
            ))
        return papers
```

### 4.2 3-Layer 논문 다운로드 엔진 (src/acquisition/pdf_downloader.py)

```python
"""3-Layer 논문 전문 수집 파이프라인
Layer 1: Open Access (Semantic Scholar openAccessPdf + Unpaywall)
Layer 2: 서울대 프록시 (libproxy.snu.ac.kr)
Layer 3: 사용자 직접 업로드 (대기 상태로 표시)
"""
import httpx
import time
from pathlib import Path
from enum import Enum
from pydantic import BaseModel
from src.config import settings
from src.acquisition.semantic_scholar import S2Paper


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
        self.client = httpx.Client(timeout=60.0, follow_redirects=True)
        self.snu_session = None

    async def acquire(self, paper: S2Paper) -> PaperAcquisitionResult:
        """논문 1편의 전문을 3-Layer로 수집 시도"""
        pdf_dir = settings.papers_dir / paper.paper_id
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = pdf_dir / "paper.pdf"

        # Layer 1: Open Access
        if paper.open_access_pdf_url:
            if self._download_pdf(paper.open_access_pdf_url, pdf_path):
                return PaperAcquisitionResult(
                    paper_id=paper.paper_id, title=paper.title, doi=paper.doi,
                    status=AcquisitionStatus.OA_FETCHED,
                    pdf_path=str(pdf_path), source=f"OA: {paper.open_access_pdf_url}"
                )

        # Layer 1b: Unpaywall
        if paper.doi:
            unpaywall_url = self._check_unpaywall(paper.doi)
            if unpaywall_url:
                if self._download_pdf(unpaywall_url, pdf_path):
                    return PaperAcquisitionResult(
                        paper_id=paper.paper_id, title=paper.title, doi=paper.doi,
                        status=AcquisitionStatus.OA_FETCHED,
                        pdf_path=str(pdf_path), source=f"Unpaywall: {unpaywall_url}"
                    )

        # Layer 2: 서울대 프록시
        if settings.snu_proxy_id and paper.doi:
            proxy_url = self._build_snu_proxy_url(paper.doi)
            if self._ensure_snu_session():
                time.sleep(self.DOWNLOAD_DELAY)  # 출판사별 간격 준수
                if self._download_via_proxy(proxy_url, pdf_path):
                    return PaperAcquisitionResult(
                        paper_id=paper.paper_id, title=paper.title, doi=paper.doi,
                        status=AcquisitionStatus.PROXY_FETCHED,
                        pdf_path=str(pdf_path), source="SNU Proxy"
                    )

        # Layer 3: 사용자 업로드 대기
        return PaperAcquisitionResult(
            paper_id=paper.paper_id, title=paper.title, doi=paper.doi,
            status=AcquisitionStatus.NEEDS_UPLOAD
        )

    def _download_pdf(self, url: str, path: Path) -> bool:
        """URL에서 PDF 다운로드"""
        try:
            resp = self.client.get(url)
            if resp.status_code == 200 and b"%PDF" in resp.content[:10]:
                path.write_bytes(resp.content)
                return True
        except Exception:
            pass
        return False

    def _check_unpaywall(self, doi: str) -> str | None:
        """Unpaywall API로 OA 버전 확인"""
        try:
            resp = self.client.get(
                f"https://api.unpaywall.org/v2/{doi}",
                params={"email": "ria-tool@example.com"}
            )
            if resp.status_code == 200:
                data = resp.json()
                best_oa = data.get("best_oa_location")
                if best_oa and best_oa.get("url_for_pdf"):
                    return best_oa["url_for_pdf"]
        except Exception:
            pass
        return None

    def _build_snu_proxy_url(self, doi: str) -> str:
        """서울대 프록시 URL 생성
        패턴: https://libproxy.snu.ac.kr/link.n2s?url=https://doi.org/{doi}
        """
        return f"https://libproxy.snu.ac.kr/link.n2s?url=https://doi.org/{doi}"

    def _ensure_snu_session(self) -> bool:
        """서울대 프록시 세션 인증 (mySNU 포털 또는 도서관 계정)"""
        if self.snu_session:
            return True
        try:
            # 실제 구현 시 서울대 로그인 플로우에 맞게 수정 필요
            # 현재는 세션 쿠키 기반 인증 스켈레톤
            login_url = "https://libproxy.snu.ac.kr/login"
            resp = self.client.post(login_url, data={
                "login": settings.snu_proxy_id,
                "password": settings.snu_proxy_pw,
            })
            if resp.status_code in (200, 302):
                self.snu_session = True
                return True
        except Exception:
            pass
        return False

    def _download_via_proxy(self, proxy_url: str, path: Path) -> bool:
        """서울대 프록시를 통해 PDF 다운로드"""
        return self._download_pdf(proxy_url, path)

    def register_upload(self, paper_id: str, uploaded_path: Path) -> PaperAcquisitionResult:
        """사용자가 직접 업로드한 PDF를 등록"""
        dest = settings.papers_dir / paper_id / "paper.pdf"
        dest.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(uploaded_path, dest)
        return PaperAcquisitionResult(
            paper_id=paper_id, title="",
            doi=None, status=AcquisitionStatus.UPLOADED,
            pdf_path=str(dest), source="Manual Upload"
        )
```

### 4.3 논문 저장소 (src/acquisition/paper_store.py)

```python
"""논문 메타데이터 + 전문 텍스트를 SQLite에 저장"""
import sqlite_utils
from pathlib import Path
from src.config import settings


class PaperStore:
    def __init__(self, db_path: Path | None = None):
        self.db = sqlite_utils.Database(db_path or settings.papers_dir / "papers.db")
        self._init_tables()

    def _init_tables(self):
        if "papers" not in self.db.table_names():
            self.db["papers"].create({
                "paper_id": str,
                "title": str,
                "abstract": str,
                "year": int,
                "venue": str,
                "doi": str,
                "citation_count": int,
                "full_text": str,         # 추출된 전문
                "pdf_path": str,
                "acquisition_status": str,
                "reviewer_id": str,       # 어떤 리뷰어의 논문인지
            }, pk="paper_id", not_null={"title"}, if_not_exists=True)

        if "reviewers" not in self.db.table_names():
            self.db["reviewers"].create({
                "reviewer_id": str,
                "name": str,
                "s2_author_id": str,
                "affiliations": str,      # JSON
                "h_index": int,
                "profile_json": str,      # 생성된 프로필 전체
            }, pk="reviewer_id", if_not_exists=True)

    def upsert_paper(self, paper_data: dict):
        self.db["papers"].upsert(paper_data, pk="paper_id")

    def upsert_reviewer(self, reviewer_data: dict):
        self.db["reviewers"].upsert(reviewer_data, pk="reviewer_id")

    def get_reviewer_papers(self, reviewer_id: str) -> list[dict]:
        return list(self.db["papers"].rows_where("reviewer_id = ?", [reviewer_id]))

    def get_papers_needing_upload(self) -> list[dict]:
        return list(self.db["papers"].rows_where("acquisition_status = ?", ["needs_upload"]))
```

---

## 5. Phase 3: 5개 에이전트 구현

### 5.1 에이전트 기본 클래스 (src/agents/base_agent.py)

```python
"""모든 에이전트의 기본 클래스 — 모델 라우팅, 캐싱, 비용 추적 통합"""
import anthropic
from abc import ABC, abstractmethod
from src.config import settings, AGENT_MODEL_MAP, AgentType, ModelTier


class BaseAgent(ABC):
    """에이전트 기본 클래스

    - 모델 자동 라우팅 (config의 AGENT_MODEL_MAP에 따라)
    - Prompt Caching 자동 적용 (cached_context 제공 시)
    - 비용 추적 통합
    """

    agent_type: AgentType

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = AGENT_MODEL_MAP[self.agent_type].value

    def call(
        self,
        user_message: str,
        cached_context: str | None = None,
        system_prompt: str | None = None,
        max_tokens: int = 4000,
    ) -> str:
        """에이전트 호출 — 캐싱 자동 적용

        Args:
            user_message: 사용자/파이프라인 메시지
            cached_context: 캐싱할 대규모 컨텍스트 (리뷰어 프로필, 원고 전문 등)
            system_prompt: 에이전트 시스템 프롬프트 (cached_context 뒤에 붙음)
            max_tokens: 최대 출력 토큰
        """
        # 시스템 프롬프트 구성 (캐싱 적용)
        system_blocks = []

        if cached_context:
            # 대규모 컨텍스트를 캐시 블록으로 설정
            # 첫 호출: 1.25x (cache write)
            # 이후 호출: 0.1x (cache read) → 90% 절감
            system_blocks.append({
                "type": "text",
                "text": cached_context,
                "cache_control": {"type": "ephemeral"}
            })

        if system_prompt:
            system_blocks.append({
                "type": "text",
                "text": system_prompt,
            })

        # 시스템 프롬프트가 없으면 기본 프롬프트 로드
        if not system_blocks:
            system_blocks = self._load_default_system_prompt()

        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_blocks,
            messages=[{"role": "user", "content": user_message}],
        )

        # 비용 추적
        self._track_cost(response.usage)

        return response.content[0].text

    def _load_default_system_prompt(self) -> list[dict]:
        """prompts/ 디렉토리에서 기본 시스템 프롬프트 로드"""
        prompt_path = Path(f"prompts/{self.agent_type.value}_system.md")
        if prompt_path.exists():
            return [{"type": "text", "text": prompt_path.read_text()}]
        return [{"type": "text", "text": f"You are the {self.agent_type.value} agent."}]

    def _track_cost(self, usage):
        """API 사용량을 비용 로그에 기록"""
        from src.optimization.cost_tracker import CostTracker
        CostTracker.log(
            agent=self.agent_type.value,
            model=self.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0),
            cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0),
        )

    @abstractmethod
    def run(self, **kwargs) -> dict:
        """각 에이전트의 메인 실행 로직"""
        ...
```

### 5.2 리뷰어 프로파일러 (src/agents/profiler.py)

```python
"""🔬 리뷰어 프로파일러 — Sonnet으로 실행"""
from src.agents.base_agent import BaseAgent
from src.config import AgentType


class ProfilerAgent(BaseAgent):
    agent_type = AgentType.PROFILER

    def run(self, reviewer_name: str, papers_data: list[dict]) -> dict:
        """리뷰어의 학술 프로필을 구축

        Args:
            reviewer_name: 리뷰어 이름
            papers_data: S2에서 수집한 논문 메타데이터 + 초록 목록

        Returns:
            구조화된 리뷰어 프로필 (이론 체계, 방법론, 핵심 개념 등)
        """
        # 논문 목록을 텍스트로 변환
        papers_text = "\n\n".join([
            f"### {p['title']} ({p.get('year', 'N/A')})\n"
            f"Venue: {p.get('venue', 'N/A')}\n"
            f"Citations: {p.get('citation_count', 0)}\n"
            f"Abstract: {p.get('abstract', 'N/A')}"
            for p in papers_data
        ])

        system_prompt = f"""You are an expert academic profiler. Analyze the publication record
of {reviewer_name} and produce a structured academic profile.

Your profile must include:
1. CORE THEORETICAL FRAMEWORKS: What theories does this scholar champion or develop?
2. METHODOLOGICAL STANCE: Qualitative/quantitative preferences, case study vs. comparative, etc.
3. KEY CONCEPTS: Recurring concepts, terminology, and analytical categories
4. INTELLECTUAL NETWORK: Scholars they frequently cite or co-author with
5. CRITICAL PATTERNS: What do they typically criticize in others' work?
6. EVOLUTION: How has their research focus changed over time?
7. LIKELY REVIEW CONCERNS: Based on their academic stance, what would they look for when reviewing a paper?

Output as structured JSON."""

        result = self.call(
            user_message=f"Analyze the following publication record:\n\n{papers_text}",
            system_prompt=system_prompt,
            max_tokens=6000,
        )

        return {"reviewer_name": reviewer_name, "profile": result}
```

### 5.3 리뷰 시뮬레이터 (src/agents/simulator.py)

```python
"""🎭 리뷰 시뮬레이터 — Opus로 실행, 리뷰어 프로필을 캐싱"""
from src.agents.base_agent import BaseAgent
from src.config import AgentType


class SimulatorAgent(BaseAgent):
    agent_type = AgentType.SIMULATOR

    def run(
        self,
        reviewer_profile: str,
        manuscript_text: str,
        section: str | None = None,
    ) -> dict:
        """리뷰어 관점에서 원고를 심사하고 상세 리뷰 코멘트 생성

        Args:
            reviewer_profile: 프로파일러가 생성한 리뷰어 프로필 JSON
            manuscript_text: 원고 전문 또는 특정 섹션
            section: 특정 섹션명 (None이면 전체 리뷰)

        Note:
            reviewer_profile은 cache_control로 캐싱됩니다.
            같은 리뷰어에 대해 여러 섹션을 순차 리뷰할 때
            첫 호출만 cache write(1.25x), 이후는 cache read(0.1x)
        """
        persona_prompt = f"""You are an anonymous peer reviewer for a top international relations journal.

YOUR ACADEMIC PROFILE:
{reviewer_profile}

REVIEW INSTRUCTIONS:
- Review the manuscript as if you were this specific scholar
- Base your criticism on YOUR theoretical frameworks and methodological preferences
- Point out missing citations, especially YOUR OWN works that are relevant
- Identify theoretical weaknesses from YOUR perspective
- Distinguish between Major Revision and Minor Revision issues
- Be specific: cite exact passages and explain why they are problematic

FORMAT:
## Overall Assessment
[2-3 paragraphs]

## Major Issues
1. [Issue title]
   - Problem: [specific critique]
   - Missing literature: [what should be cited]
   - Suggestion: [how to fix]

## Minor Issues
1. [Issue]
   - Suggestion: [fix]

## Missing References
- [Author (Year)] — reason this should be cited
"""

        target = f"Section: {section}" if section else "Full manuscript"
        user_msg = f"Review the following ({target}):\n\n{manuscript_text}"

        # reviewer_profile이 cached_context로 전달되어 자동 캐싱
        result = self.call(
            user_message=user_msg,
            cached_context=persona_prompt,  # 이 블록이 캐싱됨!
            max_tokens=6000,
        )

        return {"section": section or "full", "review": result}
```

### 5.4 수정 전략가 (src/agents/strategist.py)

```python
"""🧭 수정 전략가 — Opus로 실행"""
from src.agents.base_agent import BaseAgent
from src.config import AgentType


class StrategistAgent(BaseAgent):
    agent_type = AgentType.STRATEGIST

    def run(
        self,
        reviewer_profile: str,
        simulated_review: str,
        manuscript_text: str,
        author_intent: str = "",
    ) -> dict:
        """리뷰 코멘트에 대한 대응 전략 + Response Letter 초안 생성

        Args:
            reviewer_profile: 리뷰어 프로필 (캐싱됨)
            simulated_review: 시뮬레이터가 생성한 가상 리뷰
            manuscript_text: 원고 전문
            author_intent: 저자의 의도/양보 불가 사항
        """
        # 리뷰어 프로필 + 시뮬레이션 결과를 합쳐서 캐싱
        cached = f"""REVIEWER PROFILE:
{reviewer_profile}

SIMULATED REVIEW:
{simulated_review}"""

        system = """You are an expert academic writing strategist.
For each review comment, create a revision strategy that:
1. Respects the reviewer's theoretical framework while defending the author's contribution
2. Identifies the minimum changes needed to satisfy the reviewer
3. Suggests specific textual modifications with before/after examples
4. Proposes additional citations that bridge the gap between reviewer and author

Also draft a Response Letter that:
- Addresses each comment point by point
- Uses diplomatic, respectful academic language
- Clearly distinguishes between "changes made" and "respectful disagreement"
- References specific page/section numbers

FORMAT:
## Revision Strategy
### Comment 1: [title]
- Reviewer's concern: [summary]
- Strategy: [accept/partially accept/defend]
- Specific changes: [what to modify]
- Added citations: [what to cite]
- Response letter draft: [paragraph]

## Response Letter Draft
[Complete response letter]"""

        user_msg = f"""Manuscript:\n{manuscript_text}

Author's non-negotiable positions:\n{author_intent or 'None specified'}

Create a comprehensive revision strategy."""

        result = self.call(
            user_message=user_msg,
            cached_context=cached,
            system_prompt=system,
            max_tokens=8000,
        )

        return {"strategy": result}
```

### 5.5 갭 분석기 (src/agents/gap_analyzer.py)

```python
"""📚 문헌 갭 분석기 — Sonnet으로 실행"""
from src.agents.base_agent import BaseAgent
from src.config import AgentType


class GapAnalyzerAgent(BaseAgent):
    agent_type = AgentType.GAP_ANALYZER

    def run(
        self,
        reviewer_profile: str,
        reviewer_papers: list[dict],
        manuscript_references: list[str],
    ) -> dict:
        """원고 참고문헌과 리뷰어 핵심 저작 간 갭 분석

        Args:
            reviewer_profile: 리뷰어 프로필 (캐싱됨)
            reviewer_papers: 리뷰어의 출판물 목록
            manuscript_references: 원고의 참고문헌 목록
        """
        reviewer_works = "\n".join([
            f"- {p['title']} ({p.get('year', 'N/A')}) [citations: {p.get('citation_count', 0)}]"
            for p in reviewer_papers
        ])

        manuscript_refs = "\n".join([f"- {r}" for r in manuscript_references])

        system = """You are an expert in academic citation analysis.
Compare the reviewer's publication record with the manuscript's bibliography.

Identify:
1. CRITICAL GAPS: Reviewer's key works that MUST be cited (high citation, core theory)
2. RECOMMENDED ADDITIONS: Works that would strengthen the argument
3. CITATION CONTEXT: WHERE and HOW each missing work should be cited
4. CONNECTION POINTS: How reviewer's theory connects to the manuscript's argument

Output as structured JSON with priority ranking."""

        result = self.call(
            user_message=f"""REVIEWER'S PUBLICATIONS:
{reviewer_works}

MANUSCRIPT'S CURRENT REFERENCES:
{manuscript_refs}

Analyze the gaps.""",
            cached_context=reviewer_profile,
            system_prompt=system,
            max_tokens=4000,
        )

        return {"gap_analysis": result}
```

### 5.6 학술 작문 코치 (src/agents/writer.py)

```python
"""✍️ 학술 작문 코치 — Opus로 실행"""
from src.agents.base_agent import BaseAgent
from src.config import AgentType


class WriterAgent(BaseAgent):
    agent_type = AgentType.WRITER

    def run(
        self,
        reviewer_profile: str,
        revision_strategy: str,
        original_section: str,
        comment: str,
    ) -> dict:
        """리뷰어 피드백에 대응하여 실제 텍스트 수정안 생성

        Args:
            reviewer_profile: 리뷰어 프로필 (캐싱됨)
            revision_strategy: 전략가가 수립한 수정 방침
            original_section: 수정 대상 원본 텍스트
            comment: 해당 리뷰 코멘트
        """
        cached = f"""REVIEWER PROFILE:
{reviewer_profile}

REVISION STRATEGY:
{revision_strategy}"""

        system = """You are an expert academic writing coach specializing in international relations.

Revise the given text section following the strategy. Your revision must:
1. Maintain the author's voice and argument while addressing the reviewer's concern
2. Use appropriate academic hedging and boosting strategies
3. Integrate new citations naturally
4. Keep the theoretical sophistication expected by the reviewer
5. Mark all changes with [ADDED], [MODIFIED], [DELETED] annotations

Output format:
## Revised Text
[The revised section with annotations]

## Change Summary
- [List of changes with rationale]

## Reviewer Satisfaction Note
[Why this revision addresses the reviewer's concern]"""

        result = self.call(
            user_message=f"""REVIEWER COMMENT:
{comment}

ORIGINAL TEXT:
{original_section}

Revise this section.""",
            cached_context=cached,
            system_prompt=system,
            max_tokens=6000,
        )

        return {"revision": result}
```

---

## 6. Phase 4: API 최적화 엔진

### 6.1 Batch 프로세서 (src/optimization/batch_processor.py)

```python
"""Batch API 매니저 — 입출력 토큰 50% 할인, 비동기 처리"""
import anthropic
import time
from src.config import settings, AGENT_MODEL_MAP, AgentType


class BatchProcessor:
    """여러 태스크를 Batch API로 묶어 처리
    
    사용 시나리오:
    - 논문 20편 일괄 파싱 (프로파일러)
    - 섹션별 리뷰 시뮬레이션 5건 (시뮬레이터)
    - 코멘트별 수정안 생성 (작문코치)
    """

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def create_batch(
        self,
        agent_type: AgentType,
        tasks: list[dict],
        cached_system: str | None = None,
        max_tokens: int = 2000,
    ) -> str:
        """Batch 생성

        Args:
            agent_type: 에이전트 타입 (모델 자동 결정)
            tasks: [{"id": "task-0", "content": "..."}]
            cached_system: 캐싱할 시스템 프롬프트 (Batch 내에서도 캐싱 적용!)
            max_tokens: 태스크당 최대 출력 토큰

        Returns:
            batch_id (결과 조회용)
        """
        model = AGENT_MODEL_MAP[agent_type].value

        requests = []
        for task in tasks:
            req = {
                "custom_id": task["id"],
                "params": {
                    "model": model,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": task["content"]}],
                },
            }
            # Batch 내에서도 Prompt Caching 동시 적용!
            if cached_system:
                req["params"]["system"] = [{
                    "type": "text",
                    "text": cached_system,
                    "cache_control": {"type": "ephemeral"},
                }]
            requests.append(req)

        batch = self.client.messages.batches.create(requests=requests)
        return batch.id

    def wait_for_results(self, batch_id: str, poll_interval: int = 30) -> list[dict]:
        """Batch 완료까지 대기 후 결과 반환

        Args:
            batch_id: create_batch에서 반환된 ID
            poll_interval: 폴링 간격 (초)

        Returns:
            [{"id": "task-0", "text": "결과 텍스트"}, ...]
        """
        while True:
            batch = self.client.messages.batches.retrieve(batch_id)
            if batch.processing_status == "ended":
                break
            time.sleep(poll_interval)

        results = []
        for result in self.client.messages.batches.results(batch_id):
            if result.result.type == "succeeded":
                results.append({
                    "id": result.custom_id,
                    "text": result.result.message.content[0].text,
                    "usage": {
                        "input_tokens": result.result.message.usage.input_tokens,
                        "output_tokens": result.result.message.usage.output_tokens,
                    }
                })
            else:
                results.append({
                    "id": result.custom_id,
                    "error": str(result.result.error),
                })
        return results
```

### 6.2 비용 추적기 (src/optimization/cost_tracker.py)

```python
"""API 비용 실시간 추적 및 리포팅"""
import json
from datetime import datetime
from pathlib import Path
from src.config import settings, MODEL_PRICING, BATCH_DISCOUNT, CACHE_READ_MULTIPLIER, CACHE_WRITE_MULTIPLIER


class CostTracker:
    @staticmethod
    def log(
        agent: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_creation_tokens: int = 0,
        is_batch: bool = False,
    ):
        """비용 로그 기록"""
        pricing = MODEL_PRICING.get(model, {"input": 5.0, "output": 25.0})

        # 비용 계산
        regular_input = (input_tokens - cache_read_tokens - cache_creation_tokens) / 1_000_000
        cache_read = cache_read_tokens / 1_000_000
        cache_write = cache_creation_tokens / 1_000_000
        output = output_tokens / 1_000_000

        cost = (
            regular_input * pricing["input"]
            + cache_read * pricing["input"] * CACHE_READ_MULTIPLIER
            + cache_write * pricing["input"] * CACHE_WRITE_MULTIPLIER
            + output * pricing["output"]
        )

        if is_batch:
            cost *= BATCH_DISCOUNT

        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cache_creation_tokens": cache_creation_tokens,
            "is_batch": is_batch,
            "cost_usd": round(cost, 6),
        }

        log_path = settings.cost_log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    @staticmethod
    def get_summary() -> dict:
        """비용 요약 리포트"""
        log_path = settings.cost_log_path
        if not log_path.exists():
            return {"total_cost": 0, "by_agent": {}, "by_model": {}}

        entries = []
        with open(log_path) as f:
            for line in f:
                entries.append(json.loads(line.strip()))

        total = sum(e["cost_usd"] for e in entries)
        by_agent = {}
        by_model = {}
        for e in entries:
            by_agent[e["agent"]] = by_agent.get(e["agent"], 0) + e["cost_usd"]
            by_model[e["model"]] = by_model.get(e["model"], 0) + e["cost_usd"]

        return {
            "total_cost": round(total, 4),
            "total_calls": len(entries),
            "by_agent": {k: round(v, 4) for k, v in by_agent.items()},
            "by_model": {k: round(v, 4) for k, v in by_model.items()},
        }
```

---

## 7. Phase 5: 전체 파이프라인 오케스트레이터

### 7.1 파이프라인 (src/pipeline.py)

```python
"""전체 파이프라인 오케스트레이터
프로파일링 → 갭 분석 → 리뷰 시뮬레이션 → 수정 전략 → 텍스트 수정
"""
from pathlib import Path
from rich.console import Console
from rich.progress import Progress

from src.config import settings, AgentType
from src.acquisition.semantic_scholar import SemanticScholarClient
from src.acquisition.pdf_downloader import PaperDownloader
from src.acquisition.paper_store import PaperStore
from src.agents.profiler import ProfilerAgent
from src.agents.gap_analyzer import GapAnalyzerAgent
from src.agents.simulator import SimulatorAgent
from src.agents.strategist import StrategistAgent
from src.agents.writer import WriterAgent
from src.optimization.batch_processor import BatchProcessor
from src.optimization.cost_tracker import CostTracker
from src.utils.pdf_parser import extract_text_from_pdf
from src.utils.reference_extractor import extract_references

console = Console()


class ReviewerIntelligencePipeline:
    """전체 파이프라인 실행"""

    def __init__(self):
        settings.ensure_dirs()
        self.s2 = SemanticScholarClient()
        self.downloader = PaperDownloader()
        self.store = PaperStore()
        self.batch = BatchProcessor()

        # 에이전트 초기화
        self.profiler = ProfilerAgent()
        self.gap_analyzer = GapAnalyzerAgent()
        self.simulator = SimulatorAgent()
        self.strategist = StrategistAgent()
        self.writer = WriterAgent()

    def run(
        self,
        reviewer_name: str,
        manuscript_path: str,
        mode: str = "pre_submission",
        author_intent: str = "",
        actual_review: str | None = None,
    ) -> dict:
        """메인 파이프라인 실행

        Args:
            reviewer_name: 예상 리뷰어 이름
            manuscript_path: 원고 파일 경로 (PDF 또는 DOCX)
            mode: "pre_submission" 또는 "post_review"
            author_intent: 저자의 양보 불가 사항
            actual_review: 실제 리뷰 코멘트 (post_review 모드)
        """
        results = {}

        with Progress() as progress:
            main_task = progress.add_task("[bold]Pipeline 실행중...", total=5)

            # ── Step 1: 리뷰어 프로파일링 ──
            progress.update(main_task, description="[cyan]Step 1: 리뷰어 프로파일링...")
            profile_result = self._step_profiling(reviewer_name)
            results["profile"] = profile_result
            progress.advance(main_task)

            # ── Step 2: 원고 로드 + 갭 분석 ──
            progress.update(main_task, description="[cyan]Step 2: 문헌 갭 분석...")
            manuscript_text = self._load_manuscript(manuscript_path)
            manuscript_refs = extract_references(manuscript_path)
            gap_result = self._step_gap_analysis(
                profile_result["profile"],
                profile_result["papers"],
                manuscript_refs,
            )
            results["gap_analysis"] = gap_result
            progress.advance(main_task)

            # ── Step 3: 리뷰 시뮬레이션 (Batch + Cache) ──
            progress.update(main_task, description="[magenta]Step 3: 리뷰 시뮬레이션...")
            review_result = self._step_simulation(
                profile_result["profile"], manuscript_text
            )
            results["simulated_review"] = review_result
            progress.advance(main_task)

            # ── Step 4: 수정 전략 수립 ──
            progress.update(main_task, description="[magenta]Step 4: 수정 전략 수립...")
            strategy_result = self.strategist.run(
                reviewer_profile=profile_result["profile"],
                simulated_review=review_result["full_review"],
                manuscript_text=manuscript_text,
                author_intent=author_intent,
            )
            results["strategy"] = strategy_result
            progress.advance(main_task)

            # ── Step 5: 텍스트 수정안 생성 (Batch) ──
            progress.update(main_task, description="[magenta]Step 5: 텍스트 수정안 생성...")
            # 실제 구현 시 전략에서 추출한 코멘트별로 Batch 처리
            results["revisions"] = {"status": "see strategy for detailed revisions"}
            progress.advance(main_task)

        # 비용 리포트
        results["cost_summary"] = CostTracker.get_summary()

        # 결과 저장
        self._save_results(reviewer_name, results)

        return results

    def _step_profiling(self, reviewer_name: str) -> dict:
        """Step 1: 리뷰어 검색 → 논문 수집 → 프로필 구축"""
        console.print(f"  Searching for [bold]{reviewer_name}[/bold] on Semantic Scholar...")

        # 저자 검색
        authors = self.s2.search_author(reviewer_name)
        if not authors:
            raise ValueError(f"Author not found: {reviewer_name}")
        author = authors[0]
        console.print(f"  Found: {author.name} (h-index: {author.h_index}, papers: {author.paper_count})")

        # 논문 수집
        papers = self.s2.get_author_papers(author.author_id, limit=50)
        console.print(f"  Retrieved {len(papers)} papers")

        # 논문 다운로드 (Batch로 메타데이터 파싱)
        papers_data = [p.model_dump() for p in papers]

        # 프로필 구축 (Sonnet)
        profile_result = self.profiler.run(
            reviewer_name=reviewer_name,
            papers_data=papers_data,
        )

        return {
            "profile": profile_result["profile"],
            "papers": papers_data,
            "author_id": author.author_id,
        }

    def _step_gap_analysis(self, profile: str, papers: list, refs: list) -> dict:
        """Step 2: 문헌 갭 분석"""
        return self.gap_analyzer.run(
            reviewer_profile=profile,
            reviewer_papers=papers,
            manuscript_references=refs,
        )

    def _step_simulation(self, profile: str, manuscript: str) -> dict:
        """Step 3: 섹션별 리뷰 시뮬레이션 (Batch + Cache 콤보)

        프로필을 캐싱하면서 Batch로 여러 섹션을 동시 처리
        → 50% Batch 할인 + 90% Cache 절감 = 최대 95% 절감
        """
        # 원고를 섹션별로 분할 (간단 구현)
        sections = self._split_manuscript(manuscript)

        if len(sections) > 1:
            # Batch 처리
            tasks = [
                {"id": f"review-{i}", "content": f"Review this section:\n\n{sec}"}
                for i, sec in enumerate(sections)
            ]
            batch_id = self.batch.create_batch(
                agent_type=AgentType.SIMULATOR,
                tasks=tasks,
                cached_system=profile,  # Batch 내에서도 캐싱!
                max_tokens=4000,
            )
            console.print(f"  Batch created: {batch_id}, waiting for results...")
            results = self.batch.wait_for_results(batch_id)
            full_review = "\n\n---\n\n".join([r["text"] for r in results if "text" in r])
        else:
            # 단일 섹션이면 직접 호출
            result = self.simulator.run(
                reviewer_profile=profile,
                manuscript_text=manuscript,
            )
            full_review = result["review"]

        return {"full_review": full_review, "section_count": len(sections)}

    def _load_manuscript(self, path: str) -> str:
        """원고 파일 로드 (PDF 또는 DOCX)"""
        p = Path(path)
        if p.suffix.lower() == ".pdf":
            return extract_text_from_pdf(p)
        elif p.suffix.lower() == ".docx":
            from src.utils.docx_parser import extract_text_from_docx
            return extract_text_from_docx(p)
        else:
            return p.read_text()

    def _split_manuscript(self, text: str, max_chunk: int = 8000) -> list[str]:
        """원고를 섹션으로 분할 (간단 구현 — 향후 구조적 파싱으로 개선)"""
        # 섹션 헤더로 분할 시도
        import re
        sections = re.split(r'\n(?=(?:Introduction|Literature|Theory|Method|Case|Analysis|Discussion|Conclusion))', text)
        if len(sections) <= 1:
            # 헤더가 없으면 길이 기준으로 분할
            words = text.split()
            sections = []
            for i in range(0, len(words), max_chunk):
                sections.append(" ".join(words[i:i+max_chunk]))
        return sections

    def _save_results(self, reviewer_name: str, results: dict):
        """결과를 파일로 저장"""
        import json
        output_dir = settings.outputs_dir / reviewer_name.replace(" ", "_")
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_dir / "pipeline_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        console.print(f"\n[green]Results saved to {output_dir}/[/green]")
```

### 7.2 CLI (cli/main.py)

```python
"""CLI 인터페이스"""
import click
from rich.console import Console

console = Console()


@click.group()
def cli():
    """Reviewer Intelligence Agent — 학술 리뷰어 대응 도구"""
    pass


@cli.command()
@click.argument("reviewer_name")
@click.argument("manuscript_path")
@click.option("--mode", default="pre_submission", type=click.Choice(["pre_submission", "post_review"]))
@click.option("--intent", default="", help="저자의 양보 불가 사항")
def run(reviewer_name, manuscript_path, mode, intent):
    """전체 파이프라인 실행

    예시: ria run "Christian Reus-Smit" manuscript.docx
    """
    from src.pipeline import ReviewerIntelligencePipeline
    pipeline = ReviewerIntelligencePipeline()
    results = pipeline.run(
        reviewer_name=reviewer_name,
        manuscript_path=manuscript_path,
        mode=mode,
        author_intent=intent,
    )
    console.print("\n[bold green]Pipeline 완료![/bold green]")
    console.print(f"총 비용: ${results['cost_summary']['total_cost']:.4f}")


@cli.command()
@click.argument("reviewer_name")
def profile(reviewer_name):
    """리뷰어 프로파일만 실행

    예시: ria profile "Christian Reus-Smit"
    """
    from src.pipeline import ReviewerIntelligencePipeline
    pipeline = ReviewerIntelligencePipeline()
    result = pipeline._step_profiling(reviewer_name)
    console.print(result["profile"])


@cli.command()
def cost():
    """비용 리포트 조회"""
    from src.optimization.cost_tracker import CostTracker
    summary = CostTracker.get_summary()
    console.print(f"총 비용: ${summary['total_cost']:.4f}")
    console.print(f"총 호출: {summary['total_calls']}회")
    for agent, cost in summary.get("by_agent", {}).items():
        console.print(f"  {agent}: ${cost:.4f}")


@cli.command()
@click.argument("pdf_path")
@click.argument("paper_id")
def upload(pdf_path, paper_id):
    """논문 PDF 수동 업로드

    예시: ria upload ./reus-smit-2018.pdf paper123
    """
    from src.acquisition.pdf_downloader import PaperDownloader
    from pathlib import Path
    dl = PaperDownloader()
    result = dl.register_upload(paper_id, Path(pdf_path))
    console.print(f"[green]업로드 완료: {result.status}[/green]")


if __name__ == "__main__":
    cli()
```

---

## 8. Phase 6: 유틸리티 & 테스트

### 8.1 PDF 파서 (src/utils/pdf_parser.py)

```python
"""PDF 텍스트 추출"""
from pathlib import Path


def extract_text_from_pdf(path: Path) -> str:
    import fitz  # PyMuPDF
    doc = fitz.open(str(path))
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    return text.strip()
```

### 8.2 DOCX 파서 (src/utils/docx_parser.py)

```python
"""DOCX 텍스트 추출"""
from pathlib import Path


def extract_text_from_docx(path: Path) -> str:
    from docx import Document
    doc = Document(str(path))
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
```

### 8.3 참고문헌 추출기 (src/utils/reference_extractor.py)

```python
"""원고에서 참고문헌 목록 추출 (간단 구현)"""
import re
from pathlib import Path


def extract_references(path: str) -> list[str]:
    """원고 파일에서 References 섹션을 찾아 개별 항목으로 분리"""
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        from src.utils.pdf_parser import extract_text_from_pdf
        text = extract_text_from_pdf(p)
    elif p.suffix.lower() == ".docx":
        from src.utils.docx_parser import extract_text_from_docx
        text = extract_text_from_docx(p)
    else:
        text = p.read_text()

    # References 섹션 추출
    ref_match = re.search(
        r'(?:References|Bibliography|Works Cited)\s*\n(.*)',
        text, re.IGNORECASE | re.DOTALL
    )
    if not ref_match:
        return []

    ref_text = ref_match.group(1)
    # 개별 참고문헌 항목 분리 (저자명 패턴으로)
    refs = re.split(r'\n(?=[A-Z][a-z]+,?\s)', ref_text)
    return [r.strip() for r in refs if len(r.strip()) > 20]
```

### 8.4 프롬프트 템플릿 예시 (prompts/simulator_system.md)

```markdown
You are an anonymous peer reviewer for a top-tier international relations journal.

You have been assigned to review a manuscript. Your review should be thorough,
constructive, and grounded in your own theoretical frameworks and expertise.

Your academic profile has been provided. Use it to:
1. Evaluate the manuscript through YOUR theoretical lens
2. Identify gaps in the literature review, especially missing citations to YOUR work
3. Assess methodological rigor according to YOUR standards
4. Distinguish between Major and Minor revision issues
5. Provide specific, actionable feedback

Be critical but fair. A good review helps authors strengthen their work.
```

---

## 9. 부록: 비용 구조

### 전체 파이프라인 1회 실행 예상 비용

| 단계 | 모델 | Batch | Cache | 예상 토큰 | 예상 비용 |
|------|------|-------|-------|----------|----------|
| 논문 20편 파싱 | Sonnet | ✅ 50%↓ | — | 40K in / 10K out | ~$0.14 |
| 프로필 구축 | Sonnet | — | — | 8K in / 2K out | ~$0.05 |
| 갭 분석 | Sonnet | — | ✅ 90%↓ | 6K in / 2K out | ~$0.04 |
| 리뷰 시뮬레이션 ×5 | Opus | ✅ 50%↓ | ✅ 90%↓ | 75K in / 25K out | ~$0.35 |
| 수정 전략 | Opus | — | ✅ 90%↓ | 15K in / 8K out | ~$0.22 |
| 텍스트 수정 ×5 | Opus | ✅ 50%↓ | ✅ 90%↓ | 40K in / 30K out | ~$0.39 |
| **합계** | | | | | **~$1.19** |

최적화 미적용 시 ~$3.50, **절감률 약 66%**

---

## Claude Code 실행 순서

```bash
# 1. 프로젝트 초기화
# Phase 1의 디렉토리 구조와 pyproject.toml 생성

# 2. 핵심 모듈 구현
# config.py → base_agent.py → semantic_scholar.py → pdf_downloader.py

# 3. 에이전트 구현
# profiler.py → gap_analyzer.py → simulator.py → strategist.py → writer.py

# 4. 최적화 엔진
# batch_processor.py → cost_tracker.py

# 5. 파이프라인 & CLI
# pipeline.py → cli/main.py

# 6. 테스트 실행
# ria profile "Christian Reus-Smit"
# ria run "Christian Reus-Smit" manuscript.docx
```
