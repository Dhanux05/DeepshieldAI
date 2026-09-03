import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Flame,
  BarChart3,
  Boxes,
  RefreshCw,
  FileText,
  Star,
  Bot,
  ScanSearch,
  Lock,
  Sparkles,
} from "lucide-react";
import apiClient, { apiError } from "../api/client";
import {
  Card,
  Button,
  Badge,
  PageHeader,
  EmptyState,
  Alert,
  ConfidenceMeter,
  Select,
  Label,
} from "../components/ui";
import { Skeleton } from "../components/ui/Skeleton";
import { verdictOf, statusTone } from "../lib/verdict";
import { formatDateTime, formatSeconds } from "../lib/format";

/**
 * The three attribution methods the project promises.
 *
 * Rendered as honest placeholders until phase 7 fills xai/gradcam.py,
 * xai/shap_explainer.py and xai/lime_explainer.py — all three are currently
 * empty files. Showing a fake heatmap here would be worse than showing none.
 */
const METHODS = [
  {
    key: "gradcam",
    name: "Grad-CAM",
    icon: Flame,
    question: "Which pixels drove this decision?",
    detail:
      "Gradient-weighted activations from the final convolutional block, upsampled and alpha-blended over the input image.",
    accent: "border-threat/25 bg-threat/10 text-threat",
    available: true,
    modality: "Image",
  },
  {
    key: "shap",
    name: "SHAP",
    icon: BarChart3,
    question: "How much did each token contribute?",
    detail:
      "Shapley values give an additive, theoretically grounded attribution per token, against a masked-token background.",
    accent: "border-volt-500/25 bg-volt-500/10 text-volt-400",
    available: true,
    modality: "Text / Review",
  },
  {
    key: "lime",
    name: "LIME",
    icon: Boxes,
    question: "What simple model mimics this decision locally?",
    detail:
      "Perturbs superpixels or tokens and fits an interpretable surrogate around this single prediction.",
    accent: "border-neon-500/25 bg-neon-500/10 text-neon-400",
    available: false,
    modality: null,
  },
];

