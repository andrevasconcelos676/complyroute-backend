"""Testes de integração — Conciliação."""

from app.models.transaction import Transaction


async def _seed_txn(db_session, **overrides):
    defaults = dict(
        amount=10000,
        currency="BRL",
        method="pix",
        installments=1,
        status="approved",
        acquirer="rede",
        customer_name="Cliente Teste",
        customer_document="12345678900",
        customer_email="c@example.com",
    )
    defaults.update(overrides)
    txn = Transaction(**defaults)
    db_session.add(txn)
    await db_session.commit()
    return txn


async def test_reconciliation_summary_groups_by_acquirer(client, auth_headers, db_session):
    await _seed_txn(db_session, amount=10000, acquirer="rede", status="approved")
    await _seed_txn(db_session, amount=5000, acquirer="rede", status="approved")
    await _seed_txn(db_session, amount=20000, acquirer="cielo", status="approved")

    # Sem date_from/date_to: o endpoint deve assumir "hoje" (em UTC, igual ao created_at).
    res = await client.get("/api/v1/reconciliation/summary", headers=auth_headers)
    assert res.status_code == 200
    rows = {r["acquirer"]: r for r in res.json()}
    assert rows["rede"]["total_txns"] == 2
    assert rows["rede"]["gross_volume"] == 15000
    assert rows["cielo"]["total_txns"] == 1
    assert rows["cielo"]["gross_volume"] == 20000


async def test_reconciliation_summary_includes_full_day(client, auth_headers, db_session):
    """Regressão: uma transação tarde no dia não pode ser excluída por date_to=mesmo dia
    (created_at tem componente de hora; um filtro '<=' contra a data pura a excluiria)."""
    txn = await _seed_txn(db_session, amount=7500, acquirer="stone")
    created_date = txn.created_at.date().isoformat()

    res = await client.get(
        f"/api/v1/reconciliation/summary?date_from={created_date}&date_to={created_date}",
        headers=auth_headers,
    )
    assert res.status_code == 200
    rows = {r["acquirer"]: r for r in res.json()}
    assert rows["stone"]["total_txns"] == 1
    assert rows["stone"]["gross_volume"] == 7500


async def test_reconciliation_summary_empty_period(client, auth_headers, db_session):
    await _seed_txn(db_session)

    res = await client.get(
        "/api/v1/reconciliation/summary?date_from=2000-01-01&date_to=2000-01-02", headers=auth_headers
    )
    assert res.status_code == 200
    assert res.json() == []


async def test_reconciliation_requires_auth(client):
    res = await client.get("/api/v1/reconciliation/summary")
    assert res.status_code == 401
