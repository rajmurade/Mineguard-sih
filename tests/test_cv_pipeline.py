"""Unit tests for the MineGuard CV pipeline module.

Uses stub YOLO models / fake sources so the suite needs no weights, no camera,
and no backend server.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import numpy as np
import pytest

import cv2

from cv_pipeline.detector import Detector
from cv_pipeline.events import detections_to_events
from cv_pipeline.ingest import HttpEventIngester
from cv_pipeline.pipeline import CVPipeline
from cv_pipeline.proximity import ProximityAnalyzer, bbox_distance
from cv_pipeline.streaming import FramePublisher
from cv_pipeline.video_source import SourceKind, VideoSource, classify_source

PPE_NAMES = {0: "Hard_hat", 1: "No-Helmet", 2: "Vest", 3: "No-Vest", 4: "Worker"}
COCO_NAMES = {0: "person", 2: "car", 7: "truck"}


class StubBox:
    def __init__(self, cls_id: int, conf: float, xyxy: list[float]):
        self.cls = [cls_id]
        self.conf = [conf]
        self.xyxy = [xyxy]


class StubResult:
    def __init__(self, boxes: list[StubBox]):
        self.boxes = boxes


class StubModel:
    """Returns a fixed detection group per ``predict`` call."""

    def __init__(self, names: dict, groups):
        self.names = names
        self.groups = groups
        self._calls = 0

    def predict(self, source=None, **kwargs):
        group = self.groups[self._calls % len(self.groups)]
        self._calls += 1
        boxes = [StubBox(d["cls"], d["conf"], d["xyxy"]) for d in group]
        return [StubResult(boxes)]


def det(cls: int, conf: float, xyxy: list[float]) -> dict:
    return {"cls": cls, "conf": conf, "xyxy": xyxy}


# ----------------------------------------------------------------------
# classification of sources
# ----------------------------------------------------------------------


def test_classify_webcam_index():
    assert classify_source(0) is SourceKind.LIVE_CAMERA
    assert classify_source(3) is SourceKind.LIVE_CAMERA


def test_classify_stream_urls():
    assert classify_source("rtsp://cam/1") is SourceKind.LIVE_STREAM
    assert classify_source("https://example.com/stream.m3u8") is SourceKind.LIVE_STREAM


def test_classify_file(tmp_path):
    path = tmp_path / "clip.avi"
    write_avi(path, 2)
    assert classify_source(str(path)) is SourceKind.FILE


def test_classify_rejects_missing_and_bad_types(tmp_path):
    with pytest.raises(ValueError):
        classify_source(str(tmp_path / "nope.avi"))
    with pytest.raises(ValueError):
        classify_source(-1)
    with pytest.raises(TypeError):
        classify_source(None)


# ----------------------------------------------------------------------
# VideoSource (real OpenCV codec round-trip)
# ----------------------------------------------------------------------


def write_avi(path, n_frames: int, size=(320, 240)) -> None:
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, size
    )
    assert writer.isOpened(), "OpenCV VideoWriter failed to open"
    for i in range(n_frames):
        frame = np.full((size[1], size[0], 3), i * 40, dtype=np.uint8)
        writer.write(frame)
    writer.release()


def test_video_source_reads_file_frames(tmp_path):
    path = tmp_path / "clip.avi"
    write_avi(path, 4)
    with VideoSource(str(path)) as source:
        assert source.kind is SourceKind.FILE
        frames = [f for f in source.stream()]
        assert len(frames) == 4
        frame_index, frame = frames[0]
        assert frame_index == 0
        assert frame.shape[1] == 320 and frame.shape[0] == 240


def test_video_source_skip_frames(tmp_path):
    path = tmp_path / "clip.avi"
    write_avi(path, 4)
    source = VideoSource(str(path), skip_frames=1)
    try:
        frames = list(source.stream())
        assert [idx for idx, _ in frames] == [0, 2]
    finally:
        source.release()


def test_video_source_loops_until_exhausted(tmp_path):
    path = tmp_path / "clip.avi"
    write_avi(path, 2)
    source = VideoSource(str(path), loop=True)
    try:
        # with loop=True the source keeps returning frames instead of ending
        read = [source.read_frame() for _ in range(2 * 3)]
        assert all(f is not None for f in read)
    finally:
        source.release()


def test_video_source_requires_existing_file(tmp_path):
    with pytest.raises(ValueError):
        VideoSource(str(tmp_path / "missing.avi"))


# ----------------------------------------------------------------------
# Detector (stub models)
# ----------------------------------------------------------------------


def test_detector_mode_both_runs_each_model():
    ppe = StubModel(PPE_NAMES, [[det(1, 0.9, [0, 0, 10, 10])]])
    prox = StubModel(COCO_NAMES, [[det(0, 0.8, [5, 5, 15, 15])]])
    detector = Detector(model_ppe=ppe, model_prox=prox, mode="both")

    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    results = detector.run(frame, frame_index=0)

    labels = {d["class_name"] for d in results}
    assert labels == {"No-Helmet", "person"}
    sources = {d["model_source"] for d in results}
    assert sources == {"ppe", "proximity"}
    assert ppe._calls == 1 and prox._calls == 1


def test_detector_mode_alternate():
    ppe = StubModel(PPE_NAMES, [[det(3, 0.7, [0, 0, 5, 5])]])
    prox = StubModel(COCO_NAMES, [[det(2, 0.6, [0, 0, 5, 5])]])
    detector = Detector(model_ppe=ppe, model_prox=prox, mode="alternate")

    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    even = detector.run(frame, frame_index=0)  # proximity only
    odd = detector.run(frame, frame_index=1)   # ppe only

    assert [d["class_name"] for d in even] == ["car"]
    assert [d["class_name"] for d in odd] == ["No-Vest"]
    assert ppe._calls == 1 and prox._calls == 1


def test_detector_rejects_bad_mode():
    with pytest.raises(ValueError):
        Detector(mode="sometimes")


# ----------------------------------------------------------------------
# ProximityAnalyzer
# ----------------------------------------------------------------------


def _b(x1, y1, x2, y2):
    return [x1, y1, x2, y2]


def test_bbox_distance():
    assert bbox_distance(_b(0, 0, 10, 10), _b(20, 0, 30, 10)) == 20.0


def test_analyzer_flags_nearby_person_and_truck():
    analyzer = ProximityAnalyzer(threshold_px=150)
    detections = [
        {"class_name": "person", "confidence": 0.9, "bbox": _b(60, 60, 80, 80)},
        {"class_name": "truck", "confidence": 0.8, "bbox": _b(90, 60, 130, 90)},
    ]
    pairs = analyzer.analyze(detections)
    assert len(pairs) == 1
    assert pairs[0]["objects"] == ["person", "heavy_vehicle"]
    assert pairs[0]["distance"] > 0


def test_analyzer_flags_worker_heavy_vehicle_combo():
    analyzer = ProximityAnalyzer(threshold_px=150)
    detections = [
        {"class_name": "Worker", "confidence": 0.85, "bbox": _b(60, 60, 80, 80)},
        {"class_name": "car", "confidence": 0.9, "bbox": _b(80, 60, 120, 90)},
    ]
    pairs = analyzer.analyze(detections)
    assert pairs[0]["objects"] == ["worker", "heavy_vehicle"]


def test_analyzer_ignores_far_detections():
    analyzer = ProximityAnalyzer(threshold_px=50)
    detections = [
        {"class_name": "person", "confidence": 0.9, "bbox": _b(0, 0, 10, 10)},
        {"class_name": "car", "confidence": 0.9, "bbox": _b(500, 500, 520, 520)},
    ]
    assert analyzer.analyze(detections) == []


def test_analyzer_validates_threshold():
    with pytest.raises(ValueError):
        ProximityAnalyzer(threshold_px=0)


# ----------------------------------------------------------------------
# events
# ----------------------------------------------------------------------


def test_no_helmet_maps_to_event():
    events = detections_to_events(
        [{"class_name": "No-Helmet", "confidence": 0.87, "bbox": _b(0, 0, 10, 10)}],
        zone="Zone B - Open Pit",
        analyzer=ProximityAnalyzer(),
        worker_id=7,
        timestamp=datetime(2026, 1, 1, 8, tzinfo=timezone.utc),
    )
    assert len(events) == 1
    event = events[0]
    assert event["event_type"] == "no_helmet"
    assert event["source"] == "cv"
    assert event["confidence"] == 0.87
    assert event["zone"] == "Zone B - Open Pit"
    assert event["worker_id"] == 7


def test_no_vest_and_proximity_in_one_frame():
    analyzer = ProximityAnalyzer(threshold_px=150)
    detections = [
        {"class_name": "No-Vest", "confidence": 0.9, "bbox": _b(0, 0, 10, 10)},
        {"class_name": "Worker", "confidence": 0.8, "bbox": _b(40, 40, 60, 60)},
        {"class_name": "truck", "confidence": 0.7, "bbox": _b(50, 50, 90, 80)},
    ]
    events = detections_to_events(detections, zone="Zone A - Tunnel 1", analyzer=analyzer)
    types = {e["event_type"] for e in events}
    assert types == {"no_vest", "proximity_risk"}
    combo = next(e for e in events if e["event_type"] == "proximity_risk")
    assert combo["objects"] == ["worker", "heavy_vehicle"]
    assert combo["distance_px"] > 0


def test_ignores_benign_detections():
    events = detections_to_events(
        [
            {"class_name": "Hard_hat", "confidence": 0.9, "bbox": _b(0, 0, 10, 10)},
            {"class_name": "Vest", "confidence": 0.9, "bbox": _b(0, 0, 10, 10)},
        ],
        zone="Zone A - Tunnel 1",
        analyzer=ProximityAnalyzer(),
    )
    assert events == []


# ----------------------------------------------------------------------
# HttpEventIngester
# ----------------------------------------------------------------------


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeRequests:
    def __init__(self):
        self.posts = []

    def post(self, url, json=None, timeout=None):
        self.posts.append((url, json))
        return FakeResponse({"should_create_incident": True, "reason": "ok"})


def test_http_ingester_posts_to_cv_events():
    ingester = HttpEventIngester(base_url="http://localhost:8000")
    with patch("cv_pipeline.ingest._requests", new=FakeRequests()) as fake:
        responses = ingester.send_events(
            [
                {"source": "cv", "event_type": "no_helmet", "zone": "Zone A - Tunnel 1"},
                {"source": "cv", "event_type": "fall", "zone": "Zone A - Tunnel 1"},
            ]
        )
    assert len(fake.posts) == 2
    assert fake.posts[0][0] == "http://localhost:8000/cv-events"
    assert responses == [
        {"should_create_incident": True, "reason": "ok"},
        {"should_create_incident": True, "reason": "ok"},
    ]
    assert ingester.sent == 2


def test_http_ingester_noop_on_empty():
    ingester = HttpEventIngester()
    assert ingester.send_events([]) == []


# ----------------------------------------------------------------------
# FramePublisher (annotated-frame push to /cv-stream)
# ----------------------------------------------------------------------


class FakeStreamRequests:
    def __init__(self):
        self.posts = []

    def post(self, url, data=None, headers=None, timeout=None):
        self.posts.append((url, data, headers))
        return FakeResponse({"received_bytes": len(data), "frame_count": 1})


def test_frame_publisher_posts_jpeg_to_cv_stream():
    publisher = FramePublisher(base_url="http://localhost:8000", every=1)
    frame = np.full((80, 80, 3), 120, dtype=np.uint8)
    with patch("cv_pipeline.streaming._requests", new=FakeStreamRequests()) as fake:
        publisher.publish_frame(frame)
    assert len(fake.posts) == 1
    url, data, headers = fake.posts[0]
    assert url == "http://localhost:8000/cv-stream"
    assert data[:2] == b"\xff\xd8"  # JPEG magic
    assert headers["Content-Type"] == "image/jpeg"
    assert publisher.posted == 1


@pytest.mark.parametrize(
    "given,expected",
    [
        ("http://localhost:8000", "http://localhost:8000/cv-stream"),  # base form
        ("http://localhost:8000/", "http://localhost:8000/cv-stream"),
        ("http://localhost:8000/cv-stream", "http://localhost:8000/cv-stream"),  # full form
        ("http://localhost:8000/cv-stream/", "http://localhost:8000/cv-stream"),
    ],
)
def test_frame_publisher_never_double_appends_stream_path(given, expected):
    # regression: --stream-url given as the FULL endpoint used to produce
    # http://localhost:8000/cv-stream/cv-stream -> 404
    publisher = FramePublisher(base_url=given)
    frame = np.zeros((16, 16, 3), dtype=np.uint8)
    with patch("cv_pipeline.streaming._requests", new=FakeStreamRequests()) as fake:
        publisher.publish_frame(frame)
    assert fake.posts[0][0] == expected


def test_frame_publisher_throttles_with_every():
    publisher = FramePublisher(base_url="http://localhost:8000", every=3)
    frame = np.zeros((16, 16, 3), dtype=np.uint8)
    with patch("cv_pipeline.streaming._requests", new=FakeStreamRequests()) as fake:
        for _ in range(3):
            publisher.publish_frame(frame)
    assert len(fake.posts) == 1  # only the 3rd frame was pushed


def test_frame_publisher_survives_backend_errors():
    class ExplodingRequests:
        def post(self, *args, **kwargs):
            raise ConnectionError("backend down")

    publisher = FramePublisher(base_url="http://localhost:8000")
    frame = np.zeros((16, 16, 3), dtype=np.uint8)
    with patch("cv_pipeline.streaming._requests", new=ExplodingRequests()):
        publisher.publish_frame(frame)
    assert publisher.posted == 0
    assert publisher._consecutive_failures == 1


# ----------------------------------------------------------------------
# worker presence count
# ----------------------------------------------------------------------


def test_count_detected_workers():
    from cv_pipeline.pipeline import count_detected_workers

    detections = [
        {"class_name": "Worker", "confidence": 0.85, "bbox": _b(0, 0, 10, 10)},
        {"class_name": "person", "confidence": 0.9, "bbox": _b(20, 0, 30, 10)},
        {"class_name": "truck", "confidence": 0.8, "bbox": _b(40, 0, 50, 10)},
        {"class_name": "No-Helmet", "confidence": 0.7, "bbox": _b(60, 0, 70, 10)},
    ]
    assert count_detected_workers(detections) == 2


def test_frame_publisher_sends_worker_count_header():
    publisher = FramePublisher(base_url="http://localhost:8000", every=1)
    frame = np.zeros((16, 16, 3), dtype=np.uint8)
    with patch("cv_pipeline.streaming._requests", new=FakeStreamRequests()) as fake:
        publisher.publish_frame(frame, worker_count=3)
    headers = fake.posts[0][2]
    assert headers["X-MineGuard-Worker-Count"] == "3"


def test_frame_publisher_sends_zero_worker_count_by_default():
    publisher = FramePublisher(base_url="http://localhost:8000", every=1)
    frame = np.zeros((16, 16, 3), dtype=np.uint8)
    with patch("cv_pipeline.streaming._requests", new=FakeStreamRequests()) as fake:
        publisher.publish_frame(frame)
    headers = fake.posts[0][2]
    assert headers["X-MineGuard-Worker-Count"] == "0"


# ----------------------------------------------------------------------
# full pipeline (real VideoSource + stubs + fake ingester)
# ----------------------------------------------------------------------


class FakeIngester:
    def __init__(self):
        self.sent = 0
        self.payloads: list[dict] = []

    def send_events(self, events):
        self.sent += len(events)
        self.payloads.extend(events)
        return []


def test_pipeline_end_to_end(tmp_path):
    clip = tmp_path / "clip.avi"
    write_avi(clip, 4)

    ppe = StubModel(
        PPE_NAMES,
        [[det(1, 0.9, [40, 40, 80, 80])]],  # No-Helmet every frame
    )
    prox = StubModel(
        COCO_NAMES,
        [
            [
                det(0, 0.85, [40, 40, 70, 70]),  # person near the truck
                det(7, 0.8, [70, 40, 110, 70]),  # truck
            ]
        ],
    )
    detector = Detector(model_ppe=ppe, model_prox=prox, mode="both")

    evidence_dir = tmp_path / "evidence"
    ingester = FakeIngester()
    pipeline = CVPipeline(
        video_source=VideoSource(str(clip)),
        detector=detector,
        analyzer=ProximityAnalyzer(threshold_px=80),
        ingester=ingester,
        zone="Zone A - Tunnel 1",
        worker_id=42,
        evidence_dir=str(evidence_dir),
        save_evidence=True,
    )
    try:
        frames = pipeline.run()
    finally:
        pipeline.close()

    assert frames == 4
    assert ingester.sent == 8  # 2 events/frame (no_helmet + proximity_risk)
    assert ingester.payloads[0]["event_type"] == "no_helmet"
    assert ingester.payloads[1]["event_type"] == "proximity_risk"

    for folder in ("no-helmet", "proximity"):
        files = list((evidence_dir / folder).glob("*.jpg"))
        assert len(files) == 4, folder
        assert files[0].exists()

    # the first event carries an evidence path that resolves on disk
    # (cwd-relative like "evidence/no-vest/..." when under cwd, absolute otherwise)
    ev = next(p for p in ingester.payloads if p["event_type"] == "no_helmet")
    assert ev["evidence_frame_path"]
    assert os.path.exists(ev["evidence_frame_path"])


def test_pipeline_stores_cwd_relative_evidence_path(tmp_path, monkeypatch):
    """The stored evidence path is cwd-relative so it resolves against the
    API container's /app/evidence mount (volume: ./evidence:/app/evidence)."""
    clip = tmp_path / "clip.avi"
    write_avi(clip, 1)

    ppe = StubModel(
        PPE_NAMES,
        [[det(1, 0.9, [40, 40, 80, 80])]],  # No-Helmet every frame
    )
    prox = StubModel(COCO_NAMES, [[]])
    detector = Detector(model_ppe=ppe, model_prox=prox, mode="both")

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    monkeypatch.chdir(run_dir)

    ingester = FakeIngester()
    pipeline = CVPipeline(
        video_source=VideoSource(str(clip)),
        detector=detector,
        analyzer=ProximityAnalyzer(),
        ingester=ingester,
        zone="Zone A - Tunnel 1",
        evidence_dir="evidence",
        save_evidence=True,
    )
    try:
        pipeline.run()
    finally:
        pipeline.close()

    ev = next(p for p in ingester.payloads if p["event_type"] == "no_helmet")
    path = ev["evidence_frame_path"]
    assert path.startswith("evidence/no-helmet/")
    assert path == path.replace("\\", "/")  # POSIX separators
    assert os.path.exists(path)  # cwd-relative lookup within run_dir
    assert os.path.isfile(run_dir / path)


