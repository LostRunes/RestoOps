from fastapi import APIRouter
from app.api.v1.endpoints import (
    ai,
    auth,
    calls,
    campaigns,
    conversations,
    leads,
    notifications,
    orders,
    organizations,
    quotes,
    restaurants,
    suppression,
    users,
    verification,
    webhooks,
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
api_router.include_router(quotes.router, prefix="/quotes", tags=["Quotes"])
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_router.include_router(calls.router, prefix="/calls", tags=["Calls"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
