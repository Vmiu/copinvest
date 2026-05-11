import { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { ChevronUp, ChevronDown } from "lucide-react";
import { fetchDocuments } from "../api/documents";
import type { DocumentListResponse, DocumentListItem } from "../types/api";
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Skeleton } from "../components/ui/skeleton";
import { Alert, AlertDescription } from "../components/ui/alert";
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "../components/ui/select";

function formatTs(ts: string) {
  return new Date(ts).toISOString().slice(0, 16).replace("T", " ");
}

const TIER_LABELS: Record<number, string> = { 1: "Public", 2: "Internal", 3: "Restricted", 4: "Confidential" };
const TIER_CLASSES: Record<number, string> = {
  1: "bg-emerald-500 text-neutral-950",
  2: "bg-blue-500 text-neutral-950",
  3: "bg-amber-500 text-neutral-950",
  4: "bg-red-500 text-white",
};

function TierBadge({ tier }: { tier: number }) {
  return (
    <Badge className={TIER_CLASSES[tier] ?? ""}>{TIER_LABELS[tier] ?? tier}</Badge>
  );
}

export default function DocumentRegistry() {
  const [data, setData] = useState<DocumentListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tierFilter, setTierFilter] = useState("all");
  const [docTypeFilter, setDocTypeFilter] = useState("all");
  const [jurisdictionFilter, setJurisdictionFilter] = useState("all");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  useEffect(() => {
    fetchDocuments()
      .then(setData)
      .catch(() => setError("Failed to load documents. Refresh to try again."))
      .finally(() => setLoading(false));
  }, []);

  const items = useMemo<DocumentListItem[]>(() => {
    if (!data) return [];
    let filtered = data.items;
    if (tierFilter !== "all") filtered = filtered.filter(i => i.sensitivity_tier === parseInt(tierFilter));
    if (docTypeFilter !== "all") filtered = filtered.filter(i => i.document_type === docTypeFilter);
    if (jurisdictionFilter !== "all") filtered = filtered.filter(i => i.jurisdiction === jurisdictionFilter);
    return [...filtered].sort((a, b) => {
      const diff = new Date(a.ingested_at).getTime() - new Date(b.ingested_at).getTime();
      return sortDir === "asc" ? diff : -diff;
    });
  }, [data, tierFilter, docTypeFilter, jurisdictionFilter, sortDir]);

  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold text-white">Document Registry</h1>
      <p className="text-sm text-neutral-400 mt-1">All ingested documents and their metadata.</p>

      <div className="flex items-center gap-3 mt-6 mb-4">
        <Select value={tierFilter} onValueChange={v => setTierFilter(v ?? "all")}>
          <SelectTrigger className="w-44 bg-neutral-800 border-neutral-700 text-white">
            <SelectValue placeholder="All tiers" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="1">Public</SelectItem>
            <SelectItem value="2">Internal</SelectItem>
            <SelectItem value="3">Restricted</SelectItem>
            <SelectItem value="4">Confidential</SelectItem>
          </SelectContent>
        </Select>
        <Select value={docTypeFilter} onValueChange={v => setDocTypeFilter(v ?? "all")}>
          <SelectTrigger className="w-44 bg-neutral-800 border-neutral-700 text-white">
            <SelectValue placeholder="All types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="factsheet">Factsheet</SelectItem>
            <SelectItem value="compliance_doc">Compliance Document</SelectItem>
            <SelectItem value="meeting_template">Meeting Template</SelectItem>
            <SelectItem value="research_report">Research Report</SelectItem>
            <SelectItem value="other">Other</SelectItem>
          </SelectContent>
        </Select>

        <Select value={jurisdictionFilter} onValueChange={v => setJurisdictionFilter(v ?? "all")}>
          <SelectTrigger className="w-36 bg-neutral-800 border-neutral-700 text-white">
            <SelectValue placeholder="All jurisdictions" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="HK">Hong Kong</SelectItem>
            <SelectItem value="SG">Singapore</SelectItem>
            <SelectItem value="global">Global</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Filename</TableHead>
            <TableHead className="w-20">Type</TableHead>
            <TableHead className="w-32">Doc Type</TableHead>
            <TableHead className="w-16">Lang</TableHead>
            <TableHead className="w-24">Jurisdiction</TableHead>
            <TableHead className="w-40">Product Codes</TableHead>
            <TableHead>Display Title</TableHead>
            <TableHead className="w-32">Sensitivity Tier</TableHead>
            <TableHead className="w-20 text-right">Chunks</TableHead>
            <TableHead
              className="w-40 cursor-pointer select-none"
              aria-sort={sortDir === "asc" ? "ascending" : "descending"}
              onClick={() => setSortDir(d => d === "asc" ? "desc" : "asc")}
            >
              <span className="flex items-center gap-1">
                Ingested At
                {sortDir === "asc" ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              </span>
            </TableHead>
            <TableHead className="w-36">Ingested By</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <TableRow key={i}>
                {Array.from({ length: 10 }).map((_, j) => (
                  <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                ))}
              </TableRow>
            ))
          ) : items.length === 0 && data && data.items.length > 0 ? (
            <TableRow>
              <TableCell colSpan={10}>
                <div className="py-12 text-center">
                  <p className="text-white font-semibold">No documents match the selected filters</p>
                  <p className="text-neutral-400 text-sm mt-1">Try clearing the Document Type or Jurisdiction filter.</p>
                </div>
              </TableCell>
            </TableRow>
          ) : items.length === 0 ? (
            <TableRow>
              <TableCell colSpan={10}>
                <div className="py-12 text-center">
                  <p className="text-white font-semibold">No documents ingested</p>
                  <p className="text-neutral-400 text-sm mt-1">
                    No documents have been ingested yet.{" "}
                    <Link to="/ingest" className="text-indigo-500 hover:underline">
                      Go to Ingest Document
                    </Link>{" "}
                    to add the first one.
                  </p>
                </div>
              </TableCell>
            </TableRow>
          ) : (
            items.map(item => (
              <TableRow key={item.document_id}>
                <TableCell className="text-neutral-300">
                  {item.filename.length > 60 ? item.filename.slice(0, 60) + "…" : item.filename}
                </TableCell>
                <TableCell><Badge variant="secondary">{item.doc_type}</Badge></TableCell>
                <TableCell>
                  {item.document_type
                    ? <Badge variant="secondary">{item.document_type}</Badge>
                    : <span className="text-neutral-500">—</span>}
                </TableCell>
                <TableCell className="text-neutral-300 text-xs uppercase">{item.language ?? "—"}</TableCell>
                <TableCell className="text-neutral-300 text-xs">{item.jurisdiction ?? "—"}</TableCell>
                <TableCell className="text-neutral-300 text-xs">
                  {item.product_codes.length > 0
                    ? (() => { const s = item.product_codes.join(", "); return s.length > 30 ? s.slice(0, 30) + "…" : s; })()
                    : "—"}
                </TableCell>
                <TableCell className="text-neutral-300">
                  {item.parent_doc_title
                    ? (item.parent_doc_title.length > 50 ? item.parent_doc_title.slice(0, 50) + "…" : item.parent_doc_title)
                    : "—"}
                </TableCell>
                <TableCell><TierBadge tier={item.sensitivity_tier} /></TableCell>
                <TableCell className="text-right text-neutral-300">{item.chunk_count}</TableCell>
                <TableCell className="text-neutral-300 text-xs">{formatTs(item.ingested_at)}</TableCell>
                <TableCell className="text-neutral-300">{item.ingested_by}</TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
