import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { fetchAuditList } from "../api/audit";
import type { AuditListResponse, AuditListItem } from "../types/api";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Skeleton } from "../components/ui/skeleton";
import { Alert, AlertDescription } from "../components/ui/alert";
import { Button } from "../components/ui/button";

const PAGE_SIZE = 25;

function formatTs(ts: string) {
  return new Date(ts).toISOString().slice(0, 16).replace("T", " ");
}

function StatusBadge({ status }: { status: AuditListItem["status"] }) {
  const map: Record<string, string> = {
    completed: "bg-emerald-500 text-neutral-950",
    error: "bg-red-500 text-white",
  };
  const cls = map[status] ?? "";
  return cls ? <Badge className={cls}>{status}</Badge> : <Badge variant="secondary">{status}</Badge>;
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

export default function SessionQueries() {
  const { session_id } = useParams<{ session_id: string }>();
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [data, setData] = useState<AuditListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session_id) return;
    setLoading(true);
    setError(null);
    fetchAuditList({ session_id, page, limit: PAGE_SIZE })
      .then(setData)
      .catch(() => setError("Failed to load queries."))
      .finally(() => setLoading(false));
  }, [session_id, page]);

  const total = data?.total ?? 0;
  const start = (page - 1) * PAGE_SIZE + 1;
  const end = Math.min(page * PAGE_SIZE, total);

  return (
    <div className="p-8">
      <Link to="/audit" className="text-sm text-neutral-400 hover:text-white">← Sessions</Link>
      <h1 className="text-2xl font-semibold text-white mt-4">Session Queries</h1>
      <p className="text-xs text-neutral-500 font-mono mt-1">{session_id}</p>

      {error && (
        <Alert variant="destructive" className="mt-4 mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Table className="mt-6">
        <TableHeader>
          <TableRow>
            <TableHead className="w-36">Timestamp</TableHead>
            <TableHead>Query</TableHead>
            <TableHead className="w-24">Status</TableHead>
            <TableHead className="w-32">Adviser Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <TableRow key={i}>
                {Array.from({ length: 4 }).map((_, j) => (
                  <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                ))}
              </TableRow>
            ))
          ) : data?.items.length === 0 ? (
            <TableRow>
              <TableCell colSpan={4}>
                <p className="py-12 text-center text-neutral-400">No queries in this session.</p>
              </TableCell>
            </TableRow>
          ) : (
            data?.items.map(row => (
              <TableRow
                key={row.id}
                className="cursor-pointer hover:bg-neutral-900"
                onClick={() => navigate(`/audit/${row.id}`)}
              >
                <TableCell className="text-neutral-300 text-xs">{formatTs(row.timestamp)}</TableCell>
                <TableCell className="text-neutral-300 text-sm">
                  {row.query_text.length > 100 ? row.query_text.slice(0, 100) + "…" : row.query_text}
                </TableCell>
                <TableCell><StatusBadge status={row.status} /></TableCell>
                <TableCell><AdviserBadge action={row.adviser_action} /></TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {total > 0 && (
        <div className="flex items-center justify-end gap-4 mt-4">
          <span className="text-sm text-neutral-400">Showing {start}–{end} of {total}</span>
          <Button variant="ghost" className="text-neutral-400" disabled={page === 1} onClick={() => setPage(p => p - 1)}>Prev</Button>
          <Button variant="ghost" className="text-neutral-400" disabled={page * PAGE_SIZE >= total} onClick={() => setPage(p => p + 1)}>Next</Button>
        </div>
      )}
    </div>
  );
}
