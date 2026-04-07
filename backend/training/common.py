from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
API_ROOT = BACKEND_ROOT / "api"
SRC_ROOT = BACKEND_ROOT / "src"
DATA_ROOT = BACKEND_ROOT / "data"
CHECKPOINT_ROOT = BACKEND_ROOT / "checkpoints"
RETRAINING_ROOT = DATA_ROOT / "retraining"
ERROR_REVIEW_ROOT = RETRAINING_ROOT / "error_review"
DETECTOR_DATASET_ROOT = RETRAINING_ROOT / "detector_dataset"
OCR_DATASET_ROOT = RETRAINING_ROOT / "ocr_dataset"
RUNS_ROOT = RETRAINING_ROOT / "runs"


def bootstrap_python_paths() -> None:
    for path in (PROJECT_ROOT, BACKEND_ROOT, API_ROOT, SRC_ROOT):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
