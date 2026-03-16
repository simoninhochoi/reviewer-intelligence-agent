"""✍️ 학술 작문 코치 — Opus로 실행

리뷰어 피드백에 대응하여 실제 텍스트 수정안을 생성합니다.
원저자의 목소리를 유지하면서 리뷰어의 우려를 해소하는 방향으로 수정합니다.
"""
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
