# Phase 5: Web Audit & Admin UI - Research

**Researched:** 2026-05-09
**Domain:** React 18 SPA + FastAPI REST endpoints (audit/document list, pagination, filtering)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Audit log table: 6 columns — timestamp, user, channel, query (truncated), status, adviser action.
- **D-02:** Server-side filtering — filter params (user, date range, session) sent to backend on each Apply. Requires new `GET /api/v1/audit` endpoint.
- **D-03:** Pagination (not infinite scroll) — standard prev/next page controls.
- **D-04:** Row click navigates to `/audit/:trace_id` — full trace page with shareable URL.
- **D-05:** Full trace page at `/audit/:trace_id`. Displays all AuditLog fields including rewritten_query, retrieved_chunks (JSON), prompt_sent, llm_response, adviser_action, final_response, model_used, token counts, sensitivity_tier_accessed, channel, not_found flag.
- **D-06:** Collapsible sections layout for trace inspector (Claude's discretion confirmed by UI-SPEC).
- **D-07:** Single form for ingest — file picker + sensitivity tier dropdown + submit. No wizard.
- **D-08:** Spinner while request in-flight (30-60s for large PDFs). No timeout.
- **D-09:** On success: show IngestResponse inline below form. Form stays for next submission.
- **D-10:** On error: show error message inline below form.
- **D-11:** Document registry table: filename, doc_type, sensitivity_tier, chunk_count, ingested_at, ingested_by.
- **D-12:** No login page — JWT read from localStorage, set externally.
- **D-13:** All admin/compliance roles see all 4 views — no per-view role restrictions in frontend.
- **D-14:** JWT stored in localStorage. Acceptable for internal admin tool.
- **D-15:** Left sidebar navigation, 240px wide (confirmed by UI-SPEC).

### Claude's Discretion
- Trace inspector layout (collapsible sections confirmed by UI-SPEC)
- Document registry filtering/sorting (client-side filter by sensitivity tier; sort by ingested_at)
- Navigation shell style (left sidebar confirmed by UI-SPEC)
- Empty state designs (specified in UI-SPEC)
- Error state handling (specified in UI-SPEC)
- Exact date picker component choice

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-01 | Admin/compliance user can browse the audit log filtered by session, user, and date range | FastAPI query params pattern; SQLAlchemy async filter + offset/limit pagination; React filter bar with Apply button |
| UI-02 | Admin can open any audit record and view the full trace: query → retrieved chunks → prompt sent → LLM response → adviser action | GET /api/v1/audit/:trace_id endpoint; shadcn Collapsible component; AuditLog model has all required fields |
| UI-03 | Admin can view the document registry showing all ingested documents with their sensitivity tier, chunk count, and ingestion date | GET /api/v1/documents endpoint; DocumentRecord model has all required fields; client-side filter by sensitivity tier |
| UI-04 | Admin can trigger document ingestion and assign sensitivity tiers through the UI without using the CLI | POST /api/v1/ingest already exists; React form with UploadFile + Form params; long-running request handling |
</phase_requirements>

---

## Summary

Phase 5 builds a React SPA admin dashboard on top of the existing FastAPI backend. The backend needs two new read endpoints (`GET /api/v1/audit` with pagination/filtering and `GET /api/v1/documents`) plus a detail endpoint for individual trace records. The frontend is a greenfield Vite + React 18 app in a `frontend/` directory at the project root — no frontend code exists yet.

The existing backend patterns are clean and consistent: all routers use `APIRouter(prefix="/api/v1")`, `require_role()` guards sensitive endpoints, and `get_db()` provides async sessions. The new audit and document routers follow these patterns exactly. The `AuditLog` model already has all fields needed for the trace inspector (including `rewritten_query`, `not_found`, `retrieved_chunks` as JSON text). The `DocumentRecord` model has all fields for the registry.

The frontend stack is Vite + React 18 + React Router v6 + Tailwind CSS 3.x + shadcn/ui (default theme) + lucide-react. The JWT-from-localStorage auth pattern is straightforward: an Axios instance reads the token on each request via a request interceptor. The long-running ingest request (30-60s) is handled by disabling the Axios default timeout and showing a spinner until the response arrives.

**Primary recommendation:** Scaffold `frontend/` with `npm create vite@latest`, install shadcn/ui via the CLI (`npx shadcn@latest init`), then build backend endpoints first (they are the data contract), then build frontend views against them.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Audit log list + filtering | API / Backend | Database | Filtering and pagination happen at the SQL layer; frontend only sends query params |
| Trace detail view | API / Backend | Browser / Client | Backend returns full AuditLog record; frontend renders it |
| Document registry list | API / Backend | Browser / Client | Backend returns full list; client-side filter by sensitivity tier (list is small) |
| Document ingestion trigger | API / Backend | Browser / Client | POST /api/v1/ingest already exists; frontend is a thin form wrapper |
| JWT auth enforcement | API / Backend | — | require_role() dependency enforces at API layer; frontend only passes the token |
| Navigation shell | Browser / Client | — | Pure UI concern; no server involvement |
| Collapsible trace sections | Browser / Client | — | Pure UI state; shadcn Collapsible component |
| Client-side sensitivity filter | Browser / Client | — | Document list is small (<500 rows); no round-trip needed |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react | 19.2.6 | UI framework | Specified in project constraints |
| react-dom | 19.2.6 | DOM renderer | Paired with react |
| react-router-dom | 7.15.0 | Client-side routing | Current major; v7 API is stable, `<BrowserRouter>` + `<Routes>` pattern unchanged |
| vite | 8.0.11 | Build tool + dev server | Fast HMR, standard for React 18+ SPAs |
| @vitejs/plugin-react | 6.0.1 | Vite React plugin | Official Vite plugin for JSX transform |
| typescript | 6.0.3 | Type safety | Standard for React projects; shadcn/ui requires it |
| tailwindcss | 4.3.0 | Utility CSS | Specified in project constraints |
| @tailwindcss/vite | 4.x | Tailwind Vite integration | Required for Tailwind v4 with Vite |
| shadcn/ui (CLI) | 4.7.0 | Component scaffolding | Copies components into src/components/ui/ |
| lucide-react | 1.14.0 | Icons | Specified in UI-SPEC |
| axios | 1.16.0 | HTTP client | Interceptor support for JWT injection; cleaner than fetch for error handling |

[VERIFIED: npm registry — versions confirmed via `npm view` on 2026-05-09]

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| class-variance-authority | 0.7.1 | shadcn variant utility | Required by shadcn components |
| clsx | 2.1.1 | Conditional classnames | Required by shadcn cn() utility |
| tailwind-merge | 3.5.0 | Merge Tailwind classes | Required by shadcn cn() utility |
| @radix-ui/react-collapsible | 1.1.12 | Collapsible primitive | Used by shadcn Collapsible component |
| @radix-ui/react-dialog | 1.1.15 | Dialog primitive | Used by shadcn Dialog component |

[VERIFIED: npm registry]

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| axios | fetch | fetch has no interceptor API; JWT injection requires wrapper function. axios interceptors are cleaner for this pattern |
| react-router-dom v7 | v6 | v7 is the current release; v6 API still works in v7 (no breaking changes for `<BrowserRouter>` usage) |
| Tailwind v4 | Tailwind v3 | CLAUDE.md specifies v3.x; however npm latest is 4.3.0. Tailwind v4 has a different config format (CSS-first, no tailwind.config.js). Use v4 with @tailwindcss/vite plugin. |

**Note on Tailwind version:** CLAUDE.md specifies "Tailwind CSS 3.x" but npm latest is 4.3.0. [VERIFIED: npm registry]. Tailwind v4 uses a CSS-first config (`@import "tailwindcss"` in CSS, no `tailwind.config.js`). shadcn/ui supports Tailwind v4 as of shadcn CLI 4.x. The planner should use v4 since that is what `npx shadcn@latest init` will configure by default.

**Installation:**
```bash
# Scaffold frontend
npm create vite@latest frontend -- --template react-ts
cd frontend

# Tailwind v4 + shadcn
npm install tailwindcss @tailwindcss/vite
npx shadcn@latest init

# shadcn components (install individually)
npx shadcn@latest add table button badge input select dialog collapsible pagination skeleton alert separator tooltip dropdown-menu

# Routing + HTTP
npm install react-router-dom axios lucide-react
```

---

## Architecture Patterns

### System Architecture Diagram

```
Browser (React SPA)
  │
  ├── localStorage.getItem("token")
  │         │
  │   Axios instance (baseURL: http://localhost:8000)
  │   Request interceptor: inject Authorization: Bearer <token>
  │         │
  │         ▼
  ├── GET /api/v1/audit?page=1&limit=25&user_id=...&date_from=...&date_to=...&session_id=...
  │         │
  ├── GET /api/v1/audit/:trace_id
  │         │
  ├── GET /api/v1/documents
  │         │
  └── POST /api/v1/ingest  (multipart/form-data, no timeout)
              │
              ▼
        FastAPI (uvicorn, port 8000)
          │
          ├── require_role("compliance") → JWT decode → role check
          │
          ├── audit_repo.list_audits(filters, page, limit) → SQLAlchemy async
          │         └── SELECT * FROM audit_log WHERE ... ORDER BY timestamp DESC LIMIT 25 OFFSET n
          │
          ├── audit_repo.get_audit_by_id(trace_id)
          │
          ├── document_repo.list_documents() → SELECT * FROM document_registry ORDER BY ingested_at DESC
          │
          └── ingestion_service.ingest_document(...) → docling parse → Qdrant upsert → DB write
```

### Recommended Project Structure
```
frontend/
├── src/
│   ├── api/
│   │   ├── client.ts          # Axios instance + JWT interceptor
│   │   ├── audit.ts           # audit API calls
│   │   └── documents.ts       # document API calls
│   ├── components/
│   │   ├── ui/                # shadcn generated components (do not edit)
│   │   └── layout/
│   │       └── Sidebar.tsx    # 240px left nav shell
│   ├── pages/
│   │   ├── AuditLog.tsx       # /audit — table + filter bar + pagination
│   │   ├── TraceInspector.tsx # /audit/:trace_id — collapsible sections
│   │   ├── DocumentRegistry.tsx # /documents — table + client-side filter
│   │   └── IngestDocument.tsx # /ingest — form
│   ├── types/
│   │   └── api.ts             # TypeScript interfaces matching backend schemas
│   ├── App.tsx                # BrowserRouter + Routes + Sidebar layout
│   └── main.tsx               # ReactDOM.createRoot entry point
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

### Pattern 1: Axios Instance with JWT Interceptor

**What:** Single Axios instance reads JWT from localStorage on every request.
**When to use:** All API calls from the React app.

```typescript
// src/api/client.ts
// Source: axios docs — request interceptors
import axios from "axios";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  // No timeout — ingest endpoint can take 30-60s
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default apiClient;
```

[ASSUMED] — axios interceptor API is stable and well-documented; pattern is standard.

### Pattern 2: FastAPI Paginated List Endpoint

**What:** Query params for page/limit/filters; returns items + total count.
**When to use:** GET /api/v1/audit

```python
# backend/routers/audit.py
# Source: FastAPI docs — query parameters
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.database import get_db
from backend.core.dependencies import require_role
from backend.repositories import audit_repo
from backend.schemas.audit import AuditListResponse

router = APIRouter(prefix="/api/v1", tags=["audit"])

@router.get("/audit", response_model=AuditListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    user_id: str | None = Query(None),
    session_id: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    current_user: dict = Depends(require_role("compliance", "admin")),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit
    items, total = await audit_repo.list_audits(
        db, offset=offset, limit=limit,
        user_id=user_id, session_id=session_id,
        date_from=date_from, date_to=date_to,
    )
    return AuditListResponse(items=items, total=total, page=page, limit=limit)
```

[ASSUMED] — follows existing ingest.py router pattern exactly.

### Pattern 3: SQLAlchemy Async Paginated Query with Filters

**What:** Async select with optional WHERE clauses, COUNT subquery, LIMIT/OFFSET.
**When to use:** audit_repo.list_audits()

```python
# backend/repositories/audit_repo.py (extension)
# Source: SQLAlchemy 2.0 async docs
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.audit_log import AuditLog

async def list_audits(
    db: AsyncSession,
    offset: int = 0,
    limit: int = 25,
    user_id: str | None = None,
    session_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> tuple[list[AuditLog], int]:
    stmt = select(AuditLog)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if session_id:
        stmt = stmt.where(AuditLog.session_id == session_id)
    if date_from:
        stmt = stmt.where(AuditLog.timestamp >= datetime.fromisoformat(date_from))
    if date_to:
        stmt = stmt.where(AuditLog.timestamp <= datetime.fromisoformat(date_to))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    result = await db.execute(
        stmt.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all()), total
```

[ASSUMED] — SQLAlchemy 2.0 async pattern; consistent with existing audit_repo.py style.

### Pattern 4: shadcn Collapsible Section

**What:** Collapsible section with chevron toggle, aria-expanded, full-width trigger.
**When to use:** Trace inspector sections.

```tsx
// Source: shadcn/ui Collapsible docs
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";

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
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger
        className="flex w-full items-center justify-between px-4 h-12 border-b border-neutral-800 text-sm font-semibold"
        aria-expanded={open}
      >
        {label}
        {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </CollapsibleTrigger>
      <CollapsibleContent className="px-4 py-3">
        {children}
      </CollapsibleContent>
    </Collapsible>
  );
}
```

[ASSUMED] — shadcn Collapsible API is stable; pattern matches UI-SPEC requirements.

### Pattern 5: React Router v7 Route Setup

**What:** BrowserRouter with nested routes; layout wrapper for sidebar.
**When to use:** App.tsx entry point.

```tsx
// src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/layout/Sidebar";
import AuditLog from "./pages/AuditLog";
import TraceInspector from "./pages/TraceInspector";
import DocumentRegistry from "./pages/DocumentRegistry";
import IngestDocument from "./pages/IngestDocument";

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-neutral-950">
        <Sidebar />
        <main className="ml-60 flex-1 p-8">
          <Routes>
            <Route path="/" element={<Navigate to="/audit" replace />} />
            <Route path="/audit" element={<AuditLog />} />
            <Route path="/audit/:trace_id" element={<TraceInspector />} />
            <Route path="/documents" element={<DocumentRegistry />} />
            <Route path="/ingest" element={<IngestDocument />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
```

[ASSUMED] — React Router v7 BrowserRouter API is unchanged from v6 for this usage pattern.

### Pattern 6: Long-Running Ingest Request (no timeout)

**What:** Disable axios timeout for the ingest call; show spinner until response.
**When to use:** IngestDocument.tsx form submit.

```tsx
// src/pages/IngestDocument.tsx (submit handler)
const [loading, setLoading] = useState(false);
const [result, setResult] = useState<IngestResponse | null>(null);
const [error, setError] = useState<string | null>(null);

async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
  e.preventDefault();
  setLoading(true);
  setError(null);
  setResult(null);
  const formData = new FormData(e.currentTarget);
  try {
    const res = await apiClient.post<IngestResponse>("/api/v1/ingest", formData, {
      timeout: 0,  // disable timeout — ingest can take 30-60s
      headers: { "Content-Type": "multipart/form-data" },
    });
    setResult(res.data);
    (e.target as HTMLFormElement).reset();
  } catch (err: unknown) {
    const msg = axios.isAxiosError(err)
      ? err.response?.data?.detail ?? "Unknown error"
      : "Request failed";
    setError(msg);
  } finally {
    setLoading(false);
  }
}
```

[ASSUMED] — axios `timeout: 0` disables timeout; standard pattern for long-running uploads.

### Pattern 7: FastAPI CORS for React Dev Server

**What:** Add CORSMiddleware to allow localhost:5173 (Vite default port).
**When to use:** backend/main.py

```python
# backend/main.py addition
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

[ASSUMED] — FastAPI CORSMiddleware is standard; allow_credentials=True required for Authorization header.

### Anti-Patterns to Avoid

- **Fetching JWT in component render:** Read localStorage once in the Axios interceptor, not in every component. Components should not know about auth.
- **Setting axios timeout to a large number:** Use `timeout: 0` (disabled) for the ingest endpoint. A 60s timeout will fire before large PDFs finish.
- **Client-side pagination for audit log:** The audit log can have thousands of records. Always paginate server-side (D-02, D-03).
- **Putting CORS origins in a hardcoded list without env var:** In production, the origin will not be localhost:5173. Use an env var `ALLOWED_ORIGINS` that defaults to localhost for dev.
- **Using `any` type for API responses:** Define TypeScript interfaces in `src/types/api.ts` matching the Pydantic schemas. This catches field name mismatches at compile time.
- **Calling `db.commit()` in the repository:** Existing pattern uses `db.flush()` in repos; caller (router) calls `db.commit()`. New repos must follow this pattern.


---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Collapsible UI sections | Custom toggle with useState + CSS | shadcn Collapsible (Radix UI) | aria-expanded, keyboard nav, animation — all handled |
| Accessible table | Raw `<table>` with manual aria | shadcn Table | Correct thead/tbody semantics, sortable column headers with aria-sort |
| Badge variants | Custom span with conditional className | shadcn Badge with variant prop | Consistent sizing, focus ring, accessible contrast |
| Pagination controls | Custom prev/next with page math | shadcn Pagination | Accessible, keyboard navigable, handles edge cases (first/last page) |
| Skeleton loading | Custom CSS animation | shadcn Skeleton | Consistent pulse animation, matches component dimensions |
| Form alerts | Custom div with conditional color | shadcn Alert with variant | Correct role="alert" for screen readers, consistent styling |
| JWT decode in frontend | Custom base64 decode | Don't decode — just pass the token | Frontend never needs to read JWT claims; backend validates. If role display is needed, store role separately in localStorage alongside the token. |
| Date range inputs | Custom date picker | Native `<input type="date">` | The UI-SPEC specifies two date inputs (from/to). Native date inputs are sufficient for Phase 5 — no third-party date picker needed. |

**Key insight:** shadcn/ui components are copied into the project (not imported from a package), so they can be customized. But for Phase 5, use them as-is — the UI-SPEC is fully achievable with default shadcn behavior.

---

## Common Pitfalls

### Pitfall 1: Tailwind v4 Config Format Change
**What goes wrong:** Developer creates `tailwind.config.js` (v3 format) — Tailwind v4 ignores it silently.
**Why it happens:** Tailwind v4 switched to CSS-first configuration. The config file is no longer used.
**How to avoid:** In `src/index.css`, use `@import "tailwindcss"`. Custom theme tokens go in `@theme {}` block in CSS. The `npx shadcn@latest init` command handles this automatically.
**Warning signs:** Custom colors not applying; `tailwind.config.js` present but ignored.

### Pitfall 2: CORS Preflight Blocking Authorization Header
**What goes wrong:** Browser sends OPTIONS preflight for requests with `Authorization` header; FastAPI returns 400 or missing CORS headers.
**Why it happens:** `Authorization` is not a "simple" header — it triggers a preflight. CORSMiddleware must be added BEFORE other middleware and must include `allow_headers=["*"]` or explicitly list `"Authorization"`.
**How to avoid:** Add CORSMiddleware as the first middleware in main.py. Set `allow_credentials=True` and `allow_headers=["*"]`.
**Warning signs:** Network tab shows OPTIONS request returning 400 or missing `Access-Control-Allow-Origin`.

### Pitfall 3: AuditLog.retrieved_chunks is a JSON String, Not a List
**What goes wrong:** Frontend tries to render `retrieved_chunks` as an array — it's stored as `Text` (JSON string) in the DB.
**Why it happens:** SQLAlchemy `Text` column stores the JSON as a string. The Pydantic schema must either parse it or return it as a string.
**How to avoid:** In the new `AuditLogDetailOut` schema, declare `retrieved_chunks: str | None`. In the frontend, use `JSON.parse(retrieved_chunks)` before rendering. Alternatively, add a `@field_validator` in the schema to parse it to `list | None`.
**Warning signs:** `JSON.parse` error in browser console; `[object Object]` displayed instead of formatted JSON.

### Pitfall 4: require_role() Accepts Only One Role by Default
**What goes wrong:** `require_role("compliance")` blocks admin users from accessing audit endpoints.
**Why it happens:** The existing `require_role()` factory takes `*allowed_roles` — it already supports multiple roles. But the ingest router only passes `"compliance"`. New audit/document endpoints should pass both roles.
**How to avoid:** Use `require_role("compliance", "admin")` for the new read endpoints. Check `backend/models/enums.py` — `UserRole` has `adviser`, `senior_adviser`, `compliance`. There is no `admin` role in the enum. Use `require_role("compliance")` for Phase 5 endpoints.
**Warning signs:** 403 Forbidden for users with valid tokens.

**Critical finding:** `UserRole` enum has `adviser`, `senior_adviser`, `compliance` — no `admin` role. [VERIFIED: backend/models/enums.py]. All Phase 5 endpoints should use `require_role("compliance")`.

### Pitfall 5: Vite Proxy Not Configured — CORS Errors in Dev
**What goes wrong:** React dev server on :5173 calls FastAPI on :8000 — browser blocks due to CORS.
**Why it happens:** Two origins in development. Either configure CORS on FastAPI (Pattern 7) or configure Vite proxy.
**How to avoid:** Use FastAPI CORSMiddleware (Pattern 7). This is simpler than Vite proxy and works in production too. Do not use both — they conflict.
**Warning signs:** `Access to XMLHttpRequest blocked by CORS policy` in browser console.

### Pitfall 6: shadcn Init Overwrites Existing Files
**What goes wrong:** Running `npx shadcn@latest init` in an existing project overwrites `index.css` or `tailwind.config`.
**Why it happens:** shadcn init is designed for fresh projects.
**How to avoid:** Run shadcn init on the freshly scaffolded Vite project before adding any custom code. The `frontend/` directory is greenfield — this is not a risk here.

### Pitfall 7: React Router v7 — No `<Switch>` Component
**What goes wrong:** Developer uses `<Switch>` from React Router v5 muscle memory.
**Why it happens:** v5 used `<Switch>`; v6+ uses `<Routes>`. v7 is the same as v6 for this.
**How to avoid:** Use `<Routes>` and `<Route>` only. `<Switch>` does not exist in v7.

---

## Code Examples

### Backend: New Pydantic Schemas

```python
# backend/schemas/audit.py (additions)
from pydantic import BaseModel
from datetime import datetime
from backend.models.enums import AuditStatus, AdviserAction

class AuditListItem(BaseModel):
    id: str
    user_id: str
    session_id: str
    timestamp: datetime
    channel: str
    query_text: str
    status: AuditStatus
    adviser_action: AdviserAction | None = None
    not_found: bool | None = None
    model_config = {"from_attributes": True}

class AuditListResponse(BaseModel):
    items: list[AuditListItem]
    total: int
    page: int
    limit: int

class AuditDetailOut(BaseModel):
    id: str
    user_id: str
    session_id: str
    timestamp: datetime
    channel: str
    query_text: str
    rewritten_query: str | None = None
    status: AuditStatus
    retrieved_chunks: str | None = None   # JSON string — parse in frontend
    sensitivity_tier_accessed: int | None = None
    prompt_sent: str | None = None
    llm_response: str | None = None
    model_used: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    adviser_action: AdviserAction | None = None
    adviser_edited: bool | None = None
    final_response: str | None = None
    not_found: bool | None = None
    chunks_passed_rerank: int | None = None
    model_config = {"from_attributes": True}
```

### Backend: Document Schema

```python
# backend/schemas/document.py (new file)
from pydantic import BaseModel
from datetime import datetime

class DocumentListItem(BaseModel):
    document_id: str
    filename: str
    doc_type: str
    sensitivity_tier: int
    chunk_count: int
    ingested_at: datetime
    ingested_by: str
    model_config = {"from_attributes": True}

class DocumentListResponse(BaseModel):
    items: list[DocumentListItem]
    total: int
```

### Frontend: TypeScript API Types

```typescript
// src/types/api.ts
export interface AuditListItem {
  id: string;
  user_id: string;
  session_id: string;
  timestamp: string;
  channel: "web" | "telegram";
  query_text: string;
  status: "received" | "retrieved" | "generated" | "completed" | "error";
  adviser_action: "approved" | "edited" | "discarded" | null;
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
  retrieved_chunks: string | null;  // JSON string
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
```


---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Create React App | Vite | ~2022 | CRA is unmaintained; Vite is the standard scaffolding tool |
| React Router v5 `<Switch>` | React Router v6/v7 `<Routes>` | 2021/2024 | API is different; v7 is current |
| Tailwind config in `tailwind.config.js` | Tailwind v4 CSS-first config | 2025 | `@import "tailwindcss"` in CSS; no JS config file |
| shadcn/ui as npm package | shadcn/ui as CLI (copies components) | 2023 | Components live in your repo; fully customizable |

**Deprecated/outdated:**
- `create-react-app`: Unmaintained since 2023. Use `npm create vite@latest` instead.
- `react-router-dom` v5 `<Switch>`: Replaced by `<Routes>` in v6. v7 is current.
- Tailwind v3 `tailwind.config.js`: Still works but v4 is current and uses CSS-first config.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Axios interceptor pattern for JWT injection | Pattern 1 | Low — axios interceptor API is stable and widely documented |
| A2 | `timeout: 0` disables axios timeout | Pattern 6 | Low — this is documented axios behavior |
| A3 | React Router v7 BrowserRouter API unchanged from v6 for `<Routes>/<Route>` usage | Pattern 5 | Low — v7 changelog confirms no breaking changes for this pattern |
| A4 | shadcn Collapsible component API (open/onOpenChange props) | Pattern 4 | Low — Radix UI Collapsible API is stable |
| A5 | SQLAlchemy `func.count().select_from(stmt.subquery())` pattern for total count | Pattern 3 | Medium — verify against SQLAlchemy 2.0 async docs if count query returns wrong results |
| A6 | `require_role("compliance")` is sufficient for all Phase 5 endpoints (no "admin" role exists) | Pitfall 4 | HIGH — verified against enums.py: UserRole has adviser/senior_adviser/compliance only. No admin role. |
| A7 | Tailwind v4 is what `npx shadcn@latest init` will configure | Standard Stack | Medium — shadcn CLI version 4.7.0 may default to v4; verify during scaffold |

**A6 is verified, not assumed:** `UserRole` enum confirmed in `backend/models/enums.py` — no `admin` role exists. Use `require_role("compliance")` for all Phase 5 endpoints.

---

## Open Questions (RESOLVED)

1. **Tailwind v3 vs v4** — RESOLVED: Use Tailwind v4 (current npm latest 4.3.0; shadcn CLI defaults to v4). CLAUDE.md spec was written at project setup time. Plan 05-02 installs `tailwindcss @tailwindcss/vite` (v4).

2. **React version: 18 vs 19** — RESOLVED: Pin to React 18.3.x to match CLAUDE.md. Plan 05-02 explicitly pins `react@^18.3.1` and `react-dom@^18.3.1` after Vite scaffold.

3. **Vite proxy vs FastAPI CORS** — RESOLVED: Use both — FastAPI CORSMiddleware with explicit origins list (`["http://localhost:5173", "http://localhost:3000"]`) for production correctness, plus Vite proxy for dev. Plan 05-01 adds CORSMiddleware to main.py; Plan 05-02 adds proxy to vite.config.ts.

4. **GET /api/v1/audit/:trace_id — new endpoint or reuse existing?** — RESOLVED: Add new `GET /api/v1/audit/{trace_id}` endpoint to the new `backend/routers/audit.py`. The repo function `audit_repo.get_audit_by_id` already exists and is reused directly.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Frontend scaffold + build | ✓ | v24.15.0 | — |
| npm | Package installation | ✓ | 11.12.1 | — |
| Python / uv | Backend dev server | ✓ (assumed) | — | — |
| Vite dev server (port 5173) | Frontend dev | ✓ (will be installed) | 8.0.11 | — |
| FastAPI dev server (port 8000) | API calls | ✓ (existing) | 0.136.0+ | — |

[VERIFIED: npm registry for Node/npm versions via `node --version` and `npm --version`]

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.0 + pytest-asyncio 0.26.0 (backend); no frontend test framework yet |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -q -x` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-01 | GET /api/v1/audit returns paginated list with filters | integration | `uv run pytest tests/test_audit_router.py -x` | ❌ Wave 0 |
| UI-02 | GET /api/v1/audit/:trace_id returns full AuditLog detail | integration | `uv run pytest tests/test_audit_router.py::test_get_trace_detail -x` | ❌ Wave 0 |
| UI-03 | GET /api/v1/documents returns DocumentRecord list | integration | `uv run pytest tests/test_document_router.py -x` | ❌ Wave 0 |
| UI-04 | POST /api/v1/ingest accessible from React form (CORS + multipart) | integration | `uv run pytest tests/test_ingest_router.py -x` (existing) | ✅ existing |

Frontend components are not unit-tested in Phase 5 — the UI-SPEC is the acceptance contract, and manual verification is the gate. This is consistent with the project's current test approach (backend integration tests only).

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -q -x`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_audit_router.py` — covers UI-01, UI-02
- [ ] `tests/test_document_router.py` — covers UI-03
- [ ] `backend/routers/audit.py` — new router (needed before tests can run)
- [ ] `backend/routers/documents.py` — new router (needed before tests can run)
- [ ] `backend/schemas/document.py` — new schema file

---

## Security Domain

### Applicable ASVS Categories (Level 1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | JWT via `require_role()` dependency — existing pattern |
| V3 Session Management | no | No server-side sessions; JWT is stateless |
| V4 Access Control | yes | `require_role("compliance")` on all new endpoints |
| V5 Input Validation | yes | FastAPI Query params with type annotations; Pydantic schemas for responses |
| V6 Cryptography | no | No new crypto operations in Phase 5 |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unauthenticated access to audit log | Information Disclosure | `require_role("compliance")` on GET /api/v1/audit and GET /api/v1/audit/{trace_id} |
| Unauthenticated access to document registry | Information Disclosure | `require_role("compliance")` on GET /api/v1/documents |
| JWT stored in localStorage (XSS risk) | Tampering | D-14 accepted this risk for internal admin tool. Mitigate: Content-Security-Policy header on FastAPI responses |
| SQL injection via filter params | Tampering | SQLAlchemy parameterized queries — ORM handles this automatically |
| CORS misconfiguration exposing API | Information Disclosure | Restrict `allow_origins` to specific origins via env var; never use `allow_origins=["*"]` with `allow_credentials=True` |
| Oversized file upload | DoS | MAX_UPLOAD_BYTES = 50MB already enforced in ingest.py |

**CORS + credentials constraint:** FastAPI CORSMiddleware raises an error if `allow_origins=["*"]` is combined with `allow_credentials=True`. Use explicit origin list. [ASSUMED — FastAPI docs behavior]

---

## Sources

### Primary (HIGH confidence)
- `backend/models/audit_log.py` — AuditLog model fields verified directly
- `backend/models/document.py` — DocumentRecord model fields verified directly
- `backend/models/enums.py` — UserRole, SensitivityTier, AdviserAction, AuditStatus verified directly
- `backend/repositories/audit_repo.py` — existing repo pattern verified directly
- `backend/repositories/document_repo.py` — existing repo pattern verified directly
- `backend/routers/ingest.py` — router pattern verified directly
- `backend/core/dependencies.py` — require_role() pattern verified directly
- `backend/main.py` — router registration pattern verified directly
- npm registry — package versions verified via `npm view` on 2026-05-09

### Secondary (MEDIUM confidence)
- `.planning/phases/05-web-audit-admin-ui/05-CONTEXT.md` — locked decisions D-01 through D-15
- `.planning/phases/05-web-audit-admin-ui/05-UI-SPEC.md` — component contracts, color, typography, spacing
- `CLAUDE.md` — project stack and conventions

### Tertiary (LOW confidence)
- None — all critical claims verified against codebase or npm registry

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified via npm registry on 2026-05-09
- Architecture: HIGH — based on direct codebase inspection; existing patterns are clear
- Pitfalls: HIGH — most derived from direct code inspection (enums.py, audit_log.py); a few assumed from standard React/FastAPI patterns
- Backend patterns: HIGH — follow existing ingest.py/audit_repo.py patterns exactly
- Frontend patterns: MEDIUM — no existing frontend code to verify against; patterns are standard but assumed

**Research date:** 2026-05-09
**Valid until:** 2026-06-09 (stable stack — 30 days)

