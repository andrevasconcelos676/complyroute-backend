"""
Motor de Roteamento — ComplyRoute

Avalia as 12 regras em ordem de prioridade e retorna
o subadquirente selecionado com a trilha de decisão completa.
"""

from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core.config import settings
from app.core.exceptions import FraudBlockError, RoutingError

log = structlog.get_logger()


@dataclass
class TransactionContext:
    """Dados de uma transação para avaliação pelo motor de roteamento."""
    method: str                    # credit | debit | pix | boleto
    amount: int                    # em centavos
    installments: int = 1
    card_country: str = "BR"
    fraud_score: int = 100
    primary_status: str = "ok"    # ok | timeout | error
    retries: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleResult:
    """Resultado da avaliação de uma regra."""
    rule_id: int
    name: str
    matched: bool
    action: str | None   # route | block | retry | None
    target: str | None   # nome do subadquirente ou None


@dataclass
class RoutingDecision:
    """Decisão final do motor de roteamento."""
    acquirer: str | None          # subadquirente selecionado (None se bloqueado)
    blocked: bool
    block_reason: str | None
    trail: list[RuleResult]       # trilha de decisão


# ── Definição das 12 regras ───────────────────────────────

RULES: list[dict] = [
    {
        "id": 1,
        "name": "PIX → todos (exceto SafraPay)",
        "condition": lambda ctx: ctx.method == "pix",
        "action": "route",
        "target": "rede",
        "note": "SafraPay excluído por instabilidade no PIX",
    },
    {
        "id": 2,
        "name": "Boleto → bloquear SafraPay",
        "condition": lambda ctx: ctx.method == "boleto",
        "action": "block_acquirer",
        "target": "safrapay",
        "note": "SafraPay não suporta boleto",
    },
    {
        "id": 3,
        "name": "Débito → bloquear OrendaPay",
        "condition": lambda ctx: ctx.method == "debit",
        "action": "block_acquirer",
        "target": "orendapay",
        "note": "OrendaPay não suporta débito",
    },
    {
        "id": 4,
        "name": "Crédito alto valor → Cielo",
        "condition": lambda ctx: ctx.method == "credit" and ctx.amount > 1_000_000,  # R$ 10.000
        "action": "route",
        "target": "cielo",
    },
    {
        "id": 5,
        "name": "Boleto → Asaas (preferencial)",
        "condition": lambda ctx: ctx.method == "boleto",
        "action": "route",
        "target": "asaas",
    },
    {
        "id": 6,
        "name": "PIX → Rede",
        "condition": lambda ctx: ctx.method == "pix",
        "action": "route",
        "target": "rede",
    },
    {
        "id": 7,
        "name": "Débito → Cielo",
        "condition": lambda ctx: ctx.method == "debit",
        "action": "route",
        "target": "cielo",
    },
    {
        "id": 8,
        "name": "Parcelas ≥ 12x → Stone",
        "condition": lambda ctx: ctx.installments >= 12,
        "action": "route",
        "target": "stone",
    },
    {
        "id": 9,
        "name": "Bin internacional → PagSeguro",
        "condition": lambda ctx: ctx.card_country != "BR",
        "action": "route",
        "target": "pagseguro",
        "active": False,   # desativado por padrão
    },
    {
        "id": 10,
        "name": "Score antifraude < 50 → bloquear",
        "condition": lambda ctx: ctx.fraud_score < 50,
        "action": "block",
        "target": None,
    },
    {
        "id": 11,
        "name": "Fallback → GetNet (timeout primário)",
        "condition": lambda ctx: ctx.primary_status == "timeout",
        "action": "route",
        "target": "getnet",
    },
    {
        "id": 12,
        "name": "Retry automático",
        "condition": lambda ctx: ctx.primary_status == "timeout" and ctx.retries < 3,
        "action": "retry",
        "target": None,
    },
]

DEFAULT_ACQUIRER = "cielo"


class RoutingEngine:
    """Motor de roteamento — avalia regras em ordem de prioridade."""

    def evaluate(self, ctx: TransactionContext) -> RoutingDecision:
        trail: list[RuleResult] = []
        acquirer: str | None = None
        blocked = False
        block_reason: str | None = None

        # ── Antifraude primeiro (prioridade máxima, inclusive sobre o override abaixo) ──
        if ctx.fraud_score < 50:
            result = RuleResult(10, "Score antifraude < 50 → bloquear", True, "block", None)
            trail.append(result)
            log.warning("routing.fraud_blocked", score=ctx.fraud_score)
            return RoutingDecision(
                acquirer=None,
                blocked=True,
                block_reason=f"Score antifraude insuficiente ({ctx.fraud_score}/100)",
                trail=trail,
            )

        # ── Override manual (validação/ops, restrito a não-produção) ──
        # metadata.force_acquirer ignora as 12 regras e força o roteamento para um
        # subadquirente específico — usado para validar integrações novas (ex.: Necta)
        # sem alterar o roteamento padrão de ninguém mais. Nunca disponível em produção:
        # não é uma feature para o chamador da API escolher o subadquirente à vontade.
        forced = ctx.metadata.get("force_acquirer")
        if forced and settings.APP_ENV != "production":
            result = RuleResult(0, f"Override manual → {forced}", True, "route", forced)
            log.info("routing.force_acquirer", acquirer=forced)
            return RoutingDecision(acquirer=forced, blocked=False, block_reason=None, trail=[result])

        # ── Avaliar regras em sequência ───────────────────────
        for rule in RULES:
            if rule.get("id") == 10:
                continue   # já avaliado acima

            active = rule.get("active", True)
            matched = False

            try:
                matched = active and rule["condition"](ctx)
            except Exception as e:
                log.error("routing.rule_error", rule_id=rule["id"], error=str(e))

            result = RuleResult(
                rule_id=rule["id"],
                name=rule["name"],
                matched=matched,
                action=rule["action"] if matched else None,
                target=rule.get("target") if matched else None,
            )
            trail.append(result)

            if matched:
                action = rule["action"]

                if action == "block":
                    blocked = True
                    block_reason = rule["name"]
                    break

                if action == "block_acquirer":
                    # Apenas anota que esse acquirer está excluído; continua avaliando
                    continue

                if action == "route" and acquirer is None:
                    acquirer = rule["target"]

                if action == "retry":
                    # Retry é tratado pelo caller; aqui apenas registramos
                    break

        # ── Fallback padrão ───────────────────────────────────
        if not blocked and acquirer is None:
            acquirer = DEFAULT_ACQUIRER
            trail.append(RuleResult(0, f"Fallback padrão → {DEFAULT_ACQUIRER}", True, "route", DEFAULT_ACQUIRER))

        log.info(
            "routing.decision",
            acquirer=acquirer,
            blocked=blocked,
            method=ctx.method,
            amount=ctx.amount,
            fraud_score=ctx.fraud_score,
        )

        return RoutingDecision(
            acquirer=acquirer,
            blocked=blocked,
            block_reason=block_reason,
            trail=trail,
        )


# Singleton
routing_engine = RoutingEngine()
