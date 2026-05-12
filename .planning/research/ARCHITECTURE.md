# Architecture Patterns — v3.0 Agent + Drafting

**Domain:** GenAI assistant for Hong Kong investment advisers
**Researched:** 2026-05-13
**Confidence:** HIGH

## Recommended Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────┐
│                    Telegram Bot                           │
│  (adviser types freetext → agent handler → reply/docx)   │
└──────────────┬───────────────────────────────┬───────────┘
               │                               │
               ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│    Agent Service (NEW)   │    │  Inline Keyboard Handler │
│  ┌────────────────────┐  │    │  (approve/edit/discard)  │
│  │  Tool Loop Engine  │  │    └──────────────────────────┘
│  │  while not done:   │  │
│  │  1. LLM thinks     │  │
│  │  2. tool_calls? →  │  │
│  │     execute tool    │  │
│  │  3. append result   │  │
│  │  4. if final answer │  │
│  │     → return        │  │
│  └──────┬─────────────┘  │
│         │                 │
│  ┌──────┼─────────────┐  │
│  │ Tools│              │  │
│  │ ┌────┴──────────┐  │  │
│  │ │ search_rag    │──┼──┼──→ query_service.process_query()
│  │ ├───────────────┤  │  │    (existing RAG pipeline)
│  │ │ search_client │──┼──┼──→ ClientDataStore.search()
│  │ ├───────────────┤  │  │    (JSON → future CRM)
│  │ │ draft_docx    │──┼──┼──→ docx_builder.build_*_docx()
│  │ └───────────────┘  │  │    (existing + new follow-up)
│  └────────────────────┘  │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│              Audit Service (EXTENDED)                     │
│  - create_audit_record() — agent turn start               │
│  - log_tool_call() — each tool invocation (NEW)           │
│  - update_generation() — final answer                     │
│  - update_adviser_action() — approve/edit/discard         │
│  - AuditLog.tool_calls JSON column (NEW)                  │
│  - AuditLog.prompt_version string column (NEW)            │
└──────────────────────────────────────────────────────────┘
```

### Agent Tool Loop — Detailed Flow

```
User: "prepare a meeting brief for alex chan next tuesday"

┌─ Turn 0 ──────────────────────────────────────────────┐
│ LLM (with tools + system prompt):                     │
│   "User wants a meeting brief for Alex Chan.           │
│    I need client info and meeting date.                │
│    Let me search for Alex Chan's profile."             │
│                                                        │
│ tool_calls: [{name: "search_client",                   │
│               arguments: {client_name: "alex chan"}}]   │
└────────────────────────────────────────────────────────┘
         │
         ▼ execute search_client → returns client profile
         │
