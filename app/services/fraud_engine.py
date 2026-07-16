"""
Motor de Antifraude — ComplyRoute

Calcula o score de risco (0–100) combinando múltiplos sinais.
Score alto = baixo risco. Score baixo = alto risco.
"""

import hashlib
from dataclasses import dataclass

import structlog

log = structlog.get_logger()


@dataclass
class FraudContext:
    ip_address: str
    device_fingerprint: str | None
    card_bin: str | None
    card_country: str
    customer_document: str
    customer_email: str
    amount: int
    method: str
    billing_zip: str | None = None


@dataclass
class FraudResult:
    score: int                     # 0–100
    signals: dict[str, int]        # contribuição de cada sinal
    blocked: bool
    block_reason: str | None


class FraudEngine:
    """
    Score composto por sinais independentes.
    Cada sinal retorna uma penalidade (0 = sem risco, 100 = risco total).
    O score final é 100 - média_ponderada_das_penalidades.
    """

    async def evaluate(self, ctx: FraudContext) -> FraudResult:
        signals = {}

        # ── Sinal 1: velocidade de IP ─────────────────────────
        # (em produção: consultar Redis para contagem de tentativas)
        ip_penalty = await self._check_ip_velocity(ctx.ip_address)
        signals["ip_velocity"] = ip_penalty

        # ── Sinal 2: device fingerprint ───────────────────────
        fp_penalty = await self._check_device_fingerprint(ctx.device_fingerprint)
        signals["device_fingerprint"] = fp_penalty

        # ── Sinal 3: BIN em lista negra ───────────────────────
        bin_penalty = await self._check_bin_blacklist(ctx.card_bin)
        signals["bin_blacklist"] = bin_penalty

        # ── Sinal 4: país divergente ──────────────────────────
        geo_penalty = self._check_geo_divergence(ctx.card_country, ctx.ip_address)
        signals["geo_divergence"] = geo_penalty

        # ── Sinal 5: valor anômalo ────────────────────────────
        amount_penalty = self._check_amount_anomaly(ctx.amount, ctx.method)
        signals["amount_anomaly"] = amount_penalty

        # ── Cálculo do score ──────────────────────────────────
        weights = {
            "ip_velocity":      0.30,
            "device_fingerprint": 0.20,
            "bin_blacklist":    0.25,
            "geo_divergence":   0.15,
            "amount_anomaly":   0.10,
        }
        weighted_penalty = sum(signals[k] * weights[k] for k in signals)
        score = max(0, min(100, int(100 - weighted_penalty)))

        blocked = score < 50
        block_reason = "Score antifraude insuficiente" if blocked else None

        log.info("fraud.evaluated", score=score, blocked=blocked, signals=signals)

        return FraudResult(score=score, signals=signals, blocked=blocked, block_reason=block_reason)

    # ── Implementações dos sinais ─────────────────────────────

    async def _check_ip_velocity(self, ip: str) -> float:
        """
        Penalidade por velocidade de IP.
        Em produção: contar tentativas no Redis com janela deslizante de 60s.
        """
        # Placeholder: retorna 0 (sem penalidade)
        return 0.0

    async def _check_device_fingerprint(self, fingerprint: str | None) -> float:
        """Penalidade se o fingerprint já foi visto em múltiplas contas."""
        if not fingerprint:
            return 10.0   # penalidade leve por ausência
        # Em produção: consultar banco para contar contas únicas com este fingerprint
        return 0.0

    async def _check_bin_blacklist(self, bin_: str | None) -> float:
        """Penalidade se o BIN está em lista negra."""
        if not bin_:
            return 0.0
        # Em produção: consultar tabela de BINs bloqueados
        return 0.0

    def _check_geo_divergence(self, card_country: str, ip: str) -> float:
        """Penalidade se o país do cartão diverge do país estimado do IP."""
        # Em produção: usar serviço de geolocalização de IP
        # Placeholder: sem penalidade
        return 0.0

    def _check_amount_anomaly(self, amount: int, method: str) -> float:
        """Penalidade se o valor é anômalo para o método."""
        # PIX acima de R$ 20.000 merece atenção extra
        if method == "pix" and amount > 2_000_000:
            return 20.0
        # Crédito em parcela única acima de R$ 30.000
        if method == "credit" and amount > 3_000_000:
            return 10.0
        return 0.0


# Singleton
fraud_engine = FraudEngine()
