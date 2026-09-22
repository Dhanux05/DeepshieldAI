/**
 * Small labelled checkbox, styled to match Field.jsx's `.field` inputs.
 *
 * Pulled out as its own primitive (rather than inline markup on the one page
 * that first needed it — the Account form in Upload.jsx) because a boolean
 * toggle is exactly as reusable as Input/Select/Textarea already are, and
 * the project's own architecture rule is "modular, scalable, clean" over
 * "fastest to type right now".
 */
export default function Checkbox({ checked, onChange, label, hint }) {
  return (
    <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-line/10 bg-void-900/40 px-3.5 py-3 transition hover:border-neon-500/30">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-0.5 h-4 w-4 shrink-0 rounded border-line/30 bg-void-700 accent-neon-500"
      />
      <span className="min-w-0">
        <span className="block text-sm font-medium text-slate-200">{label}</span>
        {hint && (
          <span className="mt-0.5 block text-xs text-slate-500">{hint}</span>
        )}
      </span>
    </label>
  );
}
