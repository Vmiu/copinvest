# Phase 5: Web Audit & Admin UI - Pattern Map

**Mapped:** 2026-05-09
**Files analyzed:** 14
**Analogs found:** 7 / 14 (7 backend with analogs; 7 frontend greenfield)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/routers/audit.py` | router | request-response | `backend/routers/ingest.py` | role-match |
| `backend/routers/documents.py` | router | request-response | `backend/routers/ingest.py` | role-match |
| `backend/repositories/audit_repo.py` | repository | CRUD | `backend/repositories/document_repo.py` | exact |
| `backend/repositories/document_repo.py` | repository | CRUD | `backend/repositories/audit_repo.py` | exact |
| `backend/schemas/audit.py` | schema | transform | `backend/schemas/ingest.py` | role-match |
| `backend/schemas/document.py` | schema | transform | `backend/schemas/ingest.py` | role-match |
| `backend/main.py` | config | request-response | self (modify) | exact |
| `frontend/src/App.tsx` | component | request-response | none (greenfield) | none |
| `frontend/src/api/client.ts` | utility | request-response | none (greenfield) | none |
| `frontend/src/pages/AuditLog.tsx` | component | CRUD | none (greenfield) | none |
| `frontend/src/pages/TraceInspector.tsx` | component | request-response | none (greenfield) | none |
| `frontend/src/pages/DocumentRegistry.tsx` | component | CRUD | none (greenfield) | none |
| `frontend/src/pages/IngestDocument.tsx` | component | request-response | none (greenfield) | none |
| `frontend/src/components/layout/Sidebar.tsx` | component | event-driven | none (greenfield) | none |

---

## Pattern Assignments

### `backend/routers/audit.py` (router, request-response)

**Analog:** `backend/routers/ingest.py`

**Imports pattern** (`backend/routers/ingest.py` lines 1-13):
```python
import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import require_role
from backend.schemas.audit import AuditListResponse, AuditDetailOut
from backend.repositories import audit_repo

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["audit"])
```

**Auth/guard pattern** (`backend/routers/ingest.py` line 25):
```python
current_user: dict = Depends(require_role("compliance")),
```
Note: `UserRole` enum has `adviser`, `senior_adviser`, `compliance` only — no `admin` role. Use `require_role("compliance")` for all Phase 5 endpoints. Verified in `backend/models/enums.py`.

**Core GET list pattern** (modeled on ingest.py structure + RESEARCH.md Pattern 2):
```python
from fastapi import Query

