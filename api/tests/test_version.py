from api.tests.test_readings import client


def test_version_is_static():
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {
        "name": "Metro Interstate Traffic Volume API",
        "version": "0.1.0",
    }
