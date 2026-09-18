from fastapi import APIRouter
from app.api.v1.endpoints import (
    ai,
    auth,
    campaigns,
    conversations,
    leads,
    organizations,
    restaurants,
    suppression,
    users,
    verification,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(
    organizations.router, prefix="/organizations", tags=["Organizations"]
)
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(
    restaurants.router, prefix="/restaurants", tags=["Restaurants"]
)
api_router.include_router(leads.router, prefix="/leads", tags=["Leads"])
api_router.include_router(
    verification.router, prefix="/verification", tags=["Verification"]
)
api_router.include_router(
    suppression.router, prefix="/suppression", tags=["Suppression"]
)
api_router.include_router(
    campaigns.router, prefix="/campaigns", tags=["Campaigns"]
)
api_router.include_router(
    conversations.router, prefix="/conversations", tags=["Conversations"]
)
api_router.include_router(ai.router, prefix="/ai", tags=["AI"])
