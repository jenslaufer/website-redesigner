"""Tests for the FastAPI REST API."""

import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport

from app import app, jobs, Job


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
def clear_jobs():
    """Clear job store between tests."""
    jobs.clear()
    yield
    jobs.clear()


@pytest.mark.anyio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_post_redesign_valid_url(client):
    with patch("app.process_url_async") as mock_process:
        mock_process.return_value = None
        resp = await client.post("/redesign", json={"url": "https://example.com"})
    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "pending"


@pytest.mark.anyio
async def test_post_redesign_invalid_url(client):
    resp = await client.post("/redesign", json={"url": "not-a-url"})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_post_redesign_missing_url(client):
    resp = await client.post("/redesign", json={})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_get_job_status_pending(client):
    with patch("app.process_url_async") as mock_process:
        mock_process.return_value = None
        resp = await client.post("/redesign", json={"url": "https://example.com"})
    job_id = resp.json()["job_id"]

    resp = await client.get(f"/redesign/{job_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == job_id
    assert data["status"] in ("pending", "processing")


@pytest.mark.anyio
async def test_get_job_status_done(client, tmp_output):
    job_id = "done_job"
    jobs[job_id] = Job(
        job_id=job_id,
        url="https://example.com",
        status="done",
        output_dir=str(tmp_output / "test_job"),
    )

    resp = await client.get(f"/redesign/{job_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "done"
    assert "files" in data
    assert "original.png" in data["files"]
    assert "redesign.png" in data["files"]
    assert "redesign.html" in data["files"]


@pytest.mark.anyio
async def test_get_job_status_failed(client):
    job_id = "failed_job"
    jobs[job_id] = Job(
        job_id=job_id,
        url="https://example.com",
        status="failed",
        error="Connection timeout",
    )

    resp = await client.get(f"/redesign/{job_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failed"
    assert data["error"] == "Connection timeout"


@pytest.mark.anyio
async def test_get_job_not_found(client):
    resp = await client.get("/redesign/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_file_original_png(client, tmp_output):
    job_id = "file_job"
    jobs[job_id] = Job(
        job_id=job_id,
        url="https://example.com",
        status="done",
        output_dir=str(tmp_output / "test_job"),
    )

    resp = await client.get(f"/redesign/{job_id}/original.png")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"


@pytest.mark.anyio
async def test_get_file_redesign_png(client, tmp_output):
    job_id = "file_job2"
    jobs[job_id] = Job(
        job_id=job_id,
        url="https://example.com",
        status="done",
        output_dir=str(tmp_output / "test_job"),
    )

    resp = await client.get(f"/redesign/{job_id}/redesign.png")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"


@pytest.mark.anyio
async def test_get_file_redesign_html(client, tmp_output):
    job_id = "file_job3"
    jobs[job_id] = Job(
        job_id=job_id,
        url="https://example.com",
        status="done",
        output_dir=str(tmp_output / "test_job"),
    )

    resp = await client.get(f"/redesign/{job_id}/redesign.html")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"


@pytest.mark.anyio
async def test_get_file_not_found(client, tmp_output):
    job_id = "file_job4"
    jobs[job_id] = Job(
        job_id=job_id,
        url="https://example.com",
        status="done",
        output_dir=str(tmp_output / "test_job"),
    )

    resp = await client.get(f"/redesign/{job_id}/nonexistent.png")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_file_job_not_found(client):
    resp = await client.get("/redesign/nonexistent/original.png")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_file_disallowed_filename(client, tmp_output):
    """Prevent path traversal."""
    job_id = "file_job5"
    jobs[job_id] = Job(
        job_id=job_id,
        url="https://example.com",
        status="done",
        output_dir=str(tmp_output / "test_job"),
    )

    resp = await client.get(f"/redesign/{job_id}/../../etc/passwd")
    assert resp.status_code in (400, 404, 422)


@pytest.mark.anyio
async def test_get_file_only_allowed_extensions(client, tmp_output):
    """Only serve known file types."""
    job_id = "file_job6"
    jobs[job_id] = Job(
        job_id=job_id,
        url="https://example.com",
        status="done",
        output_dir=str(tmp_output / "test_job"),
    )

    resp = await client.get(f"/redesign/{job_id}/content.json")
    assert resp.status_code == 200
