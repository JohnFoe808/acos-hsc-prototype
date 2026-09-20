from uuid import uuid4

from fastapi.testclient import TestClient

from acos.main import app


def test_conversation_create_list_revisit_rename_and_message_persistence():
    client = TestClient(app)
    title = f"Project {uuid4().hex[:8]}"

    created = client.post("/api/conversations", json={"title": title})
    assert created.status_code == 200
    conversation = created.json()
    conversation_id = conversation["id"]
    assert conversation["title"] == title

    message = client.post(
        "/api/message",
        json={"conversation_id": conversation_id, "text": "What should I do next?"},
    )
    assert message.status_code == 200
    assert message.json()["data"]["conversation_id"] == conversation_id

    renamed = client.patch(
        f"/api/conversations/{conversation_id}", json={"title": "Renamed project"}
    )
    assert renamed.json()["title"] == "Renamed project"
    assert any(
        item["id"] == conversation_id
        for item in client.get("/api/conversations").json()
    )

    metadata = client.get(f"/api/conversations/{conversation_id}/metadata").json()
    assert metadata["title"] == "Renamed project"
    assert metadata["message_count"] == 2
    history = client.get(f"/api/conversations/{conversation_id}").json()
    assert [item["role"] for item in history] == ["user", "assistant"]
