from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from api.db import get_db
from api.models import Holiday, TrafficReading, WeatherCondition
from api.schemas import ReadingCreate, SqlReading

router = APIRouter(prefix="/sql/readings", tags=["sql"])


def _reading_query(db: Session):
    return select(TrafficReading).options(
        joinedload(TrafficReading.weather),
        joinedload(TrafficReading.holiday),
    )


def _to_reading(row: TrafficReading) -> SqlReading:
    return SqlReading(
        id=row.id,
        date_time=row.date_time,
        temp=row.temp,
        rain_1h=row.rain_1h,
        snow_1h=row.snow_1h,
        clouds_all=row.clouds_all,
        traffic_volume=row.traffic_volume,
        weather_main=row.weather.weather_main,
        weather_description=row.weather.weather_description,
        holiday=row.holiday.name if row.holiday else None,
    )


def _weather(db: Session, body: ReadingCreate) -> WeatherCondition:
    row = db.scalar(
        select(WeatherCondition).where(
            WeatherCondition.weather_main == body.weather_main,
            WeatherCondition.weather_description == body.weather_description,
        )
    )
    if row is None:
        row = WeatherCondition(
            weather_main=body.weather_main,
            weather_description=body.weather_description,
        )
        db.add(row)
        db.flush()
    return row


def _holiday(db: Session, name: str | None) -> Holiday | None:
    if name is None:
        return None
    row = db.scalar(select(Holiday).where(Holiday.name == name))
    if row is None:
        row = Holiday(name=name)
        db.add(row)
        db.flush()
    return row


def _get_or_404(db: Session, reading_id: int) -> TrafficReading:
    row = db.scalar(_reading_query(db).where(TrafficReading.id == reading_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Reading not found")
    return row


def _apply(row: TrafficReading, body: ReadingCreate, db: Session) -> None:
    holiday = _holiday(db, body.holiday)
    row.date_time = body.date_time
    row.temp = body.temp
    row.rain_1h = body.rain_1h
    row.snow_1h = body.snow_1h
    row.clouds_all = body.clouds_all
    row.traffic_volume = body.traffic_volume
    row.weather = _weather(db, body)
    row.holiday = holiday


def _check_range(start: datetime, end: datetime) -> None:
    if start > end:
        raise HTTPException(status_code=400, detail="start must be before or equal to end")


@router.post("", response_model=SqlReading, status_code=201)
def create_reading(body: ReadingCreate, db: Session = Depends(get_db)) -> SqlReading:
    row = TrafficReading(
        date_time=body.date_time,
        temp=body.temp,
        rain_1h=body.rain_1h,
        snow_1h=body.snow_1h,
        clouds_all=body.clouds_all,
        traffic_volume=body.traffic_volume,
    )
    _apply(row, body, db)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_reading(_get_or_404(db, row.id))


@router.get("/latest", response_model=SqlReading)
def latest_reading(db: Session = Depends(get_db)) -> SqlReading:
    row = db.scalar(
        _reading_query(db).order_by(TrafficReading.date_time.desc(), TrafficReading.id.desc()).limit(1)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="No readings found")
    return _to_reading(row)


@router.get("/range", response_model=list[SqlReading])
def readings_by_range(
    start: datetime,
    end: datetime,
    db: Session = Depends(get_db),
) -> list[SqlReading]:
    _check_range(start, end)
    rows = db.scalars(
        _reading_query(db)
        .where(TrafficReading.date_time >= start, TrafficReading.date_time <= end)
        .order_by(TrafficReading.date_time.asc(), TrafficReading.id.asc())
    ).unique().all()
    return [_to_reading(row) for row in rows]


@router.get("", response_model=list[SqlReading])
def list_readings(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[SqlReading]:
    rows = db.scalars(
        _reading_query(db)
        .order_by(TrafficReading.date_time.desc(), TrafficReading.id.desc())
        .offset(offset)
        .limit(limit)
    ).unique().all()
    return [_to_reading(row) for row in rows]


@router.get("/{reading_id}", response_model=SqlReading)
def get_reading(reading_id: int, db: Session = Depends(get_db)) -> SqlReading:
    return _to_reading(_get_or_404(db, reading_id))


@router.put("/{reading_id}", response_model=SqlReading)
def update_reading(
    reading_id: int,
    body: ReadingCreate,
    db: Session = Depends(get_db),
) -> SqlReading:
    row = _get_or_404(db, reading_id)
    _apply(row, body, db)
    db.commit()
    return _to_reading(_get_or_404(db, reading_id))


@router.delete("/{reading_id}", status_code=204)
def delete_reading(reading_id: int, db: Session = Depends(get_db)) -> Response:
    row = _get_or_404(db, reading_id)
    db.delete(row)
    db.commit()
    return Response(status_code=204)
