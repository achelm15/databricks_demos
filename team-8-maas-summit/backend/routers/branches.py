"""Lakebase Autoscaling branch lifecycle — the "Onboard New Advertiser" flow.

A Lakebase branch is a copy-on-write fork of the project's production data. We
use it for two flows in the demo:

  1. **Onboarding**: a new advertiser is spun up as a branch, gets a sandbox to
     model campaign changes before they push to the main instance.
  2. **What-if sandbox**: an existing advertiser clicks "Sandbox this advertiser"
     to model a campaign change against a forked copy.

Autoscale REST API:
  POST  /api/2.0/postgres/projects/{project}/branches?branch_id={id}
  GET   /api/2.0/postgres/projects/{project}/branches
  DELETE /api/2.0/postgres/projects/{project}/branches/{id}
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from databricks.sdk import WorkspaceClient
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..auth import is_agency_admin
from ..config import get_settings

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["branches"])

# Auto-delete sandbox branches after 7 days so demo doesn't accumulate state.
SANDBOX_TTL_SECONDS = 7 * 24 * 60 * 60

# Autoscale branch_id rules: 1-63 chars, lowercase letters/digits/hyphens, no leading/trailing hyphen.
_BRANCH_ID_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")


class CreateBranchRequest(BaseModel):
    name: str                       # branch id e.g. "maas-team8-allbirds-sandbox-3707"
    advertiser_id: Optional[str] = None
    purpose: str = "sandbox"        # "sandbox" | "onboarding"


def _project_path(project: str) -> str:
    return f"projects/{project}"


def _branch_path(project: str, branch_id: str) -> str:
    return f"projects/{project}/branches/{branch_id}"


@router.get("/branches")
async def list_branches(request: Request):
    settings = get_settings()
    w = WorkspaceClient()
    resp = w.api_client.do(
        "GET", f"/api/2.0/postgres/{_project_path(settings.lakebase_project)}/branches"
    )
    out = []
    for br in resp.get("branches", []):
        status = br.get("status") or {}
        branch_id = status.get("branch_id") or br.get("name", "").split("/")[-1]
        # Hide the default production branch from the "branches list" UI —
        # only show user-spawned forks (sandboxes, onboardings).
        if status.get("default"):
            continue
        out.append({
            "name": branch_id,
            "full_name": br.get("name"),
            "state": _normalize_state(status.get("current_state")),
            "parent": status.get("source_branch") or br.get("parent"),
            "branch_time": status.get("source_branch_time"),
            "created": br.get("create_time"),
            "expire_time": status.get("expire_time"),
            "logical_size_bytes": status.get("logical_size_bytes"),
            # Capacity isn't a branch-level property in autoscale (each endpoint
            # has min/max CU). Show "autoscale" so the frontend column stays sane.
            "capacity": "autoscale",
        })
    return out


@router.post("/branches")
async def create_branch(req: CreateBranchRequest, request: Request):
    if not await is_agency_admin(request):
        raise HTTPException(403, "only agency admins can create branches")

    if not _BRANCH_ID_RE.match(req.name):
        raise HTTPException(
            400,
            "branch name must be 1-63 chars, lowercase letters/digits/hyphens, "
            "and cannot start or end with a hyphen",
        )

    settings = get_settings()
    w = WorkspaceClient()

    body = {
        "spec": {
            "source_branch": _branch_path(settings.lakebase_project, settings.lakebase_branch),
            "ttl": f"{SANDBOX_TTL_SECONDS}s",
        }
    }
    try:
        resp = w.api_client.do(
            "POST",
            f"/api/2.0/postgres/{_project_path(settings.lakebase_project)}/branches",
            query={"branch_id": req.name},
            body=body,
        )
    except Exception as e:
        log.exception("branch creation failed")
        raise HTTPException(500, f"branch create failed: {e}")

    # Create returns a long-running operation; pull the embedded resource if present.
    branch = resp.get("response") or resp
    status = (branch.get("status") or {}) if isinstance(branch, dict) else {}
    return {
        "name": req.name,
        "full_name": branch.get("name") if isinstance(branch, dict) else None,
        "state": _normalize_state(status.get("current_state")) or "CREATING",
        "uid": branch.get("uid") if isinstance(branch, dict) else None,
        "parent": _branch_path(settings.lakebase_project, settings.lakebase_branch),
        "purpose": req.purpose,
        "advertiser_id": req.advertiser_id,
    }


@router.delete("/branches/{name}")
async def delete_branch(name: str, request: Request):
    if not await is_agency_admin(request):
        raise HTTPException(403, "only agency admins can delete branches")
    settings = get_settings()
    if name == settings.lakebase_branch:
        raise HTTPException(400, "refusing to delete the production branch")

    w = WorkspaceClient()
    try:
        w.api_client.do(
            "DELETE",
            f"/api/2.0/postgres/{_branch_path(settings.lakebase_project, name)}",
        )
    except Exception as e:
        raise HTTPException(500, f"delete failed: {e}")
    return {"deleted": name}


def _normalize_state(state: Optional[str]) -> Optional[str]:
    """Map autoscale states onto what the frontend pill expects.

    Frontend treats "AVAILABLE" as the happy state; everything else renders
    as a warning pill.
    """
    if state == "READY":
        return "AVAILABLE"
    return state
