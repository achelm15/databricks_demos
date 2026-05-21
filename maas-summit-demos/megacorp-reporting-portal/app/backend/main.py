"""
Multi-Tenant Reporting Portal - FastAPI Backend
Connects to Lakebase for app state + synced campaign data.
"""

import os
import uuid
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# --- Configuration ---
PROJECT_ID = os.getenv("LAKEBASE_PROJECT_ID", "adtech-portal")
BRANCH = os.getenv("LAKEBASE_BRANCH", "production")
DATABASE = os.getenv("LAKEBASE_DATABASE", "databricks_postgres")
GENIE_SPACE_ID = os.getenv("GENIE_SPACE_ID", "")

# Load SPA HTML - try multiple paths for container compatibility
SPA_HTML = "<h1>Portal loading error - index.html not found</h1>"
_candidates = [
    Path(__file__).parent.parent / "static" / "index.html",  # relative to main.py
    Path.cwd() / "static" / "index.html",                    # relative to cwd
    Path("/app/static/index.html"),                           # absolute container path
]
for p in _candidates:
    if p.exists():
        SPA_HTML = p.read_text()
        print(f"Loaded SPA from: {p}")
        break
else:
    print(f"WARNING: index.html not found. Tried: {[str(p) for p in _candidates]}")
    print(f"CWD: {Path.cwd()}")
    print(f"__file__: {__file__}")
    # List what we can find
    try:
        for item in Path.cwd().rglob("*.html"):
            print(f"  Found HTML: {item}")
    except Exception:
        pass


# --- Lakebase Connection ---
class LakebasePool:
    def __init__(self):
        self._host = None
        self._token = None
        self._token_expires = None
        self._username = None
        self._initialized = False
        self.w = None

    def _init_connection(self):
        if self._initialized:
            return
        try:
            from databricks.sdk import WorkspaceClient
            self.w = WorkspaceClient()
        except Exception as e:
            print(f"SDK init failed: {e}")
            self.w = None
        self._initialized = True

    def _refresh_if_needed(self):
        self._init_connection()
        if not self.w:
            return
        now = datetime.utcnow()
        if self._token and self._token_expires and now < self._token_expires:
            return
        ep_name = f"projects/{PROJECT_ID}/branches/{BRANCH}/endpoints/primary"
        if not self._host:
            endpoint = self.w.postgres.get_endpoint(name=ep_name)
            self._host = endpoint.status.hosts.host
            self._username = self.w.current_user.me().user_name
        cred = self.w.postgres.generate_database_credential(endpoint=ep_name)
        self._token = cred.token
        self._token_expires = now + timedelta(minutes=50)

    def get_connection(self):
        import psycopg
        from psycopg.rows import dict_row
        self._refresh_if_needed()
        if not self._host:
            raise HTTPException(503, "Lakebase not configured or not reachable")
        return psycopg.connect(
            host=self._host, dbname=DATABASE, user=self._username,
            password=self._token, sslmode="require", row_factory=dict_row
        )


pool = LakebasePool()


# --- Models ---
class LoginRequest(BaseModel):
    email: str
    tenant_id: str

class SaveReportRequest(BaseModel):
    title: str
    description: Optional[str] = None
    query_text: str

class GenieQuestion(BaseModel):
    question: str


# --- Auth ---
async def get_current_session(x_session_id: str = Header(None)):
    if not x_session_id:
        raise HTTPException(401, "Missing session header")
    try:
        with pool.get_connection() as conn:
            result = conn.execute(
                """SELECT s.session_id, s.tenant_id, s.user_id, t.distributor_name, u.role
                   FROM portal.sessions s
                   JOIN portal.tenants t ON s.tenant_id = t.tenant_id
                   JOIN portal.users u ON s.user_id = u.user_id
                   WHERE s.session_id = %s AND s.expires_at > NOW()""",
                (x_session_id,)
            ).fetchone()
        if not result:
            raise HTTPException(401, "Invalid or expired session")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Database error: {e}")


# --- App ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Portal starting - project: {PROJECT_ID}")
    print(f"SPA loaded: {len(SPA_HTML)} chars")
    yield

app = FastAPI(title="Multi-Tenant Reporting Portal", lifespan=lifespan)


