from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "acos.main:app",
        host=os.getenv("ACOS_HOST", "0.0.0.0"),
        port=int(os.getenv("ACOS_PORT", "8000")),
        reload=os.getenv("ACOS_RELOAD", "false").lower() == "true",
    )
