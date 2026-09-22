"""
AI-based ball detector (YOLOv5 via torch.hub).

Requirements: `torch` and internet access for the first run to download model weights.

This module exposes `AIBallDetector` with method `detect(image)` where `image`
is a BGR numpy array (as from OpenCV). It returns (x_px, y_px, radius_px) or None.
"""
from typing import Optional, Tuple
import numpy as np
import cv2

try:
    import torch
except Exception as e:
    torch = None


class AIBallDetector:
    def __init__(self, conf_thres: float = 0.35):
        if torch is None:
            raise RuntimeError("Torch is required for AIBallDetector; install torch first")

        # Load YOLOv5 small model from hub (will download on first run)
        self.model = torch.hub.load("ultralytics/yolov5", "yolov5s", pretrained=True)
        self.model.conf = conf_thres
        self.names = self.model.names

    def detect(self, image: np.ndarray) -> Optional[Tuple[int, int, int]]:
        """Detect ball (sports ball class). Returns (x_px, y_px, radius_px) or None."""
        # model accepts BGR numpy images
        results = self.model(image)
        # results.xyxy[0] is a tensor: (x1, y1, x2, y2, conf, cls)
        preds = results.xyxy[0]
        if preds is None or len(preds) == 0:
            return None

        # Find first detection classified as 'sports ball'
        for *box, conf, cls in preds.cpu().numpy():
            cls = int(cls)
            name = self.names.get(cls, str(cls)) if isinstance(self.names, dict) else self.names[cls]
            if name == "sports ball":
                x1, y1, x2, y2 = box[:4]
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)
                r = int(max((x2 - x1), (y2 - y1)) / 2)
                return cx, cy, r

        return None


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ai_ball_detector.py <image-file>")
        sys.exit(1)

    img = cv2.imread(sys.argv[1])
    det = AIBallDetector()
    res = det.detect(img)
    print("Detection:", res)