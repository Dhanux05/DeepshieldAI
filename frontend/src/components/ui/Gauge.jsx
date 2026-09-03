/**
 * Semicircular gauge, matching the "satisfaction rate" dial in the reference.
 *
 * Drawn with two SVG arcs and a dash offset rather than a chart library —
 * recharts has no native half-doughnut with a rounded cap, and this is ~30
 * lines with no extra dependency.
 */
export default function Gauge({
  value = 0,
  min = 0,
  max = 100,
  label,
  caption,
  size = 200,
}) {
  const pct = Math.max(0, Math.min((Number(value) - min) / (max - min), 1));

  const stroke = 12;
  const radius = (size - stroke) / 2;
  const cx = size / 2;
  const cy = size / 2;

  // Half circle: left edge -> right edge over the top.
  const arc = Math.PI * radius;
  const d = `M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`;

  return (
    <div className="flex flex-col items-center">
      <svg
        width={size}
        height={size / 2 + stroke}
        viewBox={`0 0 ${size} ${size / 2 + stroke}`}
        className="overflow-visible"
        role="img"
        aria-label={`${label ?? "Gauge"}: ${Math.round(pct * 100)}%`}
      >
        <defs>
          <linearGradient id="gaugeFill" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#0075ff" />
            <stop offset="100%" stopColor="#21d4fd" />
          </linearGradient>
        </defs>

        <path
          d={d}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={stroke}
          strokeLinecap="round"
        />
        <path
          d={d}
          fill="none"
          stroke="url(#gaugeFill)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={arc}
          strokeDashoffset={arc * (1 - pct)}
          style={{ transition: "stroke-dashoffset 700ms ease-out" }}
        />
      </svg>

      <div className="-mt-10 text-center">
        <p className="text-3xl font-bold tracking-tight text-slate-50">
          {Math.round(pct * 100)}%
        </p>
        {caption && <p className="mt-1 text-xs text-slate-400">{caption}</p>}
      </div>

      <div className="mt-3 flex w-full justify-between px-1 text-[0.68rem] text-slate-500">
        <span>{min}%</span>
        <span>{max}%</span>
      </div>
    </div>
  );
}
