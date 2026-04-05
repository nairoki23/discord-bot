from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String

class User(Base):
    __tablename__ = "users"

    discord_id: Mapped[str] = mapped_column(String, primary_key=True)

    # ブロック
    blocked_users: Mapped[list["User"]] = relationship(
        "User",
        secondary=user_blocks,
        primaryjoin=discord_id == user_blocks.c.blocker_id,
        secondaryjoin=discord_id == user_blocks.c.blocked_id,
        backref="blocked_by",
    )

    # 関連
    timers: Mapped[list["Timer"]] = relationship(back_populates="user")
    trackings: Mapped[list["Tracking"]] = relationship(back_populates="owner")