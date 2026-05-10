import { useState } from "react";
import axios from "axios";
import { Loader2, X } from "lucide-react";
import { ingestDocument } from "../api/documents";
import type { IngestResponse } from "../types/api";
import { Button } from "../components/ui/button";
import { Alert, AlertDescription } from "../components/ui/alert";
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "../components/ui/select";

export default function IngestDocument() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<IngestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tierValue, setTierValue] = useState("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fileInput = form.elements.namedItem("file") as HTMLInputElement;
    if (!fileInput.files?.[0] || !tierValue) return;
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    formData.append("sensitivity_tier", tierValue);
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await ingestDocument(formData);
      setResult(res);
      form.reset();
      setTierValue("");
    } catch (err: unknown) {
      const msg = axios.isAxiosError(err)
        ? (err.response?.data?.detail ?? "Unknown error")
        : "Request failed";
      setError(`Ingestion failed: ${msg}. Check the file format and try again.`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold text-white">Ingest Document</h1>
      <p className="text-sm text-neutral-400 mt-1">Upload a document and assign its sensitivity tier.</p>

      <form onSubmit={handleSubmit} className="max-w-lg mx-auto mt-8 flex flex-col gap-6">
        <div className="flex flex-col gap-1">
          <label htmlFor="file" className="text-sm font-medium text-white">Document</label>
          <input
            id="file"
            name="file"
            type="file"
            accept=".pdf,.docx,.xlsx"
            required
            disabled={loading}
            className="rounded border border-neutral-700 bg-neutral-800 text-neutral-400 p-2 text-sm file:mr-2 file:rounded file:border-0 file:bg-neutral-700 file:text-white file:text-xs file:px-2 file:py-1"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-white">Sensitivity Tier</label>
          <Select value={tierValue} onValueChange={v => setTierValue(v ?? "")} disabled={loading}>
            <SelectTrigger className="w-full bg-neutral-800 border-neutral-700 text-white">
              <SelectValue placeholder="Select sensitivity tier" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1">Public</SelectItem>
              <SelectItem value="2">Internal</SelectItem>
              <SelectItem value="3">Restricted</SelectItem>
              <SelectItem value="4">Confidential</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Button
          type="submit"
          disabled={loading}
          className="w-full bg-indigo-500 hover:bg-indigo-600 text-white"
        >
          {loading ? (
            <><Loader2 className="h-4 w-4 animate-spin mr-2" />Ingesting...</>
          ) : (
            "Ingest Document"
          )}
        </Button>

        {result && (
          <Alert className="border-emerald-500 bg-emerald-500/10">
            <AlertDescription className="text-emerald-400">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-medium">Document ingested successfully.</p>
                  <p className="mt-1 text-xs text-neutral-400">ID: {result.document_id}</p>
                  <p className="text-xs text-neutral-400">Chunks: {result.chunk_count}</p>
                  {result.warnings.length > 0 && (
                    <p className="text-xs text-amber-400 mt-1">{result.warnings.join("; ")}</p>
                  )}
                </div>
                <button type="button" onClick={() => setResult(null)} className="text-neutral-400 hover:text-white">
                  <X className="h-4 w-4" />
                </button>
              </div>
            </AlertDescription>
          </Alert>
        )}

        {error && (
          <Alert variant="destructive">
            <AlertDescription>
              <div className="flex items-start justify-between gap-2">
                <span>{error}</span>
                <button type="button" onClick={() => setError(null)} className="text-neutral-400 hover:text-white">
                  <X className="h-4 w-4" />
                </button>
              </div>
            </AlertDescription>
          </Alert>
        )}
      </form>
    </div>
  );
}
