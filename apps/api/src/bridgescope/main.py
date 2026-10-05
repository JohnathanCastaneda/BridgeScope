from fastapi import FastAPI

from bridgescope.api.router import api_router

app = FastAPI(
    title="BridgeScope API",
    version="0.1.0",
)

app.include_router(api_router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Confirm that the API process is running."""
    return {"status": "ok"}
