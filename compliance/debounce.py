"""In-memory debounce tracker for CV detections.

Counts qualifying detections per ``(event_type, zone, worker_id)`` inside a
rolling time window using a deque of timestamps. Reduces false positives from
single-frame flickers: an incident is only produced once N detections have
been seen within the last ``window_seconds``.

Fires on the **rising edge only**: once a key reaches the required count it
reports ``True`` exactly once, and stays quiet while the counting continues
above the threshold. It re-arms only after the count drops back below the
threshold (the window slides empty / the violation stops), so a continuous
violation produces one incident instead of a flood per new confirmation frame.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from typing import Hashable


class DebounceTracker:
    def __init__(self, required_detections: int = 3, window_seconds: float = 5.0):
        if required_detections < 1:
            raise ValueError("required_detections must be >= 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        self.required_detections = required_detections
        self.window_seconds = window_seconds
        self._stamps: dict[Hashable, deque[datetime]] = {}
        self._fired: dict[Hashable, bool] = {}

    def update(self, key: Hashable, detection_time: datetime) -> bool:
        """Record one qualifying detection.

        Returns True only on the update that first reaches the required count
        within the sliding window (rising edge), not on subsequent keep-alive
        detections that keep the count above the threshold.
        """
        stamps = self._stamps.setdefault(key, deque())
        cutoff = detection_time - timedelta(seconds=self.window_seconds)

        while stamps and stamps[0] < cutoff:
            stamps.popleft()

        stamps.append(detection_time)

        reached = len(stamps) >= self.required_detections
        fired = self._fired.get(key, False)
        should_fire = reached and not fired
        self._fired[key] = reached  # disarms automatically when count drops
        return should_fire

    def current_count(self, key: Hashable, now: datetime | None = None) -> int:
        """Number of detections currently inside the window for ``key``."""
        stamps = self._stamps.get(key)
        if not stamps:
            return 0
        if now is not None:
            cutoff = now - timedelta(seconds=self.window_seconds)
            while stamps and stamps[0] < cutoff:
                stamps.popleft()
        return len(stamps)

    def is_confirmed(self, key: Hashable) -> bool:
        """True when ``key`` has already reached the threshold and is above it."""
        return self._fired.get(key, False)

    def reset(self, key: Hashable) -> None:
        self._stamps.pop(key, None)
        self._fired.pop(key, None)

    def prune(self, now: datetime, max_idle_seconds: float = 60.0) -> int:
        """Drop keys that have seen no detections for ``max_idle_seconds``."""
        cutoff = now - timedelta(seconds=max_idle_seconds)
        stale = [key for key, stamps in self._stamps.items() if not stamps or stamps[-1] < cutoff]
        for key in stale:
            self._stamps.pop(key, None)
            self._fired.pop(key, None)
        return len(stale)