def test_pipeline_min_confidence_filters(tmp_path):
    clip = tmp_path / "clip.avi"
    write_avi(clip, 2)
    ppe = StubModel(PPE_NAMES, [[det(1, 0.4, [40, 40, 80, 80])]])  # low conf
    prox = StubModel(COCO_NAMES, [[det(0, 0.3, [0, 0, 5, 5])]])
    ingester = FakeIngester()
    pipeline = CVPipeline(
        video_source=VideoSource(str(clip)),
        detector=Detector(model_ppe=ppe, model_prox=prox, mode="both"),
        analyzer=ProximityAnalyzer(),
        ingester=ingester,
        zone="Zone A - Tunnel 1",
        min_confidence=0.5,
        save_evidence=False,
    )
    try:
        pipeline.run()
    finally:
        pipeline.close()
    assert ingester.sent == 0  # every detection was below 0.5


def test_pipeline_forwards_annotated_frames_to_frame_sink(tmp_path):
    clip = tmp_path / "clip.avi"
    write_avi(clip, 3)

    class FakePublisher:
        def __init__(self):
            self.received = []

        def publish_frame(self, frame, worker_count=0):
            self.received.append((frame, worker_count))

    publisher = FakePublisher()
    pipeline = CVPipeline(
        video_source=VideoSource(str(clip)),
        detector=Detector(
            model_ppe=StubModel(
                PPE_NAMES, [[det(1, 0.9, [40, 40, 60, 60])]]
            ),  # No-Helmet -> NOT counted
            model_prox=StubModel(COCO_NAMES, [[det(0, 0.8, [5, 5, 15, 15])]]),  # person -> counted
            mode="both",
        ),
        analyzer=ProximityAnalyzer(threshold_px=80),
        ingester=FakeIngester(),
        zone="Zone A - Tunnel 1",
        save_evidence=False,
        frame_sink=publisher.publish_frame,
    )
    try:
        pipeline.run()
    finally:
        pipeline.close()

    assert len(publisher.received) == 3
    assert all(
        f.ndim == 3 and f.shape[2] == 3 for f, _ in publisher.received
    )  # annotated BGR ndarrays
    # one "person" (proximity) per frame -> live worker count of 1 per frame
    assert all(wc == 1 for _, wc in publisher.received)


def test_pipeline_worker_count_reflects_ppe_and_proximity(tmp_path):
    clip = tmp_path / "clip.avi"
    write_avi(clip, 2)

    class FakePublisher:
        def __init__(self):
            self.counts = []

        def publish_frame(self, frame, worker_count=0):
            self.counts.append(worker_count)

    publisher = FakePublisher()
    pipeline = CVPipeline(
        video_source=VideoSource(str(clip)),
        detector=Detector(
            model_ppe=StubModel(PPE_NAMES, [[det(4, 0.9, [40, 40, 60, 60])]]),  # Worker
            model_prox=StubModel(COCO_NAMES, [[det(0, 0.8, [5, 5, 15, 15])]]),  # person
            mode="both",
        ),
        analyzer=ProximityAnalyzer(),
        ingester=FakeIngester(),
        zone="Zone A - Tunnel 1",
        save_evidence=False,
        frame_sink=publisher.publish_frame,
    )
    try:
        pipeline.run()
    finally:
        pipeline.close()

    assert publisher.counts == [2, 2]  # Worker (ppe) + person (proximity)