from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "traffic"
    mysql_password: str = "traffic"
    mysql_database: str = "traffic"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_host: str = ""
    mongo_port: int = 27017
    mongo_db: str = "traffic"
    mongo_collection: str = "traffic_readings"
    init_on_startup: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def apply_mongo_host(self):
        host = self.mongo_host.strip()
        if host:
            self.mongo_uri = f"mongodb://{host}:{self.mongo_port}"
        return self

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"mysql+pymysql://{quote_plus(self.mysql_user)}:{quote_plus(self.mysql_password)}"
            f"@{self.mysql_host}:{self.mysql_port}/{quote_plus(self.mysql_database)}"
        )


settings = Settings()
