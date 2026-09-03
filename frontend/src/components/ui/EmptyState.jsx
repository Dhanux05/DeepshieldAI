export default function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className = "",
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center rounded-2xl border border-dashed border-line/12 bg-void-700/30 px-6 py-12 text-center transition-colors duration-300 hover:border-neon-500/30 ${className}`}
    >
      {Icon && (
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-line/10 bg-hover/5 text-slate-500">
          <Icon className="h-6 w-6" strokeWidth={1.75} />
        </div>
      )}
      <p className="text-sm font-semibold text-slate-200">{title}</p>
      {description && (
        <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-slate-500">
          {description}
        </p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
