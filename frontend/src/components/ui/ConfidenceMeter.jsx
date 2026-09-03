/**
 * Horizontal confidence bar.
 *
 * `value` is the model's 0..1 confidence. The bar colour is driven by the
 * verdict, not by the magnitude — a 95% confident "Genuine" should read as
 * reassuring, not alarming, so tone must be passed in by the caller.
 */
export default function ConfidenceMeter({
  value = 0,
  tone = "neon",
  showLabel = true,
  size = "md",
}) {
  const pct = Math.max(0, Math.min(Number(value) * 100, 100));

  const fills = {
    threat: "bg-gradient-to-r from-threat/60 to-threat",
    clear: "bg-gradient-to-r from-clear/60 to-clear",
    caution: "bg-gradient-to-r from-caution/60 to-caution",
    neon: "bg-neon-gradient",
  };

  const heights = { sm: "h-1.5", md: "h-2.5", lg: "h-3" };

  return (
    <div>
      {showLabel && (
        <div className="mb-2 flex items-baseline justify-between">
          <span className="hud-label">Confidence</span>
          <span className="font-mono text-sm font-bold text-slate-50">
            {pct.toFixed(1)}%
          </span>
        </div>
      )}
      <div
        className={`w-full overflow-hidden rounded-full bg-hover/8 ${heights[size]}`}
        role="progressbar"
        aria-valuenow={Number(pct.toFixed(1))}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={`h-full rounded-full transition-[width] duration-700 ease-out ${fills[tone] ?? fills.neon}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
