import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { fetchAuditList } from "../api/audit";
import type { AuditListResponse, AuditListItem } from "../types/api";
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Skeleton } from "../components/ui/skeleton";
import { Alert, AlertDescription } from "../components/ui/alert";
import {
  Tooltip, TooltipContent, TooltipTrigger, TooltipProvider,
} from "../components/ui/tooltip";

const PAGE_SIZE = 25;

function formatTs(ts: string) {
  return new Date(ts).toISOString().slice(0, 16).replace("T", " ");
}

function ChannelBadge({ channel }: { channel: string }) {
  if (channel === "telegram")
    return <Badge className="bg-blue-400 text-neutral-950">{channel}</Badge>;
  return <Badge variant="secondary">{channel}</Badge>;
}

function StatusBadge({ status }: { status: AuditListItem["status"] }) {
  const map: Record<string, string> = {
    completed: "bg-emerald-500 text-neutral-950",
    error: "bg-red-500 text-white",
  };
  const cls = map[status] ?? "";
  return cls ? (
    <Badge className={cls}>{status}</Badge>
  ) : (
    <Badge variant="secondary">{status}</Badge>
  );
}

function AdviserBadge({ action }: { action: AuditListItem["adviser_action"] }) {
  if (!action) return <Badge variant="secondary">Pending</Badge>;
  const map: Record<string, string> = {
    approved: "bg-emerald-500 text-neutral-950",
    discarded: "bg-red-500 text-white",
    edited: "bg-amber-500 text-neutral-950",
  };
  return <Badge className={map[action] ?? ""}>{action}</Badge>;
}

export default function AuditLog() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState({ user_id: "", session_id: "", date_from: "", date_to: "" });
  const [pendingFilters, setPendingFilters] = useState({ user_id: "", session_id: "", date_from: "", date_to: "" });
  const [page, setPage] = useState(1);
  const [data, setData] = useState<AuditListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (f: typeof filters, p: number) => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        page: p,
        limit: PAGE_SIZE,
        ...(f.user_id ? { user_id: f.user_id } : {}),
        ...(f.session_id ? { session_id: f.session_id } : {}),
        ...(f.date_from ? { date_from: f.date_from } : {}),
        ...(f.date_to ? { date_to: f.date_to } : {}),
      };
      const res = await fetchAuditList(params);
      setData(res);
    } catch {
      setError("Failed to load audit records. Refresh to try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(filters, page); }, [filters, page, load]);

  function handleApply() {
    setFilters(pendingFilters);
    setPage(1);
  }

  function handleClear() {
    const empty = { user_id: "", session_id: "", date_from: "", date_to: "" };
    setPendingFilters(empty);
    setFilters(empty);
    setPage(1);
  }

  const total = data?.total ?? 0;
  const start = (page - 1) * PAGE_SIZE + 1;
  const end = Math.min(page * PAGE_SIZE, total);

  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold text-white">Audit Log</h1>
      <p className="text-sm text-neutral-400 mt-1">Browse and filter all query traces.</p>

      {/* Filter bar */}
      <div className="flex flex-wrap gap-3 mt-6 mb-4 items-end">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-400">From</label>
          <input
            type="date"
            className="w-36 rounded border border-neutral-700 bg-neutral-800 text-white text-sm px-2 py-1"
            value={pendingFilters.date_from}
            onChange={e => setPendingFilters(f => ({ ...f, date_from: e.target.value }))}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-400">To</label>
          <input
            type="date"
            className="w-36 rounded border border-neutral-700 bg-neutral-800 text-white text-sm px-2 py-1"
            value={pendingFilters.date_to}
            onChange={e => setPendingFilters(f => ({ ...f, date_to: e.target.value }))}
          />
        </div>
        <Input
          className="w-44 bg-neutral-800 border-neutral-700 text-white"
          placeholder="Filter by user"
          value={pendingFilters.user_id}
          onChange={e => setPendingFilters(f => ({ ...f, user_id: e.target.value }))}
        />
        <Input
          className="w-44 bg-neutral-800 border-neutral-700 text-white"
          placeholder="Session ID"
          value={pendingFilters.session_id}
          onChange={e => setPendingFilters(f => ({ ...f, session_id: e.target.value }))}
        />
        <Button className="bg-indigo-500 hover:bg-indigo-600 text-white" onClick={handleApply}>
          Apply Filters
        </Button>
        <Button variant="ghost" className="text-neutral-400" onClick={handleClear}>
          Clear Filters
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-40">Timestamp</TableHead>
            <TableHead className="w-36">User</TableHead>
            <TableHead className="w-20">Channel</TableHead>
            <TableHead>Query</TableHead>
            <TableHead className="w-24">Status</TableHead>
            <TableHead className="w-32">Adviser Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <TableRow key={i}>
                {Array.from({ length: 6 }).map((_, j) => (
                  <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                ))}
              </TableRow>
            ))
          ) : data && data.items.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6}>
                <div className="py-12 text-center">
                  <p className="text-white font-semibold">No audit records found</p>
                  <p className="text-neutral-400 text-sm mt-1">
                    No records match the current filters. Try adjusting the date range or clearing the filters.
                  </p>
                  <Button variant="ghost" className="mt-4 text-neutral-400" onClick={handleClear}>
                    Clear Filters
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ) : (
            data?.items.map(row => (
              <TableRow
                key={row.id}
                className="cursor-pointer hover:bg-neutral-900"
                onClick={() => navigate("/audit/" + row.id)}
              >
                <TableCell className="text-neutral-300 text-xs">{formatTs(row.timestamp)}</TableCell>
                <TableCell className="text-neutral-300">{row.user_id}</TableCell>
                <TableCell><ChannelBadge channel={row.channel} /></TableCell>
                <TableCell>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger className="text-neutral-300 text-sm text-left">
                        {row.query_text.length > 80
                          ? row.query_text.slice(0, 80) + "…"
                          : row.query_text}
                      </TooltipTrigger>
                      <TooltipContent className="max-w-sm whitespace-pre-wrap">
                        {row.query_text}
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </TableCell>
                <TableCell><StatusBadge status={row.status} /></TableCell>
                <TableCell><AdviserBadge action={row.adviser_action} /></TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {/* Pagination */}
      {data && data.total > 0 && (
        <div className="flex items-center justify-end gap-4 mt-4">
          <span className="text-sm text-neutral-400">
            Showing {start}–{end} of {total} records
          </span>
          <Button
            variant="ghost"
            className="text-neutral-400"
            disabled={page === 1}
            onClick={() => setPage(p => p - 1)}
          >
            Prev
          </Button>
          <Button
            variant="ghost"
            className="text-neutral-400"
            disabled={page * PAGE_SIZE >= total}
            onClick={() => setPage(p => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
