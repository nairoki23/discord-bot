from sqlalchemy import Integer, String, ForeignKey, UniqueConstraint

class Tracking(Base):
    __tablename__ = "trackings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    carrier: Mapped[Carrier] = mapped_column(Enum(Carrier))
    tracking_id: Mapped[str] = mapped_column(String)

    owner_id: Mapped[str] = mapped_column(ForeignKey("users.discord_id"))
    owner: Mapped["User"] = relationship(back_populates="trackings")

    receivers: Mapped[list["User"]] = relationship(
        "User",
        secondary=tracking_receivers,
    )

    histories: Mapped[list["TrackingHistory"]] = relationship(
        back_populates="tracking",
        cascade="all, delete-orphan",
        order_by="TrackingHistory.created_at",
    )

    __table_args__ = (
        UniqueConstraint("carrier", "tracking_id"),
    )