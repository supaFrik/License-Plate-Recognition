from functools import lru_cache
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile

import cv2
import numpy as np


BACKEND_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BACKEND_DIR / "src"
CHECKPOINTS_DIR = BACKEND_DIR / "checkpoints"
MAX_VIDEO_FRAMES = 18
MAX_SEQUENTIAL_VIDEO_SCAN_FRAMES = 240


def _ensure_src_path() -> None:
    src_dir = str(SRC_DIR)
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)


@lru_cache(maxsize=1)
def get_plate_recognizer():
    _ensure_src_path()
    from recognizer import PlateRecognizer

    return PlateRecognizer(
        yolo_ckpt=str(CHECKPOINTS_DIR / "detect_best.pt"),
        digit_ckpt=str(CHECKPOINTS_DIR / "digit_best.pth"),
        letter_ckpt=str(CHECKPOINTS_DIR / "letter_best.pth"),
    )


def decode_uploaded_image(file_bytes: bytes):
    image_array = np.frombuffer(file_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    return image


def _build_frame_result(image, plate_number, plate):
    normalized_plate = plate_number.strip().upper() if plate_number else ""
    bbox = None

    if plate:
        (x1, y1), (x2, y2) = plate["landmark"]
        height = plate["height"]
        bbox = {
            "x_min": int(x1),
            "y_min": int(y1 - height / 2),
            "x_max": int(x2),
            "y_max": int(y2 + height / 2),
        }

    return {
        "detected": bool(plate and normalized_plate),
        "plate_number": normalized_plate or None,
        "confidence": float(plate["conf"]) if plate else None,
        "plate_type": plate["label"] if plate else None,
        "bbox": bbox,
        "image_width": int(image.shape[1]),
        "image_height": int(image.shape[0]),
    }


def _detect_candidates_in_frames(frames):
    recognizer = get_plate_recognizer()
    plate_numbers = recognizer.predict_batch(frames)
    _, plates = recognizer.detect_batch(frames)

    results = []
    for index, frame in enumerate(frames):
        plate_number = plate_numbers[index] if index < len(plate_numbers) else ""
        plate = plates[index] if index < len(plates) else None
        results.append(_build_frame_result(frame, plate_number, plate))

    return results


def _pick_best_video_result(frame_results, sampled_indices):
    candidates_by_plate = {}
    for result, frame_index in zip(frame_results, sampled_indices, strict=False):
        if not result["detected"] or not result["plate_number"]:
            continue

        plate_number = result["plate_number"]
        candidate = candidates_by_plate.setdefault(
            plate_number,
            {
                "count": 0,
                "confidence_sum": 0.0,
                "best_confidence": -1.0,
                "best_result": None,
                "best_frame_index": None,
            },
        )
        confidence = float(result["confidence"] or 0.0)
        candidate["count"] += 1
        candidate["confidence_sum"] += confidence
        if confidence > candidate["best_confidence"]:
            candidate["best_confidence"] = confidence
            candidate["best_result"] = result
            candidate["best_frame_index"] = frame_index

    if not candidates_by_plate:
        fallback = frame_results[0]
        return {
            **fallback,
            "selected_frame_index": None,
            "sampled_frames": len(sampled_indices),
            "analyzed_frames": len(frame_results),
            "validation_note": "No valid plate could be confirmed from the sampled video frames.",
        }

    winning_plate, winning_candidate = max(
        candidates_by_plate.items(),
        key=lambda item: (
            item[1]["count"],
            item[1]["best_confidence"],
            item[1]["confidence_sum"] / item[1]["count"],
        ),
    )
    validation_note = (
        f"Validated plate {winning_plate} across {winning_candidate['count']} sampled frames."
        if winning_candidate["count"] > 1
        else f"Selected the highest-confidence frame for plate {winning_plate}."
    )

    return {
        **winning_candidate["best_result"],
        "selected_frame_index": winning_candidate["best_frame_index"],
        "sampled_frames": len(sampled_indices),
        "analyzed_frames": len(frame_results),
        "validation_note": validation_note,
    }


def _sample_video_frames(file_bytes: bytes, filename: str | None = None):
    suffix = Path(filename or "upload.mp4").suffix or ".mp4"
    temp_path = None

    try:
        with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(file_bytes)
            temp_path = Path(temp_file.name)

        capture = cv2.VideoCapture(str(temp_path))
        if not capture.isOpened():
            raise ValueError("Uploaded file is not a valid video.")

        frames = []
        sampled_indices = []
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        if total_frames > 0:
            sample_count = min(total_frames, MAX_VIDEO_FRAMES)
            indices = sorted(
                {
                    int(round(position * (total_frames - 1) / max(sample_count - 1, 1)))
                    for position in range(sample_count)
                }
            )
            for frame_index in indices:
                capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ok, frame = capture.read()
                if ok and frame is not None:
                    frames.append(frame)
                    sampled_indices.append(frame_index)
        else:
            fps = capture.get(cv2.CAP_PROP_FPS) or 0
            frame_stride = max(int(round(fps / 2)), 1) if fps > 0 else 5
            frame_index = 0
            while frame_index < MAX_SEQUENTIAL_VIDEO_SCAN_FRAMES:
                ok, frame = capture.read()
                if not ok:
                    break
                if frame is not None and frame_index % frame_stride == 0:
                    frames.append(frame)
                    sampled_indices.append(frame_index)
                    if len(frames) >= MAX_VIDEO_FRAMES:
                        break
                frame_index += 1

        capture.release()

        if not frames:
            raise ValueError("No readable frames were found in the uploaded video.")
        return frames, sampled_indices
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def detect_plate_in_image(file_bytes: bytes):
    image = decode_uploaded_image(file_bytes)
    if image is None:
        raise ValueError("Uploaded file is not a valid image.")

    result = _detect_candidates_in_frames([image])[0]
    return {
        **result,
        "input_kind": "image",
        "sampled_frames": 1,
        "analyzed_frames": 1,
        "selected_frame_index": 0 if result["detected"] else None,
        "validation_note": "Single image analyzed.",
    }


def detect_plate_in_video(file_bytes: bytes, filename: str | None = None):
    frames, sampled_indices = _sample_video_frames(file_bytes, filename)
    frame_results = _detect_candidates_in_frames(frames)
    return {
        **_pick_best_video_result(frame_results, sampled_indices),
        "input_kind": "video",
    }
