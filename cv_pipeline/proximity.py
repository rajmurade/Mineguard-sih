"""Flags when a person/Worker bbox is near a car/truck bbox.

NOTE: distances here are in raw *pixels*. For production you would calibrate a
ground plane homography (or use depth measurements) to map pixel distances to
real-world metres before trusting the threshold — the pixel threshold is only a
demo-grade proxy.
"""

from __future__ import annotations

import math


def bbox_center(bbox: list[float]) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def bbox_distance(a: list[float], b: list[float]) -> float:
    ax, ay = bbox_center(a)
    bx, by = bbox_center(b)
    return math.hypot(ax - bx, ay - by)


class ProximityAnalyzer:
    """Matches person-like and vehicle-like detections inside a pixel radius.

    Parameters
    ----------
    threshold_px:
        Maximum center-to-center distance (in pixels) to count as a risk.
    person_classes:
        Class names treated as the person side ("person" from COCO, "Worker"
        from the PPE model).
    vehicle_classes:
        Class names treated as the vehicle side ("car", "truck" from COCO).
    """

    def __init__(
        self,
        threshold_px: int = 120,
        person_classes: tuple[str, ...] = ("person", "Worker"),
        vehicle_classes: tuple[str, ...] = ("car", "truck"),
    ) -> None:
        if threshold_px <= 0:
            raise ValueError("threshold_px must be > 0")
        self.threshold_px = threshold_px
        self.person_classes = person_classes
        self.vehicle_classes = vehicle_classes

    def analyze(self, detections: list[dict]) -> list[dict]:
        """Return proximity pairs ``[{person, vehicle, distance, objects}]``.

        ``objects`` re-tags the person side for the Compliance Engine:
        ``["worker", "heavy_vehicle"]`` when the PPE Worker class matched
        (that combo escalates to CRITICAL), else ``["person", "heavy_vehicle"]``.
        """
        persons = [d for d in detections if d.get("class_name") in self.person_classes]
        vehicles = [d for d in detections if d.get("class_name") in self.vehicle_classes]

        pairs: list[dict] = []
        for person in persons:
            for vehicle in vehicles:
                distance = bbox_distance(person["bbox"], vehicle["bbox"])
                if distance <= self.threshold_px:
                    person_label = "worker" if person["class_name"] == "Worker" else "person"
                    pairs.append(
                        {
                            "person": person,
                            "vehicle": vehicle,
                            "distance": distance,
                            "objects": [person_label, "heavy_vehicle"],
                        }
                    )
        return pairs