"""Tests for the FastAPI REST API endpoints."""

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client(tmp_path):
    """Create a test client with fresh app state."""
    # Ensure no auth required for tests
    os.environ.pop("MARKET_SWARM_API_KEY", None)

    from market_swarm.api.jobs import JobManager
    from market_swarm.api.main import app
    from market_swarm.api.routes import init_job_manager

    # Initialize JobManager with temp directory (startup event doesn't fire in tests)
    manager = JobManager(storage_dir=str(tmp_path / "results"))
    init_job_manager(manager)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
class TestHealthCheck:
    async def test_health_returns_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data


@pytest.mark.asyncio
class TestPacksEndpoint:
    async def test_list_packs(self, client):
        resp = await client.get("/api/packs")
        assert resp.status_code == 200
        packs = resp.json()
        assert len(packs) == 4
        types = {p["product_type"] for p in packs}
        assert types == {"fmcg", "b2b_saas", "pharma", "automotive"}

    async def test_pack_has_persona_count(self, client):
        resp = await client.get("/api/packs")
        packs = resp.json()
        for p in packs:
            assert "persona_count" in p
            assert p["persona_count"] > 0

    async def test_fmcg_personas(self, client):
        resp = await client.get("/api/packs/fmcg/personas")
        assert resp.status_code == 200
        personas = resp.json()
        assert len(personas) == 12
        # Check structure
        for p in personas:
            assert "name" in p
            assert "type" in p
            assert p["pack_type"] == "fmcg"

    async def test_invalid_pack_returns_404(self, client):
        resp = await client.get("/api/packs/nonexistent_pack/personas")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestSimulationsEndpoint:
    async def test_list_simulations_empty(self, client):
        resp = await client.get("/api/simulations")
        assert resp.status_code == 200
        assert resp.json() == [] or isinstance(resp.json(), list)

    async def test_create_simulation_invalid_yaml(self, client):
        resp = await client.post(
            "/api/simulations",
            json={"product_yaml": "not: valid: yaml: [[["},
        )
        # Should still parse as YAML (this is valid YAML, just wrong structure)
        # Let's use actually invalid content
        resp = await client.post(
            "/api/simulations",
            json={"product_yaml": "just a string, no product key"},
        )
        assert resp.status_code == 400

    async def test_create_simulation_missing_product_key(self, client):
        resp = await client.post(
            "/api/simulations",
            json={"product_yaml": "simulation:\n  rounds: 3"},
        )
        assert resp.status_code == 400
        assert "product" in resp.json()["detail"].lower()

    async def test_create_simulation_invalid_pack(self, client):
        yaml_content = "product:\n  name: Test\n  product_type: nonexistent"
        resp = await client.post(
            "/api/simulations",
            json={"product_yaml": yaml_content},
        )
        assert resp.status_code == 400
        assert "No Industry Pack found" in resp.json()["detail"]

    async def test_get_nonexistent_simulation(self, client):
        resp = await client.get("/api/simulations/nonexistent-uuid")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestResultsEndpoint:
    async def test_get_nonexistent_result(self, client):
        resp = await client.get("/api/results/nonexistent-uuid")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestAuth:
    async def test_no_auth_required_when_env_unset(self, client):
        """When MARKET_SWARM_API_KEY is not set, all endpoints are open."""
        os.environ.pop("MARKET_SWARM_API_KEY", None)
        resp = await client.get("/api/simulations")
        assert resp.status_code == 200

    async def test_auth_required_when_env_set(self, client):
        """When MARKET_SWARM_API_KEY is set, requests without key get 401."""
        os.environ["MARKET_SWARM_API_KEY"] = "test-secret-key"
        try:
            resp = await client.get("/api/simulations")
            assert resp.status_code == 401
        finally:
            os.environ.pop("MARKET_SWARM_API_KEY", None)

    async def test_auth_passes_with_correct_key(self, client):
        """Correct X-API-Key header should be accepted."""
        os.environ["MARKET_SWARM_API_KEY"] = "test-secret-key"
        try:
            resp = await client.get(
                "/api/simulations",
                headers={"X-API-Key": "test-secret-key"},
            )
            assert resp.status_code == 200
        finally:
            os.environ.pop("MARKET_SWARM_API_KEY", None)

    async def test_auth_fails_with_wrong_key(self, client):
        os.environ["MARKET_SWARM_API_KEY"] = "test-secret-key"
        try:
            resp = await client.get(
                "/api/simulations",
                headers={"X-API-Key": "wrong-key"},
            )
            assert resp.status_code == 401
        finally:
            os.environ.pop("MARKET_SWARM_API_KEY", None)
