"""
Image preprocessing for the MobileNetV2 detector.

Preprocessing MUST match training exactly. A model trained on [-1, 1] inputs
but served [0, 1] inputs does not error — it just returns confident nonsense,
which is the single hardest class of bug to notice in a deepfake pipeline.

The trained artefact (`best_model.keras`) contains no Rescaling layer, so the
scaling was applied outside the graph during training and has to be
reproduced here. Which convention was used is not recoverable from the file,
so it is configuration, resolvable empirically with
`scripts/calibrate_image_model.py`.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

#: Supported scaling conventions.
PREPROCESS_MODES = ("mobilenet_v2", "rescale", "raw")

DEFAULT_INPUT_SIZE = 224


def load_image(file_path: str) -> Image.Image:
    """Open an image as RGB, honouring EXIF orientation."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Image not found: {file_path}")

    image = Image.open(path)
    # Phone photos carry rotation in EXIF; without this a portrait selfie is
    # fed to the model sideways.
    image = ImageOps.exif_transpose(image)
    return image.convert("RGB")


def to_batch(
    image: Image.Image,
    input_size: int = DEFAULT_INPUT_SIZE,
    mode: str = "mobilenet_v2",
) -> np.ndarray:
    """
    Resize to the model's input size and scale pixels.

    Returns a float32 array of shape (1, size, size, 3) — Keras expects
    channels-last with a leading batch dimension.
    """
    if mode not in PREPROCESS_MODES:
        raise ValueError(
            f"Unknown preprocess mode '{mode}'. Expected one of {PREPROCESS_MODES}."
        )

    resized = image.resize((input_size, input_size), Image.BILINEAR)
    array = np.asarray(resized, dtype="float32")

    if mode == "mobilenet_v2":
        # keras.applications.mobilenet_v2.preprocess_input: x/127.5 - 1
        array = array / 127.5 - 1.0
    elif mode == "rescale":
        # layers.Rescaling(1./255)
        array = array / 255.0
    # "raw" leaves 0..255 untouched

    return np.expand_dims(array, axis=0)


def preprocess_file(
    file_path: str,
    input_size: int = DEFAULT_INPUT_SIZE,
    mode: str = "mobilenet_v2",
) -> np.ndarray:
    """Convenience: path -> model-ready batch."""
    return to_batch(load_image(file_path), input_size=input_size, mode=mode)
