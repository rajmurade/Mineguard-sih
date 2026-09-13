"""MineGuard real-time computer-vision pipeline.

Modular pieces — each swappable/testable independently:

- :class:`cv_pipeline.video_source.VideoSource`   unified frame source (camera / stream / file)
- :class:`cv_pipeline.detector.Detector`          PPE (HF) + proximity (COCO) YOLO detection
- :class:`cv_pipeline.proximity.ProximityAnalyzer` person/vehicle proximity flags
- :class:`cv_pipeline.events.detections_to_events` detection -> compliance event conversion
- :class:`cv_pipeline.pipeline.CVPipeline`        the main frame loop
- :class:`cv_pipeline.ingest.*`                   event delivery (HTTP POST /cv-events)
- :class:`cv_pipeline.streaming.FramePublisher`   optional annotated-frame push (GET /cv-stream)
"""

from cv_pipeline.detector import Detector
from cv_pipeline.events import detections_to_events
from cv_pipeline.ingest import EventIngester, HttpEventIngester
from cv_pipeline.pipeline import CVPipeline, draw_detections
from cv_pipeline.proximity import ProximityAnalyzer
from cv_pipeline.streaming import FramePublisher
from cv_pipeline.video_source import SourceKind, VideoSource

__all__ = [
    "CVPipeline",
    "Detector",
    "EventIngester",
    "FramePublisher",
    "HttpEventIngester",
    "ProximityAnalyzer",
    "SourceKind",
    "VideoSource",
    "detections_to_events",
    "draw_detections",
]