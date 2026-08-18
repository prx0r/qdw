"""RouteLLM integration tests — real routing behavior."""

from pathlib import Path

import pytest

from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.hotswap.routellm import RouteLLMRouter, RouteLLMResult


@pytest.fixture
def env(tmp_path: Path):
    db = Database(str(tmp_path / "db.db"))
    db.migrate()
    ledger = Ledger(db)
    router = RouteLLMRouter(db, ledger)
    return db, ledger, router


class TestRouteLLMRouter:
    def test_short_prompt_routes_to_cheap(self, env) -> None:
        """Short prompts should route to weak/cheap models."""
        _, _, router = env
        result = router.route("hello", threshold=0.5, strong_model="gpt-4", weak_model="gpt-3.5-turbo")
        assert result.selected_model == "gpt-3.5-turbo"
        assert result.confidence > 0

    def test_long_prompt_routes_to_strong(self, env) -> None:
        """Long complex prompts should route to strong models."""
        _, _, router = env
        long_prompt = "x" * 600
        result = router.route(long_prompt, threshold=0.5, strong_model="gpt-4", weak_model="gpt-3.5-turbo")
        assert result.selected_model == "gpt-4"

    def test_threshold_controls_routing(self, env) -> None:
        """Different thresholds should change routing decisions."""
        _, _, router = env
        prompt = "x" * 300  # medium complexity

        # Low threshold → route to strong
        result_low = router.route(prompt, threshold=0.3)
        assert result_low.selected_model == "gpt-4"

        # High threshold → route to weak
        result_high = router.route(prompt, threshold=0.9)
        assert result_high.selected_model == "gpt-3.5-turbo"

    def test_cost_savings_calculated(self, env) -> None:
        """Weak model selection should show cost savings."""
        _, _, router = env
        result = router.route("hi", threshold=0.9)
        assert result.cost_savings_estimate > 0

    def test_register_model_pair(self, env) -> None:
        db, ledger, router = env
        pair_id = router.register_model_pair("gpt-4", "gpt-3.5", "sw_ranking")
        assert pair_id.startswith("modelpair_")
        pairs = router.get_model_pairs()
        assert len(pairs) == 1
        assert pairs[0]["strong_model"] == "gpt-4"

    def test_result_is_immutable(self, env) -> None:
        _, _, router = env
        result = router.route("test")
        # Result is a frozen dataclass
        with pytest.raises(AttributeError):
            result.selected_model = "modified"
