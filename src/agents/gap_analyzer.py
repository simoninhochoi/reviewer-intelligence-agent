"""📚 문헌 갭 분석기 — Sonnet으로 실행

원고의 참고문헌 목록과 리뷰어의 핵심 저작을 비교하여
인용 갭을 식별하고 추가 인용 전략을 수립합니다.
"""
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
                             [{"title": str, "year": int, "citation_count": int}, ...]
            manuscript_references: 원고의 참고문헌 목록 (문자열 리스트)

        Returns:
            {"gap_analysis": str} — 구조화된 JSON 갭 분석 결과
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
