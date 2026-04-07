import argparse
import random
from pathlib import Path

from PIL import Image
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset, random_split

from common import (
    CHECKPOINT_ROOT,
    OCR_DATASET_ROOT,
    RUNS_ROOT,
    bootstrap_python_paths,
    ensure_directory,
)


class CharacterDataset(Dataset):
    def __init__(self, samples, transform):
        self.samples = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        image_path, label_index = self.samples[index]
        image = Image.open(image_path).convert("RGB")
        return self.transform(image), label_index


def parse_args():
    parser = argparse.ArgumentParser(description="Train digit or letter OCR classifier.")
    parser.add_argument("--task", choices=["digit", "letter"], required=True)
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=OCR_DATASET_ROOT,
        help="Root directory created by build_classifier_dataset.py",
    )
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--val-split", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output checkpoint path. Defaults to backend/checkpoints/<task>_best_retrained.pth",
    )
    return parser.parse_args()


def resolve_device(device_arg: str) -> torch.device:
    if device_arg == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device_arg.isdigit():
        return torch.device(f"cuda:{device_arg}")
    return torch.device(device_arg)


def build_samples(dataset_dir: Path, class_order: list[str]):
    samples = []
    for label_index, class_name in enumerate(class_order):
        class_dir = dataset_dir / class_name
        if not class_dir.exists():
            continue

        for image_path in sorted(class_dir.glob("*")):
            if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                continue
            samples.append((image_path, label_index))
    return samples


def main():
    args = parse_args()
    bootstrap_python_paths()

    from classification import ObjectClassifier, letter_dict, transform

    random.seed(args.seed)
    torch.manual_seed(args.seed)

    if args.task == "digit":
        class_order = [str(index) for index in range(10)]
        dataset_dir = args.dataset_root / "digits"
        num_classes = 10
        default_output = CHECKPOINT_ROOT / "digit_best_retrained.pth"
    else:
        class_order = [letter_dict[index] for index in sorted(letter_dict)]
        dataset_dir = args.dataset_root / "letters"
        num_classes = len(class_order)
        default_output = CHECKPOINT_ROOT / "letter_best_retrained.pth"

    samples = build_samples(dataset_dir, class_order)
    if not samples:
        raise RuntimeError(f"No training samples found in {dataset_dir}")

    dataset = CharacterDataset(samples, transform=transform)
    val_size = max(1, int(len(dataset) * args.val_split))
    train_size = max(len(dataset) - val_size, 1)
    if train_size + val_size > len(dataset):
        val_size = len(dataset) - train_size

    train_dataset, val_dataset = random_split(
        dataset,
        [train_size, val_size],
        generator=torch.Generator().manual_seed(args.seed),
    )

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False)

    device = resolve_device(args.device)
    model = ObjectClassifier(num_classes).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)

    best_val_accuracy = -1.0
    output_path = args.output or default_output
    ensure_directory(output_path.parent)

    for epoch in range(1, args.epochs + 1):
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0

        for images, labels in train_loader:
            images = images.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * labels.size(0)
            predictions = outputs.argmax(dim=1)
            train_correct += (predictions == labels).sum().item()
            train_total += labels.size(0)

        model.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device)
                labels = labels.to(device)
                outputs = model(images)
                predictions = outputs.argmax(dim=1)
                val_correct += (predictions == labels).sum().item()
                val_total += labels.size(0)

        train_accuracy = train_correct / max(train_total, 1)
        val_accuracy = val_correct / max(val_total, 1)
        average_train_loss = train_loss / max(train_total, 1)

        print(
            f"Epoch {epoch:02d}/{args.epochs} "
            f"- loss {average_train_loss:.4f} "
            f"- train_acc {train_accuracy:.4f} "
            f"- val_acc {val_accuracy:.4f}"
        )

        if val_accuracy > best_val_accuracy:
            best_val_accuracy = val_accuracy
            torch.save(model.state_dict(), output_path)

    print(f"Best validation accuracy: {best_val_accuracy:.4f}")
    print(f"Saved checkpoint: {output_path}")


if __name__ == "__main__":
    main()
