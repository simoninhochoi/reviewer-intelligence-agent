"""전역 설정 및 모델 라우팅 테이블"""
from enum import Enum
from pathlib import Path
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()


class ModelTier(str, Enum):
    SONNET = "claude-sonnet-4-6"
    OPUS = "claude-opus-4-6"


class AgentType(str, Enum):
    PROFILER = "profiler"
    GAP_ANALYZER = "gap_analyzer"
    SIMULATOR = "simulator"
    STRATEGIST = "strategist"
    WRITER = "writer"


# ═══════════════════════════════════════════════════
# 모델 라우팅: 수집·구조화는 Sonnet, 분석·작성은 Opus
# ═══════════════════════════════════════════════════

AGENT_MODEL_MAP: dict[AgentType, ModelTier] = {
    AgentType.PROFILER:     ModelTier.SONNET,    # 수집·구조화
    AgentType.GAP_ANALYZER: ModelTier.SONNET,    # 문헌 비교
    AgentType.SIMULATOR:    ModelTier.OPUS,      # 깊은 분석
    AgentType.STRATEGIST:   ModelTier.OPUS,      # 전략 추론
    AgentType.WRITER:       ModelTier.OPUS,      # 학술 작문
}

# 모델별 가격 (USD per 1M tokens)
MODEL_PRICING = {
    ModelTier.SONNET: {"input": 3.0, "output": 15.0},
    ModelTier.OPUS:   {"input": 5.0, "output": 25.0},
}

# Batch/Cache 할인율
BATCH_DISCOUNT = 0.5          # 50% 할인
CACHE_WRITE_MULTIPLIER = 1.25  # 첫 캐시 쓰기
CACHE_READ_MULTIPLIER = 0.1    # 캐시 히트 시 90% 절감


class Settings(BaseModel):
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    s2_api_key: str | None = os.getenv("S2_API_KEY")
    snu_proxy_id: str | None = os.getenv("SNU_PROXY_ID")
    snu_proxy_pw: str | None = os.getenv("SNU_PROXY_PW")
    snu_auth_method: str = os.getenv("SNU_AUTH_METHOD", "portal")
    chroma_persist_dir: Path = Path(os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db"))
    cost_log_path: Path = Path(os.getenv("COST_LOG_PATH", "./data/cost_log.jsonl"))
    papers_dir: Path = Path("./data/papers")
    profiles_dir: Path = Path("./data/profiles")
    outputs_dir: Path = Path("./data/outputs")

    def ensure_dirs(self):
        for d in [self.chroma_persist_dir, self.papers_dir, self.profiles_dir, self.outputs_dir]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
