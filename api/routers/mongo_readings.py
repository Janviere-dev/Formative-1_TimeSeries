from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pymongo.collection import Collection

from api.db import get_readings_collection
from api.schemas import MongoReading, ReadingCreate

router = APIRouter(prefix="/mongo/readings", tags=["mongo"])


def _parse_id(reading_id: str) -> ObjectId:
    try:
        return ObjectId(reading_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid reading id") from None


def _to_reading(doc: dict) -> MongoReading:
    return MongoReading(
        id=str(doc["_id"]),
        date_time=doc["date_time"],
        temp=doc["temp"],
        rain_1h=doc["rain_1h"],
        snow_1h=doc["snow_1h"],
        clouds_all=doc["clouds_all"],
        traffic_volume=doc["traffic_volume"],
        weather_main=doc["weather_main"],
        weather_description=doc["weather_description"],
        holiday=doc.get("holiday"),
    )


def _check_range(start: datetime, end: datetime) -> None:
    if start > end:
        raise HTTPException(status_code=400, detail="start must be before or equal to end")


@router.post("", response_model=MongoReading, status_code=201)
def create_reading(
    body: ReadingCreate,
    collection: Collection = Depends(get_readings_collection),
) -> MongoReading:
    result = collection.insert_one(body.model_dump())
    doc = collection.find_one({"_id": result.inserted_id})
    return _to_reading(doc)


@router.get("/latest", response_model=MongoReading)
def latest_reading(collection: Collection = Depends(get_readings_collection)) -> MongoReading:
    docs = list(collection.find({}).sort([("date_time", -1), ("_id", -1)]).limit(1))
    if not docs:
        raise HTTPException(status_code=404, detail="No readings found")
    return _to_reading(docs[0])


@router.get("/range", response_model=list[MongoReading])
def readings_by_range(
    start: datetime,
    end: datetime,
    collection: Collection = Depends(get_readings_collection),
) -> list[MongoReading]:
    _check_range(start, end)
    docs = collection.find({"date_time": {"$gte": start, "$lte": end}}).sort(
        [("date_time", 1), ("_id", 1)]
    )
    return [_to_reading(doc) for doc in docs]


@router.get("", response_model=list[MongoReading])
def list_readings(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    collection: Collection = Depends(get_readings_collection),
) -> list[MongoReading]:
    docs = (
        collection.find({})
        .sort([("date_time", -1), ("_id", -1)])
        .skip(offset)
        .limit(limit)
    )
    return [_to_reading(doc) for doc in docs]


@router.get("/{reading_id}", response_model=MongoReading)
def get_reading(
    reading_id: str,
    collection: Collection = Depends(get_readings_collection),
) -> MongoReading:
    doc = collection.find_one({"_id": _parse_id(reading_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Reading not found")
    return _to_reading(doc)


@router.put("/{reading_id}", response_model=MongoReading)
def update_reading(
    reading_id: str,
    body: ReadingCreate,
    collection: Collection = Depends(get_readings_collection),
) -> MongoReading:
    oid = _parse_id(reading_id)
    result = collection.update_one({"_id": oid}, {"$set": body.model_dump()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Reading not found")
    return _to_reading(collection.find_one({"_id": oid}))


@router.delete("/{reading_id}", status_code=204)
def delete_reading(
    reading_id: str,
    collection: Collection = Depends(get_readings_collection),
) -> Response:
    result = collection.delete_one({"_id": _parse_id(reading_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Reading not found")
    return Response(status_code=204)
