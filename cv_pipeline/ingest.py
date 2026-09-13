"""Event delivery: sends compliance events to the MineGuard backend."""

from __future__ import annotations

import abc
import logging

logger = logging.getLogger("cv_pipeline.ingest")

_requests = None  # lazy-loaded HTTP transport (also the test-injection seam)


def _get_requests():
    global _requests
    if _requests is None:
        import requests as _requests
    return _requests


class EventIngester(abc.ABC):
    """Base interface for pushing CV events into the backend."""

    def __init__(self) -> None:
        self.sent = 0

    @abc.abstractmethod
    def send_events(self, events: list[dict]) -> list[dict]:
        """POST a batch of events; returns backend evals (one per event)."""


class HttpEventIngester(EventIngester):
    """Sends events to ``POST {base_url}/cv-events``.

    Parameters
    ----------
    base_url:
        e.g. ``http://localhost:8000`` (env ``MINEGUARD_API``).
    timeout:
        Per-request timeout in seconds.
    """

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 5.0) -> None:
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def send_events(self, events: list[dict]) -> list[dict]:
        if not events:
            return []
        http = _get_requests()

        endpoint = f"{self.base_url}/cv-events"
        responses: list[dict] = []
        for event in events:
            try:
                resp = http.post(endpoint, json=event, timeout=self.timeout)
                resp.raise_for_status()
                responses.append(resp.json())
                self.sent += 1
            except Exception as exc:  # keep the pipeline alive on network hiccups
                logger.error("ingest failed for %s: %s", event.get("event_type"), exc)
        total_evals = len(responses)
        incidents = sum(1 for r in responses if r.get("should_create_incident"))
        logger.info(
            "ingested %d event(s): %d created incident(s), %d response(s)",
            len(events),
            incidents,
            total_evals,
        )
        return responses