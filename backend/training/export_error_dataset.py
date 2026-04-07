import argparse
import csv
import shutil
from pathlib import Path

from common import (
    ERROR_REVIEW_ROOT,
    bootstrap_python_paths,
    ensure_directory,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export real detection captures into a review dataset for retraining.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ERROR_REVIEW_ROOT,
        help="Directory where the review dataset should be written.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Maximum number of detections to export.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=None,
        help="Optional minimum final confidence filter.",
    )
    parser.add_argument(
        "--max-confidence",
        type=float,
        default=0.92,
        help="Optional maximum final confidence filter. Lower-confidence detections are useful for review.",
    )
    parser.add_argument(
        "--camera-id",
        type=int,
        default=None,
        help="Optional camera filter.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    bootstrap_python_paths()

    from api.database import SessionLocal
    from api.models import Camera, Detection

    output_dir = ensure_directory(args.output_dir)
    images_dir = ensure_directory(output_dir / "images")
    manifest_path = output_dir / "manifest.csv"

    rows = []
    db = SessionLocal()
    try:
        query = db.query(Detection, Camera).join(Camera, Detection.camera_id == Camera.id)
        query = query.filter(Detection.capture_path.isnot(None))

        if args.camera_id is not None:
            query = query.filter(Detection.camera_id == args.camera_id)
        if args.min_confidence is not None:
            query = query.filter(Detection.confidence >= args.min_confidence)
        if args.max_confidence is not None:
            query = query.filter(Detection.confidence <= args.max_confidence)

        detections = (
            query.order_by(Detection.timestamp.desc(), Detection.id.desc())
            .limit(args.limit)
            .all()
        )

        for index, (detection, camera) in enumerate(detections, start=1):
            capture_name = Path(detection.capture_path).name
            source_path = Path(__file__).resolve().parents[1] / "data" / "detection_captures" / capture_name
            if not source_path.exists():
                continue

            exported_name = f"{index:05d}_{capture_name}"
            exported_path = images_dir / exported_name
            shutil.copy2(source_path, exported_path)

            rows.append(
                {
                    "export_id": index,
                    "detection_id": detection.id,
                    "camera_id": detection.camera_id,
                    "camera_name": camera.location_name,
                    "timestamp": detection.timestamp.isoformat(),
                    "input_kind": detection.input_kind,
                    "predicted_plate": detection.plate_number,
                    "final_confidence": detection.confidence,
                    "detector_confidence": detection.detector_confidence,
                    "ocr_confidence": detection.ocr_confidence,
                    "source_capture_url": detection.capture_path,
                    "exported_image": f"images/{exported_name}",
                    "review_status": "",
                    "corrected_plate": "",
                    "notes": "",
                }
            )
    finally:
        db.close()

    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "export_id",
                "detection_id",
                "camera_id",
                "camera_name",
                "timestamp",
                "input_kind",
                "predicted_plate",
                "final_confidence",
                "detector_confidence",
                "ocr_confidence",
                "source_capture_url",
                "exported_image",
                "review_status",
                "corrected_plate",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Exported {len(rows)} detections to {output_dir}")
    print(f"Review manifest: {manifest_path}")


if __name__ == "__main__":
    main()
