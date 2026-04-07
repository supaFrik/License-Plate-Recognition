import argparse
from pathlib import Path

from common import (
    CHECKPOINT_ROOT,
    DETECTOR_DATASET_ROOT,
    RUNS_ROOT,
    bootstrap_python_paths,
    ensure_directory,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Fine-tune the YOLO detector on reviewed plate data.")
    parser.add_argument(
        "--data",
        type=Path,
        default=DETECTOR_DATASET_ROOT / "data.yaml",
        help="Path to dataset YAML.",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=CHECKPOINT_ROOT / "detect_best.pt",
        help="Starting checkpoint.",
    )
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", type=str, default="0")
    parser.add_argument("--patience", type=int, default=15)
    parser.add_argument(
        "--project",
        type=Path,
        default=RUNS_ROOT / "detector",
        help="Directory where Ultralytics training runs should be written.",
    )
    parser.add_argument("--name", type=str, default="finetune")
    return parser.parse_args()


def main():
    args = parse_args()
    bootstrap_python_paths()

    from ultralytics import YOLO

    ensure_directory(args.project)
    model = YOLO(str(args.checkpoint))
    results = model.train(
        data=str(args.data),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        patience=args.patience,
        project=str(args.project),
        name=args.name,
        exist_ok=True,
    )

    best_weights = Path(results.save_dir) / "weights" / "best.pt"
    print(f"Detector training complete. Best checkpoint: {best_weights}")


if __name__ == "__main__":
    main()
