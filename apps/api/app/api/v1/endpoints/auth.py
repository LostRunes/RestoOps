from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    hash_token,
    verify_password,
)
from app.db.session import get_db
from app.models.organization import Organization
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    Token,
)
from app.schemas.user import UserResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_211_CREATED if hasattr(status, 'HTTP_211_CREATED') else status.HTTP_201_CREATED)
async def register_organization(
    req: RegisterRequest, db: Annotated[AsyncSession, Depends(get_db)]
):
    # Check if email exists
    email_check = await db.execute(select(User).where(User.email == req.email))
    if email_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Check if org slug exists
    slug_check = await db.execute(
        select(Organization).where(Organization.slug == req.organization_slug)
    )
    if slug_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization slug already taken",
        )

    # Get OWNER role
    owner_role = await db.execute(select(Role).where(Role.name == "OWNER"))
    role = owner_role.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default roles not initialized in database",
        )

    # Create Org
    org = Organization(name=req.organization_name, slug=req.organization_slug)
    db.add(org)
    await db.flush()

    # Create Owner User
    user = User(
        organization_id=org.id,
        role_id=role.id,
        email=req.email,
        password_hash=get_password_hash(req.password),
        first_name=req.first_name,
        last_name=req.last_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


@router.post("/login", response_model=Token)
async def login(req: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    stmt = select(User).where(User.email == req.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    access_token = create_access_token(user.id)
    raw_refresh_token, expires_at = create_refresh_token(user.id)

    # Save refresh token hash
    rf_token_obj = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh_token),
        expires_at=expires_at,
    )
    db.add(rf_token_obj)
    await db.commit()

    return Token(access_token=access_token, refresh_token=raw_refresh_token)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    req: RefreshTokenRequest, db: Annotated[AsyncSession, Depends(get_db)]
):
    try:
        payload = decode_token(req.refresh_token)
        user_id: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if user_id is None or token_type != "refresh":
            raise ValueError()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    token_h = hash_token(req.refresh_token)
    stmt = select(RefreshToken).where(
        RefreshToken.token_hash == token_h,
        RefreshToken.is_revoked == False,
        RefreshToken.expires_at > datetime.now(timezone.utc),
    )
    result = await db.execute(stmt)
    token_obj = result.scalar_one_or_none()

    if not token_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired or revoked",
        )

    # Revoke old refresh token
    token_obj.is_revoked = True

    # Generate new tokens
    new_access_token = create_access_token(user_id)
    new_refresh_token, expires_at = create_refresh_token(user_id)

    new_token_obj = RefreshToken(
        user_id=user_id,
        token_hash=hash_token(new_refresh_token),
        expires_at=expires_at,
    )
    db.add(new_token_obj)
    await db.commit()

    return Token(access_token=new_access_token, refresh_token=new_refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user
