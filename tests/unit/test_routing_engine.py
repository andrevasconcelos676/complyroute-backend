"""Testes unitários — Motor de Roteamento."""

import pytest
from app.services.routing_engine import RoutingEngine, TransactionContext


@pytest.fixture
def engine():
    return RoutingEngine()


def test_pix_routes_to_rede(engine):
    ctx = TransactionContext(method="pix", amount=10000, fraud_score=90)
    decision = engine.evaluate(ctx)
    assert not decision.blocked
    assert decision.acquirer == "rede"


def test_boleto_routes_to_asaas(engine):
    ctx = TransactionContext(method="boleto", amount=5000, fraud_score=85)
    decision = engine.evaluate(ctx)
    assert not decision.blocked
    assert decision.acquirer == "asaas"


def test_high_value_credit_routes_to_cielo(engine):
    ctx = TransactionContext(method="credit", amount=1_500_000, fraud_score=90)
    decision = engine.evaluate(ctx)
    assert not decision.blocked
    assert decision.acquirer == "cielo"


def test_long_installments_routes_to_stone(engine):
    ctx = TransactionContext(method="credit", amount=50000, installments=12, fraud_score=80)
    decision = engine.evaluate(ctx)
    assert not decision.blocked
    assert decision.acquirer == "stone"


def test_low_fraud_score_blocks_transaction(engine):
    ctx = TransactionContext(method="credit", amount=10000, fraud_score=30)
    decision = engine.evaluate(ctx)
    assert decision.blocked
    assert decision.acquirer is None
    assert "antifraude" in decision.block_reason.lower()


def test_timeout_routes_to_getnet(engine):
    ctx = TransactionContext(method="credit", amount=10000, fraud_score=80, primary_status="timeout")
    decision = engine.evaluate(ctx)
    assert not decision.blocked
    assert decision.acquirer == "getnet"


def test_debit_routes_to_cielo(engine):
    ctx = TransactionContext(method="debit", amount=20000, fraud_score=90)
    decision = engine.evaluate(ctx)
    assert not decision.blocked
    assert decision.acquirer == "cielo"


def test_force_acquirer_override_routes_directly(engine, monkeypatch):
    from app.services import routing_engine as routing_engine_module
    monkeypatch.setattr(routing_engine_module.settings, "APP_ENV", "development")

    ctx = TransactionContext(method="pix", amount=10000, fraud_score=90, metadata={"force_acquirer": "necta"})
    decision = engine.evaluate(ctx)
    assert not decision.blocked
    assert decision.acquirer == "necta"


def test_force_acquirer_override_disabled_in_production(engine, monkeypatch):
    from app.services import routing_engine as routing_engine_module
    monkeypatch.setattr(routing_engine_module.settings, "APP_ENV", "production")

    ctx = TransactionContext(method="pix", amount=10000, fraud_score=90, metadata={"force_acquirer": "necta"})
    decision = engine.evaluate(ctx)
    assert not decision.blocked
    assert decision.acquirer == "rede"  # regra normal de PIX, override ignorado


def test_force_acquirer_override_does_not_bypass_fraud_block(engine, monkeypatch):
    from app.services import routing_engine as routing_engine_module
    monkeypatch.setattr(routing_engine_module.settings, "APP_ENV", "development")

    ctx = TransactionContext(method="pix", amount=10000, fraud_score=10, metadata={"force_acquirer": "necta"})
    decision = engine.evaluate(ctx)
    assert decision.blocked
    assert decision.acquirer is None


def test_decision_has_trail(engine):
    ctx = TransactionContext(method="pix", amount=10000, fraud_score=90)
    decision = engine.evaluate(ctx)
    assert len(decision.trail) > 0
