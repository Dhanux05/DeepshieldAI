"""
Audio preprocessing for the wav2vec2 detector.

Preprocessing MUST match training exactly — same reasoning as
`preprocessing.py` for the image model. Per `docs/MODELS.md`
(Audio_Model_Training.ipynb): audio was loaded with librosa, forced to
mono, resampled to 16 000 Hz, and every clip was truncated or zero-padded
to exactly 5 seconds (80 000 samples) before being handed to the
Wav2Vec2 feature extractor. A clip fed in at a different length or sample
rate does not raise an error — wav2vec2's convolutional front end accepts
any length — it just produces a representation the classifier head was
never trained on, which returns confident nonsense exactly like the image
model's preprocessing mismatch would.

Unlike the Keras image model, the fine-tuned Wav2Vec2 checkpoint DOES carry
its own label mapping (`config.json` -> `id2label`), because `transformers`
persists it automatically at save time. `audio_detector.py` reads that
mapping directly from the loaded model instead of hardcoding it here, so
there is no equivalent of the image model's polarity bug possible for audio.
"""

from pathlib import Path

import librosa
import numpy as np

TARGET_SAMPLE_RATE = 16_000
TARGET_DURATION_SECONDS = 5.0
TARGET_NUM_SAMPLES = int(TARGET_SAMPLE_RATE * TARGET_DURATION_SECONDS)


def load_audio(file_path: str, sample_rate: int = TARGET_SAMPLE_RATE) -> np.ndarray:
    """Load an audio file as mono float32 at the target sample rate."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    # mono=True downmixes stereo; sr=sample_rate resamples on load — both
    # match what Audio_Model_Training.ipynb did before feature extraction.
    waveform, _ = librosa.load(str(path), sr=sample_rate, mono=True)
    return waveform.astype(np.float32)


def fix_length(
    waveform: np.ndarray,
    num_samples: int = TARGET_NUM_SAMPLES,
) -> np.ndarray:
    """
    Truncate or zero-pad to exactly `num_samples`.

    Mirrors the training pipeline's `truncation=True, padding="max_length"`
    with `max_length=80000`. The model was trained exclusively on fixed
    5-second windows, so a shorter or longer window at inference time is
    out-of-distribution for the classifier head even though the wav2vec2
    backbone itself would happily accept it.
    """
    if len(waveform) >= num_samples:
        return waveform[:num_samples]

    padded = np.zeros(num_samples, dtype=waveform.dtype)
    padded[: len(waveform)] = waveform
    return padded


def preprocess_file(
    file_path: str,
    sample_rate: int = TARGET_SAMPLE_RATE,
    num_samples: int = TARGET_NUM_SAMPLES,
) -> np.ndarray:
    """Convenience: path -> fixed-length mono waveform ready for the feature extractor."""
    waveform = load_audio(file_path, sample_rate=sample_rate)
    return fix_length(waveform, num_samples=num_samples)
