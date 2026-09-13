"""Live runner: webcam or RTSP/HTTP(S) stream.

Usage:
    python -m cv_pipeline.run_live \
        --source 0 \
        --api-url http://localhost:8000 \
        --zone "Zone A - Tunnel 1"
"""

from __future__ import annotations

import argparse
import os
import sys

from cv_pipeline.detector import Detector
from cv_pipeline.ingest import HttpEventIngester
from cv_pipeline.pipeline import CVPipeline
from cv_pipeline.proximity import ProximityAnalyzer
from cv_pipeline.runners import add_common_parser_args, configure_logging
from cv_pipeline.streaming import FramePublisher
from cv_pipeline.video_source import VideoSource


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MineGuard live CV capture/ingest")
    parser.add_argument(
        "--source",
        default="0",
        help="Webcam index, rtsp:// or http(s):// URL (default: %(default)s)",
    )
    add_common_parser_args(parser)
    parser.add_argument(
        "--loop",
        action="store_true",
        help=(
            "For FILE sources only: restart playback at the end "
            "(kept here so a stream URL can be swapped for a file path)"
        ),
    )
    return parser.parse_args(argv)


def _resolve_source(raw: str):
    """'0' -> int 0 (webcam index); anything else is handed to VideoSource as-is."""
    if raw.isdigit():
        return int(raw)
    return raw


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.log_level)

    if args.source.startswith(("rtsp://", "http://", "https://")):
        source = args.source
    else:
        source = _resolve_source(args.source)

    video_source = VideoSource(
        source, loop=args.loop, skip_frames=args.skip_frames
    )
    detector = Detector(mode=args.mode, conf=args.conf, imgsz=args.imgsz, device=args.device)
    analyzer = ProximityAnalyzer(threshold_px=args.proximity_threshold)
    ingester = HttpEventIngester(base_url=args.api_url)
    publisher = (
        FramePublisher(base_url=args.stream_url, every=args.stream_skip + 1)
        if args.stream_url
        else None
    )

    pipeline = CVPipeline(
        video_source=video_source,
        detector=detector,
        analyzer=analyzer,
        ingester=ingester,
        zone=args.zone,
        worker_id=args.worker_id,
        evidence_dir=args.evidence_dir,
        save_evidence=not args.no_evidence,
        min_confidence=args.min_confidence,
        show=args.show,
        output_path=args.output,
        frame_sink=publisher.publish_frame if publisher else None,
    )
    try:
        pipeline.run()
    except KeyboardInterrupt:
        pass
    finally:
        pipeline.close()
        if args.show:
            try:
                import cv2

                cv2.destroyAllWindows()
            except ImportError:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())