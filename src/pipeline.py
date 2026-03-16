"""전체 파이프라인 오케스트레이터

프로파일링 → 갭 분석 → 리뷰 시뮬레이션 → 수정 전략 → 텍스트 수정

두 가지 운영 모드:
  - pre_submission: 투고 전 원고 강화
  - post_review: R&R 대응 (실제 리뷰 기반)
"""
from __future__ import annotations

import json
import re
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
from src.utils.logging_config import logger

console = Console()


class ReviewerIntelligencePipeline:
    """전체 파이프라인 실행

    Usage:
        pipeline = ReviewerIntelligencePipeline()
        results = pipeline.run(
            reviewer_name="Christian Reus-Smit",
            manuscript_path="manuscript.docx",
        )
    """

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

        Returns:
            각 단계별 결과를 담은 dict
        """
        results = {}

        with Progress() as progress:
            main_task = progress.add_task("[bold]Pipeline 실행중...", total=5)

            # ── Step 1: 리뷰어 프로파일링 ──
            progress.update(
                main_task,
                description="[cyan]Step 1: 리뷰어 프로파일링...",
            )
            profile_result = self._step_profiling(reviewer_name)
            results["profile"] = profile_result
            progress.advance(main_task)

            # ── Step 2: 원고 로드 + 갭 분석 ──
            progress.update(
                main_task,
                description="[cyan]Step 2: 문헌 갭 분석...",
            )
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
            progress.update(
                main_task,
                description="[magenta]Step 3: 리뷰 시뮬레이션...",
            )
            if mode == "post_review" and actual_review:
                # R&R 모드: 실제 리뷰 사용
                review_result = {
                    "full_review": actual_review,
                    "section_count": 1,
                }
            else:
                review_result = self._step_simulation(
                    profile_result["profile"],
                    manuscript_text,
                )
            results["simulated_review"] = review_result
            progress.advance(main_task)

            # ── Step 4: 수정 전략 수립 ──
            progress.update(
                main_task,
                description="[magenta]Step 4: 수정 전략 수립...",
            )
            strategy_result = self.strategist.run(
                reviewer_profile=profile_result["profile"],
                simulated_review=review_result["full_review"],
                manuscript_text=manuscript_text,
                author_intent=author_intent,
            )
            results["strategy"] = strategy_result
            progress.advance(main_task)

            # ── Step 5: 텍스트 수정안 생성 (Batch) ──
            progress.update(
                main_task,
                description="[magenta]Step 5: 텍스트 수정안 생성...",
            )
            revisions = self._step_revisions(
                profile_result["profile"],
                strategy_result,
                manuscript_text,
            )
            results["revisions"] = revisions
            progress.advance(main_task)

        # 비용 리포트
        results["cost_summary"] = CostTracker.get_summary()

        # 결과 저장
        self._save_results(reviewer_name, results)

        return results

    # ─────────────────────────────────────────────
    # Private step methods
    # ─────────────────────────────────────────────

    def _step_profiling(self, reviewer_name: str) -> dict:
        """Step 1: 리뷰어 검색 → 논문 수집 → 프로필 구축"""
        console.print(
            f"  Searching for [bold]{reviewer_name}[/bold] on Semantic Scholar..."
        )

        # 저자 검색
        authors = self.s2.search_author(reviewer_name)
        if not authors:
            raise ValueError(f"Author not found: {reviewer_name}")
        author = authors[0]
        console.print(
            f"  Found: {author.name} "
            f"(h-index: {author.h_index}, papers: {author.paper_count})"
        )

        # 논문 수집
        papers = self.s2.get_author_papers(author.author_id, limit=50)
        console.print(f"  Retrieved {len(papers)} papers")

        # 논문 데이터 직렬화
        papers_data = [p.model_dump() for p in papers]

        # 프로필 구축 (Sonnet)
        profile_result = self.profiler.run(
            reviewer_name=reviewer_name,
            papers_data=papers_data,
        )

        # DB에 리뷰어 + 논문 저장
        reviewer_id = author.author_id
        self.store.upsert_reviewer({
            "reviewer_id": reviewer_id,
            "name": reviewer_name,
            "s2_author_id": author.author_id,
            "affiliations": author.affiliations or [],
            "h_index": author.h_index,
            "profile_json": profile_result["profile"],
        })
        for p in papers_data:
            p_copy = {**p, "reviewer_id": reviewer_id}
            self.store.upsert_paper(p_copy)

        return {
            "profile": profile_result["profile"],
            "papers": papers_data,
            "author_id": author.author_id,
        }

    def _step_gap_analysis(
        self, profile: str, papers: list, refs: list
    ) -> dict:
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
            console.print(
                f"  Batch created: {batch_id}, waiting for results..."
            )
            results = self.batch.wait_for_results(batch_id)
            full_review = "\n\n---\n\n".join(
                r["text"] for r in results if "text" in r
            )
        else:
            # 단일 섹션이면 직접 호출
            result = self.simulator.run(
                reviewer_profile=profile,
                manuscript_text=manuscript,
            )
            full_review = result["review"]

        return {"full_review": full_review, "section_count": len(sections)}

    def _step_revisions(
        self,
        profile: str,
        strategy: dict,
        manuscript_text: str,
    ) -> dict:
        """Step 5: 전략에서 추출한 코멘트별 수정안 생성

        전략 결과에서 개별 코멘트를 추출하여 WriterAgent로 수정안 생성.
        코멘트가 여러 개면 순차적으로 처리합니다.
        """
        strategy_text = strategy.get("strategy", "")

        # 전략 텍스트에서 "raw_response"가 있으면 사용
        if "raw_response" in strategy:
            strategy_text = strategy["raw_response"]

        # WriterAgent에 전체 전략을 넘겨 수정안 생성
        try:
            revision_result = self.writer.run(
                reviewer_profile=profile,
                revision_strategy=strategy_text,
                original_section=manuscript_text[:8000],  # 첫 8000자
                comment="Apply the revision strategy to improve the manuscript.",
            )
            return {
                "status": "completed",
                "revision": revision_result.get("revision", ""),
            }
        except Exception as e:
            logger.warning("수정안 생성 중 오류: %s", e)
            return {
                "status": "see strategy for detailed revisions",
                "error": str(e),
            }

    # ─────────────────────────────────────────────
    # Utility methods
    # ─────────────────────────────────────────────

    def _load_manuscript(self, path: str) -> str:
        """원고 파일 로드 (PDF 또는 DOCX)"""
        p = Path(path)
        if p.suffix.lower() == ".pdf":
            return extract_text_from_pdf(p)
        elif p.suffix.lower() == ".docx":
            from src.utils.docx_parser import extract_text_from_docx

            return extract_text_from_docx(p)
        else:
            return p.read_text(encoding="utf-8")

    def _split_manuscript(
        self, text: str, max_chunk: int = 8000
    ) -> list[str]:
        """원고를 섹션으로 분할

        학술 논문의 일반적인 섹션 헤더를 기준으로 분할합니다.
        헤더가 없으면 단어 수 기준으로 분할합니다.
        """
        sections = re.split(
            r"\n(?=(?:Introduction|Literature|Theory|Method|"
            r"Case|Analysis|Discussion|Conclusion|Results|"
            r"Findings|Framework|Background|Hypothes))",
            text,
        )
        if len(sections) <= 1:
            # 헤더가 없으면 길이 기준으로 분할
            words = text.split()
            sections = []
            for i in range(0, len(words), max_chunk):
                sections.append(" ".join(words[i : i + max_chunk]))
        return sections

    def _save_results(self, reviewer_name: str, results: dict):
        """결과를 파일로 저장"""
        output_dir = settings.outputs_dir / reviewer_name.replace(" ", "_")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "pipeline_results.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str, ensure_ascii=False)
        console.print(f"\n[green]Results saved to {output_dir}/[/green]")
