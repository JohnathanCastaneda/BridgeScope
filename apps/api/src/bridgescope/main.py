from fastapi import FastAPI

from bridgescope.api.error_handlers import register_exception_handlers
from bridgescope.api.router import api_router

app = FastAPI(
    title="BridgeScope API",
    version="0.1.0",
)

register_exception_handlers(app)
app.include_router(api_router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Confirm that the API process is running."""
    return {"status": "ok"}