export default function Explain() {
  const [predictions, setPredictions] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [reviews, setReviews] = useState([]);
  const [bots, setBots] = useState([]);
  const [reports, setReports] = useState([]);
  const [explanations, setExplanations] = useState([]);

  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [generatingMethod, setGeneratingMethod] = useState("");
  const [generateError, setGenerateError] = useState("");

  const loadPredictions = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.get("/predictions/", {
        params: { limit: 100 },
      });
      setPredictions(response.data);
      setSelectedId((current) => current || String(response.data[0]?.id ?? ""));
    } catch (err) {
      setError(apiError(err, "Unable to load predictions."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPredictions();
  }, [loadPredictions]);

  // Everything the API can currently attach to a prediction.
  useEffect(() => {
    if (!selectedId) return;

    let cancelled = false;
    setDetailLoading(true);

    Promise.all([
      apiClient
        .get(`/review-analysis/prediction/${selectedId}`)
        .catch(() => ({ data: [] })),
      apiClient
        .get(`/bot-analysis/prediction/${selectedId}`)
        .catch(() => ({ data: [] })),
      apiClient
        .get(`/reports/prediction/${selectedId}`)
        .catch(() => ({ data: [] })),
      apiClient
        .get(`/explanations/prediction/${selectedId}`)
        .catch(() => ({ data: [] })),
    ])
      .then(([reviewRes, botRes, reportRes, explanationRes]) => {
        if (cancelled) return;
        setReviews(reviewRes.data ?? []);
        setBots(botRes.data ?? []);
        setReports(reportRes.data ?? []);
        setExplanations(explanationRes.data ?? []);
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  const handleGenerate = async (methodKey) => {
    if (!selectedId) return;

    setGeneratingMethod(methodKey);
    setGenerateError("");

    try {
      const response = await apiClient.post(
        `/explanations/generate/${selectedId}`,
        null,
        { params: { method: methodKey } }
      );
      // Newest first, replacing any earlier run of the same method for
      // this prediction so the card always shows the latest artefact.
      setExplanations((current) => [
        response.data,
        ...current.filter((item) => item.method !== methodKey),
      ]);
    } catch (err) {
      setGenerateError(apiError(err, `Unable to generate ${methodKey}.`));
    } finally {
      setGeneratingMethod("");
    }
  };

  const selected = predictions.find(
    (item) => String(item.id) === String(selectedId)
  );
  const verdict = verdictOf(selected?.predicted_label);
  const VerdictIcon = verdict.icon;

  return (
    <div className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <PageHeader
          eyebrow="Explainability"
          title="Why the model decided what it decided"
          description="Attribution overlays, feature contributions and supporting evidence for a single prediction."
          actions={
            <Button
              variant="secondary"
              size="sm"
              icon={RefreshCw}
              onClick={loadPredictions}
            >
              Reload
            </Button>
          }
        />

        {error && <Alert variant="error">{error}</Alert>}

        {loading ? (
          <div className="space-y-5">
            <Skeleton className="h-28 w-full" />
            <div className="grid gap-5 lg:grid-cols-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-56 w-full" />
              ))}
            </div>
          </div>
        ) : predictions.length === 0 ? (
          <Card>
            <EmptyState
              icon={ScanSearch}
              title="No predictions to explain"
              description="Explainability operates on a completed prediction. Run detection first."
              action={
                <Button as={Link} to="/predict" size="sm" icon={ScanSearch}>
                  Go to Analyze
                </Button>
              }
            />
          </Card>
        ) : (
          <>
            {/* Subject selector + verdict summary */}
            <Card glow>
              <div className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
                <div>
                  <Label htmlFor="prediction">Prediction under inspection</Label>
                  <Select
                    id="prediction"
                    value={selectedId}
                    onChange={(event) => setSelectedId(event.target.value)}
                  >
                    {predictions.map((item) => (
                      <option key={item.id} value={item.id}>
                        #{item.id} · {item.predicted_label} ·{" "}
                        {(item.confidence_score * 100).toFixed(1)}% ·{" "}
                        {item.model_name}
                      </option>
                    ))}
                  </Select>

                  {selected && (
                    <div className="mt-4 grid grid-cols-2 gap-3">
                      <Meta label="Document" value={`#${selected.document_id}`} />
                      <Meta label="Model" value={selected.model_name} />
                      <Meta
                        label="Latency"
                        value={formatSeconds(selected.processing_time)}
                      />
                      <Meta
                        label="Recorded"
                        value={formatDateTime(selected.created_at)}
                      />
                    </div>
                  )}
                </div>

                {selected && (
                  <div className="rounded-2xl border border-line/10 bg-void-900/50 p-5">
                    <div className="flex items-center justify-between">
                      <p className="hud-label">Verdict</p>
                      <Badge tone={statusTone(selected.processing_status)} dot>
                        {selected.processing_status}
                      </Badge>
                    </div>
                    <div className="mt-4 flex items-center gap-4">
                      <div
                        className={`flex h-14 w-14 items-center justify-center rounded-2xl border ${verdict.ring}`}
                      >
                        <VerdictIcon className="h-7 w-7" strokeWidth={2} />
                      </div>
                      <p
                        className={`font-display text-2xl font-bold ${verdict.text} text-glow`}
                      >
                        {selected.predicted_label}
                      </p>
                    </div>
                    <div className="mt-5">
                      <ConfidenceMeter
                        value={selected.confidence_score}
                        tone={verdict.tone}
                      />
                    </div>
                  </div>
                )}
              </div>
            </Card>

            {/* The three attribution methods */}
            {generateError && <Alert variant="error">{generateError}</Alert>}

            <div className="grid gap-5 lg:grid-cols-3">
              {METHODS.map((method) => {
                const Icon = method.icon;
                const explanation = explanations.find(
                  (item) => item.method === method.key
                );
                const isGenerating = generatingMethod === method.key;

                return (
                  <Card key={method.key} className="flex flex-col">
                    <div className="flex items-start justify-between gap-3">
                      <div
                        className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border ${method.accent}`}
                      >
                        <Icon className="h-5 w-5" strokeWidth={2} />
                      </div>
                      {!method.available ? (
                        <Badge tone="warning">phase 7 — deferred</Badge>
                      ) : explanation ? (
                        <Badge tone="brand">generated</Badge>
                      ) : (
                        <Badge tone="neutral">{method.modality}</Badge>
                      )}
                    </div>

                    <p className="mt-4 font-display text-lg font-bold text-slate-50">
                      {method.name}
                    </p>
                    <p className="mt-1.5 text-sm font-medium text-slate-400">
                      {method.question}
                    </p>
                    <p className="mt-3 text-xs leading-relaxed text-slate-500">
                      {method.detail}
                    </p>

                    {!method.available ? (
                      // Placeholder canvas — deliberately empty, not fabricated
                      <div className="mt-5 flex flex-1 items-center justify-center rounded-xl border border-dashed border-line/10 bg-void-900/50 py-10">
                        <div className="text-center">
                          <Lock className="mx-auto h-5 w-5 text-slate-700" />
                          <p className="mt-2 font-mono text-[0.68rem] uppercase tracking-wider text-slate-600">
                            no artefact
                          </p>
                        </div>
                      </div>
                    ) : explanation ? (
                      <div className="mt-5 flex-1">
                        <ExplanationArtifact explanation={explanation} />
                      </div>
                    ) : (
                      <div className="mt-5 flex flex-1 flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-line/10 bg-void-900/50 py-10">
                        <p className="max-w-[16rem] text-center font-mono text-[0.68rem] uppercase tracking-wider text-slate-600">
                          no artefact yet
                        </p>
                        <Button
                          type="button"
                          variant="secondary"
                          size="sm"
                          icon={Sparkles}
                          loading={isGenerating}
                          disabled={Boolean(generatingMethod)}
                          onClick={() => handleGenerate(method.key)}
                        >
                          {isGenerating ? "Generating…" : "Generate"}
                        </Button>
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>

            <Alert variant="pending" title="LIME not implemented yet">
              Grad-CAM (Image) and SHAP (Text/Review) are live —{" "}
              <code className="font-mono text-xs">xai/gradcam.py</code> and{" "}
              <code className="font-mono text-xs">xai/shap_explainer.py</code>{" "}
              generate real artefacts on demand, stored in the{" "}
              <code className="font-mono text-xs">explanations</code> table.{" "}
              <code className="font-mono text-xs">xai/lime_explainer.py</code>{" "}
              is still empty — a deliberately scoped-out follow-up, not an
              oversight (see PROJECT_STATUS_RECHECK).
            </Alert>

            {/* Evidence that DOES exist today */}
            <div className="grid gap-5 lg:grid-cols-3">
              <EvidenceCard
                title="Linked reports"
                icon={FileText}
                count={reports.length}
                loading={detailLoading}
                emptyText="No report generated for this prediction."
                items={reports.map((report) => ({
                  id: report.id,
                  primary: report.report_title,
                  secondary: report.report_summary,
                }))}
              />
              <EvidenceCard
                title="Review forensics"
                icon={Star}
                count={reviews.length}
                loading={detailLoading}
                emptyText="No review analysis attached (phase 10)."
                items={reviews.map((review) => ({
                  id: review.id,
                  primary: review.summary,
                  secondary: review.recommendation,
                }))}
              />
              <EvidenceCard
                title="Bot analysis"
                icon={Bot}
                count={bots.length}
                loading={detailLoading}
                emptyText="No bot analysis attached (phase 10)."
                items={bots.map((bot) => ({
                  id: bot.id,
                  primary: bot.question,
                  secondary: bot.answer,
                }))}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function Meta({ label, value }) {
  return (
    <div className="rounded-xl border border-line/8 bg-void-900/40 px-3.5 py-2.5">
      <p className="hud-label">{label}</p>
      <p className="mt-1 truncate font-mono text-sm text-slate-200">{value}</p>
    </div>
  );
}

/**
 * Renders one generated explanation artefact. `artifact_type` decides the
 * shape: "image" is a base64 PNG (Grad-CAM's heatmap overlay), "tokens" is
 * a JSON-encoded array of {token, weight} (SHAP) — see
 * app/schemas/explanation.py for why the wire format keeps `artifact` as a
 * plain string either way instead of a union type.
 */
function ExplanationArtifact({ explanation }) {
  if (explanation.artifact_type === "image") {
    return (
      <img
        src={`data:image/png;base64,${explanation.artifact}`}
        alt={`${explanation.method} overlay`}
        className="w-full rounded-xl border border-line/10 bg-void-900/50"
      />
    );
  }

  if (explanation.artifact_type === "tokens") {
    let tokens = [];
    try {
      tokens = JSON.parse(explanation.artifact);
    } catch {
      return (
        <p className="text-xs text-slate-600">
          Could not parse the attribution payload.
        </p>
      );
    }

    const maxWeight =
      Math.max(1e-6, ...tokens.map((item) => Math.abs(item.weight))) || 1;

    return (
      <div className="rounded-xl border border-line/10 bg-void-900/50 p-4">
        <div className="flex flex-wrap gap-1.5 text-sm leading-relaxed">
          {tokens.map((item, index) => {
            const intensity = Math.min(
              1,
              Math.abs(item.weight) / maxWeight
            );
            // Positive weight = pushed the model toward the predicted
            // label; negative = pulled away from it.
            const background =
              item.weight >= 0
                ? `rgba(255, 90, 90, ${0.12 + intensity * 0.55})`
                : `rgba(90, 140, 255, ${0.1 + intensity * 0.4})`;
            return (
              <span
                key={index}
                title={item.weight.toFixed(4)}
                style={{ background }}
                className="rounded px-1 py-0.5 font-mono text-slate-100"
              >
                {item.token}
              </span>
            );
          })}
        </div>
        <p className="mt-3 flex items-center gap-3 font-mono text-[0.65rem] uppercase tracking-wider text-slate-600">
          <span className="flex items-center gap-1">
            <span
              className="h-2.5 w-2.5 rounded-sm"
              style={{ background: "rgba(255, 90, 90, 0.5)" }}
            />
            toward predicted label
          </span>
          <span className="flex items-center gap-1">
            <span
              className="h-2.5 w-2.5 rounded-sm"
              style={{ background: "rgba(90, 140, 255, 0.4)" }}
            />
            away from it
          </span>
        </p>
      </div>
    );
  }

  return (
    <p className="text-xs text-slate-600">
      Unknown artefact type "{explanation.artifact_type}".
    </p>
  );
}

function EvidenceCard({ title, icon: Icon, count, items, loading, emptyText }) {
  return (
    <Card>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Icon className="h-4 w-4 text-slate-500" />
          <p className="hud-label">{title}</p>
        </div>
        <Badge tone={count > 0 ? "brand" : "neutral"}>{count}</Badge>
      </div>

      <div className="mt-4 space-y-2.5">
        {loading ? (
          <Skeleton className="h-16 w-full" />
        ) : items.length > 0 ? (
          items.slice(0, 3).map((item) => (
            <div
              key={item.id}
              className="rounded-xl border border-line/8 bg-void-900/40 p-3.5"
            >
              <p className="truncate text-sm font-semibold text-slate-200">
                {item.primary}
              </p>
              <p className="mt-1 line-clamp-2 text-xs text-slate-500">
                {item.secondary}
              </p>
            </div>
          ))
        ) : (
          <p className="py-5 text-center text-sm text-slate-600">{emptyText}</p>
        )}
      </div>
    </Card>
  );
}