┌─ Turn 1 ──────────────────────────────────────────────┐
│ LLM (sees client profile in context):                  │
│   "Alex Chan is a student with moderate risk.          │
│    Now I need product info for the brief.              │
│    Let me search for relevant products."               │
│                                                        │
│ tool_calls: [{name: "search_rag",                      │
│               arguments: {query: "investment products  │
│               suitable for student beginner moderate    │
│               risk Hong Kong"}}]                       │
└────────────────────────────────────────────────────────┘
         │
         ▼ execute search_rag → returns RAG results (chunks)
         │
┌─ Turn 2 ──────────────────────────────────────────────┐
│ LLM (sees client + RAG results in context):            │
│   "I have client profile and product info.            │
│    Let me draft the meeting brief."                    │
│                                                        │
│ tool_calls: [{name: "draft_docx",                      │
│               arguments: {doc_type: "brief",            │
│               client_name: "Alex Chan",                 │
│               meeting_date: "2026-05-19",               │
│               content: "..."}}]                         │
└────────────────────────────────────────────────────────┘
         │
         ▼ execute draft_docx → saves .docx, returns path
         │
┌─ Turn 3 ──────────────────────────────────────────────┐
│ LLM (sees file path):                                  │
│   content: "I've prepared the meeting brief for        │
│   Alex Chan. The draft includes [sources].             │
│   Please review and approve."                          │
│                                                        │
│ tool_calls: None → LOOP ENDS                           │
└────────────────────────────────────────────────────────┘
         │
         ▼ Return to Telegram handler
         │
         ▼ Handler sends: text summary + .docx file + inline keyboard
```

### Component Boundaries

| Component | Responsibility | Communicates With | New/Existing |
|-----------|---------------|-------------------|--------------|
| `AgentService` (NEW) | Manages tool loop: sends messages to LLM, inspects tool_calls, executes tools, returns final answer | `AsyncOpenAI` (DeepSeek), `ToolRegistry`, `AuditService` | New |
| `ToolRegistry` (NEW) | Holds tool definitions (JSON schemas) and execution functions. Maps tool names to implementations. | `AgentService`, individual tool implementations | New |
| `search_rag_tool` (NEW) | Wraps `query_service.process_query()` as a tool. Executes full RAG pipeline. Returns text + sources. | `query_service` (existing) | New wrapper |
| `search_client_tool` (NEW) | Searches client data via `ClientDataStore`. Returns structured profile. | `ClientDataStore` (new interface) | New |
| `draft_docx_tool` (NEW) | Calls docx_builder with appropriate template. Returns file path. | `docx_builder` (existing, extended) | New wrapper |
| `ClientDataStore` (NEW abstract class) | Interface for client data lookup. MockJSON implementation for v3.0. | `search_client_tool` | New |
| `docx_builder` (EXISTING, extended) | Two functions: `build_brief_docx()`, `build_followup_docx()`. Saves to `/data/drafts/`. | `draft_docx_tool` | Extended |
| `AuditService` (EXISTING, extended) | New `log_tool_call(audit, tool_name, input, output_summary)` method. | `AgentService`, `AuditLog` model | Extended |
| `AuditLog` model (EXISTING, extended) | New columns: `tool_calls` (JSON), `prompt_version` (String). | `AuditService` | Extended |
| `AgentPromptManager` (NEW) | Loads versioned prompt templates from `backend/prompts/`. Returns prompt string + version tag. | `AgentService` | New |
| Telegram `agent_handler` (NEW) | Replaces existing `handle_query`. Invokes agent loop, sends result + .docx + inline keyboard. | `AgentService`, `python-telegram-bot` | New (replaces handler) |
| Telegram `callback_handler` (NEW) | Handles inline keyboard callbacks: Approve → mark final, Edit → store diff, Discard → log discard. | `AuditService.update_adviser_action()` (existing) | New |
| React Audit Dashboard (EXISTING, extended) | New view: tool-call trace as expandable rows within each audit log entry. | `AuditLog.tool_calls` | Extended |

### Data Flow

```
1. Adviser sends freetext via Telegram
2. Telegram handler → AgentService.run(query, user_id, user_role)
3. AgentService creates audit record (status: received)
4. AgentService loads prompt template (version v3.0.0)
5. AgentService sends [system_prompt + tools] + user message to DeepSeek V4 Pro
6. LLM responds with either:
   a. tool_calls → AgentService executes tools, logs each call, appends results, loops (max 5 turns)
   b. content (final answer) → AgentService returns
7. AgentService updates audit: status → generated, records final answer, prompt_version
8. If tool loop produced draft_docx → Telegram handler sends .docx + inline keyboard
9. If tool loop produced text-only → Telegram handler sends text + sources
10. Adviser interaction with inline keyboard → callback_handler updates audit: status → completed
```

## Patterns to Follow

### Pattern 1: Tool Definition Schema

**What:** Define each tool as a standard OpenAI-compatible function schema with clear descriptions that guide LLM tool selection.

**When:** For every tool the agent can call.

**Example:**
```python
SEARCH_RAG_TOOL = {
    "type": "function",
    "function": {
        "name": "search_rag",
        "description": "Search the internal document library for product information, fund factsheets, compliance guidelines, and market data. Use this for ANY question about investment products, fund performance, fees, rules, or regulations. Returns source-attributed text with citation markers.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query. Be specific: include product names, fund codes, or topic keywords.",
                }
            },
            "required": ["query"],
        },
    },
}

SEARCH_CLIENT_TOOL = {
    "type": "function",
    "function": {
        "name": "search_client",
        "description": "Look up a client's profile including risk tolerance, portfolio holdings, investment objectives, KYC status, and meeting history. Use this when the user mentions a client by name and the query requires personalized information (meeting brief, follow-up note, portfolio review).",
        "parameters": {
            "type": "object",
            "properties": {
                "client_name": {
                    "type": "string",
                    "description": "The client's name (partial match supported). E.g., 'Alex Chan' or 'Wong'.",
                }
            },
            "required": ["client_name"],
        },
    },
}

