"""The main CV frame loop: pull -> detect -> analyze -> send -> annotate."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from cv_pipeline.events import EVENT_DIR_NAMES, detections_to_events
from cv_pipeline.proximity import ProximityAnalyzer
from cv_pipeline.video_source import VideoSource

logger = logging.getLogger("cv_pipeline.pipeline")

# Class labels that count as a detected worker: the PPE model's "Worker" and
# the proximity (COCO) model's "person".
WORKER_CLASS_NAMES = frozenset({"Worker", "person"})


def count_detected_workers(detections: list[dict]) -> int:
    """How many distinct Worker/person boxes are visible in *detections*."""
    return sum(1 for d in detections if d.get("class_name") in WORKER_CLASS_NAMES)


def draw_detections(frame, detections: list[dict]) -> None:
    """Draw bboxes + labels onto *frame* in place (colored per model source).

    Note: the ProximityAnalyzer does not auto-enter; we annotate directly.
    """
    try:
        import cv2
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("opencv-python is required for draw_detections") from exc

    for det in detections:
        color = (0, 0, 255) if det["model_source"] == "ppe" else (0, 255, 255)
        x1, y1, x2, y2 = (int(v) for v in det["bbox"])
        label = f"{det['class_name']} {det['confidence']:.2f}"
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            frame,
            label,
            (x1, max(y1 - 6, 0)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
            cv2.LINE_AA,
        )


class CVPipeline:
    """End-to-end loop shared by the live and recorded runners.

    Parameters
    ----------
    video_source:
        A :class:`VideoSource` (or anything with ``read_frame()/release()``).
    detector, analyzer, ingester:
        The pipeline stages (see package modules).
    zone:
        Zone label sent on every event (e.g. ``"Zone A - Tunnel 1"``).
    worker_id:
        Optional staff ID the CV station is attributed to (may be ``None``).
    evidence_dir:
        Folder where JPEG evidence frames are saved.
    save_evidence:
        Whether to actually persist evidence frames (useful to disable in tests).
    min_confidence:
        Drop detections below this confidence before analysis (extra filter on
        top of the model's own ``conf``).
    show:
        If true, display frames with ``cv2.imshow``.
    output_path:
        Optional file to write the annotated stream to (skipped when ``None``).
    frame_sink:
        Optional callable receiving the *annotated* frame ndarray after each
        loop iteration, e.g. ``frame_sink(frame, worker_count=N)`` (a
        :class:`cv_pipeline.streaming.FramePublisher` pushed to the dashboard's
        live feed). ``None`` disables it.
    """

    def __init__(
        self,
        video_source: VideoSource,
        detector,
        analyzer: ProximityAnalyzer,
        ingester,
        zone: str,
        worker_id: int | None = None,
        evidence_dir: str = "evidence",
        save_evidence: bool = True,
        min_confidence: float = 0.0,
        show: bool = False,
        output_path: str | None = None,
        frame_sink=None,
    ) -> None:
        self.video_source = video_source
        self.detector = detector
        self.analyzer = analyzer
        self.ingester = ingester
        self.zone = zone
        self.worker_id = worker_id
        self.evidence_dir = Path(evidence_dir)
        self.save_evidence = save_evidence
        self.min_confidence = min_confidence
        self.show = show
        self.output_path = output_path
        self.frame_sink = frame_sink
        self._writer = None
        self._fps_window: list[float] = []

    # ------------------------------------------------------------------
    # evidence frames
    # ------------------------------------------------------------------

    def save_evidence_frame(self, frame, event_type: str, frame_index: int) -> str | None:
        """Persist a JPEG of *frame*; returns its path or ``None``.

        The returned path is POSIX-style and relative to the current working
        directory when the evidence dir lives under it (e.g.
        ``evidence/no-vest/20260712-...frame000001.jpg``), so the same string
        resolves both on the host and inside the API container against the
        mounted ``/app/evidence`` volume. Falls back to an absolute path when
        the evidence dir is outside the cwd.
        """
        if not self.save_evidence:
            return None
        try:
            import cv2
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("opencv-python is required to save evidence") from exc

        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        folder = EVENT_DIR_NAMES.get(event_type, event_type)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S%f")[:-3]
        path = self.evidence_dir / folder / f"{stamp}-frame{frame_index:06d}.jpg"
        path.parent.mkdir(parents=True, exist_ok=True)
        ok = cv2.imwrite(str(path), frame)
        if not ok:
            logger.warning("failed writing evidence frame %s", path)
            return None
        resolved = path.resolve()
        try:
            return resolved.relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            return resolved.as_posix()

    def _latest_events(self, events: list[dict]) -> list[dict]:
        """Collapse repeated detections of the same event_type to one event/frame."""
        seen: dict[str, dict] = {}
        for event in events:
            key = event["event_type"]
            if key not in seen:
                seen[key] = event
        return list(seen.values())

    # ------------------------------------------------------------------
    # the loop
    # ------------------------------------------------------------------

    def run(self, max_frames: int | None = None) -> int:
        """Process frames until the source ends. Returns total frames processed."""
        counted = 0
        while True:
            started = time.perf_counter()
            frame = self.video_source.read_frame()
            if frame is None:
                break
            self._track_fps(started)

            detections = self.detector.run(frame, counted)
            if self.min_confidence:
                detections = [
                    d for d in detections if d.get("confidence", 0.0) >= self.min_confidence
                ]

            events = detections_to_events(
                detections,
                zone=self.zone,
                analyzer=self.analyzer,
                worker_id=self.worker_id,
            )
            for event in self._latest_events(events):
                path = self.save_evidence_frame(frame, event["event_type"], counted)
                if path:
                    event["evidence_frame_path"] = path

            if events:
                self.ingester.send_events(self._latest_events(events))

            self._annotate(frame, detections)
            if self.frame_sink is not None:
                try:
                    self.frame_sink(frame, worker_count=count_detected_workers(detections))
                except Exception as exc:  # a broken sink must not stop the loop
                    logger.warning("frame sink failed: %s", exc)
            if self.show:
                try:
                    import cv2

                    cv2.imshow("MineGuard CV", frame)
                    if cv2.waitKey(1) & 0xFF in (27, ord("q")):  # Esc / q
                        break
                except ImportError:  # pragma: no cover
                    logger.warning("--show requires opencv-python")

            counted += 1
            if max_frames is not None and counted >= max_frames:
                break

        logger.info(
            "processed %d frames via %s source, sent %d event(s)",
            counted,
            self.video_source.kind.value,
            self.ingester.sent,
        )
        self._close_annotated_output()
        return counted

    def _annotate(self, frame, detections: list[dict]) -> None:
        try:
            import cv2
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("opencv-python is required") from exc
        draw_detections(frame, detections)
        if self.output_path:
            if self._writer is None:
                h, w = frame.shape[:2]
                self._writer = cv2.VideoWriter(
                    self.output_path,
                    cv2.VideoWriter_fourcc(*"mp4v"),
                    20.0,
                    (w, h),
                )
            if self._writer is not None:
                self._writer.write(frame)

    def _close_annotated_output(self) -> None:
        if self._writer is not None:
            self._writer.release()
            self._writer = None

    def close(self) -> None:
        self._close_annotated_output()
        self.video_source.release()

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ------------------------------------------------------------------
    # misc
    # ------------------------------------------------------------------

    def _track_fps(self, started: float) -> None:
        import time as _time

        self._fps_window.append(_time.perf_counter() - started)
        if len(self._fps_window) > 60:
            self._fps_window.pop(0)
        fps = len(self._fps_window) / sum(self._fps_window) if self._fps_window else 0.0
        if len(self._fps_window) % 30 == 0:
            logger.info("fps=%.1f", fps)