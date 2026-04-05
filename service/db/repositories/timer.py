# services/db/repositories/timer.py
from sqlalchemy import select
from datetime import datetime
from services.db.models import Timer
from .base import BaseRepository

class TimerRepository(BaseRepository):

    async def create(self, user_id: str, run_at: datetime, channel_id: str) -> Timer:
        timer = Timer(
            user_id=user_id,
            run_at=run_at,
            channel_id=channel_id,
        )
        self.session.add(timer)
        await self.session.flush()
        return timer

    async def get_due(self, now: datetime):
        result = await self.session.execute(
            select(Timer).where(Timer.run_at <= now)
        )
        return result.scalars().all()

    async def delete(self, timer: Timer):
        await self.session.delete(timer)