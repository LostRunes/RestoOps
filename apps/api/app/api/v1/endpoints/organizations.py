from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import OrganizationResponse, OrganizationUpdate

router = APIRouter()


@router.get("/me", response_model=OrganizationResponse)
async def get_my_organization(
    current_user: Annotated[User, Depends(get_current_user)]
):
    return current_user.organization


@router.patch(
    "/me",
    response_model=OrganizationResponse,
    dependencies=[Depends(require_roles("OWNER"))],
)
async def update_my_organization(
    req: OrganizationUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    org = current_user.organization

    if req.name is not None:
        org.name = req.name
    if req.slug is not None:
        slug_check = await db.execute(
            select(Organization).where(
                Organization.slug == req.slug, Organization.id != org.id
            )
        )
        if slug_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Slug already taken",
            )
        org.slug = req.slug

    await db.commit()
    await db.refresh(org)

    return org
