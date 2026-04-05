# services/db/repositories/tracking.py
from sqlalchemy import select
from services.db.models import Tracking, TrackingHistory, User
from .base import BaseRepository

class TrackingRepository(BaseRepository):

    async def create(self, owner_id: str, carrier, tracking_id: str) -> Tracking:
        tracking = Tracking(
            owner_id=owner_id,
            carrier=carrier,
            tracking_id=tracking_id,
        )
        self.session.add(tracking)
        await self.session.flush()
        return tracking

    async def add_receiver(self, tracking: Tracking, user: User):
        tracking.receivers.append(user)
        await self.session.flush()

    async def add_history(
        self,
        tracking: Tracking,
        state: str,
        details: str,
    ) -> TrackingHistory:
        history = TrackingHistory(
            state=state,
            details_text=details,
            details_length=len(details),
        )
        tracking.histories.append(history)
        await self.session.flush()
        return history

    async def get_by_number(self, carrier, tracking_id: str) -> Tracking | None:
        result = await self.session.execute(
            select(Tracking).where(
                Tracking.carrier == carrier,
                Tracking.tracking_id == tracking_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_all(self):
        result = await self.session.execute(select(Tracking))
        return result.scalars().all()