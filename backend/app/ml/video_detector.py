import pickle
import time
from pathlib import Path

import torch

from app.core.logging import get_logger
from app.ml.base import BaseDetector, DetectionResult, ModelUnavailableError
from app.ml.video_preprocessing import FRAME_SIZE, NUM_FRAMES, extract_frames

logger = get_logger(__name__)

# Fallback only for the (unexpected) case where class_names.pkl is missing.
# CONFIRMED from DeepShieldAI_Video_Retraining.ipynb, cell 6 & 52 — reading
# the checkpoint's own class_names.pkl when present is still preferred over
# this constant, for the same reason audio_detector.py reads id2label from
# the model instead of hardcoding it.
DEFAULT_CLASS_NAMES = ["videos_real", "videos_fake"]


class VideoDetector(BaseDetector):
    """
    R3D-18 (torchvision, Kinetics-400 pretrained) fine-tuned for real/fake
    video classification.

    Architecture, per DeepShieldAI_Video_Retraining.ipynb: the full R3D-18
    backbone frozen, then a two-stage fine-tune — first only the replaced
    `fc` layer, then `layer4` (the last residual block) unfrozen alongside
    `fc` at a much lower learning rate. That second stage is what took the
    model from predicting one class always (F1 0.385) to a real, if still
    noisy, 0.75 test accuracy — see docs/MODELS.md and PROJECT_STATUS_RECHECK
    for the full before/after.

    Unlike Audio's Wav2Vec2ForSequenceClassification, a raw `state_dict`
    carries no label metadata at all — so, like the Image detector, the
    class mapping is external. Here it comes from `class_names.pkl`, which
    the training notebook saved right alongside the weights (not from
    hardcoded config, which is what caused the Image model's polarity bug).
    """

    modality = "Video"

    def __init__(
        self,
        weights_path: str,
        class_names_path: str | None = None,
        num_frames: int = NUM_FRAMES,
        frame_size: int = FRAME_SIZE,
        device: str = "cpu",
    ):
        self.weights_path = weights_path
        self.class_names_path = class_names_path
        self.num_frames = num_frames
        self.frame_size = frame_size

        requested_device = device if (device != "cuda" or torch.cuda.is_available()) else "cpu"
        self.device = torch.device(requested_device)

        self._model = None
        self._class_names: list[str] = DEFAULT_CLASS_NAMES
        self._name = "r3d18_deepshield_video_finetuned"
        self._load_error: str | None = None

    # ------------------------------------------------------------ contract
    @property
    def model_name(self) -> str:
        return self._name

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        """
        Load the fine-tuned checkpoint once, at startup.

        R3D-18 is a 3D CNN over 16 full-resolution frames — meaningfully
        heavier per-inference than the Image detector, so the singleton
        load-once discipline matters even more here.
        """
        weights_path = Path(self.weights_path)

        if not weights_path.exists():
            self._load_error = f"Weights not found at {weights_path}"
            logger.warning("VideoDetector: %s", self._load_error)
            return

        try:
            from torchvision.models.video import r3d_18
        except ImportError:
            self._load_error = (
                "torchvision is not installed. "
                "Install requirements/ml.txt to enable video inference."
            )
            logger.warning("VideoDetector: %s", self._load_error)
            return

        # Recreate the exact architecture the checkpoint was saved from:
        # R3D-18 with an untrained 2-class head, matching cell 55 of the
        # retraining notebook. weights=None — no need to re-download the
        # Kinetics-400 pretrained weights just to overwrite every one of
        # them with the checkpoint immediately afterward.
        try:
            model = r3d_18(weights=None)
            model.fc = torch.nn.Linear(model.fc.in_features, 2)

            state_dict = torch.load(
                str(weights_path),
                map_location=self.device,
                weights_only=True,
            )
            model.load_state_dict(state_dict)

            model = model.to(self.device)
            model.eval()
        except Exception as exc:  # noqa: BLE001 - surfaced via /models
            self._load_error = f"{type(exc).__name__}: {exc}"
            logger.exception("VideoDetector failed to load %s", weights_path)
            return

        self._model = model

        if self.class_names_path and Path(self.class_names_path).exists():
            with open(self.class_names_path, "rb") as f:
                self._class_names = pickle.load(f)
        else:
            logger.warning(
                "VideoDetector: class_names.pkl not found at %s — "
                "falling back to %s. Verify this matches the checkpoint.",
                self.class_names_path,
                DEFAULT_CLASS_NAMES,
            )

        logger.info(
            "VideoDetector ready — %s (%s params, device=%s, classes=%s)",
            self._name,
            f"{sum(p.numel() for p in self._model.parameters()):,}",
            self.device,
            self._class_names,
        )

    # ------------------------------------------------------------ inference
    def predict(self, file_path: str) -> DetectionResult:
        if self._model is None:
            raise ModelUnavailableError(
                self._load_error or "Video model is not loaded."
            )

        started = time.perf_counter()

        frames = extract_frames(
            file_path,
            num_frames=self.num_frames,
            frame_size=self.frame_size,
        )

        # (T, H, W, C) -> (1, C, T, H, W) — matches VideoFrameDataset in the
        # training notebook exactly, including the batch-of-one dimension.
        clip = (
            torch.from_numpy(frames)
            .permute(3, 0, 1, 2)
            .unsqueeze(0)
            .float()
            .to(self.device)
        )

        with torch.no_grad():
            logits = self._model(clip)
            probs = torch.softmax(logits, dim=1)[0]

        predicted_id = int(torch.argmax(probs).item())
        raw_label = self._class_names[predicted_id]
        confidence = float(probs[predicted_id])

        # "videos_real" / "videos_fake" -> "Real" / "Fake": readable labels
        # for the API response, derived from the checkpoint's own class
        # names rather than a second hardcoded mapping.
        label = "Fake" if "fake" in raw_label.lower() else "Real"

        probabilities = {
            ("Fake" if "fake" in name.lower() else "Real"): round(float(p), 6)
            for name, p in zip(self._class_names, probs)
        }

        return DetectionResult(
            label=label,
            confidence=confidence,
            probabilities=probabilities,
            model_name=self._name,
            processing_time=time.perf_counter() - started,
            metadata={
                "num_frames": self.num_frames,
                "frame_size": self.frame_size,
                "device": str(self.device),
                "raw_class_name": raw_label,
            },
        )

    def describe(self) -> dict:
        payload = super().describe()
        payload.update(
            {
                "weights_path": self.weights_path,
                "num_frames": self.num_frames,
                "frame_size": self.frame_size,
                "labels": ["Real", "Fake"],
                "error": self._load_error,
            }
        )
        return payload
