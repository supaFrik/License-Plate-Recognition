from pathlib import Path
from uuid import uuid4

import cv2


BACKEND_DIR = Path(__file__).resolve().parents[1]
MEDIA_ROOT = BACKEND_DIR / "data" / "detection_captures"
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


def save_detection_capture(image, input_kind: str) -> str:
    extension = ".jpg"
    filename = f"{input_kind}-{uuid4().hex}{extension}"
    output_path = MEDIA_ROOT / filename

    ok = cv2.imwrite(str(output_path), image)
    if not ok:
        raise ValueError("Failed to store the detection capture.")

    return f"/media/detections/{filename}"
