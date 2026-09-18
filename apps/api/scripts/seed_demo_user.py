import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import AsyncSessionLocal
from app.models.organization import Organization
from app.models.role import Role
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select


async def main():
    async with AsyncSessionLocal() as session:
        # Seed Roles
        roles = ["OWNER", "ADMIN", "AGENT"]
        role_objs = {}
        for r_name in roles:
            res = await session.execute(select(Role).where(Role.name == r_name))
            r = res.scalar_one_or_none()
            if not r:
                r = Role(name=r_name, description=f"{r_name} role")
                session.add(r)
                await session.flush()
            role_objs[r_name] = r

        # Check Org
        res = await session.execute(select(Organization).where(Organization.slug == "restoops-demo"))
        org = res.scalar_one_or_none()
        if not org:
            org = Organization(name="RestoOps Demo Org", slug="restoops-demo")
            session.add(org)
            await session.flush()

        # Check User
        res = await session.execute(select(User).where(User.email == "owner@restoops.com"))
        user = res.scalar_one_or_none()
        if not user:
            user = User(
                organization_id=org.id,
                role_id=role_objs["OWNER"].id,
                email="owner@restoops.com",
                first_name="RestoOps",
                last_name="Owner",
                password_hash=get_password_hash("password123"),
                is_active=True,
            )
            session.add(user)
            await session.commit()
            print("Successfully seeded owner user: owner@restoops.com / password123")
        else:
            user.password_hash = get_password_hash("password123")
            await session.commit()
            print("Updated owner@restoops.com password to password123")

if __name__ == "__main__":
    asyncio.run(main())
