"""🔬 리뷰어 프로파일러 — Sonnet으로 실행

리뷰어의 저작 목록(초록 포함)을 분석하여 학술 프로필을 구축합니다.
이론 체계, 방법론, 핵심 개념, 비판 패턴 등을 구조화합니다.
"""
from src.agents.base_agent import BaseAgent
from src.config import AgentType


class ProfilerAgent(BaseAgent):
    agent_type = AgentType.PROFILER

    def run(self, reviewer_name: str, papers_data: list[dict]) -> dict:
        """리뷰어의 학술 프로필을 구축

        Args:
            reviewer_name: 리뷰어 이름
            papers_data: S2에서 수집한 논문 메타데이터 + 초록 목록
                         [{"title": str, "year": int, "venue": str,
                           "citation_count": int, "abstract": str}, ...]

        Returns:
            {"reviewer_name": str, "profile": str} — 구조화된 JSON 프로필
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
