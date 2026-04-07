import argparse
import csv
import shutil
from pathlib import Path

import cv2

from common import (
    CHECKPOINT_ROOT,
    DETECTOR_DATASET_ROOT,
    bootstrap_python_paths,
    ensure_directory,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a draft YOLO detector dataset from reviewed capture exports using current model predictions.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Path to review manifest.csv. Defaults to backend/data/retraining/error_review/manifest.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DETECTOR_DATASET_ROOT,
        help="Where the YOLO dataset should be written.",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=CHECKPOINT_ROOT / "detect_best.pt",
        help="Detector checkpoint used to generate draft labels.",
    )
    parser.add_argument(
        "--val-stride",
        type=int,
        default=5,
        help="Every Nth sample goes to validation split.",
    )
    return parser.parse_args()


def normalize_bbox(x_min, y_min, x_max, y_max, width, height):
    x_center = ((x_min + x_max) / 2.0) / width
    y_center = ((y_min + y_max) / 2.0) / height
    bbox_width = (x_max - x_min) / width
    bbox_height = (y_max - y_min) / height
    return x_center, y_center, bbox_width, bbox_height


def main():
    args = parse_args()
    bootstrap_python_paths()

    from recognizer import PlateRecognizer

    manifest_path = args.manifest or (DETECTOR_DATASET_ROOT.parent / "error_review" / "manifest.csv")
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    recognizer = PlateRecognizer(
        yolo_ckpt=str(args.checkpoint),
        digit_ckpt=str(CHECKPOINT_ROOT / "digit_best.pth"),
        letter_ckpt=str(CHECKPOINT_ROOT / "letter_best.pth"),
    )
    class_map = {name: index for index, name in recognizer.yolo_model.names.items()}

    output_dir = ensure_directory(args.output_dir)
    for split in ("train", "val"):
        ensure_directory(output_dir / "images" / split)
        ensure_directory(output_dir / "labels" / split)

    with manifest_path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    written = 0
    for index, row in enumerate(rows, start=1):
        image_path = manifest_path.parent / row["exported_image"]
        image = cv2.imread(str(image_path))
        if image is None:
            continue

        batch_objects, batch_plates = recognizer.detect_batch([image])
        objects = batch_objects[0]
        plate = batch_plates[0]
        if plate is None:
            continue

        height, width = image.shape[:2]
        labels = []

        plate_bbox = recognizer._compute_plate_bbox(plate)
        if plate_bbox is not None:
            labels.append(
                (
                    class_map[plate["label"]],
                    *normalize_bbox(
                        plate_bbox["x_min"],
                        plate_bbox["y_min"],
                        plate_bbox["x_max"],
                        plate_bbox["y_max"],
                        width,
                        height,
                    ),
                )
            )

        for obj in objects:
            x_min, y_min, x_max, y_max = obj["box"]
            labels.append(
                (
                    class_map[obj["label"]],
                    *normalize_bbox(x_min, y_min, x_max, y_max, width, height),
                )
            )

        split = "val" if index % max(args.val_stride, 2) == 0 else "train"
        exported_name = f"{Path(row['exported_image']).stem}.jpg"
        target_image = output_dir / "images" / split / exported_name
        target_label = output_dir / "labels" / split / f"{Path(exported_name).stem}.txt"

        shutil.copy2(image_path, target_image)
        with target_label.open("w", encoding="utf-8") as label_file:
            for class_id, x_center, y_center, bbox_width, bbox_height in labels:
                label_file.write(
                    f"{class_id} {x_center:.6f} {y_center:.6f} {bbox_width:.6f} {bbox_height:.6f}\n"
                )
        written += 1

    data_yaml = output_dir / "data.yaml"
    names_in_order = [name for _, name in sorted(recognizer.yolo_model.names.items())]
    data_yaml.write_text(
        "\n".join(
            [
                f"path: {output_dir.as_posix()}",
                "train: images/train",
                "val: images/val",
                f"names: {names_in_order}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {written} draft detector samples to {output_dir}")
    print(f"Dataset YAML: {data_yaml}")
    print("These labels are bootstrapped from the current model and should be reviewed before retraining.")


if __name__ == "__main__":
    main()