@router.get("/audit", response_model=AuditListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    user_id: str | None = Query(None),
    session_id: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    current_user: dict = Depends(require_role("compliance")),
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

**Core GET detail pattern** (modeled on audit_repo.get_audit_by_id + ingest.py error handling):
```python
@router.get("/audit/{trace_id}", response_model=AuditDetailOut)
async def get_audit_detail(
    trace_id: str,
    current_user: dict = Depends(require_role("compliance")),
    db: AsyncSession = Depends(get_db),
):
    record = await audit_repo.get_audit_by_id(db, trace_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Audit record not found")
    return record
```

**Error handling pattern** (`backend/routers/ingest.py` lines 53-55):
```python
except ValueError as e:
    raise HTTPException(status_code=422, detail=str(e))
except RuntimeError as e:
    raise HTTPException(status_code=422, detail=str(e))
```
For read-only endpoints, only the 404 case applies — no try/except needed beyond the None check.

---

### `backend/routers/documents.py` (router, request-response)

**Analog:** `backend/routers/ingest.py`

**Imports pattern** (same structure as ingest.py):
```python
import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import require_role
from backend.schemas.document import DocumentListResponse
from backend.repositories import document_repo

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["documents"])
```

**Core GET list pattern**:
```python
@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    current_user: dict = Depends(require_role("compliance")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await document_repo.list_documents(db)
    return DocumentListResponse(items=items, total=total)
```

No pagination needed — document list is small. Client-side filter by sensitivity tier (D-11, RESEARCH.md architecture table).

---

### `backend/repositories/audit_repo.py` (repository, CRUD — EXTEND)

**Analog:** `backend/repositories/audit_repo.py` (self) + `backend/repositories/document_repo.py`

**Existing pattern** (`backend/repositories/audit_repo.py` lines 1-10):
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.audit_log import AuditLog

async def get_audit_by_id(db: AsyncSession, trace_id: str) -> AuditLog | None:
    result = await db.execute(select(AuditLog).where(AuditLog.id == trace_id))
    return result.scalar_one_or_none()
```

**flush pattern** (`backend/repositories/document_repo.py` line 28 and audit_repo.py line 33):
```python
await db.flush()  # repos flush; routers commit
```

**New list_audits function to add** (RESEARCH.md Pattern 3):
```python
from datetime import datetime
from sqlalchemy import select, func

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

---

### `backend/repositories/document_repo.py` (repository, CRUD — EXTEND)

**Analog:** `backend/repositories/document_repo.py` (self)

**Existing pattern** (`backend/repositories/document_repo.py` lines 1-10):
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.document import DocumentRecord

async def get_document_by_id(db: AsyncSession, document_id: str) -> DocumentRecord | None:
    result = await db.execute(
        select(DocumentRecord).where(DocumentRecord.document_id == document_id)
    )
    return result.scalar_one_or_none()
```

**New list_documents function to add**:
```python
async def list_documents(db: AsyncSession) -> tuple[list[DocumentRecord], int]:
    stmt = select(DocumentRecord).order_by(DocumentRecord.ingested_at.desc())
    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return items, len(items)
```

No pagination — document list is small. No `func.count()` subquery needed.

---

### `backend/schemas/audit.py` (schema — EXTEND)

**Analog:** `backend/schemas/audit.py` (self) + `backend/schemas/ingest.py`

**Existing pattern** (`backend/schemas/audit.py` lines 1-19):
```python
from pydantic import BaseModel
from datetime import datetime
from backend.models.enums import AuditStatus, AdviserAction

class AuditRecordOut(BaseModel):
    id: str
    ...
    model_config = {"from_attributes": True}
```

**New classes to add** (RESEARCH.md Code Examples):
```python
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

---

### `backend/schemas/document.py` (schema — NEW)

**Analog:** `backend/schemas/ingest.py`

**Pattern** (`backend/schemas/ingest.py` lines 1-13):
```python
from pydantic import BaseModel

class IngestResponse(BaseModel):
    document_id: str
    filename: str
    ...
```

**New file content** (RESEARCH.md Code Examples):
```python
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

---

### `backend/main.py` (config — MODIFY)

**Analog:** `backend/main.py` (self)

**Existing router registration pattern** (`backend/main.py` lines 56-58):
```python
app.include_router(auth_router)
app.include_router(ingest_router)
app.include_router(query_router)
```

**Existing import pattern** (`backend/main.py` lines 13-15):
```python
from backend.routers.auth import router as auth_router
from backend.routers.ingest import router as ingest_router
from backend.routers.query import router as query_router
```

**Additions needed:**
```python
# Add to imports
from fastapi.middleware.cors import CORSMiddleware
from backend.routers.audit import router as audit_router
from backend.routers.documents import router as documents_router

# Add BEFORE app.include_router calls — CORS must be registered first
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origins],  # env var; default "http://localhost:5173"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add alongside existing include_router calls
app.include_router(audit_router)
app.include_router(documents_router)
```

CORS pitfall: `allow_origins=["*"]` with `allow_credentials=True` raises a FastAPI error. Use explicit origin list from env var. Add middleware before `include_router` calls.

---

## Frontend Patterns (Greenfield — No Existing Analog)

All frontend files are new. No existing frontend code exists in the project. Patterns come from RESEARCH.md.

---

### `frontend/src/api/client.ts` (utility, request-response)

**Analog:** None (greenfield)
**Source:** RESEARCH.md Pattern 1

```typescript
// frontend/src/api/client.ts
import axios from "axios";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  // No default timeout — ingest endpoint can take 30-60s
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

