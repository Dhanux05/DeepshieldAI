"""
Resolve the two unknowns in the trained image model, empirically.

`best_model.keras` stores the architecture and the weights, but NOT:

  1. which physical class the single sigmoid output corresponds to
     (Keras discards the directory -> index mapping), and
  2. how pixels were scaled during training.

Guessing either wrong produces a model that is confidently, silently wrong —
inverted verdicts, or garbage confidences. This script determines both by
running every combination against images you have already labelled.

Usage (from `backend/`):

    python -m scripts.calibrate_image_model --real <dir> --fake <dir>

`--real` should contain genuine/authentic images, `--fake` manipulated ones.
A dozen of each is plenty. The script prints the accuracy of every
(preprocessing x polarity) combination and tells you exactly which lines to
put in your .env.
"""

import argparse
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

PREPROCESS_MODES = ["mobilenet_v2", "rescale", "raw"]


def collect(directory: str) -> list[Path]:
    path = Path(directory)

    if not path.is_dir():
        raise SystemExit(f"Not a directory: {directory}")

    files = sorted(
        p for p in path.rglob("*") if p.suffix.lower() in IMAGE_EXTS
    )

    if not files:
        raise SystemExit(f"No images found in {directory}")

    return files


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calibrate the image detector's polarity and preprocessing."
    )
    parser.add_argument("--real", required=True, help="Folder of genuine images.")
    parser.add_argument("--fake", required=True, help="Folder of deepfake images.")
    parser.add_argument(
        "--weights",
        default=None,
        help="Override the model path (defaults to settings.IMAGE_MODEL_PATH).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=40,
        help="Max images to use per class (default 40).",
    )
    args = parser.parse_args()

    from app.core.config import settings
    from app.ml.preprocessing import preprocess_file

    weights = args.weights or settings.IMAGE_MODEL_PATH

    if not Path(weights).exists():
        raise SystemExit(f"Model not found: {weights}")

    try:
        import keras
    except ImportError:
        raise SystemExit(
            "Keras is not installed. Run: pip install -r requirements/ml.txt"
        ) from None

    print(f"Loading {weights} ...")
    model = keras.saving.load_model(weights, compile=False)
    print(f"Loaded: {model.name} ({model.count_params():,} params)\n")

    real_files = collect(args.real)[: args.limit]
    fake_files = collect(args.fake)[: args.limit]
    print(f"{len(real_files)} genuine · {len(fake_files)} deepfake\n")

    results = []

    for mode in PREPROCESS_MODES:
        scores = {"real": [], "fake": []}

        for group, files in (("real", real_files), ("fake", fake_files)):
            for file in files:
                try:
                    batch = preprocess_file(
                        str(file),
                        input_size=settings.IMAGE_INPUT_SIZE,
                        mode=mode,
                    )
                    scores[group].append(
                        float(model.predict(batch, verbose=0)[0][0])
                    )
                except Exception as exc:  # noqa: BLE001
                    print(f"  skipped {file.name}: {exc}")

        mean_real = sum(scores["real"]) / max(len(scores["real"]), 1)
        mean_fake = sum(scores["fake"]) / max(len(scores["fake"]), 1)

        # Polarity A: high sigmoid == genuine
        acc_a = (
            sum(1 for s in scores["real"] if s >= 0.5)
            + sum(1 for s in scores["fake"] if s < 0.5)
        ) / max(len(scores["real"]) + len(scores["fake"]), 1)

        # Polarity B: high sigmoid == deepfake
        acc_b = 1.0 - acc_a

        results.append((mode, mean_real, mean_fake, acc_a, acc_b))

        print(f"[{mode}]")
        print(f"  mean sigmoid on genuine  : {mean_real:.4f}")
        print(f"  mean sigmoid on deepfake : {mean_fake:.4f}")
        print(f"  accuracy if high=Genuine : {acc_a:.1%}")
        print(f"  accuracy if high=Deepfake: {acc_b:.1%}\n")

    # Pick the winner across both axes.
    best_mode, _, _, acc_a, acc_b = max(
        results, key=lambda r: max(r[3], r[4])
    )
    high_is_genuine = acc_a >= acc_b
    best_acc = max(acc_a, acc_b)

    print("=" * 62)
    print(f"BEST: {best_mode} preprocessing, "
          f"high sigmoid = {'Genuine' if high_is_genuine else 'Deepfake'} "
          f"({best_acc:.1%} accuracy)")
    print("=" * 62)
    print("\nPut this in backend/.env:\n")
    print(f"IMAGE_PREPROCESS_MODE={best_mode}")
    if high_is_genuine:
        print("IMAGE_POSITIVE_LABEL=Genuine")
        print("IMAGE_NEGATIVE_LABEL=Deepfake")
    else:
        print("IMAGE_POSITIVE_LABEL=Deepfake")
        print("IMAGE_NEGATIVE_LABEL=Genuine")

    if best_acc < 0.7:
        print(
            "\nWARNING: the best combination is still under 70%. Either the "
            "sample folders are mislabelled, or this model does not "
            "generalise to these images. Do not ship it before checking."
        )


if __name__ == "__main__":
    main()
