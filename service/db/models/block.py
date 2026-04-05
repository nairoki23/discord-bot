from sqlalchemy import Table, Column, ForeignKey
from service.db.models.base import Base
user_blocks = Table(
    "user_blocks",
    Base.metadata,
    Column("blocker_id", ForeignKey("users.discord_id"), primary_key=True),
    Column("blocked_id", ForeignKey("users.discord_id"), primary_key=True),
)