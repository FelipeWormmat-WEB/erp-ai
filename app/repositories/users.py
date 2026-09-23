import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    async def get_by_username(
        self, session: AsyncSession, username: str
    ) -> User | None:
        result = await session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_id(
        self, session: AsyncSession, user_id: uuid.UUID
    ) -> User | None:
        return await session.get(User, user_id)


user_repository = UserRepository()
