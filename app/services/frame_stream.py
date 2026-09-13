"""In-process buffer for the annotated CV frame stream.

The FastAPI app holds the latest annotated JPEG(s) pushed by a running CV
pipeline (``cv_pipeline.streaming.FramePublisher``). ``GET /cv-stream`` serves
them back to the dashboard as a ``multipart/x-mixed-replace`` MJPEG stream and
``GET /cv-stream/status`` lets the frontend choose between the live image and a
"no active feed" placeholder.

The buffer lives at module scope, so the pipeline MUST push to /cv-stream on the
SAME process that serves GET /cv-stream — which is the designed deployment (a
single FastAPI app instance).
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

STALE_AFTER_SECONDS = 5.0  # no frame pushed this long -> treat as inactive
MAX_BACKLOG = 8  # sliding window of JPEGs kept for late subscribers


class FrameBuffer:
    """Thread-safe holder for the most recent annotated frames."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # (seq, ts, jpeg, worker_count)
        self._frames: list[tuple[int, float, bytes, int]] = []
        self._source: str | None = None

    def push(self, jpeg: bytes, source: str = "cv-pipeline", worker_count: int = 0) -> int:
        """Store the newest annotated JPEG; returns its frame sequence number.

        ``worker_count`` is the number of Worker/person detections in that
        frame (the live camera's current worker presence).
        """
        if not jpeg:
            return 0
        with self._lock:
            seq = (self._frames[-1][0] if self._frames else 0) + 1
            self._frames.append((seq, time.time(), jpeg, max(0, worker_count)))
            self._frames = self._frames[-MAX_BACKLOG:]
            self._source = source
            return seq

    def latest(self) -> tuple[int, float, bytes, int] | None:
        with self._lock:
            return self._frames[-1] if self._frames else None

    def snapshot(self) -> dict:
        """Current state, for the frontend's active/placeholder decision."""
        with self._lock:
            last = self._frames[-1] if self._frames else None
            source = self._source
        if last is None:
            return {
                "active": False,
                "source": None,
                "frame_count": 0,
                "last_updated": None,
                "stale": False,
                "current_worker_count": 0,
            }
        age = time.time() - last[1]
        return {
            "active": age <= STALE_AFTER_SECONDS,
            "source": source or "cv-pipeline",
            "frame_count": last[0],
            "last_updated": datetime.fromtimestamp(last[1], tz=timezone.utc),
            "stale": age > STALE_AFTER_SECONDS,
            "current_worker_count": last[3],
        }

    def reset(self) -> None:
        """Clear buffered frames (mainly for tests)."""
        with self._lock:
            self._frames.clear()
            self._source = None


frames = FrameBuffer()