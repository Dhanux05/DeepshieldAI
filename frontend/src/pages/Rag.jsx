import { useCallback, useEffect, useMemo, useState } from "react";
import {
  BookOpen,
  Search,
  Database,
  Layers,
  Plus,
  RefreshCw,
  Trash2,
  Cpu,
} from "lucide-react";
import apiClient, { apiError } from "../api/client";
import {
  Card,
  Button,
  Badge,
  PageHeader,
  EmptyState,
  Alert,
  StatCard,
  Input,
  Select,
  Label,
} from "../components/ui";
import { Skeleton } from "../components/ui/Skeleton";
import { formatRelative } from "../lib/format";

const EMBEDDING_MODELS = [
  "all-MiniLM-L6-v2",
  "all-mpnet-base-v2",
  "bge-small-en-v1.5",
];

const INDEX_STATUSES = ["Pending", "Indexed", "Failed"];

export default function Rag() {
  const [entries, setEntries] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [query, setQuery] = useState("");

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [deleting, setDeleting] = useState(null);

  // Index-entry form
  const [showForm, setShowForm] = useState(false);
  const [documentId, setDocumentId] = useState("");
  const [embeddingModel, setEmbeddingModel] = useState(EMBEDDING_MODELS[0]);
  const [chunkCount, setChunkCount] = useState(12);
  const [indexStatus, setIndexStatus] = useState("Indexed");
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    setError("");
    try {
      const [entriesRes, documentsRes] = await Promise.all([
        apiClient.get("/knowledge-base/"),
        apiClient.get("/documents/", { params: { limit: 100 } }),
      ]);
      setEntries(entriesRes.data);
      setDocuments(documentsRes.data);
      setDocumentId((current) => current || String(documentsRes.data[0]?.id ?? ""));
    } catch (err) {
      setError(apiError(err, "Unable to load the knowledge base."));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const documentNames = useMemo(() => {
    const map = new Map();
    documents.forEach((d) => map.set(d.id, d.original_file_name));
    return map;
  }, [documents]);

  // Lexical filter only. Real semantic search arrives in phase 9 — labelling
  // a substring match as "semantic retrieval" would be a lie.
  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return entries;
    return entries.filter((entry) =>
      [
        entry.vector_id,
        entry.embedding_model,
        entry.index_status,
        documentNames.get(entry.document_id),
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(term))
    );
  }, [entries, query, documentNames]);

  const totalChunks = useMemo(
    () => entries.reduce((sum, entry) => sum + (entry.chunk_count ?? 0), 0),
    [entries]
  );

  const indexedCount = entries.filter(
    (entry) => entry.index_status === "Indexed"
  ).length;

  const handleCreate = async (event) => {
    event.preventDefault();
    if (!documentId) {
      setError("Select a source document.");
      return;
    }

    setSubmitting(true);
    setError("");
    setStatus("");

    try {
      await apiClient.post("/knowledge-base/", {
        document_id: Number(documentId),
        // Until ChromaDB exists (phase 9) the vector id is a deterministic
        // placeholder that the real ingestion pipeline will overwrite.
        vector_id: `doc-${documentId}-${Date.now().toString(36)}`,
        embedding_model: embeddingModel,
        chunk_count: Number(chunkCount),
        index_status: indexStatus,
      });
      setStatus("Knowledge entry registered.");
      setShowForm(false);
      await load(true);
    } catch (err) {
      setError(apiError(err, "Unable to register this entry."));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    setDeleting(id);
    setError("");
    try {
      await apiClient.delete(`/knowledge-base/${id}`);
      await load(true);
    } catch (err) {
      setError(apiError(err, "Delete failed."));
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <PageHeader
          eyebrow="Retrieval"
          title="Grounded knowledge base"
          description="Indexed sources used to support and cite detection verdicts."
          actions={
            <>
              <Button
                variant="secondary"
                size="sm"
                icon={RefreshCw}
                loading={refreshing}
                onClick={() => load(true)}
              >
                Refresh
              </Button>
              <Button
                size="sm"
                icon={Plus}
                onClick={() => setShowForm((prev) => !prev)}
              >
                Index a document
              </Button>
            </>
          }
        />

        {error && <Alert variant="error">{error}</Alert>}
        {status && <Alert variant="success">{status}</Alert>}

        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Entries"
            value={entries.length}
            hint="Registered sources"
            icon={BookOpen}
            accent="neon"
          />
          <StatCard
            label="Indexed"
            value={indexedCount}
            hint="Ready for retrieval"
            icon={Database}
            accent="clear"
          />
          <StatCard
            label="Total chunks"
            value={totalChunks}
            hint="Across all entries"
            icon={Layers}
            accent="volt"
          />
          <StatCard
            label="Vector store"
            value="Offline"
            hint="ChromaDB — phase 9"
            icon={Cpu}
            accent="caution"
          />
        </div>

        {showForm && (
          <Card glow>
            <p className="hud-label text-neon-400">Register knowledge entry</p>
            <form
              onSubmit={handleCreate}
              className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4"
            >
              <div>
                <Label htmlFor="document">Source document</Label>
                <Select
                  id="document"
                  value={documentId}
                  onChange={(event) => setDocumentId(event.target.value)}
                >
                  {documents.length === 0 && <option value="">No documents</option>}
                  {documents.map((document) => (
                    <option key={document.id} value={document.id}>
                      #{document.id} · {document.original_file_name}
                    </option>
                  ))}
                </Select>
              </div>

              <div>
                <Label htmlFor="model">Embedding model</Label>
                <Select
                  id="model"
                  value={embeddingModel}
                  onChange={(event) => setEmbeddingModel(event.target.value)}
                >
                  {EMBEDDING_MODELS.map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </Select>
              </div>

              <div>
                <Label htmlFor="chunks">Chunk count</Label>
                <Input
                  id="chunks"
                  type="number"
                  min="1"
                  max="10000"
                  value={chunkCount}
                  onChange={(event) => setChunkCount(event.target.value)}
                />
              </div>

              <div>
                <Label htmlFor="status">Index status</Label>
                <Select
                  id="status"
                  value={indexStatus}
                  onChange={(event) => setIndexStatus(event.target.value)}
                >
                  {INDEX_STATUSES.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </Select>
              </div>

              <div className="md:col-span-2 xl:col-span-4">
                <Button
                  type="submit"
                  loading={submitting}
                  disabled={documents.length === 0}
                >
                  Register entry
                </Button>
              </div>
            </form>
          </Card>
        )}

        {/* Query surface */}
        <Card>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="min-w-0 flex-1">
              <Label htmlFor="query" hint="lexical match">
                Search the knowledge base
              </Label>
              <Input
                id="query"
                icon={Search}
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="e.g. jawline artefacts, MiniLM, indexed…"
              />
            </div>
            <Badge tone="warning">semantic search · phase 9</Badge>
          </div>

          <p className="mt-3 text-xs leading-relaxed text-slate-500">
            This filters registered entries by substring. Embedding-based
            retrieval with cited passages requires the ChromaDB vector store
            and the ingestion pipeline built in phase 9 — the{" "}
            <code className="font-mono">rag/</code> package is currently empty.
          </p>
        </Card>

        {/* Entries */}
        <Card padding="p-0">
          <div className="flex items-center justify-between px-6 pb-3 pt-5">
            <p className="hud-label">Registered entries</p>
            <Badge tone="neutral">{filtered.length}</Badge>
          </div>
          <div className="neon-rule" />

          {loading ? (
            <div className="space-y-3 p-6">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-14 w-full" />
              ))}
            </div>
          ) : filtered.length > 0 ? (
            <div className="divide-y divide-line">
              {filtered.map((entry) => (
                <div
                  key={entry.id}
                  className="group flex flex-wrap items-center gap-4 px-6 py-4 transition hover:bg-hover/[0.03]"
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-volt-500/25 bg-volt-500/10 text-volt-400">
                    <BookOpen className="h-[18px] w-[18px]" />
                  </div>

                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-slate-200">
                      {documentNames.get(entry.document_id) ??
                        `Document #${entry.document_id}`}
                    </p>
                    <p className="truncate font-mono text-[0.68rem] text-slate-600">
                      {entry.vector_id}
                    </p>
                  </div>

                  <div className="hidden sm:block">
                    <p className="hud-label">Model</p>
                    <p className="mt-0.5 font-mono text-xs text-slate-400">
                      {entry.embedding_model}
                    </p>
                  </div>

                  <div className="hidden md:block">
                    <p className="hud-label">Chunks</p>
                    <p className="mt-0.5 font-mono text-xs text-slate-400">
                      {entry.chunk_count}
                    </p>
                  </div>

                  <Badge
                    tone={
                      entry.index_status === "Indexed"
                        ? "success"
                        : entry.index_status === "Failed"
                          ? "danger"
                          : "neutral"
                    }
                  >
                    {entry.index_status}
                  </Badge>

                  <span className="hidden shrink-0 font-mono text-[0.68rem] text-slate-600 lg:block">
                    {formatRelative(entry.created_at)}
                  </span>

                  <button
                    onClick={() => handleDelete(entry.id)}
                    disabled={deleting === entry.id}
                    className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-slate-600 opacity-0 transition hover:bg-threat/10 hover:text-threat focus:opacity-100 group-hover:opacity-100 disabled:opacity-40"
                    aria-label="Delete entry"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-6">
              <EmptyState
                icon={BookOpen}
                title={query ? "No matching entries" : "Knowledge base is empty"}
                description={
                  query
                    ? "Try a different term."
                    : "Register an indexed document to enable grounded citations."
                }
                action={
                  !query && (
                    <Button size="sm" icon={Plus} onClick={() => setShowForm(true)}>
                      Index a document
                    </Button>
                  )
                }
              />
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
