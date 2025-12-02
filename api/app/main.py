# ===========================
# StegVerse SCW API (v4 clean)
# Combined master main.py
# Includes tickets router hook
# ===========================

from __future__ import annotations
import os
import json
import time
import hashlib
import hmac
from typing import Any, Dict, Optional, List

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --------------------------------------------------------------------------------------
# Storage Layer (Redis or Mem)
# --------------------------------------------------------------------------------------

USE_MEMORY_ONLY = False

_mem_kv: Dict[str, str] = {}
_mem_list: List[str] = []

def _mem_get(key: str) -> Optional[str]:
    return _mem_kv.get(key)

def _mem_set(key: str, val: str):
    _mem_kv[key] = val

def _mem_hset(name: str, key: str, val: str):
    _mem_kv[f"{name}:{key}"] = val

def _mem_hgetall(name: str) -> Dict[str, str]:
    prefix = f"{name}:"
    return {k[len(prefix):]: v for k, v in _mem_kv.items() if k.startswith(prefix)}

def _mem_lpush(key: str, val: str):
    _mem_list.insert(0, val)

# Redis init if available
try:
    import redis  # type: ignore
    REDIS_URL = os.getenv("REDIS_URL")
    if REDIS_URL:
        r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    else:
        r = None
except Exception:
    r = None

def kv_get(key: str) -> Optional[str]:
    if USE_MEMORY_ONLY or not r:
        return _mem_get(key)
    try:
        return r.get(key)
    except Exception:
        return _mem_get(key)

def kv_set(key: str, val: str):
    if USE_MEMORY_ONLY or not r:
        return _mem_set(key, val)
    try:
        r.set(key, val)
    except Exception:
        _mem_set(key, val)

def kv_hset(name: str, key: str, val: str):
    if USE_MEMORY_ONLY or not r:
        return _mem_hset(name, key, val)
    try:
        r.hset(name, key, val)
    except Exception:
        _mem_hset(name, key, val)

def kv_hgetall(name: str) -> Dict[str, str]:
    if USE_MEMORY_ONLY or not r:
        return _mem_hgetall(name)
    try:
        raw = r.hgetall(name)
        if isinstance(raw, dict):
            return {k: v for k, v in raw.items()}
        return {}
    except Exception:
        return _mem_hgetall(name)

# --------------------------------------------------------------------------------------
# FastAPI app init
# --------------------------------------------------------------------------------------

app = FastAPI(
    title="StegVerse SCW API",
    version="4.0.0",
    description="StegVerse Sovereign Control Workspace API"
)

# Broad permissive CORS for now
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------------------
# Shared Models
# --------------------------------------------------------------------------------------

class ConfigSetItem(BaseModel):
    key: str
    value: Any

# --------------------------------------------------------------------------------------
# Ops — Bootstrap, Status, Snapshot
# --------------------------------------------------------------------------------------

@app.get("/v1/ops/snapshot")
async def snapshot() -> Dict[str, Any]:
    return {
        "kv": kv_hgetall("config"),
        "time": time.time(),
    }

@app.post("/v1/ops/config/set")
async def config_set(item: ConfigSetItem):
    kv_hset("config", item.key, json.dumps(item.value))
    return {"ok": True, "key": item.key}

@app.get("/v1/ops/config/list")
async def config_list():
    cfg = kv_hgetall("config")
    return {k: json.loads(v) for k, v in cfg.items()}

@app.get("/v1/ops/config/get/{name}")
async def config_get(name: str):
    raw = kv_hgetall("config").get(name)
    if raw is None:
        raise HTTPException(404, f"{name} not found")
    return json.loads(raw)

@app.get("/v1/ops/config/bootstrap/status")
async def bootstrap_status():
    t = kv_get("ADMIN_TOKEN")
    return {"initialized": bool(t)}

class BootstrapBody(BaseModel):
    admin_token: str

@app.post("/v1/ops/config/bootstrap")
async def bootstrap(body: BootstrapBody):
    existing = kv_get("ADMIN_TOKEN")
    if existing:
        return {"ok": False, "detail": "Already initialized"}

    kv_set("ADMIN_TOKEN", body.admin_token)
    return {"ok": True}

# --------------------------------------------------------------------------------------
# Redeploy / Deploy Hooks
# --------------------------------------------------------------------------------------

async def _trigger_webhook(url: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(url)
            return {"status_code": resp.status_code}
        except Exception as exc:
            return {"error": str(exc)}

@app.post("/v1/ops/redeploy/ui")
async def redeploy_ui():
    url = kv_get("HOOK_NETLIFY")
    if not url:
        raise HTTPException(400, "Missing HOOK_NETLIFY")
    return await _trigger_webhook(url)

@app.post("/v1/ops/redeploy/api")
async def redeploy_api():
    url = kv_get("HOOK_RENDER_API")
    if not url:
        raise HTTPException(400, "Missing HOOK_RENDER_API")
    return await _trigger_webhook(url)

@app.post("/v1/ops/redeploy/worker")
async def redeploy_worker():
    url = kv_get("HOOK_RENDER_WORKER")
    if not url:
        raise HTTPException(400, "Missing HOOK_RENDER_WORKER")
    return await _trigger_webhook(url)

@app.post("/v1/ops/redeploy/netlify")
async def redeploy_netlify():
    url = kv_get("HOOK_NETLIFY")
    if not url:
        raise HTTPException(400, "Missing HOOK_NETLIFY")
    return await _trigger_webhook(url)

@app.post("/v1/ops/redeploy/vercel")
async def redeploy_vercel():
    url = kv_get("HOOK_VERCEL")
    if not url:
        raise HTTPException(400, "Missing HOOK_VERCEL")
    return await _trigger_webhook(url)

# --------------------------------------------------------------------------------------
# Admin — rotate token / recover / reset all
# --------------------------------------------------------------------------------------

class RotateBody(BaseModel):
    new_token: str

@app.post("/v1/ops/admin/rotate_token")
async def admin_rotate(body: RotateBody):
    kv_set("ADMIN_TOKEN", body.new_token)
    return {"ok": True}

@app.post("/v1/ops/admin/recover")
async def admin_recover():
    t = kv_get("ADMIN_TOKEN")
    return {"admin_token": t}

@app.post("/v1/ops/admin/reset_all")
async def admin_reset_all():
    for k in list(_mem_kv.keys()):
        del _mem_kv[k]
    if r:
        try:
            r.flushdb()
        except Exception:
            pass
    return {"ok": True}

# --------------------------------------------------------------------------------------
# Friendly + WhoAmI
# --------------------------------------------------------------------------------------

@app.get("/friendly")
async def friendly():
    return {"hi": "SCW is online"}

@app.get("/whoami")
async def whoami():
    return {"service": "scw-api", "env": os.getenv("RENDER_SERVICE_ID")}

# --------------------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------------------

@app.get("/healthz")
async def healthz():
    return {"ok": True}

# --------------------------------------------------------------------------------------
# INCLUDE ALL ROUTERS (this is where *tickets* router goes)
# --------------------------------------------------------------------------------------

from .routes_tickets import router as tickets_router
app.include_router(tickets_router)

# If you have other routers such as:
# from .routes_admin import router as admin_router
# app.include_router(admin_router)
# etc.
# They stay as-is.

# --------------------------------------------------------------------------------------
# Startup
# --------------------------------------------------------------------------------------

@app.on_event("startup")
async def on_startup():
    kv_set("SCW_API_LAST_BOOT", str(time.time()))

# --------------------------------------------------------------------------------------
# END
# --------------------------------------------------------------------------------------
