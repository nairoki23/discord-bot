tracking_receivers = Table(
    "tracking_receivers",
    Base.metadata,
    Column("tracking_id", ForeignKey("trackings.id"), primary_key=True),
    Column("user_id", ForeignKey("users.discord_id"), primary_key=True),
)