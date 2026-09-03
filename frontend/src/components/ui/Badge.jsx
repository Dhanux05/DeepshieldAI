const tones = {
  success: "bg-clear/12 text-clear ring-1 ring-inset ring-clear/30 hover:bg-clear/20",
  danger: "bg-threat/12 text-threat ring-1 ring-inset ring-threat/30 hover:bg-threat/20",
  warning: "bg-caution/12 text-caution ring-1 ring-inset ring-caution/30 hover:bg-caution/20",
  info: "bg-aqua-500/12 text-aqua-300 ring-1 ring-inset ring-aqua-500/30 hover:bg-aqua-500/20",
  neutral: "bg-hover/6 text-slate-400 ring-1 ring-inset ring-line/12 hover:bg-hover/12",
  brand: "bg-neon-500/12 text-neon-300 ring-1 ring-inset ring-neon-500/30 hover:bg-neon-500/20",
};

export default function Badge({
  tone = "neutral",
  dot = false,
  className = "",
  children,
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-[0.7rem] font-semibold transition-colors duration-200 ${tones[tone]} ${className}`}
    >
      {dot && (
        <span className="h-1.5 w-1.5 rounded-full bg-current shadow-glow-sm" />
      )}
      {children}
    </span>
  );
}
