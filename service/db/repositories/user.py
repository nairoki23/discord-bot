# services/db/repositories/user.py
from sqlalchemy import select
from services.db.models import User
from .base import BaseRepository

class UserRepository(BaseRepository):

    async def get(self, discord_id: str) -> User | None:
        return await self.session.get(User, discord_id)

    async def create(self, discord_id: str) -> User:
        user = User(discord_id=discord_id)
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_or_create(self, discord_id: str) -> User:
        user = await self.get(discord_id)
        if user:
            return user
        return await self.create(discord_id)

    async def block(self, a: str, b: str):
        user_a = await self.get(a)
        user_b = await self.get(b)
        user_a.blocked_users.append(user_b)
        await self.session.flush()

    async def is_blocked(self, a: str, b: str) -> bool:
        user_a = await self.get(a)
        user_b = await self.get(b)
        return user_b in user_a.blocked_users or user_a in user_b.blocked_users