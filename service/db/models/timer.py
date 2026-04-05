from sqlalchemy import DateTime, ForeignKey, Integer

class Timer(Base):
    __tablename__ = "timers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    run_at: Mapped = mapped_column(DateTime)
    channel_id: Mapped[str] = mapped_column(String)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.discord_id"))
    user: Mapped["User"] = relationship(back_populates="timers")