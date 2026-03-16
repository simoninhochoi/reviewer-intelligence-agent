"""모든 에이전트의 기본 클래스 — 모델 라우팅, 캐싱, 비용 추적 통합"""
import anthropic
from abc import ABC, abstractmethod
from pathlib import Path

from src.config import settings, AGENT_MODEL_MAP, AgentType, ModelTier
from src.utils.logging_config import logger


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
        logger.debug(f"에이전트 초기화: {self.agent_type.value} → {self.model}")

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
                "cache_control": {"type": "ephemeral"},
            })

        if system_prompt:
            system_blocks.append({
                "type": "text",
                "text": system_prompt,
            })

        # 시스템 프롬프트가 없으면 기본 프롬프트 로드
        if not system_blocks:
            system_blocks = self._load_default_system_prompt()

        logger.info(f"[{self.agent_type.value}] API 호출 ({self.model})")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_blocks,
            messages=[{"role": "user", "content": user_message}],
        )

        # 비용 추적
        self._track_cost(response.usage)

        logger.info(
            f"[{self.agent_type.value}] 완료: "
            f"in={response.usage.input_tokens}, out={response.usage.output_tokens}"
        )

        return response.content[0].text

    def _load_default_system_prompt(self) -> list[dict]:
        """prompts/ 디렉토리에서 기본 시스템 프롬프트 로드"""
        prompt_path = Path(f"prompts/{self.agent_type.value}_system.md")
        if prompt_path.exists():
            return [{"type": "text", "text": prompt_path.read_text(encoding="utf-8")}]
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
