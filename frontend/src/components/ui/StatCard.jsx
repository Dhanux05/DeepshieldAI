import { TrendingUp, TrendingDown } from "lucide-react";
import Card from "./Card";

const tiles = {
  neon: "bg-neon-gradient",
  volt: "bg-volt-gradient",
  clear: "bg-gradient-to-br from-clear to-aqua-500",
  caution: "bg-gradient-to-br from-caution to-threat",
  threat: "bg-gradient-to-br from-threat to-volt-600",
};

export default function StatCard({
  label,
  value,
  hint,
  delta,
  icon: Icon,
  accent = "neon",
  loading = false,
}) {
  const positive = typeof delta === "number" && delta >= 0;
  const DeltaIcon = positive ? TrendingUp : TrendingDown;

  return (
    <Card padding="p-5">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="hud-label">{label}</p>

          <div className="mt-2 flex items-baseline gap-2">
            <p className="text-2xl font-bold tracking-tight text-slate-50">
              {loading ? "—" : value}
            </p>
            {typeof delta === "number" && (
              <span
                className={`inline-flex items-center gap-0.5 text-xs font-bold ${
                  positive ? "text-clear" : "text-threat"
                }`}
              >
                <DeltaIcon className="h-3 w-3" />
                {Math.abs(delta)}%
              </span>
            )}
          </div>

          {hint && <p className="mt-1 truncate text-xs text-slate-500">{hint}</p>}
        </div>

        {Icon && (
          <div className={`tile h-12 w-12 shrink-0 ${tiles[accent]}`}>
            <Icon className="h-5 w-5" strokeWidth={2.25} />
          </div>
        )}
      </div>
    </Card>
  );
}
