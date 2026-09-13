"""Unified video source: webcam, live stream, or recorded file.

Same ``read_frame()`` semantics for every source kind; connection drop / loop /
frame-skipping handled here so callers don't care about the transport.
"""

from __future__ import annotations

import enum
import logging
import os
import time

logger = logging.getLogger("cv_pipeline.video_source")


class SourceKind(str, enum.Enum):
    LIVE_CAMERA = "camera"
    LIVE_STREAM = "stream"
    FILE = "file"


def classify_source(source) -> SourceKind:
    """Map a constructor ``source`` value to its kind."""
    if isinstance(source, int):
        if source < 0:
            raise ValueError("webcam index must be >= 0")
        return SourceKind.LIVE_CAMERA
    if isinstance(source, str):
        lowered = source.lower()
        if lowered.startswith(("rtsp://", "http://", "https://")):
            return SourceKind.LIVE_STREAM
        if os.path.exists(source) and os.path.isfile(source):
            return SourceKind.FILE
        raise ValueError(
            f"source '{source}' is neither a live stream URL nor a file path that exists"
        )
    raise TypeError("source must be an int (webcam) or str (URL / file path)")


class VideoSource:
    """Wrap ``cv2.VideoCapture`` behind a uniform frame reader.

    Parameters
    ----------
    source:
        int webcam index, ``rtsp://``/``http(s)://`` stream URL, or a file path.
    loop:
        For files only: restart from frame 0 after the end (default: stop at end).
    skip_frames:
        Return every ``skip_frames + 1``-th frame (0 = process every frame).
    reconnect_attempts:
        For live sources: how many times to re-open after a read drop.
    reconnect_delay:
        Seconds to sleep between reconnects.
    """

    def __init__(
        self,
        source,
        loop: bool = False,
        skip_frames: int = 0,
        reconnect_attempts: int = 5,
        reconnect_delay: float = 2.0,
    ) -> None:
        if skip_frames < 0:
            raise ValueError("skip_frames must be >= 0")
        self.source = source
        self.loop = loop
        self.skip_frames = skip_frames
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.kind = classify_source(source)

        import cv2  # deferred so importing this module stays light

        self._cv2 = cv2
        self._cap = None
        self._frame_index = -1  # raw frames pulled (cv2-side)
        self._returned = 0      # frames returned to the caller
        self._exhausted = False
        self._open()

    def _open(self) -> None:
        import cv2

        if self.kind is SourceKind.FILE:
            self._cap = cv2.VideoCapture(os.fspath(self.source))
            if not self._cap.isOpened():
                raise IOError(f"could not open video file '{self.source}'")
        elif self.kind is SourceKind.LIVE_CAMERA:
            self._cap = cv2.VideoCapture(int(self.source))
        else:
            self._cap = cv2.VideoCapture(str(self.source))

    def read_frame(self):
        """Return the next (skipped/downsampled) frame, or ``None`` at end.

        Live sources transparently attempt reconnects on read failure.
        """
        while not self._exhausted:
            if self._cap is None or not self._cap.isOpened():
                if not self._reopen():
                    return None

            ok, frame = self._cap.read()
            if ok and frame is not None:
                self._frame_index += 1
                if self.skip_frames and (self._frame_index % (self.skip_frames + 1)) != 0:
                    continue  # skip this frame, keep pulling
                self._returned += 1
                return frame

            # A read failed or returned an empty frame.
            if self.kind is SourceKind.FILE:
                if self.loop:
                    self._frame_index = -1
                    self._cap.set(self._cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                self._exhausted = True
                return None

            if not self._reopen():
                self._exhausted = True
                return None

        return None

    def _reopen(self) -> bool:
        """Reconnect a live source with retries. Returns True on success."""
        if self.kind is SourceKind.FILE:
            return False
        for attempt in range(1, self.reconnect_attempts + 1):
            logger.warning(
                "source dropped (attempt %d/%d), reconnecting in %.1fs…",
                attempt,
                self.reconnect_attempts,
                self.reconnect_delay,
            )
            time.sleep(self.reconnect_delay)
            if self._cap is not None:
                self._cap.release()
            self._open()
            if self._cap is not None and self._cap.isOpened():
                logger.info("reconnected to %r", self.source)
                return True
        logger.error("gave up reconnecting %r", self.source)
        return False

    def stream(self):
        """Generator yielding ``(frame_index, frame)`` tuples (0-based index)."""
        while not self._exhausted:
            frame = self.read_frame()
            if frame is None:
                break
            yield self._frame_index, frame

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        self.release()