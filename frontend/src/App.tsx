import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/layout/Sidebar";
import { lazy, Suspense } from "react";

const AuditLog = lazy(() => import("./pages/AuditLog"));
const TraceInspector = lazy(() => import("./pages/TraceInspector"));
const DocumentRegistry = lazy(() => import("./pages/DocumentRegistry"));
const IngestDocument = lazy(() => import("./pages/IngestDocument"));

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-neutral-950">
        <Sidebar />
        <main className="ml-60 flex-1 p-8">
          <Suspense fallback={<div className="text-neutral-400 text-sm">Loading...</div>}>
            <Routes>
              <Route path="/" element={<Navigate to="/audit" replace />} />
              <Route path="/audit" element={<AuditLog />} />
              <Route path="/audit/:trace_id" element={<TraceInspector />} />
              <Route path="/documents" element={<DocumentRegistry />} />
              <Route path="/ingest" element={<IngestDocument />} />
            </Routes>
          </Suspense>
        </main>
      </div>
    </BrowserRouter>
  );
}
