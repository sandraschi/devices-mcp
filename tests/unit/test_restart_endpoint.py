"""POST /api/v1/restart must really exit the process (NSSM respawns it), not just claim to."""

import asyncio
import os

import httpx
from backend.v1.endpoints import system as v1_system
from fastapi import FastAPI


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(v1_system.router, prefix="/api/v1")
    return app


async def test_restart_exits_the_process_shortly_after_responding(monkeypatch):
    exits: list[int] = []
    monkeypatch.setattr(os, "_exit", lambda code: exits.append(code))

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_app()), base_url="http://test") as client:
        r = await client.post("/api/v1/restart")
        assert r.status_code == 200
        assert r.json()["status"] == "shutting_down"
        assert exits == [], "must respond before exiting so the reply flushes"
        await asyncio.sleep(0.8)
    assert exits == [0]


async def test_restart_needs_no_api_key_even_when_one_is_configured(monkeypatch):
    monkeypatch.setattr(os, "_exit", lambda code: None)
    app = _app()
    app.dependency_overrides[v1_system.ServerConfig] = lambda: type("C", (), {"api_key": "secret"})()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post("/api/v1/restart")).status_code == 200
        await asyncio.sleep(0.8)
