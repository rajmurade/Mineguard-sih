"""Live annotated-frame stream endpoints.

- ``GET  /cv-stream``        MJPEG (``multipart/x-mixed-replace``) the dashboard
                             points an ``<img src="/cv-stream">`` at.
- ``POST /cv-stream``        Raw-JPEG push from a running CV pipeline (see
                             ``cv_pipeline.streaming.FramePublisher``).  The
                             optional ``X-MineGuard-Worker-Count`` header
                             carries the live camera's current worker count.
- ``GET  /cv-stream/status`` {active, source, frame_count, last_updated, stale,
                             current_worker_count} so the frontend can switch
                             between the live frame and the "no active feed"
                             placeholder and show a live worker count.

No frames can appear until a CV pipeline is actively pushing to the POST
endpoint — see the note in cv_pipeline/streaming.py.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from app.services.frame_stream import frames

router = APIRouter(prefix="/cv-stream", tags=["cv-stream"])

BOUNDARY = "mineguard-frame"
_PART = b"--%b\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n"
_FRAME_GAP_SECONDS = 1.0 / 30.0  # never emit faster than 30 fps
_POLL_SECONDS = 0.05


async def _mjpg_generator():
    """Yield the current frame, then any new ones, until the <img> disconnects.

    Polling every 50ms is cheap and avoids bridging the shared FrameBuffer's
    threading primitives into the async event loop.
    """
    sent_seq = 0
    while True:
        latest = frames.latest()
        if latest is not None and latest[0] > sent_seq:
            seq, _, jpeg, _ = latest
            yield _PART % (BOUNDARY.encode(), len(jpeg))
            yield jpeg
            yield b"\r\n"
            sent_seq = seq
            await asyncio.sleep(_FRAME_GAP_SECONDS)
        else:
            await asyncio.sleep(_POLL_SECONDS)


@router.get("", response_class=StreamingResponse)
def cv_stream():
    """Chunked MJPEG stream of the latest annotated frames."""
    return StreamingResponse(
        _mjpg_generator(),
        media_type=f"multipart/x-mixed-replace; boundary={BOUNDARY}",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("", status_code=200)
async def ingest_frame(request: Request, source: str | None = None):
    """Ingest one raw JPEG body pushed by a CV pipeline."""
    body = await request.body()
    if not body:
        raise HTTPException(status_code=422, detail="empty body — expected a JPEG payload")

    raw_count = request.headers.get("x-mineguard-worker-count")
    try:
        worker_count = int(raw_count) if raw_count else 0
    except ValueError:
        worker_count = 0

    seq = frames.push(
        body,
        source=source or "cv-pipeline",
        worker_count=max(0, worker_count),
    )
    return {"received_bytes": len(body), "frame_count": seq}


@router.get("/status")
def cv_stream_status():
    """How fresh the buffered feed is, for the dashboard UI state."""
    return frames.snapshot()