DRAFT_DOCX_TOOL = {
    "type": "function",
    "function": {
        "name": "draft_docx",
        "description": "Generate a .docx draft document. Use for meeting briefs and follow-up notes. The file is saved to /draft/ and must be reviewed by the adviser before use.",
        "parameters": {
            "type": "object",
            "properties": {
                "doc_type": {
                    "type": "string",
                    "enum": ["meeting_brief", "follow_up_note"],
                    "description": "Type of document to generate.",
                },
                "client_name": {"type": "string", "description": "Client's full name."},
                "title": {"type": "string", "description": "Document title or subject line."},
                "content": {"type": "string", "description": "The full document content in markdown format. Include all sections, findings, and source citations."},
                "meeting_date": {"type": "string", "description": "Meeting date in YYYY-MM-DD format. Optional — use if known."},
            },
            "required": ["doc_type", "client_name", "title", "content"],
        },
    },
}
```

### Pattern 2: Agent Tool Loop (While-Not-Done)

**What:** A simple loop that sends messages to the LLM, inspects the response, executes any requested tool calls, and repeats until the LLM produces a final text answer.

**When:** Every user message that requires agent processing.

**Example:**
```python
MAX_TOOL_TURNS = 5

async def run_agent_turn(
    client: AsyncOpenAI,
    messages: list[dict],
    tools: list[dict],
    tool_executors: dict[str, callable],
    audit: AuditLog,
    db: AsyncSession,
) -> dict:
    """Run the agent tool loop. Returns {answer, sources, tool_calls_made, draft_path?}."""
    tool_calls_made = []
    
    for turn in range(MAX_TOOL_TURNS):
        response = await client.chat.completions.create(
            model="deepseek-v4-pro",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.0,
        )
        
        msg = response.choices[0].message
        messages.append(msg.model_dump())
        
        if msg.tool_calls is None:
            # Final answer — no more tools needed
            return {
                "answer": msg.content,
                "sources": extract_sources(msg.content, messages),
                "tool_calls_made": tool_calls_made,
            }
        
        # Execute each tool call
        for tool_call in msg.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            
            result = await tool_executors[tool_name](**tool_args)
            
            # Log the tool call
            await audit_service.log_tool_call(
                db, audit, turn + 1, tool_name, tool_args, result
            )
            tool_calls_made.append({
                "turn": turn + 1,
                "tool": tool_name,
                "input": tool_args,
                "output_summary": str(result)[:500],
            })
            
            # Append tool result to conversation
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result) if isinstance(result, dict) else str(result),
            })
    
    # Max turns exceeded — ask LLM to produce answer with whatever context it has
    messages.append({
        "role": "user",
        "content": "Please provide the best answer you can with the information gathered so far. Do not call any more tools."
    })
    response = await client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=messages,
        temperature=0.0,
    )
    return {
        "answer": response.choices[0].message.content,
        "sources": [],
        "tool_calls_made": tool_calls_made,
        "warning": "Max tool turns reached",
    }
