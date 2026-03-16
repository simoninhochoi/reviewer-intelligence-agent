"""Batch API 매니저 — 입출력 토큰 50% 할인, 비동기 처리

사용 시나리오:
- 논문 20편 일괄 파싱 (프로파일러)
- 섹션별 리뷰 시뮬레이션 5건 (시뮬레이터)
- 코멘트별 수정안 생성 (작문코치)

Batch + Prompt Cache 동시 적용 가능 → 콤보 절감
"""
from __future__ import annotations

import time

import anthropic
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.config import settings, AGENT_MODEL_MAP, AgentType
from src.optimization.cost_tracker import CostTracker
from src.utils.logging_config import logger


class BatchProcessor:
    """여러 태스크를 Batch API로 묶어 처리"""

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
                req["params"]["system"] = [
                    {
                        "type": "text",
                        "text": cached_system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            requests.append(req)

        logger.info(
            "Batch 생성: agent=%s, model=%s, tasks=%d",
            agent_type.value,
            model,
            len(tasks),
        )
        batch = self.client.messages.batches.create(requests=requests)
        logger.info("Batch ID: %s", batch.id)
        return batch.id

    def wait_for_results(
        self,
        batch_id: str,
        poll_interval: int = 30,
        show_progress: bool = True,
    ) -> list[dict]:
        """Batch 완료까지 대기 후 결과 반환

        Args:
            batch_id: create_batch에서 반환된 ID
            poll_interval: 폴링 간격 (초)
            show_progress: Rich progress spinner 표시 여부

        Returns:
            [{"id": "task-0", "text": "결과 텍스트", "usage": {...}}, ...]
            실패한 태스크는 {"id": ..., "error": "..."}
        """
        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]Batch 처리 중... {task.description}"),
            ) as progress:
                task = progress.add_task(batch_id, total=None)
                results = self._poll_and_collect(batch_id, poll_interval)
                progress.update(task, description="완료!")
        else:
            results = self._poll_and_collect(batch_id, poll_interval)

        return results

    def _poll_and_collect(self, batch_id: str, poll_interval: int) -> list[dict]:
        """Batch 폴링 및 결과 수집 (내부 메서드)"""
        while True:
            batch = self.client.messages.batches.retrieve(batch_id)
            if batch.processing_status == "ended":
                break
            logger.debug(
                "Batch %s 처리 중... (status=%s)",
                batch_id,
                batch.processing_status,
            )
            time.sleep(poll_interval)

        results = []
        for result in self.client.messages.batches.results(batch_id):
            if result.result.type == "succeeded":
                msg = result.result.message
                usage = msg.usage

                # Batch 비용 자동 추적
                CostTracker.log(
                    agent=f"batch_{result.custom_id}",
                    model=msg.model,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
                    cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
                    is_batch=True,
                )

                results.append(
                    {
                        "id": result.custom_id,
                        "text": msg.content[0].text,
                        "usage": {
                            "input_tokens": usage.input_tokens,
                            "output_tokens": usage.output_tokens,
                        },
                    }
                )
            else:
                logger.warning(
                    "Batch task %s failed: %s",
                    result.custom_id,
                    result.result.error,
                )
                results.append(
                    {
                        "id": result.custom_id,
                        "error": str(result.result.error),
                    }
                )

        succeeded = sum(1 for r in results if "text" in r)
        failed = sum(1 for r in results if "error" in r)
        logger.info(
            "Batch %s 완료: %d 성공, %d 실패",
            batch_id,
            succeeded,
            failed,
        )

        return results

    def create_and_wait(
        self,
        agent_type: AgentType,
        tasks: list[dict],
        cached_system: str | None = None,
        max_tokens: int = 2000,
        poll_interval: int = 30,
    ) -> list[dict]:
        """Batch 생성 + 대기 + 결과 반환 (편의 메서드)"""
        batch_id = self.create_batch(
            agent_type=agent_type,
            tasks=tasks,
            cached_system=cached_system,
            max_tokens=max_tokens,
        )
        return self.wait_for_results(batch_id, poll_interval=poll_interval)
