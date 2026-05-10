import apiClient from "./client";
import type { AuditDetailOut, AuditListResponse, SessionListResponse } from "../types/api";

export interface AuditListParams {
  page?: number;
  limit?: number;
  session_id?: string;
}

export async function fetchSessions(page = 1, limit = 25): Promise<SessionListResponse> {
  const res = await apiClient.get<SessionListResponse>("/audit/sessions", { params: { page, limit } });
  return res.data;
}

export async function fetchAuditList(params: AuditListParams = {}): Promise<AuditListResponse> {
  const res = await apiClient.get<AuditListResponse>("/audit", { params });
  return res.data;
}

export async function fetchAuditDetail(traceId: string): Promise<AuditDetailOut> {
  const res = await apiClient.get<AuditDetailOut>(`/audit/${traceId}`);
  return res.data;
}
