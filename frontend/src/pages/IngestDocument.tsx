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
  const [docTypeValue, setDocTypeValue] = useState("");
  const [languageValue, setLanguageValue] = useState("");
  const [jurisdictionValue, setJurisdictionValue] = useState("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fileInput = form.elements.namedItem("file") as HTMLInputElement;
    if (!fileInput.files?.[0] || !tierValue || !docTypeValue || !languageValue || !jurisdictionValue) return;
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    formData.append("sensitivity_tier", tierValue);
    formData.append("document_type", docTypeValue);
    formData.append("language", languageValue);
    formData.append("jurisdiction", jurisdictionValue);
    const productCodesInput = (form.elements.namedItem("product_codes") as HTMLInputElement)?.value ?? "";
    if (productCodesInput.trim()) formData.append("product_codes", productCodesInput.trim());
    const displayTitleInput = (form.elements.namedItem("parent_doc_title") as HTMLInputElement)?.value ?? "";
    if (displayTitleInput.trim()) formData.append("parent_doc_title", displayTitleInput.trim());
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await ingestDocument(formData);
      setResult(res);
      form.reset();
      setTierValue("");
      setDocTypeValue("");
      setLanguageValue("");
      setJurisdictionValue("");
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

        {/* Document Type */}
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-white">Document Type</label>
          <Select value={docTypeValue} onValueChange={v => setDocTypeValue(v ?? "")} disabled={loading}>
            <SelectTrigger className="w-full bg-neutral-800 border-neutral-700 text-white">
              <SelectValue placeholder="Select document type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="factsheet">Factsheet</SelectItem>
              <SelectItem value="compliance_doc">Compliance Document</SelectItem>
              <SelectItem value="meeting_template">Meeting Template</SelectItem>
              <SelectItem value="research_report">Research Report</SelectItem>
              <SelectItem value="other">Other</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Language */}
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-white">Language</label>
          <Select value={languageValue} onValueChange={v => setLanguageValue(v ?? "")} disabled={loading}>
            <SelectTrigger className="w-full bg-neutral-800 border-neutral-700 text-white">
              <SelectValue placeholder="Select language" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="en">English</SelectItem>
              <SelectItem value="zh">Chinese</SelectItem>
              <SelectItem value="other">Other</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Jurisdiction */}
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-white">Jurisdiction</label>
          <Select value={jurisdictionValue} onValueChange={v => setJurisdictionValue(v ?? "")} disabled={loading}>
            <SelectTrigger className="w-full bg-neutral-800 border-neutral-700 text-white">
              <SelectValue placeholder="Select jurisdiction" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="HK">Hong Kong</SelectItem>
              <SelectItem value="SG">Singapore</SelectItem>
              <SelectItem value="global">Global</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Product Codes */}
        <div className="flex flex-col gap-1">
          <label htmlFor="product_codes" className="text-sm font-medium text-white">Product Codes</label>
          <input
            id="product_codes"
            name="product_codes"
            type="text"
            disabled={loading}
            placeholder="e.g. HSBC001, FUND002"
            aria-describedby="product-codes-hint"
            className="rounded border border-neutral-700 bg-neutral-800 text-neutral-300 p-2 text-sm w-full"
          />
          <p id="product-codes-hint" className="text-xs text-neutral-400">Comma-separated. Leave blank if not applicable.</p>
        </div>

        {/* Display Title */}
        <div className="flex flex-col gap-1">
          <label htmlFor="parent_doc_title" className="text-sm font-medium text-white">Display Title</label>
          <input
            id="parent_doc_title"
            name="parent_doc_title"
            type="text"
            disabled={loading}
            placeholder="e.g. HSBC Annual Report 2024"
            aria-describedby="display-title-hint"
            className="rounded border border-neutral-700 bg-neutral-800 text-neutral-300 p-2 text-sm w-full"
          />
          <p id="display-title-hint" className="text-xs text-neutral-400">Human-readable name shown in the document registry.</p>
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
