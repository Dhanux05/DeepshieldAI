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
  User,
  FileJson,
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
  Input,
  Textarea,
  Segmented,
  Checkbox,
} from "../components/ui";
import { Skeleton } from "../components/ui/Skeleton";
import { formatBytes, formatRelative, fileMeta } from "../lib/format";

const ACCEPTED = [
  { type: "Image", exts: "JPG · PNG · WEBP · BMP" },
  { type: "Video", exts: "MP4 · MKV · AVI · MOV" },
  { type: "Audio", exts: "MP3 · WAV · AAC · FLAC" },
  { type: "Text", exts: "TXT · PDF · DOCX · CSV" },
];

// Every field bot_preprocessing.extract_features() knows how to read (see
// that module's docstring). Numbers default to "0" rather than being left
// blank -- an empty string posted as JSON would still coerce to 0 through
// _safe_int either way, but a visible 0 is less confusing mid-form than a
// blank box with no unit next to it.
const ACCOUNT_FORM_DEFAULTS = {
  screen_name: "",
  name: "",
  description: "",
  url: "",
  created_at: "",
  followers_count: "0",
  friends_count: "0",
  listed_count: "0",
  favourites_count: "0",
  statuses_count: "0",
  verified: false,
  default_profile: false,
  default_profile_image: false,
  has_extended_profile: false,
};

