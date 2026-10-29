import os
from datetime import datetime

os.environ["INIT_ON_STARTUP"] = "false"

from bson import ObjectId
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.db import get_db, get_readings_collection
from api.main import app
from api.models import Base

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=engine)


class MemoryCollection:
    def __init__(self):
        self.docs = []

    def insert_one(self, doc):
        stored = dict(doc)
        stored["_id"] = ObjectId()
        self.docs.append(stored)

        class Result:
            inserted_id = stored["_id"]

        return Result()

    def find_one(self, filt):
        for doc in self.docs:
            if _matches(doc, filt):
                return dict(doc)
        return None

    def find(self, filt):
        return _Cursor([dict(doc) for doc in self.docs if _matches(doc, filt)])

    def update_one(self, filt, update):
        for doc in self.docs:
            if _matches(doc, filt):
                doc.update(update["$set"])
                doc["_id"] = filt["_id"]

                class Result:
                    matched_count = 1

                return Result()

        class Missing:
            matched_count = 0

        return Missing()

    def delete_one(self, filt):
        for index, doc in enumerate(self.docs):
            if _matches(doc, filt):
                del self.docs[index]

                class Result:
                    deleted_count = 1

                return Result()

        class Missing:
            deleted_count = 0

        return Missing()


class _Cursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, keys):
        for field, direction in reversed(keys):
            self.docs.sort(key=lambda doc: doc.get(field), reverse=direction < 0)
        return self

    def skip(self, count):
        self.docs = self.docs[count:]
        return self

    def limit(self, count):
        self.docs = self.docs[:count]
        return self

    def __iter__(self):
        return iter(self.docs)


def _matches(doc, filt):
    for key, expected in filt.items():
        value = doc.get(key)
        if isinstance(expected, dict):
            if "$gte" in expected and value < expected["$gte"]:
                return False
            if "$lte" in expected and value > expected["$lte"]:
                return False
        elif value != expected:
            return False
    return True


def _override_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


collection = MemoryCollection()
app.dependency_overrides[get_db] = _override_db
app.dependency_overrides[get_readings_collection] = lambda: collection
client = TestClient(app)

SAMPLE = {
    "date_time": "2012-10-02T09:00:00",
    "temp": 288.28,
    "rain_1h": 0.0,
    "snow_1h": 0.0,
    "clouds_all": 40,
    "traffic_volume": 5545,
    "weather_main": "Clouds",
    "weather_description": "scattered clouds",
    "holiday": "None",
}


def _payload(**overrides):
    body = dict(SAMPLE)
    body.update(overrides)
    return body


def test_sql_crud_latest_and_range():
    created = client.post("/sql/readings", json=_payload())
    assert created.status_code == 201
    body = created.json()
    assert body["holiday"] is None
    assert body["traffic_volume"] == 5545
    reading_id = body["id"]

    later = client.post(
        "/sql/readings",
        json=_payload(
            date_time="2012-10-02T11:00:00",
            traffic_volume=4767,
            holiday="Labor Day",
            weather_description="broken clouds",
        ),
    )
    assert later.status_code == 201
    middle = client.post(
        "/sql/readings",
        json=_payload(date_time="2012-10-02T10:00:00", traffic_volume=4516),
    )
    assert middle.status_code == 201

    fetched = client.get(f"/sql/readings/{reading_id}")
    assert fetched.status_code == 200
    assert fetched.json()["weather_description"] == "scattered clouds"

    listed = client.get("/sql/readings")
    assert [row["date_time"] for row in listed.json()] == [
        "2012-10-02T11:00:00",
        "2012-10-02T10:00:00",
        "2012-10-02T09:00:00",
    ]

    latest = client.get("/sql/readings/latest")
    assert latest.json()["traffic_volume"] == 4767
    assert latest.json()["holiday"] == "Labor Day"

    window = client.get(
        "/sql/readings/range",
        params={"start": "2012-10-02T09:00:00", "end": "2012-10-02T10:00:00"},
    )
    assert window.status_code == 200
    assert [row["traffic_volume"] for row in window.json()] == [5545, 4516]

    bad_window = client.get(
        "/sql/readings/range",
        params={"start": "2012-10-03T00:00:00", "end": "2012-10-02T00:00:00"},
    )
    assert bad_window.status_code == 400

    updated = client.put(
        f"/sql/readings/{reading_id}",
        json=_payload(traffic_volume=5600, holiday="State Fair"),
    )
    assert updated.status_code == 200
    assert updated.json()["traffic_volume"] == 5600
    assert updated.json()["holiday"] == "State Fair"

    same_weather = client.post("/sql/readings", json=_payload(date_time="2012-10-02T12:00:00"))
    assert same_weather.status_code == 201

    assert client.delete(f"/sql/readings/{reading_id}").status_code == 204
    assert client.get(f"/sql/readings/{reading_id}").status_code == 404
    assert client.get("/sql/readings/999999").status_code == 404

    invalid = client.post("/sql/readings", json=_payload(clouds_all=120))
    assert invalid.status_code == 422


def test_mongo_crud_latest_and_range():
    created = client.post("/mongo/readings", json=_payload(holiday=None))
    assert created.status_code == 201
    reading_id = created.json()["id"]
    assert created.json()["holiday"] is None

    client.post(
        "/mongo/readings",
        json=_payload(date_time="2012-10-02T12:00:00", traffic_volume=5026, holiday="Christmas Day"),
    )
    client.post(
        "/mongo/readings",
        json=_payload(date_time="2012-10-02T08:00:00", traffic_volume=3000),
    )

    fetched = client.get(f"/mongo/readings/{reading_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == reading_id

    latest = client.get("/mongo/readings/latest")
    assert latest.json()["date_time"] == "2012-10-02T12:00:00"
    assert latest.json()["holiday"] == "Christmas Day"

    window = client.get(
        "/mongo/readings/range",
        params={"start": "2012-10-02T09:00:00", "end": "2012-10-02T12:00:00"},
    )
    assert [row["traffic_volume"] for row in window.json()] == [5545, 5026]

    updated = client.put(
        f"/mongo/readings/{reading_id}",
        json=_payload(temp=290.1, weather_main="Clear", weather_description="sky is clear"),
    )
    assert updated.status_code == 200
    assert updated.json()["temp"] == 290.1
    assert client.get(f"/mongo/readings/{reading_id}").json()["weather_main"] == "Clear"

    assert client.delete(f"/mongo/readings/{reading_id}").status_code == 204
    assert client.get(f"/mongo/readings/{reading_id}").status_code == 404
    assert client.get("/mongo/readings/not-an-id").status_code == 400
    assert client.delete("/mongo/readings/" + str(ObjectId())).status_code == 404

    sql_only = client.get("/sql/readings/latest")
    mongo_latest = client.get("/mongo/readings/latest")
    assert sql_only.json()["traffic_volume"] != mongo_latest.json()["traffic_volume"] or (
        sql_only.json()["date_time"] != mongo_latest.json()["date_time"]
    )


def test_health_is_independent_of_readings():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    root = client.get("/")
    assert root.status_code == 200
    assert root.json() == {
        "sql_readings": "/sql/readings",
        "mongo_readings": "/mongo/readings",
    }


def test_datetime_values_round_trip():
    moment = datetime(2012, 10, 2, 9, 0, 0)
    assert moment.isoformat() == "2012-10-02T09:00:00"
