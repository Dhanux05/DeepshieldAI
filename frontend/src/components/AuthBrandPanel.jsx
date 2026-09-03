import { ShieldCheck, ScanFace, Waves, FileSearch } from "lucide-react";

const features = [
  {
    icon: ScanFace,
    title: "Multimodal detection",
    text: "Image, video, audio and text analysed by dedicated models, then fused.",
  },
  {
    icon: Waves,
    title: "Explainable by default",
    text: "Grad-CAM, SHAP and LIME expose why a verdict was reached.",
  },
  {
    icon: FileSearch,
    title: "Grounded evidence",
    text: "Retrieval-augmented citations back every forensic report.",
  },
];

export default function AuthBrandPanel() {
  return (
    <div className="theme-dark-scope relative hidden overflow-hidden border-r border-line/10 bg-void-800 lg:flex lg:w-[46%] lg:flex-col lg:justify-between lg:p-12">
      {/* neon washes */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage:
            "radial-gradient(ellipse 70% 50% at 15% 0%, rgba(0,117,255,0.32), transparent 60%), radial-gradient(ellipse 70% 60% at 90% 90%, rgba(88,44,255,0.3), transparent 60%)",
        }}
      />
      {/* perspective grid */}
      <div
        className="pointer-events-none absolute inset-x-0 bottom-0 h-1/2 opacity-25"
        style={{
          backgroundImage:
            "linear-gradient(rgba(0,117,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(88,44,255,0.4) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
          maskImage: "linear-gradient(to top, black, transparent)",
          WebkitMaskImage: "linear-gradient(to top, black, transparent)",
        }}
      />
      {/* horizon glow */}
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-64 w-[36rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-neon-500/20 blur-[100px]" />

      <div className="relative flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-neon-gradient shadow-tile">
          <ShieldCheck className="h-6 w-6 text-white" strokeWidth={2.25} />
        </div>
        <span className="font-display text-xl font-bold tracking-tight text-white">
          DEEPSHIELD<span className="text-neon-400">AI</span>
        </span>
      </div>

      <div className="relative">
        <p className="hud-label text-neon-400">Digital content authenticity</p>
        <h2 className="mt-4 font-display text-[2rem] font-bold leading-[1.15] text-white">
          Explainable
          <br />
          deepfake defense.
        </h2>
        <p className="mt-4 max-w-sm text-sm leading-relaxed text-slate-400">
          Detect synthetic media, verify authenticity, and surface the evidence
          behind every decision.
        </p>

        <ul className="mt-9 space-y-5">
          {features.map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.title} className="flex items-start gap-3.5">
                <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-line/10 bg-hover/5">
                  <Icon className="h-4 w-4 text-neon-400" strokeWidth={2} />
                </span>
                <div>
                  <p className="text-sm font-semibold text-slate-200">
                    {item.title}
                  </p>
                  <p className="mt-0.5 text-xs leading-relaxed text-slate-500">
                    {item.text}
                  </p>
                </div>
              </li>
            );
          })}
        </ul>
      </div>

      <p className="relative font-mono text-[0.68rem] text-slate-600">
        © {new Date().getFullYear()} DeepShieldAI · Final year engineering project
      </p>
    </div>
  );
}
