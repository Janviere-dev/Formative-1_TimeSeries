from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["version"])

API_NAME = "Metro Interstate Traffic Volume API"
API_VERSION = "0.1.0"


class VersionInfo(BaseModel):
    name: str
    version: str


@router.get("/version", response_model=VersionInfo)
def version() -> VersionInfo:
    return VersionInfo(name=API_NAME, version=API_VERSION)
