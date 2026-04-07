# VietPlateAI Retraining Workflow

This workspace is for improving confidence on real camera data.

## 1. Export real error captures

```powershell
cd backend\training
python export_error_dataset.py --limit 500 --max-confidence 0.92
```

This writes:

- `backend/data/retraining/error_review/images/`
- `backend/data/retraining/error_review/manifest.csv`

Review `manifest.csv` and fill in:

- `review_status`
- `corrected_plate`
- `notes`

## 2. Bootstrap detector labels

```powershell
python bootstrap_detector_dataset.py
```

This creates a draft YOLO dataset in:

- `backend/data/retraining/detector_dataset/`

These labels are generated from the current detector. Review and correct them before training.

## 3. Retrain detector first

```powershell
python train_detector.py --epochs 60 --batch 16 --device 0
```

This fine-tunes from `backend/checkpoints/detect_best.pt`.

## 4. Build OCR dataset from reviewed captures

After the detector is improved and `manifest.csv` has `corrected_plate` values:

```powershell
python build_classifier_dataset.py --detector-checkpoint ..\checkpoints\detect_best.pt
```

This creates:

- `backend/data/retraining/ocr_dataset/digits/`
- `backend/data/retraining/ocr_dataset/letters/`

## 5. Retrain digit classifier

```powershell
python train_classifier.py --task digit --epochs 20 --batch-size 64 --device 0
```

## 6. Retrain letter classifier

```powershell
python train_classifier.py --task letter --epochs 20 --batch-size 64 --device 0
```

## Notes

- The API now records:
  - final confidence
  - detector confidence
  - OCR confidence
- Final confidence is a weighted combination of detector confidence and OCR probability.
- Historical captures are exported from real saved detections, not synthetic samples.
