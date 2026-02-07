"""
Comprehensive test suite for the Smart Commute Optimization API.

Tests cover:
  1. Key loading -- all Azure keys are present and non-empty.
  2. GET  /                       -- root service description.
  3. GET  /navigation/commute/health     -- health-check.
  4. GET  /navigation/commute/config     -- public config + key-status flags.
  5. POST /navigation/commute/optimize   -- validation errors (missing fields).
  6. POST /navigation/commute/optimize   -- LIVE call to Azure Maps Route Matrix API
                                     (Rutgers campus: drive + walk).

Run with:
    cd backend && python -m pytest tests/test_commute.py -v
"""

from __future__ import annotations

import pytest
import pytest_asyncio
import httpx

# ADAPTED IMPORT: 'backend.app' -> 'main'
from main import app
# ADAPTED IMPORT: 'backend.config' -> 'config.settings'
from config.settings import settings


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client():
    """Async test client using httpx ASGITransport."""
    transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# 1. Key loading tests  (sync -- no client needed)
# ---------------------------------------------------------------------------


class TestKeyLoading:
    """Verify all Azure keys loaded from .env at startup."""

    def test_azure_maps_subscription_key_loaded(self):
        assert settings.azure_maps_subscription_key
        assert len(settings.azure_maps_subscription_key) > 5

    def test_azure_maps_client_id_loaded(self):
        assert settings.azure_maps_client_id
        assert "-" in settings.azure_maps_client_id  # UUID format

    def test_azure_maps_base_url_loaded(self):
        assert settings.azure_maps_base_url == "https://atlas.microsoft.com"

    def test_azure_communication_connection_string_loaded(self):
        assert settings.azure_communication_connection_string
        assert "endpoint=" in settings.azure_communication_connection_string
        assert "accesskey=" in settings.azure_communication_connection_string


# ---------------------------------------------------------------------------
# 2. GET /  (root)
# ---------------------------------------------------------------------------


class TestRoot:
    @pytest.mark.asyncio
    async def test_root_returns_service_info(self, client: httpx.AsyncClient):
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        # Main app might validly return different root info, but checking connectivity
        assert "status" in data or "message" in data


