/**
 * Segmented control (tab switcher).
 *
 * options: [{ value, label, count? }]
 */
export default function Segmented({ options, value, onChange, className = "" }) {
  return (
    <div
      className={`inline-flex items-center gap-1 rounded-2xl border border-line/10 bg-void-700/50 p-1 ${className}`}
      role="tablist"
    >
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(option.value)}
            className={`inline-flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-semibold transition-all duration-200 ${
              active
                ? "bg-neon-gradient text-white shadow-tile"
                : "text-slate-400 hover:bg-hover/8 hover:text-slate-50"
            }`}
          >
            {option.label}
            {option.count !== undefined && (
              <span
                className={`rounded-md px-1.5 py-0.5 font-mono text-[0.62rem] ${
                  active ? "bg-black/25 text-white" : "bg-hover/8 text-slate-500"
                }`}
              >
                {option.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
