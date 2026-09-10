from datetime import date
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    db_response = client.get("/api/health/database")
    assert db_response.status_code == 200
    assert db_response.json()["database"] in {"available", "unavailable"}


def test_discovery_endpoints_and_pagination():
    response = client.get("/api/discoveries/today")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert payload

    first = payload[0]
    discovery_id = first["id"]

    response = client.get(f"/api/discoveries/{date.today().isoformat()}")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    response = client.get(f"/api/discoveries/{discovery_id}")
    assert response.status_code == 200
    assert response.json()["id"] == discovery_id

    response = client.get("/api/discoveries?limit=10&offset=0")
    assert response.status_code == 200
    assert "items" in response.json()


def test_favorites_and_history_endpoints():
    response = client.get("/api/discoveries/today")
    discovery_id = response.json()[0]["id"]

    favorite = client.post(f"/api/discoveries/{discovery_id}/favorite")
    assert favorite.status_code == 200
    assert favorite.json()["favorite"] is True

    response = client.get("/api/favorites")
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] or payload["items"] == []

    history = client.get("/api/history")
    assert history.status_code == 200
    assert "items" in history.json()


def test_quiz_flow():
    today = date.today().isoformat()
    quiz_response = client.get("/api/quiz/today")
    assert quiz_response.status_code == 200
    questions = quiz_response.json()
    assert questions

    payload = {str(question["id"]): "A" for question in questions}
    response = client.post(
        "/api/quiz/submit",
        json={"quiz_date": today, "answers": payload},
    )
    assert response.status_code == 200
    data = response.json()
    assert "score" in data
    assert "total_questions" in data


def test_statistics_search_and_settings_endpoints():
    stats_response = client.get("/api/statistics")
    assert stats_response.status_code == 200
    assert "xp" in stats_response.json()

    search_response = client.get("/api/search?q=Science")
    assert search_response.status_code == 200
    assert "items" in search_response.json()

    settings_response = client.get("/api/settings")
    assert settings_response.status_code == 200
    assert "theme" in settings_response.json()

    put_response = client.put(
        "/api/settings",
        json={
            "theme": "Science",
            "enabled_categories": ["Science", "Space"],
            "timezone": "UTC",
            "daily_notification_enabled": False,
        },
    )
    assert put_response.status_code == 200
    assert put_response.json()["theme"] == "Science"


def test_recommendations_endpoint():
    response = client.get("/api/recommendations")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
