import pytest
from fastapi.testclient import TestClient

from acos.main import app
from acos.search import is_trusted_domain, local_search, validate_source_url


def test_search_is_deterministic_and_local():
    assert local_search("bounded simulation")[0]["url"].startswith("local://")
    assert is_trusted_domain("example.gov")
    assert is_trusted_domain("docs.python.org")
    assert not is_trusted_domain("example.com")


def test_search_rejects_untrusted_domains_and_network_stays_disabled():
    client = TestClient(app)
    response = client.post("/api/search", json={"query": "test", "domains": ["example.com"]})
    assert response.status_code == 422
    response = client.post("/api/search", json={"query": "test", "network": True})
    assert response.status_code == 200
    assert response.json()["network"] is False
    assert response.json()["provider"] == "local-fallback"


def test_source_url_requires_https_and_trusted_host():
    with pytest.raises(ValueError):
        validate_source_url("http://example.gov")
    assert validate_source_url("https://docs.python.org/3/").startswith("https://")


def test_incognito_message_does_not_persist_chat_history():
    client = TestClient(app)
    response = client.post(
        "/api/message",
        json={"text": "temporary question", "context": {"incognito": True}},
    )
    assert response.status_code == 200
    conversation_id = response.json()["data"]["conversation_id"]
    assert client.get(f"/api/conversations/{conversation_id}/metadata").status_code == 404
