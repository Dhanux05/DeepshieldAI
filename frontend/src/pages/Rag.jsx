import { useState } from "react";
import {
  BookOpen,
  Search,
  Sparkles,
  RefreshCw,
  FileText,
} from "lucide-react";
import apiClient, { apiError } from "../api/client";
import {
  Card,
  Button,
  Badge,
  PageHeader,
  EmptyState,
  Alert,
  Input,
  Label,
} from "../components/ui";
import { Skeleton } from "../components/ui/Skeleton";

const SUGGESTED_QUESTIONS = [
  "Why does the video detector predict one class for everything?",
  "What does a Suspicious result mean?",
  "Why can an audio-only MP4 not be analyzed as video?",
  "What should a complete investigation include?",
  "Why can a genuine image receive a Deepfake result?",
];

export default function Rag() {
  const [question, setQuestion] = useState("");
  const [results, setResults] = useState([]);
  const [askedQuestion, setAskedQuestion] = useState("");
  const [hasSearched, setHasSearched] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [syncing, setSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState("");

  const ask = async (rawQuestion) => {
    const text = rawQuestion.trim();
    if (!text) {
      setError("Enter a question first.");
      return;
    }

    setLoading(true);
    setError("");
    setSyncStatus("");

    try {
      const { data } = await apiClient.post("/rag/query", { question: text });
      setResults(data.results);
      setAskedQuestion(data.question);
      setHasSearched(true);
    } catch (err) {
      setError(apiError(err, "Unable to query the knowledge base."));
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    ask(question);
  };

  const handleSuggested = (text) => {
    setQuestion(text);
    ask(text);
  };

  const handleSync = async () => {
    setSyncing(true);
    setError("");
    setSyncStatus("");

    try {
      const { data } = await apiClient.post("/rag/sync");
      const parts = [];
      if (data.synced.length) parts.push(`${data.synced.length} synced`);
      if (data.skipped.length) parts.push(`${data.skipped.length} unchanged`);
      if (data.removed_stale.length)
        parts.push(`${data.removed_stale.length} removed`);
      setSyncStatus(
        parts.length
          ? `Knowledge base sync complete — ${parts.join(", ")}.`
          : "Knowledge base sync complete — nothing to do."
      );
    } catch (err) {
      setError(apiError(err, "Unable to sync the knowledge base."));
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <div className="mx-auto max-w-5xl space-y-6">
        <PageHeader
          eyebrow="Retrieval"
          title="Knowledge base assistant"
          description="Ask about detection methods, model limitations, confidence scores, or investigation procedure. Answers are passages retrieved from the documentation — not model-generated text."
          actions={
            <Button
              variant="secondary"
              size="sm"
              icon={RefreshCw}
              loading={syncing}
              onClick={handleSync}
            >
              Sync knowledge base
            </Button>
          }
        />

        {error && <Alert variant="error">{error}</Alert>}
        {syncStatus && <Alert variant="success">{syncStatus}</Alert>}

        <Card>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="question" hint="retrieval only — no generated text">
                Ask a question
              </Label>
              <div className="flex flex-col gap-3 sm:flex-row">
                <div className="min-w-0 flex-1">
                  <Input
                    id="question"
                    icon={Search}
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    placeholder="e.g. Why can two different files receive the same result?"
                  />
                </div>
                <Button type="submit" icon={Sparkles} loading={loading}>
                  Ask
                </Button>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {SUGGESTED_QUESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => handleSuggested(suggestion)}
                  className="rounded-full border border-line bg-hover/[0.04] px-3 py-1.5 text-xs text-slate-400 transition hover:border-volt-500/40 hover:text-volt-300"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </form>
        </Card>

        <Card padding="p-0">
          <div className="flex items-center justify-between px-6 pb-3 pt-5">
            <p className="hud-label">
              {hasSearched ? `Results for "${askedQuestion}"` : "Results"}
            </p>
            {hasSearched && <Badge tone="neutral">{results.length}</Badge>}
          </div>
          <div className="neon-rule" />

          {loading ? (
            <div className="space-y-3 p-6">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-24 w-full" />
              ))}
            </div>
          ) : !hasSearched ? (
            <div className="p-6">
              <EmptyState
                icon={BookOpen}
                title="Ask a question to get started"
                description="Try one of the suggested questions above, or ask your own about detection methods, limitations, or investigation procedure."
              />
            </div>
          ) : results.length > 0 ? (
            <div className="divide-y divide-line">
              {results.map((passage, index) => (
                <div key={`${passage.source}-${passage.chunk_index}-${index}`} className="px-6 py-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <FileText className="h-3.5 w-3.5" />
                      <span className="font-mono">{passage.source}</span>
                      <span className="text-slate-700">·</span>
                      <span>chunk {passage.chunk_index}</span>
                    </div>
                    <Badge tone={passage.relevance >= 0.5 ? "success" : "neutral"}>
                      {Math.round(passage.relevance * 100)}% relevant
                    </Badge>
                  </div>
                  <p className="mt-2 text-sm leading-relaxed text-slate-300">
                    {passage.text}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-6">
              <EmptyState
                icon={BookOpen}
                title="No relevant passages found"
                description="Try rephrasing the question, or sync the knowledge base if it was just updated."
              />
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
