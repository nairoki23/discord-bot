# services/db/uow.py
from services.db.session import SessionLocal
from services.db.repositories.user import UserRepository
from services.db.repositories.timer import TimerRepository
from services.db.repositories.tracking import TrackingRepository

class UnitOfWork:
    async def __aenter__(self):
        self.session = SessionLocal()
        self.user = UserRepository(self.session)
        self.timer = TimerRepository(self.session)
        self.tracking = TrackingRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc:
            await self.session.rollback()
        else:
            await self.session.commit()
        await self.session.close()