```

### Pattern 3: ClientDataStore Abstraction

**What:** Abstract interface for client data retrieval, with mock JSON implementation for v3.0.

**When:** Any time the agent needs client profile data. Ensures tool code is CRM-agnostic.

**Example:**
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ClientProfile:
    client_id: str
    name: str
    risk_tolerance: str
    portfolio: list[dict]
    goals: list[dict]
    kyc_status: str
    meeting_history: list[dict]
    raw: dict  # Full data for LLM context

class ClientDataStore(ABC):
    @abstractmethod
    async def search(self, advisor_id: str, client_name: str) -> list[ClientProfile]:
        """Search clients by advisor and name (partial match)."""
        ...

class MockJSONClientDataStore(ClientDataStore):
    def __init__(self, data_dir: str = "./demo_material"):
        self.data_dir = Path(data_dir)
        self._profiles: dict[str, ClientProfile] = {}
        self._load_profiles()
    
    def _load_profiles(self):
        # Load .json and .md files, parse into ClientProfile objects
        ...
    
    async def search(self, advisor_id: str, client_name: str) -> list[ClientProfile]:
        name_lower = client_name.lower()
        return [
            p for p in self._profiles.values()
            if name_lower in p.name.lower()
        ]
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Agent Framework Overuse

**What:** Importing LangGraph, LangChain agents, or similar frameworks to manage a 3-tool agent.

**Why bad:** v2.0 already proved this approach is "messy/unsatisfying" for this use case. These frameworks add abstraction layers that obscure the simple LLM→tool→LLM loop. Debugging becomes harder, dependencies multiply, and the framework's opinionated structure fights against simple prompt-driven orchestration.

**Instead:** Use the pattern above — a while-loop with the standard OpenAI SDK. 30 lines of Python vs 200+ lines of framework configuration. Easier to debug (print messages array at each turn), easier to audit (explicit tool call logging), easier to customize agent behavior (edit the prompt, not framework code).

### Anti-Pattern 2: Mode Classification as Separate Step

**What:** Running a classifier before the agent to determine "this is a QA query" vs "this is a brief request," then routing to different handling paths.

**Why bad:** This was the v2.0 skill-classification approach that failed. It adds latency (extra LLM call), creates misclassification edge cases, and fragments the handling logic. The LLM's tool-calling capability already performs intent detection as a natural byproduct of selecting tools.

**Instead:** The agent's system prompt describes all capabilities. The LLM decides which tools to use based on the user's query. If it picks `draft_docx`, it's a brief/follow-up intent. If it picks `search_rag` only, it's QA. If it picks neither, it's chat. No separate classifier needed.

### Anti-Pattern 3: Blocking Audit Writes

**What:** Writing tool-call audit records synchronously within the agent loop, blocking the next LLM call until the DB write completes.

**Why bad:** Adds latency to every tool turn. With 3-4 tool calls per agent turn, this could add 200-400ms of unnecessary wait time.

**Instead:** Use `asyncio.create_task()` or FastAPI `BackgroundTasks` for audit writes. The agent loop continues immediately after dispatching the audit write. In the unlikely event of an audit write failure, the tool call is still logged to structlog (application logs), providing a fallback trace.

### Anti-Pattern 4: Hardcoded Prompt in Agent Code

**What:** Embedding the agent system prompt as a Python string constant in `agent_service.py`.

**Why bad:** Prompt iteration is the primary development workflow for prompt-driven agents. Hardcoding requires code deploys for every prompt tweak. Makes A/B testing impossible.

**Instead:** Load from versioned files in `backend/prompts/`. The file header contains a version tag. At startup, `AgentPromptManager` loads the latest version. Audit logs record which version was used. Prompt updates become file changes tracked in git, not code changes.

## Scalability Considerations

| Concern | At 5 advisers (v3.0) | At 50 advisers | At 500 advisers |
|---------|----------------------|----------------|-----------------|
| Agent LLM latency | ~3-8s per turn (3-4 tool calls). Acceptable. | Same. DeepSeek API scales. | Consider Flash for simple QA (cost optimization). |
| Tool-call audit writes | SQLite + BackgroundTasks. Fine. | Postgres with connection pooling. | Separate audit DB or write-behind queue. |
| Client data store | Mock JSON. Instant. | Switch to SQLite `clients` table. | Postgres `clients` table with full-text search. |
| .docx storage | Local `/data/drafts/`. Fine. | Same. Add cleanup cron for >90-day drafts. | Object storage (S3/MinIO) with retention policies. |
| Prompt versioning | Git-tracked files. Fine. | Same. | Admin UI for prompt management + A/B testing. |

## Sources

- DeepSeek API — Function Calling flow and tool call response format: https://api-docs.deepseek.com/guides/function_calling (HIGH confidence)
- DeepSeek API — Tool Calls with thinking mode (multi-turn example): https://api-docs.deepseek.com/guides/thinking_mode (HIGH confidence)
- DeepSeek API — Chat Completion response schema (tool_calls field): https://api-docs.deepseek.com/api/create-chat-completion (HIGH confidence)
- CopInvest codebase — existing `query_service.py`, `docx_builder.py`, `audit_service.py`, `AuditLog` model (HIGH confidence — primary sources)
- CopInvest PROJECT.md — v2.0 failures, v3.0 approach decision: "replaced by prompt-driven orchestration in v3.0" (HIGH confidence)