# ---------------------------------------------------------------------------
# 3. GET /navigation/commute/health
# ---------------------------------------------------------------------------


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_returns_200(self, client: httpx.AsyncClient):
        resp = await client.get("/navigation/commute/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["service"] == "smart-commute-optimization"
        assert "timestamp" in data


# ---------------------------------------------------------------------------
# 4. GET /navigation/commute/config
# ---------------------------------------------------------------------------


class TestConfig:
    @pytest.mark.asyncio
    async def test_config_returns_client_id(self, client: httpx.AsyncClient):
        resp = await client.get("/navigation/commute/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["azure_maps_client_id"] == settings.azure_maps_client_id
        assert data["azure_maps_base_url"] == "https://atlas.microsoft.com"

    @pytest.mark.asyncio
    async def test_config_keys_all_configured(self, client: httpx.AsyncClient):
        resp = await client.get("/navigation/commute/config")
        data = resp.json()
        ks = data["keys_configured"]
        assert ks["azure_maps_subscription_key"] is True
        assert ks["azure_maps_client_id"] is True
        assert ks["azure_communication_connection_string"] is True


# ---------------------------------------------------------------------------
# 5. POST /navigation/commute/optimize  -- validation errors
# ---------------------------------------------------------------------------


class TestOptimizeValidation:
    @pytest.mark.asyncio
    async def test_missing_body_returns_422(self, client: httpx.AsyncClient):
        resp = await client.post("/navigation/commute/optimize")
        assert resp.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_missing_origin_returns_422(self, client: httpx.AsyncClient):
        resp = await client.post(
            "/navigation/commute/optimize",
            json={
                "destination": {"latitude": 40.5, "longitude": -74.4},
                "transitionPoints": [
                    {"latitude": 40.51, "longitude": -74.45}
                ],
            },
        )
        assert resp.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_missing_transition_points_returns_422(
        self, client: httpx.AsyncClient
    ):
        resp = await client.post(
            "/navigation/commute/optimize",
            json={
                "origin": {"latitude": 40.5, "longitude": -74.4},
                "destination": {"latitude": 40.52, "longitude": -74.46},
            },
        )
        assert resp.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_empty_transition_points_returns_422(
        self, client: httpx.AsyncClient
    ):
        resp = await client.post(
            "/navigation/commute/optimize",
            json={
                "origin": {"latitude": 40.5, "longitude": -74.4},
                "destination": {"latitude": 40.52, "longitude": -74.46},
                "transitionPoints": [],
            },
        )
        assert resp.status_code in (400, 422)


# ---------------------------------------------------------------------------
# 6. POST /navigation/commute/optimize  -- LIVE Azure Maps call
# ---------------------------------------------------------------------------


class TestOptimizeLive:
    """Hit the real Azure Maps Route Matrix API with your subscription key.

    Uses Rutgers University campus coordinates:
      - Origin:       Rutgers Student Center  (40.5008, -74.4474)
      - Destination:  Scott Hall              (40.4986, -74.4479)
      - Transition A: Lot 26                  (40.5018, -74.4512)
      - Transition B: Lot 30                  (40.4997, -74.4500)
    """

    PAYLOAD = {
        "origin": {"latitude": 40.5008, "longitude": -74.4474},
        "destination": {"latitude": 40.4986, "longitude": -74.4479},
        "transitionPoints": [
            {"latitude": 40.5018, "longitude": -74.4512, "label": "Lot 26"},
            {"latitude": 40.4997, "longitude": -74.4500, "label": "Lot 30"},
        ],
    }

    @pytest.mark.asyncio
    async def test_optimize_returns_valid_result(
        self, client: httpx.AsyncClient
    ):
        resp = await client.post("/navigation/commute/optimize", json=self.PAYLOAD)
        assert resp.status_code == 200, (
            f"Expected 200 but got {resp.status_code}: {resp.text}"
        )
        data = resp.json()

        # Top-level shape
        assert data["success"] is True
        result = data["data"]
        assert "origin" in result
        assert "destination" in result
        assert "best" in result
        assert "candidates" in result

    @pytest.mark.asyncio
    async def test_optimize_best_has_valid_times(
        self, client: httpx.AsyncClient
    ):
        resp = await client.post("/navigation/commute/optimize", json=self.PAYLOAD)
        assert resp.status_code == 200
        best = resp.json()["data"]["best"]

        assert best["total_travel_time_in_seconds"] > 0
        assert best["total_length_in_meters"] > 0
        assert best["drive_leg"]["travel_time_in_seconds"] > 0
        assert best["walk_leg"]["travel_time_in_seconds"] > 0

    @pytest.mark.asyncio
    async def test_optimize_candidates_sorted_ascending(
        self, client: httpx.AsyncClient
    ):
        resp = await client.post("/navigation/commute/optimize", json=self.PAYLOAD)
        assert resp.status_code == 200
        candidates = resp.json()["data"]["candidates"]

        times = [c["total_travel_time_in_seconds"] for c in candidates]
        assert times == sorted(times), "Candidates should be sorted by total time"

    @pytest.mark.asyncio
    async def test_optimize_best_is_first_candidate(
        self, client: httpx.AsyncClient
    ):
        resp = await client.post("/navigation/commute/optimize", json=self.PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["best"] == data["candidates"][0]

    @pytest.mark.asyncio
    async def test_optimize_candidates_have_labels(
        self, client: httpx.AsyncClient
    ):
        resp = await client.post("/navigation/commute/optimize", json=self.PAYLOAD)
        assert resp.status_code == 200
        candidates = resp.json()["data"]["candidates"]
        labels = {c["label"] for c in candidates}
        assert "Lot 26" in labels
        assert "Lot 30" in labels
