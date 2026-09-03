import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ScanSearch,
  Search,
  UploadCloud,
  Cpu,
  Radar,
  ServerCog,
  RefreshCw,
  FileStack,
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
  Input,
} from "../components/ui";
import { Skeleton } from "../components/ui/Skeleton";
import { verdictOf, statusTone } from "../lib/verdict";
import { formatBytes, formatRelative, formatSeconds, fileMeta } from "../lib/format";

export default function Predict() {
  const [documents, setDocuments] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [history, setHistory] = useState([]);
  const [result, setResult] = useState(null);

  const [query, setQuery] = useState("");
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");
  // Set when the API answers 503 — an unloaded model is a distinct state
  // from a failure, and the UI should say so rather than showing a red error.
  const [engineOffline, setEngineOffline] = useState("");
  // Live registry status from GET /predictions/models.
  const [models, setModels] = useState([]);

  const loadDocuments = useCallback(async () => {
    setLoadingDocs(true);
    try {
      const response = await apiClient.get("/documents/", {
        params: { limit: 100 },
      });
      setDocuments(response.data);
      setSelectedId((current) => current ?? response.data[0]?.id ?? null);
    } catch (err) {
      setError(apiError(err, "Unable to load documents."));
    } finally {
      setLoadingDocs(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // Which detectors are actually loaded on the server right now.
  useEffect(() => {
    apiClient
      .get("/predictions/models")
      .then((response) => setModels(response.data.detectors ?? []))
      .catch(() => setModels([]));
  }, []);

  // Prior runs for the selected document.
  useEffect(() => {
    if (!selectedId) {
      setHistory([]);
      return;
    }

    let cancelled = false;
    setLoadingHistory(true);
    setResult(null);
    setEngineOffline("");

    apiClient
      .get(`/predictions/document/${selectedId}`)
      .then((response) => {
        if (!cancelled) setHistory(response.data);
      })
      .catch(() => {
        if (!cancelled) setHistory([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingHistory(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return documents;
    return documents.filter((document) =>
      document.original_file_name.toLowerCase().includes(term)
    );
  }, [documents, query]);

  const selected = documents.find((document) => document.id === selectedId);

  const handleAnalyze = async () => {
    if (!selectedId) return;

    setAnalyzing(true);
    setError("");
    setEngineOffline("");
    setResult(null);

    try {
      const response = await apiClient.post(`/predictions/analyze/${selectedId}`);
      setResult(response.data);
      const refreshed = await apiClient.get(
        `/predictions/document/${selectedId}`
      );
      setHistory(refreshed.data);
    } catch (err) {
      if (err.response?.status === 503) {
        setEngineOffline(apiError(err));
      } else {
        setError(apiError(err, "Analysis request failed."));
      }
    } finally {
      setAnalyzing(false);
    }
  };

  const latest = result ?? history[0] ?? null;
  const verdict = verdictOf(latest?.predicted_label);
  const VerdictIcon = verdict.icon;

  return (
    <div className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <PageHeader
          eyebrow="Inference"
          title="Run detection on ingested media"
          description="Select a document and dispatch it to the multimodal detection pipeline."
          actions={
            <>
              <Button
                variant="secondary"
                size="sm"
                icon={RefreshCw}
                onClick={loadDocuments}
              >
                Reload
              </Button>
              <Button as={Link} to="/upload" size="sm" icon={UploadCloud}>
                Upload
              </Button>
            </>
          }
        />

        {error && <Alert variant="error">{error}</Alert>}

        <div className="grid gap-5 lg:grid-cols-[0.85fr_1.15fr]">
          {/* Document picker */}
          <Card padding="p-0" className="flex max-h-[36rem] flex-col">
            <div className="px-5 pb-3 pt-5">
              <div className="flex items-center justify-between">
                <p className="hud-label text-neon-400">Select target</p>
                <Badge tone="neutral">{filtered.length}</Badge>
              </div>
              <div className="mt-3">
                <Input
                  icon={Search}
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Filter by filename…"
                  type="search"
                />
              </div>
            </div>
            <div className="neon-rule" />

            <div className="flex-1 divide-y divide-line overflow-y-auto">
              {loadingDocs ? (
                <div className="space-y-3 p-5">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : filtered.length > 0 ? (
                filtered.map((document) => {
                  const meta = fileMeta(document.original_file_name);
                  const Icon = meta.icon;
                  const active = document.id === selectedId;

                  return (
                    <button
                      key={document.id}
                      onClick={() => setSelectedId(document.id)}
                      className={`flex w-full items-center gap-3 px-5 py-3 text-left transition ${
                        active
                          ? "bg-gradient-to-r from-neon-500/15 to-transparent"
                          : "hover:bg-hover/[0.03]"
                      }`}
                    >
                      <div
                        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border ${meta.accent}`}
                      >
                        <Icon className="h-[18px] w-[18px]" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p
                          className={`truncate text-sm font-semibold ${
                            active ? "text-slate-50" : "text-slate-300"
                          }`}
                        >
                          {document.original_file_name}
                        </p>
                        <p className="font-mono text-[0.68rem] text-slate-600">
                          #{document.id} · {formatBytes(document.file_size)} ·{" "}
                          {meta.type}
                        </p>
                      </div>
                      {active && (
                        <span className="h-2 w-2 shrink-0 rounded-full bg-neon-500" />
                      )}
                    </button>
                  );
                })
              ) : (
                <div className="p-5">
                  <EmptyState
                    icon={FileStack}
                    title={query ? "No matches" : "No documents ingested"}
                    description={
                      query
                        ? "Try a different filename."
                        : "Upload a file before running detection."
                    }
                    action={
                      !query && (
                        <Button as={Link} to="/upload" size="sm" icon={UploadCloud}>
                          Upload a file
                        </Button>
                      )
                    }
                  />
                </div>
              )}
            </div>
          </Card>

          {/* Analysis panel */}
          <div className="space-y-5">
            <Card glow>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="hud-label text-volt-400">Analysis target</p>
                  <p className="mt-2.5 truncate font-display text-lg font-bold text-slate-50">
                    {selected?.original_file_name ?? "No document selected"}
                  </p>
                  {selected && (
                    <p className="mt-1 font-mono text-xs text-slate-500">
                      {fileMeta(selected.original_file_name).type} ·{" "}
                      {formatBytes(selected.file_size)} · uploaded{" "}
                      {formatRelative(selected.uploaded_at)}
                    </p>
                  )}
                </div>

                <Button
                  size="lg"
                  icon={!analyzing ? Radar : undefined}
                  loading={analyzing}
                  disabled={!selectedId}
                  onClick={handleAnalyze}
                >
                  {analyzing ? "Analyzing…" : "Run detection"}
                </Button>
              </div>

              {engineOffline && (
                <Alert
                  variant="pending"
                  title="Detector unavailable for this file type"
                  className="mt-5"
                >
                  {engineOffline}
                </Alert>
              )}

              {latest ? (
                <div className="mt-5 rounded-2xl border border-line/10 bg-void-900/50 p-5">
                  <div className="flex items-center justify-between">
                    <p className="hud-label">
                      {result ? "Result" : "Most recent run"}
                    </p>
                    <Badge tone={statusTone(latest.processing_status)} dot>
                      {latest.processing_status}
                    </Badge>
                  </div>

                  <div className="mt-4 flex items-center gap-4">
                    <div
                      className={`flex h-14 w-14 items-center justify-center rounded-2xl border ${verdict.ring}`}
                    >
                      <VerdictIcon className="h-7 w-7" strokeWidth={2} />
                    </div>
                    <div className="min-w-0">
                      <p
                        className={`font-display text-2xl font-bold ${verdict.text} text-glow`}
                      >
                        {latest.predicted_label}
                      </p>
                      <p className="truncate font-mono text-xs text-slate-500">
                        {latest.model_name} ·{" "}
                        {formatSeconds(latest.processing_time)}
                      </p>
                    </div>
                  </div>

                  <div className="mt-5">
                    <ConfidenceMeter
                      value={latest.confidence_score}
                      tone={verdict.tone}
                    />
                  </div>
                </div>
              ) : (
                !engineOffline && (
                  <div className="mt-5 rounded-2xl border border-dashed border-line/10 bg-void-900/40 p-8 text-center">
                    <ScanSearch className="mx-auto h-8 w-8 text-slate-700" />
                    <p className="mt-3 text-sm font-semibold text-slate-400">
                      No result for this document
                    </p>
                    <p className="mt-1 text-sm text-slate-600">
                      Run detection to produce a verdict.
                    </p>
                  </div>
                )
              )}
            </Card>

            {/* Detector registry — live status straight from the server */}
            <Card>
              <div className="flex items-center justify-between">
                <div>
                  <p className="hud-label text-neon-400">Detector registry</p>
                  <p className="mt-1.5 text-xs text-slate-400">
                    Models currently loaded in the API process
                  </p>
                </div>
                <Badge tone={models.some((m) => m.ready) ? "success" : "warning"}>
                  {models.filter((m) => m.ready).length}/{models.length} ready
                </Badge>
              </div>

              <div className="mt-4 grid gap-2.5 sm:grid-cols-2">
                {models.length > 0 ? (
                  models.map((model) => (
                    <div
                      key={model.modality}
                      className="flex items-start gap-3 rounded-xl border border-line/8 bg-void-700/40 px-3.5 py-3 transition-all duration-200 hover:-translate-y-0.5 hover:border-neon-500/30"
                      title={model.error ?? undefined}
                    >
                      {model.ready ? (
                        <Cpu className="mt-0.5 h-4 w-4 shrink-0 text-clear" />
                      ) : (
                        <ServerCog className="mt-0.5 h-4 w-4 shrink-0 text-slate-600" />
                      )}
                      <div className="min-w-0 flex-1">
                        <p
                          className={`truncate text-sm font-semibold ${
                            model.ready ? "text-slate-100" : "text-slate-500"
                          }`}
                        >
                          {model.modality}
                        </p>
                        <p className="truncate font-mono text-[0.64rem] text-slate-600">
                          {model.model_name}
                        </p>
                        {!model.ready && model.error && (
                          <p className="mt-1 line-clamp-2 text-[0.66rem] leading-snug text-caution/80">
                            {model.error}
                          </p>
                        )}
                      </div>
                      <Badge tone={model.ready ? "success" : "neutral"}>
                        {model.ready ? "live" : "offline"}
                      </Badge>
                    </div>
                  ))
                ) : (
                  <p className="col-span-full py-4 text-center text-sm text-slate-500">
                    Registry status unavailable.
                  </p>
                )}
              </div>
            </Card>

            {/* Prior runs for this document */}
            <Card padding="p-0">
              <div className="flex items-center justify-between px-6 pb-3 pt-5">
                <p className="hud-label">Run history for this document</p>
                <Badge tone="neutral">{history.length}</Badge>
              </div>
              <div className="neon-rule" />

              <div className="max-h-64 divide-y divide-line overflow-y-auto">
                {loadingHistory ? (
                  <div className="space-y-3 p-5">
                    {Array.from({ length: 2 }).map((_, i) => (
                      <Skeleton key={i} className="h-10 w-full" />
                    ))}
                  </div>
                ) : history.length > 0 ? (
                  history.map((run) => {
                    const runVerdict = verdictOf(run.predicted_label);
                    return (
                      <div
                        key={run.id}
                        className="flex items-center gap-3 px-6 py-3"
                      >
                        <span
                          className={`h-2 w-2 shrink-0 rounded-full`}
                          style={{ backgroundColor: runVerdict.chart }}
                        />
                        <span
                          className={`w-24 shrink-0 text-sm font-semibold ${runVerdict.text}`}
                        >
                          {run.predicted_label}
                        </span>
                        <span className="font-mono text-xs text-slate-400">
                          {(run.confidence_score * 100).toFixed(1)}%
                        </span>
                        <span className="hidden min-w-0 flex-1 truncate font-mono text-xs text-slate-600 sm:block">
                          {run.model_name}
                        </span>
                        <span className="ml-auto shrink-0 font-mono text-[0.68rem] text-slate-600">
                          {formatRelative(run.created_at)}
                        </span>
                      </div>
                    );
                  })
                ) : (
                  <div className="p-5">
                    <EmptyState
                      icon={Radar}
                      title="No previous runs"
                      description="Results for this document will be listed here."
                    />
                  </div>
                )}
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
