from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ReadingCreate(BaseModel):
    date_time: datetime
    temp: float
    rain_1h: float = Field(ge=0)
    snow_1h: float = Field(ge=0)
    clouds_all: int = Field(ge=0, le=100)
    traffic_volume: int = Field(ge=0)
    weather_main: str = Field(min_length=1, max_length=32)
    weather_description: str = Field(min_length=1, max_length=64)
    holiday: str | None = Field(default=None, max_length=64)

    @field_validator("holiday", mode="before")
    @classmethod
    def blank_holiday_is_null(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if value == "" or value.lower() == "none":
                return None
        return value

    @field_validator("weather_main", "weather_description")
    @classmethod
    def strip_weather(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value


class SqlReading(ReadingCreate):
    id: int


class MongoReading(ReadingCreate):
    id: str


class HealthStatus(BaseModel):
    status: str
