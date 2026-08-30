"""Dev entrypoint: `python main.py` boots the app defined in app/main.py."""
from __future__ import annotations

if __name__ == "__main__":
    import uvicorn
    from app.core.config import settings

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.DEBUG,
        # Don't restart the server when training writes model pickles or logs
        reload_excludes=["saved_models/*", "*.pkl", "*.log"],
    )
