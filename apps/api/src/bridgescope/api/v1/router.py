from fastapi import APIRouter

from bridgescope.api.v1.routes.bridges import router as bridges_router
from bridgescope.api.v1.routes.rankings import router as rankings_router

router = APIRouter()

router.include_router(
    bridges_router,
    prefix="/bridges",
    tags=["bridges"],
)

router.include_router(
    rankings_router,
    prefix="/rankings",
    tags=["rankings"],
)
