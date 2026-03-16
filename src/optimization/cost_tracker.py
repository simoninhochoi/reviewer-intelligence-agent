"""API 비용 실시간 추적 및 리포팅"""
import json
from datetime import datetime

from src.config import (
    settings,
    MODEL_PRICING,
    BATCH_DISCOUNT,
    CACHE_READ_MULTIPLIER,
    CACHE_WRITE_MULTIPLIER,
    ModelTier,
)


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
        """비용 로그 기록

        Args:
            agent: 에이전트 이름 (profiler, simulator 등)
            model: 모델 ID (claude-sonnet-4-6 등)
            input_tokens: 입력 토큰 수
            output_tokens: 출력 토큰 수
            cache_read_tokens: 캐시 읽기 토큰 수
            cache_creation_tokens: 캐시 생성 토큰 수
            is_batch: Batch API 사용 여부 (50% 할인)
        """
        # model string에서 ModelTier enum 매칭 시도
        pricing = {"input": 5.0, "output": 25.0}  # 기본값 (Opus)
        for tier in ModelTier:
            if tier.value == model:
                pricing = MODEL_PRICING[tier]
                break

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
        """비용 요약 리포트

        Returns:
            {"total_cost": float, "total_calls": int,
             "by_agent": {agent: cost}, "by_model": {model: cost}}
        """
        log_path = settings.cost_log_path
        if not log_path.exists():
            return {"total_cost": 0, "total_calls": 0, "by_agent": {}, "by_model": {}}

        entries = []
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))

        total = sum(e["cost_usd"] for e in entries)
        by_agent: dict[str, float] = {}
        by_model: dict[str, float] = {}
        for e in entries:
            by_agent[e["agent"]] = by_agent.get(e["agent"], 0) + e["cost_usd"]
            by_model[e["model"]] = by_model.get(e["model"], 0) + e["cost_usd"]

        return {
            "total_cost": round(total, 4),
            "total_calls": len(entries),
            "by_agent": {k: round(v, 4) for k, v in by_agent.items()},
            "by_model": {k: round(v, 4) for k, v in by_model.items()},
        }

    @staticmethod
    def reset():
        """비용 로그 초기화 (테스트용)"""
        log_path = settings.cost_log_path
        if log_path.exists():
            log_path.unlink()
