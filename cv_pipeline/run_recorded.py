"""Recorded runner: process a local video file through the same pipeline.

Usage:
    python -m cv_pipeline.run_recorded \
        --file path/to/video.mp4 \
        --api-url http://localhost:8000 \
        --loop
"""

from __future__ import annotations

import argparse
import sys

from cv_pipeline.detector import Detector
from cv_pipeline.ingest import HttpEventIngester
from cv_pipeline.pipeline import CVPipeline
from cv_pipeline.proximity import ProximityAnalyzer
from cv_pipeline.runners import add_common_parser_args, configure_logging
from cv_pipeline.streaming import FramePublisher
from cv_pipeline.video_source import VideoSource


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MineGuard recorded-file CV processing")
    parser.add_argument("--file", required=True, help="Path to the video file to process")
    add_common_parser_args(parser)
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Restart the file at the end instead of stopping",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.log_level)

    video_source = VideoSource(
        args.file, loop=args.loop, skip_frames=args.skip_frames
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