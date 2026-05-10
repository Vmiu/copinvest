import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { fetchSessions } from "../api/audit";
import type { SessionListItem, SessionListResponse } from "../types/api";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "../components/ui/table";
import { Skeleton } from "../components/ui/skeleton";
import { Alert, AlertDescription } from "../components/ui/alert";
import { Button } from "../components/ui/button";

const PAGE_SIZE = 25;

function formatTs(ts: string) {
  return new Date(ts).toISOString().slice(0, 16).replace("T", " ");
}

export default function AuditLog() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [data, setData] = useState<SessionListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchSessions(page, PAGE_SIZE)
      .then(setData)
      .catch(() => setError("Failed to load sessions."))
      .finally(() => setLoading(false));
  }, [page]);

  const total = data?.total ?? 0;
  const start = (page - 1) * PAGE_SIZE + 1;
  const end = Math.min(page * PAGE_SIZE, total);

  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold text-white">Audit Log</h1>
      <p className="text-sm text-neutral-400 mt-1">Sessions — click to view queries.</p>

      {error && (
        <Alert variant="destructive" className="mt-4 mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Table className="mt-6">
        <TableHeader>
          <TableRow>
            <TableHead>Session ID</TableHead>
            <TableHead className="w-40">User</TableHead>
            <TableHead className="w-20 text-right">Queries</TableHead>
            <TableHead className="w-40">Started</TableHead>
            <TableHead className="w-40">Last Activity</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <TableRow key={i}>
                {Array.from({ length: 5 }).map((_, j) => (
                  <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                ))}
              </TableRow>
            ))
          ) : data?.items.length === 0 ? (
            <TableRow>
              <TableCell colSpan={5}>
                <p className="py-12 text-center text-neutral-400">No sessions found.</p>
              </TableCell>
            </TableRow>
          ) : (
            data?.items.map((row: SessionListItem) => (
              <TableRow
                key={row.session_id}
                className="cursor-pointer hover:bg-neutral-900"
                onClick={() => navigate(`/audit/session/${row.session_id}`)}
              >
                <TableCell className="text-neutral-300 font-mono text-xs">{row.session_id}</TableCell>
                <TableCell className="text-neutral-300">{row.user_id}</TableCell>
                <TableCell className="text-right text-neutral-300">{row.query_count}</TableCell>
                <TableCell className="text-neutral-300 text-xs">{formatTs(row.started_at)}</TableCell>
                <TableCell className="text-neutral-300 text-xs">{formatTs(row.last_activity)}</TableCell>
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
