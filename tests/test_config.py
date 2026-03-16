"""src/config.py 테스트"""
from src.config import (
    AgentType,
    ModelTier,
    AGENT_MODEL_MAP,
    MODEL_PRICING,
    BATCH_DISCOUNT,
    CACHE_READ_MULTIPLIER,
    CACHE_WRITE_MULTIPLIER,
    Settings,
)


class TestModelTier:
    def test_sonnet_value(self):
        assert ModelTier.SONNET.value == "claude-sonnet-4-6"

    def test_opus_value(self):
        assert ModelTier.OPUS.value == "claude-opus-4-6"


class TestAgentType:
    def test_all_agents_defined(self):
        expected = {"profiler", "gap_analyzer", "simulator", "strategist", "writer"}
        actual = {a.value for a in AgentType}
        assert actual == expected


class TestModelRouting:
    def test_profiler_uses_sonnet(self):
        assert AGENT_MODEL_MAP[AgentType.PROFILER] == ModelTier.SONNET

    def test_gap_analyzer_uses_sonnet(self):
        assert AGENT_MODEL_MAP[AgentType.GAP_ANALYZER] == ModelTier.SONNET

    def test_simulator_uses_opus(self):
        assert AGENT_MODEL_MAP[AgentType.SIMULATOR] == ModelTier.OPUS

    def test_strategist_uses_opus(self):
        assert AGENT_MODEL_MAP[AgentType.STRATEGIST] == ModelTier.OPUS

    def test_writer_uses_opus(self):
        assert AGENT_MODEL_MAP[AgentType.WRITER] == ModelTier.OPUS

    def test_all_agents_have_routing(self):
        for agent_type in AgentType:
            assert agent_type in AGENT_MODEL_MAP, f"{agent_type} missing from routing"


class TestPricing:
    def test_sonnet_pricing(self):
        p = MODEL_PRICING[ModelTier.SONNET]
        assert p["input"] == 3.0
        assert p["output"] == 15.0

    def test_opus_pricing(self):
        p = MODEL_PRICING[ModelTier.OPUS]
        assert p["input"] == 5.0
        assert p["output"] == 25.0

    def test_batch_discount(self):
        assert BATCH_DISCOUNT == 0.5

    def test_cache_multipliers(self):
        assert CACHE_WRITE_MULTIPLIER == 1.25
        assert CACHE_READ_MULTIPLIER == 0.1


class TestSettings:
    def test_default_dirs(self):
        s = Settings()
        assert s.papers_dir.name == "papers"
        assert s.profiles_dir.name == "profiles"
        assert s.outputs_dir.name == "outputs"

    def test_ensure_dirs(self, tmp_path):
        s = Settings(
            papers_dir=tmp_path / "p",
            profiles_dir=tmp_path / "pr",
            outputs_dir=tmp_path / "o",
            chroma_persist_dir=tmp_path / "c",
        )
        s.ensure_dirs()
        assert (tmp_path / "p").exists()
        assert (tmp_path / "pr").exists()
        assert (tmp_path / "o").exists()
        assert (tmp_path / "c").exists()
