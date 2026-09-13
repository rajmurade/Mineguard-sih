"""Runs both pretrained YOLO models and merges their detections."""

from __future__ import annotations

import logging

logger = logging.getLogger("cv_pipeline.detector")


class Detector:
    """PPE + proximity detection with a single ``run(frame)`` call.

    - PPE model: ``killuminati1/construction-ppe-yolov8`` from Hugging Face
      (Hard_hat, No-Helmet, Vest, No-Vest, Worker).
    - Proximity model: stock Ultralytics ``yolov8n.pt`` (COCO: person, car, truck…).

    Models load lazily / from injected instances so the class stays unit-testable
    without downloading weights.

    Parameters
    ----------
    model_ppe, model_prox:
        Preloaded YOLO instances (tests inject stubs here).
    mode:
        ``"both"`` run both models every frame; ``"alternate"`` alternate per
        frame (odd frames -> PPE, even frames -> proximity) to save compute on
        modest hardware.
    """

    def __init__(
        self,
        model_ppe=None,
        model_prox=None,
        mode: str = "both",
        conf: float = 0.35,
        imgsz: int = 640,
        device: str | None = None,
    ) -> None:
        if mode not in ("both", "alternate"):
            raise ValueError("mode must be 'both' or 'alternate'")
        self.mode = mode
        self.conf = conf
        self.imgsz = imgsz
        self.device = device
        self._ppe = model_ppe
        self._prox = model_prox

    # ------------------------------------------------------------------
    # model loading (lazy, only when actually used)
    # ------------------------------------------------------------------

    def ppe_model(self):
        if self._ppe is None:
            from huggingface_hub import hf_hub_download
            from ultralytics import YOLO

            logger.info("downloading PPE weights from Hugging Face…")
            weights = hf_hub_download(
                repo_id="killuminati1/construction-ppe-yolov8", filename="best.pt"
            )
            self._ppe = YOLO(weights)
        return self._ppe

    def proximity_model(self):
        if self._prox is None:
            from ultralytics import YOLO

            logger.info("loading stock yolov8n (COCO)…")
            self._prox = YOLO("yolov8n.pt")  # auto-downloads on first use
        return self._prox

    # ------------------------------------------------------------------
    # inference
    # ------------------------------------------------------------------

    def run(self, frame, frame_index: int = 0) -> list[dict]:
        """Detect on one frame. Returns unified detection dicts:
        ``{"class_name", "confidence", "bbox", "model_source"}`` where ``bbox``
        is ``[x1, y1, x2, y2]`` in pixel coordinates.
        """
        detections: list[dict] = []
        run_ppe = self.mode == "both" or (
            self.mode == "alternate" and frame_index % 2 == 1
        )
        run_prox = self.mode == "both" or (
            self.mode == "alternate" and frame_index % 2 == 0
        )
        if run_ppe:
            detections.extend(self._predict(self.ppe_model(), frame, "ppe"))
        if run_prox:
            detections.extend(self._predict(self.proximity_model(), frame, "proximity"))
        return detections

    def _predict(self, model, frame, tag: str) -> list[dict]:
        kwargs = {"source": frame, "conf": self.conf, "imgsz": self.imgsz, "verbose": False}
        if self.device:
            kwargs["device"] = self.device

        results = model.predict(**kwargs)
        out: list[dict] = []
        names = getattr(model, "names", {}) or {}
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            for box in boxes:
                cls_id = int(box.cls[0])
                confidence = float(box.conf[0])
                x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])
                out.append(
                    {
                        "class_name": names.get(cls_id, str(cls_id)),
                        "confidence": confidence,
                        "bbox": [x1, y1, x2, y2],
                        "model_source": tag,
                    }
                )
        return out