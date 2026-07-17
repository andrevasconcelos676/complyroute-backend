"""Testes de integração — Subadquirentes."""

from app.models.acquirer import Acquirer


async def _seed_acquirer(db_session, **overrides):
    defaults = dict(
        name="cielo",
        display_name="Cielo",
        api_url="https://api.cielo.com.br",
        priority=1,
        is_primary=True,
    )
    defaults.update(overrides)
    acq = Acquirer(**defaults)
    db_session.add(acq)
    await db_session.commit()
    return acq


async def test_list_acquirers_empty(client, auth_headers):
    res = await client.get("/api/v1/acquirers", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == []


async def test_list_acquirers_ordered_by_priority(client, auth_headers, db_session):
    await _seed_acquirer(db_session, name="stone", display_name="Stone", api_url="https://api.stone.com.br", priority=5)
    await _seed_acquirer(db_session, name="rede", display_name="Rede", api_url="https://api.rede.com.br", priority=2)

    res = await client.get("/api/v1/acquirers", headers=auth_headers)
    assert res.status_code == 200
    names = [a["name"] for a in res.json()]
    assert names == ["rede", "stone"]


async def test_get_acquirer_status(client, auth_headers, db_session):
    await _seed_acquirer(db_session, name="pagseguro", display_name="PagSeguro", api_url="https://api.pagseguro.com")

    res = await client.get("/api/v1/acquirers/pagseguro/status", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["name"] == "pagseguro"


async def test_get_acquirer_status_not_found(client, auth_headers):
    res = await client.get("/api/v1/acquirers/inexistente/status", headers=auth_headers)
    assert res.status_code == 404


async def test_acquirers_requires_auth(client):
    res = await client.get("/api/v1/acquirers")
    assert res.status_code == 401
