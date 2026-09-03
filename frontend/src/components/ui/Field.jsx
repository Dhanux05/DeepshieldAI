import { forwardRef } from "react";

export function Label({ children, htmlFor, hint }) {
  return (
    <div className="mb-1.5 flex items-baseline justify-between gap-3">
      <label
        htmlFor={htmlFor}
        className="text-xs font-semibold uppercase tracking-wide text-slate-400"
      >
        {children}
      </label>
      {hint && <span className="text-[0.7rem] text-slate-600">{hint}</span>}
    </div>
  );
}

export const Input = forwardRef(function Input(
  { icon: Icon, className = "", ...props },
  ref
) {
  return (
    <div className="relative">
      {Icon && (
        <Icon className="pointer-events-none absolute left-3.5 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-slate-600" />
      )}
      <input
        ref={ref}
        className={`field ${Icon ? "pl-11" : ""} ${className}`}
        {...props}
      />
    </div>
  );
});

export const Select = forwardRef(function Select(
  { className = "", children, ...props },
  ref
) {
  return (
    <select ref={ref} className={`field cursor-pointer ${className}`} {...props}>
      {children}
    </select>
  );
});

export const Textarea = forwardRef(function Textarea(
  { className = "", ...props },
  ref
) {
  return (
    <textarea
      ref={ref}
      className={`field min-h-[104px] resize-y ${className}`}
      {...props}
    />
  );
});
