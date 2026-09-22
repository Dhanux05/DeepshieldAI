import {
  ShieldAlert,
  ShieldCheck,
  ShieldQuestion,
  Shield,
  HelpCircle,
} from "lucide-react";

/**
 * Single source of truth for how a predicted label is rendered.
 *
 * Every page displays verdicts, and before this existed each one had its own
 * inline colour map — which is how the same label ended up amber on one
 * screen and grey on another. Import from here instead.
 */
const MAP = {
  Deepfake: {
    tone: "threat",
    badge: "danger",
    text: "text-threat",
    ring: "border-threat/30 bg-threat/10 text-threat",
    tile: "bg-gradient-to-br from-threat to-volt-600",
    chart: "#ff5b5b",
    icon: ShieldAlert,
  },
  Genuine: {
    tone: "clear",
    badge: "success",
    text: "text-clear",
    ring: "border-clear/30 bg-clear/10 text-clear",
    tile: "bg-gradient-to-br from-clear to-aqua-500",
    chart: "#01b574",
    icon: ShieldCheck,
  },
  Suspicious: {
    tone: "caution",
    badge: "warning",
    text: "text-caution",
    ring: "border-caution/30 bg-caution/10 text-caution",
    tile: "bg-gradient-to-br from-caution to-threat",
    chart: "#ffb547",
    icon: ShieldQuestion,
  },
  Uncertain: {
    tone: "neutral",
    badge: "neutral",
    text: "text-slate-400",
    ring: "border-line bg-hover/[0.05] text-slate-400",
    tile: "bg-gradient-to-br from-slate-600 to-slate-500",
    chart: "#64748b",
    icon: HelpCircle,
  },
};

const FALLBACK = {
  tone: "neon",
  badge: "neutral",
  text: "text-slate-300",
  ring: "border-white/10 bg-white/5 text-slate-400",
  tile: "bg-neon-gradient",
  chart: "#0075ff",
  icon: Shield,
};

export function verdictOf(label) {
  return MAP[label] ?? FALLBACK;
}

/**
 * Confidence bands behind the display verdict below.
 *
 * A raw "87.3%" reads as false precision next to detectors whose real-world
 * reliability varies wildly by modality (see docs/MODELS.md — Video's F1 is
 * 0.385, Audio's is 0.980; the same-looking number means very different
 * things coming from each). Per overview.md's own four result
 * labels, only a genuinely confident call is shown as Genuine/Deepfake —
 * anything softer becomes a qualitative "Suspicious" or "Uncertain" word
 * instead of a number that implies more precision than the model earns.
 *
 * REVISED (was 0.8 / 0.6): those thresholds turned out to be far too strict
 * for how these models actually behave. A correctly-classified real photo
 * through the Image detector (MobileNetV2, a single un-calibrated sigmoid —
 * see image_detector.py's docstring) routinely scores in the 0.6-0.8 range
 * even when it's unambiguously right; that's normal, expected behaviour for
 * this architecture, not a sign the call is shaky. At 0.8 the UI was
 * mislabelling perfectly good "Genuine" results as "Suspicious", which is a
 * worse failure than showing a number ever was. The bands are now set so
 * ANY call clearly on one side of a coin flip (>=0.55) shows its real
 * label; only calls within a few points of an actual 50/50 tie are flagged
 * "Suspicious", and "Uncertain" is reserved for a missing/invalid score. If
 * a specific modality later gets real confidence calibration (temperature
 * scaling against a validation set), these can be tightened again with
 * evidence instead of a guess.
 */
export const CONFIDENT_THRESHOLD = 0.55;
export const SUSPICIOUS_THRESHOLD = 0.5;

/**
 * Maps a detector's raw (label, confidence) pair to what the UI shows.
 * >= CONFIDENT_THRESHOLD: the real predicted label, unchanged.
 * >= SUSPICIOUS_THRESHOLD: "Suspicious" — flagged for human review.
 * below that (near a coin flip): "Uncertain".
 *
 * The raw confidence_score still exists on every API response for anything
 * that needs the real number (audit trail, LIME/SHAP, dashboard aggregates)
 * — this function only decides what a human reads for one specific result.
 */
export function getDisplayVerdict(predictedLabel, confidenceScore) {
  const confidence = Number(confidenceScore);

  if (!Number.isFinite(confidence)) {
    return predictedLabel;
  }
  if (confidence >= CONFIDENT_THRESHOLD) {
    return predictedLabel;
  }
  if (confidence >= SUSPICIOUS_THRESHOLD) {
    return "Suspicious";
  }
  return "Uncertain";
}

/** Status pill tones for `processing_status`. */
export function statusTone(status) {
  switch (status) {
    case "Completed":
      return "success";
    case "Processing":
      return "info";
    case "Failed":
      return "danger";
    case "Pending":
    default:
      return "neutral";
  }
}

/** Stable chart colours, in the order categories are encountered. */
export const CHART_PALETTE = [
  "#0075ff",
  "#582cff",
  "#21d4fd",
  "#01b574",
  "#ffb547",
  "#ff5b5b",
];
