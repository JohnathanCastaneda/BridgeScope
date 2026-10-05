from fastapi import APIRouter

from bridgescope.api.v1.routes.bridges import router as bridges_router

router = APIRouter()

router.include_router(
    bridges_router,
    prefix="/bridges",
    tags=["bridges"],
)
