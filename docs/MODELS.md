# Trained model inventory

**Verified against the five Colab training notebooks, 10 Aug 2026.**
Source of truth: `MyDrive/DeepShieldAI/` (owner: vinuthabr2020@gmail.com)

Every fact below is read from notebook source or captured cell output — not
inferred from the artefacts.

---

## Where the good copies live

Use **`Models/`**, not `checkpoints/`. `Models/` holds the clean exports
(`trainer.save_model()` + tokenizer/feature-extractor); `checkpoints/` holds
mid-training Trainer state with 500 MB+ optimiser buffers you don't need.

| Modality | Copy this | Size |
|---|---|---|
| Image | `Models/image_model/` → `model.keras`, `labels.pkl`, `training_history.pkl` | ~12 MB |
| Audio | `Models/audio_model/` → `config.json`, `model.safetensors`, `preprocessor_config.json` | ~380 MB |
| Review | `Models/review_model/` → `config.json`, `model.safetensors`, `tokenizer.json`, `vocab.txt`, `tokenizer_config.json`, `special_tokens_map.json` | ~270 MB |
| Text/News | `checkpoints/text/` → `model.safetensors` + tokenizer files (no `Models/` export exists) | ~270 MB |
| Video | `Models/video_model/video_model.pth` | ~127 MB |

Skip every `optimizer.pt`, `scheduler.pt` and `rng_state.pth`.

---

## 1. Image — LIVE ✅

| | |
|---|---|
| Notebook | `Image_Training_Model.ipynb` |
| Architecture | MobileNetV2 (ImageNet, **frozen**) → GAP → Dropout(0.3) → Dense(128, relu) → Dropout(0.2) → Dense(1, **sigmoid**) |
| Input | 224×224×3 |
| **Scaling** | **`image / 255.0` → [0, 1]** |
| **Labels** | **`0 = REAL`, `1 = FAKE`** → sigmoid output is **P(FAKE)** |
| Data | 500 real + 500 fake; split 800 / 100 / 100 (seed 42) |
| Training | 3 epochs, Adam lr 1e-4, batch 16, binary crossentropy |
| Augmentation | RandomFlip(horizontal), RandomRotation(0.1), RandomZoom(0.1) — train only |

**Test results (n=100):**

| Metric | Value |
|---|---|
| Accuracy | 0.7600 |
| Precision | 0.7167 |
| Recall | 0.8600 |
| F1 | 0.7818 |

Confusion matrix `[[33, 17], [7, 43]]` — REAL recall is only **0.66**, so it
misclassifies a third of genuine images as fake. It over-predicts FAKE.

### Both of my earlier defaults were wrong — now corrected

| Setting | I had assumed | Notebook says |
|---|---|---|
| Preprocessing | `mobilenet_v2` ([-1, 1]) | **`rescale`** ([0, 1]) |
| Polarity | high sigmoid = Genuine | **high sigmoid = Deepfake** |

The polarity error would have **inverted every verdict** with no error raised.
`backend/app/core/config.py` now reads:

```env
IMAGE_PREPROCESS_MODE=rescale
IMAGE_POSITIVE_LABEL=Deepfake
IMAGE_NEGATIVE_LABEL=Genuine
```

`scripts/calibrate_image_model.py` is no longer needed to *find* these, but
it's still worth one run as an independent confirmation.

> Note: training resized with `tf.image.resize` (bilinear) and applied no EXIF
> transpose. Our `preprocessing.py` uses bilinear (matches) and *does* apply
> EXIF transpose (deliberate improvement for phone uploads).

---

## 2. Audio — READY TO WIRE ✅

| | |
|---|---|
| Notebook | `Audio_Model_Training.ipynb` |
| Base | `facebook/wav2vec2-base`, `Wav2Vec2ForSequenceClassification` |
| Preprocessing | librosa → **mono, 16 000 Hz**, max **5 s** (80 000 samples), `truncation=True, padding="max_length"` |
| Labels | `{"fake": 0, "real": 1}` · id2label `{0: "Fake", 1: "Real"}` |
| Data | 500 real + 500 fake (`mini_audio_deepfake_dataset`); 700 / 150 / 150 |
| Training | 5 epochs, lr 3e-5, batch 8, warmup 0.1, weight decay 0.01, feature encoder frozen, early stopping (patience 2), best-by-F1 |

**Test results (n=150): Accuracy 0.9800 · Precision 0.9808 · Recall 0.9800 · F1 0.9800**
Per class: Fake P 0.96 / R 1.00 · Real P 1.00 / R 0.96.

The strongest model in the project. `Models/audio_model/` is complete and
includes `preprocessor_config.json`, so it loads with a plain
`pipeline("audio-classification", model=...)`.

---

## 3. Review (fake review / CG vs OR) — READY TO WIRE, WITH A CAVEAT ⚠️

| | |
|---|---|
| Notebook | `Review_Model_Training.ipynb` |
| Base | `distilbert-base-uncased` |
| Tokenisation | `max_length=256`, truncation, **dynamic padding** (`DataCollatorWithPadding`) |
| Labels | `{"CG": 0, "OR": 1}` · id2label `{0: "Fake (CG)", 1: "Genuine (OR)"}` |
| Data | 40 432 rows → 40 420 after dedupe; balanced (20 205 CG / 20 215 OR); 28 294 train / 6 063 test |
| Training | 3 epochs, lr 2e-5, batch 16, early stopping (patience 2), best-by-F1 |

