import asyncio

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.user import User
from app.repositories.users import user_repository


async def seed_user() -> None:
    settings = get_settings()
    async with AsyncSessionFactory() as session:
        existing_user = await user_repository.get_by_username(
            session, settings.seed_username
        )
        if existing_user is not None:
            print(f"Usuário seed '{settings.seed_username}' já existe.")
            return

        session.add(
            User(
                username=settings.seed_username,
                password_hash=hash_password(settings.seed_password),
            )
        )
        await session.commit()
        print(f"Usuário seed '{settings.seed_username}' criado.")


if __name__ == "__main__":
    asyncio.run(seed_user())
