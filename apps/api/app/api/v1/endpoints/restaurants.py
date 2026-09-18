from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.restaurant import Restaurant
from app.models.user import User
from app.schemas.restaurant import (
    RestaurantCreate,
    RestaurantResponse,
    RestaurantUpdate,
)

router = APIRouter()


@router.get("/", response_model=List[RestaurantResponse])
async def list_restaurants(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    stmt = select(Restaurant).where(
        Restaurant.organization_id == current_user.organization_id
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post(
    "/",
    response_model=RestaurantResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "MANAGER"))],
)
async def create_restaurant(
    req: RestaurantCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    restaurant = Restaurant(
        organization_id=current_user.organization_id,
        name=req.name,
        address=req.address,
        city=req.city,
        state=req.state,
        zip_code=req.zip_code,
        phone=req.phone,
        cuisine_type=req.cuisine_type,
        is_active=req.is_active,
    )
    db.add(restaurant)
    await db.commit()
    await db.refresh(restaurant)

    return restaurant


@router.get("/{restaurant_id}", response_model=RestaurantResponse)
async def get_restaurant(
    restaurant_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    stmt = select(Restaurant).where(
        Restaurant.id == restaurant_id,
        Restaurant.organization_id == current_user.organization_id,
    )
    result = await db.execute(stmt)
    restaurant = result.scalar_one_or_none()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found"
        )

    return restaurant


@router.patch(
    "/{restaurant_id}",
    response_model=RestaurantResponse,
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "MANAGER"))],
)
async def update_restaurant(
    restaurant_id: str,
    req: RestaurantUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    stmt = select(Restaurant).where(
        Restaurant.id == restaurant_id,
        Restaurant.organization_id == current_user.organization_id,
    )
    result = await db.execute(stmt)
    restaurant = result.scalar_one_or_none()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found"
        )

    for field, val in req.model_dump(exclude_unset=True).items():
        setattr(restaurant, field, val)

    await db.commit()
    await db.refresh(restaurant)

    return restaurant


@router.delete(
    "/{restaurant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("OWNER", "ADMIN"))],
)
async def delete_restaurant(
    restaurant_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    stmt = select(Restaurant).where(
        Restaurant.id == restaurant_id,
        Restaurant.organization_id == current_user.organization_id,
    )
    result = await db.execute(stmt)
    restaurant = result.scalar_one_or_none()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found"
        )

    await db.delete(restaurant)
    await db.commit()