# --- Auth Endpoints ---
@app.post("/api/auth/login")
async def login(req: LoginRequest):
    try:
        with pool.get_connection() as conn:
            user = conn.execute(
                "SELECT user_id, tenant_id, display_name, role FROM portal.users WHERE email = %s AND tenant_id = %s",
                (req.email, req.tenant_id)
            ).fetchone()
            if not user:
                raise HTTPException(401, "Invalid credentials")
            session_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO portal.sessions (session_id, user_id, tenant_id) VALUES (%s, %s, %s)",
                (session_id, user["user_id"], user["tenant_id"])
            )
            conn.commit()
        return {"session_id": session_id, "user": user, "tenant_id": req.tenant_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Database error: {e}")

@app.get("/api/auth/me")
async def get_me(session=Depends(get_current_session)):
    return session


# --- Metrics ---
@app.get("/api/metrics/overview")
async def get_overview(session=Depends(get_current_session)):
    publisher = session["distributor_name"]
    with pool.get_connection() as conn:
        metrics = conn.execute("""
            SELECT campaign, SUM(reach_ind) as total_reach,
                   SUM(matched_imps) as total_impressions,
                   SUM(raw_imps) as total_raw_impressions,
                   COUNT(DISTINCT device_type) as device_types,
                   COUNT(DISTINCT marketing_region) as regions
            FROM reach_cube WHERE publisher = %s
            GROUP BY campaign ORDER BY total_reach DESC
        """, (publisher,)).fetchall()
    return {"publisher": publisher, "campaigns": metrics}

@app.get("/api/metrics/reach-by-device")
async def get_reach_by_device(session=Depends(get_current_session)):
    publisher = session["distributor_name"]
    with pool.get_connection() as conn:
        data = conn.execute("""
            SELECT device_type, SUM(reach_ind) as reach, SUM(matched_imps) as impressions
            FROM reach_cube WHERE publisher = %s GROUP BY device_type ORDER BY reach DESC
        """, (publisher,)).fetchall()
    return {"data": data}

@app.get("/api/metrics/reach-by-region")
async def get_reach_by_region(campaign: Optional[str] = None, session=Depends(get_current_session)):
    publisher = session["distributor_name"]
    with pool.get_connection() as conn:
        q = "SELECT marketing_region, SUM(reach_ind) as reach, SUM(matched_imps) as impressions FROM reach_cube WHERE publisher = %s"
        params = [publisher]
        if campaign:
            q += " AND campaign = %s"
            params.append(campaign)
        q += " GROUP BY marketing_region ORDER BY reach DESC LIMIT 20"
        data = conn.execute(q, params).fetchall()
    return {"data": data}

@app.get("/api/metrics/frequency")
async def get_frequency(session=Depends(get_current_session)):
    with pool.get_connection() as conn:
        data = conn.execute("SELECT campaign_name, frequency_cap, in_target_freq, pct_pop FROM frequency_caps ORDER BY campaign_name").fetchall()
    return {"data": data}


# --- Reports ---
@app.get("/api/reports")
async def list_reports(session=Depends(get_current_session)):
    with pool.get_connection() as conn:
        reports = conn.execute(
            "SELECT report_id, title, description, query_text, created_at FROM portal.saved_reports WHERE tenant_id = %s ORDER BY created_at DESC",
            (session["tenant_id"],)
        ).fetchall()
    return {"reports": reports}

@app.post("/api/reports")
async def save_report(req: SaveReportRequest, session=Depends(get_current_session)):
    report_id = str(uuid.uuid4())
    with pool.get_connection() as conn:
        conn.execute(
            "INSERT INTO portal.saved_reports (report_id, tenant_id, user_id, title, description, query_text) VALUES (%s, %s, %s, %s, %s, %s)",
            (report_id, session["tenant_id"], session["user_id"], req.title, req.description, req.query_text)
        )
        conn.commit()
    return {"report_id": report_id, "status": "saved"}

@app.get("/api/reports/search")
async def search_reports(q: str, session=Depends(get_current_session)):
    with pool.get_connection() as conn:
        reports = conn.execute(
            "SELECT report_id, title, description, query_text, created_at FROM portal.saved_reports WHERE tenant_id = %s AND (title ILIKE %s OR query_text ILIKE %s) ORDER BY created_at DESC LIMIT 10",
            (session["tenant_id"], f"%{q}%", f"%{q}%")
        ).fetchall()
    return {"reports": reports}


# --- Genie ---
@app.post("/api/genie/ask")
async def ask_genie(req: GenieQuestion, session=Depends(get_current_session)):
    if not GENIE_SPACE_ID:
        return {"status": "not_configured", "message": "Set GENIE_SPACE_ID env var to enable NL queries"}
    publisher = session["distributor_name"]
    scoped = f"For publisher '{publisher}': {req.question}"
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        conv = w.genie.start_conversation(space_id=GENIE_SPACE_ID, content=scoped)
        return {"conversation_id": conv.conversation_id, "message_id": conv.message_id, "status": "processing", "scoped_question": scoped}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/genie/result/{conversation_id}/{message_id}")
async def get_genie_result(conversation_id: str, message_id: str, session=Depends(get_current_session)):
    if not GENIE_SPACE_ID:
        return {"status": "not_configured"}
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        msg = w.genie.get_message(space_id=GENIE_SPACE_ID, conversation_id=conversation_id, message_id=message_id)
        # Check if the message is complete
        if msg.status and msg.status.value in ("EXECUTING_QUERY", "FETCHING_METADATA", "ASKING_AI"):
            return {"status": "processing"}
        # Extract the result
        result = {"status": "complete"}
        if msg.attachments:
            for att in msg.attachments:
                if att.text:
                    result["answer"] = att.text.content if hasattr(att.text, 'content') else str(att.text)
                if att.query:
                    result["sql"] = att.query.query if hasattr(att.query, 'query') else str(att.query)
                    result["description"] = att.query.description if hasattr(att.query, 'description') else ""
        if not result.get("answer") and not result.get("sql"):
            # Try to extract from different response shapes
            if hasattr(msg, 'content') and msg.content:
                result["answer"] = msg.content
            else:
                result["answer"] = "Query completed. Check the Genie space for full results."
        return result
    except Exception as e:
        err_str = str(e)
        if "COMPLETED" in err_str.upper() or "NOT_FOUND" in err_str.upper():
            return {"status": "error", "message": "Result no longer available"}
        # If still processing, return processing status
        if "IN_PROGRESS" in err_str.upper() or "EXECUTING" in err_str.upper():
            return {"status": "processing"}
        return {"status": "error", "message": err_str}


# --- Sandbox (Branching) ---
@app.post("/api/sandbox/create")
async def create_sandbox(session=Depends(get_current_session)):
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.postgres import Branch, BranchSpec, Duration
    tenant_id = session["tenant_id"]
    branch_id = f"sandbox-{tenant_id}-{uuid.uuid4().hex[:8]}"
    try:
        w = WorkspaceClient()
        branch = w.postgres.create_branch(
            parent=f"projects/{PROJECT_ID}",
            branch=Branch(spec=BranchSpec(
                source_branch=f"projects/{PROJECT_ID}/branches/production",
                ttl=Duration(seconds=3600)
            )),
            branch_id=branch_id
        ).wait()
        return {"branch_id": branch_id, "branch_name": branch.name, "expires_in": "1 hour", "message": "Sandbox created!"}
    except Exception as e:
        raise HTTPException(500, f"Failed to create sandbox: {e}")

@app.delete("/api/sandbox/{branch_id}")
async def delete_sandbox(branch_id: str, session=Depends(get_current_session)):
    from databricks.sdk import WorkspaceClient
    try:
        w = WorkspaceClient()
        w.postgres.delete_branch(name=f"projects/{PROJECT_ID}/branches/{branch_id}").wait()
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(500, f"Failed: {e}")


# --- Features ---
@app.get("/api/features")
async def get_features(session=Depends(get_current_session)):
    with pool.get_connection() as conn:
        flags = conn.execute("SELECT flag_name, enabled FROM portal.feature_flags WHERE tenant_id = %s", (session["tenant_id"],)).fetchall()
    return {"features": {f["flag_name"]: f["enabled"] for f in flags}}


# --- Health ---
@app.get("/api/health")
async def health():
    return {"status": "healthy", "project": PROJECT_ID, "spa_loaded": len(SPA_HTML) > 100}


# --- Serve SPA ---
@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content=SPA_HTML)

@app.get("/{full_path:path}")
async def catch_all(request: Request, full_path: str = ""):
    # Don't intercept API routes or internal auth routes
    if full_path.startswith("api/") or full_path.startswith(".auth"):
        raise HTTPException(404)
    return HTMLResponse(content=SPA_HTML)
