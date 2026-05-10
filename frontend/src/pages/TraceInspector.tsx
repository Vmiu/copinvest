import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { ChevronDown, ChevronRight } from "lucide-react";
import { fetchAuditDetail } from "../api/audit";
import type { AuditDetailOut } from "../types/api";
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from "../components/ui/collapsible";
import { Badge } from "../components/ui/badge";
import { Skeleton } from "../components/ui/skeleton";
import { Alert, AlertDescription } from "../components/ui/alert";

function TraceSection({
  label,
  defaultOpen = false,
  children,
}: {
  label: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Collapsible open={open} onOpenChange={setOpen} className="border border-neutral-800 rounded-md">
      <CollapsibleTrigger
        className="flex w-full items-center justify-between px-4 h-12 text-sm font-semibold text-white hover:bg-neutral-900 rounded-t-md"
        aria-expanded={open}
      >
        {label}
        {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </CollapsibleTrigger>
      <CollapsibleContent className="px-4 py-3 border-t border-neutral-800">
        {children}
      </CollapsibleContent>
    </Collapsible>
  );
}

function AdviserBadge({ action }: { action: AuditDetailOut["adviser_action"] }) {
  if (!action) return <Badge variant="secondary">Pending</Badge>;
  const map: Record<string, string> = {
    approved: "bg-emerald-500 text-neutral-950",
    discarded: "bg-red-500 text-white",
    edited: "bg-amber-500 text-neutral-950",
  };
  return <Badge className={map[action] ?? ""}>{action}</Badge>;
}

export default function TraceInspector() {
  const { trace_id: traceId } = useParams<{ trace_id: string }>();
  const [data, setData] = useState<AuditDetailOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!traceId) return;
    setLoading(true);
    fetchAuditDetail(traceId)
      .then(setData)
      .catch(() => setError("Trace not found."))
      .finally(() => setLoading(false));
  }, [traceId]);

  if (loading) {
    return (
      <div className="p-8 space-y-3">
        <Skeleton className="h-6 w-48" />
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8">
        <Link to="/audit" className="text-sm text-neutral-400 hover:text-white">← Audit Log</Link>
        <Alert variant="destructive" className="mt-4">
          <AlertDescription>
            {error ?? "Trace not found."}{" "}
            <Link to="/audit" className="underline">Back to Audit Log</Link>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  interface Chunk {
    source_id: string | null;
    chunk_index: number | null;
    section_title: string | null;
    sensitivity_tier: number | null;
    text: string | null;
  }
  let parsedChunks: Chunk[] = [];
  try {
    if (data.retrieved_chunks) parsedChunks = JSON.parse(data.retrieved_chunks);
  } catch { /* leave empty */ }
  const chunkCount = parsedChunks.length;

  return (
    <div className="p-8">
      <Link to="/audit" className="text-sm text-neutral-400 hover:text-white">← Audit Log</Link>
      <h1 className="text-2xl font-semibold text-white mt-4">Trace: {traceId}</h1>
      <div className="flex items-center gap-3 mt-1 text-sm text-neutral-400">
        <span>{new Date(data.timestamp).toISOString().slice(0, 16).replace("T", " ")}</span>
        <span>{data.user_id}</span>
        <span>{data.channel}</span>
        {data.not_found && <Badge className="bg-amber-500 text-neutral-950">No chunks retrieved</Badge>}
      </div>

      <div className="mt-6 space-y-3">
        <TraceSection label="Query" defaultOpen>
          <pre className="font-mono text-xs text-neutral-300 whitespace-pre-wrap">{data.query_text}</pre>
          {data.rewritten_query && (
            <>
              <p className="text-xs text-neutral-400 mt-2">Rewritten:</p>
              <pre className="font-mono text-xs text-neutral-300 whitespace-pre-wrap">{data.rewritten_query}</pre>
            </>
          )}
          {data.not_found && (
            <Badge className="mt-2 bg-amber-500 text-neutral-950">No chunks retrieved</Badge>
          )}
        </TraceSection>

        <TraceSection label={`Retrieved Chunks (${chunkCount})`}>
          {parsedChunks.length === 0 ? (
            <p className="text-sm text-neutral-400">No chunks retrieved</p>
          ) : (
            <div className="space-y-4">
              {parsedChunks.map((chunk, i) => (
                <div key={i} className="border border-neutral-700 rounded p-3 space-y-2">
                  <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-neutral-400">
                    <span><span className="text-neutral-500">source</span> {chunk.source_id ?? "—"}</span>
                    <span><span className="text-neutral-500">chunk</span> {chunk.chunk_index ?? "—"}</span>
                    <span><span className="text-neutral-500">tier</span> {chunk.sensitivity_tier ?? "—"}</span>
                    {chunk.section_title && (
                      <span><span className="text-neutral-500">section</span> {chunk.section_title}</span>
                    )}
                  </div>
                  <pre className="font-mono text-xs text-neutral-300 whitespace-pre-wrap overflow-auto max-h-48">
                    {chunk.text ?? "—"}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </TraceSection>

        <TraceSection label="Prompt Sent">
          <pre className="font-mono text-xs text-neutral-300 whitespace-pre-wrap overflow-auto max-h-96">
            {data.prompt_sent ?? "—"}
          </pre>
        </TraceSection>

        <TraceSection label="LLM Response" defaultOpen>
          <p className="text-sm text-neutral-300 whitespace-pre-wrap overflow-auto max-h-96">
            {data.llm_response ?? "—"}
          </p>
        </TraceSection>

        <TraceSection label="Adviser Action" defaultOpen>
          <AdviserBadge action={data.adviser_action} />
          {data.final_response && (
            <p className="text-sm text-neutral-300 mt-3 whitespace-pre-wrap">{data.final_response}</p>
          )}
        </TraceSection>

        <TraceSection label="Metadata">
          <dl className="grid grid-cols-2 gap-2 text-sm">
            {[
              ["Model", data.model_used],
              ["Prompt tokens", data.prompt_tokens],
              ["Completion tokens", data.completion_tokens],
              ["Sensitivity tier", data.sensitivity_tier_accessed],
              ["Channel", data.channel],
              ["Session ID", data.session_id],
              ["Chunks passed rerank", data.chunks_passed_rerank],
            ].map(([k, v]) => (
              <>
                <dt key={`k-${k}`} className="text-neutral-400">{k}</dt>
                <dd key={`v-${k}`} className="text-white">{v ?? "—"}</dd>
              </>
            ))}
          </dl>
        </TraceSection>
      </div>
    </div>
  );
}
