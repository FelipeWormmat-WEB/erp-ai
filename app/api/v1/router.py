from fastapi import APIRouter

from app.api.v1.routers import agent, auth, overview, products, reports


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(products.router)
api_router.include_router(overview.router)
api_router.include_router(reports.router)
api_router.include_router(agent.router)