Key: no timeout set at instance level. Override per-call with `{ timeout: 0 }` for ingest only.

---

### `frontend/src/App.tsx` (component, request-response)

**Analog:** None (greenfield)
**Source:** RESEARCH.md Pattern 5

```tsx
// frontend/src/App.tsx
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

Use `<Routes>` not `<Switch>` — v7 API. Sidebar is 240px (D-15); `ml-60` = 240px offset.

---

### `frontend/src/components/layout/Sidebar.tsx` (component, event-driven)

**Analog:** None (greenfield)
**Source:** RESEARCH.md + UI-SPEC (D-15: 240px left sidebar, 4 nav items)

```tsx
// Pattern: NavLink with active state via React Router
import { NavLink } from "react-router-dom";
import { ClipboardList, FileText, Upload } from "lucide-react";

const navItems = [
  { to: "/audit", label: "Audit Log", icon: ClipboardList },
  { to: "/documents", label: "Document Registry", icon: FileText },
  { to: "/ingest", label: "Ingest Document", icon: Upload },
];

// NavLink className receives { isActive } — use for active highlight
<NavLink
  to={item.to}
  className={({ isActive }) =>
    `flex items-center gap-3 px-4 py-2 rounded-md text-sm ${
      isActive ? "bg-neutral-800 text-white" : "text-neutral-400 hover:text-white"
    }`
  }
>
```

TraceInspector has no sidebar nav item — it is only reachable by clicking an audit row (D-04).

---

### `frontend/src/pages/AuditLog.tsx` (component, CRUD)

**Analog:** None (greenfield)
**Source:** RESEARCH.md + UI-SPEC (D-01 through D-04)

Key patterns:
- shadcn `Table` for the 6-column display (timestamp, user, channel, query truncated, status, adviser action)
- Filter bar: two `<input type="date">` (from/to), text inputs for user_id and session_id, Apply button
- Filters sent to backend on Apply click only — not on every keystroke (D-02)
- shadcn `Pagination` for prev/next (D-03)
- Row click: `useNavigate()` to `/audit/:trace_id` (D-04)
- shadcn `Skeleton` while loading; shadcn `Alert` on error

```tsx
// State shape
const [filters, setFilters] = useState({ user_id: "", session_id: "", date_from: "", date_to: "" });
const [applied, setApplied] = useState(filters);  // only update on Apply
const [page, setPage] = useState(1);

// Fetch triggers on applied + page change, not on filter input change
useEffect(() => {
  fetchAuditLogs(applied, page);
}, [applied, page]);

// Apply button handler
function handleApply() {
  setPage(1);
  setApplied({ ...filters });
}
```

---

### `frontend/src/pages/TraceInspector.tsx` (component, request-response)

**Analog:** None (greenfield)
**Source:** RESEARCH.md Pattern 4 + UI-SPEC (D-05, D-06)

Key patterns:
- `useParams()` to get `trace_id`
- Fetch `GET /api/v1/audit/:trace_id` on mount
- shadcn `Collapsible` for each section (D-06)
- `retrieved_chunks` is a JSON string — `JSON.parse()` before rendering

```tsx
// RESEARCH.md Pattern 4 — reuse as-is for each section
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";