export default function Upload() {
  const [mode, setMode] = useState("file"); // "file" | "account"

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

  // Account (bot detection) form state — a structured alternative to
  // hand-writing the JSON file app/ml/bot_detector.py expects. Submitting
  // this builds that JSON client-side and posts it through the same
  // /documents/upload endpoint with document_type=Account (see
  // DocumentService.upload_document's docstring for why Account needs the
  // explicit override instead of extension-based typing).
  const [accountForm, setAccountForm] = useState(ACCOUNT_FORM_DEFAULTS);
  const [accountSubmitting, setAccountSubmitting] = useState(false);

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

  const updateAccountField = (field, value) => {
    setAccountForm((current) => ({ ...current, [field]: value }));
  };

  const resetAccountForm = () => {
    setAccountForm(ACCOUNT_FORM_DEFAULTS);
  };

  const handleAccountSubmit = async (event) => {
    event.preventDefault();

    if (!accountForm.screen_name.trim()) {
      setError("Enter a screen name before submitting.");
      return;
    }

    setError("");
    setStatus("");
    setAccountSubmitting(true);

    try {
      // Field names here must match app/ml/bot_preprocessing.py's
      // extract_features() exactly — that module reads these keys (or
      // "favorites_count" as a fallback spelling) straight off the parsed
      // JSON. created_at is posted as a plain "YYYY-MM-DD" from the date
      // input; parse_account_datetime() falls through to dateutil for
      // anything that isn't Twitter's own datetime format, which handles
      // ISO dates without any extra conversion here.
      const payload = {
        screen_name: accountForm.screen_name.trim(),
        name: accountForm.name.trim(),
        description: accountForm.description.trim(),
        url: accountForm.url.trim(),
        created_at: accountForm.created_at,
        followers_count: Number(accountForm.followers_count) || 0,
        friends_count: Number(accountForm.friends_count) || 0,
        listed_count: Number(accountForm.listed_count) || 0,
        favourites_count: Number(accountForm.favourites_count) || 0,
        statuses_count: Number(accountForm.statuses_count) || 0,
        verified: accountForm.verified,
        default_profile: accountForm.default_profile,
        default_profile_image: accountForm.default_profile_image,
        has_extended_profile: accountForm.has_extended_profile,
      };

      const blob = new Blob([JSON.stringify(payload, null, 2)], {
        type: "application/json",
      });
      const safeName =
        payload.screen_name.replace(/[^a-zA-Z0-9_-]/g, "") || "account";
      const jsonFile = new File([blob], `${safeName}.json`, {
        type: "application/json",
      });

      const formData = new FormData();
      formData.append("file", jsonFile);
      formData.append("document_type", "Account");
      formData.append(
        "description",
        `Account snapshot for @${payload.screen_name}`
      );

      const response = await apiClient.post("/documents/upload", formData);

      setStatus(
        `Account "@${payload.screen_name}" ingested as document #${response.data.id}. ` +
          `Go to Analyze to run the bot detector on it.`
      );
      resetAccountForm();
      await loadDocuments();
    } catch (err) {
      setError(apiError(err, "Account submission failed."));
    } finally {
      setAccountSubmitting(false);
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

        <Segmented
          options={[
            { value: "file", label: "Upload a file" },
            { value: "account", label: "Analyze an account" },
          ]}
          value={mode}
          onChange={(value) => {
            setMode(value);
            setError("");
            setStatus("");
          }}
        />

        {mode === "file" ? (
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
                    <span className="text-neon-400">Click to upload</span> or
                    drag and drop
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
                  Files are stored on the API server and typed by extension.
                  An unsupported extension is rejected before any bytes are
                  written.
                </p>
                <p className="mt-3 flex items-start gap-2 text-xs leading-relaxed text-slate-500">
                  <User className="mt-0.5 h-3.5 w-3.5 shrink-0 text-neon-400" />
                  Checking a social-media account instead? Switch to
                  "Analyze an account" above — no file needed.
                </p>
              </Card>

              <RecentUploads
                documents={documents}
                loading={listLoading}
                deletingId={deletingId}
                onDelete={async (documentId) => {
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
                }}
              />
            </div>
          </div>
        ) : (
          <div className="grid gap-5 lg:grid-cols-[1.35fr_0.65fr]">
            <Card>
              <form onSubmit={handleAccountSubmit} className="space-y-6">
                <div className="flex items-start gap-3 rounded-xl border border-line/10 bg-void-900/40 p-4">
                  <FileJson className="mt-0.5 h-5 w-5 shrink-0 text-neon-400" />
                  <p className="text-xs leading-relaxed text-slate-400">
                    Fill in what you know about the account. Every field is
                    read defensively on the server — leave anything blank and
                    it degrades to a neutral default instead of failing the
                    whole submission. This builds a JSON snapshot and ingests
                    it as an <span className="text-slate-200">Account</span>{" "}
                    document, same as a file upload.
                  </p>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <Label htmlFor="screen_name">Screen name</Label>
                    <Input
                      id="screen_name"
                      required
                      value={accountForm.screen_name}
                      onChange={(event) =>
                        updateAccountField("screen_name", event.target.value)
                      }
                      placeholder="e.g. jdoe_official"
                    />
                  </div>
                  <div>
                    <Label htmlFor="name" hint="optional">
                      Display name
                    </Label>
                    <Input
                      id="name"
                      value={accountForm.name}
                      onChange={(event) =>
                        updateAccountField("name", event.target.value)
                      }
                      placeholder="e.g. Jane Doe"
                    />
                  </div>
                </div>

                <div>
                  <Label htmlFor="description" hint="the account's bio">
                    Bio / description
                  </Label>
                  <Textarea
                    id="description"
                    value={accountForm.description}
                    onChange={(event) =>
                      updateAccountField("description", event.target.value)
                    }
                    placeholder="Whatever appears in the account's profile bio…"
                  />
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <Label htmlFor="url" hint="optional">
                      Profile link
                    </Label>
                    <Input
                      id="url"
                      type="url"
                      value={accountForm.url}
                      onChange={(event) =>
                        updateAccountField("url", event.target.value)
                      }
                      placeholder="https://…"
                    />
                  </div>
                  <div>
                    <Label htmlFor="created_at" hint="account creation date">
                      Created on
                    </Label>
                    <Input
                      id="created_at"
                      type="date"
                      value={accountForm.created_at}
                      onChange={(event) =>
                        updateAccountField("created_at", event.target.value)
                      }
                    />
                  </div>
                </div>

                <div>
                  <Label hint="raw counts as they appear on the profile">
                    Activity counts
                  </Label>
                  <div className="grid gap-3 sm:grid-cols-3">
                    <NumberField
                      label="Followers"
                      value={accountForm.followers_count}
                      onChange={(v) =>
                        updateAccountField("followers_count", v)
                      }
                    />
                    <NumberField
                      label="Following"
                      value={accountForm.friends_count}
                      onChange={(v) => updateAccountField("friends_count", v)}
                    />
                    <NumberField
                      label="Listed count"
                      value={accountForm.listed_count}
                      onChange={(v) => updateAccountField("listed_count", v)}
                    />
                    <NumberField
                      label="Favourites / likes"
                      value={accountForm.favourites_count}
                      onChange={(v) =>
                        updateAccountField("favourites_count", v)
                      }
                    />
                    <NumberField
                      label="Posts / statuses"
                      value={accountForm.statuses_count}
                      onChange={(v) =>
                        updateAccountField("statuses_count", v)
                      }
                    />
                  </div>
                </div>

                <div>
                  <Label hint="profile flags, as shown on the account">
                    Profile flags
                  </Label>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Checkbox
                      label="Verified"
                      checked={accountForm.verified}
                      onChange={(v) => updateAccountField("verified", v)}
                    />
                    <Checkbox
                      label="Using the default profile theme"
                      checked={accountForm.default_profile}
                      onChange={(v) =>
                        updateAccountField("default_profile", v)
                      }
                    />
                    <Checkbox
                      label="Using the default profile picture"
                      checked={accountForm.default_profile_image}
                      onChange={(v) =>
                        updateAccountField("default_profile_image", v)
                      }
                    />
                    <Checkbox
                      label="Has an extended profile"
                      checked={accountForm.has_extended_profile}
                      onChange={(v) =>
                        updateAccountField("has_extended_profile", v)
                      }
                    />
                  </div>
                </div>

                {error && <Alert variant="error">{error}</Alert>}
                {status && <Alert variant="success">{status}</Alert>}

                <div className="flex flex-wrap gap-3">
                  <Button
                    type="submit"
                    size="lg"
                    loading={accountSubmitting}
                    icon={!accountSubmitting ? User : undefined}
                  >
                    {accountSubmitting ? "Submitting…" : "Submit account"}
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
                <p className="hud-label text-neon-400">
                  How this feeds the bot detector
                </p>
                <p className="mt-3 text-xs leading-relaxed text-slate-500">
                  These fields map directly onto the 20 engineered features
                  the XGBoost bot/human classifier was trained on — follower
                  ratios, posting cadence, bio sentiment, and account age at
                  the time it's checked. Nothing here is stored anywhere
                  except this project's own database.
                </p>
                <p className="mt-3 text-xs leading-relaxed text-slate-500">
                  After submitting, head to{" "}
                  <span className="text-slate-300">Analyze</span> and select
                  the new document to run the classifier, then{" "}
                  <span className="text-slate-300">Explain</span> for a SHAP
                  breakdown of which fields drove the verdict.
                </p>
              </Card>

              <RecentUploads
                documents={documents}
                loading={listLoading}
                deletingId={deletingId}
                onDelete={async (documentId) => {
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
                }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function NumberField({ label, value, onChange }) {
  return (
    <div>
      <Label hint={null}>{label}</Label>
      <Input
        type="number"
        min="0"
        inputMode="numeric"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}

function RecentUploads({ documents, loading, deletingId, onDelete }) {
  return (
    <Card padding="p-0">
      <div className="flex items-center justify-between px-6 pb-3 pt-5">
        <p className="hud-label">Recent uploads</p>
        <Badge tone="neutral">{documents.length}</Badge>
      </div>
      <div className="neon-rule" />

      <div className="max-h-[22rem] divide-y divide-line overflow-y-auto">
        {loading ? (
          <div className="space-y-3 p-5">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : documents.length > 0 ? (
          documents.map((document) => {
            const meta = fileMeta(
              document.original_file_name,
              document.document_type_name
            );
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
                  onClick={() => onDelete(document.id)}
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
  );
}
