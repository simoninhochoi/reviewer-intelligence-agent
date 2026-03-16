# CLAUDE.md — Reviewer Intelligence Agent

## 프로젝트 정체성
까다로운 학술 리뷰어의 저서·논문을 학습하고, 리뷰를 시뮬레이션하여, 논문 수정 전략을 자동으로 수립하는 멀티 에이전트 시스템.

## 핵심 설계 원칙

### 모델 라우팅 (절대 변경 금지)
- **Sonnet 4.6**: 프로파일러, 갭 분석기 (수집·구조화·비교 태스크)
- **Opus 4.6**: 시뮬레이터, 전략가, 작문코치 (분석·추론·창작 태스크)

### API 최적화 (모든 호출에 적용)
- **Prompt Caching**: 리뷰어 프로필, 원고 전문 등 반복 컨텍스트에 `cache_control: {"type": "ephemeral"}` 적용
- **Batch API**: 논문 일괄 파싱, 섹션별 시뮬레이션, 수정안 생성 등 즉시 응답 불필요한 작업은 `client.messages.batches.create()` 사용
- Batch + Cache는 동시 적용 가능 (콤보 절감)

### 논문 수집 3-Layer 폴백
1. Open Access (S2 openAccessPdf + Unpaywall) → 자동
2. 서울대 프록시 (`libproxy.snu.ac.kr/link.n2s?url=`) → 자동, 5초 간격
3. 사용자 직접 업로드 → 수동

## 기술 스택
- Python 3.11+, anthropic SDK, httpx, chromadb, pydantic, click, rich, streamlit
- Semantic Scholar API (논문 수집), Unpaywall API (OA 탐색)
- SQLite (메타데이터), ChromaDB (벡터 검색)

## 디렉토리 규칙
- `src/` — 모든 소스 코드
- `src/agents/` — 5개 에이전트 (base_agent.py 상속)
- `src/acquisition/` — 논문 수집 파이프라인
- `src/optimization/` — Batch/Cache/Cost 추적
- `prompts/` — 에이전트 시스템 프롬프트 (마크다운)
- `data/` — 로컬 데이터 (gitignore)

## 코딩 컨벤션
- Pydantic 모델 사용, type hints 필수
- tenacity로 API 재시도
- rich로 CLI 출력
- 모든 비용은 CostTracker.log()로 기록

## 구현 상세 스펙
전체 구현 스펙은 `RIA_CLAUDE_CODE_SPEC.md` 참조. 6개 Phase로 구성:
1. 프로젝트 셋업 & 핵심 인프라
2. 논문 수집 파이프라인 (3-Layer)
3. 5개 에이전트 구현
4. API 최적화 엔진 (Batch + Cache)
5. 파이프라인 오케스트레이터 & CLI
6. 테스트 & 배포
