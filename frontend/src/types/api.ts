export interface SessionListItem {
  session_id: string;
  user_id: string;
  query_count: number;
  started_at: string;
  last_activity: string;
}

export interface SessionListResponse {
  items: SessionListItem[];
  total: number;
  page: number;
  limit: number;
}

export type AuditStatus = "received" | "retrieved" | "generated" | "completed" | "error";
export type AdviserAction = "approved" | "edited" | "discarded";

export interface AuditListItem {
  id: string;
  user_id: string;
  session_id: string;
  timestamp: string;
  channel: string;
  query_text: string;
  status: AuditStatus;
  adviser_action: AdviserAction | null;
  not_found: boolean | null;
}

export interface AuditListResponse {
  items: AuditListItem[];
  total: number;
  page: number;
  limit: number;
}

export interface AuditDetailOut extends AuditListItem {
  rewritten_query: string | null;
  retrieved_chunks: string | null;
  sensitivity_tier_accessed: number | null;
  prompt_sent: string | null;
  llm_response: string | null;
  model_used: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  adviser_edited: boolean | null;
  final_response: string | null;
  chunks_passed_rerank: number | null;
}

export interface DocumentListItem {
  document_id: string;
  filename: string;
  doc_type: string;
  sensitivity_tier: number;
  chunk_count: number;
  ingested_at: string;
  ingested_by: string;
  document_type: string | null;
  language: string | null;
  jurisdiction: string | null;
  product_codes: string[];
  parent_doc_title: string | null;
}

export interface DocumentListResponse {
  items: DocumentListItem[];
  total: number;
}

export interface IngestResponse {
  document_id: string;
  filename: string;
  doc_type: string;
  sensitivity_tier: number;
  chunk_count: number;
  total_chars: number;
  warnings: string[];
  parse_duration_ms: number;
  extraction_method: string;
}
