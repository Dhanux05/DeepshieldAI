"""
Grad-CAM for the Image detector (MobileNetV2, running as a Keras 3 model on
the PyTorch backend — see app/ml/image_detector.py's docstring for why
there's no `tensorflow` install in this project at all).

`docs/MODELS.md` originally assumed `tf-keras-vis` for this, but that
library is TensorFlow-only and this project deliberately runs Keras on
the PyTorch backend instead. Rather than fight that mismatch, Grad-CAM is
implemented directly here using plain `torch.autograd` — since the active
backend is torch, a Keras 3 model's forward pass already produces real
torch.Tensor objects wired into torch's autograd graph, so the standard
Grad-CAM recipe (grab the last conv layer's activations, take the gradient
of the target output w.r.t. them, weight the channels by their average
gradient) works exactly as it would for a hand-written torch model.

Algorithm (Selvaraju et al., 2017):
    1. Build a second model exposing (last_conv_layer_output, final_output).
    2. Forward the input through it.
    3. Take d(final_output)/d(last_conv_layer_output) via autograd.
    4. Global-average-pool that gradient over space -> one weight per
       channel (this is "how much did this channel matter overall").
    5. Weight each channel of the conv activations by that and sum -> a
       single-channel heatmap over the conv layer's spatial resolution.
    6. ReLU it (Grad-CAM only cares about features that *increase* the
       target score) and normalise to [0, 1].
    7. Upsample to the input resolution and alpha-blend over the image.
"""
import base64
import io

import numpy as np
import torch
from PIL import Image

from app.ml.preprocessing import load_image, to_batch


def _find_last_conv_layer(model):
    """
    The last layer whose output is a 4D (batch, height, width, channels)
    feature map. Found by walking the model's layers rather than hardcoded
    by name — MobileNetV2's internal layer names aren't something this
    project should have to keep in sync with the trained `.keras` artefact
    by hand (same reasoning as reading id2label from a checkpoint instead
    of hardcoding it, elsewhere in app/ml/).
    """
    for layer in reversed(model.layers):
        shape = getattr(getattr(layer, "output", None), "shape", None)
        if shape is not None and len(shape) == 4:
            return layer

    raise ValueError(
        "No 4D convolutional-style layer found — Grad-CAM needs one to "
        "explain a spatial region of the input."
    )


def _apply_colormap(gray: np.ndarray) -> Image.Image:
    """
    A minimal black -> red -> yellow colormap, so a heatmap overlay doesn't
    require pulling in matplotlib as a dependency just for this. `gray` is
    uint8, shape (H, W).
    """
    r = np.clip(gray.astype("int16") * 2, 0, 255).astype("uint8")
    g = np.clip((gray.astype("int16") - 128) * 2, 0, 255).astype("uint8")
    b = np.zeros_like(gray, dtype="uint8")
    return Image.fromarray(np.stack([r, g, b], axis=-1), mode="RGB")


def generate(
    model,
    file_path: str,
    input_size: int = 224,
    preprocess_mode: str = "rescale",
    alpha: float = 0.45,
) -> dict:
    """
    Run Grad-CAM against a loaded ImageDetector's Keras model for the image
    at `file_path`. `model` is `ImageDetector.underlying_model`;
    `input_size`/`preprocess_mode` should be the same detector's own
    settings, so the explanation sees exactly what the classifier saw.

    Returns {"method", "artifact_type", "artifact", "metadata"} — see
    app/models/explanation.py for what "artifact_type": "image" means on
    the wire.
    """
    import keras

    original = load_image(file_path)
    batch = to_batch(original, input_size=input_size, mode=preprocess_mode)

    last_conv_layer = _find_last_conv_layer(model)
    grad_model = keras.Model(
        inputs=model.inputs,
        outputs=[last_conv_layer.output, model.output],
    )

    input_tensor = torch.tensor(batch, requires_grad=True)
    conv_output, predictions = grad_model(input_tensor)

    # Single sigmoid unit (see ImageDetector's docstring): there's no
    # softmax/argmax to pick a class from — the one output *is* the target.
    target = predictions[:, 0]

    grads = torch.autograd.grad(target, conv_output)[0]

    # Channels-last (N, H, W, C) — average the gradient spatially to get one
    # importance weight per channel, per the Grad-CAM paper.
    pooled_grads = grads.mean(dim=(0, 1, 2))

    conv_output = conv_output[0]  # drop the batch dim -> (H, W, C)
    heatmap = torch.einsum("hwc,c->hw", conv_output, pooled_grads)
    heatmap = torch.relu(heatmap)

    heatmap = heatmap.detach().cpu().numpy()
    peak = float(heatmap.max())
    if peak > 0:
        heatmap = heatmap / peak

    resized_original = original.resize((input_size, input_size), Image.BILINEAR)
    heatmap_img = Image.fromarray(np.uint8(255 * heatmap)).resize(
        (input_size, input_size), Image.BILINEAR
    )
    colored = _apply_colormap(np.asarray(heatmap_img))
    overlay = Image.blend(resized_original.convert("RGB"), colored, alpha=alpha)

    buffer = io.BytesIO()
    overlay.save(buffer, format="PNG")
    artifact = base64.b64encode(buffer.getvalue()).decode("ascii")

    return {
        "method": "gradcam",
        "artifact_type": "image",
        "artifact": artifact,
        "metadata": {
            "layer": getattr(last_conv_layer, "name", "unknown"),
            "input_size": input_size,
            "peak_activation": peak,
        },
    }
