"""Shared argparse helpers for the run_live / run_recorded entry points."""

from __future__ import annotations

import argparse
import logging


def add_common_parser_args(parser: argparse.ArgumentParser) -> None:
    """Options shared by both runners (kept in one place)."""
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Base URL of the MineGuard API (default: %(default)s)",
    )
    parser.add_argument(
        "--zone",
        default="Zone A - Tunnel 1",
        help="Zone label attached to every event (default: %(default)s)",
    )
    parser.add_argument(
        "--worker-id",
        type=int,
        default=None,
        help="Staff ID the CV station is attributed to (default: none)",
    )
    parser.add_argument(
        "--skip-frames",
        type=int,
        default=0,
        help="Process every Nth+1 frame (0 = every frame)",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.35,
        help="YOLO confidence threshold (default: %(default)s)",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="Extra detections filter applied in the pipeline (default: %(default)s)",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="YOLO inference size (default: %(default)s)",
    )
    parser.add_argument(
        "--mode",
        choices=("both", "alternate"),
        default="both",
        help="Run both models per frame or alternate odd/even frames",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="PyTorch device override (e.g. 'cpu', '0'; default: ultralytics auto)",
    )
    parser.add_argument(
        "--proximity-threshold",
        type=int,
        default=120,
        help="Max pixel distance for a proximity risk (default: %(default)s)",
    )
    parser.add_argument(
        "--evidence-dir",
        default="evidence",
        help="Folder that receives JPEG evidence frames (default: %(default)s)",
    )
    parser.add_argument("--no-evidence", action="store_true", help="Disable saving evidence frames")
    parser.add_argument("--show", action="store_true", help="Display frames with cv2.imshow")
    parser.add_argument(
        "--output",
        default=None,
        help="Write the annotated stream to this video file (e.g. out.mp4)",
    )
    parser.add_argument(
        "--stream-url",
        default="",
        help=(
            "Backend URL to push ANNOTATED frames to for the dashboard's live feed. "
            "Give the BASE URL, e.g. http://localhost:8000 (frames go to "
            "POST http://localhost:8000/cv-stream); the full "
            "http://localhost:8000/cv-stream endpoint is also accepted. "
            "Empty = disabled (default: %(default)r)"
        ),
    )
    parser.add_argument(
        "--stream-skip",
        type=int,
        default=0,
        help="Publish every Nth+1 annotated frame to the live feed (0 = every frame)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging verbosity (default: %(default)s)",
    )


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )