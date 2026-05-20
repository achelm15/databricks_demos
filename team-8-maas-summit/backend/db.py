"""Lakebase connection pool with OAuth-token refresh.

Inside a Databricks App, the user's OAuth token arrives as `x-forwarded-access-token`
on every request. We use *that* token (not the service principal token) because the
SP token lacks Lakebase security labels.

The middleware in `main.py` calls `pool.update_token(token)` on every request, which
applies it to the asyncpg pool's connect callback before any query runs.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

import asyncpg
from databricks.sdk import WorkspaceClient

log = logging.getLogger(__name__)


class LakebasePool:
    """Asyncpg pool that uses a rotating OAuth token as the Postgres password."""

    def __init__(self, instance_name: str, database: str):
        self.instance_name = instance_name
        self.database = database
        self._token: Optional[str] = None
        self._user_email: Optional[str] = None
        self._pool: Optional[asyncpg.Pool] = None
        self._host: Optional[str] = None
        self._lock = asyncio.Lock()

    @property
    def available(self) -> bool:
        return self._pool is not None and not self._pool.is_closing()

    def update_token(self, token: str) -> None:
        """Latest token wins. Tokens expire ~1h, so refresh on every request."""
        if token:
            self._token = token

    def capture_user_token(self, email: str, token: str) -> None:
        self._user_email = email
        self._token = token

    async def _resolve_host(self) -> str:
        if self._host:
            return self._host
        w = WorkspaceClient()
        inst = w.api_client.do("GET", f"/api/2.0/database/instances/{self.instance_name}")
        self._host = inst["read_write_dns"]
        return self._host

    async def init(self) -> None:
        """Create the pool. Token must already be set via update_token()."""
        async with self._lock:
            if self.available:
                return
            if not self._token or not self._user_email:
                raise RuntimeError("token/email must be set before init()")
            host = await self._resolve_host()

            # asyncpg dynamic password — refresh on each new connection
            async def _password_provider():
                return self._token

            self._pool = await asyncpg.create_pool(
                host=host,
                port=5432,
                user=self._user_email,
                password=_password_provider,
                database=self.database,
                ssl="require",
                min_size=1,
                max_size=10,
                statement_cache_size=0,  # safer with rotating creds
                server_settings={"application_name": "maas-summit-team8"},
            )
            log.info("Lakebase pool ready for %s@%s/%s", self._user_email, host, self.database)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def fetch(self, query: str, *args):
        assert self._pool, "pool not initialized"
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        assert self._pool, "pool not initialized"
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def execute(self, query: str, *args):
        assert self._pool, "pool not initialized"
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args)
