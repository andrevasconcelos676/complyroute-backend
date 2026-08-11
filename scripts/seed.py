"""
Script de seed — popula o banco com dados iniciais.
Execute: python scripts/seed.py
"""

import asyncio
from app.db.session import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.acquirer import Acquirer
from app.models.routing_rule import RoutingRule


ACQUIRERS_SEED = [
    {"name":"cielo",     "display_name":"Cielo",     "priority":1,  "is_primary":True,  "traffic_pct":28.0, "supports_debit":True,  "supports_pix":True,  "supports_boleto":True},
    {"name":"rede",      "display_name":"Rede",       "priority":2,  "traffic_pct":18.0, "supports_debit":True,  "supports_pix":True,  "supports_boleto":True},
    {"name":"stone",     "display_name":"Stone",      "priority":3,  "traffic_pct":12.0, "supports_debit":True,  "supports_pix":True,  "supports_boleto":True},
    {"name":"pagseguro", "display_name":"PagSeguro",  "priority":4,  "traffic_pct":7.0,  "supports_debit":True,  "supports_pix":True,  "supports_boleto":True},
    {"name":"getnet",    "display_name":"GetNet",     "priority":5,  "is_fallback":True, "traffic_pct":4.0,  "supports_debit":True,  "supports_pix":True,  "supports_boleto":True},
    {"name":"safrapay",  "display_name":"SafraPay",   "priority":6,  "traffic_pct":2.0,  "supports_debit":True,  "supports_pix":True,  "supports_boleto":False},
    {"name":"zoop",      "display_name":"Zoop",       "priority":7,  "traffic_pct":10.0, "supports_debit":True,  "supports_pix":True,  "supports_boleto":True},
    {"name":"asaas",     "display_name":"Asaas",      "priority":8,  "traffic_pct":11.0, "supports_debit":True,  "supports_pix":True,  "supports_boleto":True},
    {"name":"orendapay", "display_name":"OrendaPay",  "priority":9,  "traffic_pct":8.0,  "supports_debit":False, "supports_pix":True,  "supports_boleto":True},
    {"name":"necta",     "display_name":"Necta Multi-Pay", "priority":10, "traffic_pct":0.0, "supports_debit":False, "supports_pix":True, "supports_boleto":True, "api_url":"https://api-gateway.nectaco.com.br"},
]

RULES_SEED = [
    {"priority":1,  "name":"PIX → Rede",                       "condition":{"field":"method","op":"eq","value":"pix"},                           "action":"route",         "target_acquirer":"rede"},
    {"priority":2,  "name":"Boleto → bloquear SafraPay",        "condition":{"field":"method","op":"eq","value":"boleto"},                        "action":"block_acquirer","target_acquirer":"safrapay"},
    {"priority":3,  "name":"Débito → bloquear OrendaPay",       "condition":{"field":"method","op":"eq","value":"debit"},                         "action":"block_acquirer","target_acquirer":"orendapay"},
    {"priority":4,  "name":"Crédito alto valor → Cielo",        "condition":{"field":"amount","op":"gt","value":1000000},                         "action":"route",         "target_acquirer":"cielo"},
    {"priority":5,  "name":"Boleto → Asaas",                    "condition":{"field":"method","op":"eq","value":"boleto"},                        "action":"route",         "target_acquirer":"asaas"},
    {"priority":6,  "name":"PIX → Rede (fallback)",             "condition":{"field":"method","op":"eq","value":"pix"},                           "action":"route",         "target_acquirer":"rede"},
    {"priority":7,  "name":"Débito → Cielo",                    "condition":{"field":"method","op":"eq","value":"debit"},                         "action":"route",         "target_acquirer":"cielo"},
    {"priority":8,  "name":"Parcelas ≥ 12x → Stone",            "condition":{"field":"installments","op":"gte","value":12},                      "action":"route",         "target_acquirer":"stone"},
    {"priority":9,  "name":"Bin internacional → PagSeguro",     "condition":{"field":"card_country","op":"neq","value":"BR"},                     "action":"route",         "target_acquirer":"pagseguro","is_active":False},
    {"priority":10, "name":"Score < 50 → bloquear",             "condition":{"field":"fraud_score","op":"lt","value":50},                         "action":"block",         "target_acquirer":None},
    {"priority":11, "name":"Fallback GetNet (timeout)",          "condition":{"field":"primary_status","op":"eq","value":"timeout"},              "action":"route",         "target_acquirer":"getnet"},
    {"priority":12, "name":"Retry automático",                   "condition":{"field":"retries","op":"lt","value":3},                             "action":"retry",         "target_acquirer":None},
]


async def seed():
    async with AsyncSessionLocal() as db:
        # Admin user
        admin = User(
            name="Admin Master",
            email="admin@complyroute.com.br",
            password_hash=hash_password("Admin@2026!"),
            role="admin",
            is_active=True,
        )
        db.add(admin)

        # Subadquirentes
        for data in ACQUIRERS_SEED:
            acq = Acquirer(**{
                "api_url": f"https://api.{data['name']}.com.br",
                **data,
            })
            db.add(acq)

        # Regras
        for data in RULES_SEED:
            rule = RoutingRule(**data)
            db.add(rule)

        await db.commit()
        print("✓ Seed concluído.")
        print("  Admin: admin@complyroute.com.br / Admin@2026!")
        print("  Troque a senha imediatamente em produção!")


if __name__ == "__main__":
    asyncio.run(seed())
