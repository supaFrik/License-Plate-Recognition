import argparse
import csv
from pathlib import Path

import cv2

from common import (
    CHECKPOINT_ROOT,
    OCR_DATASET_ROOT,
    bootstrap_python_paths,
    ensure_directory,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build digit and letter classifier datasets from reviewed real-camera captures.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Path to review manifest.csv. Defaults to backend/data/retraining/error_review/manifest.csv",
    )
    parser.add_argument(
        "--detector-checkpoint",
        type=Path,
        default=CHECKPOINT_ROOT / "detect_best.pt",
        help="Detector checkpoint used to localize plates and characters.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OCR_DATASET_ROOT,
        help="Where the OCR dataset should be written.",
    )
    parser.add_argument(
        "--label-column",
        type=str,
        default="corrected_plate",
        help="CSV column containing reviewed plate labels.",
    )
    return parser.parse_args()


def normalize_plate_text(value: str) -> str:
    return "".join(character for character in value.upper() if character.isalnum())


def main():
    args = parse_args()
    bootstrap_python_paths()

    from classification import letter_dict
    from recognizer import PlateRecognizer
    from utils import sort_objects

    manifest_path = args.manifest or (OCR_DATASET_ROOT.parent / "error_review" / "manifest.csv")
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    letter_classes = set(letter_dict.values())
    output_dir = ensure_directory(args.output_dir)
    digits_dir = ensure_directory(output_dir / "digits")
    letters_dir = ensure_directory(output_dir / "letters")

    recognizer = PlateRecognizer(
        yolo_ckpt=str(args.detector_checkpoint),
        digit_ckpt=str(CHECKPOINT_ROOT / "digit_best.pth"),
        letter_ckpt=str(CHECKPOINT_ROOT / "letter_best.pth"),
    )

    written_rows = []
    skipped_rows = []

    with manifest_path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    sample_index = 0
    for row in rows:
        plate_text = normalize_plate_text(row.get(args.label_column, ""))
        if not plate_text:
            skipped_rows.append(
                {
                    "exported_image": row.get("exported_image", ""),
                    "reason": f"Missing {args.label_column}",
                }
            )
            continue

        image_path = manifest_path.parent / row["exported_image"]
        image = cv2.imread(str(image_path))
        if image is None:
            skipped_rows.append(
                {
                    "exported_image": row["exported_image"],
                    "reason": "Image unreadable",
                }
            )
            continue

        batch_objects, batch_plates = recognizer.detect_batch([image])
        objects = batch_objects[0]
        plate = batch_plates[0]
        if plate is None:
            skipped_rows.append(
                {
                    "exported_image": row["exported_image"],
                    "reason": "No plate detected",
                }
            )
            continue

        objects = sort_objects(objects, plate)
        if len(objects) != len(plate_text):
            skipped_rows.append(
                {
                    "exported_image": row["exported_image"],
                    "reason": f"Character count mismatch: detected {len(objects)} expected {len(plate_text)}",
                }
            )
            continue

        sample_index += 1
        image_stem = Path(row["exported_image"]).stem
        for char_index, (obj, label_char) in enumerate(zip(objects, plate_text), start=1):
            if label_char.isdigit():
                class_dir = ensure_directory(digits_dir / label_char)
            elif label_char in letter_classes:
                class_dir = ensure_directory(letters_dir / label_char)
            else:
                skipped_rows.append(
                    {
                        "exported_image": row["exported_image"],
                        "reason": f"Unsupported character label: {label_char}",
                    }
                )
                continue

            output_name = f"{sample_index:05d}_{image_stem}_{char_index:02d}.png"
            output_path = class_dir / output_name
            cv2.imwrite(str(output_path), obj["image"])

            written_rows.append(
                {
                    "source_image": row["exported_image"],
                    "character": label_char,
                    "output_path": str(output_path.relative_to(output_dir)),
                }
            )

    with (output_dir / "dataset_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source_image", "character", "output_path"],
        )
        writer.writeheader()
        writer.writerows(written_rows)

    with (output_dir / "skipped_samples.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["exported_image", "reason"])
        writer.writeheader()
        writer.writerows(skipped_rows)

    print(f"Wrote {len(written_rows)} OCR training crops to {output_dir}")
    print(f"Skipped {len(skipped_rows)} samples. Review skipped_samples.csv before training.")


if __name__ == "__main__":
    main()
