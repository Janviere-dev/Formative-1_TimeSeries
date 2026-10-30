from api.config import Settings


def test_password_is_escaped_in_sqlalchemy_url():
    settings = Settings(
        mysql_user="traffic",
        mysql_password="a/b+c=",
        mysql_host="db",
        mysql_port=3306,
        mysql_database="traffic",
    )
    assert settings.sqlalchemy_url == "mysql+pymysql://traffic:a%2Fb%2Bc%3D@db:3306/traffic"


def test_mongo_host_overrides_uri():
    settings = Settings(mongo_host="traffic-mongo", mongo_port=27017)
    assert settings.mongo_uri == "mongodb://traffic-mongo:27017"


def test_blank_mongo_host_keeps_uri():
    settings = Settings(mongo_host="", mongo_uri="mongodb://mongodb:27017")
    assert settings.mongo_uri == "mongodb://mongodb:27017"
