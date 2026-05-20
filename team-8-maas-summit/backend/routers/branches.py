"""Lakebase branch lifecycle — the "Onboard New Advertiser" flow.

A Lakebase branch is a copy-on-write fork of a parent instance. We use it for two
flows in the demo:

  1. **Onboarding**: a new advertiser is spun up as a branch, gets a sandbox to
     model campaign changes before they push to the main instance.
  2. **What-if sandbox**: an existing advertiser clicks "Sandbox this advertiser"
     to model a campaign change against a forked copy.

The actual Databricks REST endpoint:
  POST /api/2.0/database/instances
  {
    "name": "<branch-name>",
    "capacity": "CU_1",
    "parent_instance_ref": {
      "name": "<parent-instance>",
      "branch_time": "<RFC3339 timestamp>"
    }
  }
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from databricks.sdk import WorkspaceClient
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..auth import is_agency_admin
from ..config import get_settings

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["branches"])


class CreateBranchRequest(BaseModel):
    name: str                       # branch name e.g. "maas-team8-allbirds-sandbox"
    advertiser_id: Optional[str] = None
    purpose: str = "sandbox"        # "sandbox" | "onboarding"


@router.get("/branches")
async def list_branches(request: Request):
    settings = get_settings()
    w = WorkspaceClient()
    resp = w.api_client.do("GET", "/api/2.0/database/instances")
    branches = []
    for inst in resp.get("database_instances", []):
        parent = inst.get("parent_instance_ref")
        if parent and parent.get("name") == settings.lakebase_instance:
            branches.append({
                "name": inst["name"],
                "state": inst.get("state"),
                "parent": parent.get("name"),
                "branch_time": parent.get("branch_time"),
                "created": inst.get("creation_time"),
                "capacity": inst.get("capacity"),
            })
    return branches


@router.post("/branches")
async def create_branch(req: CreateBranchRequest, request: Request):
    if not await is_agency_admin(request):
        raise HTTPException(403, "only agency admins can create branches")

    settings = get_settings()
    w = WorkspaceClient()

    # Branch from "now" — Lakebase rounds to the nearest recoverable point.
    branch_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    body = {
        "name": req.name,
        "capacity": "CU_1",
        "parent_instance_ref": {
            "name": settings.lakebase_instance,
            "branch_time": branch_time,
        },
    }
    try:
        resp = w.api_client.do("POST", "/api/2.0/database/instances", body=body)
    except Exception as e:
        log.exception("branch creation failed")
        raise HTTPException(500, f"branch create failed: {e}")

    return {
        "name": resp["name"],
        "state": resp.get("state"),
        "uid": resp.get("uid"),
        "dns": resp.get("read_write_dns"),
        "branch_time": branch_time,
        "parent": settings.lakebase_instance,
        "purpose": req.purpose,
        "advertiser_id": req.advertiser_id,
    }


@router.delete("/branches/{name}")
async def delete_branch(name: str, request: Request):
    if not await is_agency_admin(request):
        raise HTTPException(403, "only agency admins can delete branches")
    if name == get_settings().lakebase_instance:
        raise HTTPException(400, "refusing to delete the parent instance")
    w = WorkspaceClient()
    try:
        w.api_client.do("DELETE", f"/api/2.0/database/instances/{name}")
    except Exception as e:
        raise HTTPException(500, f"delete failed: {e}")
    return {"deleted": name}
