from sqlalchemy import Text, DateTime
from datetime import datetime

class TrackingDetail(Base):
    __tablename__ = "tracking_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    tracking_id: Mapped[int] = mapped_column(ForeignKey("trackings.id"))
    tracking: Mapped["Tracking"] = relationship(back_populates="histories")

    state: Mapped[str] = mapped_column(String)

    details_length: Mapped[int] = mapped_column(Integer)
    details_text: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)