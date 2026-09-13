"""Optional annotated-frame publishing (MJPEG) to the MineGuard backend.

The pipeline stays fully functional without this module: frame publishing is
opt-in via ``--stream-url`` and simply POSTs JPEG-encoded *annotated* frames to
``POST {base_url}/cv-stream``. The FastAPI app serves those frames back to the
dashboard as a ``multipart/x-mixed-replace`` stream at ``GET /cv-stream``, which
``LiveFeedPanel.jsx`` shows through a plain ``<img src="/cv-stream">``.

For anything to be visible on the dashboard the CV pipeline must be actively
running (``python -m cv_pipeline.run_live`` or ``run_recorded``) AND pointed at
this stream endpoint, i.e. launched with ``--stream-url http://localhost:8000``.
"""

from __future__ import annotations

import logging
from urllib.parse import urlsplit

logger = logging.getLogger("cv_pipeline.streaming")

_requests = None  # lazy-loaded HTTP transport (also the test-injection seam)


def _get_requests():
    global _requests
    if _requests is None:
        import requests as _requests
    return _requests


def _stream_endpoint(base_url: str) -> str:
    """Return the full ``.../cv-stream`` POST target, tolerating both forms.

    ``base_url`` may be the backend origin (``http://localhost:8000``) *or* the
    full endpoint (``http://localhost:8000/cv-stream``) — the suffix is only
    appended when missing, so it can never be doubled.
    """
    url = base_url.rstrip("/")
    parts = urlsplit(url)
    if parts.path.rstrip("/").endswith("/cv-stream"):
        return url
    return f"{url}/cv-stream"


class FramePublisher:
    """Encodes annotated frames as JPEG and pushes them to the backend.

    Parameters
    ----------
    base_url:
        Backend URL the annotated frames are posted to. Either the base
        (``http://localhost:8000`` -> ``POST http://localhost:8000/cv-stream``)
        or the already-complete endpoint
        (``http://localhost:8000/cv-stream``, used as-is). The ``--stream-url``
        runner flag and the dashboard's example use the BASE form.
    timeout:
        Per-request timeout; short so a dead backend can't stall the frame loop.
    every:
        Publish every Nth annotated frame (1 = every frame). Lets a fast camera
        be cheaply throttled toward the MJPEG stream's frame rate.
    quality:
        JPEG encode quality (0-100) for the stream frames.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 2.0,
        every: int = 1,
        quality: int = 80,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.every = max(1, int(every))
        self.quality = quality
        self._count = 0
        self.posted = 0
        self._consecutive_failures = 0

    def publish_frame(
        self, frame, worker_count: int = 0
    ) -> None:
        """Encode *frame* (annotated BGR ndarray) and POST it to the backend.

        ``worker_count`` is the number of Worker/person detections visible in
        the frame; it is forwarded to the backend as a header so ``GET
        /cv-stream/status`` can expose the live camera count.
        """
        try:
            import cv2
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("opencv-python is required to publish frames") from exc

        self._count += 1
        if self._count % self.every != 0:
            return

        ok, jpeg = cv2.imencode(
            ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.quality]
        )
        if not ok:
            return
        self._post(jpeg.tobytes(), worker_count)

    def _post(self, jpeg: bytes, worker_count: int = 0) -> None:
        http = _get_requests()
        try:
            resp = http.post(
                _stream_endpoint(self.base_url),
                data=jpeg,
                headers={
                    "Content-Type": "image/jpeg",
                    "X-MineGuard-Source": "cv-pipeline",
                    "X-MineGuard-Worker-Count": str(max(0, worker_count)),
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            self.posted += 1
            self._consecutive_failures = 0
        except Exception as exc:  # keep the frame loop alive on network hiccups
            self._consecutive_failures += 1
            if self._consecutive_failures in (1, 10, 50):
                logger.warning(
                    "frame publish failed (%d consecutive): %s",
                    self._consecutive_failures,
                    exc,
                )