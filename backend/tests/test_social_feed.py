"""
Tests for the Social Feed API.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
import httpx

from main import app


@pytest_asyncio.fixture
async def client():
    """Async test client."""
    transport = httpx.ASGITransport(app=app) # type: ignore[arg-type]
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.mark.asyncio
async def test_create_post(client: httpx.AsyncClient):
    """Verify a new post can be created."""
    payload = {
        "user_id": "user123",
        "lot_id": "lotA",
        "content": "Parking lot A is almost full!",
        "type": "news"
    }
    resp = await client.post("/social/feed/post", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "user123"
    assert data["lot_id"] == "lotA"
    assert data["content"] == "Parking lot A is almost full!"
    assert data["type"] == "news"
    assert "post_id" in data


@pytest.mark.asyncio
async def test_create_alert(client: httpx.AsyncClient):
    """Verify an alert can be created."""
    payload = {
        "user_id": "user456",
        "lot_id": "lotB",
        "content": "Tow truck spotted in lot B!",
        "type": "alert"
    }
    resp = await client.post("/social/feed/post", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "alert"


@pytest.mark.asyncio
async def test_get_lot_feed(client: httpx.AsyncClient):
    """Verify retrieval of posts for a specific lot."""
    # Create a post first
    await client.post("/social/feed/post", json={
        "user_id": "user1",
        "lot_id": "lotC",
        "content": "Lot C is nice today."
    })
    
    resp = await client.get("/social/feed/lot/lotC")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["lot_id"] == "lotC"


@pytest.mark.asyncio
async def test_toggle_like(client: httpx.AsyncClient):
    """Verify liking and unliking a post."""
    # Create a post
    post_resp = await client.post("/social/feed/post", json={
        "user_id": "user1",
        "lot_id": "lotD",
        "content": "Like me!"
    })
    post_id = post_resp.json()["post_id"]
    
    # Like
    resp = await client.post(f"/social/feed/like/{post_id}?user_id=tester")
    assert resp.status_code == 200
    assert resp.json()["likes_count"] == 1
    
    # Unlike
    resp = await client.post(f"/social/feed/like/{post_id}?user_id=tester")
    assert resp.status_code == 200
    assert resp.json()["likes_count"] == 0


@pytest.mark.asyncio
async def test_add_reply(client: httpx.AsyncClient):
    """Verify adding a reply to a post."""
    # Create a post
    post_resp = await client.post("/social/feed/post", json={
        "user_id": "user1",
        "lot_id": "lotE",
        "content": "I have a question."
    })
    post_id = post_resp.json()["post_id"]
    
    # Add reply
    reply_payload = {
        "user_id": "user2",
        "content": "Here is the answer."
    }
    resp = await client.post(f"/social/feed/reply/{post_id}", json=reply_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "user2"
    assert data["content"] == "Here is the answer."
    
    # Verify post has the reply
    get_resp = await client.get(f"/social/feed/lot/lotE")
    post = [p for p in get_resp.json() if p["post_id"] == post_id][0]
    assert len(post["replies"]) == 1
    assert post["replies"][0]["content"] == "Here is the answer."


@pytest.mark.asyncio
async def test_get_alerts(client: httpx.AsyncClient):
    """Verify retrieval of active alerts."""
    # Create an alert
    await client.post("/social/feed/post", json={
        "user_id": "user1",
        "lot_id": "lotF",
        "content": "Emergency!",
        "type": "alert"
    })
    
    # Create a regular post
    await client.post("/social/feed/post", json={
        "user_id": "user1",
        "lot_id": "lotF",
        "content": "Normal status.",
        "type": "news"
    })
    
    resp = await client.get("/social/feed/alerts")
    assert resp.status_code == 200
    data = resp.json()
    assert all(p["type"] == "alert" for p in data)
