from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Holiday(Base):
    __tablename__ = "holidays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    readings: Mapped[list["TrafficReading"]] = relationship(back_populates="holiday")


class WeatherCondition(Base):
    __tablename__ = "weather_conditions"
    __table_args__ = (
        UniqueConstraint("weather_main", "weather_description", name="uq_weather"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    weather_main: Mapped[str] = mapped_column(String(32), nullable=False)
    weather_description: Mapped[str] = mapped_column(String(64), nullable=False)
    readings: Mapped[list["TrafficReading"]] = relationship(back_populates="weather")


class TrafficReading(Base):
    __tablename__ = "traffic_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    temp: Mapped[float] = mapped_column(Float, nullable=False)
    rain_1h: Mapped[float] = mapped_column(Float, nullable=False)
    snow_1h: Mapped[float] = mapped_column(Float, nullable=False)
    clouds_all: Mapped[int] = mapped_column(Integer, nullable=False)
    traffic_volume: Mapped[int] = mapped_column(Integer, nullable=False)
    weather_id: Mapped[int] = mapped_column(ForeignKey("weather_conditions.id"), nullable=False)
    holiday_id: Mapped[int | None] = mapped_column(ForeignKey("holidays.id"), nullable=True)
    weather: Mapped[WeatherCondition] = relationship(back_populates="readings")
    holiday: Mapped[Holiday | None] = relationship(back_populates="readings")
