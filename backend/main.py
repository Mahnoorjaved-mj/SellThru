"""Entrypoint: `python main.py` boots the app defined in app/main.py."""
from __future__ import annotations
import os

if __name__ == "__main__":
    import uvicorn
    from app.core.config import settings

    # In production (e.g. Render), host must be 0.0.0.0 and port is assigned via $PORT
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=settings.DEBUG,
        # Don't restart the server when training writes model pickles or logs
        reload_excludes=["saved_models/*", "*.pkl", "*.log"],
    )
