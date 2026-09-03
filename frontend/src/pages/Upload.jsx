import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  UploadCloud,
  X,
  Clock3,
  ScanSearch,
  Trash2,
  HardDrive,
  ShieldCheck,
} from "lucide-react";
import apiClient, { apiError } from "../api/client";
import {
  Card,
  Button,
  Badge,
  PageHeader,
  EmptyState,
  Alert,
  Label,
  Textarea,
  Segmented,
} from "../components/ui";
import { Skeleton } from "../components/ui/Skeleton";
import { formatBytes, formatRelative, fileMeta } from "../lib/format";

const ACCEPTED = [
  { type: "Image", exts: "JPG · PNG · WEBP · BMP" },
  { type: "Video", exts: "MP4 · MKV · AVI · MOV" },
  { type: "Audio", exts: "MP3 · WAV · AAC · FLAC" },
  { type: "Text", exts: "TXT · PDF · DOCX · CSV" },
];

export default function Upload() {
  const [file, setFile] = useState(null);
  const [description, setDescription] = useState("");
  const [documents, setDocuments] = useState([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [listLoading, setListLoading] = useState(true);
  const [dragActive, setDragActive] = useState(false);
  const [inputKey, setInputKey] = useState(() => Date.now());
  const [deletingId, setDeletingId] = useState(null);
  const [documentTypes, setDocumentTypes] = useState([]);
  // Only meaningful for plain-text uploads (.txt/.csv/.json/.xml etc.) —
  // extension alone can't tell a news article apart from a product review,
  // so the person uploading has to say which one this is. Everything else
  // (image/video/audio) keeps being typed automatically by extension.
  const [contentCategory, setContentCategory] = useState("text");

  const dragCounter = useRef(0);
  const navigate = useNavigate();

  const loadDocuments = useCallback(async () => {
    try {
      const response = await apiClient.get("/documents/", {
        params: { limit: 12 },
      });
      setDocuments(response.data);
    } catch (err) {
      setError(apiError(err, "Unable to load documents."));
    } finally {
      setListLoading(false);
    }
  }, []);

  const loadDocumentTypes = useCallback(async () => {
    try {
      const response = await apiClient.get("/document-types/");
      setDocumentTypes(response.data);
    } catch {
      // Non-fatal — worst case the Text/Review choice below can't resolve
      // an id and upload falls back to the auto-detected type.
    }
  }, []);

  useEffect(() => {
    loadDocuments();
    loadDocumentTypes();
  }, [loadDocuments, loadDocumentTypes]);

  const handleFile = (selected) => {
    if (!selected) return;
    setFile(selected);
    setStatus("");
    setError("");
  };

  // A counter is needed because dragleave fires for every child element the
  // pointer crosses; a naive boolean makes the highlight flicker.
  const onDragEnter = (event) => {
    event.preventDefault();
    dragCounter.current += 1;
    setDragActive(true);
  };

  const onDragLeave = (event) => {
    event.preventDefault();
    dragCounter.current -= 1;
    if (dragCounter.current <= 0) setDragActive(false);
  };

  const onDrop = (event) => {
    event.preventDefault();
    dragCounter.current = 0;
    setDragActive(false);
    handleFile(event.dataTransfer.files?.[0]);
  };

  const resetForm = () => {
    setFile(null);
    setDescription("");
    setContentCategory("text");
    setInputKey(Date.now());
    setProgress(0);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!file) {
      setError("Select a file before uploading.");
      return;
    }

    setError("");
    setStatus("");
    setUploading(true);
    setProgress(0);

    try {
      const formData = new FormData();
      formData.append("file", file);
      if (description) formData.append("description", description);

      const response = await apiClient.post("/documents/upload", formData, {
        onUploadProgress: (event) => {
          if (!event.total) return;
          setProgress(Math.round((event.loaded * 100) / event.total));
        },
      });

      let ingestedAs = "Text";

      if (selectedMeta?.type === "Text" && contentCategory === "review") {
        const reviewType = documentTypes.find(
          (type) => type.type_name === "Review"
        );

        if (reviewType) {
          await apiClient.patch(`/documents/${response.data.id}`, {
            document_type_id: reviewType.id,
          });
          ingestedAs = "Review";
        }
        // If the Review type isn't found (types failed to load), the
        // document stays typed as Text rather than silently failing the
        // whole upload — the user can still fix it from the document list.
      }

      setStatus(
        `"${response.data.original_file_name}" ingested as document #${response.data.id} (${ingestedAs}).`
      );
      resetForm();
      await loadDocuments();
    } catch (err) {
      setError(apiError(err, "Upload failed."));
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (documentId) => {
    setDeletingId(documentId);
    setError("");
    try {
      await apiClient.delete(`/documents/${documentId}`);
      setStatus(`Document #${documentId} removed.`);
      await loadDocuments();
    } catch (err) {
      setError(apiError(err, "Unable to delete this document."));
    } finally {
      setDeletingId(null);
    }
  };

  const selectedMeta = file ? fileMeta(file.name) : null;
  const SelectedIcon = selectedMeta?.icon;

  return (
    <div className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <PageHeader
          eyebrow="Ingestion"
          title="Submit media for verification"
          description="Files are stored server-side, typed by extension, and queued for multimodal analysis."
          actions={
            <Button
              variant="secondary"
              size="sm"
              icon={ScanSearch}
              onClick={() => navigate("/predict")}
            >
              Go to Analyze
            </Button>
          }
        />

        <div className="grid gap-5 lg:grid-cols-[1.35fr_0.65fr]">
          <Card>
            <form onSubmit={handleSubmit} className="space-y-5">
              <label
                onDragOver={(event) => event.preventDefault()}
                onDragEnter={onDragEnter}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
                className={`relative flex cursor-pointer flex-col items-center justify-center overflow-hidden rounded-2xl border-2 border-dashed px-6 py-14 text-center transition-all ${
                  dragActive
                    ? "border-neon-500/70 bg-neon-500/5"
                    : "border-line/12 bg-void-900/40 hover:border-neon-500/40"
                }`}
              >
                {/* scanline sweep — only while dragging */}
                {dragActive && (
                  <span className="pointer-events-none absolute inset-x-0 top-0 h-16 animate-scan bg-gradient-to-b from-neon-500/25 to-transparent" />
                )}

                <input
                  key={inputKey}
                  type="file"
                  className="hidden"
                  onChange={(event) => handleFile(event.target.files?.[0])}
                />

                <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-neon-500/25 bg-neon-500/10 text-neon-400">
                  <UploadCloud className="h-7 w-7" strokeWidth={1.75} />
                </div>
                <p className="mt-5 text-sm font-semibold text-slate-200">
                  <span className="text-neon-400">Click to upload</span> or drag
                  and drop
                </p>
                <p className="mt-1.5 font-mono text-xs text-slate-600">
                  image · video · audio · text
                </p>
              </label>

              {file && (
                <div className="flex items-center justify-between gap-3 rounded-xl border border-line/10 bg-void-900/50 p-4">
                  <div className="flex min-w-0 items-center gap-3">
                    <div
                      className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${selectedMeta.accent}`}
                    >
                      <SelectedIcon className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-100">
                        {file.name}
                      </p>
                      <p className="font-mono text-xs text-slate-500">
                        {formatBytes(file.size)} · {selectedMeta.type}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={resetForm}
                    className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-slate-500 transition hover:bg-hover/5 hover:text-threat"
                    aria-label="Remove selected file"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              )}

              {selectedMeta?.type === "Text" && (
                <div>
                  <Label hint="extension alone can't tell these apart">
                    What kind of text is this?
                  </Label>
                  <Segmented
                    options={[
                      { value: "text", label: "News / article" },
                      { value: "review", label: "Product / service review" },
                    ]}
                    value={contentCategory}
                    onChange={setContentCategory}
                  />
                </div>
              )}

              {uploading && progress > 0 && (
                <div>
                  <div className="mb-1.5 flex justify-between">
                    <span className="hud-label">Uploading</span>
                    <span className="font-mono text-xs text-neon-400">
                      {progress}%
                    </span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-hover/8">
                    <div
                      className="h-full rounded-full bg-neon-gradient transition-[width]"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>
              )}

              <div>
                <Label htmlFor="description" hint="optional">
                  Description
                </Label>
                <Textarea
                  id="description"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  placeholder="Case reference, source, or context for this file…"
                />
              </div>

              {error && <Alert variant="error">{error}</Alert>}
              {status && <Alert variant="success">{status}</Alert>}

              <div className="flex flex-wrap gap-3">
                <Button
                  type="submit"
                  size="lg"
                  loading={uploading}
                  icon={!uploading ? UploadCloud : undefined}
                >
                  {uploading ? "Uploading…" : "Upload file"}
                </Button>
                {documents.length > 0 && (
                  <Button
                    type="button"
                    variant="secondary"
                    size="lg"
                    icon={ScanSearch}
                    onClick={() => navigate("/predict")}
                  >
                    Analyze uploads
                  </Button>
                )}
              </div>
            </form>
          </Card>

          <div className="space-y-5">
            <Card>
              <p className="hud-label text-neon-400">Accepted formats</p>
              <div className="mt-4 space-y-2">
                {ACCEPTED.map((item) => {
                  const meta = fileMeta(
                    item.type === "Image"
                      ? "a.png"
                      : item.type === "Video"
                        ? "a.mp4"
                        : item.type === "Audio"
                          ? "a.mp3"
                          : "a.txt"
                  );
                  const Icon = meta.icon;
                  return (
                    <div
                      key={item.type}
                      className="flex items-center gap-3 rounded-xl border border-line/8 bg-void-900/40 p-3"
                    >
                      <div
                        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border ${meta.accent}`}
                      >
                        <Icon className="h-[18px] w-[18px]" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-slate-200">
                          {item.type}
                        </p>
                        <p className="truncate font-mono text-[0.68rem] text-slate-600">
                          {item.exts}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
              <p className="mt-4 flex items-start gap-2 text-xs leading-relaxed text-slate-500">
                <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-clear" />
                Files are stored on the API server and typed by extension. An
                unsupported extension is rejected before any bytes are written.
              </p>
            </Card>

            <Card padding="p-0">
              <div className="flex items-center justify-between px-6 pb-3 pt-5">
                <p className="hud-label">Recent uploads</p>
                <Badge tone="neutral">{documents.length}</Badge>
              </div>
              <div className="neon-rule" />

              <div className="max-h-[22rem] divide-y divide-line overflow-y-auto">
                {listLoading ? (
                  <div className="space-y-3 p-5">
                    {Array.from({ length: 3 }).map((_, i) => (
                      <Skeleton key={i} className="h-12 w-full" />
                    ))}
                  </div>
                ) : documents.length > 0 ? (
                  documents.map((document) => {
                    const meta = fileMeta(document.original_file_name);
                    const Icon = meta.icon;
                    return (
                      <div
                        key={document.id}
                        className="group flex items-center gap-3 px-5 py-3 transition hover:bg-hover/[0.03]"
                      >
                        <div
                          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border ${meta.accent}`}
                        >
                          <Icon className="h-[18px] w-[18px]" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-semibold text-slate-200">
                            {document.original_file_name}
                          </p>
                          <p className="flex items-center gap-1.5 font-mono text-[0.68rem] text-slate-600">
                            <Clock3 className="h-3 w-3" />
                            {formatRelative(document.uploaded_at)}
                            <span className="text-slate-700">·</span>
                            <HardDrive className="h-3 w-3" />
                            {formatBytes(document.file_size)}
                          </p>
                        </div>
                        <button
                          onClick={() => handleDelete(document.id)}
                          disabled={deletingId === document.id}
                          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-slate-600 opacity-0 transition hover:bg-threat/10 hover:text-threat focus:opacity-100 group-hover:opacity-100 disabled:opacity-40"
                          aria-label={`Delete ${document.original_file_name}`}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    );
                  })
                ) : (
                  <div className="p-5">
                    <EmptyState
                      icon={UploadCloud}
                      title="No uploads yet"
                      description="Ingested files appear here."
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
