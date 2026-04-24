from fastapi import APIRouter

from backend.app.api.routes import auth, conversations, dashboard, health, messaging, onboarding, ops, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(onboarding.router)
api_router.include_router(dashboard.router)
api_router.include_router(conversations.router)
api_router.include_router(messaging.router)
api_router.include_router(ops.router)
