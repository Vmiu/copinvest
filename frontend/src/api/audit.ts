import apiClient from "./client";
import type { AuditDetailOut, AuditListResponse } from "../types/api";

export interface AuditListParams {
  page?: number;
  limit?: number;
  user_id?: string;
  session_id?: string;
  date_from?: string;
  date_to?: string;
}

export async function fetchAuditList(params: AuditListParams = {}): Promise<AuditListResponse> {
  const res = await apiClient.get<AuditListResponse>("/audit", { params });
  return res.data;
}

export async function fetchAuditDetail(traceId: string): Promise<AuditDetailOut> {
  const res = await apiClient.get<AuditDetailOut>(`/audit/${traceId}`);
  return res.data;
}
