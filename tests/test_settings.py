from config.settings import get_settings


def test_settings_use_environment_values(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("APP_TIMEZONE", "America/New_York")
    monkeypatch.setenv("DAILY_NOTIFICATION_ENABLED", "true")

    settings = get_settings()

    assert settings.database_url == "sqlite:///:memory:"
    assert settings.app_timezone == "America/New_York"
    assert settings.daily_notification_enabled is True