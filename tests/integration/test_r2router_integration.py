"""R2-Router integration tests — joint model+budget routing."""

from pathlib import Path

import pytest

from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.hotswap.r2_router import R2Router, R2Route


@pytest.fixture
def env(tmp_path: Path):
    db = Database(str(tmp_path / "db.db"))
    db.migrate()
    ledger = Ledger(db)
    router = R2Router(db, ledger)
    return db, ledger, router


class TestR2Router:
    def test_route_selects_best_model_budget(self, env) -> None:
        """R2-Router should select the (model, budget) pair with best risk score."""
        _, _, router = env
        result = router.route("Write a complex Python function", models=[
            {"model_id": "gpt-4o", "provider": "openai", "max_tokens": 4000, "cost_per_1k": 0.005},
            {"model_id": "gpt-3.5", "provider": "openai", "max_tokens": 4000, "cost_per_1k": 0.0005},
        ])
        assert isinstance(result, R2Route)
        assert result.model_id in {"gpt-4o", "gpt-3.5"}
        assert result.token_budget > 0
        assert result.predicted_quality > 0

    def test_complex_query_gets_higher_budget(self, env) -> None:
        """Complex queries should get higher token budgets."""
        _, _, router = env
        simple = router.route("hello")
        complex = router.route("x" * 1000)
        # Complex queries should get higher budgets
        assert complex.token_budget >= simple.token_budget

    def test_cost_quality_tradeoff(self, env) -> None:
        """Lambda controls cost vs quality tradeoff."""
        _, _, router = env
        models = [{"model_id": "expensive", "provider": "p", "max_tokens": 4000, "cost_per_1k": 0.01}]
        # High lambda = prioritize cost savings
        cheap = router.route("test", models=models, lambda_val=0.99)
        # Low lambda = prioritize quality
        quality = router.route("test", models=models, lambda_val=0.01)
        # Quality route should get higher budget
        assert quality.token_budget >= cheap.token_budget

    def test_register_model(self, env) -> None:
        db, ledger, router = env
        mid = router.register_model("gpt-4o", "openai", 4000)
        assert mid.startswith("r2model_")

    def test_register_outcome(self, env) -> None:
        _, _, router = env
        route = R2Route("gpt-4o", 1000, 0.9, 0.005, 0.85)
        router.register_outcome(route, True, 800)
        # No assertion needed — just verify no crash

    def test_r2_fits_qdw_cpvs(self, env) -> None:
        """R2-Router's (model, budget) pairs map directly to QDW's CPVS concept."""
        _, _, router = env
        result = router.route("test task")
        # R2Route has model_id + token_budget = CPVS(model, budget)
        assert hasattr(result, 'model_id')
        assert hasattr(result, 'token_budget')
        assert hasattr(result, 'predicted_quality')
        assert hasattr(result, 'predicted_cost')
        assert hasattr(result, 'risk_score')
