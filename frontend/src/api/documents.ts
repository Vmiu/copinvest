import apiClient from "./client";
import type { DocumentListResponse, IngestResponse } from "../types/api";

export async function fetchDocuments(): Promise<DocumentListResponse> {
  const res = await apiClient.get<DocumentListResponse>("/documents");
  return res.data;
}

export async function ingestDocument(formData: FormData, document_type?: string): Promise<IngestResponse> {
  const res = await apiClient.post<IngestResponse>("/ingest", formData, {
    timeout: 0,
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}
