import { AlertTriangle, CheckCircle2, Info, Wrench } from "lucide-react";

const styles = {
  error: {
    wrap: "bg-threat/8 text-threat ring-1 ring-inset ring-threat/25",
    icon: AlertTriangle,
  },
  success: {
    wrap: "bg-clear/8 text-clear ring-1 ring-inset ring-clear/25",
    icon: CheckCircle2,
  },
  info: {
    wrap: "bg-volt-500/8 text-volt-300 ring-1 ring-inset ring-volt-500/25",
    icon: Info,
  },
  pending: {
    wrap: "bg-caution/8 text-caution ring-1 ring-inset ring-caution/25",
    icon: Wrench,
  },
};

export default function Alert({
  variant = "info",
  title,
  children,
  className = "",
}) {
  if (!children && !title) return null;
  const { wrap, icon: Icon } = styles[variant] ?? styles.info;

  return (
    <div
      className={`flex items-start gap-3 rounded-xl px-4 py-3 text-sm ${wrap} ${className}`}
      role={variant === "error" ? "alert" : "status"}
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0" strokeWidth={2.25} />
      <div className="min-w-0">
        {title && <p className="font-semibold leading-snug">{title}</p>}
        {children && (
          <p className={`leading-snug ${title ? "mt-1 opacity-85" : ""}`}>
            {children}
          </p>
        )}
      </div>
    </div>
  );
}
