"""Tests for the /cv-stream MJPEG feed (in-process frame buffer).

Reuses the shared SQLite harness from test_cv_backend (TestClient + get_db
override). Each test resets the module-level FrameBuffer so results don't leak
across tests.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from test_cv_backend import client  # noqa: F401 (shared engine + override)

from app.routers.cv_stream import _mjpg_generator
from app.services.frame_stream import STALE_AFTER_SECONDS, frames

JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00\x43\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\x09\x09"
    b"\x08\x0a\x0c\x14\x0d\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f"
    b"\x1e\x1d\x1a\x1c\x1c\x20\x24\x2e\x27\x20\x22\x2c\x23\x1c\x1c"
)


@pytest.fixture(autouse=True)
def clean_buffer():
    frames.reset()
    yield
    frames.reset()


def test_ingest_rejects_empty_body():
    response = client.post("/cv-stream", content=b"")
    assert response.status_code == 422


def test_ingest_buffers_jpeg_and_status_flips_to_active():
    assert client.get("/cv-stream/status").json()["active"] is False

    response = client.post("/cv-stream", content=JPEG_BYTES)
    assert response.status_code == 200
    body = response.json()
    assert body["received_bytes"] == len(JPEG_BYTES)
    assert body["frame_count"] == 1

    status = client.get("/cv-stream/status").json()
    assert status["active"] is True
    assert status["stale"] is False
    assert status["source"] == "cv-pipeline"
    assert status["frame_count"] == 1
    assert status["last_updated"] is not None


def test_status_source_override():
    client.post("/cv-stream", content=JPEG_BYTES, params={"source": "cam-01"})
    status = client.get("/cv-stream/status").json()
    assert status["source"] == "cam-01"


def test_status_exposes_current_worker_count_from_header():
    client.post(
        "/cv-stream",
        content=JPEG_BYTES,
        headers={"X-MineGuard-Worker-Count": "3"},
    )
    status = client.get("/cv-stream/status").json()
    assert status["current_worker_count"] == 3


def test_status_worker_count_defaults_to_zero_no_pipeline():
    client.post("/cv-stream", content=JPEG_BYTES)
    status = client.get("/cv-stream/status").json()
    assert status["current_worker_count"] == 0


def test_status_worker_count_ignores_invalid_header():
    client.post(
        "/cv-stream",
        content=JPEG_BYTES,
        headers={"X-MineGuard-Worker-Count": "not-a-number"},
    )
    status = client.get("/cv-stream/status").json()
    assert status["current_worker_count"] == 0
    assert status["active"] is True  # invalid header must not break the frame ingest


def test_status_worker_count_zero_when_no_frames():
    status = client.get("/cv-stream/status").json()
    assert status["active"] is False
    assert status["current_worker_count"] == 0


def test_buffer_turns_stale_when_frames_stop():
    client.post("/cv-stream", content=JPEG_BYTES)
    with patch("app.services.frame_stream.STALE_AFTER_SECONDS", 0.0):
        status = client.get("/cv-stream/status").json()
    assert status["active"] is False
    assert status["stale"] is True
    assert STALE_AFTER_SECONDS > 0


def test_mjpg_generator_emits_boundary_then_frame_bytes():
    frames.push(JPEG_BYTES, source="cam-01")

    async def _run():
        generator = _mjpg_generator()
        part = await generator.__anext__()
        payload = await generator.__anext__()
        await generator.aclose()
        return part, payload

    part, payload = asyncio.run(_run())
    assert part.startswith(b"--mineguard-frame")
    assert b"Content-Type: image/jpeg" in part
    assert f"Content-Length: {len(JPEG_BYTES)}".encode() in part
    assert payload == JPEG_BYTES


def test_mjpg_generator_keeps_last_frame_until_new_ones_arrive():
    frames.push(JPEG_BYTES)

    async def _run():
        generator = _mjpg_generator()
        part1 = await generator.__anext__()   # boundary of frame 1
        payload1 = await generator.__anext__()  # jpeg of frame 1
        await generator.__anext__()          # \r\n separator
        frames.push(JPEG_BYTES, source="cam-01")
        part2 = await generator.__anext__()  # boundary of frame 2 (after ~33ms poll)
        payload2 = await generator.__anext__()  # jpeg of frame 2
        await generator.aclose()
        return part1, payload1, part2, payload2

    part1, payload1, part2, payload2 = asyncio.run(_run())
    assert part1.startswith(b"--mineguard-frame")
    assert payload1 == JPEG_BYTES
    assert part2.startswith(b"--mineguard-frame")
    assert payload2 == JPEG_BYTES


def test_mjpg_generator_initial_wait_then_frame():
    # generator with an empty buffer waits (poll loop) instead of erroring
    async def _run():
        generator = _mjpg_generator()
        task = asyncio.create_task(generator.__anext__())
        await asyncio.sleep(0)
        frames.push(JPEG_BYTES)
        part = await asyncio.wait_for(task, timeout=3)
        await generator.aclose()
        return part

    part = asyncio.run(_run())
    assert part.startswith(b"--mineguard-frame")