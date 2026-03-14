from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from routers import runs

load_dotenv()

# ============================================================
# レートリミット
# ============================================================
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# ============================================================
# アプリ
# ============================================================
app = FastAPI(title="STS2 Tracker API", version="0.1.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# ルーター
# ============================================================
app.include_router(runs.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