**Test results (n=6 063): Accuracy 0.9725 · F1 0.9725** — on a large, balanced
test set, which makes this the most statistically trustworthy number here.

### The caveat — check this before you demo it

The notebook's own ad-hoc examples are all wrong. Every hand-written spammy
review was classified **Genuine (OR)** with high confidence:

| Input | Prediction |
|---|---|
| "Amazing amazing amazing best product ever 100 percent recommend to everyone must buy" | Genuine (OR) — 0.997 |
| "This product completely changed my life, five stars, best purchase ever, buy now!!!" | Genuine (OR) — 0.995 |

97% on held-out data but failing on obvious out-of-distribution spam means the
model has learned to recognise *this dataset's* machine-generated style, not
"fake review" as a general concept. That's a legitimate finding to report — and
one an examiner may well probe by typing their own review into the demo.

---

## 4. Text / News — READY TO WIRE, BUT THE DATA PIPELINE HAS A BUG 🐛

| | |
|---|---|
| Notebook | `DeepShield_Text_Training(news and text).ipynb` |
| Base | `distilbert-base-uncased` |
| Tokenisation | `max_length=256`, truncation, `padding="max_length"` |
| Labels | id2label `{0: "FAKE", 1: "REAL"}` |
| Training | 3 epochs, lr 2e-5, batch 8, `save_strategy="epoch"`, saved to `checkpoints/text` |

**Reported test results: Accuracy 0.9940 · Precision 0.9825 · Recall 0.9825 · F1 0.9825**

### Do not quote that accuracy without qualifying it

Trace the row counts through the notebook:

```
loaded from CSV        3 729 rows   (FAKE 1 877 / REAL 1 852 — balanced)
after cleaning         3 721 rows   (FAKE 1 871 / REAL 1 850 — still balanced)
after label encoding   2 229 rows   (0 → 1 851 / 1 → 378  — 83/17 imbalance)
train+val+test         1 560 + 334 + 335 = 2 229
```

**1 492 rows (40% of the dataset) vanished during label encoding**, and the
class balance collapsed from 50/50 to 83/17. The test set is 278 vs 57.

On an 83/17 split, a model that answers "0" every time scores 83% accuracy. The
reported 99.4% is above that, and F1 0.982 on the minority class is genuinely
good — but the headline number is inflated by the imbalance, and the missing
40% is a bug, not a design choice. **Re-run the encoding cell** before this
goes in the report; the fix is likely a case/whitespace mismatch in the
`label` → id mapping.

---

## 5. Video — TRAINED BUT NOT USABLE ❌

| | |
|---|---|
| Notebook | `video_deepfake_detection.ipynb` |
| Architecture | **R3D-18** (torchvision, pretrained Kinetics), fc → Linear(512, 2); 33 167 298 params, all trainable |
| Preprocessing | 16 frames uniformly sampled, 224×224, `/255`, then mean `[0.43216, 0.394666, 0.37645]` / std `[0.22803, 0.22145, 0.216989]`; tensor `(C, T, H, W)` |
| Labels | `CLASS_NAMES = ["videos_real", "videos_fake"]` → 0 = real, 1 = fake |
| Data | **106 videos total** (53 real / 53 fake); 84 train / 11 val / 11 test |
| Training | 3 epochs, Adam lr 1e-4, batch 4; finished in 26 seconds |

**Test results (n=11): Accuracy 0.5455 · Precision 0.2975 · Recall 0.5455 · F1 0.3850**

```
              precision    recall  f1-score   support
 videos_real       0.55      1.00      0.71         6
 videos_fake       0.00      0.00      0.00         5
```

**The model predicts "real" for every input.** Fake recall is 0.00. Accuracy of
54.5% is exactly the majority-class rate on an 11-sample test set.

Validation accuracy across epochs: 0.4545 → 0.3636 → **0.1818**. It diverged;
the best checkpoint is epoch 1, before it learned anything.

Root cause is sample size — 84 training clips for a 33 M-parameter 3D CNN with
the entire backbone unfrozen. **Do not ship this.** Options: freeze the
backbone and train only `fc`, gather far more video, or drop the modality and
route video through the image detector frame-by-frame.

---

## Summary

| Modality | Test F1 | Test set size | Status |
|---|---|---|---|
| Audio | **0.980** | 150 | Best model. Wire it. |
| Review | **0.973** | 6 063 | Best evidence. Note the OOD caveat. |
| Text | 0.982 | 335 | Wire it, but fix the 40% data loss first. |
| Image | 0.782 | 100 | Live in the app now. |
| Video | 0.385 | 11 | Broken — predicts one class. |

**Framework mix:** Keras 3 (image) + PyTorch/Transformers (audio, text, review)
+ torchvision (video). State this in the report rather than letting a reviewer
discover it. The practical consequence lands in the XAI phase: Grad-CAM for the
Keras model needs `tf-keras-vis`, while SHAP/LIME for the transformers use the
standard PyTorch path.
