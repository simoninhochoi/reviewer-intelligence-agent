"""🧭 수정 전략가 — Opus로 실행

리뷰 코멘트에 대한 대응 전략을 수립하고
Response Letter 초안을 생성합니다.
"""
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
