from __future__ import annotations

from dashboard.app import server


class TestHealthCheck:
    def test_healthz_returns_200_when_data_loaded(self):
        client = server.test_client()
        resp = client.get("/healthz")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "ok"
        assert body["report_rows"] > 0

    def test_root_page_renders(self):
        client = server.test_client()
        resp = client.get("/")
        assert resp.status_code == 200
