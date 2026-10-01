from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from govasset_api import database
from govasset_api.main import create_app


def test_vercel_postgres_engine_uses_transaction_pooler_safe_settings(monkeypatch):
    captured = {}
    configured_engine = object()

    def fake_create_engine(url, **kwargs):
        captured.update(url=url, **kwargs)
        return SimpleNamespace(
            dialect=SimpleNamespace(name="postgresql"),
            execution_options=lambda **_options: configured_engine,
        )

    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setattr(database, "create_engine", fake_create_engine)

    assert database.make_engine("postgresql://user:password@localhost/database") is configured_engine
    assert captured["url"].startswith("postgresql+psycopg://")
    assert captured["connect_args"] == {
        "prepare_threshold": None,
        "sslmode": "require",
        "connect_timeout": 10,
    }
    assert captured["pool_size"] == 1
    assert captured["max_overflow"] == 0
    assert captured["pool_pre_ping"] is True


def test_vercel_runtime_rejects_disabled_authentication(monkeypatch):
    engine = create_engine("sqlite://")
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("AUTH_REQUIRED", "false")
    monkeypatch.setattr("govasset_api.main.make_engine", lambda: engine)

    with pytest.raises(RuntimeError, match="Hosted mode requires AUTH_REQUIRED=true"):
        with TestClient(create_app()):
            pass

    engine.dispose()