function TraceSection({ label, defaultOpen = false, children }: {
  label: string; defaultOpen?: boolean; children: React.ReactNode;
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
      <CollapsibleContent className="px-4 py-3">{children}</CollapsibleContent>
    </Collapsible>
  );
}
```

Sections: Query (defaultOpen=true), Retrieved Chunks, Prompt Sent, LLM Response, Adviser Action.

---

### `frontend/src/pages/DocumentRegistry.tsx` (component, CRUD)

**Analog:** None (greenfield)
**Source:** RESEARCH.md + UI-SPEC (D-11)

Key patterns:
- Fetch full list from `GET /api/v1/documents` on mount (no server-side pagination)
- Client-side filter by sensitivity_tier via `<select>` — list is small
- Client-side sort by ingested_at (default: newest first)
- shadcn `Table`, `Badge` for sensitivity tier display

```tsx
// Client-side filter pattern
const [tierFilter, setTierFilter] = useState<number | "all">("all");
const filtered = tierFilter === "all"
  ? documents
  : documents.filter(d => d.sensitivity_tier === tierFilter);
```

---

### `frontend/src/pages/IngestDocument.tsx` (component, request-response)

**Analog:** None (greenfield)
**Source:** RESEARCH.md Pattern 6 + UI-SPEC (D-07 through D-10)

```tsx
// RESEARCH.md Pattern 6 — copy directly
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

Form stays after success (D-09). Show `IngestResponse` fields inline: document_id, chunk_count, warnings. Use shadcn `Alert` for error (D-10), shadcn `Skeleton` or spinner while loading (D-08).

---

## Shared Patterns

### Authentication (JWT injection)
**Source:** RESEARCH.md Pattern 1 — `frontend/src/api/client.ts`
**Apply to:** All frontend API calls
```typescript
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
```
Components never read localStorage directly. All auth is in the axios interceptor.

### require_role guard
**Source:** `backend/core/dependencies.py` lines 79-87
**Apply to:** All new backend routers (audit.py, documents.py)
```python
def require_role(*allowed_roles: str):
    async def _check(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"Role '{current_user['role']}' not authorized")
        return current_user
    return _check
```
Use `require_role("compliance")` — no `admin` role exists in `UserRole` enum.

### Async DB session
**Source:** `backend/routers/ingest.py` line 27 + `backend/core/dependencies.py`
**Apply to:** All new backend routers
```python
db: AsyncSession = Depends(get_db),
```

### Repository flush pattern
**Source:** `backend/repositories/document_repo.py` line 28, `backend/repositories/audit_repo.py` line 33
**Apply to:** All new repository write functions
```python
await db.flush()  # repos flush; routers call db.commit()
```

### Structured logging
**Source:** `backend/routers/ingest.py` lines 1, 13
**Apply to:** All new backend routers
```python
import structlog
logger = structlog.get_logger()
```

### TypeScript API types
**Source:** RESEARCH.md Code Examples — `frontend/src/types/api.ts`
**Apply to:** All frontend pages
Define interfaces matching Pydantic schemas. Never use `any` for API responses. Key types: `AuditListItem`, `AuditListResponse`, `AuditDetailOut`, `DocumentListItem`, `DocumentListResponse`, `IngestResponse`.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `frontend/src/App.tsx` | component | request-response | No frontend exists yet |
| `frontend/src/api/client.ts` | utility | request-response | No frontend exists yet |
| `frontend/src/pages/AuditLog.tsx` | component | CRUD | No frontend exists yet |
| `frontend/src/pages/TraceInspector.tsx` | component | request-response | No frontend exists yet |
| `frontend/src/pages/DocumentRegistry.tsx` | component | CRUD | No frontend exists yet |
| `frontend/src/pages/IngestDocument.tsx` | component | request-response | No frontend exists yet |
| `frontend/src/components/layout/Sidebar.tsx` | component | event-driven | No frontend exists yet |

For all frontend files, use RESEARCH.md patterns directly. The patterns in that document are concrete and complete.

---

## Metadata

**Analog search scope:** `backend/routers/`, `backend/repositories/`, `backend/schemas/`, `backend/models/`, `backend/core/`, `backend/main.py`
**Files scanned:** 10 backend files read directly
**Pattern extraction date:** 2026-05-09
