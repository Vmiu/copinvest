import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/layout/Sidebar";
import LoginPage from "./pages/LoginPage";
import { lazy, Suspense, useState } from "react";

const AuditLog = lazy(() => import("./pages/AuditLog"));
const SessionQueries = lazy(() => import("./pages/SessionQueries"));
const TraceInspector = lazy(() => import("./pages/TraceInspector"));
const DocumentRegistry = lazy(() => import("./pages/DocumentRegistry"));
const IngestDocument = lazy(() => import("./pages/IngestDocument"));

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem("token"));

  function handleLogout() {
    localStorage.removeItem("token");
    setToken(null);
  }

  if (!token) {
    return <LoginPage onLogin={setToken} />;
  }

  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-background">
        <Sidebar onLogout={handleLogout} />
        <main className="ml-60 flex-1 p-8">
          <Suspense fallback={<div className="text-muted-foreground text-sm">Loading...</div>}>
            <Routes>
              <Route path="/" element={<Navigate to="/audit" replace />} />
              <Route path="/audit" element={<AuditLog />} />
              <Route path="/audit/session/:session_id" element={<SessionQueries />} />
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
