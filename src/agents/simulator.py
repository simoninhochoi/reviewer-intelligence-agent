"""🎭 리뷰 시뮬레이터 — Opus로 실행, 리뷰어 프로필을 캐싱

리뷰어의 학술적 관점에서 원고를 심사하고
상세 리뷰 코멘트(Major/Minor Issues, Missing References)를 생성합니다.
"""
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
