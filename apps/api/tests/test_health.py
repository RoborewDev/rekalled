async def test_health_reports_ok_when_database_is_reachable(client):
    response = await client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
